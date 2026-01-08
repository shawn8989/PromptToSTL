# PromptToSTL

PromptToSTL is a local GUI tool for generating 3D-printable STL files from structured templates using OpenSCAD. It provides a reliable, repeatable pipeline with live preview, designed to scale from simple parametric objects (keychains, coasters, nameplates) to AI-assisted generation workflows later.

This project prioritizes:
- Deterministic geometry (no hallucinated meshes)
- Local generation (no cloud dependency)
- Print-safe outputs
- Extensibility toward AI agents (LangChain) in later phases

FEATURES

- Template-based STL generation  
  Each object is defined by a schema plus an OpenSCAD model.
- Local Streamlit GUI  
  Edit parameters and build interactively.
- Repeatable builds  
  Modify parameters and rebuild as many times as needed.
- Live 3D preview  
  Always-on STL preview with auto-refresh.
- Versioned outputs  
  Each build produces a uniquely named STL file.
- STL validation  
  Basic geometry checks using trimesh.

CURRENT TEMPLATES

- Keychain  
  Text emboss or engrave, adjustable size and thickness.

More templates planned: coaster, nameplate, plaques, lithophanes.

PROJECT STRUCTURE

PromptToSTL/
- app.py                 Streamlit GUI
- src/
  - core/
    - catalog.py         Template discovery
    - runner.py          OpenSCAD execution
    - validate.py        STL validation
    - layout.py          Planned text/layout logic
- templates/
  - <template_id>/
    - schema.json        Parameter definitions
    - model.scad         OpenSCAD geometry
- out/                   Generated STL files (gitignored)
- .venv/

REQUIREMENTS

- Python 3.10+
- OpenSCAD (CLI accessible)
- macOS, Linux, or Windows (tested on macOS)

Python packages:
- streamlit
- streamlit-stl
- trimesh

SETUP

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

Install OpenSCAD from https://openscad.org and ensure the `openscad` binary is available in your PATH.

RUNNING THE APP

streamlit run app.py

Then open http://localhost:8501 in your browser.

HOW TEMPLATES WORK

Each template consists of:
- schema.json defining UI parameters and constraints
- model.scad consuming those parameters to generate geometry

The GUI loads the schema, renders inputs dynamically, passes values to OpenSCAD using -D defines, generates an STL, previews it, and validates the result. This design keeps geometry deterministic and print-safe.

WHY NOT GENERATE GEOMETRY WITH AI?

LLMs are not used to create meshes directly. Geometry is always created by OpenSCAD. AI (planned) will only choose templates, fill parameters, and retry or adjust on failure. This avoids invalid, non-manifold, or unprintable models.

ROADMAP

Near term:
- Coaster template
- Nameplate template
- Robust text overflow handling
- SVG emblem overlays

Mid term:
- Lithophanes
- Relief plaques
- Image-to-STL pipelines

Long term:
- LangChain agents for prompt routing, parameter filling, and layout correction
- API backend for mobile and web apps

STATUS

Active development.
Not production-ready.
Local-only by design for now.

LICENSE

MIT (subject to change before public release).
