import ast
import json
import subprocess
import time
import uuid
from pathlib import Path
import streamlit as st

from src.core.catalog import list_templates, load_template
from src.core.layout import layout_text
from src.core.runner import run_openscad
from src.core.validate import validate_stl
from streamlit_stl import stl_from_file
import trimesh
try:
    import pyvista as pv
except Exception:
    pv = None


DEFAULT_OPENSCAD = "openscad"  # on mac: usually in PATH

OUT_DIR = Path(__file__).resolve().parent / "out"
PLACEHOLDER_STL = Path(__file__).resolve().parent / "templates" / "placeholder.stl"
TEXT_MARGIN = 0.9


def eval_expr(value, params):
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return 0.0

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            left = _eval(node.left)
            right = _eval(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right if right != 0 else 0.0
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            val = _eval(node.operand)
            return val if isinstance(node.op, ast.UAdd) else -val
        if isinstance(node, ast.Name):
            return float(params.get(node.id, 0.0))
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        return 0.0

    try:
        parsed = ast.parse(value, mode="eval")
        return float(_eval(parsed))
    except Exception:
        return 0.0

st.set_page_config(page_title="PromptToSTL", layout="wide")
st.title("PromptToSTL (Local GUI)")

if "preview_nonce" not in st.session_state:
    st.session_state["preview_nonce"] = 0

with st.sidebar:
    st.header("Engine")
    openscad_exe = st.text_input("OpenSCAD executable", value=DEFAULT_OPENSCAD)

templates = list_templates()
if not templates:
    st.error("No templates found. Add templates/<id>/schema.json and model.scad")
    st.stop()

colL, colR = st.columns([1, 1], gap="large")

with colL:
    st.subheader("Template")
    template_id = st.selectbox("Choose template", templates)
    schema, scad_path = load_template(template_id)

    st.caption(schema.get("label", template_id))

    st.subheader("Parameters")
    params = {}
    for k, spec in schema["params"].items():
        t = spec["type"]
        default = spec.get("default")

        if t == "string":
            params[k] = st.text_input(k, value=str(default) if default is not None else "")
        elif t == "int":
            params[k] = st.number_input(k, value=int(default), step=1,
                                        min_value=int(spec.get("min", -10**9)),
                                        max_value=int(spec.get("max", 10**9)))
        elif t == "number":
            params[k] = st.number_input(k, value=float(default),
                                        min_value=float(spec.get("min", -1e9)),
                                        max_value=float(spec.get("max", 1e9)))
        else:
            st.warning(f"Unknown type {t} for {k}")

    layout_debug = None
    text_box = schema.get("text_box") or {}
    if text_box and "text_size" in params:
        max_text_size = float(params.get("text_size", 0))
        min_text_size = float(schema["params"].get("text_size", {}).get("min", max_text_size))
        max_lines = int(schema.get("max_lines", 1))
        box_w = eval_expr(text_box.get("box_w", 0), params)
        box_h = eval_expr(text_box.get("box_h", 0), params)
        offset_x = eval_expr(text_box.get("offset_x", 0), params)
        offset_y = eval_expr(text_box.get("offset_y", 0), params)

        raw_lines = []
        for key in ("line1", "line2", "line3"):
            if key in params:
                raw_lines.append(str(params.get(key, "")))
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
        layout_debug = layout

        params["text_size"] = layout["text_size"]
        params["offset_x"] = offset_x
        params["offset_y"] = offset_y
        if "line_gap" in params and "line_gap_mm" in layout:
            params["line_gap"] = layout["line_gap_mm"]

        lines = layout["lines"] + ["", "", ""]
        if "line1" in params:
            params["line1"] = lines[0]
        if "line2" in params:
            params["line2"] = lines[1]
        if "line3" in params:
            params["line3"] = lines[2]

        if layout.get("warning"):
            st.warning(layout["warning"])
        elif layout.get("truncated"):
            st.warning("Text was truncated to fit the text box.")

    with st.expander("Layout Debug", expanded=False):
        if layout_debug:
            st.write(f"box_w: {box_w}")
            st.write(f"box_h: {box_h}")
            st.write(f"offset_x: {offset_x}")
            st.write(f"offset_y: {offset_y}")
            st.write(f"text_size: {layout_debug.get('text_size')}")
            st.write(f"lines: {layout_debug.get('lines')}")
            st.write(f"offsets_y: {layout_debug.get('offsets_y')}")
            st.write(f"warning: {layout_debug.get('warning')}")
            st.write(f"truncated: {layout_debug.get('truncated')}")
        else:
            st.write("No layout data for this template.")

    st.subheader("Build")
    job_name = st.text_input("Output name", value=f"{template_id}_{uuid.uuid4().hex[:8]}")
    build = st.button("Build STL", type="primary")

with colR:
    st.subheader("3D Preview")

    use_placeholder = st.checkbox("Use placeholder")
    open_external = st.checkbox("Open in external viewer")

    st.caption("Load STL")
    stl_files = [p for p in OUT_DIR.rglob("*.stl") if p.resolve() != PLACEHOLDER_STL]
    stl_files = sorted(stl_files, key=lambda p: p.stat().st_mtime, reverse=True)
    stl_labels = {}
    for p in stl_files:
        rel = p.relative_to(OUT_DIR)
        job = rel.parts[0] if rel.parts else ""
        mtime_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(p.stat().st_mtime))
        label = f"{job}/{p.name} ({mtime_str})"
        stl_labels[label] = p

    if stl_labels:
        selected_label = st.selectbox("Select STL", list(stl_labels.keys()))
        if st.button("Load selected"):
            st.session_state["last_stl_path"] = str(stl_labels[selected_label])
            st.session_state["preview_nonce"] += 1
    else:
        st.info("No STL files found in /out.")

    if st.button("Refresh preview"):
        st.session_state["preview_nonce"] += 1

    last = st.session_state.get("last_stl_path")
    preview_path = Path(last) if last else None
    if use_placeholder:
        preview_path = PLACEHOLDER_STL

    resolved_path = preview_path.resolve() if preview_path else None
    exists = resolved_path.exists() if resolved_path else False
    size = resolved_path.stat().st_size if exists else 0

    st.caption("Preview diagnostics")
    st.write(f"Exists: {exists}")
    st.write(f"Size: {size} bytes")
    if resolved_path:
        st.write(f"Path: {resolved_path}")
    else:
        st.write("Path: (none)")

    if resolved_path and exists:
        try:
            with resolved_path.open("r", encoding="utf-8", errors="replace") as f:
                lines = []
                for _ in range(5):
                    line = f.readline()
                    if not line:
                        break
                    lines.append(line.rstrip("\n"))
            st.code("\n".join(lines) if lines else "(file is empty)", language="text")
        except Exception as e:
            st.warning(f"Could not read preview lines: {e}")
    else:
        st.code("(no file to read)", language="text")

    if open_external:
        if resolved_path:
            st.write(f"Full path: {resolved_path}")
            if st.button("Open output folder"):
                subprocess.run(["open", str(resolved_path.parent)])
        else:
            st.info("No preview path available.")

    if resolved_path and exists and size > 0:
        try:
            stl_from_file(
                str(resolved_path),
                height=500,
                key=f"stl_{st.session_state['preview_nonce']}",
            )
        except Exception as e:
            st.error(f"streamlit_stl failed: {e}")
            try:
                mesh = trimesh.load_mesh(resolved_path, force="mesh")
                st.write(f"Bounds: {mesh.bounds.tolist()}")
                st.write(f"Extents: {mesh.extents.tolist()}")
            except Exception as mesh_err:
                st.warning(f"trimesh failed: {mesh_err}")
            if pv is None:
                st.warning("PyVista is not available for fallback rendering.")
            else:
                try:
                    pv_mesh = pv.read(str(resolved_path))
                    plotter = pv.Plotter(off_screen=True)
                    plotter.add_mesh(pv_mesh, color="#d0d0d0")
                    plotter.view_isometric()
                    img = plotter.screenshot(None, return_img=True, window_size=(800, 600))
                    plotter.close()
                    if img is not None:
                        st.image(img, caption="Fallback preview (PyVista)")
                    else:
                        st.warning("PyVista did not return an image.")
                except Exception as pv_err:
                    st.warning(f"PyVista failed: {pv_err}")
    else:
        st.info("No STL built yet. Click Build STL.")
    
