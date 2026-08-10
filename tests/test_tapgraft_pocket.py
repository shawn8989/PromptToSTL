"""Tests for pocket detection and preservation through a real union."""
from __future__ import annotations

import json

import numpy as np
import trimesh

from src.tapgraft import cli
from src.tapgraft.pocket import detect_pocket
from tests.tapgraft_primitives import (
    POCKET_DEPTH_MM,
    POCKET_DIAMETER_MM,
    drilled_cylinder,
    lumpy_sphere_on_stick,
)


def test_detects_generated_pocket():
    pocket = detect_pocket(drilled_cylinder())

    assert pocket.mounting_face == "-Z"
    assert np.isclose(pocket.diameter_mm, POCKET_DIAMETER_MM, atol=0.02)
    assert np.isclose(pocket.depth_mm, POCKET_DEPTH_MM, atol=0.02)
    assert np.allclose(pocket.center_mm, [0.0, 0.0, 0.0], atol=0.02)


def test_pocket_survives_graft(tmp_path):
    scan_path = tmp_path / "scan.stl"
    base_path = tmp_path / "base.stl"
    output_path = tmp_path / "grafted.stl"
    json_path = tmp_path / "report.json"
    lumpy_sphere_on_stick().export(scan_path)
    drilled_cylinder().export(base_path)

    exit_code = cli.main(
        [
            "--scan",
            str(scan_path),
            "--base",
            str(base_path),
            "--out",
            str(output_path),
            "--json",
            str(json_path),
            "--allow-unverified-scale",
        ]
    )

    assert exit_code == 0
    assert output_path.exists()
    report = json.loads(json_path.read_text(encoding="utf-8"))
    pocket_check = next(check for check in report["checks"] if check["name"] == "pocket_intact")
    assert pocket_check["pass"] is True
    assert max(pocket_check["measured"].values()) <= 0.2

    result = trimesh.load_mesh(output_path, process=True)
    after = detect_pocket(result)
    assert np.isclose(after.diameter_mm, POCKET_DIAMETER_MM, atol=0.2)
    assert np.isclose(after.depth_mm, POCKET_DEPTH_MM, atol=0.2)
    assert np.allclose(after.center_mm, [0.0, 0.0, 0.0], atol=0.2)

