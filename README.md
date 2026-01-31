# PromptToSTL

**Generate 3D-printable STL files from text-based descriptions and templates.**

PromptToSTL combines structured templates with OpenSCAD to create parametric 3D geometries. Designed as a local tool with AI extensibility, it supports interactive parameter editing, live previews, and STL validation.

## Features
- **Local Streamlit GUI**: Modify parameters via a dynamic interface.
- **Template-based generation**: Builds using `.scad` + `.json` templates.
- **Repeatable builds**: Deterministic outputs with versioning.
- **Live 3D preview**: Auto-refreshed STL previews.
- **Extensible**: AI-driven workflows with LangChain planned.

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
- OpenSCAD (CLI accessible)
- Libraries: `pip install -r requirements.txt`

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