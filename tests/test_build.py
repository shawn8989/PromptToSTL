"""End-to-end build smoke tests: template + defaults -> OpenSCAD -> valid STL.

Skipped automatically when OpenSCAD is not installed, so the suite still runs
(schema tests only) in minimal environments.
"""
from __future__ import annotations

import subprocess

import pytest

from src.core.catalog import load_template
from src.core.runner import run_openscad
from src.core.validate import validate_stl
from tests.conftest import (
    ASSET_DEPENDENT,
    SLOW_LEGACY,
    default_params,
    discover_templates,
)

TEMPLATE_IDS = discover_templates()
# Per-template render cap so a pathological model fails loudly instead of hanging CI.
BUILD_TIMEOUT_S = 60


@pytest.mark.parametrize("tid", TEMPLATE_IDS)
def test_template_builds_valid_stl(tid, openscad, tmp_path):
    if tid in ASSET_DEPENDENT:
        pytest.skip(f"{tid} needs an external asset (emblem/heightmap) to render")
    if tid in SLOW_LEGACY:
        pytest.xfail(f"{tid} is too slow on legacy OpenSCAD (needs Manifold backend)")

    schema, scad_path = load_template(tid)
    params = default_params(schema)
    out_stl = tmp_path / f"{tid}.stl"

    try:
        # run_openscad has no timeout of its own; guard it here.
        with _time_limit(BUILD_TIMEOUT_S):
            run_openscad(openscad, scad_path, out_stl, params)
    except subprocess.TimeoutExpired:
        pytest.fail(f"{tid}: render exceeded {BUILD_TIMEOUT_S}s")

    result = validate_stl(out_stl)
    assert result["ok"], f"{tid}: invalid STL -> {result.get('error')}"
    assert result["faces"] > 0, f"{tid}: STL has no faces"
    assert all(d > 0 for d in result["size_xyz_mm"]), f"{tid}: degenerate bounds {result['size_xyz_mm']}"


class _time_limit:
    """Enforce a wall-clock cap on the OpenSCAD subprocess via SIGALRM."""

    def __init__(self, seconds: int):
        self.seconds = seconds

    def __enter__(self):
        import signal

        def _raise(signum, frame):
            raise subprocess.TimeoutExpired("openscad", self.seconds)

        self._old = signal.signal(signal.SIGALRM, _raise)
        signal.alarm(self.seconds)
        return self

    def __exit__(self, *exc):
        import signal

        signal.alarm(0)
        signal.signal(signal.SIGALRM, self._old)
        return False
