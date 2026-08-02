import json
import os
import shutil
import subprocess
import sys
import time
import uuid
import zipfile
from pathlib import Path
import streamlit as st

from dotenv import load_dotenv

from src.core.catalog import list_templates, load_template
from src.core.image_prep import prepare_lithophane_image
from src.core.layout import apply_text_layout, eval_expr
from src.core.litho_mesh import build_litho_mesh
from src.core.qr import make_qr_png
from src.core.runner import run_openscad, supports_manifold
from src.core.template_builder import (
    EmblemSpec,
    TemplateSpec,
    TextSpec,
    coerce_template_spec,
    create_template,
    sanitize_template_id,
    spec_to_defaults,
)
from src.core.validate import validate_stl
from src.intent.router import repair_params, route_intent
from src.intent.template_builder_agent import propose_template_spec
from streamlit_stl import stl_from_file
try:
    import pyvista as pv
except Exception:
    pv = None


OUT_DIR = Path(__file__).resolve().parent / "out"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
PLACEHOLDER_STL = TEMPLATES_DIR / "placeholder.stl"
TEXT_MARGIN = 0.9
MAX_KEPT_JOBS = 20   # cloud hosts have small ephemeral disks

load_dotenv()

# Streamlit Community Cloud supplies API keys via st.secrets rather than .env;
# mirror them into the environment so src/intent/router.py works either way.
try:
    for _key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "LLM_PROVIDER"):
        if _key in st.secrets and not os.environ.get(_key):
            os.environ[_key] = str(st.secrets[_key])
except Exception:
    pass  # no secrets.toml locally — .env already handled it


