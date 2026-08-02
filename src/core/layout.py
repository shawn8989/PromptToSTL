from __future__ import annotations

import ast
from typing import Any, Dict, Iterable, List, Union


def eval_expr(value: Any, params: Dict[str, Any]) -> float:
    """Evaluate a schema `text_box` arithmetic expression against params.

    Supports + - * / and parameter names only — never eval()s arbitrary code.
    Returns 0.0 for anything unparseable.
    """
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return 0.0

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            left, right = _eval(node.left), _eval(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            return left / right if right != 0 else 0.0
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


def apply_text_layout(schema: Dict[str, Any], params: Dict[str, Any],
                      margin: float = 0.9) -> Dict[str, Any] | None:
    """Auto-fit a template's text into its text_box, mutating `params`.

    Mirrors what the app does before a build: shrinks text_size and wraps
    lines so the text fits the plate. Returns the layout result, or None if
    the template has no text_box.
    """
    text_box = schema.get("text_box") or {}
    if not text_box or "text_size" not in params:
        return None

    params["offset_x"] = eval_expr(text_box.get("offset_x", 0), params)
    params["offset_y"] = eval_expr(text_box.get("offset_y", 0), params)
    box_w = eval_expr(text_box.get("box_w", 0), params)
    box_h = eval_expr(text_box.get("box_h", 0), params)

    if schema.get("self_fitting_text"):
        # The .scad scales text to fit on its own; don't second-guess it.
        return {
            "lines": [params.get(k, "") for k in ("line1", "line2", "line3") if k in params],
            "text_size": params.get("text_size"),
            "offsets_y": [], "warning": "", "truncated": False,
            "box_w": box_w, "box_h": box_h,
        }

    raw = [str(params.get(k, "")) for k in ("line1", "line2", "line3") if k in params]
    if not raw and "text" in params:
        raw = [str(params.get("text", ""))]

    layout = layout_text(
        raw,
        max_lines=int(schema.get("max_lines", 1)),
        box_w_mm=box_w,
        box_h_mm=box_h,
        max_text_size=float(params.get("text_size", 0)),
        min_text_size=float(schema["params"].get("text_size", {}).get(
            "min", params.get("text_size", 0))),
        margin=margin,
        line_gap_mm=float(params.get("line_gap", 0)),
    )
    params["text_size"] = layout["text_size"]
    if "line_gap" in params and "line_gap_mm" in layout:
        params["line_gap"] = layout["line_gap_mm"]
    lines = layout["lines"] + ["", "", ""]
    for i, key in enumerate(("line1", "line2", "line3")):
        if key in params:
            params[key] = lines[i]
    # Expose the computed text area so callers (e.g. emblem snapping) don't
    # need duplicate text_box_* params kept in sync by hand.
    layout["box_w"], layout["box_h"] = box_w, box_h
    return layout


def layout_text(
    text_or_lines: Union[str, Iterable[str]],
    max_lines: int,
    box_w_mm: float,
    box_h_mm: float,
    max_text_size: float,
    min_text_size: float,
    margin: float = 0.9,
    line_gap_mm: float = 0.0,
) -> dict:
    max_lines = max(1, int(max_lines))
    box_w_mm = max(0.0, float(box_w_mm))
    box_h_mm = max(0.0, float(box_h_mm))
    max_text_size = float(max_text_size)
    min_text_size = float(min_text_size)
    margin = float(margin)
    line_gap_mm = max(0.0, float(line_gap_mm))

    if max_text_size < min_text_size:
        max_text_size, min_text_size = min_text_size, max_text_size

    if isinstance(text_or_lines, str):
        raw_text = text_or_lines.strip()
    else:
        parts = [str(p).strip() for p in text_or_lines if str(p).strip()]
        raw_text = " ".join(parts).strip()

    wide = set("WM")
    medium = set("AVYXK")
    narrow = set("Il1|")

    def char_factor(ch: str) -> float:
        if ch == " ":
            return 0.35
        if ch in narrow:
            return 0.36
        if ch in wide:
            return 0.98
        if ch in medium:
            return 0.75
        return 0.62

    def units(s: str) -> float:
        return sum(char_factor(ch) for ch in s)

    def line_width(line: str, text_size: float) -> float:
        return text_size * units(line)

    def truncate_line(line: str, text_size: float, max_width: float) -> str:
        if max_width <= 0 or text_size <= 0:
            return "…"
        max_units = max_width / text_size
        if units(line) <= max_units:
            return line
        ellipsis = "…"
        allowed = max_units - units(ellipsis)
        if allowed <= 0:
            return ellipsis
        acc = 0.0
        out = ""
        for ch in line:
            u = char_factor(ch)
            if acc + u > allowed:
                break
            out += ch
            acc += u
        return out + ellipsis

    def split_no_spaces(value: str, count: int) -> List[str]:
        if count <= 1:
            return [value]
        n = len(value)
        if n <= count:
            return [value] + [""] * (count - 1)
        if count == 2:
            best = None
            for i in range(1, n):
                a = value[:i]
                b = value[i:]
                score = max(units(a), units(b))
                if best is None or score < best[0]:
                    best = (score, [a, b])
            return best[1]
        best = None
        for i in range(1, n - 1):
            for j in range(i + 1, n):
                a = value[:i]
                b = value[i:j]
                c = value[j:]
                score = max(units(a), units(b), units(c))
                if best is None or score < best[0]:
                    best = (score, [a, b, c])
        return best[1]

    def split_words(value: str, count: int) -> List[str]:
        words = value.split()
        if len(words) < count:
            return split_no_spaces(value, count)
        if count == 2:
            best = None
            for i in range(1, len(words)):
                a = " ".join(words[:i])
                b = " ".join(words[i:])
                score = max(units(a), units(b))
                if best is None or score < best[0]:
                    best = (score, [a, b])
            return best[1]
        best = None
        for i in range(1, len(words) - 1):
            for j in range(i + 1, len(words)):
                a = " ".join(words[:i])
                b = " ".join(words[i:j])
                c = " ".join(words[j:])
                score = max(units(a), units(b), units(c))
                if best is None or score < best[0]:
                    best = (score, [a, b, c])
        return best[1]

    def wrap(value: str, count: int) -> List[str]:
        if count <= 1:
            return [value]
        if " " in value:
            return split_words(value, count)
        return split_no_spaces(value, count)

    def compute_offsets(count: int, gap: float) -> List[float]:
        if count <= 1:
            return [0.0]
        mid = (count - 1) / 2.0
        return [((mid - i) * gap) for i in range(count)]

    def gap_for_height(text_size: float, count: int, box_h_eff: float) -> float:
        if count <= 1:
            return 0.0
        max_gap = (box_h_eff - text_size) / (count - 1)
        if max_gap < 0:
            return -1.0
        return min(line_gap_mm, max_gap)

    box_w_eff = box_w_mm * margin
    box_h_eff = box_h_mm * margin

    if raw_text == "":
        return {
            "lines": [""],
            "text_size": max_text_size,
            "offsets_y": [0.0],
            "scale": 1.0,
            "truncated": False,
            "warning": "",
            "line_widths": [0.0],
        }

    step = 0.5
    steps = int(round((max_text_size - min_text_size) / step)) if step > 0 else 0
    sizes = [max_text_size - i * step for i in range(steps + 1)]
    if sizes[-1] > min_text_size:
        sizes.append(min_text_size)

    for text_size in sizes:
        for count in range(1, max_lines + 1):
            if count == 1 and text_size > box_h_eff:
                continue
            lines = wrap(raw_text, count)
            widths = [line_width(line, text_size) for line in lines]
            if widths and max(widths) > box_w_eff:
                continue
            gap_eff = gap_for_height(text_size, count, box_h_eff)
            if gap_eff < 0:
                continue
            offsets_y = compute_offsets(count, gap_eff)
            warning = ""
            if count > 1 and gap_eff < line_gap_mm:
                warning = "Line gap reduced to fit the text box."
            return {
                "lines": lines,
                "text_size": text_size,
                "offsets_y": offsets_y,
                "scale": 1.0,
                "truncated": False,
                "warning": warning,
                "line_widths": widths,
                "line_gap_mm": gap_eff,
            }

    final_text_size = min(min_text_size, box_h_eff) if box_h_eff > 0 else min_text_size
    lines = wrap(raw_text, max_lines)
    gap_eff = gap_for_height(final_text_size, len(lines), box_h_eff)
    if gap_eff < 0:
        gap_eff = 0.0
    offsets_y = compute_offsets(len(lines), gap_eff)
    widths = [line_width(line, final_text_size) for line in lines]
    if widths:
        lines[-1] = truncate_line(lines[-1], final_text_size, box_w_eff)
        widths[-1] = line_width(lines[-1], final_text_size)
    warning = "Text truncated to fit the text box."
    if len(lines) > 1 and gap_eff < line_gap_mm:
        warning = "Text truncated; line gap reduced to fit the text box."
    return {
        "lines": lines,
        "text_size": final_text_size,
        "offsets_y": offsets_y,
        "scale": 1.0,
        "truncated": True,
        "warning": warning,
        "line_widths": widths,
        "line_gap_mm": gap_eff,
    }
