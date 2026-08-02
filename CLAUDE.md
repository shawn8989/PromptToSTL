# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

PromptToSTL is a local Streamlit app that generates 3D-printable STL files from parametric templates. Users either fill in parameters manually or type a natural-language description ("Describe it" mode), which is routed through an LLM to select a template and populate parameters. The resulting parameters are passed as `-D` defines to OpenSCAD, which renders the STL.

## Running the App

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The app runs at `http://localhost:8501`. OpenSCAD must be installed and on `PATH` (`openscad` command) for builds to work.

## Linting and Tests

```bash
ruff src/ tests/    # lint
pytest              # run all tests
pytest tests/test_layout.py  # single test file
```

Dependencies are in `requirements.txt` (includes `Pillow` for lithophane image preprocessing). Install with `pip install -r requirements.txt`.

The `OPENAI_API_KEY` environment variable (loaded via `.env`) is required for "Describe it" / intent mode (`src/intent/router.py`). The rest of the app works without it.

## Architecture

### Request Flow

```
app.py (Streamlit UI: gallery → customize → build wizard)
  ├── "Describe it" mode → src/intent/router.py → ChatOpenAI (gpt-4o-mini) → proposal JSON
  ├── Template gallery  → src/core/catalog.py → reads templates/<id>/schema.json + model.scad
  ├── Text layout       → src/core/layout.py → computes text_size, line splits, y-offsets
  ├── Build button      → schema has native_litho? → src/core/litho_mesh.py (pure Python, ~2 s)
  │                       otherwise → src/core/runner.py → subprocess OpenSCAD with -D flags
  │                       (auto-appends --backend=Manifold on 2024.09+ snapshots)
  └── Validation        → src/core/validate.py → trimesh mesh inspection
```

### Native Lithophane Mesher (`src/core/litho_mesh.py`)

Templates with `"native_litho": "heart"|"circle"|"roundrect"|"ornament"` in their schema skip
OpenSCAD entirely: `build_litho_mesh()` composes the whole plate (base + frame ring +
photo heightfield) as one vertex grid and emits a watertight trimesh directly —
~700× faster than OpenSCAD `surface()` and requires no OpenSCAD install.
`lithophane_mom`/`_dad` still use OpenSCAD because their letters need `text()`.
Wall windings are constructed outward-facing; do not add `fix_normals` (it costs
~14 s at 300 px and is unnecessary).

### Template System

Each template lives in `templates/<id>/` and requires two files:

- **`schema.json`** — defines the template label, the `.scad` filename, optional `text_box` geometry expressions, `max_lines`, and a `params` map with `type`/`default`/`min`/`max` per parameter. UI metadata: template-level `category`, `icon` (emoji), `description` drive the gallery cards; param-level `label`, `unit`, `help`, `group` ("Text"/"Dimensions"/"Style" render inline, "Emblem"/"Advanced" render in collapsed expanders; ungrouped params fall back to name-prefix heuristics), and `options` (renders a selectbox). `hidden: true` hides a param from the form.

  Don't hand-edit param metadata — `scripts/apply_param_docs.py` owns it. Add
  an entry to that script's `D` table (or `HIDE` set) and re-run it; it fails
  loudly if any visible param is undocumented. Other optional template-level
  flags: `self_fitting_text` (the `.scad` scales text itself, so the Python
  layout engine leaves `text_size` alone) and `thumb_yaw` (camera azimuth for
  the gallery thumbnail, when the default view faces a blank side).

### Gallery Thumbnails

`scripts/render_thumbnails.py` builds every template at its defaults and writes
`templates/<id>/thumb.png`, which the gallery cards display. It uses a small
numpy+PIL software rasterizer, so it needs no GL and adds no runtime
dependency — thumbnails are committed, and the app never renders at request
time. Re-run it after changing geometry or defaults. It shares the app's text
auto-fit (`apply_text_layout`) so thumbnails match what users actually get.
- **`model.scad`** (or `keychain.scad`) — OpenSCAD geometry that reads variables injected via `-D` CLI flags. All parameters in `schema.json` must have matching variable declarations in the `.scad` file.

The `text_box` field in `schema.json` contains arithmetic expressions (evaluated by `eval_expr` in `app.py`) that compute the usable text area in mm from other parameters. This drives the auto-sizing logic in `layout.py`.

### Text Layout (`src/core/layout.py`)

`layout_text()` fits text into a bounding box by:
1. Trying decreasing font sizes (stepping down 0.5 mm from `max_text_size` to `min_text_size`)
2. At each size, trying 1 up to `max_lines` line splits (word-aware, then character-split fallback)
3. Returning the first combination that fits within `box_w × box_h` (with `margin` factor applied)
4. If nothing fits, truncating the last line with `…`

