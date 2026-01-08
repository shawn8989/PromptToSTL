from pathlib import Path
import trimesh


def validate_stl(stl_path: Path) -> dict:
    stl_path = Path(stl_path).resolve()

    if not stl_path.exists():
        return {"ok": False, "error": "STL missing"}

    if stl_path.stat().st_size < 1000:
        return {"ok": False, "error": "STL too small / likely empty"}

    mesh = trimesh.load_mesh(stl_path, force="mesh")
    if mesh.is_empty:
        return {"ok": False, "error": "Mesh is empty"}

    bounds = mesh.bounds  # [[minx,miny,minz],[maxx,maxy,maxz]]
    size = (bounds[1] - bounds[0]).tolist()

    return {
        "ok": True,
        "bounds_min": bounds[0].tolist(),
        "bounds_max": bounds[1].tolist(),
        "size_xyz_mm": size,
        "watertight": bool(mesh.is_watertight),
        "faces": int(len(mesh.faces)),
        "verts": int(len(mesh.vertices)),
    }