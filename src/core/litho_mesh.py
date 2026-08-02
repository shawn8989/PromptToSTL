"""Native lithophane mesh generation — no OpenSCAD needed.

A lithophane plate (base + frame ring + heightmap fill) is a pure
heightfield, so we mesh it directly: a vertex grid over the plate where
each vertex carries one Z height, top surface triangles over active
cells, a flat bottom, and vertical walls along the silhouette boundary.
Watertight by construction; renders in ~1–2 s where OpenSCAD's
surface() + intersection() takes 30 s to minutes.

Height rules per region (matching templates/lithophane_*/model.scad):
  frame ring (inside outer shape, outside inner): base_height + max_thickness
  interior  (inside inner shape):  base_height + min_thickness
                                   + pixel/255 * (max_thickness − min_thickness)
  outside the outer shape: no geometry

The heightmap PNG is expected pre-processed by prepare_lithophane_image
(grayscale, bright = thick).
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw


# ── Shape outlines (polygon point lists, centered at origin) ────────────────

def _heart_points(w: float, h: float, n: int = 256) -> np.ndarray:
    """Parametric heart scaled to a w×h bounding box, same curve as the SCAD:
    x = 16·sin³t, y = 13·cos t − 5·cos 2t − 2·cos 3t − cos 4t
    Natural bbox 32 × 29.5, centre offset y = −2.25."""
    t = np.linspace(0.0, 2.0 * math.pi, n, endpoint=False)
    x = 16.0 * np.sin(t) ** 3
    y = 13.0 * np.cos(t) - 5.0 * np.cos(2 * t) - 2.0 * np.cos(3 * t) - np.cos(4 * t)
    x = x * (w / 32.0)
    y = (y + 2.25) * (h / 29.5)
    return np.column_stack([x, y])


def _circle_points(d: float, n: int = 256) -> np.ndarray:
    t = np.linspace(0.0, 2.0 * math.pi, n, endpoint=False)
    r = d / 2.0
    return np.column_stack([r * np.cos(t), r * np.sin(t)])


def _roundrect_points(w: float, h: float, r: float, n_arc: int = 16) -> np.ndarray:
    """Rounded rectangle centered at origin. Corner radius clamped like the
    SCAD's rounded_rect (min(r, w/4, h/4))."""
    r = max(0.0, min(r, w / 4.0, h / 4.0))
    hw, hh = w / 2.0, h / 2.0
    if r <= 0:
        return np.array([[-hw, -hh], [hw, -hh], [hw, hh], [-hw, hh]])
    pts = []
    # corner centers and their arc start angles (CCW from -x,-y corner)
    corners = [
        (hw - r, hh - r, 0.0),        # top-right
        (-hw + r, hh - r, 90.0),      # top-left
        (-hw + r, -hh + r, 180.0),    # bottom-left
        (hw - r, -hh + r, 270.0),     # bottom-right
    ]
    for cx, cy, a0 in corners:
        for i in range(n_arc + 1):
            a = math.radians(a0 + 90.0 * i / n_arc)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return np.array(pts)


def _shape_outlines(shape: str, params: dict) -> tuple[np.ndarray, np.ndarray, float, float]:
    """Return (outer_pts, inner_pts, plate_w, plate_h) for a shape id."""
    fw = float(params.get("frame_width", 4.0))
    if shape == "heart":
        w = float(params["heart_w"])
        h = float(params["heart_h"])
        return _heart_points(w, h), _heart_points(w - 2 * fw, h - 2 * fw), w, h
    if shape in ("circle", "ornament"):
        d = float(params["diameter"])
        return _circle_points(d), _circle_points(d - 2 * fw), d, d
    if shape == "roundrect":
        w = float(params["plate_w"])
        h = float(params["plate_h"])
        r = float(params.get("corner_r", 0.0))
        inner_r = max(0.0, r - fw)
        return (_roundrect_points(w, h, r),
                _roundrect_points(w - 2 * fw, h - 2 * fw, inner_r), w, h)
    raise ValueError(f"Unknown lithophane shape: {shape}")


