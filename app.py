"""PromptToSTL — main Streamlit app."""
import json
import time
import uuid
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from src.core.catalog import list_templates, load_template
from src.core.runner import run_openscad
from src.core.template_builder import (
    EmblemSpec, TemplateSpec, TextSpec,
    coerce_template_spec, create_template, sanitize_template_id, spec_to_defaults,
)
from src.core.validate import validate_stl
from src.intent.router import route_intent
from src.intent.template_builder_agent import propose_template_spec
from src.ui.helpers import save_image_as_dat
from src.ui.params_panel import render_params, apply_text_layout
from src.ui.emblem_panel import render_emblem_section
from src.ui.lithophane_panel import render_lithophane_section
from src.ui.preview_panel import render_preview_panel

load_dotenv()

OUT_DIR = Path(__file__).resolve().parent / "out"
DEFAULT_OPENSCAD = "openscad"

st.set_page_config(page_title="PromptToSTL", layout="wide")
st.title("PromptToSTL")

# ── Session state defaults ────────────────────────────────────────────────────
for key, val in [("preview_nonce", 0), ("last_build_id", 0)]:
    st.session_state.setdefault(key, val)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Mode")
    app_mode = st.radio("", ["Build", "Create Template"], horizontal=True)
    if app_mode == "Build":
        openscad_exe = st.text_input("OpenSCAD path", value=DEFAULT_OPENSCAD)
        build_mode = st.radio("Input", ["Manual", "Describe it"], horizontal=True)


