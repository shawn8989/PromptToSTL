"""PCA orientation and explicit millimetre-scale verification."""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import trimesh
from scipy.linalg import eigh


@dataclass
class OrientationResult:
    mesh: trimesh.Trimesh
    flipped: bool
    narrow_end: str
    spread_ratio: float
    lower_spread_mm: float
    upper_spread_mm: float

    def report(self) -> dict:
        data = asdict(self)
        data.pop("mesh")
        return data


@dataclass
class ScaleResult:
    mesh: trimesh.Trimesh
    applied_factor: float
    target_height_mm: float | None
    warning: str | None

    def report(self) -> dict:
        data = asdict(self)
        data.pop("mesh")
        return data


def _half_spreads(vertices: np.ndarray) -> tuple[float, float]:
    median_z = float(np.median(vertices[:, 2]))
    lower = vertices[vertices[:, 2] <= median_z]
    upper = vertices[vertices[:, 2] > median_z]

    def spread(points: np.ndarray) -> float:
        center = points[:, :2].mean(axis=0)
        return float(np.sqrt(np.mean(np.sum((points[:, :2] - center) ** 2, axis=1))))

    return spread(lower), spread(upper)


def orient_scan(mesh: trimesh.Trimesh, flip: bool = False) -> OrientationResult:
    """Align the dominant PCA axis to Z and put the narrow physical end at -Z."""
    result = mesh.copy()
    centered = result.vertices - result.vertices.mean(axis=0)
    covariance = np.cov(centered, rowvar=False)
    _, eigenvectors = eigh(covariance)
    basis = eigenvectors[:, [0, 1, 2]]
    if np.linalg.det(basis) < 0.0:
        basis[:, 0] *= -1.0
    result.vertices = centered @ basis

    lower_spread, upper_spread = _half_spreads(result.vertices)
    if lower_spread > upper_spread:
        result.vertices[:, [1, 2]] *= -1.0
        lower_spread, upper_spread = _half_spreads(result.vertices)

    if flip:
        result.vertices[:, [1, 2]] *= -1.0
        lower_spread, upper_spread = _half_spreads(result.vertices)

    denominator = max(min(lower_spread, upper_spread), 1e-12)
    ratio = max(lower_spread, upper_spread) / denominator
    return OrientationResult(
        mesh=result,
        flipped=flip,
        narrow_end="+Z" if flip else "-Z",
        spread_ratio=float(ratio),
        lower_spread_mm=lower_spread,
        upper_spread_mm=upper_spread,
    )


def scale_to_height(mesh: trimesh.Trimesh, target_height_mm: float | None) -> ScaleResult:
    """Uniformly scale only when an explicit measured height is supplied."""
    result = mesh.copy()
    if target_height_mm is None:
        return ScaleResult(result, 1.0, None, "scale unverified: --height was not supplied")
    if target_height_mm <= 0.0:
        raise ValueError("--height must be greater than zero")
    current_height = float(result.extents[2])
    if current_height <= 0.0:
        raise ValueError("scan has zero Z extent after orientation")
    factor = float(target_height_mm / current_height)
    result.apply_scale(factor)
    warning = None
    if factor < 0.5 or factor > 2.0:
        warning = (
            f"scale factor {factor:.4f} is outside 0.5-2.0; "
            "the STL may use different units or --height may be incorrect"
        )
    return ScaleResult(result, factor, float(target_height_mm), warning)

