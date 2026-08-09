"""CLI output, reporting, and exit-code contract tests."""
from __future__ import annotations

import trimesh

from src.tapgraft import cli, graft
from tests.tapgraft_primitives import drilled_cylinder, lumpy_sphere_on_stick


def _write_inputs(tmp_path):
    scan_path = tmp_path / "scan.stl"
    base_path = tmp_path / "base.stl"
    lumpy_sphere_on_stick().export(scan_path)
    drilled_cylinder().export(base_path)
    return scan_path, base_path


def test_exit_nonzero_on_verification_failure(monkeypatch, tmp_path):
    scan_path, base_path = _write_inputs(tmp_path)
    output_path = tmp_path / "result.stl"
    failed_path = tmp_path / "result.FAILED.stl"

    def return_disconnected_mesh(scan, base):
        return graft.BooleanResult(
            mesh=trimesh.util.concatenate((base.copy(), scan.copy())),
            engine="manifold3d",
            fell_back=False,
            diagnostic="simulated detached union result",
        )

    monkeypatch.setattr(graft, "union_meshes", return_disconnected_mesh)

    exit_code = cli.main(
        ["--scan", str(scan_path), "--base", str(base_path), "--out", str(output_path)]
    )

    assert exit_code != 0
    assert failed_path.exists()
    assert not output_path.exists()
    assert cli.last_report()["error"]["message"] == "verification check failed: single_component"
    assert cli.last_report()["error"]["likely_cause"]


def test_report_only_writes_nothing(tmp_path):
    scan_path, base_path = _write_inputs(tmp_path)
    output_path = tmp_path / "must-not-exist.stl"
    json_path = tmp_path / "must-not-exist.json"

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
            "--report-only",
        ]
    )

    assert exit_code == 0
    assert cli.last_report()["ok"] is True
    assert not output_path.exists()
    assert not json_path.exists()
    assert not list(tmp_path.glob("*.FAILED.stl"))


def test_scale_warning_is_loud_and_report_only_continues(capsys, tmp_path):
    scan_path, base_path = _write_inputs(tmp_path)

    exit_code = cli.main(
        [
            "--scan",
            str(scan_path),
            "--base",
            str(base_path),
            "--height",
            "220",
            "--report-only",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "WARNING" in captured.out
    assert "outside 0.5-2.0" in captured.out
    assert cli.last_report()["scale"]["applied_factor"] > 2.0

