"""Tests for PCA alignment, end selection, and explicit scaling."""
from __future__ import annotations

import numpy as np

from src.tapgraft.orient import orient_scan, scale_to_height
from tests.tapgraft_primitives import lumpy_sphere_on_stick


def test_orientation_picks_narrow_end():
    scan = lumpy_sphere_on_stick()
    transform = np.eye(4)
    transform[:3, :3] = np.array(
        [
            [0.0, 0.0, 1.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ]
    )
    scan.apply_transform(transform)

    automatic = orient_scan(scan)
    flipped = orient_scan(scan, flip=True)

    assert automatic.mesh.extents[2] == max(automatic.mesh.extents)
    assert automatic.narrow_end == "-Z"
    assert automatic.lower_spread_mm < automatic.upper_spread_mm
    assert automatic.spread_ratio > 1.2

    assert flipped.narrow_end == "+Z"
    assert flipped.lower_spread_mm > flipped.upper_spread_mm


def test_scale_warning_outside_bounds():
    scan = orient_scan(lumpy_sphere_on_stick()).mesh
    result = scale_to_height(scan, target_height_mm=float(scan.extents[2]) * 3.0)

    assert result.applied_factor == 3.0
    assert result.warning is not None
    assert "outside 0.5-2.0" in result.warning
    assert np.isclose(result.mesh.extents[2], scan.extents[2] * 3.0)

