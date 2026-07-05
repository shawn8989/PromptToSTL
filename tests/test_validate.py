"""Tests for src/core/validate.py."""
from __future__ import annotations

import struct
from pathlib import Path

from src.core.validate import validate_stl


def _write_binary_stl(path: Path, triangles: list[tuple]) -> None:
    """Write a minimal valid binary STL."""
    with open(path, "wb") as f:
        f.write(b"\x00" * 80)  # header
        f.write(struct.pack("<I", len(triangles)))
        for normal, v0, v1, v2 in triangles:
            for coord in normal + v0 + v1 + v2:
                f.write(struct.pack("<f", coord))
            f.write(struct.pack("<H", 0))  # attribute


def _cube_triangles():
    """12 triangles forming a unit cube, repeated to exceed the 1000-byte size floor."""
    faces = [
        ((0,0,-1),(0,0,0),(1,0,0),(1,1,0)),
        ((0,0,-1),(0,0,0),(1,1,0),(0,1,0)),
        ((0,0,1),(0,0,1),(1,1,1),(1,0,1)),
        ((0,0,1),(0,0,1),(0,1,1),(1,1,1)),
        ((0,-1,0),(0,0,0),(0,0,1),(1,0,1)),
        ((0,-1,0),(0,0,0),(1,0,1),(1,0,0)),
        ((0,1,0),(0,1,0),(1,1,0),(1,1,1)),
        ((0,1,0),(0,1,0),(1,1,1),(0,1,1)),
        ((-1,0,0),(0,0,0),(0,1,0),(0,1,1)),
        ((-1,0,0),(0,0,0),(0,1,1),(0,0,1)),
        ((1,0,0),(1,0,0),(1,0,1),(1,1,1)),
        ((1,0,0),(1,0,0),(1,1,1),(1,1,0)),
    ]
    # Repeat enough times so total file size > 1000 bytes
    # Each tri = 50 bytes, header+count = 84 bytes, so need ≥19 tris
    return [f for f in faces for _ in range(3)]  # 36 tris × 50B + 84B = 1884B


def test_missing_file_returns_error() -> None:
    result = validate_stl(Path("/nonexistent/path/model.stl"))
    assert result["ok"] is False
    assert "error" in result


def test_too_small_file_returns_error(tmp_path: Path) -> None:
    tiny = tmp_path / "tiny.stl"
    tiny.write_bytes(b"solid\nendsolid\n")
    result = validate_stl(tiny)
    assert result["ok"] is False


def test_corrupt_bytes_returns_error(tmp_path: Path) -> None:
    corrupt = tmp_path / "corrupt.stl"
    corrupt.write_bytes(b"\xff" * 2000)
    result = validate_stl(corrupt)
    assert result["ok"] is False


def test_valid_stl_returns_ok(tmp_path: Path) -> None:
    stl = tmp_path / "cube.stl"
    _write_binary_stl(stl, _cube_triangles())
    result = validate_stl(stl)
    assert result["ok"] is True
    assert "faces" in result
    assert result["faces"] > 0
    assert "bounds_min" in result
    assert "bounds_max" in result
