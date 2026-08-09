"""The ordered verification gate for print-ready grafts."""
from __future__ import annotations

from typing import Any

import numpy as np
import trimesh

from .meshio import component_count
from .pocket import (
    PocketDetectionError,
    PocketMeasurements,
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
) -> list[dict[str, Any]]:
    """Run checks in the exact order required by the cross-process contract."""
    checks: list[dict[str, Any]] = []
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

    try:
        pocket_after = detect_pocket(result, protected_wall_mm=pocket_before.protected_wall_mm)
        differences = pocket_differences(pocket_before, pocket_after)
        pocket_passed = all(value <= 0.2 for value in differences.values())
        pocket_measured: Any = differences
    except PocketDetectionError as exc:
        pocket_passed = False
        pocket_measured = {"detection_error": str(exc)}
    checks.append(
        _check(
            "pocket_intact",
            pocket_passed,
            pocket_measured,
            {"max_difference_mm": 0.2},
        )
    )

    if target_height_mm is not None:
        measured_height = float(result.extents[2])
        tolerance = float(target_height_mm * 0.05)
        checks.append(
            _check(
                "height_within_tolerance",
                abs(measured_height - target_height_mm) <= tolerance,
                measured_height,
                {"target_mm": float(target_height_mm), "tolerance_mm": tolerance},
            )
        )
    return checks


def first_failure(checks: list[dict[str, Any]]) -> tuple[str, str] | None:
    for check in checks:
        if not check["pass"]:
            name = str(check["name"])
            return name, LIKELY_CAUSES[name]
    return None
