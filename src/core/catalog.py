import json
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"

def list_templates():
    items = []
    for d in sorted(TEMPLATES_DIR.iterdir()):
        if d.is_dir():
            schema = d / "schema.json"
            if schema.exists():
                items.append(d.name)
    return items

def load_template(template_id: str):
    tdir = TEMPLATES_DIR / template_id
    schema_path = tdir / "schema.json"
    if not schema_path.exists():
        raise FileNotFoundError(f"Missing schema: {schema_path}")
    schema = json.loads(schema_path.read_text())
    scad_path = tdir / schema["scad_file"]
    if not scad_path.exists():
        raise FileNotFoundError(f"Missing scad: {scad_path}")
    return schema, scad_path