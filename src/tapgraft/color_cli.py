"""`tapgraft-color` — export a scan's colour as OBJ/PLY/GLB.

Object Capture writes a *textured* USDZ, but the STL pipeline discards that
colour because STL cannot carry it. This command recovers it.

    tapgraft-color --scan-folder <studio scan folder> --out colored.obj
    tapgraft-color --usdz model.usdz --out colored.obj --filaments 4

macOS only: reading USDZ needs ModelIO, so a small Swift helper is compiled
on first use and cached.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .color import (
    COLOR_FORMATS,
    ColorError,
    color_report,
    export_colored,
    has_color,
    load_colored,
    quantize_colors,
)

_HELPER_SOURCE = Path(__file__).resolve().parents[2] / "tools" / "usdz2obj.swift"


def _helper_binary() -> Path:
    """Compile the ModelIO helper once and cache it next to the source."""
    binary = _HELPER_SOURCE.with_suffix("")
    if binary.is_file() and binary.stat().st_mtime >= _HELPER_SOURCE.stat().st_mtime:
        return binary
    if sys.platform != "darwin":
        raise ColorError("reading USDZ requires macOS (ModelIO)")
    if shutil.which("swiftc") is None:
        raise ColorError("swiftc not found; install Xcode command line tools")
    subprocess.run(
        ["swiftc", "-O", str(_HELPER_SOURCE), "-o", str(binary)],
        check=True,
        capture_output=True,
    )
    return binary


def usdz_to_obj(usdz: Path, destination_dir: Path) -> Path:
    """Convert a USDZ to OBJ + MTL + textures so trimesh can read the colour."""
    destination_dir.mkdir(parents=True, exist_ok=True)
    obj_path = destination_dir / "scan.obj"
    result = subprocess.run(
        [str(_helper_binary()), str(usdz), str(obj_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not obj_path.is_file():
        raise ColorError(f"USDZ conversion failed: {result.stdout.strip()} {result.stderr.strip()}")
    return obj_path


def _resolve_source(args: argparse.Namespace) -> Path:
    if args.usdz:
        source = Path(args.usdz)
        if not source.is_file():
            raise ColorError(f"USDZ not found: {source}")
        return source
    folder = Path(args.scan_folder)
    candidates = [
        folder / "reconstructed" / "output.usdz",
        folder / "output.usdz",
        folder,
    ]
    for candidate in candidates:
        if candidate.is_file() and candidate.suffix.lower() == ".usdz":
            return candidate
    raise ColorError(
        f"no reconstructed/output.usdz under {folder}. Reconstruct the scan in Studio first"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tapgraft-color",
        description="Export a scan's texture as a colour-carrying mesh.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--scan-folder", help="Studio scan folder containing reconstructed/output.usdz")
    group.add_argument("--usdz", help="a USDZ file directly")
    parser.add_argument("--out", required=True, help=f"output file; one of {sorted(COLOR_FORMATS)}")
    parser.add_argument(
        "--filaments",
        type=int,
        help="quantise colour to this many filaments (e.g. 4 for an AMS). Omit to keep full colour",
    )
    parser.add_argument(
        "--height",
        type=float,
        help=(
            "real measured height of the object in mm. Photogrammetry without depth "
            "data produces an arbitrary scale, so pass a caliper measurement to get "
            "true size. Omit to keep the reconstruction's own scale"
        ),
    )
    args = parser.parse_args(argv)

    try:
        source = _resolve_source(args)
        print(f"source: {source}")
        with tempfile.TemporaryDirectory() as tmp:
            obj_path = usdz_to_obj(source, Path(tmp))
            mesh = load_colored(obj_path)
            report = color_report(mesh)
            print(f"colour: {report['unique_colors']} unique colours, mean RGB {report.get('mean_rgb')}")
            if not has_color(mesh):
                print(
                    "WARNING: no varied colour found. The USDZ may be untextured — "
                    "check that reconstruction produced a texture.",
                    file=sys.stderr,
                )
            if args.filaments:
                mesh = quantize_colors(mesh, args.filaments)
                print(f"quantised to {color_report(mesh)['unique_colors']} colours for printing")

            # USDZ and the OBJ ModelIO writes from it are in METRES. Every
            # slicer treats mesh units as millimetres, so an unscaled export
            # imports 1000x too small. See ADR-003.
            mesh.apply_scale(1000.0)
            print(f"scaled metres -> millimetres: bbox {[round(float(v), 2) for v in mesh.extents]} mm")

            if args.height:
                current = float(mesh.extents.max())
                if current <= 0:
                    raise ColorError("model has no measurable extent")
                factor = args.height / current
                mesh.apply_scale(factor)
                print(f"scaled to --height {args.height} mm (factor {factor:.4f})")
                if not 0.5 <= factor <= 2.0:
                    print(
                        f"WARNING: scale factor {factor:.4f} is far from 1.0 — the "
                        "reconstruction's own scale was unreliable (capture without depth)",
                        file=sys.stderr,
                    )

            written = export_colored(mesh, args.out)
        size_mb = written.stat().st_size / 1e6
        print(f"wrote {written} ({size_mb:.2f} MB)")
        print(f"triangles: {len(mesh.faces)}, bbox: {[round(float(v), 2) for v in mesh.extents]} mm")
        if not args.height:
            print("NOTE: no --height given, so real-world size is unverified.")
        return 0
    except ColorError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def entrypoint() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    entrypoint()
