from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional

from langchain_openai import ChatOpenAI

try:
    from langchain_anthropic import ChatAnthropic
except ImportError:
    ChatAnthropic = None


def _make_model():
    """Pick the LLM provider.

    LLM_PROVIDER env ("anthropic" | "openai") forces a choice; otherwise
    Anthropic is used when ANTHROPIC_API_KEY is set (claude-haiku-4-5 —
    fast + cheap for routing), falling back to OpenAI gpt-4o-mini.
    """
    provider = os.environ.get("LLM_PROVIDER", "").strip().lower()
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY")) and ChatAnthropic is not None
    if provider == "openai":
        return ChatOpenAI(model="gpt-4o-mini", temperature=0)
    if provider == "anthropic" or has_anthropic:
        if ChatAnthropic is None:
            raise RuntimeError(
                "LLM_PROVIDER=anthropic but langchain-anthropic is not installed "
                "(pip install langchain-anthropic)"
            )
        return ChatAnthropic(model="claude-haiku-4-5", temperature=0)
    return ChatOpenAI(model="gpt-4o-mini", temperature=0)


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


_ROUTING_HINTS = (
    "Photo-based (lithophane) templates — choose when the user mentions "
    "a photo, picture, image, backlit print, or light-up display:\n"
    "  lithophane_heart: heart-shaped photo lithophane.\n"
    "  lithophane_circle: circular photo lithophane.\n"
    "  lithophane_rectangle: rectangular photo lithophane.\n"
    "  lithophane_ornament: round photo lithophane with a hanger hole — "
    "Christmas ornaments, window charms.\n"
    "  lithophane_mom: Mother's Day gift — M heart-lithophane M, "
    "single piece; route here for 'mom', 'mother', 'Mother's Day' + photo.\n"
    "  lithophane_dad: Father's Day gift — D heart-lithophane D, "
    "single piece; route here for 'dad', 'father', 'Father's Day' + photo.\n"
    "For any lithophane template, note in 'notes' that the user must "
    "upload a photo before building.\n\n"
    "Other templates:\n"
    "  pet_tag: dog/cat ID tag (bone, round, or heart shape) — pet names.\n"
    "  luggage_tag: travel tag with name + phone and a strap slot.\n"
    "  desk_name_sign: wedge desk sign with a name/title.\n"
    "  fridge_magnet_text: text plate with magnet pockets.\n"
    "  phone_stand: desk phone stand with adjustable angle.\n"
    "  wall_hook: screw-mount J-hook for coats/bags/headphones.\n"
    "  mini_planter: tapered succulent pot with drainage holes.\n"
    "  keychain_roundrect: name keychain.\n"
    "  coaster_round: drink coaster with text.\n"
    "  nameplate: desk/door nameplate, up to 3 lines.\n"
    "  qr_plaque: scannable raised QR-code plaque — put the URL/text in the "
    "qr_text param (WiFi cards, menus, business links).\n"
    "  gridfinity_bin: Gridfinity-compatible storage bin (grid units).\n"
    "  cookie_cutter: heart/star/circle/hexagon cookie cutter.\n"
    "  spiral_vase: twisted lobed vase for vase-mode printing."
)


def _build_messages(
    description: str,
    template_list: list,
    current: Optional[Dict[str, Any]] = None,
) -> list:
    """Build the chat messages for a routing (or refinement) request."""
    system_prompt = (
        "You map user descriptions to a single template and parameters. "
        "Output ONLY valid JSON with keys: template_id, params, notes. "
        "Do not invent personal data. Use only user-provided text. "
        "Only include params that exist in the chosen template schema. "
        "Use defaults when missing. Keep numbers within min/max.\n\n"
        + _ROUTING_HINTS
    )
    payload: Dict[str, Any] = {
        "description": description,
        "templates": template_list,
    }
    if current:
        system_prompt += (
            "\n\nThe user is REFINING an existing design. 'current' holds the "
            "template and parameters they are working on. Treat the "
            "description as a modification request (e.g. 'make it wider', "
            "'add a second line'), keep everything they did not mention "
            "unchanged, and return the FULL updated params. Stay on the "
            "current template unless they clearly ask for a different object."
        )
        payload["current"] = current
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(payload)},
    ]


def route_intent(
    description: str,
    templates: Dict[str, Dict[str, Any]],
    current: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Route a description (or a refinement of `current`) to template + params.

    current: optional {"template_id": ..., "params": {...}} of the design the
    user is iterating on — enables 'make it wider' style follow-ups.
    """
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
            "description": schema.get("description", ""),
            "params": schema.get("params", {}),
        })

    model = _make_model()
    response = model.invoke(_build_messages(description, template_list, current))
    data = _parse_json(response.content or "")

    template_id = data.get("template_id")
    if template_id not in templates:
        template_id = (current or {}).get("template_id")
    if template_id not in templates:
        template_id = next(iter(templates.keys()))
    schema = templates[template_id]
    params = _sanitize_params(schema, data.get("params", {}))
    notes = str(data.get("notes", "")).strip()
    return {"template_id": template_id, "params": params, "notes": notes}


def repair_params(
    schema: Dict[str, Any],
    params: Dict[str, Any],
    error_log: str,
) -> Optional[Dict[str, Any]]:
    """One-shot attempt to fix params after a failed OpenSCAD build.

    Returns corrected params, or None if the model can't propose a fix.
    Caller is responsible for retrying at most once.
    """
    system_prompt = (
        "A parametric 3D build failed. You get the template's param schema, "
        "the params used, and the OpenSCAD error log. Output ONLY valid JSON: "
        '{"params": {...}, "notes": "what you changed"} with corrected '
        "parameter values that should build successfully. Change as little as "
        "possible. If the error is not caused by parameter values, output "
        '{"params": null, "notes": "reason"}.'
    )
    payload = {
        "schema_params": schema.get("params", {}),
        "params_used": params,
        "error_log": error_log[-3000:],
    }
    model = _make_model()
    response = model.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(payload)},
    ])
    data = _parse_json(response.content or "")
    fixed = data.get("params")
    if not isinstance(fixed, dict):
        return None
    return _sanitize_params(schema, {**params, **fixed})
