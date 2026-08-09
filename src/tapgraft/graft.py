"""Scan trimming, placement, and boolean union."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import trimesh

from .pocket import PocketMeasurements


class BooleanFailure(RuntimeError):
    """Raised after both boolean attempts fail."""


@dataclass
class BooleanResult:
    mesh: trimesh.Trimesh
    engine: str
    fell_back: bool
    diagnostic: str | None

    def report(self) -> dict:
        return {
            "engine": self.engine,
            "fell_back": self.fell_back,
            "diagnostic": self.diagnostic,
        }


def trim_and_place_scan(
    scan: trimesh.Trimesh,
    base: trimesh.Trimesh,
    pocket: PocketMeasurements,
    overlap_mm: float,
) -> trimesh.Trimesh:
    """Flatten the mating end when needed, center it, and sink it into the base."""
    if overlap_mm <= 0.0:
        raise ValueError("--overlap must be greater than zero")
    result = scan.copy()
    minimum_z = float(result.bounds[0, 2])
    flat_tolerance = max(0.02, float(result.extents[2]) * 1e-4)
    points_at_bottom = np.count_nonzero(np.abs(result.vertices[:, 2] - minimum_z) <= flat_tolerance)

    if points_at_bottom < 3:
        trim_z = minimum_z + float(result.extents[2]) * 0.02
        margin = max(float(result.extents.max()), 1.0)
        box_height = float(result.bounds[1, 2] - trim_z + margin)
        clip = trimesh.creation.box(
            extents=[float(result.extents[0] + 2.0 * margin), float(result.extents[1] + 2.0 * margin), box_height]
        )
        clip.apply_translation(
            [
                float(result.bounds[:, 0].mean()),
                float(result.bounds[:, 1].mean()),
                trim_z + box_height / 2.0,
            ]
        )
        result = trimesh.boolean.intersection([result, clip], engine="manifold", check_volume=False)
        if result is None or len(result.faces) == 0:
            raise BooleanFailure("manifold3d could not trim the scan to a flat mating plane")

    scan_center = result.bounds.mean(axis=0)[:2]
    target_xy = np.asarray(pocket.center_mm[:2], dtype=float)
    target_bottom_z = float(base.bounds[1, 2] - overlap_mm)
    result.apply_translation(
        [
            float(target_xy[0] - scan_center[0]),
            float(target_xy[1] - scan_center[1]),
            float(target_bottom_z - result.bounds[0, 2]),
        ]
    )
    return result


def union_meshes(scan: trimesh.Trimesh, base: trimesh.Trimesh) -> BooleanResult:
    """Union with manifold3d first, then ask trimesh for its automatic fallback."""
    primary_error: str | None = None
    try:
        mesh = trimesh.boolean.union([base, scan], engine="manifold", check_volume=False)
        if mesh is None or len(mesh.faces) == 0:
            raise RuntimeError("engine returned an empty result")
        return BooleanResult(mesh=mesh, engine="manifold3d", fell_back=False, diagnostic=None)
    except Exception as exc:  # noqa: BLE001 - third-party engines raise varied exception types
        primary_error = f"manifold3d failed: {type(exc).__name__}: {exc}"

    try:
        mesh = trimesh.boolean.union([base, scan], engine=None, check_volume=False)
        if mesh is None or len(mesh.faces) == 0:
            raise RuntimeError("engine returned an empty result")
        return BooleanResult(mesh=mesh, engine="trimesh", fell_back=True, diagnostic=primary_error)
    except Exception as exc:
        fallback_error = f"trimesh fallback failed: {type(exc).__name__}: {exc}"
        raise BooleanFailure(f"{primary_error}; {fallback_error}") from exc
