"""Detection and comparison of a base's ferrule pocket."""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import trimesh


class PocketDetectionError(ValueError):
    """Raised when a mounting-face pocket cannot be measured reliably."""


@dataclass
class PocketMeasurements:
    diameter_mm: float
    depth_mm: float
    center_mm: list[float]
    protected_wall_mm: float
    mounting_face: str

    def as_dict(self) -> dict:
        return asdict(self)


def _fit_circle(points: np.ndarray) -> tuple[np.ndarray, float]:
    """Fit a circle by linear least squares."""
    xy = np.asarray(points, dtype=float)[:, :2]
    matrix = np.column_stack((2.0 * xy[:, 0], 2.0 * xy[:, 1], np.ones(len(xy))))
    rhs = np.sum(xy**2, axis=1)
    solution, *_ = np.linalg.lstsq(matrix, rhs, rcond=None)
    center = solution[:2]
    radius_squared = float(solution[2] + np.dot(center, center))
    if radius_squared <= 0.0:
        raise PocketDetectionError("circle fit produced a non-positive radius")
    return center, float(np.sqrt(radius_squared))


def _radius_clusters(radii: np.ndarray, tolerance: float) -> list[np.ndarray]:
    order = np.argsort(radii)
    clusters: list[list[int]] = []
    for point_index in order:
        if not clusters:
            clusters.append([int(point_index)])
            continue
        current = clusters[-1]
        current_radius = float(np.mean(radii[current]))
        if abs(float(radii[point_index]) - current_radius) <= tolerance:
            current.append(int(point_index))
        else:
            clusters.append([int(point_index)])
    return [np.asarray(cluster, dtype=int) for cluster in clusters]


def _face_candidate(mesh: trimesh.Trimesh, face_z: float, label: str) -> tuple | None:
    z_extent = max(float(mesh.extents[2]), 1.0)
    z_tolerance = max(0.02, z_extent * 1e-4)
    face_points = mesh.vertices[np.abs(mesh.vertices[:, 2] - face_z) <= z_tolerance]
    if len(face_points) < 16:
        return None

    bounds_center = mesh.bounds.mean(axis=0)[:2]
    radii = np.linalg.norm(face_points[:, :2] - bounds_center, axis=1)
    radial_tolerance = max(0.03, max(float(mesh.extents[0]), float(mesh.extents[1])) * 1e-3)
    minimum_cluster = max(8, int(len(face_points) * 0.05))
    clusters = [
        cluster
        for cluster in _radius_clusters(radii, radial_tolerance)
        if len(cluster) >= minimum_cluster and float(np.mean(radii[cluster])) > radial_tolerance
    ]
    if len(clusters) < 2:
        return None

    clusters.sort(key=lambda cluster: float(np.mean(radii[cluster])))
    inner_points = face_points[clusters[0]]
    center, radius = _fit_circle(inner_points)
    residual = float(np.sqrt(np.mean((np.linalg.norm(inner_points[:, :2] - center, axis=1) - radius) ** 2)))
    return residual, label, face_z, center, radius


def detect_pocket(mesh: trimesh.Trimesh, protected_wall_mm: float = 4.0) -> PocketMeasurements:
    """Measure the innermost circular loop on either Z mounting face."""
    candidates = [
        candidate
        for candidate in (
            _face_candidate(mesh, float(mesh.bounds[0, 2]), "-Z"),
            _face_candidate(mesh, float(mesh.bounds[1, 2]), "+Z"),
        )
        if candidate is not None
    ]
    if not candidates:
        raise PocketDetectionError(
            "no circular interior loop found on either Z face; check base orientation and pocket geometry"
        )

    _, mounting_face, face_z, center, radius = min(candidates, key=lambda item: item[0])
    vertex_radii = np.linalg.norm(mesh.vertices[:, :2] - center, axis=1)
    radial_tolerance = max(0.15, radius * 0.04)
    wall_points = mesh.vertices[np.abs(vertex_radii - radius) <= radial_tolerance]
    if len(wall_points) < 8:
        raise PocketDetectionError("not enough pocket-wall vertices to determine depth")
    if mounting_face == "-Z":
        depth = float(wall_points[:, 2].max() - face_z)
    else:
        depth = float(face_z - wall_points[:, 2].min())
    if depth <= 0.0:
        raise PocketDetectionError("pocket depth is zero or points outside the base")

    return PocketMeasurements(
        diameter_mm=radius * 2.0,
        depth_mm=depth,
        center_mm=[float(center[0]), float(center[1]), float(face_z)],
        protected_wall_mm=float(protected_wall_mm),
        mounting_face=mounting_face,
    )


def pocket_differences(before: PocketMeasurements, after: PocketMeasurements) -> dict[str, float]:
    return {
        "diameter_mm": abs(after.diameter_mm - before.diameter_mm),
        "depth_mm": abs(after.depth_mm - before.depth_mm),
        "position_mm": float(
            np.linalg.norm(np.asarray(after.center_mm, dtype=float) - np.asarray(before.center_mm, dtype=float))
        ),
    }


def protected_extents(pocket: PocketMeasurements) -> dict[str, list[float]]:
    radius = pocket.diameter_mm / 2.0 + pocket.protected_wall_mm
    x, y, z = pocket.center_mm
    direction = 1.0 if pocket.mounting_face == "-Z" else -1.0
    far_z = z + direction * (pocket.depth_mm + pocket.protected_wall_mm)
    return {
        "min_mm": [x - radius, y - radius, min(z - pocket.protected_wall_mm, far_z)],
        "max_mm": [x + radius, y + radius, max(z + pocket.protected_wall_mm, far_z)],
    }

