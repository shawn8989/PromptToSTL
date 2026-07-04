# PromptToSTL

Generate 3D-printable STL files from structured prompts and parametric templates.

PromptToSTL is a local, template-driven tool that turns structured inputs into deterministic OpenSCAD models and exportable STL files. It is designed for reproducible 3D printing workflows with optional AI-assisted prompt routing.

![Pipeline overview](assets/pipeline.svg)

## Features
- Local Streamlit UI for parameter editing and builds
- Template-based generation using `.scad` + schema definitions
- Deterministic geometry (OpenSCAD only, no AI meshes)
- Live STL preview and basic validation
- Optional AI-assisted prompt routing (Describe it mode)

## Example Output
![STL preview](assets/model_preview.svg)

## Quickstart
### Requirements
- Python 3.10+
- OpenSCAD (CLI accessible in `PATH`)

### Install
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Optional: AI Prompt Routing
The app runs fully without any API key — every template can be built and
exported manually. To additionally enable the AI "Describe it" and
template-proposal modes, create a `.env` file with an Anthropic key:
```bash
ANTHROPIC_API_KEY=your_key_here
```
Without a key the AI features simply show a note and fall back to manual
editing; nothing else is affected.

### Run
```bash
streamlit run app.py
```
Open http://localhost:8501 in your browser.

### Tests
```bash
pip install -r requirements-dev.txt
pytest
```
The suite validates every template schema and builds each template through
OpenSCAD to confirm it produces a watertight STL. Build tests auto-skip if
OpenSCAD is not installed.

## Current Templates
- Keychain (rounded rectangle)
- Coaster (round)
- Nameplate (multiline text layout)
- Plaque
- Badge (round)
- Multicolor badge
- Cuban link chain
- Lithophane (photo → heightmap plate)

## How It Works
1. A template schema defines parameters and constraints.
2. The UI renders inputs and passes values to OpenSCAD.
3. OpenSCAD generates deterministic geometry.
4. The STL is previewed and validated locally.

## Tech Stack
- Python (Streamlit, trimesh)
- OpenSCAD CLI
- Streamlit-STL for live rendering
- Anthropic Claude (optional prompt routing / template proposals)

## Project Structure
```plaintext
app.py              # Streamlit entry point
src/core/           # Geometry pipeline (catalog, runner, validate, layout)
src/intent/         # Optional AI routing + template proposals (Claude)
src/ui/             # Streamlit panels (params, preview, emblem, lithophane)
templates/          # OpenSCAD templates + JSON schemas
tests/              # Schema + headless build smoke tests
assets/             # Screenshots and diagrams for README
out/                # Generated builds (gitignored)
```

## Notes
- Geometry is always produced by OpenSCAD for deterministic, printable output.
- The "Describe it" mode uses Anthropic Claude; manual mode works fully offline.
- The Cuban link chain uses BOSL2 bezier sweeps and renders much faster on
  OpenSCAD 2024+ (Manifold backend) than on the legacy 2021.01 CGAL backend.

## Roadmap (Short)
- More templates (gridfinity bins, cookie cutters, QR plaques, tags)
- Conversational parameter refinement ("make it 20% wider")
- Self-healing AI template builder (render-check-retry loop)
- Better layout constraints and text overflow handling

## License
MIT
