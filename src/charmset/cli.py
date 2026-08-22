"""`charmset` — render a whole word as individual letter charms.

    charmset --text JOINLINKS --size large --out out/joinlinks

Each letter becomes its own STL with a jigsaw tab on the right and a socket on
the left, so the set assembles into the word. The first letter gets no socket
and the last no tab, giving the finished word clean outer edges.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.core.catalog import load_template
from src.core.runner import run_openscad
from src.core.validate import validate_stl

TEMPLATE_ID = "letter_charm"

# Only the values that actually differ between sizes. Everything else comes
# from the template defaults, so the schema stays the single source of truth.
SIZE_PRESETS: dict[str, dict[str, float]] = {
    "small": {
        "plate_w": 26, "plate_h": 32, "plate_th": 3, "letter_size": 17,
        "nfc_dia": 16, "joint_w": 6, "joint_depth": 4.5, "joint_head": 9,
        "magnet_dia": 4.2, "magnet_depth": 2.1, "bail_w": 8, "bail_h": 6,
    },
    "medium": {
        "plate_w": 33, "plate_h": 41, "plate_th": 3.5, "letter_size": 21,
        "nfc_dia": 26, "joint_w": 7.5, "joint_depth": 5.2, "joint_head": 11,
    },
    "large": {},  # template defaults are the large preset
}


class CharmsetError(RuntimeError):
    pass


def letter_filename(index: int, char: str) -> str:
    """Index-prefixed so repeated letters do not overwrite each other.

    "JOINLINKS" contains I, N and K more than once; naming purely by character
    would silently produce fewer files than letters.
    """
    return f"{index:02d}_{char}.stl"


def build_params(schema: dict, char: str, size: str, is_first: bool, is_last: bool,
                 overrides: dict | None = None) -> dict:
    if size not in SIZE_PRESETS:
        raise CharmsetError(f"unknown size '{size}'; choose from {sorted(SIZE_PRESETS)}")
    params = {k: v["default"] for k, v in schema["params"].items()}
    params.update(SIZE_PRESETS[size])
    params.update(overrides or {})
    params["letter"] = char
    params["end_left"] = 1 if is_first else 0
    params["end_right"] = 1 if is_last else 0
    return params


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="charmset", description=__doc__)
    parser.add_argument("--text", required=True, help="the word, e.g. JOINLINKS")
    parser.add_argument("--size", default="large", choices=sorted(SIZE_PRESETS))
    parser.add_argument("--out", required=True, help="output directory")
    parser.add_argument("--openscad", default="openscad")
    parser.add_argument("--chain-style", default="none", choices=["none", "cuban", "round"])
    parser.add_argument("--chain-links", type=int, default=8)
    parser.add_argument("--font", default=None)
    parser.add_argument("--no-nfc", action="store_true")
    parser.add_argument("--no-magnets", action="store_true")
    args = parser.parse_args(argv)

    letters = [c for c in args.text if not c.isspace()]
    if not letters:
        print("error: --text contains no printable letters", file=sys.stderr)
        return 2

    try:
        schema, scad = load_template(TEMPLATE_ID)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    overrides: dict = {"chain_style": args.chain_style, "chain_links": args.chain_links}
    if args.font is not None:
        overrides["font"] = args.font
    if args.no_nfc:
        overrides["nfc_enabled"] = 0
    if args.no_magnets:
        overrides["magnet_enabled"] = 0

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict = {"text": args.text, "size": args.size, "template": TEMPLATE_ID, "letters": []}
    failures = 0

    for index, char in enumerate(letters):
        params = build_params(
            schema, char, args.size,
            is_first=(index == 0), is_last=(index == len(letters) - 1),
            overrides=overrides,
        )
        destination = out_dir / letter_filename(index, char)
        print(f"[{index + 1}/{len(letters)}] {char} -> {destination.name}", flush=True)
        try:
            run_openscad(args.openscad, scad, destination, params)
        except RuntimeError as exc:
            print(f"  FAILED: {exc}".splitlines()[0], file=sys.stderr)
            failures += 1
            continue

        report = validate_stl(destination)
        if report.get("ok"):
            size_mm = [round(v, 2) for v in report["size_xyz_mm"]]
            print(f"  ok: {size_mm} mm, watertight={report['watertight']}")
        else:
            print(f"  INVALID: {report.get('error')}", file=sys.stderr)
            failures += 1
        manifest["letters"].append({"index": index, "letter": char,
                                    "file": destination.name,
                                    "params": params, "report": report})

    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    print(f"\n{len(letters) - failures}/{len(letters)} letters written to {out_dir}")
    if failures:
        print(f"{failures} failed", file=sys.stderr)
    return 1 if failures else 0


def entrypoint() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    entrypoint()
