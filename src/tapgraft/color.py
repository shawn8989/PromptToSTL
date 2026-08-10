"""Colour preservation: texture -> vertex colours -> 3MF.

Object Capture produces a *textured* USDZ. The STL path discards that colour
because STL cannot carry it at all. This module keeps the colour by baking the
texture into per-vertex colours and writing a format that can hold them.

Expectation setting: a photographic texture is not directly printable. An AMS
prints a handful of filaments, so colour must be quantised to that many before
it means anything on a printer. `quantize_colors` does that; the result is a
good starting point for painting in a slicer, not a finished colour print.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import trimesh

# Verified by round-trip on 2026-08-10: these three write vertex colours and
# read them back intact.
COLOR_FORMATS = {"ply", "glb", "obj"}

# trimesh's 3MF exporter emits geometry only — no <color> and no
# <basematerials> — so a "coloured" 3MF written through it silently loses
# every colour. Carrying colour in 3MF needs the materials extension written
# by hand. Until that exists, refuse rather than hand back a grey model.
COLOR_FORMATS_UNSUPPORTED = {
    "3mf": (
        "trimesh's 3MF exporter does not write vertex colours, so the colour "
        "would be silently lost. Use .obj for Bambu Studio, or .ply/.glb for "
        "general tools"
    ),
    "stl": "STL cannot carry colour by specification",
}


class ColorError(ValueError):
    """Raised when colour cannot be recovered from a source model."""


def load_colored(path: str | Path) -> trimesh.Trimesh:
    """Load a model and bake any texture down to per-vertex colours.

    STL inputs have no colour and come back untouched.
    """
    source = Path(path)
    if not source.is_file():
        raise ColorError(f"input file does not exist: {source}")
    loaded = trimesh.load(source, force="mesh", process=False)
    if isinstance(loaded, trimesh.Scene):
        if not loaded.geometry:
            raise ColorError(f"input contains no geometry: {source}")
        loaded = trimesh.util.concatenate(tuple(loaded.geometry.values()))
    if not isinstance(loaded, trimesh.Trimesh):
        raise ColorError(f"input is not a triangle mesh: {source}")

    visual = getattr(loaded, "visual", None)
    if isinstance(visual, trimesh.visual.TextureVisuals):
        # to_color() samples the texture image at each vertex's UV.
        try:
            loaded.visual = visual.to_color()
        except Exception as exc:  # texture missing or unreadable
            raise ColorError(f"could not bake texture to vertex colours: {exc}") from exc
    return loaded


def _unique_color_count(mesh: trimesh.Trimesh) -> int:
    visual = getattr(mesh, "visual", None)
    if not isinstance(visual, trimesh.visual.ColorVisuals):
        return 0
    colors = getattr(visual, "vertex_colors", None)
    if colors is None or len(colors) == 0:
        return 0
    return len(np.unique(np.asarray(colors)[:, :3], axis=0))


def has_color(mesh: trimesh.Trimesh) -> bool:
    """True when the mesh carries *varied* colour.

    trimesh assigns a default grey to every mesh, so "has vertex_colors" alone
    proves nothing. More than one distinct colour means real data — either a
    baked texture or a deliberate multi-colour assignment.
    """
    return _unique_color_count(mesh) > 1


def quantize_colors(mesh: trimesh.Trimesh, filament_count: int) -> trimesh.Trimesh:
    """Reduce vertex colours to `filament_count` clusters.

    A printer loads a fixed number of filaments, so a photographic texture has
    to collapse to that many before it can be printed. Uses k-means over RGB.
    """
    if filament_count < 1:
        raise ColorError("filament_count must be at least 1")
    if not has_color(mesh):
        raise ColorError("mesh has no vertex colours to quantise")

    from scipy.cluster.vq import kmeans2

    rgb = np.asarray(mesh.visual.vertex_colors)[:, :3].astype(float)
    unique = np.unique(rgb, axis=0)
    k = int(min(filament_count, len(unique)))
    centroids, labels = kmeans2(rgb, k, minit="++", seed=0)
    quantised = np.clip(centroids[labels], 0, 255).astype(np.uint8)
    alpha = np.full((len(quantised), 1), 255, dtype=np.uint8)

    out = mesh.copy()
    out.visual = trimesh.visual.ColorVisuals(mesh=out, vertex_colors=np.hstack([quantised, alpha]))
    return out


def apply_flat_color(mesh: trimesh.Trimesh, rgb: tuple[int, int, int]) -> trimesh.Trimesh:
    """Paint a mesh one solid colour — used to distinguish the base from the scan."""
    out = mesh.copy()
    colors = np.tile(np.array([*rgb, 255], dtype=np.uint8), (len(out.vertices), 1))
    out.visual = trimesh.visual.ColorVisuals(mesh=out, vertex_colors=colors)
    return out


def export_colored(mesh: trimesh.Trimesh, path: str | Path) -> Path:
    """Write a format that genuinely preserves vertex colours."""
    destination = Path(path)
    suffix = destination.suffix.lower().lstrip(".")
    if suffix in COLOR_FORMATS_UNSUPPORTED:
        raise ColorError(f"'{suffix}' cannot be used: {COLOR_FORMATS_UNSUPPORTED[suffix]}")
    if suffix not in COLOR_FORMATS:
        raise ColorError(f"'{suffix}' is not a known colour format; use one of {sorted(COLOR_FORMATS)}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(destination)
    return destination


def color_report(mesh: trimesh.Trimesh) -> dict[str, Any]:
    """Colour facts for the JSON report.

    `unique_colors` is always the true count — a deliberately flat-coloured
    base reports 1, not 0 — while `has_color` stays the "is this varied
    colour" signal.
    """
    count = _unique_color_count(mesh)
    report: dict[str, Any] = {"has_color": count > 1, "unique_colors": count}
    if count:
        rgb = np.asarray(mesh.visual.vertex_colors)[:, :3]
        report["mean_rgb"] = [int(v) for v in rgb.mean(axis=0)]
    return report
