# PromptToSTL

**Generate 3D-printable STL files from text-based descriptions and templates.**

PromptToSTL combines structured templates with OpenSCAD to create parametric 3D geometries. Designed as a local tool with AI extensibility, it supports interactive parameter editing, live previews, and STL validation.

## Features
- **Photo lithophanes in seconds**: heart / circle / rectangle photo plates are
  meshed natively in Python (numpy + trimesh) — no OpenSCAD needed, ~2 s builds.
- **Visual template gallery**: 25 designs shown as rendered 3D previews,
  grouped by category and searchable; every setting has a plain-English
  explanation.
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

## Deploy to the web (use it from your phone)

The app runs on **[Streamlit Community Cloud](https://share.streamlit.io)** for
free, straight from this repo — no server to manage, and it redeploys on every
push. `packages.txt` installs OpenSCAD and the Liberation fonts on the server,
so all templates work (photo lithophanes and QR plaques need no OpenSCAD at all).

1. Go to **share.streamlit.io** and sign in with GitHub.
2. **Create app** → select this repo, pick the branch, main file `app.py`.
   In **Advanced settings**, set **Python version to 3.13** (or 3.12).
   ⚠️ Python **3.14 does not work**: pydantic (pulled in by langchain) calls
   `typing._eval_type(..., prefer_fwd_module=True)`, which 3.14 removed, so
   importing `src/intent/router.py` raises `TypeError` and the app never
   starts. Everything else — Streamlit, trimesh, numpy, the mesher — is
   fine on 3.14; only the AI dependency chain breaks.
3. *(Optional — only for the AI "Describe it" chat and auto-repair)*
   App **Settings → Secrets**, paste one of:
   ```toml
   OPENAI_API_KEY = "sk-…"
   # or
   ANTHROPIC_API_KEY = "sk-ant-…"
   ```
4. Deploy. You get a public `https://<name>.streamlit.app` URL that works on
   any phone or laptop.

Notes:
- The free tier has ~1 GB RAM. Native templates (photo lithophanes, ornaments,
  QR plaques) are fast; heavy OpenSCAD renders like the MOM/DAD plaques at high
  photo detail may be slow.
- The app is public by default — restrict it to invited viewers in the app
  settings if you'd rather keep it private.
- Files in `out/` are ephemeral (cleared on redeploy, and pruned to the newest
  20 builds), so download STLs you want to keep.

Alternative free host: **Hugging Face Spaces** (choose the Streamlit SDK; it
reads the same `requirements.txt` and `packages.txt`).

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