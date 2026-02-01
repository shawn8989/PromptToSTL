# Documentation

This folder contains lightweight design notes and decision records for PromptToSTL.

## Architecture (High Level)
- Streamlit UI renders template parameters from JSON schemas.
- Parameters are passed to OpenSCAD for deterministic geometry.
- Output STL is previewed and validated locally.

## Key Modules
- `src/core/catalog.py`: template discovery and schema loading
- `src/core/runner.py`: OpenSCAD execution
- `src/core/validate.py`: STL validation
- `src/intent/router.py`: optional prompt routing (LangChain + OpenAI)

## Planned Docs
- Template authoring guide
- Validation and print-safety checks
- Prompt routing policy and guardrails
