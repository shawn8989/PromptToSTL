# PromptToSTL

**Generate 3D-printable STL files from structured prompts and parametric templates.**

PromptToSTL is a local, template-driven tool that converts structured inputs into deterministic OpenSCAD models and exportable STL files. It is designed for reproducible 3D printing workflows with future AI-assisted routing.

## What It Does
- Converts structured inputs into parametric 3D models
- Uses OpenSCAD templates for deterministic geometry
- Supports repeatable STL generation
- Designed to run locally (no cloud dependency)
- Built to be extended with AI-assisted prompt routing

## Tech Stack
- Python
- OpenSCAD (CLI)
- Streamlit (local UI)
- Trimesh (validation, planned)

## Project Structure
```plaintext
src/                # Core application logic
templates/          # OpenSCAD templates + schemas
docs/               # Architecture and design decisions
tests/              # Test scaffolding (WIP)
.github/workflows/  # CI configuration Running Locally