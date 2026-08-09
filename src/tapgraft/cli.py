"""Command-line interface and stable JSON contract for tapgraft."""
from __future__ import annotations

import argparse
import copy
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__, graft
from .clean import clean_scan
from .meshio import (
    InputError,
    failed_output_path,
    load_mesh,
    mesh_report,
    write_json,
    write_mesh,
)
from .orient import orient_scan, scale_to_height
from .pocket import PocketDetectionError, detect_pocket, protected_extents
from .verify import first_failure, run_verification

_LAST_REPORT: dict = {}


def last_report() -> dict:
    """Expose the most recent in-process report for callers and tests."""
    return copy.deepcopy(_LAST_REPORT)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tapgraft",
        description="Merge an STL scan onto a tap-handle base and verify the print-ready result.",
    )
    parser.add_argument("--version", action="version", version=f"tapgraft {__version__}")
    parser.add_argument("--scan", required=True, help="scanned STL, interpreted as millimetres")
    parser.add_argument("--base", required=True, help="base STL with ferrule pocket, interpreted as millimetres")
    parser.add_argument("--out", help="verified output STL")
    parser.add_argument("--height", type=float, help="measured object height in millimetres")
    parser.add_argument("--overlap", type=float, default=2.0, help="scan/base overlap in millimetres")
    parser.add_argument("--flip", action="store_true", help="invert automatic end selection")
    parser.add_argument("--decimate", type=int, help="target scan face count")
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="analyse through pocket detection and write nothing",
    )
    parser.add_argument("--json", dest="json_path", help="write the stable report JSON")
    parser.add_argument("--verbose", action="store_true")
    return parser


def _empty_report(scan_path: str, base_path: str) -> dict:
    return {
        "ok": False,
        "tool_version": __version__,
        "input": {
            "scan": {"path": scan_path},
            "base": {"path": base_path},
        },
        "orientation": None,
        "scale": None,
        "pocket": None,
        "boolean": None,
        "checks": [],
        "output": None,
        "error": None,
    }


def _print_mesh(label: str, data: dict) -> None:
    bbox = " x ".join(f"{value:.3f}" for value in data["bbox_mm"])
    print(
        f"load {label}: {data['vertices']} vertices, {data['triangles']} triangles, "
        f"bbox {bbox} mm, volume {data['volume_mm3']:.3f} mm^3, "
        f"watertight={'yes' if data['watertight'] else 'no'}, components={data['components']}"
    )


def _progress(stage: str, percent: int) -> None:
    """Emit the machine-readable progress line the Studio bridge parses."""
    print(f"PROGRESS {stage} {percent}", flush=True)


def _emit_report(report: dict) -> None:
    """Echo the report as the final stdout line, per the bridge contract."""
    print(json.dumps(report, sort_keys=True), flush=True)


def _set_error(report: dict, code: int, message: str, likely_cause: str) -> None:
    report["ok"] = False
    report["error"] = {"code": code, "message": message, "likely_cause": likely_cause}


def _maybe_write_json(report: dict, json_path: str | None, report_only: bool = False) -> None:
    """Write the report whenever --json was requested.

    ``--report-only`` suppresses *STL* output, not the report itself: the
    analysis is the entire point of that mode, and the Studio bridge needs it.
    """
    del report_only  # retained for call-site clarity; no longer suppresses JSON
    if json_path:
        write_json(report, json_path)


