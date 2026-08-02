"""Tests for src/core/qr.py and the qr_plaque native mesh path."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from src.core.litho_mesh import build_litho_mesh
from src.core.qr import make_qr_png


def test_qr_png_is_square_grayscale(tmp_path: Path) -> None:
    png = tmp_path / "qr.png"
    w, h = make_qr_png("https://example.com", png)
    img = Image.open(png)
    assert img.mode == "L"
    assert (w, h) == img.size
    assert w == h, "QR image must be square"


def test_qr_modules_are_bright(tmp_path: Path) -> None:
    """Dark QR modules must be encoded as 255 (raised) on 0 background."""
    png = tmp_path / "qr.png"
    make_qr_png("test", png)
    arr = np.array(Image.open(png))
    values = set(np.unique(arr))
    assert values <= {0, 255}, f"unexpected gray values: {values}"
    assert 255 in values and 0 in values
    # corners are quiet zone → background (0)
    assert arr[0, 0] == 0


def test_qr_quiet_zone_present(tmp_path: Path) -> None:
    """A border of quiet-zone modules must surround the code."""
    png = tmp_path / "qr.png"
    make_qr_png("test", png, box_size=10, border=3)
    arr = np.array(Image.open(png))
    edge = 3 * 10  # border modules × box_size
    assert arr[:edge, :].max() == 0
    assert arr[:, :edge].max() == 0


def test_qr_plaque_mesh(tmp_path: Path) -> None:
    """QR heightmap through the native mesher: watertight, right size/height."""
    png = tmp_path / "qr.png"
    make_qr_png("https://example.com", png)
    params = {"plate_w": 80.0, "plate_h": 80.0, "corner_r": 3.0,
              "frame_width": 3.0, "base_height": 3.0,
              "min_thickness": 0.01, "max_thickness": 0.6}
    mesh = build_litho_mesh(png, "roundrect", params)
    assert mesh.is_watertight
    ext = mesh.bounds[1] - mesh.bounds[0]
    assert ext[0] == pytest.approx(80.0, abs=1.0)
    assert ext[1] == pytest.approx(80.0, abs=1.0)
    # top of modules = base + max relief
    assert mesh.bounds[1][2] == pytest.approx(3.6, abs=0.05)


def test_qr_decodes_after_roundtrip(tmp_path: Path) -> None:
    """The heightmap must stay machine-readable (guards module mapping)."""
    cv2 = pytest.importorskip("cv2")
    png = tmp_path / "qr.png"
    make_qr_png("https://example.com", png)
    arr = 255 - np.array(Image.open(png))  # decoder wants dark modules
    data, _, _ = cv2.QRCodeDetector().detectAndDecode(arr)
    assert data == "https://example.com"
