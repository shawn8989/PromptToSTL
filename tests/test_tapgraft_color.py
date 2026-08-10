"""Colour preservation tests — generated primitives only, no scan assets."""
from __future__ import annotations

import numpy as np
import pytest
import trimesh

from src.tapgraft.color import (
    COLOR_FORMATS,
    COLOR_FORMATS_UNSUPPORTED,
    ColorError,
    apply_flat_color,
    color_report,
    export_colored,
    has_color,
    quantize_colors,
)


def _rainbow_sphere() -> trimesh.Trimesh:
    """A sphere with a distinct colour per vertex."""
    m = trimesh.creation.icosphere(subdivisions=3, radius=10.0)
    rgb = ((m.vertices - m.vertices.min(axis=0))
           / np.ptp(m.vertices, axis=0) * 255).astype(np.uint8)
    alpha = np.full((len(rgb), 1), 255, dtype=np.uint8)
    m.visual = trimesh.visual.ColorVisuals(mesh=m, vertex_colors=np.hstack([rgb, alpha]))
    return m


def test_has_color_rejects_a_single_flat_colour():
    plain = trimesh.creation.icosphere(subdivisions=2, radius=5.0)
    assert not has_color(plain)
    assert has_color(_rainbow_sphere())


@pytest.mark.parametrize("ext", sorted(COLOR_FORMATS))
def test_colour_survives_round_trip(tmp_path, ext):
    """Every advertised colour format must actually read its colour back."""
    m = _rainbow_sphere()
    before = color_report(m)

    path = export_colored(m, tmp_path / f"colored.{ext}")
    back = trimesh.load(path, force="mesh", process=False)
    if isinstance(back, trimesh.Scene):
        back = trimesh.util.concatenate(tuple(back.geometry.values()))

    assert has_color(back), f"{ext} lost the colour"
    assert color_report(back)["unique_colors"] == before["unique_colors"]


@pytest.mark.parametrize("ext", sorted(COLOR_FORMATS_UNSUPPORTED))
def test_formats_that_lose_colour_are_refused(tmp_path, ext):
    """Refuse rather than silently hand back a grey model."""
    with pytest.raises(ColorError) as exc:
        export_colored(_rainbow_sphere(), tmp_path / f"bad.{ext}")
    assert ext in str(exc.value)


def test_quantize_reduces_to_filament_count():
    m = _rainbow_sphere()
    assert color_report(m)["unique_colors"] > 50

    q = quantize_colors(m, 4)
    assert color_report(q)["unique_colors"] <= 4
    assert len(q.vertices) == len(m.vertices)


def test_quantize_requires_colour():
    with pytest.raises(ColorError):
        quantize_colors(trimesh.creation.icosphere(subdivisions=2), 4)


def test_flat_colour_marks_the_base():
    base = trimesh.creation.cylinder(radius=10, height=28)
    painted = apply_flat_color(base, (200, 30, 30))
    assert color_report(painted)["unique_colors"] == 1
    assert list(painted.visual.vertex_colors[0][:3]) == [200, 30, 30]
