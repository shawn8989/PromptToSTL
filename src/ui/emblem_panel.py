"""Emblem / image upload UI section."""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import streamlit as st

from src.ui.helpers import (
    emoji_to_twemoji_svg,
    image_size_from_bytes,
    svg_size_from_bytes,
)


def render_emblem_section(
    schema: Dict[str, Any],
    template_id: str,
    params: Dict[str, Any],
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Render emblem upload controls. Returns (updated_params, emblem_asset, emblem_asset_info).
    emblem_asset: {"kind": "svg"|"heightmap", "bytes": ..., ...} or None
    emblem_asset_info: {"mm_w": ..., "mm_h": ...} or None
    """
    if "emblem_enabled" not in schema.get("params", {}):
        return params, None, None

    emblem_asset = None
    emblem_asset_info = None
    supports_heightmap = "emblem_kind" in schema.get("params", {})
    emblem_scale = float(params.get("emblem_scale", 1.0) or 1.0)

    source_options = ["None", "SVG upload", "Emoji"]
    if supports_heightmap:
        source_options.append("Image (heightmap)")

    default_source = "None"
    if int(params.get("emblem_enabled", 0)) == 1:
        kind = str(params.get("emblem_kind", "svg"))
        default_source = "Image (heightmap)" if kind == "heightmap" and supports_heightmap else "SVG upload"

    emblem_source = st.selectbox(
        "Emblem source",
        source_options,
        index=source_options.index(default_source),
        key=f"emblem_source_{template_id}",
    )

    if emblem_source == "SVG upload":
        uploaded = st.file_uploader("SVG file", type=["svg"], key=f"emblem_svg_{template_id}")
        if uploaded:
            svg_bytes = uploaded.getvalue()
            emblem_asset = {"kind": "svg", "bytes": svg_bytes}
            params.update(emblem_enabled=1, emblem_kind="svg")
            size = svg_size_from_bytes(svg_bytes)
            if size:
                emblem_asset_info = {"mm_w": size[0] * emblem_scale, "mm_h": size[1] * emblem_scale}

    elif emblem_source == "Emoji":
        emoji_text = st.text_input("Emoji", value="😀", key=f"emblem_emoji_{template_id}")
        if emoji_text.strip():
            svg_bytes = emoji_to_twemoji_svg(emoji_text)
            if svg_bytes:
                emblem_asset = {"kind": "svg", "bytes": svg_bytes}
                params.update(emblem_enabled=1, emblem_kind="svg")
                size = svg_size_from_bytes(svg_bytes)
                if size:
                    emblem_asset_info = {"mm_w": size[0] * emblem_scale, "mm_h": size[1] * emblem_scale}
            else:
                st.warning("Could not fetch emoji SVG. Try a different emoji.")

    elif emblem_source == "Image (heightmap)" and supports_heightmap:
        uploaded = st.file_uploader(
            "Image file", type=["png", "jpg", "jpeg", "bmp", "gif"],
            key=f"emblem_img_{template_id}",
        )
        invert = st.checkbox(
            "Invert image",
            value=bool(int(params.get("emblem_invert", 0) or 0)),
            key=f"emblem_invert_{template_id}",
        )
        params["emblem_invert"] = 1 if invert else 0
        if uploaded:
            image_bytes = uploaded.getvalue()
            try:
                from PIL import Image  # noqa: F401
                emblem_asset = {"kind": "heightmap", "bytes": image_bytes, "max_size": 256, "invert": invert}
                params.update(emblem_enabled=1, emblem_kind="heightmap")
                img_size = image_size_from_bytes(image_bytes, max_size=256)
                if img_size:
                    w, h = img_size
                    emblem_asset_info = {
                        "mm_w": max(1, w - 1) * emblem_scale,
                        "mm_h": max(1, h - 1) * emblem_scale,
                    }
            except ImportError:
                st.error("Pillow is required for image emblems. Run: pip install Pillow")

    if emblem_asset is None and not params.get("emblem_path"):
        params["emblem_enabled"] = 0

    return params, emblem_asset, emblem_asset_info
