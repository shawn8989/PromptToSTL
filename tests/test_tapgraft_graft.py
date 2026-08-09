"""Regression tests for grafting and the post-boolean verification gate."""
from __future__ import annotations

from src.tapgraft import cli, graft
from tests.tapgraft_primitives import drilled_cylinder, lumpy_sphere_on_stick


def test_volume_check_catches_failed_boolean(monkeypatch, tmp_path):
    """A valid-looking boolean result that is just the base must be rejected."""
    scan_path = tmp_path / "scan.stl"
    base_path = tmp_path / "base.stl"
    output_path = tmp_path / "grafted.stl"
    failed_path = tmp_path / "grafted.FAILED.stl"
    lumpy_sphere_on_stick().export(scan_path)
    drilled_cylinder().export(base_path)

    def return_base_unchanged(scan, base):
        return graft.BooleanResult(
            mesh=base.copy(),
            engine="manifold3d",
            fell_back=False,
            diagnostic="simulated silent boolean failure",
        )

    monkeypatch.setattr(graft, "union_meshes", return_base_unchanged)

    exit_code = cli.main(
        ["--scan", str(scan_path), "--base", str(base_path), "--out", str(output_path)]
    )

    assert exit_code == 1
    assert failed_path.exists()
    assert not output_path.exists()
    report = cli.last_report()
    volume_check = next(check for check in report["checks"] if check["name"] == "volume_exceeds_base")
    assert volume_check["pass"] is False
    assert report["error"]["likely_cause"]
