from __future__ import annotations

import json
import re
from typing import Any, Dict

from langchain_openai import ChatOpenAI


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
        "Use defaults when missing. Keep numbers within min/max."
    )
    user_prompt = {
        "description": description,
        "templates": template_list,
    }

    model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    response = model.invoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_prompt)},
        ]
    )
    data = _parse_json(response.content or "")

    template_id = data.get("template_id")
    if template_id not in templates:
        template_id = next(iter(templates.keys()))
    schema = templates[template_id]
    params = _sanitize_params(schema, data.get("params", {}))
    notes = str(data.get("notes", "")).strip()
    return {"template_id": template_id, "params": params, "notes": notes}
