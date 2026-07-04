"""Image upload section for lithophane templates."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import streamlit as st

from src.ui.helpers import save_image_as_dat, image_size_from_bytes


def render_lithophane_section(
    params: Dict[str, Any],
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """
    Show image upload for lithophane mode. Returns (updated_params, litho_asset).
    litho_asset: {"bytes": ..., "invert": bool, "max_size": int} or None
    """
    st.subheader("Image")
    st.caption("Upload a high-contrast image. Dark areas become thick (opaque), bright areas become thin (transparent).")

    uploaded = st.file_uploader(
        "Source image", type=["png", "jpg", "jpeg", "bmp"],
        key="litho_image",
    )
    invert = st.checkbox(
        "Invert image (swap light/dark)",
        value=False,
        key="litho_invert",
        help="Use if your image looks reversed when backlit.",
    )
    max_res = st.select_slider(
        "Resolution (pixels wide)",
        options=[64, 100, 128, 192, 256, 384, 512],
        value=192,
        key="litho_res",
        help="Higher = more detail but slower to render in OpenSCAD.",
    )

    litho_asset = None
    if uploaded:
        image_bytes = uploaded.getvalue()
        img_size = image_size_from_bytes(image_bytes, max_size=max_res)
        if img_size:
            w, h = img_size
            st.success(f"Image loaded — {w}×{h}px at selected resolution.")
            litho_asset = {"bytes": image_bytes, "invert": invert, "max_size": max_res}
            params["dat_w"] = w
            params["dat_h"] = h
        else:
            st.error("Could not read image. Check that Pillow is installed.")
    else:
        st.info("No image loaded — a placeholder slab will be built.")

    return params, litho_asset
