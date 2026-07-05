"""Tests for src/core/litho_mesh.py — native lithophane mesh generation."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from src.core.litho_mesh import build_litho_mesh

BASE = 1.2
MIN_T = 0.8
MAX_T = 3.0
FRAME = 4.0


def _gradient_png(path: Path, w: int = 120, h: int = 100) -> None:
    """Horizontal gradient 0→255 so the full height range is exercised."""
    arr = np.tile(np.linspace(0, 255, w, dtype=np.uint8), (h, 1))
    Image.fromarray(arr, mode="L").save(path)


def _params(shape: str) -> dict:
    p = {"min_thickness": MIN_T, "max_thickness": MAX_T,
         "frame_width": FRAME, "base_height": BASE}
    if shape == "heart":
        p.update(heart_w=80.0, heart_h=80.0)
    elif shape == "circle":
        p.update(diameter=80.0)
    else:
        p.update(plate_w=100.0, plate_h=75.0, corner_r=4.0)
    return p


@pytest.fixture()
def heightmap(tmp_path: Path) -> Path:
    png = tmp_path / "hm.png"
    _gradient_png(png)
    return png


@pytest.mark.parametrize("shape", ["heart", "circle", "roundrect"])
def test_watertight(heightmap: Path, shape: str) -> None:
    mesh = build_litho_mesh(heightmap, shape, _params(shape))
    assert mesh.is_watertight, f"{shape} mesh is not watertight"
    assert mesh.is_winding_consistent


@pytest.mark.parametrize("shape", ["heart", "circle", "roundrect"])
def test_positive_volume(heightmap: Path, shape: str) -> None:
    mesh = build_litho_mesh(heightmap, shape, _params(shape))
    assert mesh.volume > 0, f"{shape} volume {mesh.volume} — inverted normals?"


def test_bounds_roundrect(heightmap: Path) -> None:
    mesh = build_litho_mesh(heightmap, "roundrect", _params("roundrect"))
    ext = mesh.bounds[1] - mesh.bounds[0]
    assert ext[0] == pytest.approx(100.0, abs=1.5)
    assert ext[1] == pytest.approx(75.0, abs=1.5)


def test_z_range(heightmap: Path) -> None:
    """Z spans 0 → base + max_thickness (frame guarantees the top)."""
    mesh = build_litho_mesh(heightmap, "roundrect", _params("roundrect"))
    assert mesh.bounds[0][2] == pytest.approx(0.0, abs=1e-6)
    assert mesh.bounds[1][2] == pytest.approx(BASE + MAX_T, abs=0.05)


def test_interior_height_follows_pixels(tmp_path: Path) -> None:
    """A mid-gray image puts the interior surface near base+min+0.5*(max−min)."""
    png = tmp_path / "gray.png"
    Image.new("L", (100, 100), 128).save(png)
    mesh = build_litho_mesh(png, "roundrect", _params("roundrect"))
    expected = BASE + MIN_T + (128 / 255.0) * (MAX_T - MIN_T)
    # sample vertices well inside the interior (away from the frame)
    v = mesh.vertices
    interior = v[(np.abs(v[:, 0]) < 20) & (np.abs(v[:, 1]) < 15) & (v[:, 2] > 0.1)]
    assert len(interior) > 0
    assert np.median(interior[:, 2]) == pytest.approx(expected, abs=0.1)


def test_circle_has_no_corners(heightmap: Path) -> None:
    """No vertex may lie outside the circle radius (plus one grid cell)."""
    params = _params("circle")
    mesh = build_litho_mesh(heightmap, "circle", params)
    r = params["diameter"] / 2.0
    radii = np.linalg.norm(mesh.vertices[:, :2], axis=1)
    assert radii.max() <= r + 1.0, f"vertex at radius {radii.max():.2f} > {r}"


def test_frame_too_large_raises(heightmap: Path) -> None:
    params = _params("circle")
    params["frame_width"] = 50.0  # exceeds radius
    with pytest.raises(ValueError):
        build_litho_mesh(heightmap, "circle", params)
