"""The ordered verification gate for print-ready grafts."""
from __future__ import annotations

from typing import Any

import numpy as np
import trimesh

from .meshio import component_count
from .pocket import (
    PocketDetectionError,
    PocketMeasurements,
    comparison_tolerance_mm,
    detect_pocket,
    pocket_differences,
)

LIKELY_CAUSES = {
    "single_component": "the scan and base did not overlap enough, or debris survived scan cleanup",
    "watertight": "an input had open boundaries or the boolean produced an open seam",
    "no_non_manifold_edges": "the boolean created overlapping faces or a junction shared by more than two faces",
    "volume_exceeds_base": "the boolean silently returned the base unchanged or added only numerical noise",
    "pocket_intact": "grafted geometry filled, shifted, or obscured the ferrule pocket",
    "height_within_tolerance": "the supplied --height does not match the finished graft or the scan scale is wrong",
    "scale_verified": (
        "no --height was supplied, so the scan's real-world size was never checked. "
        "Photogrammetry from photos without depth data produces an arbitrary scale "
        "(measured 4-8x oversize on this project). Pass a caliper-measured --height, "
        "or --allow-unverified-scale if the size genuinely does not matter"
    ),
}


def non_manifold_edge_count(mesh: trimesh.Trimesh) -> int:
    edges = np.sort(np.asarray(mesh.edges, dtype=np.int64), axis=1)
    if len(edges) == 0:
        return 0
    _, counts = np.unique(edges, axis=0, return_counts=True)
    return int(np.count_nonzero(counts > 2))


def _check(name: str, passed: bool, measured: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "pass": bool(passed), "measured": measured, "expected": expected}


def run_verification(
    result: trimesh.Trimesh,
    base: trimesh.Trimesh,
    pocket_before: PocketMeasurements,
    target_height_mm: float | None = None,
    allow_unverified_scale: bool = False,
    expected_total_height_mm: float | None = None,
) -> list[dict[str, Any]]:
    """Run checks in the exact order required by the cross-process contract."""
    checks: list[dict[str, Any]] = []

    # Scale first: a geometrically perfect part at the wrong size is scrap.
    scale_verified = target_height_mm is not None
    checks.append(
        _check(
            "scale_verified",
            scale_verified or allow_unverified_scale,
            {"height_supplied": scale_verified, "override": bool(allow_unverified_scale)},
            {"height_supplied": True},
        )
    )

    components = component_count(result)
    checks.append(_check("single_component", components == 1, components, 1))

    checks.append(_check("watertight", result.is_watertight, bool(result.is_watertight), True))

    non_manifold = non_manifold_edge_count(result)
    checks.append(_check("no_non_manifold_edges", non_manifold == 0, non_manifold, 0))

    base_volume = float(abs(base.volume))
    result_volume = float(abs(result.volume))
    volume_delta = result_volume - base_volume
    minimum_delta = max(1e-6, base_volume * 1e-6)
    checks.append(
        _check(
            "volume_exceeds_base",
            volume_delta > minimum_delta,
            {"result_mm3": result_volume, "base_mm3": base_volume, "delta_mm3": volume_delta},
            {"delta_greater_than_mm3": minimum_delta},
        )
    )

    pocket_tolerance = comparison_tolerance_mm(pocket_before)
    try:
        pocket_after = detect_pocket(
            result,
            protected_wall_mm=pocket_before.protected_wall_mm,
            # The pocket cannot have grown; bound the search so grafted body
            # geometry at the same radius cannot masquerade as bore depth.
            max_depth_mm=pocket_before.depth_mm * 1.5 + 1.0,
        )
        differences = pocket_differences(pocket_before, pocket_after)
        pocket_passed = all(value <= pocket_tolerance for value in differences.values())
        pocket_measured: Any = dict(differences)
        pocket_measured["threaded"] = pocket_before.is_threaded
    except PocketDetectionError as exc:
        pocket_passed = False
        pocket_measured = {"detection_error": str(exc)}
    checks.append(
        _check(
            "pocket_intact",
            pocket_passed,
            pocket_measured,
            {"max_difference_mm": pocket_tolerance, "threaded": pocket_before.is_threaded},
        )
    )

    # `--height` is the measured height of the *scanned object*. The finished
    # graft is taller by whatever the base contributes, so the two must not be
    # compared directly — doing so failed a correct graft by exactly the base
    # height. The caller supplies the expected total.
    expected_total = expected_total_height_mm
    if expected_total is None and target_height_mm is not None:
        expected_total = target_height_mm
    if expected_total is not None:
        measured_height = float(result.extents[2])
        tolerance = float(expected_total * 0.05)
        checks.append(
            _check(
                "height_within_tolerance",
                abs(measured_height - expected_total) <= tolerance,
                measured_height,
                {
                    "target_mm": float(expected_total),
                    "tolerance_mm": tolerance,
                    "scan_height_mm": float(target_height_mm) if target_height_mm else None,
                },
            )
        )
    return checks


def first_failure(checks: list[dict[str, Any]]) -> tuple[str, str] | None:
    for check in checks:
        if not check["pass"]:
            name = str(check["name"])
            return name, LIKELY_CAUSES[name]
    return None
