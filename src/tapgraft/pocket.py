"""Detection and comparison of a base's ferrule pocket."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

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
    # Threaded bores need more than a single fitted diameter. A circle fitted
    # to one slice of a helix moves with the thread phase, which produced
    # false `pocket_intact` failures on an undamaged pocket.
    minor_diameter_mm: float = 0.0
    major_diameter_mm: float = 0.0
    mean_diameter_mm: float = 0.0
    is_threaded: bool = False
    # Phase-independent centre: the XY centroid of the whole bore wall.
    robust_center_mm: list[float] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)

    @property
    def comparison_center(self) -> list[float]:
        return self.robust_center_mm or self.center_mm

    @property
    def comparison_diameter_mm(self) -> float:
        """The diameter to compare across a graft.

        `mean_diameter_mm` averages the whole bore wall, so it does not move
        with thread phase. Falls back to the fitted diameter for older data.
        """
        return self.mean_diameter_mm or self.diameter_mm


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


def detect_pocket(
    mesh: trimesh.Trimesh,
    protected_wall_mm: float = 4.0,
    max_depth_mm: float | None = None,
) -> PocketMeasurements:
    """Measure the innermost circular loop on either Z mounting face.

    `max_depth_mm` bounds how far inward the bore is searched. Pass it when
    re-measuring a grafted result, where geometry unrelated to the pocket may
    share its radius higher up the part.
    """
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
        along = wall_points[:, 2] - face_z
    else:
        along = face_z - wall_points[:, 2]
    along = along[along >= -1e-6]
    # When re-measuring a finished graft, unrelated geometry can sit at the
    # bore's radius further up the part — that read as a 181 mm deep pocket.
    # Callers who already know roughly how deep it should be clip the search.
    if max_depth_mm is not None:
        along = along[along <= float(max_depth_mm)]
    if len(along) == 0:
        raise PocketDetectionError("pocket wall vertices do not run inward from the mounting face")
    depth = float(along.max())
    if depth <= 0.0:
        raise PocketDetectionError("pocket depth is zero or points outside the base")

    # Characterise the whole bore wall, not one slice. On a threaded bore the
    # radius sweeps between minor and major with the helix, so single-slice
    # measurements move by ~0.5 mm depending on where they land.
    if mounting_face == "-Z":
        in_depth = (mesh.vertices[:, 2] >= face_z) & (mesh.vertices[:, 2] <= face_z + depth)
    else:
        in_depth = (mesh.vertices[:, 2] <= face_z) & (mesh.vertices[:, 2] >= face_z - depth)
    wall_band = in_depth & (vertex_radii <= radius * 1.6)
    band_points = mesh.vertices[wall_band]

    if len(band_points) >= 12:
        band_radii = np.linalg.norm(band_points[:, :2] - center, axis=1)
        minor_d = float(np.percentile(band_radii, 5) * 2.0)
        major_d = float(np.percentile(band_radii, 95) * 2.0)
        mean_d = float(band_radii.mean() * 2.0)
        robust_center = [
            float(band_points[:, 0].mean()),
            float(band_points[:, 1].mean()),
            float(face_z),
        ]
    else:
        minor_d = major_d = mean_d = radius * 2.0
        robust_center = [float(center[0]), float(center[1]), float(face_z)]

    # A smooth bore varies only by faceting; a thread swings far more.
    threaded = (major_d - minor_d) > max(0.30, mean_d * 0.08)

    return PocketMeasurements(
        diameter_mm=radius * 2.0,
        depth_mm=depth,
        center_mm=[float(center[0]), float(center[1]), float(face_z)],
        protected_wall_mm=float(protected_wall_mm),
        mounting_face=mounting_face,
        minor_diameter_mm=minor_d,
        major_diameter_mm=major_d,
        mean_diameter_mm=mean_d,
        is_threaded=bool(threaded),
        robust_center_mm=robust_center,
    )


def pocket_differences(before: PocketMeasurements, after: PocketMeasurements) -> dict[str, float]:
    """Compare two measurements using phase-independent statistics.

    Fitted diameter and fitted centre both move with thread phase, so they
    cannot be compared across a graft on a threaded bore without producing
    false failures. Mean bore diameter and the wall centroid do not move.
    """
    return {
        "diameter_mm": abs(after.comparison_diameter_mm - before.comparison_diameter_mm),
        "depth_mm": abs(after.depth_mm - before.depth_mm),
        "position_mm": float(
            np.linalg.norm(
                np.asarray(after.comparison_center, dtype=float)
                - np.asarray(before.comparison_center, dtype=float)
            )
        ),
    }


def comparison_tolerance_mm(pocket: PocketMeasurements, base_tolerance_mm: float = 0.2) -> float:
    """Tolerance for `pocket_intact`.

    Smooth pockets keep the strict tolerance. Threaded bores get a small
    allowance proportional to the thread depth, because even a phase-independent
    mean is resampled after the boolean re-triangulates the wall.
    """
    if not pocket.is_threaded:
        return base_tolerance_mm
    thread_depth = max(0.0, (pocket.major_diameter_mm - pocket.minor_diameter_mm) / 2.0)
    return max(base_tolerance_mm, thread_depth * 0.25)


def protected_extents(pocket: PocketMeasurements) -> dict[str, list[float]]:
    # Protect against the widest part of the bore: on a thread that is the
    # major diameter, so crests are covered rather than only the mean.
    widest = max(pocket.diameter_mm, pocket.major_diameter_mm)
    radius = widest / 2.0 + pocket.protected_wall_mm
    x, y, z = pocket.comparison_center
    direction = 1.0 if pocket.mounting_face == "-Z" else -1.0
    far_z = z + direction * (pocket.depth_mm + pocket.protected_wall_mm)
    return {
        "min_mm": [x - radius, y - radius, min(z - pocket.protected_wall_mm, far_z)],
        "max_mm": [x + radius, y + radius, max(z + pocket.protected_wall_mm, far_z)],
    }