def prune_jobs(keep: int = MAX_KEPT_JOBS) -> None:
    """Keep only the newest `keep` job folders in out/ (hosted disks are small
    and ephemeral; users download the STLs they want to keep)."""
    if not OUT_DIR.exists():
        return
    jobs = [d for d in OUT_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")]
    for stale in sorted(jobs, key=lambda d: d.stat().st_mtime, reverse=True)[keep:]:
        shutil.rmtree(stale, ignore_errors=True)


def detect_openscad() -> str:
    """Best-guess OpenSCAD executable for this machine."""
    candidates = [
        shutil.which("openscad"),
        "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD",
        str(Path.home() / "Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"),
        "/usr/bin/openscad",
        "/usr/local/bin/openscad",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    return "openscad"


@st.cache_data(show_spinner=False)
def engine_status(exe: str) -> dict:
    """Probe the OpenSCAD executable once (cached per path)."""
    try:
        p = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=10)
        version = (p.stdout + p.stderr).strip().replace("OpenSCAD version ", "")
        return {"ok": True, "version": version, "manifold": supports_manifold(exe)}
    except Exception:
        return {"ok": False, "version": "", "manifold": False}


def load_jobs(limit: int = 8) -> list[dict]:
    """Recent builds from out/*/spec.json, newest first."""
    jobs = []
    if not OUT_DIR.exists():
        return jobs
    for spec_file in OUT_DIR.glob("*/spec.json"):
        try:
            data = json.loads(spec_file.read_text())
        except Exception:
            continue
        stls = sorted(spec_file.parent.glob("*.stl"),
                      key=lambda p: p.stat().st_mtime, reverse=True)
        if not stls:
            continue
        jobs.append({
            "job": spec_file.parent.name,
            "template_id": data.get("template_id", ""),
            "params": data.get("params", {}),
            "stl": stls[0],
            "mtime": stls[0].stat().st_mtime,
        })
    return sorted(jobs, key=lambda j: j["mtime"], reverse=True)[:limit]


st.set_page_config(page_title="PromptToSTL", page_icon="🧱", layout="wide")

# Cap thumbnail size as a backstop and tighten card padding, so the gallery
# stays compact when Streamlit stacks the columns on a phone.
st.markdown(
    """
    <style>
      [data-testid="stImage"] img { max-height: 150px; object-fit: contain; }
      [data-testid="stVerticalBlockBorderWrapper"] { padding-bottom: .25rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

if "preview_nonce" not in st.session_state:
    st.session_state["preview_nonce"] = 0

templates = list_templates()
schemas = {}
for tid in templates:
    schemas[tid], _ = load_template(tid)

with st.sidebar:
    st.header("🧱 PromptToSTL")
    st.caption("Photos and text → 3D-printable STL files")
    app_mode = st.radio("", ["Build", "Create Template"], horizontal=True,
                        label_visibility="collapsed")
    mode = "Manual"
    if app_mode == "Build":
        mode = st.radio("Mode", ["Manual", "Describe it"], horizontal=True)
    st.divider()
    with st.expander("⚙️ Settings", expanded=False):
        if "openscad_exe" not in st.session_state:
            st.session_state["openscad_exe"] = detect_openscad()
        openscad_exe = st.text_input("OpenSCAD executable",
                                     key="openscad_exe",
                                     help="Only needed for text templates — photo "
                                          "lithophanes build without OpenSCAD.")
        status = engine_status(openscad_exe)
        if status["ok"]:
            st.caption(f"✅ OpenSCAD {status['version']}")
            if status["manifold"]:
                st.caption("⚡ Manifold engine — fast renders")
            else:
                st.caption("🐢 Classic engine — an [OpenSCAD snapshot]"
                           "(https://openscad.org/downloads.html#snapshots) "
                           "renders 10-100× faster")
        else:
            st.warning("OpenSCAD not found. Text templates need it "
                       "([download](https://openscad.org/downloads.html)) — "
                       "photo lithophanes still work!")
    st.caption(f"{len(templates)} designs · outputs in `out/`")

openscad_exe = st.session_state.get("openscad_exe", "openscad")

st.title("PromptToSTL")
st.caption("Turn photos and text into 3D-printable gifts in seconds.")

if not templates:
    st.error("No templates found. Add templates/<id>/schema.json and model.scad")
    st.stop()

# ── Create Template mode ─────────────────────────────────────────────────────
if app_mode == "Create Template":
    st.subheader("🛠️ Template Builder")
    st.caption("Create a reusable parametric design from building blocks — "
               "it then appears in the gallery like any other template.")

    with st.expander("✨ Describe it and let AI draft the template", expanded=False):
        desc = st.text_area("Describe the template", height=100, key="builder_desc",
                            placeholder="e.g. A 90 mm round badge with two lines of "
                                        "raised text and a logo in the centre")
        if st.button("Generate proposal"):
            try:
                st.session_state["builder_proposal"] = propose_template_spec(desc)
            except Exception as err:
                st.error(f"AI proposal failed: {err}")
        proposal = st.session_state.get("builder_proposal")
        if proposal:
            st.json(proposal, expanded=False)
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
        template_id_raw = st.text_input("Template ID",
                                        value=defaults.get("template_id", "custom_template"))
        label = st.text_input("Label", value=defaults.get("label", "Custom Template"))
        shape_label = st.selectbox("Base shape", ["Rounded Rectangle", "Circle"],
                                   index=0 if shape_default == "rounded_rect" else 1)
        sc1, sc2 = st.columns(2)
        if shape_label == "Rounded Rectangle":
            width = sc1.number_input("Width (mm)", value=float(defaults.get("width", 80.0)),
                                     min_value=10.0, max_value=400.0)
            height = sc2.number_input("Height (mm)", value=float(defaults.get("height", 30.0)),
                                      min_value=10.0, max_value=400.0)
            radius = sc1.number_input("Corner radius (mm)", value=float(defaults.get("radius", 5.0)),
                                      min_value=0.0, max_value=200.0)
            diameter = 0.0
        else:
            diameter = sc1.number_input("Diameter (mm)", value=float(defaults.get("diameter", 70.0)),
                                        min_value=10.0, max_value=400.0)
            width = height = radius = 0.0
        thickness = sc2.number_input("Thickness (mm)", value=float(defaults.get("thickness", 4.0)),
                                     min_value=1.0, max_value=50.0)

        include_text = st.checkbox("Include text region", value=bool(dt) if defaults else True)
        text_spec = None
        if include_text:
            max_lines = st.selectbox("Max lines", [1, 2, 3],
                                     index=max(0, min(2, int(dt.get("max_lines", 2)) - 1)))
            line1 = st.text_input("Default line 1", value=dt.get("line1", "YOUR TEXT"))
            line2 = st.text_input("Default line 2", value=dt.get("line2", "")) if max_lines >= 2 else ""
            line3 = st.text_input("Default line 3", value=dt.get("line3", "")) if max_lines >= 3 else ""
            tc1, tc2 = st.columns(2)
            text_size = tc1.number_input("Text size (mm)", value=float(dt.get("text_size", 12.0)),
                                         min_value=4.0, max_value=60.0)
            text_height = tc2.number_input("Text depth (mm)", value=float(dt.get("text_height", 1.2)),
                                           min_value=0.2, max_value=10.0)
            line_gap = tc1.number_input("Line gap (mm)", value=float(dt.get("line_gap", 8.0)),
                                        min_value=0.0, max_value=60.0)
            pad_x = tc2.number_input("Padding X (mm)", value=float(dt.get("pad_x", 6.0)),
                                     min_value=0.0, max_value=200.0)
            pad_y = tc1.number_input("Padding Y (mm)", value=float(dt.get("pad_y", 4.0)),
                                     min_value=0.0, max_value=200.0)
            align_opts = ["center", "left", "right"]
            text_align = tc2.selectbox("Text align", align_opts,
                                       index=align_opts.index(dt.get("text_align", "center")))
            emboss = 1 if st.selectbox(
                "Text mode", ["Emboss", "Engrave"],
                index=0 if int(dt.get("emboss", 1)) == 1 else 1) == "Emboss" else 0
            text_spec = TextSpec(
                enabled=True, max_lines=max_lines, line1=line1, line2=line2, line3=line3,
                text_size=text_size, text_height=text_height, line_gap=line_gap,
                pad_x=pad_x, pad_y=pad_y, emboss=emboss, text_align=text_align,
            )

        include_emblem = st.checkbox("Include emblem region",
                                     value=bool(de) if defaults else False)
        emblem_spec = None
        if include_emblem:
            snap_opts = ["custom", "center", "left", "right", "above_text", "below_text",
                         "top_left", "top_right", "bottom_left", "bottom_right"]
            ec1, ec2 = st.columns(2)
            emblem_snap = ec1.selectbox(
                "Emblem snap", snap_opts,
                index=snap_opts.index(de.get("snap", "custom")) if de.get("snap") in snap_opts else 0)
            emblem_autocenter = ec2.checkbox("Auto-center", value=bool(de.get("autocenter", 1)))
            emblem_scale = ec1.number_input("Emblem scale", value=float(de.get("scale", 0.25)),
                                            min_value=0.05, max_value=5.0)
            emblem_depth = ec2.number_input("Emblem depth (mm)", value=float(de.get("depth", 1.2)),
                                            min_value=0.2, max_value=10.0)
            emblem_x = ec1.number_input("Emblem X (mm)", value=float(de.get("x", 0.0)),
                                        min_value=-200.0, max_value=200.0)
            emblem_y = ec2.number_input("Emblem Y (mm)", value=float(de.get("y", 0.0)),
                                        min_value=-200.0, max_value=200.0)
            emblem_rot = ec1.number_input("Emblem rotation (°)", value=float(de.get("rot", 0.0)),
                                          min_value=-180.0, max_value=180.0)
            emblem_mode = 1 if ec2.selectbox(
                "Emblem mode", ["Emboss", "Engrave"],
                index=0 if int(de.get("mode", 1)) == 1 else 1) == "Emboss" else 0
            emblem_spec = EmblemSpec(
                enabled=True, snap=emblem_snap, autocenter=1 if emblem_autocenter else 0,
                scale=emblem_scale, depth=emblem_depth, x=emblem_x, y=emblem_y,
                rot=emblem_rot, mode=emblem_mode,
            )

        submitted = st.form_submit_button("Create template", type="primary")

    if submitted:
        tid = sanitize_template_id(template_id_raw)
        if not tid:
            st.error("Template ID cannot be empty.")
        else:
            spec = TemplateSpec(
                template_id=tid, label=label or tid,
                shape="rounded_rect" if shape_label == "Rounded Rectangle" else "circle",
                width=width, height=height, diameter=diameter,
                thickness=thickness, radius=radius,
                text=text_spec, emblem=emblem_spec,
            )
            try:
                final_id, _out_dir = create_template(spec)
                st.session_state.pop("builder_defaults", None)
                st.success(f"Template created: custom/{final_id} — "
                           f"switch to **Build** to use it.")
                st.rerun()
            except FileExistsError:
                st.error(f"Template ID already exists: {tid}")
    st.stop()

if "template_select" not in st.session_state:
    st.session_state["template_select"] = templates[0]
if st.session_state["template_select"] not in templates:
    st.session_state["template_select"] = templates[0]
if "show_gallery" not in st.session_state:
    st.session_state["show_gallery"] = True

colL, colR = st.columns([1, 1], gap="large")
uploaded_svg = None

with colL:
    if mode == "Describe it":
        st.subheader("✨ Describe it")
        has_ai_key = bool(os.environ.get("OPENAI_API_KEY")
                          or os.environ.get("ANTHROPIC_API_KEY"))
        if not has_ai_key:
            st.info("Add OPENAI_API_KEY or ANTHROPIC_API_KEY to your `.env` "
                    "to use AI mode.")
        chat = st.session_state.setdefault("chat", [])
        for msg in chat:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        chat_prompt = st.chat_input(
            "Describe your object, or refine the current one…",
            disabled=not has_ai_key,
        )
        if chat_prompt:
            chat.append({"role": "user", "content": chat_prompt})
            current = None
            if st.session_state.get("intent_template_id") in schemas:
                current = {
                    "template_id": st.session_state["intent_template_id"],
                    "params": st.session_state.get("intent_params", {}),
                }
            try:
                proposal = route_intent(chat_prompt, schemas, current=current)
                tid = proposal["template_id"]
                pschema = schemas.get(tid, {})
                st.session_state["intent_template_id"] = tid
                st.session_state["intent_params"] = proposal.get("params", {})
                st.session_state["template_select"] = tid
                st.session_state["show_gallery"] = False
                verb = "Updated" if current and current["template_id"] == tid else "Set up"
                reply = (f"{verb} **{pschema.get('icon', '')} "
                         f"{pschema.get('label', tid)}** — the form below has "
                         f"the new settings; tweak anything you like, then Build.")
                notes = proposal.get("notes", "")
                if notes:
                    reply += f"\n\n_{notes}_"
                chat.append({"role": "assistant", "content": reply})
            except Exception as e:
                chat.append({"role": "assistant",
                             "content": f"Sorry, that didn't work: {e}"})
            st.rerun()

        if chat and st.button("↺ Reset chat"):
            st.session_state["chat"] = []
            st.session_state.pop("intent_template_id", None)
            st.session_state.pop("intent_params", None)
            st.rerun()
        st.divider()

    # ── Step 1 · Choose a design ─────────────────────────────────────────
    template_id = st.session_state["template_select"]

    if st.session_state["show_gallery"]:
        st.subheader("1 · Choose a design")
        query = st.text_input(
            "Search designs", placeholder=f"Search {len(templates)} designs — try 'photo', 'tag', 'gift'…",
            label_visibility="collapsed",
        ).strip().lower()

        def _matches(tid: str) -> bool:
            if not query:
                return True
            s = schemas[tid]
            hay = " ".join([tid, s.get("label", ""), s.get("description", ""),
                            s.get("category", "")]).lower()
            return all(word in hay for word in query.split())

        by_cat: dict[str, list] = {}
        for tid in templates:
            if not _matches(tid):
                continue
            s = schemas[tid]
            by_cat.setdefault(s.get("category", "More"), []).append(tid)
        if not by_cat:
            st.info(f"No designs match “{query}”.")
        for cat in sorted(by_cat):
            st.markdown(f"**{cat}**")
            items = by_cat[cat]
            for row in range(0, len(items), 3):
                cols = st.columns(3)
                for col, tid in zip(cols, items[row:row + 3]):
                    s = schemas[tid]
                    selected = tid == template_id
                    with col, st.container(border=True):
                        thumb = TEMPLATES_DIR / tid / "thumb.png"
                        if thumb.exists():
                            # Fixed pixel width, not container width: Streamlit
                            # stacks columns on phones, and a full-width thumb
                            # would make each card fill the screen.
                            st.image(str(thumb), width=150)
                        else:
                            st.markdown(
                                f"<div style='font-size:2rem;line-height:1'>"
                                f"{s.get('icon', '📦')}</div>",
                                unsafe_allow_html=True,
                            )
                        st.markdown(f"{s.get('icon', '')} **{s.get('label', tid)}**")
                        st.caption(s.get("description", ""))
                        if st.button(
                            "✓ Selected" if selected else "Select",
                            key=f"pick_{tid}",
                            type="primary" if selected else "secondary",
                            use_container_width=True,
                        ):
                            st.session_state["template_select"] = tid
                            st.session_state["show_gallery"] = False
                            st.rerun()
    else:
        s = schemas[template_id]
        hc1, hc2 = st.columns([4, 1])
        hc1.subheader(f"{s.get('icon', '')} {s.get('label', template_id)}")
        hc1.caption(s.get("description", ""))
        if hc2.button("Change design"):
            st.session_state["show_gallery"] = True
            st.rerun()

    template_id = st.session_state["template_select"]
    schema, scad_path = load_template(template_id)
    is_native = bool(schema.get("native_litho"))

    # ── Step 2 · Customize ───────────────────────────────────────────────
    st.subheader("2 · Customize")
    params = {}
    intent_template_id = st.session_state.get("intent_template_id")
    intent_params = (st.session_state.get("intent_params")
                     if intent_template_id == template_id else None)

    def render_param(k, spec):
        default = spec.get("default")
        if intent_params and k in intent_params:
            default = intent_params.get(k)
        label = spec.get("label", k)
        unit = spec.get("unit")
        disp = f"{label} ({unit})" if unit else label
        help_txt = spec.get("help")
        t = spec["type"]
        if t == "string":
            options = spec.get("options")
            if options:
                idx = options.index(str(default)) if default in options else 0
                return st.selectbox(disp, options, index=idx, help=help_txt)
            return st.text_input(disp, value=str(default) if default is not None else "",
                                 help=help_txt)
        if t in {"int", "integer"}:
            lo = int(spec.get("min", -10**9))
            hi = int(spec.get("max", 10**9))
            try:
                val = min(hi, max(lo, int(float(default))))
            except (TypeError, ValueError):
                val = lo
            return st.number_input(disp, value=val, step=1,
                                   min_value=lo, max_value=hi, help=help_txt)
        if t == "number":
            lo = float(spec.get("min", -1e9))
            hi = float(spec.get("max", 1e9))
            try:
                val = min(hi, max(lo, float(default)))
            except (TypeError, ValueError):
                val = lo
            if spec.get("widget") == "slider" and "min" in spec and "max" in spec:
                return st.slider(disp, lo, hi, val, help=help_txt)
            return st.number_input(disp, value=val,
                                   min_value=lo, max_value=hi, help=help_txt)
        st.warning(f"Unknown type {t} for {k}")
        return default

    ADVANCED_PREFIXES = ("text_box_", "text_margin_", "text_block_", "hole")
    INLINE_GROUPS = ["Text", "Dimensions", "Style"]
    grouped: dict[str, list] = {}
    for k, spec in schema["params"].items():
        if spec.get("hidden"):
            continue
        g = spec.get("group")
        if g is None:
            if k.startswith("emblem_"):
                g = "Emblem"
            elif k.startswith(ADVANCED_PREFIXES) or k in {"debug", "holes"}:
                g = "Advanced"
            else:
                g = "main"
        grouped.setdefault(g, []).append((k, spec))

    for k, spec in grouped.get("main", []):
        params[k] = render_param(k, spec)

    for gname in INLINE_GROUPS:
        entries = grouped.get(gname, [])
        if not entries:
            continue
        st.markdown(f"**{gname}**")
        if gname == "Dimensions" and len(entries) > 1:
            cols = st.columns(2)
            for i, (k, spec) in enumerate(entries):
                with cols[i % 2]:
                    params[k] = render_param(k, spec)
        else:
            for k, spec in entries:
                params[k] = render_param(k, spec)

    if grouped.get("Emblem"):
        with st.expander("Emblem settings", expanded=False):
            for k, spec in grouped["Emblem"]:
                params[k] = render_param(k, spec)

    if grouped.get("Advanced"):
        with st.expander("Advanced", expanded=False):
            for k, spec in grouped["Advanced"]:
                params[k] = render_param(k, spec)

    # ── Photo controls (lithophane templates) ────────────────────────────
    photo_detail = 300 if is_native else 200
    photo_brightness = 1.0
    photo_contrast = 1.0
    photo_gamma = 1.0
    photo_invert = True
    if schema.get("accepts_image"):
        st.markdown("**Photo**")
        uploaded_photo = st.file_uploader(
            "Upload photo (JPG, PNG, HEIC)", type=["jpg", "jpeg", "png", "heic"]
        )
        photo_detail = st.slider(
            "Photo detail (px)",
            min_value=100,
            max_value=500 if is_native else 400,
            value=300 if is_native else 200,
            step=25,
            help="Heightmap resolution — higher is sharper. "
                 + ("Fast at any setting for this design."
                    if is_native else
                    "Higher values slow the OpenSCAD render a lot; 200 px is a "
                    "good balance."),
        )
        pc1, pc2 = st.columns(2)
        with pc1:
            photo_brightness = st.slider("Brightness", 0.5, 2.0, 1.0, 0.05)
            photo_contrast = st.slider("Contrast", 0.5, 2.0, 1.0, 0.05)
        with pc2:
            photo_gamma = st.slider("Gamma", 0.4, 2.5, 1.0, 0.05)
            photo_invert = st.checkbox(
                "Invert (backlit)", value=True,
                help="Keep on for lithophanes: dark image areas become thick "
                     "plastic so they look dark when backlit.",
            )
        if uploaded_photo is not None:
            preview_dir = OUT_DIR / ".preview"
            preview_dir.mkdir(parents=True, exist_ok=True)
            preview_png = preview_dir / "photo_preview.png"
            try:
                prepare_lithophane_image(
                    uploaded_photo.getvalue(), preview_png,
                    max_px=photo_detail,
                    brightness=photo_brightness,
                    contrast=photo_contrast,
                    gamma=photo_gamma,
                    invert=photo_invert,
                )
                ic1, ic2 = st.columns(2)
                ic1.image(uploaded_photo, caption="Original")
                ic2.image(str(preview_png), caption="Heightmap (bright = thicker)")
            except Exception as e:
                st.warning(f"Could not preview photo: {e}")
    else:
        uploaded_photo = None

    if schema.get("emblem_support"):
        st.markdown("**Emblem**")
        uploaded_svg = st.file_uploader("SVG emblem", type=["svg"])

    # ── Text layout (shared with scripts/render_thumbnails.py) ───────────
    layout_debug = apply_text_layout(schema, params, margin=TEXT_MARGIN)
    if layout_debug:
        if layout_debug.get("warning"):
            st.warning(layout_debug["warning"])
        elif layout_debug.get("truncated"):
            st.warning("Text was truncated to fit the text box.")

    emblem_snap = params.get("emblem_snap") if isinstance(params.get("emblem_snap"), str) else None
    if emblem_snap and emblem_snap != "custom":
        # Use the text area computed from the schema's text_box expressions.
        # (Older schemas duplicated this as text_box_* params the user had to
        # keep in sync by hand; those are now hidden and only used as a
        # fallback for templates without a text_box.)
        box_w = float((layout_debug or {}).get("box_w") or params.get("text_box_w", 0.0))
        box_h = float((layout_debug or {}).get("box_h") or params.get("text_box_h", 0.0))
        box_off_x = float(params.get("text_box_offset_x", 0.0))
        box_off_y = float(params.get("text_box_offset_y", 0.0))
        margin = min(box_w, box_h) * 0.1 if min(box_w, box_h) > 0 else 0.0

        def snap_pos(kind):
            if kind == "center":
                return 0.0, 0.0
            if kind == "left":
                return -box_w / 2 + margin, 0.0
            if kind == "right":
                return box_w / 2 - margin, 0.0
            if kind == "above_text":
                return 0.0, box_h / 2 - margin
            if kind == "below_text":
                return 0.0, -box_h / 2 + margin
            if kind == "top_left":
                return -box_w / 2 + margin, box_h / 2 - margin
            if kind == "top_right":
                return box_w / 2 - margin, box_h / 2 - margin
            if kind == "bottom_left":
                return -box_w / 2 + margin, -box_h / 2 + margin
            if kind == "bottom_right":
                return box_w / 2 - margin, -box_h / 2 + margin
            return 0.0, 0.0

        snap_x, snap_y = snap_pos(emblem_snap)
        autocenter = int(params.get("emblem_autocenter", 1)) == 1
        if emblem_snap == "center" and autocenter:
            snap_x, snap_y = 0.0, 0.0
        params["emblem_x"] = snap_x + box_off_x
        params["emblem_y"] = snap_y + box_off_y

    if layout_debug:
        with st.expander("Layout debug", expanded=False):
            st.write(f"box_w: {layout_debug.get('box_w')}")
            st.write(f"box_h: {layout_debug.get('box_h')}")
            st.write(f"offset_x: {params.get('offset_x')}")
            st.write(f"offset_y: {params.get('offset_y')}")
            st.write(f"text_size: {layout_debug.get('text_size')}")
            st.write(f"lines: {layout_debug.get('lines')}")
            st.write(f"offsets_y: {layout_debug.get('offsets_y')}")
            st.write(f"warning: {layout_debug.get('warning')}")
            st.write(f"truncated: {layout_debug.get('truncated')}")

    # ── Step 3 · Build ───────────────────────────────────────────────────
    st.subheader("3 · Build")
    job_name = st.text_input("Output name", value=f"{template_id}_{uuid.uuid4().hex[:8]}")
    export_parts = False
    if schema.get("multipart") and int(params.get("emboss", 1) or 0) == 1:
        export_parts = st.checkbox(
            "🎨 Also export color parts (base + text STLs)",
            help="Two extra STLs for multi-color printing: import both into "
                 "your slicer as one object and give each its own "
                 "color/filament (AMS/MMU) — or print them as a reference "
                 "for a manual filament swap.",
        )
    if is_native:
        st.caption("⚡ Builds in seconds — no OpenSCAD needed.")
    elif schema.get("accepts_image"):
        st.caption("🕐 Renders with OpenSCAD — typically 30 s to a few minutes.")
    else:
        st.caption("🕐 Renders with OpenSCAD — typically 5–30 seconds.")
    build = st.button("🛠️ Build STL", type="primary", use_container_width=True)
    if build:
        st.session_state["build_requested"] = True

with colR:
    st.subheader("3D Preview")

    # Auto-load the newest STL if nothing is selected yet
    if not st.session_state.get("last_stl_path"):
        stls = [p for p in OUT_DIR.rglob("*.stl") if p.resolve() != PLACEHOLDER_STL]
        stls = sorted(stls, key=lambda p: p.stat().st_mtime, reverse=True)
        if stls:
            st.session_state["last_stl_path"] = str(stls[0])

    oc1, oc2, oc3 = st.columns([1, 1, 1])
    preview_color = oc1.color_picker("Color", "#E8590C")
    preview_material = oc2.selectbox("Material", ["material", "flat", "wireframe"], index=0)
    preview_spin = oc3.checkbox("Spin", value=False)

    last = st.session_state.get("last_stl_path")
    preview_path = Path(last) if last else None

    resolved_path = preview_path.resolve() if preview_path else None
    exists = resolved_path.exists() if resolved_path else False
    size = resolved_path.stat().st_size if exists else 0

    if resolved_path and exists and size > 0:
        try:
            stl_from_file(
                str(resolved_path),
                height=420,
                color=preview_color,
                material=preview_material,
                auto_rotate=preview_spin,
                key=f"stl_{st.session_state['preview_nonce']}",
            )
            st.caption(f"Showing: {resolved_path.parent.name}/{resolved_path.name}")
        except Exception as e:
            st.error(f"Viewer failed: {e}")
            if pv is not None:
                try:
                    pv_mesh = pv.read(str(resolved_path))
                    plotter = pv.Plotter(off_screen=True)
                    plotter.add_mesh(pv_mesh, color="#d0d0d0")
                    plotter.view_isometric()
                    img = plotter.screenshot(None, return_img=True, window_size=(800, 600))
                    plotter.close()
                    if img is not None:
                        st.image(img, caption="Fallback preview (PyVista)")
                except Exception as pv_err:
                    st.warning(f"PyVista fallback failed: {pv_err}")
    else:
        st.info("Your 3D preview will appear here after the first build.")

    if st.button("🔄 Refresh preview"):
        st.session_state["preview_nonce"] += 1
        st.rerun()

    with st.expander("Diagnostics", expanded=False):
        st.write(f"Exists: {exists}")
        st.write(f"Size: {size} bytes")
        st.write(f"Path: {resolved_path if resolved_path else '(none)'}")
        if st.checkbox("Show placeholder model"):
            st.session_state["last_stl_path"] = str(PLACEHOLDER_STL)
            st.session_state["preview_nonce"] += 1
            st.rerun()
        # Only meaningful when the app runs on the user's own machine
        if (sys.platform == "darwin" and resolved_path
                and st.button("Open output folder")):
            subprocess.run(["open", str(resolved_path.parent)])

    # ── My builds ────────────────────────────────────────────────────────
    st.subheader("My builds")
    jobs = load_jobs()
    if not jobs:
        st.caption("No builds yet — your creations will appear here.")
    for jb in jobs:
        jschema = schemas.get(jb["template_id"], {})
        icon = jschema.get("icon", "📦")
        with st.container(border=True):
            jc1, jc2, jc3 = st.columns([3, 1, 1])
            jc1.markdown(f"{icon} **{jb['job']}**")
            jc1.caption(time.strftime("%b %d, %H:%M", time.localtime(jb["mtime"])))
            if jc2.button("View", key=f"view_{jb['job']}"):
                st.session_state["last_stl_path"] = str(jb["stl"])
                st.session_state["preview_nonce"] += 1
                st.rerun()
            if jb["template_id"] in templates:
                if jc3.button("Edit", key=f"edit_{jb['job']}",
                              help="Load this build's settings into the form"):
                    st.session_state["intent_template_id"] = jb["template_id"]
                    st.session_state["intent_params"] = jb["params"]
                    st.session_state["template_select"] = jb["template_id"]
                    st.session_state["show_gallery"] = False
                    st.rerun()

st.divider()
st.subheader("Output")
if st.session_state.pop("build_requested", False):
    job_dir = OUT_DIR / job_name
    job_dir.mkdir(parents=True, exist_ok=True)

    spec_path = job_dir / "spec.json"
    stamp = int(time.time() * 1000)
    stl_path = job_dir / f"model_{stamp}.stl"
    log_path = job_dir / "logs.txt"

    build_ok = True

    if schema.get("accepts_image"):
        if uploaded_photo is None:
            st.error("This design needs a photo — upload one in step 2 first.")
            build_ok = False
        else:
            photo_png_path = job_dir / "photo.png"
            photo_cols, photo_rows = prepare_lithophane_image(
                uploaded_photo.getvalue(), photo_png_path,
                max_px=photo_detail,
                brightness=photo_brightness,
                contrast=photo_contrast,
                gamma=photo_gamma,
                invert=photo_invert,
            )
            params["photo_path"] = str(photo_png_path.resolve())
            params["photo_cols"] = photo_cols
            params["photo_rows"] = photo_rows

    if build_ok and schema.get("qr_input"):
        qr_text = str(params.get("qr_text", "")).strip()
        if not qr_text:
            st.error("Enter a URL or text for the QR code in step 2 first.")
            build_ok = False
        else:
            qr_png_path = job_dir / "qr.png"
            qr_cols, qr_rows = make_qr_png(qr_text, qr_png_path)
            params["photo_path"] = str(qr_png_path.resolve())
            params["photo_cols"] = qr_cols
            params["photo_rows"] = qr_rows
            # the plaque is square so the code isn't stretched
            params["plate_w"] = float(params.get("size", 80))
            params["plate_h"] = float(params.get("size", 80))

    if build_ok and schema.get("emblem_support") and uploaded_svg is not None:
        emblem_path = job_dir / "emblem.svg"
        emblem_path.write_bytes(uploaded_svg.getvalue())
        params["emblem_enabled"] = 1
        params["emblem_path"] = str(emblem_path.resolve())

    if build_ok:
        spec_path.write_text(json.dumps(
            {"template_id": template_id, "params": params},
            indent=2
        ))

        repaired = False
        try:
            if is_native:
                with st.status("Generating mesh…", expanded=False) as status:
                    t0 = time.time()
                    mesh = build_litho_mesh(
                        params["photo_path"], schema["native_litho"], params
                    )
                    mesh.export(stl_path)
                    logs = (f"Native lithophane mesher: {len(mesh.faces):,} faces "
                            f"in {time.time() - t0:.1f}s, "
                            f"watertight={mesh.is_watertight}")
                    log_path.write_text(logs)
                    report = validate_stl(stl_path)
                    (job_dir / "report.json").write_text(json.dumps(report, indent=2))
                    status.update(label="Mesh generated", state="complete")
            else:
                with st.status("Rendering with OpenSCAD…", expanded=False) as status:
                    has_ai = bool(os.environ.get("OPENAI_API_KEY")
                                  or os.environ.get("ANTHROPIC_API_KEY"))
                    try:
                        logs = run_openscad(openscad_exe, scad_path, stl_path, params)
                    except RuntimeError as scad_err:
                        if not has_ai:
                            raise
                        status.update(label="Build failed — asking AI for a parameter fix…")
                        fixed = repair_params(schema, params, str(scad_err))
                        if fixed is None:
                            raise
                        params = fixed
                        spec_path.write_text(json.dumps(
                            {"template_id": template_id, "params": params}, indent=2))
                        logs = "[params auto-repaired by AI]\n" + run_openscad(
                            openscad_exe, scad_path, stl_path, params)
                        repaired = True
                    log_path.write_text(logs)
                    report = validate_stl(stl_path)
                    (job_dir / "report.json").write_text(json.dumps(report, indent=2))

                    if export_parts:
                        status.update(label="Exporting color parts…")
                        parts_dir = job_dir / "parts"
                        base_stl = parts_dir / f"{job_name}_base.stl"
                        text_stl = parts_dir / f"{job_name}_text.stl"
                        run_openscad(openscad_exe, scad_path, base_stl,
                                     {**params, "part": "base"})
                        run_openscad(openscad_exe, scad_path, text_stl,
                                     {**params, "part": "text"})
                        parts_zip_path = job_dir / f"{job_name}_color_parts.zip"
                        with zipfile.ZipFile(parts_zip_path, "w") as zf:
                            zf.write(base_stl, base_stl.name)
                            zf.write(text_stl, text_stl.name)

                    status.update(label="Build complete", state="complete")

            # Two-color filament-swap hint for raised-text designs
            swap_z = None
            swap_expr = schema.get("color_swap_z") or ""
            if swap_expr and int(params.get("emboss", 1) or 0) == 1:
                z = eval_expr(swap_expr, params)
                if z > 0:
                    swap_z = z

            prune_jobs()
            st.session_state["last_stl_path"] = str(stl_path)
            st.session_state["preview_nonce"] += 1
            st.session_state["just_built"] = True
            st.session_state["last_build"] = {
                "job": job_name,
                "stl": str(stl_path),
                "report": report,
                "logs": logs,
                "swap_z": swap_z,
                "repaired": repaired,
                "parts_zip": str(job_dir / f"{job_name}_color_parts.zip")
                             if (export_parts and not is_native) else None,
            }
            st.rerun()

        except Exception as e:
            st.error(f"Build failed: {e}")
            with st.container(border=True):
                st.markdown(
                    "**Things to try**\n"
                    "- Photo designs: lower the *Photo detail* slider\n"
                    "- Text designs: check the OpenSCAD path in ⚙️ Settings (sidebar)\n"
                    "- Check the logs below for the exact error"
                )
            if log_path.exists():
                with st.expander("Logs"):
                    st.code(log_path.read_text()[-2000:], language="text")

else:
    last_build = st.session_state.get("last_build")
    if st.session_state.pop("just_built", False):
        st.toast("STL ready 🎉")
    if last_build:
        stl_file = Path(last_build["stl"])
        st.success(f"Build completed — {last_build['job']}/{stl_file.name}")
        if last_build.get("repaired"):
            st.warning("⚙️ The first attempt failed and the parameters were "
                       "auto-repaired by AI — double-check the dimensions below.")
        if last_build.get("swap_z"):
            st.info(f"🎨 Two-color tip: pause the print at **Z = "
                    f"{last_build['swap_z']:.1f} mm** and swap filament to give "
                    f"the raised text its own color.")

        report = last_build.get("report", {})
        if report.get("ok"):
            size_xyz = report.get("size_xyz_mm", [0.0, 0.0, 0.0])
            m1, m2, m3 = st.columns(3)
            m1.metric("Size (mm)", f"{size_xyz[0]:.1f} × {size_xyz[1]:.1f} × {size_xyz[2]:.1f}")
            m2.metric("Faces", f"{report.get('faces', 0):,}")
            m3.metric("Watertight", "Yes" if report.get("watertight") else "No")
        else:
            st.warning(f"Validation: {report.get('error', 'unknown')}")

        if stl_file.exists():
            with open(stl_file, "rb") as f:
                st.download_button("⬇️ Download STL", f, file_name=stl_file.name,
                                   type="primary")
        parts_zip = last_build.get("parts_zip")
        if parts_zip and Path(parts_zip).exists():
            with open(parts_zip, "rb") as f:
                st.download_button("🎨 Color parts (.zip)", f,
                                   file_name=Path(parts_zip).name)
            st.caption("Import both STLs into your slicer as parts of one "
                       "object and assign each its own color.")

        with st.expander("Build logs", expanded=False):
            logs = last_build.get("logs", "")
            st.code(logs[-2000:] if logs else "(empty)", language="text")
        with st.expander("Full validation report", expanded=False):
            st.json(report)
    else:
        st.info("Click Build STL to generate your first model.")