# ═══════════════════════════════════════════════════════════════════════════════
# CREATE TEMPLATE MODE
# ═══════════════════════════════════════════════════════════════════════════════
if app_mode == "Create Template":
    st.header("Template Builder")
    st.caption("Create a reusable parametric template from building blocks.")

    with st.expander("AI Proposal (describe the template)", expanded=False):
        desc = st.text_area("Describe the template", height=100, key="builder_desc")
        if st.button("Generate proposal"):
            try:
                st.session_state["builder_proposal"] = propose_template_spec(desc)
            except Exception as err:
                st.error(f"AI proposal failed: {err}")
        proposal = st.session_state.get("builder_proposal")
        if proposal:
            st.json(proposal)
            if st.button("Apply to form"):
                try:
                    spec = coerce_template_spec(proposal)
                    st.session_state["builder_defaults"] = spec_to_defaults(spec)
                    st.rerun()
                except Exception as err:
                    st.error(f"Could not apply: {err}")

    defaults = st.session_state.get("builder_defaults") or {}
    dt = defaults.get("text") or {}
    de = defaults.get("emblem") or {}
    shape_default = defaults.get("shape", "rounded_rect")

    with st.form("template_builder"):
        template_id_raw = st.text_input("Template ID", value=defaults.get("template_id", "custom_template"))
        label = st.text_input("Label", value=defaults.get("label", "Custom Template"))
        shape_label = st.selectbox(
            "Base shape", ["Rounded Rectangle", "Circle"],
            index=0 if shape_default == "rounded_rect" else 1,
        )
        if shape_label == "Rounded Rectangle":
            width = st.number_input("Width (mm)", value=float(defaults.get("width", 80.0)), min_value=10.0, max_value=400.0)
            height = st.number_input("Height (mm)", value=float(defaults.get("height", 30.0)), min_value=10.0, max_value=400.0)
            radius = st.number_input("Corner radius (mm)", value=float(defaults.get("radius", 5.0)), min_value=0.0, max_value=200.0)
            diameter = 0.0
        else:
            diameter = st.number_input("Diameter (mm)", value=float(defaults.get("diameter", 70.0)), min_value=10.0, max_value=400.0)
            width = height = radius = 0.0

        thickness = st.number_input("Thickness (mm)", value=float(defaults.get("thickness", 4.0)), min_value=1.0, max_value=50.0)

        include_text = st.checkbox("Include text region", value=bool(dt) if defaults else True)
        text_spec = None
        if include_text:
            max_lines = st.selectbox("Max lines", [1, 2, 3], index=max(0, min(2, int(dt.get("max_lines", 2)) - 1)))
            line1 = st.text_input("Default line 1", value=dt.get("line1", "YOUR TEXT"))
            line2 = st.text_input("Default line 2", value=dt.get("line2", "")) if max_lines >= 2 else ""
            line3 = st.text_input("Default line 3", value=dt.get("line3", "")) if max_lines >= 3 else ""
            text_size = st.number_input("Text size (mm)", value=float(dt.get("text_size", 12.0)), min_value=4.0, max_value=60.0)
            text_height = st.number_input("Text depth (mm)", value=float(dt.get("text_height", 1.2)), min_value=0.2, max_value=10.0)
            line_gap = st.number_input("Line gap (mm)", value=float(dt.get("line_gap", 8.0)), min_value=0.0, max_value=60.0)
            pad_x = st.number_input("Padding X (mm)", value=float(dt.get("pad_x", 6.0)), min_value=0.0, max_value=200.0)
            pad_y = st.number_input("Padding Y (mm)", value=float(dt.get("pad_y", 4.0)), min_value=0.0, max_value=200.0)
            align_opts = ["center", "left", "right"]
            text_align = st.selectbox("Text align", align_opts, index=align_opts.index(dt.get("text_align", "center")))
            emboss = 1 if st.selectbox("Text mode", ["Emboss", "Engrave"], index=0 if int(dt.get("emboss", 1)) == 1 else 1) == "Emboss" else 0
            text_spec = TextSpec(
                enabled=True, max_lines=max_lines, line1=line1, line2=line2, line3=line3,
                text_size=text_size, text_height=text_height, line_gap=line_gap,
                pad_x=pad_x, pad_y=pad_y, emboss=emboss, text_align=text_align,
            )

        include_emblem = st.checkbox("Include emblem region", value=bool(de) if defaults else False)
        emblem_spec = None
        if include_emblem:
            snap_opts = ["custom", "center", "left", "right", "above_text", "below_text",
                         "top_left", "top_right", "bottom_left", "bottom_right"]
            emblem_snap = st.selectbox("Emblem snap", snap_opts,
                                       index=snap_opts.index(de.get("snap", "custom")) if de.get("snap") in snap_opts else 0)
            emblem_autocenter = st.checkbox("Auto-center", value=bool(de.get("autocenter", 1)))
            emblem_scale = st.number_input("Emblem scale", value=float(de.get("scale", 0.25)), min_value=0.05, max_value=5.0)
            emblem_depth = st.number_input("Emblem depth (mm)", value=float(de.get("depth", 1.2)), min_value=0.2, max_value=10.0)
            emblem_x = st.number_input("Emblem X (mm)", value=float(de.get("x", 0.0)), min_value=-200.0, max_value=200.0)
            emblem_y = st.number_input("Emblem Y (mm)", value=float(de.get("y", 0.0)), min_value=-200.0, max_value=200.0)
            emblem_rot = st.number_input("Emblem rotation (°)", value=float(de.get("rot", 0.0)), min_value=-180.0, max_value=180.0)
            emblem_mode = 1 if st.selectbox("Emblem mode", ["Emboss", "Engrave"], index=0 if int(de.get("mode", 1)) == 1 else 1) == "Emboss" else 0
            emblem_spec = EmblemSpec(
                enabled=True, snap=emblem_snap, autocenter=1 if emblem_autocenter else 0,
                scale=emblem_scale, depth=emblem_depth, x=emblem_x, y=emblem_y, rot=emblem_rot, mode=emblem_mode,
            )

        submitted = st.form_submit_button("Create template")

    if submitted:
        tid = sanitize_template_id(template_id_raw)
        if not tid:
            st.error("Template ID cannot be empty.")
        else:
            spec = TemplateSpec(
                template_id=tid, label=label or tid,
                shape="rounded_rect" if shape_label == "Rounded Rectangle" else "circle",
                width=width, height=height, diameter=diameter, thickness=thickness, radius=radius,
                text=text_spec, emblem=emblem_spec,
            )
            try:
                final_id, out_dir = create_template(spec)
                st.session_state.pop("builder_defaults", None)
                st.success(f"Template created: custom/{final_id}")
                st.rerun()
            except FileExistsError:
                st.error(f"Template ID already exists: {tid}")
    st.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# BUILD MODE
