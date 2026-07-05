from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps


def prepare_lithophane_image(
    src_bytes: bytes,
    out_path: Path | str,
    max_px: int = 1024,
    brightness: float = 1.0,
    contrast: float = 1.0,
    gamma: float = 1.0,
    invert: bool = True,
) -> tuple[int, int]:
    """Preprocess an image for use as an OpenSCAD surface() heightmap.

    Converts to grayscale, resizes to fit within max_px on the longest edge,
    applies brightness/contrast/gamma, and optionally inverts. Dark pixels
    will be tall (thick plastic) after inversion — the correct convention for
    a backlit lithophane.

    Returns (width_px, height_px) of the saved PNG so callers can pass exact
    pixel dimensions to OpenSCAD's surface() scaling logic.
    """
    out_path = Path(out_path)

    img = Image.open(__import__("io").BytesIO(src_bytes))

    # Discard alpha, handle palette mode
    if img.mode in ("RGBA", "LA"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # Resize so longest edge ≤ max_px, preserve aspect ratio
    w, h = img.size
    if max(w, h) > max_px:
        scale = max_px / max(w, h)
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)

    # Grayscale
    img = img.convert("L")

    # Brightness (1.0 = no change, >1 = brighter)
    if brightness != 1.0:
        img = ImageEnhance.Brightness(img).enhance(brightness)

    # Contrast (1.0 = no change, >1 = more contrast)
    if contrast != 1.0:
        img = ImageEnhance.Contrast(img).enhance(contrast)

    # Gamma correction via LUT (gamma > 1 darkens, < 1 brightens)
    if gamma != 1.0:
        lut = bytes([round(((i / 255.0) ** gamma) * 255) for i in range(256)])
        img = img.point(lut)

    # Invert: dark → tall plastic (correct for backlit lithophane display)
    if invert:
        img = ImageOps.invert(img)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG")
    return img.size  # (width_px, height_px)
