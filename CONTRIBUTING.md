# Contributing

Thanks for your interest in PromptToSTL.

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run
```bash
streamlit run app.py
```

## Style
- Keep changes small and focused.
- Prefer deterministic geometry changes.
- Avoid committing generated files from `out/`.

## Tests
- No automated test suite yet.
- Manual validation: build a template and confirm the STL renders.

## Notes
- The "Describe it" mode requires an `OPENAI_API_KEY` in `.env`.
