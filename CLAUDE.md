# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

PromptToSTL is a local Streamlit app that generates 3D-printable STL files from parametric templates. Users either fill in parameters manually, type a natural-language description ("Describe it" mode) routed through Claude Haiku to select a template and propose parameters, or create entirely new templates via the in-app Template Builder. The resulting parameters are passed as `-D` defines to OpenSCAD, which renders the STL.

## Running the App

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The app runs at `http://localhost:8501`. OpenSCAD must be installed and on `PATH` for builds to work.

Copy `.env.example` to `.env` and add `ANTHROPIC_API_KEY` to enable AI routing. The rest of the app works without it.

## Linting and Tests

```bash
# Run all non-OpenSCAD tests (no external deps needed):
pytest tests/test_schemas.py tests/test_layout.py tests/test_image_prep.py

# Run end-to-end build tests (requires OpenSCAD on PATH):
pytest tests/test_build.py

# Run a single file:
pytest tests/test_layout.py -v
```

The pytest binary may be at `/root/.local/share/uv/tools/pytest/bin/pytest` if not on PATH. `requirements-dev.txt` lists dev deps.

`test_build.py` auto-skips when OpenSCAD is not installed. `test_image_prep.py` requires Pillow.

## Architecture

### Two App Modes

- **Build mode** — the primary flow: pick a template, set parameters, build STL.
- **Create Template mode** — a form (and optional AI proposal) that generates a new `templates/custom/<id>/` with `schema.json` and `model.scad` from a set of building blocks. Implemented in `src/core/template_builder.py`.

### Request Flow (Build Mode)

```
app.py
  ├── "Describe it"  → src/intent/router.py → Claude Haiku → proposal JSON
  ├── Template pick  → src/core/catalog.py → schema.json + model.scad
  ├── Params UI      → src/ui/params_panel.py → render_params() + apply_text_layout()
  ├── Emblem UI      → src/ui/emblem_panel.py → render_emblem_section()
  ├── Lithophane UI  → src/ui/lithophane_panel.py → render_lithophane_section()
  ├── Preview        → src/ui/preview_panel.py → render_preview_panel()
  ├── Build button   → src/core/runner.py → subprocess OpenSCAD -D flags
  └── Validation     → src/core/validate.py → trimesh mesh inspection
```

### Template System

Each template lives in `templates/<id>/` and requires:

- **`schema.json`** — defines `label`, `scad_file`, optional `text_box` expressions, `max_lines`, optional schema-level flags (`lithophane_mode`, `multicolor_mode`, `print_note`), and a `params` map.
- **`model.scad`** — OpenSCAD geometry. Every param in `schema.json` must have a matching top-level variable declaration in the `.scad` file.

Custom (user-created) templates live in `templates/custom/<id>/` and are loaded alongside built-in ones by `catalog.py`.

**Adding a new template**: create `templates/<id>/schema.json` and the referenced `.scad` file. No code changes needed — the template appears automatically in the UI.

### Schema Conventions

- String params with a fixed set of choices declare `"options": [...]`; the UI renders a selectbox automatically.
- Params with `"hidden": true` are applied silently without a widget.
- Emblem support is opt-in: include `emblem_enabled` in `params` and the emblem section appears.
- Lithophane templates set `"lithophane_mode": true` at the schema root; they get the image-upload flow instead of the standard text layout.
- Two-color templates set `"multicolor_mode": true`; the UI shows the filament-change height.

### Text Layout (`src/core/layout.py`)

`layout_text()` fits multi-line text into a bounding box by:
1. Stepping down from `max_text_size` to `min_text_size` (0.5 mm steps)
2. At each size, trying 1 to `max_lines` line splits (word-aware, then character-split)
3. Returning the first combo that fits within `box_w × box_h` (scaled by `margin`)
4. Truncating with `…` if nothing fits

The `text_box` field in `schema.json` contains arithmetic expressions (evaluated by `eval_expr` in `src/ui/helpers.py`) that compute the usable text area from other param values.

### AI Intent Routing (`src/intent/router.py`)

`route_intent()` sends the description + all template schemas to Claude Haiku and asks for `{template_id, params, notes}` JSON. It degrades gracefully: no API key → immediate fallback with a note; API error → fallback with the error class in the note. `_sanitize_params()` coerces and clamps all returned values before they reach the UI.

### Output Directory

Each build writes to `out/<job_name>/`:
- `spec.json` — template ID and params snapshot
- `model_<timestamp>.stl` — the rendered STL
- `logs.txt` — OpenSCAD stdout/stderr
- `report.json` — trimesh validation results
- `emblem.svg` / `emblem.dat` / `image.dat` — uploaded assets (if any)

`out/` is gitignored.