st.subheader("Output")
if build:
    job_dir = OUT_DIR / job_name
    job_dir.mkdir(parents=True, exist_ok=True)

    spec_path = job_dir / "spec.json"
    stamp = int(time.time() * 1000)
    stl_path = job_dir / f"model_{stamp}.stl"
    log_path = job_dir / "logs.txt"

    spec_path.write_text(json.dumps(
        {"template_id": template_id, "params": params},
        indent=2
    ))

    try:
        logs = run_openscad(openscad_exe, scad_path, stl_path, params)
        st.session_state["last_stl_path"] = str(stl_path)
        st.session_state["preview_nonce"] += 1
        log_path.write_text(logs)

        report = validate_stl(stl_path)
        (job_dir / "report.json").write_text(json.dumps(report, indent=2))

        st.success("Build completed")
        st.code(logs[-2000:] if len(logs) > 2000 else logs)


        st.write("Validation report:")
        st.json(report)

        last_path = st.session_state.get("last_stl_path")
        if last_path:
            last_file = Path(last_path)
            if last_file.exists():
                with open(last_file, "rb") as f:
                    st.download_button("Download STL", f, file_name=last_file.name)

        if hasattr(st, "rerun"):
            st.rerun()
        else:
            st.experimental_rerun()

    except Exception as e:
        st.error(str(e))
        if log_path.exists():
            st.caption("Last logs:")
            st.code(log_path.read_text()[-2000:])

else:
    st.info("Click Build STL to generate output into /out/<job>/")
