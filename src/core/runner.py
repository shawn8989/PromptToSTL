import subprocess
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=8)
def supports_manifold(openscad_exe: str) -> bool:
    """True when this OpenSCAD build accepts ``--backend=Manifold``.

    Manifold arrived in OpenSCAD 2023+ and is dramatically faster than legacy
    CGAL on CSG-heavy templates — ``cuban_link_chain`` unions ~50 bezier sweeps
    and exceeds a 60s build timeout on 2021.01. Probed once per executable and
    cached, because passing an unknown flag makes older builds exit non-zero.
    """
    try:
        probe = subprocess.run(
            [openscad_exe, "--help"], capture_output=True, text=True, timeout=15, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return "--backend" in ((probe.stdout or "") + (probe.stderr or ""))


def escape_scad_string(value: str) -> str:
    """Escape a value destined for ``-D name="value"``.

    An unescaped quote or backslash in user text produced a malformed define
    and an opaque OpenSCAD parse error instead of a usable message.
    """
    return value.replace("\\", "\\\\").replace('"', '\\"')


def run_openscad(openscad_exe: str, scad_path: Path, out_stl: Path, params: dict) -> str:
    """
    Runs OpenSCAD with -D defines. Returns combined stdout/stderr text.
    """
    scad_path = scad_path.resolve()
    out_stl = out_stl.resolve()
    out_stl.parent.mkdir(parents=True, exist_ok=True)

    cmd = [openscad_exe, "-o", str(out_stl)]
    if supports_manifold(openscad_exe):
        cmd.append("--backend=Manifold")
    for k, v in params.items():
        if isinstance(v, str):
            cmd += ["-D", f'{k}="{escape_scad_string(v)}"']
        elif v is None:
            continue
        else:
            cmd += ["-D", f"{k}={v}"]
    cmd.append(str(scad_path))

    p = subprocess.run(cmd, capture_output=True, text=True, check=False)
    logs = (p.stdout or "") + ("\n" + p.stderr if p.stderr else "")
    if p.returncode != 0:
        raise RuntimeError(f"OpenSCAD failed (code {p.returncode}).\n{logs}")
    return logs
