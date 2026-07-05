"""Tests for src/core/catalog.py — template discovery and loading."""
from __future__ import annotations


import pytest
from src.core.catalog import list_templates, load_template

EXPECTED_TEMPLATES = {
    "coaster_round",
    "keychain_roundrect",
    "nameplate",
    "lithophane_heart",
    "lithophane_circle",
    "lithophane_rectangle",
    "lithophane_mom",
    "lithophane_dad",
}


def test_all_templates_discovered() -> None:
    """All expected templates must be found by list_templates()."""
    found = set(list_templates())
    missing = EXPECTED_TEMPLATES - found
    assert not missing, f"Templates not found: {missing}"


def test_load_template_returns_schema_and_path() -> None:
    """load_template() must return a dict and a valid Path for each template."""
    for tid in list_templates():
        schema, scad_path = load_template(tid)
        assert isinstance(schema, dict), f"{tid}: schema is not a dict"
        assert scad_path.exists(), f"{tid}: scad file missing at {scad_path}"


def test_schema_required_fields() -> None:
    """Every schema must have template_id, label, scad_file, and params."""
    for tid in list_templates():
        schema, _ = load_template(tid)
        for field in ("template_id", "label", "scad_file", "params"):
            assert field in schema, f"{tid}: missing '{field}' in schema"


def test_schema_params_have_type_and_default() -> None:
    """Every param must have a 'type' and 'default' key."""
    for tid in list_templates():
        schema, _ = load_template(tid)
        for param_name, spec in schema["params"].items():
            assert "type" in spec, f"{tid}.{param_name}: missing 'type'"
            assert "default" in spec, f"{tid}.{param_name}: missing 'default'"


def test_hidden_params_present_in_image_templates() -> None:
    """Templates with accepts_image=true must have photo_path hidden."""
    for tid in list_templates():
        schema, _ = load_template(tid)
        if schema.get("accepts_image"):
            params = schema["params"]
            assert "photo_path" in params, f"{tid}: missing photo_path"
            assert params["photo_path"].get("hidden"), f"{tid}: photo_path not hidden"


def test_load_template_raises_on_unknown() -> None:
    """load_template() must raise FileNotFoundError for nonexistent templates."""
    with pytest.raises(FileNotFoundError):
        load_template("nonexistent_template_xyz")
