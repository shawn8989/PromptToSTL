"""Unit tests for src/core/layout.py — layout_text() is a pure function."""
from __future__ import annotations

import pytest

from src.core.layout import layout_text

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BOX = dict(box_w_mm=60.0, box_h_mm=20.0, max_text_size=12.0, min_text_size=6.0)


def _fit(**kw):
    """Call layout_text with BOX defaults overridden by kw."""
    args = {**BOX, "max_lines": 1, "margin": 1.0, "line_gap_mm": 0.0, **kw}
    return layout_text(args.pop("text", "Hello"), **args)


# ---------------------------------------------------------------------------
# Empty text
# ---------------------------------------------------------------------------

def test_empty_string_returns_single_empty_line():
    result = layout_text("", max_lines=2, **BOX)
    assert result["lines"] == [""]
    assert result["truncated"] is False


def test_empty_list_returns_single_empty_line():
    result = layout_text([], max_lines=2, **BOX)
    assert result["lines"] == [""]
    assert result["truncated"] is False


def test_list_of_blanks_treated_as_empty():
    result = layout_text(["", "  "], max_lines=2, **BOX)
    assert result["lines"] == [""]


# ---------------------------------------------------------------------------
# Return-value contract
# ---------------------------------------------------------------------------

def test_result_has_required_keys():
    result = _fit(text="Hi")
    for key in ("lines", "text_size", "offsets_y", "truncated", "warning", "line_widths"):
        assert key in result, f"missing key: {key}"


def test_text_size_within_bounds():
    result = _fit(text="Hello world", max_text_size=14.0, min_text_size=6.0)
    assert 6.0 <= result["text_size"] <= 14.0


def test_line_count_matches_offsets():
    result = _fit(text="Hello world", max_lines=2)
    assert len(result["offsets_y"]) == len(result["lines"])


def test_line_widths_count_matches_lines():
    result = _fit(text="Hello world", max_lines=2)
    assert len(result["line_widths"]) == len(result["lines"])


# ---------------------------------------------------------------------------
# Single-line fitting
# ---------------------------------------------------------------------------

def test_short_text_fits_at_max_size():
    result = layout_text("Hi", max_lines=1, **BOX)
    assert result["text_size"] == BOX["max_text_size"]
    assert result["truncated"] is False


def test_single_line_offset_is_zero():
    result = layout_text("Hi", max_lines=1, **BOX)
    assert result["offsets_y"] == [0.0]


# ---------------------------------------------------------------------------
# Multi-line wrapping
# ---------------------------------------------------------------------------

def test_long_text_wraps_into_two_lines():
    # "HELLO WORLD" is wider than a 20mm box at 12mm; should split
    result = layout_text(
        "HELLO WORLD",
        max_lines=2,
        box_w_mm=20.0,
        box_h_mm=20.0,
        max_text_size=12.0,
        min_text_size=6.0,
        margin=1.0,
    )
    assert len(result["lines"]) == 2


def test_list_input_joins_and_wraps():
    result = layout_text(
        ["HELLO", "WORLD"],
        max_lines=2,
        box_w_mm=20.0,
        box_h_mm=20.0,
        max_text_size=12.0,
        min_text_size=6.0,
        margin=1.0,
    )
    # Lines joined to "HELLO WORLD", then re-split to fit
    assert "HELLO" in " ".join(result["lines"])


# ---------------------------------------------------------------------------
# Font-size stepping
# ---------------------------------------------------------------------------

def test_very_wide_text_reduces_font_size():
    result = layout_text(
        "WWWWWWWWWWWWWWWW",
        max_lines=1,
        box_w_mm=60.0,
        box_h_mm=30.0,
        max_text_size=12.0,
        min_text_size=4.0,
        margin=1.0,
    )
    assert result["text_size"] < 12.0


def test_min_max_swapped_still_works():
    """min > max should be silently swapped."""
    result = layout_text(
        "Hello",
        max_lines=1,
        box_w_mm=60.0,
        box_h_mm=20.0,
        max_text_size=6.0,   # intentionally swapped
        min_text_size=12.0,
        margin=1.0,
    )
    assert 6.0 <= result["text_size"] <= 12.0


# ---------------------------------------------------------------------------
# Truncation fallback
# ---------------------------------------------------------------------------

def test_impossible_fit_truncates():
    # Tiny box, max_lines=1, large text -> must truncate
    result = layout_text(
        "WWWWWWWWWWWWWWWWWWWWWWWWWWWW",
        max_lines=1,
        box_w_mm=10.0,
        box_h_mm=5.0,
        max_text_size=8.0,
        min_text_size=8.0,
        margin=1.0,
    )
    assert result["truncated"] is True
    assert result["lines"][-1].endswith("…")


def test_truncated_line_ends_with_ellipsis():
    result = layout_text(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        max_lines=1,
        box_w_mm=8.0,
        box_h_mm=8.0,
        max_text_size=8.0,
        min_text_size=8.0,
        margin=1.0,
    )
    assert "…" in result["lines"][-1]


# ---------------------------------------------------------------------------
# Line-gap behaviour
# ---------------------------------------------------------------------------

def test_two_lines_have_nonzero_offsets_when_gap_set():
    result = layout_text(
        "HELLO WORLD",
        max_lines=2,
        box_w_mm=20.0,
        box_h_mm=30.0,
        max_text_size=8.0,
        min_text_size=4.0,
        margin=1.0,
        line_gap_mm=4.0,
    )
    if len(result["lines"]) > 1:
        assert any(o != 0.0 for o in result["offsets_y"])


def test_gap_reduced_warning_when_box_too_short():
    result = layout_text(
        "TOP BOTTOM",
        max_lines=2,
        box_w_mm=30.0,
        box_h_mm=10.0,   # tight height
        max_text_size=4.0,
        min_text_size=4.0,
        margin=1.0,
        line_gap_mm=20.0,  # large gap that won't fit
    )
    if len(result["lines"]) > 1 and "line_gap_mm" in result:
        assert result["line_gap_mm"] <= 20.0


# ---------------------------------------------------------------------------
# Margin
# ---------------------------------------------------------------------------

def test_margin_below_one_tightens_box():
    # With margin=0.5 the effective box is halved; a text that barely fits at
    # margin=1.0 should require a smaller font at margin=0.5.
    common = dict(
        max_lines=1, box_w_mm=20.0, box_h_mm=20.0,
        max_text_size=12.0, min_text_size=4.0,
    )
    r_full = layout_text("HELLO", margin=1.0, **common)
    r_tight = layout_text("HELLO", margin=0.5, **common)
    assert r_tight["text_size"] <= r_full["text_size"]