# ═══════════════════════════════════════════════════════════════════════════════
templates = list_templates()
if not templates:
    st.error("No templates found. Add templates/<id>/schema.json and model.scad.")
    st.stop()

colL, colR = st.columns([1, 1], gap="large")
emblem_asset = emblem_asset_info = litho_asset = None

with colL:
    # ── Describe it mode ──────────────────────────────────────────────────────
    if build_mode == "Describe it":
        st.subheader("Describe it")
        description = st.text_area("Describe what you want to make", height=100)

        col_gen, col_regen = st.columns(2)
        with col_gen:
            if st.button("Generate proposal", type="primary"):
                template_map = {tid: load_template(tid)[0] for tid in templates}
                proposal = route_intent(description, template_map)
                st.session_state["intent_proposal"] = proposal
                st.rerun()
        with col_regen:
            if st.button("Regenerate") and st.session_state.get("intent_proposal"):
                template_map = {tid: load_template(tid)[0] for tid in templates}
                st.session_state["intent_proposal"] = route_intent(description, template_map)
                st.rerun()

        proposal = st.session_state.get("intent_proposal")
        if proposal:
            ptid = proposal.get("template_id", "")
            pschema, _ = load_template(ptid) if ptid in templates else (None, None)
            label_str = pschema.get("label", ptid) if pschema else ptid
            st.write(f"**Template:** {label_str}")
            st.json(proposal.get("params", {}))
            if proposal.get("notes"):
                st.info(proposal["notes"])
            if st.button("Apply to form"):
                st.session_state.update(
                    intent_template_id=proposal.get("template_id"),
                    intent_params=proposal.get("params", {}),
                    template_select=proposal.get("template_id"),
                    pending_build=True,
                )
                st.rerun()

    # ── Template selector ────────────────────────────────────────────────────
    st.subheader("Template")
    intent_tid = st.session_state.get("intent_template_id")
    if "template_select" not in st.session_state and intent_tid in templates:
        st.session_state["template_select"] = intent_tid

    template_id = st.selectbox("Choose template", templates, key="template_select")
    schema, scad_path = load_template(template_id)
    st.caption(schema.get("label", template_id))

    is_lithophane = schema.get("lithophane_mode", False)
    is_multicolor = schema.get("multicolor_mode", False)

    # ── Lithophane image upload ───────────────────────────────────────────────
    if is_lithophane:
        intent_params_raw = st.session_state.get("intent_params") if intent_tid == template_id else None
        params = render_params(schema, template_id, intent_params_raw)
        params, litho_asset = render_lithophane_section(params)

    else:
        # ── Regular template parameters ───────────────────────────────────────
        st.subheader("Parameters")
        intent_params_raw = st.session_state.get("intent_params") if intent_tid == template_id else None
        params = render_params(schema, template_id, intent_params_raw)
        params = apply_text_layout(schema, template_id, params)

        # ── Emblem section ────────────────────────────────────────────────────
        if "emblem_enabled" in schema.get("params", {}):
            st.subheader("Emblem")
            params, emblem_asset, emblem_asset_info = render_emblem_section(schema, template_id, params)

        # Emblem snap position calculation
        emblem_snap = params.get("emblem_snap") if isinstance(params.get("emblem_snap"), str) else None
        if emblem_snap and emblem_snap != "custom":
            box_w = float(params.get("text_box_w", 0.0))
            box_h = float(params.get("text_box_h", 0.0))
            box_off_x = float(params.get("text_box_offset_x", 0.0))
            box_off_y = float(params.get("text_box_offset_y", 0.0))
            m = min(box_w, box_h) * 0.1 if min(box_w, box_h) > 0 else 0.0
            snap_map = {
                "center": (0.0, 0.0), "left": (-box_w/2+m, 0.0), "right": (box_w/2-m, 0.0),
                "above_text": (0.0, box_h/2-m), "below_text": (0.0, -box_h/2+m),
                "top_left": (-box_w/2+m, box_h/2-m), "top_right": (box_w/2-m, box_h/2-m),
                "bottom_left": (-box_w/2+m, -box_h/2+m), "bottom_right": (box_w/2-m, -box_h/2+m),
            }
            sx, sy = snap_map.get(emblem_snap, (0.0, 0.0))
            params["emblem_x"] = sx + box_off_x
            params["emblem_y"] = sy + box_off_y

    # ── Multicolor info ───────────────────────────────────────────────────────
    if is_multicolor:
        base_thick = float(params.get("base_thick", 2.0))
        st.info(f"**2-Color Print:** Change filament at **{base_thick:.1f} mm** layer height.\n\n"
                f"Color A = base plate · Color B = raised text/emblem")

    # ── Print note ────────────────────────────────────────────────────────────
    print_note = schema.get("print_note", "")
    if print_note and not is_multicolor:
        st.info(print_note.format(**params))

    # ── Build ─────────────────────────────────────────────────────────────────
    st.subheader("Build")
    job_name = st.text_input("Output name", value=f"{template_id.replace('/', '_')}_{uuid.uuid4().hex[:8]}")
    build = st.button("Build STL", type="primary")
    if build:
        st.session_state["build_requested"] = True

