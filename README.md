# PromptToSTL

**Generate 3D-printable STL files from text-based descriptions and templates.**

PromptToSTL combines structured templates with OpenSCAD to create parametric 3D geometries. Designed as a local tool with AI extensibility, it supports interactive parameter editing, live previews, and STL validation.

## Features
- **Photo lithophanes in seconds**: heart / circle / rectangle photo plates are
  meshed natively in Python (numpy + trimesh) — no OpenSCAD needed, ~2 s builds.
- **Visual template gallery**: browse designs by category, customize with
  friendly labeled parameters, build, download.
- **Local Streamlit GUI**: photo preprocessing (brightness/contrast/gamma/invert)
  with live heightmap preview; live 3D viewer with color/material controls.
- **My builds**: every build is re-editable — reload its settings, tweak, rebuild.
- **Template-based generation**: text designs use `.scad` + `.json` templates via
  OpenSCAD (auto-uses the fast Manifold backend on 2024.09+ snapshots).
- **"Describe it" mode**: LLM routes a natural-language request to a template.

## Tech Stack
- **Python**: Streamlit, trimesh
- **OpenSCAD**: Geometry definitions
- **Streamlit-STL**: Live rendering

## Project Structure
```plaintext
src/              # Core logic
templates/        # Parameterized shape models
docs/             # Architecture & design
tests/            # Unit/validation tests
.github/workflows # CI pipeline
```

## Setup Instructions
### Requirements
- Python ≥ 3.10
- Libraries: `pip install -r requirements.txt`
- OpenSCAD — only for text templates (keychain, coaster, nameplate, MOM/DAD
  plaques). Photo lithophanes build without it. A
  [2024.09+ snapshot](https://openscad.org/downloads.html#snapshots) renders
  10–100× faster (Manifold backend, auto-detected).

### Running the App
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```
- Visit the app at **http://localhost:8501**

### Testing
```bash
pytest                      # Run unit tests
ruff src/ tests/            # Linter checks
```

## Roadmap
### Short Term
- Add templates (coaster, nameplate)
- Robust text layout handling
- Overlay SVG logos into objects

### Long Term
- LangChain integration for AI-driven templates
- Backend API for remote access
- Image-to-STL pipelines with AI

## Demo
_TODO: Include screenshots of the Streamlit GUI and example STL generation._