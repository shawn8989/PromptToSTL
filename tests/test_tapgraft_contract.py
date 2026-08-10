"""Bridge-contract tests: the stdout and JSON surface Studio depends on.

These lock the pieces of the contract that previously drifted from
Specs/studio-graft-bridge.md: the canonical ``triangles`` key, PROGRESS
lines, the final stdout JSON line, and ``--report-only`` honouring --json.
"""
from __future__ import annotations

import json

from src.tapgraft import cli
from tests.tapgraft_primitives import drilled_cylinder, lumpy_sphere_on_stick


def _write_inputs(tmp_path):
    scan_path = tmp_path / "scan.stl"
    base_path = tmp_path / "base.stl"
    lumpy_sphere_on_stick().export(scan_path)
    drilled_cylinder().export(base_path)
    return scan_path, base_path


def _final_json(captured_stdout: str) -> dict:
    """The contract says the report is the last stdout line."""
    lines = [line for line in captured_stdout.splitlines() if line.strip()]
    return json.loads(lines[-1])


def test_final_stdout_line_is_the_report_json(capsys, tmp_path):
    scan_path, base_path = _write_inputs(tmp_path)
    out_path = tmp_path / "result.stl"

    exit_code = cli.main(
        ["--scan", str(scan_path), "--base", str(base_path), "--out", str(out_path),
         "--allow-unverified-scale"]
    )
    report = _final_json(capsys.readouterr().out)

    assert exit_code == 0
    assert report["ok"] is True
    assert report["tool_version"]
    assert report["output"]["path"] == str(out_path)


def test_output_reports_canonical_triangles_key(capsys, tmp_path):
    scan_path, base_path = _write_inputs(tmp_path)
    out_path = tmp_path / "result.stl"

    cli.main(["--scan", str(scan_path), "--base", str(base_path), "--out", str(out_path),
              "--allow-unverified-scale"])
    report = _final_json(capsys.readouterr().out)

    for block in (report["output"], report["input"]["scan"], report["input"]["base"]):
        assert "triangles" in block
        # `faces` is retained as an alias and must never disagree.
        assert block["triangles"] == block["faces"]
    assert report["output"]["triangles"] > 0


def test_progress_lines_are_emitted_and_end_at_100(capsys, tmp_path):
    scan_path, base_path = _write_inputs(tmp_path)
    out_path = tmp_path / "result.stl"

    cli.main(["--scan", str(scan_path), "--base", str(base_path), "--out", str(out_path),
              "--allow-unverified-scale"])
    stdout = capsys.readouterr().out

    progress = [line for line in stdout.splitlines() if line.startswith("PROGRESS ")]
    assert progress, "no PROGRESS lines emitted"

    percents = []
    for line in progress:
        _, stage, percent = line.split()
        assert stage
        percents.append(int(percent))

    assert percents == sorted(percents), "progress must not go backwards"
    assert percents[-1] == 100


def test_report_only_writes_json_but_no_stl(capsys, tmp_path):
    scan_path, base_path = _write_inputs(tmp_path)
    out_path = tmp_path / "result.stl"
    json_path = tmp_path / "report.json"

    exit_code = cli.main(
        [
            "--scan", str(scan_path),
            "--base", str(base_path),
            "--out", str(out_path),
            "--json", str(json_path),
            "--report-only",
        ]
    )

    assert exit_code == 0
    assert json_path.exists(), "--report-only must honour --json"
    assert not out_path.exists(), "--report-only must not write an STL"

    written = json.loads(json_path.read_text())
    assert written["pocket"] is not None
    assert written["output"] is None
    assert _final_json(capsys.readouterr().out)["ok"] is True


def test_input_error_still_emits_report_json(capsys, tmp_path):
    _, base_path = _write_inputs(tmp_path)
    json_path = tmp_path / "report.json"

    exit_code = cli.main(
        [
            "--scan", str(tmp_path / "missing.stl"),
            "--base", str(base_path),
            "--out", str(tmp_path / "result.stl"),
            "--json", str(json_path),
        ]
    )
    report = _final_json(capsys.readouterr().out)

    assert exit_code == 2
    assert report["ok"] is False
    assert report["error"]["code"] == 2
    assert json_path.exists(), "a failing run must still produce the report Studio reads"
