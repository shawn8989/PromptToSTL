"""Static validation of every built-in template schema.

These tests need no OpenSCAD and run in milliseconds; they catch the most
common template-authoring mistakes (bad JSON, missing scad file, params with
no default or an out-of-range default).
"""
from __future__ import annotations

import pytest

from src.core.catalog import load_template
from tests.conftest import default_params, discover_templates

TEMPLATE_IDS = discover_templates()
ALLOWED_TYPES = {"string", "int", "integer", "number"}


def test_at_least_one_template():
    assert TEMPLATE_IDS, "no built-in templates discovered"


@pytest.mark.parametrize("tid", TEMPLATE_IDS)
def test_template_loads(tid):
    """schema.json parses and its referenced scad_file exists on disk."""
    schema, scad_path = load_template(tid)
    assert schema.get("scad_file"), f"{tid}: schema missing 'scad_file'"
    assert scad_path.exists(), f"{tid}: scad file {scad_path} does not exist"
    assert isinstance(schema.get("params", {}), dict), f"{tid}: 'params' must be an object"


@pytest.mark.parametrize("tid", TEMPLATE_IDS)
def test_params_have_valid_defaults(tid):
    """Every parameter declares a known type and an in-range default."""
    schema, _ = load_template(tid)
    for name, spec in schema.get("params", {}).items():
        vtype = spec.get("type", "string")
        assert vtype in ALLOWED_TYPES, f"{tid}.{name}: unknown type {vtype!r}"
        assert "default" in spec, f"{tid}.{name}: missing 'default'"

        default = spec.get("default")
        if vtype in {"int", "integer", "number"} and default is not None:
            lo, hi = spec.get("min"), spec.get("max")
            if lo is not None and hi is not None:
                assert lo <= hi, f"{tid}.{name}: min {lo} > max {hi}"
            if lo is not None:
                assert default >= lo, f"{tid}.{name}: default {default} < min {lo}"
            if hi is not None:
                assert default <= hi, f"{tid}.{name}: default {default} > max {hi}"


@pytest.mark.parametrize("tid", TEMPLATE_IDS)
def test_default_params_are_extractable(tid):
    """The app's default-param extraction yields one entry per declared param."""
    schema, _ = load_template(tid)
    params = default_params(schema)
    assert set(params) == set(schema.get("params", {}))