def main(argv: Sequence[str] | None = None) -> int:
    global _LAST_REPORT
    args = _parser().parse_args(argv)
    report = _empty_report(args.scan, args.base)
    _LAST_REPORT = report

    if not args.report_only and not args.out:
        _set_error(report, 2, "--out is required unless --report-only is used", "missing output path")
        print(report["error"]["message"], file=sys.stderr)
        _LAST_REPORT = report
        _emit_report(report)
        return 2

    try:
        _progress("load", 5)
        scan = load_mesh(args.scan)
        base = load_mesh(args.base)
        report["input"]["scan"] = mesh_report(scan, args.scan)
        report["input"]["base"] = mesh_report(base, args.base)
        _print_mesh("scan", report["input"]["scan"])
        _print_mesh("base", report["input"]["base"])

        _progress("clean", 20)
        cleaned, clean_report = clean_scan(scan, decimate=args.decimate)
        details = clean_report.as_dict()
        report["clean"] = details
        print(
            f"clean scan: {details['faces_before']} -> {details['faces_after']} faces; "
            f"components removed={details['components_removed']}, "
            f"degenerate={details['degenerate_faces_removed']}, duplicates={details['duplicate_faces_removed']}, "
            f"vertices merged={details['vertices_merged']}"
        )

        _progress("orient", 35)
        oriented = orient_scan(cleaned, flip=args.flip)
        report["orientation"] = oriented.report()
        print(
            f"orient scan: dominant axis -> Z, actual narrow end={oriented.narrow_end}, "
            f"spread ratio={oriented.spread_ratio:.4f}, flip={'yes' if args.flip else 'no'}"
        )

        _progress("scale", 45)
        scaled = scale_to_height(oriented.mesh, args.height)
        report["scale"] = scaled.report()
        if scaled.warning:
            prefix = "WARNING" if args.height is not None else "scale"
            print(f"{prefix}: {scaled.warning}")
        else:
            print(f"scale: factor={scaled.applied_factor:.6f}, target={scaled.target_height_mm:.3f} mm")

        _progress("pocket", 55)
        pocket = detect_pocket(base)
        pocket_report = pocket.as_dict()
        pocket_report["protected_extents_mm"] = protected_extents(pocket)
        report["pocket"] = pocket_report
        print(
            f"pocket: diameter={pocket.diameter_mm:.3f} mm, depth={pocket.depth_mm:.3f} mm, "
            f"center={pocket.center_mm}, mounting face={pocket.mounting_face}, protected wall=4.000 mm"
        )

        if args.report_only:
            report["ok"] = True
            report["error"] = None
            _LAST_REPORT = report
            _maybe_write_json(report, args.json_path)
            _progress("done", 100)
            print("report-only: analysis complete; no STL written")
            _emit_report(report)
            return 0

        _progress("boolean", 70)
        placed = graft.trim_and_place_scan(scaled.mesh, base, pocket, args.overlap)
        boolean_result = graft.union_meshes(placed, base)
        report["boolean"] = boolean_result.report()
        if boolean_result.fell_back:
            print(f"boolean: manifold3d failed; using trimesh fallback; {boolean_result.diagnostic}")
        else:
            print("boolean: manifold3d union succeeded")

        _progress("verify", 85)
        checks = run_verification(boolean_result.mesh, base, pocket, target_height_mm=args.height)
        report["checks"] = checks
        for check in checks:
            print(
                f"{'PASS' if check['pass'] else 'FAIL'} {check['name']}: "
                f"measured={check['measured']} expected={check['expected']}"
            )

        failure = first_failure(checks)
        if failure is not None:
            name, likely_cause = failure
            failed_path = failed_output_path(args.out)
            write_mesh(boolean_result.mesh, failed_path)
            report["output"] = mesh_report(boolean_result.mesh, failed_path)
            message = f"verification check failed: {name}"
            _set_error(report, 1, message, likely_cause)
            _LAST_REPORT = report
            _maybe_write_json(report, args.json_path)
            _progress("done", 100)
            print(f"{message}; likely cause: {likely_cause}", file=sys.stderr)
            _emit_report(report)
            return 1

        output_path = Path(args.out)
        write_mesh(boolean_result.mesh, output_path)
        report["output"] = mesh_report(boolean_result.mesh, output_path)
        report["ok"] = True
        report["error"] = None
        _LAST_REPORT = report
        _maybe_write_json(report, args.json_path)
        _progress("done", 100)
        print(f"output: verified STL written to {output_path}")
        _emit_report(report)
        return 0

    except (InputError, PocketDetectionError, ValueError) as exc:
        _set_error(report, 2, str(exc), "invalid, empty, mis-oriented, or unsupported input mesh")
        _LAST_REPORT = report
        _maybe_write_json(report, args.json_path)
        print(f"input error: {exc}", file=sys.stderr)
        _emit_report(report)
        return 2
    except graft.BooleanFailure as exc:
        report["boolean"] = {"engine": None, "fell_back": True, "diagnostic": str(exc)}
        _set_error(report, 3, "both boolean engines failed", str(exc))
        _LAST_REPORT = report
        _maybe_write_json(report, args.json_path)
        print(f"boolean failure: {exc}", file=sys.stderr)
        _emit_report(report)
        return 3


def entrypoint() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    entrypoint()
