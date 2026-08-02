"""Shared pytest fixtures/helpers for the PromptToSTL test suite."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = REPO_ROOT / "templates"


def discover_templates() -> list[str]:
    """Return built-in (non-custom) template ids that have a schema.json."""
    ids = []
    if TEMPLATES_DIR.exists():
        for d in sorted(TEMPLATES_DIR.iterdir()):
            if d.is_dir() and d.name != "custom" and (d / "schema.json").exists():
                ids.append(d.name)
    return ids


def default_params(schema: dict) -> dict:
    """Extract the default value for each schema parameter."""
    return {k: v.get("default") for k, v in schema.get("params", {}).items()}


def openscad_exe() -> str | None:
    """Path to an OpenSCAD executable, or None if unavailable."""
    return shutil.which("openscad")


# Templates that cannot be built headlessly from default params alone.
# Empirically every built-in template renders a valid STL from defaults
# (emblem templates simply omit the disabled-by-default emblem; the lithophane
# renders a flat plate when no heightmap is set), so this is currently empty.
ASSET_DEPENDENT: set[str] = set()

# Templates too slow to render on the legacy OpenSCAD 2021.01 CGAL backend
# (BOSL2 bezier sweeps). They build fine on 2024+ with the Manifold backend;
# marked xfail here so the suite stays honest without hanging CI.
SLOW_LEGACY = {"cuban_link_chain"}


@pytest.fixture(scope="session")
def openscad():
    exe = openscad_exe()
    if not exe:
        pytest.skip("OpenSCAD not installed / not on PATH")
    return exe
