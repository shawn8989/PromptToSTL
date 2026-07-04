"""Shared utility functions for the Streamlit UI."""
from __future__ import annotations

import ast
import io
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Tuple

try:
    from PIL import Image, ImageOps
except Exception:
    Image = None
    ImageOps = None


def eval_expr(value, params: dict) -> float:
    """Safely evaluate a simple math expression using param values."""
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return 0.0

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            left, right = _eval(node.left), _eval(node.right)
            if isinstance(node.op, ast.Add): return left + right
            if isinstance(node.op, ast.Sub): return left - right
            if isinstance(node.op, ast.Mult): return left * right
            if isinstance(node.op, ast.Div): return left / right if right != 0 else 0.0
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            val = _eval(node.operand)
            return val if isinstance(node.op, ast.UAdd) else -val
        if isinstance(node, ast.Name):
            return float(params.get(node.id, 0.0))
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        return 0.0

    try:
        return float(_eval(ast.parse(value, mode="eval")))
    except Exception:
        return 0.0


def _parse_svg_length(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    match = re.search(r"[-+]?[0-9]*\.?[0-9]+", value)
    return float(match.group(0)) if match else None


def svg_size_from_bytes(svg_bytes: bytes) -> Optional[Tuple[float, float]]:
    try:
        root = ET.fromstring(svg_bytes)
    except Exception:
        return None
    vb = root.attrib.get("viewBox") or root.attrib.get("viewbox")
    if vb:
        parts = re.split(r"[ ,]+", vb.strip())
        if len(parts) >= 4:
            try:
                return float(parts[2]), float(parts[3])
            except Exception:
                pass
    w = _parse_svg_length(root.attrib.get("width"))
    h = _parse_svg_length(root.attrib.get("height"))
    return (w, h) if w and h else None


def emoji_to_twemoji_svg(emoji_text: str) -> Optional[bytes]:
    emoji_text = (emoji_text or "").strip()
    if not emoji_text:
        return None
    codepoints = "-".join(f"{ord(ch):x}" for ch in emoji_text)
    url = f"https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/svg/{codepoints}.svg"
    try:
        from urllib.request import urlopen
        with urlopen(url, timeout=10) as resp:
            return resp.read()
    except Exception:
        return None


def image_size_from_bytes(image_bytes: bytes, max_size: int = 256) -> Optional[Tuple[int, int]]:
    if Image is None:
        return None
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("L")
        img.thumbnail((max_size, max_size))
        return img.size
    except Exception:
        return None


def save_image_as_dat(
    image_bytes: bytes,
    out_path: Path,
    max_size: int = 256,
    invert: bool = False,
) -> Optional[Tuple[int, int]]:
    if Image is None or ImageOps is None:
        return None
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("L")
        img.thumbnail((max_size, max_size))
        if invert:
            img = ImageOps.invert(img)
        w, h = img.size
        pixels = list(img.getdata())
        with out_path.open("w", encoding="utf-8") as f:
            for y in range(h):
                row = pixels[y * w: (y + 1) * w]
                f.write(" ".join(f"{p / 255:.4f}" for p in row) + "\n")
        return w, h
    except Exception:
        return None