with colR:
    render_preview_panel(st.session_state["last_build_id"])


# ═══════════════════════════════════════════════════════════════════════════════
# BUILD EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════
build_requested = st.session_state.pop("build_requested", False) or st.session_state.pop("pending_build", False)
if build_requested:
    job_dir = OUT_DIR / job_name
    job_dir.mkdir(parents=True, exist_ok=True)

    stamp = int(time.time() * 1000)
    stl_path = job_dir / f"model_{stamp}.stl"
    log_path = job_dir / "logs.txt"

    # Handle emblem asset
    if "emblem_enabled" in schema.get("params", {}) and emblem_asset is not None:
        if emblem_asset.get("kind") == "svg":
            ep = job_dir / "emblem.svg"
            ep.write_bytes(emblem_asset["bytes"])
            params.update(emblem_kind="svg", emblem_enabled=1, emblem_path=str(ep.resolve()))
        elif emblem_asset.get("kind") == "heightmap":
            ep = job_dir / "emblem.dat"
            size = save_image_as_dat(
                emblem_asset["bytes"], ep,
                max_size=int(emblem_asset.get("max_size", 256)),
                invert=bool(emblem_asset.get("invert", False)),
            )
            if size is None:
                st.error("Failed to process image emblem. Check Pillow is installed.")
                st.stop()
            params.update(emblem_kind="heightmap", emblem_enabled=1, emblem_path=str(ep.resolve()))

    # Handle lithophane image asset
    if is_lithophane and litho_asset is not None:
        lp = job_dir / "image.dat"
        size = save_image_as_dat(
            litho_asset["bytes"], lp,
            max_size=int(litho_asset.get("max_size", 192)),
            invert=bool(litho_asset.get("invert", False)),
        )
        if size is None:
            st.error("Failed to process lithophane image. Check Pillow is installed.")
            st.stop()
        w, h = size
        params.update(dat_file=str(lp.resolve()), dat_w=w, dat_h=h)

    # Save spec
    (job_dir / "spec.json").write_text(
        json.dumps({"template_id": template_id, "params": params}, indent=2)
    )

    try:
        st.subheader("Output")
        with st.spinner("Running OpenSCAD…"):
            logs = run_openscad(openscad_exe, scad_path, stl_path, params)

        log_path.write_text(logs)
        report = validate_stl(stl_path)
        (job_dir / "report.json").write_text(json.dumps(report, indent=2))

        st.session_state.update(
            last_stl_path=str(stl_path),
            last_build_id=st.session_state["last_build_id"] + 1,
            preview_nonce=st.session_state["preview_nonce"] + 1,
        )

        st.success("Build complete!")

        with st.expander("Build log"):
            st.code(logs[-3000:] if len(logs) > 3000 else logs)
        with st.expander("Validation report"):
            st.json(report)

        last_file = Path(st.session_state["last_stl_path"])
        if last_file.exists():
            st.download_button(
                "Download STL",
                data=last_file.read_bytes(),
                file_name=last_file.name,
                mime="application/sla",
            )

        st.rerun()

    except Exception as e:
        st.error(str(e))
        if log_path.exists():
            with st.expander("Error log"):
                st.code(log_path.read_text()[-3000:])
else:
    if build_requested is False:
        st.info("Configure your template on the left, then click **Build STL**.")
