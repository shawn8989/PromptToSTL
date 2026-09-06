#!/usr/bin/env python3
"""Printability gate for generated meshes, with repair and fidelity accounting.

Generative 3D models emit GLB/OBJ/PLY tuned for rendering. This measures
whether such a mesh could be printed, what automated repair has to change to
get it there, and what that repair costs in fidelity.

Run over a directory of meshes:   python printability_gate.py <dir> [...]
Run the self-validation suite:    python printability_gate.py --self-test
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import trimesh

# A print is judged in millimetres. A generative model emits a unit-normalised
# mesh with no real-world scale, so this range only asserts "plausible object",
# not "correct size" -- correct size can only come from a measurement.
MIN_PLAUSIBLE_MM, MAX_PLAUSIBLE_MM = 5.0, 500.0
MIN_WALL_MM = 0.8          # two perimeters of a 0.4 mm nozzle
# Genus counts handles/tunnels. A decorative trinket is genus 0-2; a mug is 1.
# Voxel-remesh noise pushes it into the dozens, so a generous ceiling flags
# artefacts without rejecting legitimately holed shapes.
MAX_PLAUSIBLE_GENUS = 8
THICKNESS_SAMPLES = 1500


def load_any(path: Path) -> trimesh.Trimesh | None:
    """Load a mesh of any format, flattening scenes and normalising indexing.

    STL stores every triangle as three independent vertices with no shared
    index, so without merging identical positions each triangle reads as its
    own disconnected body and nothing is ever watertight. Merging is format
    normalisation, not geometric repair: it moves no surface and changes no
    volume. Repair proper happens later, and is accounted for separately.
    """
    try:
        loaded = trimesh.load(path, force="mesh", process=False)
    except Exception:
        return None
    if isinstance(loaded, trimesh.Scene):
        if not loaded.geometry:
            return None
        loaded = trimesh.util.concatenate(tuple(loaded.geometry.values()))
    if not isinstance(loaded, trimesh.Trimesh) or len(loaded.faces) == 0:
        return None
    loaded.merge_vertices()
    return loaded


def non_manifold_edges(mesh: trimesh.Trimesh) -> int:
    """Edges shared by more than two faces. Same definition tapgraft uses."""
    edges = np.sort(np.asarray(mesh.edges, dtype=np.int64), axis=1)
    if len(edges) == 0:
        return 0
    _, counts = np.unique(edges, axis=0, return_counts=True)
    return int(np.count_nonzero(counts > 2))


def open_boundary_edges(mesh: trimesh.Trimesh) -> int:
    """Edges used by exactly one face: the holes."""
    edges = np.sort(np.asarray(mesh.edges, dtype=np.int64), axis=1)
    if len(edges) == 0:
        return 0
    _, counts = np.unique(edges, axis=0, return_counts=True)
    return int(np.count_nonzero(counts == 1))


def degenerate_faces(mesh: trimesh.Trimesh) -> int:
    areas = np.asarray(mesh.area_faces)
    return int(np.count_nonzero(areas <= 1e-12))


def solid_via_manifold(mesh: trimesh.Trimesh) -> tuple[bool, str]:
    """Can the boolean engine accept this as a solid?

    manifold3d is the engine the project already relies on. If it refuses the
    mesh, no downstream boolean (pocket, base graft) can run on it, which makes
    this the operative test rather than an academic one.
    """
    try:
        import manifold3d
    except Exception:
        return (False, "manifold3d unavailable")
    try:
        mm = manifold3d.Manifold(
            manifold3d.Mesh(
                vert_properties=np.asarray(mesh.vertices, dtype=np.float32),
                tri_verts=np.asarray(mesh.faces, dtype=np.uint32),
            )
        )
        if mm.is_empty():
            return (False, "manifold3d produced an empty solid")
        return (True, f"genus={mm.genus()}")
    except Exception as exc:
        return (False, f"{type(exc).__name__}: {str(exc)[:80]}")


def min_wall_thickness(mesh: trimesh.Trimesh, samples: int = THICKNESS_SAMPLES):
    """Approximate minimum wall by casting rays inward from the surface.

    Approximate on purpose: exact thickness needs a medial axis. This samples
    the surface, fires each ray along the inward normal, and reports the
    shortest crossing. Good enough to catch paper-thin shells.
    """
    try:
        # Step the origin well clear of its own face, or the ray re-hits the
        # triangle it started on and every wall measures as zero.
        eps = max(float(mesh.scale) * 1e-4, 1e-5)
        points, face_idx = trimesh.sample.sample_surface(mesh, samples)
        normals = np.asarray(mesh.face_normals)[face_idx]
        origins = points - normals * eps
        hits = mesh.ray.intersects_location(
            ray_origins=origins, ray_directions=-normals, multiple_hits=False
        )
        locations, index_ray = hits[0], hits[1]
        if len(locations) == 0:
            return None
        dist = np.linalg.norm(locations - origins[index_ray], axis=1)
        dist = dist[dist > eps * 5]
        return float(dist.min()) if len(dist) else None
    except Exception as exc:
        # Never swallow this: a missing ray backend (rtree/pyembree) silently
        # turns every wall check into a failure and looks like bad geometry.
        return f"unmeasurable: {type(exc).__name__}: {str(exc)[:60]}"


def run_gate(mesh: trimesh.Trimesh, check_thickness: bool = True) -> list[dict]:
    """The ordered printability gate. Every check states what it measured."""
    checks: list[dict] = []

    def add(name, passed, measured, expected):
        checks.append({"name": name, "pass": bool(passed), "measured": measured,
                       "expected": expected})

    components = int(mesh.body_count)
    add("single_component", components == 1, components, 1)

    degen = degenerate_faces(mesh)
    add("no_degenerate_faces", degen == 0, degen, 0)

    holes = open_boundary_edges(mesh)
    add("no_open_boundary", holes == 0, holes, 0)

    add("watertight", mesh.is_watertight, bool(mesh.is_watertight), True)

    nm = non_manifold_edges(mesh)
    add("no_non_manifold_edges", nm == 0, nm, 0)

    add("winding_consistent", mesh.is_winding_consistent,
        bool(mesh.is_winding_consistent), True)

    vol = float(mesh.volume)
    add("positive_volume", vol > 0, round(vol, 6), "> 0")

    ok_solid, detail = solid_via_manifold(mesh)
    add("accepted_by_boolean_engine", ok_solid, detail, "accepted")

    # Euler characteristic gives genus without the boolean engine: V - E + F
    # = 2 - 2g for a closed orientable surface.
    if mesh.is_watertight:
        genus = (2 - int(mesh.euler_number)) // 2
        add("plausible_genus", genus <= MAX_PLAUSIBLE_GENUS, genus,
            f"<= {MAX_PLAUSIBLE_GENUS}")

    # This is a smell test, not a scale check. A generative mesh is
    # unit-normalised, so it usually lands at 1-2 mm and is caught here -- but a
    # mesh that happens to fall inside the range is still of unknown real size.
    # Only a supplied measurement establishes scale; tapgraft already refuses to
    # infer it, and this pipeline must not either.
    extents = np.asarray(mesh.extents, dtype=float)
    largest = float(extents.max()) if extents.size else 0.0
    plausible = MIN_PLAUSIBLE_MM <= largest <= MAX_PLAUSIBLE_MM
    add("plausible_mm_scale", plausible, round(largest, 4),
        f"{MIN_PLAUSIBLE_MM}-{MAX_PLAUSIBLE_MM} mm")

    if check_thickness:
        wall = min_wall_thickness(mesh)
        if wall is None or isinstance(wall, str):
            add("min_wall_thickness", False, wall or "not measurable",
                f">= {MIN_WALL_MM} mm")
        else:
            add("min_wall_thickness", wall >= MIN_WALL_MM, round(wall, 4),
                f">= {MIN_WALL_MM} mm")
    return checks


def repair(mesh: trimesh.Trimesh) -> tuple[trimesh.Trimesh, list[str]]:
    """Standard automated repair, recording every action it took."""
    actions: list[str] = []
    out = mesh.copy()

    before_v = len(out.vertices)
    out.merge_vertices()
    if len(out.vertices) != before_v:
        actions.append(f"merged {before_v - len(out.vertices)} duplicate vertices")

    before_f = len(out.faces)
    out.update_faces(out.nondegenerate_faces())
    out.update_faces(out.unique_faces())
    out.remove_unreferenced_vertices()
    if len(out.faces) != before_f:
        actions.append(f"removed {before_f - len(out.faces)} degenerate/duplicate faces")

    if not out.is_winding_consistent:
        trimesh.repair.fix_winding(out)
        actions.append("fixed inconsistent winding")

    if not out.is_watertight:
        holes_before = open_boundary_edges(out)
        trimesh.repair.fill_holes(out)
        holes_after = open_boundary_edges(out)
        if holes_before != holes_after:
            actions.append(f"filled holes ({holes_before} -> {holes_after} boundary edges)")

    trimesh.repair.fix_normals(out)
    if float(out.volume) < 0:
        trimesh.repair.fix_inversion(out)
        actions.append("inverted mesh to positive volume")

    return out, actions


def fidelity(before: trimesh.Trimesh, after: trimesh.Trimesh) -> dict:
    """What repair cost. A mesh that prints but no longer matches is a failure."""
    def pct(a, b):
        return None if a == 0 else round((b - a) / abs(a) * 100.0, 3)

    result = {
        "faces_before": len(before.faces),
        "faces_after": len(after.faces),
        "volume_change_pct": pct(float(before.volume), float(after.volume)),
        "area_change_pct": pct(float(before.area), float(after.area)),
        "bbox_change_mm": [round(float(x), 5) for x in
                           (np.asarray(after.extents) - np.asarray(before.extents))],
    }
    # Surface deviation: how far the repaired skin moved from the original.
    try:
        pts = trimesh.sample.sample_surface(after, 3000)[0]
        dist = trimesh.proximity.closest_point(before, pts)[1]
        result["surface_deviation_mm"] = {
            "mean": round(float(np.mean(dist)), 5),
            "p95": round(float(np.percentile(dist, 95)), 5),
            "max": round(float(np.max(dist)), 5),
        }
    except Exception as exc:
        result["surface_deviation_mm"] = f"unavailable: {type(exc).__name__}"
    return result


def evaluate(path: Path, check_thickness: bool = True) -> dict:
    mesh = load_any(path)
    if mesh is None:
        return {"file": path.name, "loadable": False, "verdict": "unsalvageable"}

    checks = run_gate(mesh, check_thickness)
    failed = [c["name"] for c in checks if not c["pass"]]
    if not failed:
        return {"file": path.name, "loadable": True, "verdict": "pass_unmodified",
                "checks": checks, "failed": []}

    fixed, actions = repair(mesh)
    checks_after = run_gate(fixed, check_thickness)
    failed_after = [c["name"] for c in checks_after if not c["pass"]]

    return {
        "file": path.name,
        "loadable": True,
        "verdict": "pass_after_repair" if not failed_after else "unsalvageable",
        "failed_before": failed,
        "failed_after": failed_after,
        "repair_actions": actions,
        "fidelity": fidelity(mesh, fixed),
        "checks": checks_after,
    }


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    paths: list[Path] = []
    for arg in argv:
        p = Path(arg)
        if p.is_dir():
            for ext in ("*.glb", "*.obj", "*.ply", "*.stl", "*.gltf"):
                paths.extend(sorted(p.rglob(ext)))
        elif p.is_file():
            paths.append(p)

    results = [evaluate(p) for p in paths]
    tally: dict[str, int] = {}
    for r in results:
        tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1

    print(json.dumps({"results": results, "tally": tally,
                      "total": len(results)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
