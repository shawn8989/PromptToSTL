"""Mesh loading, reporting, and output helpers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import trimesh


class InputError(ValueError):
    """Raised when an input cannot provide a usable triangle mesh."""


def load_mesh(path: str | Path) -> trimesh.Trimesh:
    """Load one STL mesh without changing its millimetre-scale coordinates."""
    source = Path(path)
    if not source.is_file():
        raise InputError(f"input file does not exist: {source}")
    try:
        loaded = trimesh.load(source, force="mesh", process=True)
    except Exception as exc:
        raise InputError(f"could not read {source}: {exc}") from exc
    if isinstance(loaded, trimesh.Scene):
        if not loaded.geometry:
            raise InputError(f"input contains no geometry: {source}")
        loaded = trimesh.util.concatenate(tuple(loaded.geometry.values()))
    if not isinstance(loaded, trimesh.Trimesh) or len(loaded.faces) == 0:
        raise InputError(f"input contains no triangles: {source}")
    if not np.isfinite(loaded.vertices).all():
        raise InputError(f"input contains non-finite vertex coordinates: {source}")
    return loaded


def component_count(mesh: trimesh.Trimesh) -> int:
    """Return the number of face-connected components."""
    return len(mesh.split(only_watertight=False))


def mesh_report(mesh: trimesh.Trimesh, path: str | Path) -> dict[str, Any]:
    """Return the stable input/output measurements used by the JSON contract."""
    return {
        "path": str(Path(path)),
        "vertices": len(mesh.vertices),
        "faces": len(mesh.faces),
        "bbox_mm": [float(value) for value in mesh.extents],
        "volume_mm3": float(abs(mesh.volume)),
        "watertight": bool(mesh.is_watertight),
        "components": component_count(mesh),
    }


def write_mesh(mesh: trimesh.Trimesh, path: str | Path) -> Path:
    """Write an STL, creating only its immediate parent directory."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(destination, file_type="stl")
    return destination


def write_json(report: dict[str, Any], path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return destination


def failed_output_path(path: str | Path) -> Path:
    """Map ``part.stl`` to the unambiguous ``part.FAILED.stl`` form."""
    destination = Path(path)
    return destination.with_name(f"{destination.stem}.FAILED{destination.suffix or '.stl'}")
