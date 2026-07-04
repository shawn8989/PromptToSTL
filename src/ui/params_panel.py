"""Render parameter widgets for a template schema and apply intent overrides."""
from __future__ import annotations

from typing import Any, Dict, Optional

import streamlit as st

from src.ui.helpers import eval_expr
from src.core.layout import layout_text

TEXT_MARGIN = 0.9


def render_params(
    schema: Dict[str, Any],
    template_id: str,
    intent_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Render all non-hidden params as Streamlit widgets. Returns a params dict."""
    params: Dict[str, Any] = {}

    for k, spec in schema["params"].items():
        t = spec["type"]
        default = spec.get("default")
        if intent_params and k in intent_params:
            default = intent_params[k]
        if spec.get("hidden"):
            params[k] = default
            continue

        if t == "string":
            opts = spec.get("options")
            if opts:
                options = [str(o) for o in opts]
                dv = str(default) if default is not None else options[0]
                idx = options.index(dv) if dv in options else 0
                params[k] = st.selectbox(k, options, index=idx)
            else:
                params[k] = st.text_input(k, value=str(default) if default is not None else "")
        elif t in {"int", "integer"}:
            params[k] = st.number_input(
                k, value=int(default), step=1,
                min_value=int(spec.get("min", -(10**9))),
                max_value=int(spec.get("max", 10**9)),
            )
        elif t == "number":
            params[k] = st.number_input(
                k, value=float(default),
                min_value=float(spec.get("min", -1e9)),
                max_value=float(spec.get("max", 1e9)),
            )
        else:
            st.warning(f"Unknown type '{t}' for param '{k}'")

    return params


def apply_text_layout(
    schema: Dict[str, Any],
    template_id: str,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """Auto-fit text into the template's text_box, returning updated params."""
    text_box = schema.get("text_box") or {}
    if not text_box or "text_size" not in params:
        return params

    max_text_size = float(params.get("text_size", 0))
    min_text_size = float(schema["params"].get("text_size", {}).get("min", max_text_size))
    max_lines = int(schema.get("max_lines", 1))

    box_w = eval_expr(text_box.get("box_w", 0), params)
    box_h = eval_expr(text_box.get("box_h", 0), params)
    offset_x = eval_expr(text_box.get("offset_x", 0), params)
    offset_y = eval_expr(text_box.get("offset_y", 0), params)

    params.setdefault("offset_x", offset_x)
    params.setdefault("offset_y", offset_y)
    params.setdefault("text_box_w", box_w)
    params.setdefault("text_box_h", box_h)
    params.setdefault("text_box_offset_x", offset_x)
    params.setdefault("text_box_offset_y", offset_y)

    raw_lines = [str(params.get(k, "")) for k in ("line1", "line2", "line3") if k in params]
    if not raw_lines and "text" in params:
        raw_lines = [str(params.get("text", ""))]

    line_gap = float(params.get("line_gap", 0))

    layout = layout_text(
        raw_lines,
        max_lines=max_lines,
        box_w_mm=box_w,
        box_h_mm=box_h,
        max_text_size=max_text_size,
        min_text_size=min_text_size,
        margin=TEXT_MARGIN,
        line_gap_mm=line_gap,
    )

    params["text_size"] = layout["text_size"]
    if "line_gap" in params and "line_gap_mm" in layout:
        params["line_gap"] = layout["line_gap_mm"]

    lines = layout["lines"] + ["", "", ""]
    for i, key in enumerate(("line1", "line2", "line3")):
        if key in params:
            params[key] = lines[i]

    if layout.get("warning"):
        st.warning(layout["warning"])
    elif layout.get("truncated"):
        st.warning("Text was truncated to fit.")

    return params
