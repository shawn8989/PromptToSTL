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

No `requirements.txt` is committed — install dependencies from the README stack: `streamlit`, `trimesh`, `streamlit-stl`, `langchain-openai`, `python-dotenv`, and optionally `pyvista`.

The `OPENAI_API_KEY` environment variable (loaded via `.env`) is required for "Describe it" / intent mode (`src/intent/router.py`). The rest of the app works without it.

## Architecture

### Request Flow

```
app.py (Streamlit UI)
  ├── "Describe it" mode → src/intent/router.py → ChatOpenAI (gpt-4o-mini) → proposal JSON
  ├── Template selector → src/core/catalog.py → reads templates/<id>/schema.json + model.scad
  ├── Text layout      → src/core/layout.py → computes text_size, line splits, y-offsets
  ├── Build button     → src/core/runner.py → subprocess OpenSCAD with -D param flags
  └── Validation       → src/core/validate.py → trimesh mesh inspection
```

### Template System

Each template lives in `templates/<id>/` and requires two files:

- **`schema.json`** — defines the template label, the `.scad` filename, optional `text_box` geometry expressions, `max_lines`, and a `params` map with `type`/`default`/`min`/`max` per parameter.
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

`route_intent()` sends the user description + full template schemas to `gpt-4o-mini` and asks it to output `{template_id, params, notes}` JSON. The response is sanitized through `_sanitize_params()` which coerces types and clamps to `min`/`max` bounds. Adding a new template is sufficient for it to be available to the LLM automatically.

### Emblem / SVG Support

Templates that support SVG emblems pass `emblem_enabled`, `emblem_path`, `emblem_scale`, `emblem_x`, `emblem_y`, `emblem_rot`, `emblem_mode`, and `emblem_depth` to OpenSCAD. The `emblem_snap` param (handled entirely in `app.py`) is a UI convenience that maps named positions (e.g. `"top_left"`, `"center"`) to absolute `emblem_x`/`emblem_y` coordinates before the build; it is not passed to OpenSCAD.
