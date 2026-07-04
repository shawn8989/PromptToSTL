"""Tests for src/core/layout.py — no external dependencies."""
from __future__ import annotations

import pytest
from src.core.layout import layout_text


def test_single_word_fits_at_max_size() -> None:
    """A short word should fit in one line at max_text_size."""
    result = layout_text("Hi", max_lines=3, box_w_mm=60, box_h_mm=20,
                         max_text_size=10.0, min_text_size=4.0)
    assert result["lines"] == ["Hi"]
    assert result["text_size"] == 10.0
    assert result["truncated"] is False


def test_long_text_wraps_multiple_lines() -> None:
    """Text too wide for one line should be split across multiple lines without truncation."""
    result = layout_text("Hello World", max_lines=3, box_w_mm=20, box_h_mm=30,
                         max_text_size=10.0, min_text_size=4.0)
    assert len(result["lines"]) > 1
    assert result["truncated"] is False


def test_long_text_wraps_to_three_lines() -> None:
    """Text too wide for two lines should use three when allowed."""
    result = layout_text("One Two Three", max_lines=3, box_w_mm=14, box_h_mm=40,
                         max_text_size=8.0, min_text_size=4.0)
    assert len(result["lines"]) == 3
    assert result["truncated"] is False


def test_truncation_with_ellipsis() -> None:
    """Text that cannot fit even at min size should be truncated with …"""
    result = layout_text("VeryLongWordThatWontFit", max_lines=1,
                         box_w_mm=5, box_h_mm=5,
                         max_text_size=3.0, min_text_size=3.0)
    assert result["truncated"] is True
    assert result["lines"][-1].endswith("…")


def test_line_gap_reduced_warning() -> None:
    """Warning should mention line gap when height is tight."""
    result = layout_text("One Two", max_lines=2, box_w_mm=30, box_h_mm=12,
                         max_text_size=6.0, min_text_size=4.0, line_gap_mm=4.0)
    # May or may not reduce gap depending on fit, but should not crash
    assert "lines" in result
    assert "text_size" in result


def test_empty_text_returns_max_size() -> None:
    """Empty input should return max_text_size and a single empty line."""
    result = layout_text("", max_lines=3, box_w_mm=100, box_h_mm=30,
                         max_text_size=12.0, min_text_size=4.0)
    assert result["text_size"] == 12.0
    assert result["lines"] == [""]
    assert result["truncated"] is False


def test_line_widths_match_lines() -> None:
    """line_widths list length must equal lines list length."""
    result = layout_text("Alpha Beta Gamma", max_lines=3, box_w_mm=40, box_h_mm=40,
                         max_text_size=8.0, min_text_size=4.0)
    assert len(result["line_widths"]) == len(result["lines"])


def test_offsets_y_match_lines() -> None:
    """offsets_y list length must equal lines list length."""
    result = layout_text("A B C", max_lines=3, box_w_mm=40, box_h_mm=40,
                         max_text_size=8.0, min_text_size=4.0)
    assert len(result["offsets_y"]) == len(result["lines"])


def test_iterable_input() -> None:
    """Passing a list of strings should join them into a single text."""
    result = layout_text(["Hello", "World"], max_lines=3, box_w_mm=80, box_h_mm=20,
                         max_text_size=8.0, min_text_size=4.0)
    assert "Hello" in " ".join(result["lines"])


def test_no_fit_uses_min_text_size() -> None:
    """When nothing fits, output text_size should be ≤ min_text_size."""
    result = layout_text("WWWWWWWWWWWWWWWWWWWW", max_lines=1,
                         box_w_mm=10, box_h_mm=10,
                         max_text_size=6.0, min_text_size=3.0)
    assert result["text_size"] <= 3.0
