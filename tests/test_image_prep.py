"""Tests for src/core/image_prep.py — all use synthetic PIL images, no file I/O."""
from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

from src.core.image_prep import prepare_lithophane_image


def _make_png(width: int, height: int, color: int = 128) -> bytes:
    """Return PNG bytes for a solid-color grayscale image."""
    img = Image.new("L", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_rgb_png(width: int, height: int) -> bytes:
    """Return PNG bytes for a gradient RGB image."""
    img = Image.new("RGB", (width, height))
    for x in range(width):
        for y in range(height):
            img.putpixel((x, y), (x * 255 // width, y * 255 // height, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# grayscale
# ---------------------------------------------------------------------------

def test_grayscale_output(tmp_path: Path) -> None:
    """Output PNG must be single-channel (mode L)."""
    src = _make_rgb_png(64, 64)
    out = tmp_path / "out.png"
    prepare_lithophane_image(src, out, invert=False)
    result = Image.open(out)
    assert result.mode == "L", f"Expected L, got {result.mode}"


# ---------------------------------------------------------------------------
# invert
# ---------------------------------------------------------------------------

def test_invert_flips_pixel_values(tmp_path: Path) -> None:
    """A pure-white image (255) becomes pure-black (0) after inversion."""
    src = _make_png(32, 32, color=200)
    out_on = tmp_path / "inv.png"
    out_off = tmp_path / "noinv.png"
    prepare_lithophane_image(src, out_on, invert=True)
    prepare_lithophane_image(src, out_off, invert=False)

    pixel_on = Image.open(out_on).getpixel((0, 0))
    pixel_off = Image.open(out_off).getpixel((0, 0))
    # inverted value should be approximately 255 - original
    assert abs(pixel_on - (255 - pixel_off)) <= 2, (
        f"Expected ~{255 - pixel_off}, got {pixel_on}"
    )


def test_invert_off_preserves_brightness(tmp_path: Path) -> None:
    """With invert=False a bright image stays bright (> 200)."""
    src = _make_png(32, 32, color=220)
    out = tmp_path / "out.png"
    prepare_lithophane_image(src, out, invert=False)
    pixel = Image.open(out).getpixel((0, 0))
    assert pixel > 200, f"Expected bright pixel, got {pixel}"


# ---------------------------------------------------------------------------
# resize
# ---------------------------------------------------------------------------

def test_resize_long_edge_respected(tmp_path: Path) -> None:
    """Longest edge of the output must be ≤ max_px."""
    src = _make_png(2048, 512, color=128)
    out = tmp_path / "out.png"
    prepare_lithophane_image(src, out, max_px=512, invert=False)
    w, h = Image.open(out).size
    assert max(w, h) <= 512, f"Long edge {max(w, h)} exceeds 512"


def test_resize_preserves_aspect_ratio(tmp_path: Path) -> None:
    """Aspect ratio must be preserved within ±2% after resize."""
    src = _make_png(800, 400, color=128)  # 2:1
    out = tmp_path / "out.png"
    prepare_lithophane_image(src, out, max_px=300, invert=False)
    w, h = Image.open(out).size
    ratio = w / h
    assert abs(ratio - 2.0) < 0.05, f"Aspect ratio changed: {ratio:.3f}"


def test_small_image_not_upscaled(tmp_path: Path) -> None:
    """Images smaller than max_px must not be enlarged."""
    src = _make_png(100, 80, color=128)
    out = tmp_path / "out.png"
    prepare_lithophane_image(src, out, max_px=1024, invert=False)
    w, h = Image.open(out).size
    assert (w, h) == (100, 80), f"Small image was resized to {w}×{h}"


def test_returns_pixel_dims(tmp_path: Path) -> None:
    """Return value must match the saved PNG dimensions."""
    src = _make_png(300, 200, color=100)
    out = tmp_path / "out.png"
    returned_w, returned_h = prepare_lithophane_image(src, out, max_px=1024, invert=False)
    saved_w, saved_h = Image.open(out).size
    assert (returned_w, returned_h) == (saved_w, saved_h)


# ---------------------------------------------------------------------------
# gamma
# ---------------------------------------------------------------------------

def test_gamma_gt1_darkens_midtones(tmp_path: Path) -> None:
    """Gamma > 1 should darken a midtone gray (128 → less than 128)."""
    src = _make_png(32, 32, color=128)
    out = tmp_path / "out.png"
    prepare_lithophane_image(src, out, gamma=2.2, invert=False)
    pixel = Image.open(out).getpixel((0, 0))
    assert pixel < 128, f"Gamma>1 should darken midtone, got {pixel}"


def test_gamma_lt1_brightens_midtones(tmp_path: Path) -> None:
    """Gamma < 1 should brighten a midtone gray (128 → greater than 128)."""
    src = _make_png(32, 32, color=128)
    out = tmp_path / "out.png"
    prepare_lithophane_image(src, out, gamma=0.45, invert=False)
    pixel = Image.open(out).getpixel((0, 0))
    assert pixel > 128, f"Gamma<1 should brighten midtone, got {pixel}"


def test_gamma_1_is_identity(tmp_path: Path) -> None:
    """Gamma = 1.0 must not change pixel values."""
    src = _make_png(32, 32, color=160)
    out = tmp_path / "out.png"
    prepare_lithophane_image(src, out, gamma=1.0, invert=False)
    pixel = Image.open(out).getpixel((0, 0))
    assert pixel == 160, f"Gamma=1 changed pixel to {pixel}"
