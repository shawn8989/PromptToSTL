from __future__ import annotations

import json
import os
import re
from typing import Any, Dict


def _coerce_value(value: Any, spec: Dict[str, Any]) -> Any:
    default = spec.get("default")
    vtype = spec.get("type", "string")
    if value is None:
        return default
    if vtype in {"int", "integer"}:
        try:
            val = int(float(value))
        except Exception:
            return default
        min_v = spec.get("min")
        max_v = spec.get("max")
        if min_v is not None:
            val = max(int(min_v), val)
        if max_v is not None:
            val = min(int(max_v), val)
        return val
    if vtype == "number":
        try:
            val = float(value)
        except Exception:
            return default
        min_v = spec.get("min")
        max_v = spec.get("max")
        if min_v is not None:
            val = max(float(min_v), val)
        if max_v is not None:
            val = min(float(max_v), val)
        return val
    return str(value)


def _sanitize_params(schema: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for key, spec in schema.get("params", {}).items():
        if key in params:
            out[key] = _coerce_value(params.get(key), spec)
        else:
            out[key] = spec.get("default")
    return out


def _parse_json(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                return {}
    return {}


def _fallback(templates: Dict[str, Dict[str, Any]], notes: str) -> Dict[str, Any]:
    """Return a safe default proposal (first template + defaults) with a note."""
    first_template = next(iter(templates.keys()))
    schema = templates[first_template]
    return {
        "template_id": first_template,
        "params": _sanitize_params(schema, {}),
        "notes": notes,
    }


def route_intent(description: str, templates: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    description = (description or "").strip()
    if not description:
        first_template = next(iter(templates.keys()))
        schema = templates[first_template]
        return {
            "template_id": first_template,
            "params": _sanitize_params(schema, {}),
            "notes": "Add a description to generate a proposal.",
        }

    template_list = []
    for template_id, schema in templates.items():
        template_list.append({
            "template_id": template_id,
            "label": schema.get("label", template_id),
            "params": schema.get("params", {}),
        })

    system_prompt = (
        "You map user descriptions to a single template and parameters. "
        "Output ONLY valid JSON with keys: template_id, params, notes. "
        "Do not invent personal data. Use only user-provided text. "
        "Only include params that exist in the chosen template schema. "
        "Use defaults when missing. Keep numbers within min/max.\n\n"
        "Photo-based (lithophane) templates — choose when the user mentions "
        "a photo, picture, image, backlit print, or light-up display:\n"
        "  lithophane_heart: heart-shaped photo lithophane.\n"
        "  lithophane_circle: circular photo lithophane.\n"
        "  lithophane_rectangle: rectangular photo lithophane.\n"
        "  lithophane_mom: Mother's Day gift — M heart-lithophane M, "
        "single piece; route here for 'mom', 'mother', 'Mother's Day' + photo.\n"
        "  lithophane_dad: Father's Day gift — D heart-lithophane D, "
        "single piece; route here for 'dad', 'father', 'Father's Day' + photo.\n"
        "For any lithophane template, note in 'notes' that the user must "
        "upload a photo before building."
    )
    user_prompt = {
        "description": description,
        "templates": template_list,
    }

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return _fallback(
            templates,
            "AI routing is off (no ANTHROPIC_API_KEY set). Showing a default "
            "template — pick one and edit the parameters manually.",
        )

    # Lazy import keeps app startup fast and makes the AI dependency optional.
    import anthropic

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": json.dumps(user_prompt)}],
        )
        data = _parse_json(response.content[0].text if response.content else "")
    except Exception as exc:  # noqa: BLE001 — degrade gracefully on any API error
        return _fallback(
            templates,
            f"AI routing failed ({exc.__class__.__name__}); showing a default "
            "template. Edit the parameters manually.",
        )

    template_id = data.get("template_id")
    if template_id not in templates:
        template_id = next(iter(templates.keys()))
    schema = templates[template_id]
    params = _sanitize_params(schema, data.get("params", {}))
    notes = str(data.get("notes", "")).strip()
    return {"template_id": template_id, "params": params, "notes": notes}
