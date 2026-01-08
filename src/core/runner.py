import subprocess
from pathlib import Path

def run_openscad(openscad_exe: str, scad_path: Path, out_stl: Path, params: dict) -> str:
    """
    Runs OpenSCAD with -D defines. Returns combined stdout/stderr text.
    """
    scad_path = scad_path.resolve()
    out_stl = out_stl.resolve()
    out_stl.parent.mkdir(parents=True, exist_ok=True)

    cmd = [openscad_exe, "-o", str(out_stl)]
    for k, v in params.items():
        if isinstance(v, str):
            cmd += ["-D", f'{k}="{v}"']
        elif v is None:
            continue
        else:
            cmd += ["-D", f"{k}={v}"]
    cmd.append(str(scad_path))

    p = subprocess.run(cmd, capture_output=True, text=True)
    logs = (p.stdout or "") + ("\n" + p.stderr if p.stderr else "")
    if p.returncode != 0:
        raise RuntimeError(f"OpenSCAD failed (code {p.returncode}).\n{logs}")
    return logs