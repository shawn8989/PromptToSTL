from __future__ import annotations

import json
import os
import re
from typing import Any, Dict


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


def propose_template_spec(description: str) -> Dict[str, Any]:
    description = (description or "").strip()
    if not description:
        return {}

    system_prompt = (
        "You create a template specification for a parametric 3D object builder. "
        "Output ONLY valid JSON with keys: template_id, label, shape, width, height, "
        "diameter, thickness, radius, text, emblem. "
        "shape must be 'rounded_rect' or 'circle'. "
        "If shape is 'circle', use diameter and ignore width/height/radius. "
        "text is either null or an object with: enabled, max_lines, line1, line2, line3, "
        "text_size, text_height, line_gap, pad_x, pad_y, offset_x, offset_y, emboss, text_align. "
        "emblem is either null or an object with: enabled, snap, autocenter, scale, depth, x, y, rot, mode. "
        "Use reasonable defaults when uncertain. Do not include any other keys."
    )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "AI template proposals need an ANTHROPIC_API_KEY. Add one to your "
            ".env file, or build a template manually with the form below."
        )

    # Lazy import keeps app startup fast and makes the AI dependency optional.
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": json.dumps({"description": description})}],
    )

    return _parse_json(response.content[0].text if response.content else "")
