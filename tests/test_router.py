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


# ---------------------------------------------------------------------------
# provider selection (_make_model) — offline, no API calls
# ---------------------------------------------------------------------------

def test_make_model_defaults_to_openai(monkeypatch) -> None:
    from src.intent.router import _make_model
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    model = _make_model()
    assert type(model).__name__ == "ChatOpenAI"


def test_make_model_prefers_anthropic_when_key_set(monkeypatch) -> None:
    import src.intent.router as router
    if router.ChatAnthropic is None:
        pytest.skip("langchain-anthropic not installed")
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    model = router._make_model()
    assert type(model).__name__ == "ChatAnthropic"


def test_make_model_env_override_openai(monkeypatch) -> None:
    from src.intent.router import _make_model
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    model = _make_model()
    assert type(model).__name__ == "ChatOpenAI"


# ---------------------------------------------------------------------------
# refinement message construction — offline
# ---------------------------------------------------------------------------

def test_build_messages_plain() -> None:
    from src.intent.router import _build_messages
    msgs = _build_messages("a dog tag", [{"template_id": "pet_tag"}])
    assert msgs[0]["role"] == "system"
    assert "REFINING" not in msgs[0]["content"]
    assert "current" not in msgs[1]["content"]


def test_build_messages_refinement_includes_current() -> None:
    from src.intent.router import _build_messages
    current = {"template_id": "pet_tag", "params": {"tag_w": 40}}
    msgs = _build_messages("make it wider", [{"template_id": "pet_tag"}], current)
    assert "REFINING" in msgs[0]["content"]
    assert '"tag_w": 40' in msgs[1]["content"]