def _ornament_hole(params: dict) -> tuple[float, float, float]:
    """(center_y, hole_r, ring_r) for the ornament hanger hole — placed just
    inside the top edge, with a reinforcement ring at frame height."""
    d = float(params["diameter"])
    fw = float(params.get("frame_width", 4.0))
    hole_d = float(params.get("hole_d", 4.0))
    ring_w = float(params.get("hole_ring", 2.5))
    cy = d / 2.0 - hole_d / 2.0 - max(fw, 3.0)
    return cy, hole_d / 2.0, hole_d / 2.0 + ring_w


# ── Rasterization helpers ────────────────────────────────────────────────────

def _rasterize(pts: np.ndarray, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    """Boolean inside-mask of polygon `pts` sampled at the grid defined by
    coordinate vectors xs (len nx) and ys (len ny). Returns (ny, nx)."""
    nx, ny = len(xs), len(ys)
    x0, x1 = float(xs[0]), float(xs[-1])
    y0, y1 = float(ys[0]), float(ys[-1])
    # map polygon mm coords -> pixel coords in an nx×ny image
    sx = (nx - 1) / (x1 - x0) if x1 > x0 else 1.0
    sy = (ny - 1) / (y1 - y0) if y1 > y0 else 1.0
    poly = [((px - x0) * sx, (py - y0) * sy) for px, py in pts]
    img = Image.new("1", (nx, ny), 0)
    ImageDraw.Draw(img).polygon(poly, fill=1)
    return np.array(img, dtype=bool)


def _sample_heightmap(img: np.ndarray, xs: np.ndarray, ys: np.ndarray,
                      inner_w: float, inner_h: float) -> np.ndarray:
    """Bilinear-sample the grayscale heightmap (stretched to inner_w×inner_h,
    centered at origin) at every grid vertex. Returns (ny, nx) floats 0-255."""
    ih, iw = img.shape
    # vertex mm coords -> fractional pixel coords (image row 0 = top = +y)
    u = (xs + inner_w / 2.0) / inner_w * (iw - 1)
    v = (inner_h / 2.0 - ys) / inner_h * (ih - 1)
    u = np.clip(u, 0, iw - 1)
    v = np.clip(v, 0, ih - 1)
    uu, vv = np.meshgrid(u, v)
    u0 = np.floor(uu).astype(int)
    v0 = np.floor(vv).astype(int)
    u1 = np.minimum(u0 + 1, iw - 1)
    v1 = np.minimum(v0 + 1, ih - 1)
    fu = uu - u0
    fv = vv - v0
    imgf = img.astype(np.float64)
    top = imgf[v0, u0] * (1 - fu) + imgf[v0, u1] * fu
    bot = imgf[v1, u0] * (1 - fu) + imgf[v1, u1] * fu
    return top * (1 - fv) + bot * fv


# ── Mesh construction ────────────────────────────────────────────────────────

def build_litho_mesh(heightmap_path: Path | str, shape: str, params: dict) -> trimesh.Trimesh:
    """Build a watertight lithophane mesh from a preprocessed heightmap PNG.

    shape: "heart" | "circle" | "roundrect"
    params: the template params dict (heart_w / diameter / plate_w…,
            min_thickness, max_thickness, frame_width, base_height).
    """
    min_t = float(params.get("min_thickness", 0.8))
    max_t = float(params.get("max_thickness", 3.0))
    fw = float(params.get("frame_width", 4.0))
    base = float(params.get("base_height", 1.2))

    outer_pts, inner_pts, plate_w, plate_h = _shape_outlines(shape, params)
    inner_w = plate_w - 2 * fw
    inner_h = plate_h - 2 * fw
    if inner_w <= 0 or inner_h <= 0:
        raise ValueError("frame_width too large for the plate size")

    img = np.array(Image.open(heightmap_path).convert("L"))
    ih, iw = img.shape

    # Grid resolution: image pixels span the inner box; extend to full plate.
    cell_x = inner_w / iw
    cell_y = inner_h / ih
    nx = int(round(plate_w / cell_x)) + 1   # vertices in x
    ny = int(round(plate_h / cell_y)) + 1   # vertices in y
    xs = np.linspace(-plate_w / 2.0, plate_w / 2.0, nx)
    ys = np.linspace(-plate_h / 2.0, plate_h / 2.0, ny)

    outer_v = _rasterize(outer_pts, xs, ys)          # (ny, nx) at vertices
    inner_v = _rasterize(inner_pts, xs, ys)

    ring_v = None
    if shape == "ornament":
        hole_cy, hole_r, ring_r = _ornament_hole(params)
        hole_v = _rasterize(_circle_points(hole_r * 2) + [0.0, hole_cy], xs, ys)
        ring_v = _rasterize(_circle_points(ring_r * 2) + [0.0, hole_cy], xs, ys)
        outer_v &= ~hole_v      # hole cells go inactive → walls form around it
        inner_v &= ~hole_v

    litho = _sample_heightmap(img, xs, ys, inner_w, inner_h)
    height = np.zeros((ny, nx))
    height[outer_v] = base + max_t                                  # frame
    interior = base + min_t + litho * (max_t - min_t) / 255.0
    height[inner_v] = interior[inner_v]                             # image
    if ring_v is not None:
        height[ring_v & outer_v] = base + max_t     # reinforce around the hole

    # Active cells: all 4 corner vertices inside the outer shape.
    cell = (outer_v[:-1, :-1] & outer_v[:-1, 1:]
            & outer_v[1:, :-1] & outer_v[1:, 1:])                   # (ny-1, nx-1)
    if not cell.any():
        raise ValueError("Shape rasterized to an empty mask")

    # Vertex indexing: top grid then bottom grid.
    n_grid = nx * ny
    vid = np.arange(n_grid).reshape(ny, nx)
    xx, yy = np.meshgrid(xs, ys)
    verts_top = np.column_stack([xx.ravel(), yy.ravel(), height.ravel()])
    verts_bot = np.column_stack([xx.ravel(), yy.ravel(), np.zeros(n_grid)])
    vertices = np.vstack([verts_top, verts_bot])

    cj, ci = np.nonzero(cell)              # cell row (y), col (x)
    v00 = vid[cj, ci]
    v10 = vid[cj, ci + 1]
    v01 = vid[cj + 1, ci]
    v11 = vid[cj + 1, ci + 1]

    faces = []
    # Top surface (+z normal): CCW seen from above
    faces.append(np.column_stack([v00, v10, v11]))
    faces.append(np.column_stack([v00, v11, v01]))
    # Bottom (−z normal): reversed winding, offset into bottom grid
    faces.append(np.column_stack([v00, v11, v10]) + n_grid)
    faces.append(np.column_stack([v00, v01, v11]) + n_grid)

    # Boundary walls: cell edges where the neighbor cell is inactive.
    pad = np.zeros((cell.shape[0] + 2, cell.shape[1] + 2), dtype=bool)
    pad[1:-1, 1:-1] = cell

    def wall(mask, va, vb):
        """Wall quads along edge (va→vb, top) down to the bottom grid.
        With edge direction d in the xy-plane, this winding faces the side
        90° clockwise from d — callers pick va→vb so that side is outward."""
        j, i = np.nonzero(mask)
        a = va(j, i)
        b = vb(j, i)
        f1 = np.column_stack([a, b + n_grid, b])
        f2 = np.column_stack([a, a + n_grid, b + n_grid])
        return [f1, f2]

    # south edge (neighbor below inactive): edge v00→v10, outward = −y
    m = cell & ~pad[:-2, 1:-1]
    faces += wall(m, lambda j, i: vid[j, i], lambda j, i: vid[j, i + 1])
    # north edge: edge v11→v01, outward = +y
    m = cell & ~pad[2:, 1:-1]
    faces += wall(m, lambda j, i: vid[j + 1, i + 1], lambda j, i: vid[j + 1, i])
    # west edge: edge v01→v00, outward = −x
    m = cell & ~pad[1:-1, :-2]
    faces += wall(m, lambda j, i: vid[j + 1, i], lambda j, i: vid[j, i])
    # east edge: edge v10→v11, outward = +x
    m = cell & ~pad[1:-1, 2:]
    faces += wall(m, lambda j, i: vid[j, i + 1], lambda j, i: vid[j + 1, i + 1])

    # Vertices are already shared via the grid index, and windings are chosen
    # outward-facing above — skip trimesh's expensive merge/repair passes.
    mesh = trimesh.Trimesh(
        vertices=vertices,
        faces=np.vstack(faces),
        process=False,
    )
    mesh.remove_unreferenced_vertices()
    return mesh
