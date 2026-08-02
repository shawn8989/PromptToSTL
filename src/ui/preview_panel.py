"""3D preview panel."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Optional
import subprocess

import streamlit as st

try:
    from streamlit_stl import stl_from_file
except ImportError:
    stl_from_file = None

try:
    import trimesh
except ImportError:
    trimesh = None


PLACEHOLDER_STL = Path(__file__).resolve().parents[2] / "templates" / "placeholder.stl"
OUT_DIR = Path(__file__).resolve().parents[2] / "out"


def render_preview_panel(build_id: int) -> None:
    """Render the right-column 3D preview panel."""
    st.subheader("3D Preview")

    use_placeholder = st.checkbox("Show placeholder model")
    open_folder = st.checkbox("Open output folder after build")

    st.caption("Previously built models")
    stl_files = sorted(
        [p for p in OUT_DIR.rglob("*.stl") if p.resolve() != PLACEHOLDER_STL],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    stl_labels = {}
    for p in stl_files:
        rel = p.relative_to(OUT_DIR)
        job = rel.parts[0] if rel.parts else ""
        mtime = time.strftime("%Y-%m-%d %H:%M", time.localtime(p.stat().st_mtime))
        stl_labels[f"{job}/{p.name} ({mtime})"] = p

    if stl_labels:
        selected_label = st.selectbox("Load previous model", list(stl_labels.keys()))
        if st.button("Load selected"):
            st.session_state["last_stl_path"] = str(stl_labels[selected_label])
            st.session_state["preview_nonce"] = st.session_state.get("preview_nonce", 0) + 1

    last = st.session_state.get("last_stl_path")
    preview_path: Optional[Path] = Path(last) if last else None
    if use_placeholder:
        preview_path = PLACEHOLDER_STL

    if preview_path and preview_path.exists() and preview_path.stat().st_size > 0:
        if open_folder:
            if st.button("Open output folder"):
                subprocess.run(["open", str(preview_path.parent)])
        _render_stl(preview_path, build_id)
    else:
        st.info("Build an STL to see a preview here.")


def _render_stl(path: Path, build_id: int) -> None:
    if stl_from_file:
        try:
            stl_from_file(str(path), height=500, key=f"stl_preview_{build_id}")
            return
        except Exception as e:
            st.warning(f"3D viewer error: {e}")

    if trimesh:
        try:
            mesh = trimesh.load_mesh(path, force="mesh")
            st.write(f"Bounds: {mesh.bounds.tolist()}")
            st.write(f"Extents: {mesh.extents.tolist()}")
        except Exception as e:
            st.warning(f"Could not inspect mesh: {e}")
    else:
        st.warning("Install streamlit-stl and trimesh for 3D preview.")
