#!/usr/bin/env python3
"""Render a preview thumbnail for every template at its default parameters.

Writes templates/<id>/thumb.png, which the gallery shows on each card.

Uses a tiny built-in software rasterizer (numpy + PIL) rather than a GL
renderer so it runs headless anywhere and adds no runtime dependency —
thumbnails are pre-rendered and committed, so the app never renders at
request time.

    python scripts/render_thumbnails.py            # all templates
    python scripts/render_thumbnails.py pet_tag    # just one
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.core.catalog import list_templates, load_template  # noqa: E402
from src.core.image_prep import prepare_lithophane_image  # noqa: E402
from src.core.layout import apply_text_layout  # noqa: E402
from src.core.litho_mesh import build_litho_mesh  # noqa: E402
from src.core.qr import make_qr_png  # noqa: E402
from src.core.runner import run_openscad  # noqa: E402

SIZE = 512           # render at 2x then downsample for cheap antialiasing
OUT = 256
BG = (255, 255, 255, 0)
BASE_COLOR = np.array([232, 89, 12], dtype=float)   # app's amber
LIGHT = np.array([-0.35, -0.55, 0.75])              # from upper-front-left


def _sample_photo(path: Path) -> None:
    """A neutral portrait-ish gradient so lithophane thumbs show relief."""
    w, h = 240, 300
    yy, xx = np.mgrid[0:h, 0:w]
    face = np.exp(-(((xx - w / 2) / (w * 0.28)) ** 2 + ((yy - h * 0.45) / (h * 0.3)) ** 2))
    img = 60 + 170 * face
    img += 25 * np.exp(-(((xx - w * 0.38) / 14) ** 2 + ((yy - h * 0.38) / 14) ** 2))
    img -= 45 * np.exp(-(((xx - w * 0.40) / 7) ** 2 + ((yy - h * 0.36) / 7) ** 2))
    img -= 45 * np.exp(-(((xx - w * 0.60) / 7) ** 2 + ((yy - h * 0.36) / 7) ** 2))
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "L").save(path)


def build_mesh(tid: str, tmp: Path) -> trimesh.Trimesh:
    """Build a template at its defaults and return the mesh."""
    schema, scad_path = load_template(tid)
    params = {k: v.get("default") for k, v in schema["params"].items()}

    if schema.get("qr_input"):
        png = tmp / "qr.png"
        cols, rows = make_qr_png(str(params.get("qr_text") or "https://example.com"), png)
        params.update(photo_path=str(png), photo_cols=cols, photo_rows=rows)
        size = float(params.get("size", 80))
        params.update(plate_w=size, plate_h=size)
    elif schema.get("accepts_image"):
        src = tmp / "src.png"
        _sample_photo(src)
        png = tmp / "hm.png"
        cols, rows = prepare_lithophane_image(src.read_bytes(), png, max_px=220)
        params.update(photo_path=str(png), photo_cols=cols, photo_rows=rows)

    if schema.get("native_litho"):
        return build_litho_mesh(params["photo_path"], schema["native_litho"], params)

    # Same auto-fit the app runs, so thumbnails match what users get
    apply_text_layout(schema, params)

    stl = tmp / f"{tid}.stl"
    run_openscad("openscad", scad_path, stl, params)
    return trimesh.load_mesh(stl, force="mesh")


def render(mesh: trimesh.Trimesh, yaw_deg: float = -35.0) -> Image.Image:
    """Flat-shaded isometric render via painter's algorithm.

    yaw_deg: camera azimuth. The default views the model from -Y, which
    shows the top face of flat plates. Templates whose detail faces another
    direction (e.g. the desk sign's slanted face) set `thumb_yaw` in their
    schema.
    """
    v = mesh.vertices - mesh.bounds.mean(axis=0)          # center on origin

    # Isometric-ish camera: yaw then pitch, Z-up model -> screen Y-up
    yaw, pitch = np.radians(yaw_deg), np.radians(24.0)
    cy, sy = np.cos(yaw), np.sin(yaw)
    cp, sp = np.cos(pitch), np.sin(pitch)
    rot = np.array([
        [cy,       sy,      0],
        [-sy * sp, cy * sp, cp],
        [sy * cp, -cy * cp, sp],
    ])
    p = v @ rot.T                                         # x right, y up, z depth

    span = max(np.ptp(p[:, 0]), np.ptp(p[:, 1])) or 1.0
    scale = SIZE * 0.82 / span
    sx = p[:, 0] * scale + SIZE / 2
    sy_ = SIZE / 2 - p[:, 1] * scale                      # flip for image coords
    depth = p[:, 2]

    faces = mesh.faces
    # Cull back faces, then paint far -> near
    normals = mesh.face_normals @ rot.T
    front = normals[:, 2] > 0
    faces, normals = faces[front], normals[front]
    order = np.argsort(depth[faces].mean(axis=1))

    shade = np.clip(normals @ (LIGHT / np.linalg.norm(LIGHT)), 0, 1)
    shade = 0.28 + 0.72 * shade                           # ambient + diffuse

    img = Image.new("RGBA", (SIZE, SIZE), BG)
    draw = ImageDraw.Draw(img)
    for i in order:
        a, b, c = faces[i]
        col = tuple(int(x) for x in np.clip(BASE_COLOR * shade[i], 0, 255)) + (255,)
        draw.polygon([(sx[a], sy_[a]), (sx[b], sy_[b]), (sx[c], sy_[c])],
                     fill=col, outline=col)
    return img.resize((OUT, OUT), Image.LANCZOS)


def main(only: list[str]) -> int:
    ids = only or list_templates()
    failures = []
    for tid in ids:
        try:
            with tempfile.TemporaryDirectory() as td:
                mesh = build_mesh(tid, Path(td))
                # Thumbnails don't need full lithophane relief detail
                if len(mesh.faces) > 60_000:
                    keep = np.linspace(0, len(mesh.faces) - 1, 60_000).astype(int)
                    mesh = trimesh.Trimesh(mesh.vertices, mesh.faces[keep], process=False)
                schema, _ = load_template(tid)
                yaw = float(schema.get("thumb_yaw", -35.0))
                render(mesh, yaw).save(ROOT / "templates" / tid / "thumb.png")
            ext = mesh.bounds[1] - mesh.bounds[0]
            print(f"  ✓ {tid:22} {ext[0]:6.1f} x {ext[1]:5.1f} x {ext[2]:5.1f} mm")
        except Exception as e:
            failures.append(tid)
            print(f"  ✗ {tid:22} {e.__class__.__name__}: {str(e)[:70]}")
    if failures:
        print(f"\nFailed: {', '.join(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