The character-width model is heuristic (per-character factors, not font metrics), so actual rendered width may differ slightly.

### Output Directory

Each build writes to `out/<job_name>/`:
- `spec.json` — template ID and params snapshot
- `model_<timestamp>.stl` — the rendered STL
- `logs.txt` — OpenSCAD stdout/stderr
- `report.json` — trimesh validation results (bounds, watertight, face/vert counts)
- `emblem.svg` (if an SVG emblem was uploaded)

The `out/` directory is gitignored.

### Adding a New Template

1. Create `templates/<new_id>/schema.json` with the required structure (copy an existing one as a base).
2. Create the `.scad` file referenced by `schema.json`'s `scad_file` field; declare every param as a top-level variable with a default.
3. If the template has text, add a `text_box` section to the schema and set `max_lines`.
4. The template appears automatically in the UI — no code changes needed.

### Intent Router (`src/intent/router.py`)

`route_intent()` sends the user description + full template schemas to an LLM and asks it to output `{template_id, params, notes}` JSON. Provider: `_make_model()` picks Anthropic `claude-haiku-4-5` when `ANTHROPIC_API_KEY` is set (requires `langchain-anthropic`), else OpenAI `gpt-4o-mini`; `LLM_PROVIDER=anthropic|openai` forces a choice. The response is sanitized through `_sanitize_params()` which coerces types and clamps to `min`/`max` bounds. Adding a new template is sufficient for it to be available to the LLM automatically.

"Describe it" mode in `app.py` is a chat (`st.chat_message`/`st.chat_input`): each reply auto-applies the proposal to the form via the `intent_*` session keys. Passing `current={"template_id", "params"}` to `route_intent()` switches the prompt to refinement mode ("make it wider" keeps everything else unchanged). `repair_params()` is the build-repair hook: on an OpenSCAD failure with an API key present, `app.py` asks it for corrected params and retries exactly once, flagging the result as auto-repaired.

### Two-color / filament-swap hint

A template-level `"color_swap_z"` schema field holds an `eval_expr` expression (e.g. `"th"`, `"base_height + max_thickness"`) for the Z height where raised text begins. After a successful build with `emboss == 1` (or no emboss param), the Output panel shows a "pause at Z = X mm and swap filament" tip computed from the built params.

### Multi-part color export

Templates with `"multipart": true` declare a `part = "all"|"base"|"text"` variable in their `.scad` with guards around the plate vs. raised-text geometry (`part` is injected by `app.py`, never a schema param). When `emboss == 1`, the Build step offers "Also export color parts": after the main render, OpenSCAD runs twice more with `-D part=...` into `<job>/parts/`, both STLs are zipped, and the Output panel shows a "Color parts (.zip)" download for per-part color assignment in the slicer.

### QR Plaques

`qr_plaque` uses `"qr_input": true`: the `qr_text` string param is turned into a QR PNG at build time by `src/core/qr.py` (`make_qr_png` — modules are white/255 = raised) and fed through the native mesher (`native_litho: "roundrect"`); `app.py` forces `plate_w == plate_h == size` so the code isn't stretched. No OpenSCAD involved; the checked-in `model.scad` is a blank-plate fallback only.

### Lithophane Photo Controls

Templates with `accepts_image: true` show a photo uploader plus preprocessing controls in `app.py`: a "Photo detail" slider (native templates: 100–500 px, default 300; OpenSCAD templates: 100–400 px, default 200) that caps the heightmap resolution passed to `prepare_lithophane_image(max_px=...)`, and brightness/contrast/gamma/invert sliders with a live original-vs-heightmap preview. HEIC (iPhone) photos are supported via `pillow-heif`. For OpenSCAD-path templates keep detail near 200 px — `surface()` render time grows roughly quadratically with resolution, and `run_openscad` aborts after 300 s. The hidden `photo_cols`/`photo_rows` params are set from the processed image's actual pixel dimensions at build time.

### Emblem / SVG Support

Templates that support SVG emblems pass `emblem_enabled`, `emblem_path`, `emblem_scale`, `emblem_x`, `emblem_y`, `emblem_rot`, `emblem_mode`, and `emblem_depth` to OpenSCAD. The `emblem_snap` param (handled entirely in `app.py`) is a UI convenience that maps named positions (e.g. `"top_left"`, `"center"`) to absolute `emblem_x`/`emblem_y` coordinates before the build; it is not passed to OpenSCAD.
