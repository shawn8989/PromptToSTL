"""Tests for _coerce_value and _sanitize_params in src/intent/router.py — no API key needed."""
from __future__ import annotations

import pytest
from src.intent.router import _coerce_value, _sanitize_params


# ---------------------------------------------------------------------------
# _coerce_value
# ---------------------------------------------------------------------------

def test_coerce_integer_from_float_string() -> None:
    spec = {"type": "integer", "default": 5, "min": 1, "max": 100}
    assert _coerce_value("42.9", spec) == 42


def test_coerce_integer_clamp_min() -> None:
    spec = {"type": "integer", "default": 10, "min": 20, "max": 100}
    assert _coerce_value(5, spec) == 20


def test_coerce_integer_clamp_max() -> None:
    spec = {"type": "integer", "default": 10, "min": 1, "max": 50}
    assert _coerce_value(99, spec) == 50


def test_coerce_integer_invalid_returns_default() -> None:
    spec = {"type": "integer", "default": 7, "min": 1, "max": 100}
    assert _coerce_value("not_a_number", spec) == 7


def test_coerce_number_float() -> None:
    spec = {"type": "number", "default": 1.0, "min": 0.5, "max": 5.0}
    assert _coerce_value("3.14", spec) == pytest.approx(3.14)


def test_coerce_number_clamp_min() -> None:
    spec = {"type": "number", "default": 1.0, "min": 2.0, "max": 10.0}
    assert _coerce_value(0.5, spec) == pytest.approx(2.0)


def test_coerce_number_clamp_max() -> None:
    spec = {"type": "number", "default": 1.0, "min": 0.0, "max": 3.0}
    assert _coerce_value(9.9, spec) == pytest.approx(3.0)


def test_coerce_string() -> None:
    spec = {"type": "string", "default": "hello"}
    assert _coerce_value("world", spec) == "world"


def test_coerce_none_returns_default() -> None:
    spec = {"type": "integer", "default": 42, "min": 1, "max": 100}
    assert _coerce_value(None, spec) == 42


# ---------------------------------------------------------------------------
# _sanitize_params
# ---------------------------------------------------------------------------

def test_sanitize_uses_defaults_for_missing_keys() -> None:
    schema = {
        "params": {
            "width": {"type": "number", "default": 80.0, "min": 30.0, "max": 200.0},
        }
    }
    result = _sanitize_params(schema, {})
    assert result["width"] == pytest.approx(80.0)


def test_sanitize_coerces_and_clamps() -> None:
    schema = {
        "params": {
            "lines": {"type": "integer", "default": 1, "min": 1, "max": 3},
        }
    }
    result = _sanitize_params(schema, {"lines": 99})
    assert result["lines"] == 3


def test_sanitize_drops_unknown_keys() -> None:
    schema = {
        "params": {
            "plate_w": {"type": "number", "default": 100.0, "min": 30.0, "max": 250.0},
        }
    }
    result = _sanitize_params(schema, {"plate_w": 120.0, "unknown_param": "ignored"})
    assert "unknown_param" not in result
    assert result["plate_w"] == pytest.approx(120.0)


def test_sanitize_empty_schema() -> None:
    result = _sanitize_params({}, {"something": 1})
    assert result == {}
