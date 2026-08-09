"""Generated mesh primitives used by tapgraft tests; no external assets."""
from __future__ import annotations

import numpy as np
import trimesh

POCKET_DIAMETER_MM = 9.6
POCKET_DEPTH_MM = 8.0


def drilled_cylinder(
    *,
    outer_radius: float = 15.0,
    height: float = 12.0,
    pocket_radius: float = POCKET_DIAMETER_MM / 2.0,
    pocket_depth: float = POCKET_DEPTH_MM,
    sections: int = 64,
) -> trimesh.Trimesh:
    """Create a watertight cylinder with a coaxial blind pocket at -Z."""
    angles = np.linspace(0.0, 2.0 * np.pi, sections, endpoint=False)
    outer_xy = np.column_stack((np.cos(angles), np.sin(angles))) * outer_radius
    inner_xy = np.column_stack((np.cos(angles), np.sin(angles))) * pocket_radius
    pocket_ceiling = pocket_depth

    vertices = np.vstack(
        (
            np.column_stack((outer_xy, np.zeros(sections))),
            np.column_stack((outer_xy, np.full(sections, height))),
            np.column_stack((inner_xy, np.zeros(sections))),
            np.column_stack((inner_xy, np.full(sections, pocket_ceiling))),
            [[0.0, 0.0, height], [0.0, 0.0, pocket_ceiling]],
        )
    )
    outer_bottom = 0
    outer_top = sections
    inner_bottom = sections * 2
    inner_top = sections * 3
    top_center = sections * 4
    pocket_center = top_center + 1
    faces: list[list[int]] = []

    for index in range(sections):
        nxt = (index + 1) % sections
        faces.extend(
            (
                [outer_bottom + index, outer_bottom + nxt, outer_top + nxt],
                [outer_bottom + index, outer_top + nxt, outer_top + index],
                [outer_bottom + index, inner_bottom + nxt, outer_bottom + nxt],
                [outer_bottom + index, inner_bottom + index, inner_bottom + nxt],
            )
        )
        faces.append([top_center, outer_top + index, outer_top + nxt])
        faces.extend(
            (
                [inner_bottom + index, inner_top + nxt, inner_bottom + nxt],
                [inner_bottom + index, inner_top + index, inner_top + nxt],
            )
        )
        faces.append([pocket_center, inner_top + nxt, inner_top + index])

    mesh = trimesh.Trimesh(vertices=vertices, faces=np.asarray(faces), process=True)
    mesh.fix_normals()
    assert mesh.is_watertight
    return mesh


def lumpy_sphere_on_stick(*, sections: int = 48) -> trimesh.Trimesh:
    """Create a single scan-like body with a narrow stick at its -Z end."""
    z_levels = np.array([0.0, 3.0, 8.0, 14.0, 22.0, 30.0, 38.0, 44.0])
    radii = np.array([3.0, 3.2, 3.6, 6.5, 9.5, 10.0, 7.5, 3.5])
    angles = np.linspace(0.0, 2.0 * np.pi, sections, endpoint=False)
    rings = []
    for level, radius in zip(z_levels, radii, strict=True):
        lumpy_radius = radius * (1.0 + 0.055 * np.sin(3.0 * angles + level * 0.11))
        rings.append(
            np.column_stack(
                (lumpy_radius * np.cos(angles), lumpy_radius * np.sin(angles), np.full(sections, level))
            )
        )

    vertices = np.vstack((*rings, [[0.0, 0.0, z_levels[0]], [0.0, 0.0, z_levels[-1]]]))
    bottom_center = len(z_levels) * sections
    top_center = bottom_center + 1
    faces: list[list[int]] = []
    for ring in range(len(z_levels) - 1):
        lower = ring * sections
        upper = (ring + 1) * sections
        for index in range(sections):
            nxt = (index + 1) % sections
            faces.extend(([lower + index, lower + nxt, upper + nxt], [lower + index, upper + nxt, upper + index]))
    top_ring = (len(z_levels) - 1) * sections
    for index in range(sections):
        nxt = (index + 1) % sections
        faces.append([bottom_center, index, nxt])
        faces.append([top_center, top_ring + nxt, top_ring + index])

    mesh = trimesh.Trimesh(vertices=vertices, faces=np.asarray(faces), process=True)
    mesh.fix_normals()
    assert mesh.is_watertight
    return mesh
