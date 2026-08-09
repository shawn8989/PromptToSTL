"""Topology cleanup for scan meshes."""
from __future__ import annotations

from dataclasses import asdict, dataclass

import trimesh


@dataclass
class CleanReport:
    faces_before: int
    faces_after: int
    components_removed: int
    degenerate_faces_removed: int
    duplicate_faces_removed: int
    vertices_merged: int
    holes_filled: int
    decimated_to: int | None

    def as_dict(self) -> dict:
        return asdict(self)


def clean_scan(mesh: trimesh.Trimesh, decimate: int | None = None) -> tuple[trimesh.Trimesh, CleanReport]:
    """Clean a scan while preserving its input scale exactly."""
    result = mesh.copy()
    faces_before = len(result.faces)

    components = result.split(only_watertight=False)
    components_removed = max(0, len(components) - 1)
    if components:
        result = max(components, key=lambda item: (abs(item.volume), item.area)).copy()

    before = len(result.faces)
    result.update_faces(result.nondegenerate_faces(height=1e-10))
    degenerate_removed = before - len(result.faces)

    before = len(result.faces)
    result.update_faces(result.unique_faces())
    duplicate_removed = before - len(result.faces)

    before_vertices = len(result.vertices)
    result.merge_vertices(digits_vertex=6)
    result.remove_unreferenced_vertices()
    vertices_merged = before_vertices - len(result.vertices)

    # General scan hole filling is intentionally deferred by the handoff. The
    # tool repairs winding, but does not invent large missing surfaces.
    trimesh.repair.fix_normals(result, multibody=False)

    decimated_to = None
    if decimate is not None and decimate < len(result.faces):
        if decimate < 4:
            raise ValueError("--decimate must be at least 4 faces")
        try:
            result = result.simplify_quadric_decimation(face_count=decimate)
        except Exception as exc:
            raise ValueError(f"scan decimation failed: {exc}") from exc
        decimated_to = len(result.faces)

    report = CleanReport(
        faces_before=faces_before,
        faces_after=len(result.faces),
        components_removed=components_removed,
        degenerate_faces_removed=degenerate_removed,
        duplicate_faces_removed=duplicate_removed,
        vertices_merged=vertices_merged,
        holes_filled=0,
        decimated_to=decimated_to,
    )
    return result, report
