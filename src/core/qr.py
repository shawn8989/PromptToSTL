"""QR code heightmap generation for the qr_plaque template.

Produces a grayscale PNG where the QR modules are WHITE (255) on a BLACK (0)
background — the convention build_litho_mesh() expects for raised features
(255 → max_thickness relief, 0 → flat plate).
"""
from __future__ import annotations

from pathlib import Path

import qrcode


def make_qr_png(
    text: str,
    out_path: Path | str,
    box_size: int = 12,
    border: int = 3,
) -> tuple[int, int]:
    """Render `text` as a QR code PNG sized for the native relief mesher.

    box_size: pixels per module — 12 gives crisp edges after the mesher's
    bilinear vertex sampling. border: quiet-zone width in modules (the QR
    spec asks for ≥4; 3 works for printed relief codes since the raised
    border ring adds separation).

    Returns (width_px, height_px).
    """
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(text)
    qr.make(fit=True)
    # fill=white on black: dark modules become the RAISED (255) regions
    img = qr.make_image(fill_color="white", back_color="black").convert("L")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG")
    return img.size
