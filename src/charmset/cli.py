"""`charmset` — render text as individual letter charms that join into words.

    charmset --text JOINLINKS --size large --out out/joinlinks
    charmset --text "JOIN LINKS" --join magnet --out out/two-words
    charmset --text HELLO WORLD 2026 --assembled --out out/mixed

Whitespace separates words. Each word is its own connected run: its first letter
gets no socket and its last no tab, so every word ends flat. Words are rendered
into one output directory and laid out on separate rows in the assembled
preview.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

from src.core.catalog import load_template
from src.core.runner import run_openscad
from src.core.validate import validate_stl

TEMPLATE_ID = "letter_charm"
JOIN_MODES = ("jigsaw", "magnet", "both", "none")

# Only the values that actually differ between sizes. Everything else comes
# from the template defaults, so the schema stays the single source of truth.
SIZE_PRESETS: dict[str, dict[str, float]] = {
    "small": {
        "plate_w": 26, "plate_h": 32, "plate_th": 3, "letter_size": 17,
        "nfc_dia": 16, "joint_w": 6, "joint_depth": 4.5, "joint_head": 9,
        "magnet_dia": 3, "magnet_depth": 1.6, "bail_w": 8, "bail_h": 6,
    },
    "medium": {
        "plate_w": 33, "plate_h": 41, "plate_th": 3.5, "letter_size": 21,
        "nfc_dia": 26, "joint_w": 7.5, "joint_depth": 5.2, "joint_head": 11,
    },
    "large": {},  # template defaults are the large preset
}


class CharmsetError(RuntimeError):
    pass


def parse_words(chunks: list[str]) -> list[list[str]]:
    """Split the requested text into words, each a list of characters.

    A word is one connected run of charms. Splitting on whitespace is what lets
    the same tool make "JOINLINKS", "JOIN LINKS", or a single initial.
    """
    return [list(word) for chunk in chunks for word in chunk.split()]


def uses_jigsaw(join_mode: str) -> bool:
    return join_mode in ("jigsaw", "both")


def uses_magnets(join_mode: str) -> bool:
    return join_mode in ("magnet", "both")


def required_plate_th(params: dict) -> float:
    """Minimum plate thickness for the magnet slots to stay inside the plate.

    A slot lies axis-along-X so its *diameter* spans the thickness. At exactly
    magnet_dia the cylinder is tangent to both faces, which is a degenerate
    non-manifold surface, not merely thin — hence the wall on each side.
    """
    if not uses_magnets(params["join_mode"]):
        return 0.0
    return params["magnet_dia"] + 2 * params["magnet_wall"]


def nfc_fits(params: dict) -> tuple[bool, float]:
    """Does the NFC pocket clear the joint hardware?

    The jigsaw socket is cut into the -X edge and reaches inward; a pocket
    centred on the plate overlapped it and came out as a bitten-off circle.
    Magnet slots eat into both edges. The template auto-centres the pocket in
    whatever band is left, but on a narrow plate there may be no room, and that
    must be said rather than silently cropped.
    """
    left = 0.0
    right = 0.0
    if uses_jigsaw(params["join_mode"]):
        left = (params["joint_depth"] + params["joint_clearance"]) * 0.55 \
            + (params["joint_head"] + 2 * params["joint_clearance"]) / 2
    if uses_magnets(params["join_mode"]):
        reach = params["magnet_depth"] + 1
        left = max(left, reach)
        right = reach
    available = params["plate_w"] - left - right
    return params["nfc_dia"] <= available, available


_UNSAFE = re.compile(r"[^A-Za-z0-9]")


def safe_char(char: str) -> str:
    """A filename-safe stand-in for any character.

    Arbitrary text means characters like "/" and "?" reach this, and a raw "/"
    would silently write outside the output directory.
    """
    if _UNSAFE.match(char):
        name = unicodedata.name(char, "").split()[0].lower() or "x"
        return f"{name}-{ord(char):04X}"
    return char


def letter_filename(index: int, char: str, word_index: int | None = None) -> str:
    """Index-prefixed so repeated letters do not overwrite each other.

    "JOINLINKS" contains I, N and K more than once; naming purely by character
    would silently produce fewer files than letters. The index also keeps "a"
    and "A" apart on a case-insensitive filesystem.
    """
    prefix = "" if word_index is None else f"w{word_index + 1}_"
    return f"{prefix}{index:02d}_{safe_char(char)}.stl"


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
    params["plate_th"] = max(params["plate_th"], required_plate_th(params))
    return params


def write_assembled(rows: list[list[Path]], plate_w: float, plate_h: float,
                    destination: Path) -> Path:
    """One STL with every letter placed in reading order, one row per word.

    Individual files all load at the origin, so a slicer shows the whole set
    overlapping and the intended order is anyone's guess. This lays them out
    spelling the text, which is both the answer to "which order?" and a fit
    preview. It is not a print target — print the individual files.
    """
    import trimesh

    parts = []
    for row_index, row in enumerate(rows):
        for index, path in enumerate(row):
            mesh = trimesh.load_mesh(path, force="mesh")
            mesh.apply_translation([index * plate_w, -row_index * plate_h * 1.6, 0])
            parts.append(mesh)
    combined = trimesh.util.concatenate(parts)
    combined.export(destination)
    return destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="charmset", description=__doc__)
    parser.add_argument("--text", required=True, nargs="+",
                        help='the text; whitespace separates words, e.g. "JOIN LINKS"')
    parser.add_argument("--size", default="large", choices=sorted(SIZE_PRESETS))
    parser.add_argument("--out", required=True, help="output directory")
    parser.add_argument("--openscad", default="openscad")
    parser.add_argument("--join", default="jigsaw", choices=JOIN_MODES,
                        help="jigsaw = tab and socket; magnet = flat butt edges with "
                             "magnet slots; both; none. jigsaw and magnet are "
                             "alternatives, not a stack")
    parser.add_argument("--magnet-count", type=int, default=None,
                        help="magnet slots per side (magnet mode)")
    parser.add_argument("--chain-style", default="none", choices=["none", "cuban", "round"])
    parser.add_argument("--chain-links", type=int, default=8)
    parser.add_argument("--font", default=None)
    parser.add_argument("--no-nfc", action="store_true")
    parser.add_argument("--nfc-cover", default=None, choices=["sealed", "lid", "open"],
                        help="sealed = fully enclosed, insert during a print pause")
    parser.add_argument("--assembled", action="store_true",
                        help="also write assembled.stl with the text laid out in order")
    args = parser.parse_args(argv)

    words = parse_words(args.text)
    if not words:
        print("error: --text contains no printable characters", file=sys.stderr)
        return 2

    try:
        schema, scad = load_template(TEMPLATE_ID)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    overrides: dict = {
        "join_mode": args.join,
        "chain_style": args.chain_style,
        "chain_links": args.chain_links,
    }
    if args.magnet_count is not None:
        overrides["magnet_count"] = args.magnet_count
    if args.font is not None:
        overrides["font"] = args.font
    if args.no_nfc:
        overrides["nfc_enabled"] = 0
    if args.nfc_cover is not None:
        overrides["nfc_cover"] = args.nfc_cover

    probe = build_params(schema, words[0][0], args.size, True, False, overrides)
    preset_th = SIZE_PRESETS[args.size].get("plate_th", schema["params"]["plate_th"]["default"])
    if probe["plate_th"] > preset_th:
        print(
            f"note: plate thickened {preset_th} -> {probe['plate_th']}mm so a "
            f"{probe['magnet_dia']}mm magnet slot stays inside the plate."
        )
    fits, available = nfc_fits(probe)
    if probe["nfc_enabled"] and not fits:
        print(
            f"warning: a {probe['nfc_dia']}mm NFC pocket does not fit — only "
            f"{available:.1f}mm of plate clears the joint. Use a smaller tag, "
            f"a wider plate, or --no-nfc.",
            file=sys.stderr,
        )

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    multiword = len(words) > 1
    rows: list[list[Path]] = []
    manifest: dict = {
        "text": " ".join(args.text), "size": args.size, "join": args.join,
        "template": TEMPLATE_ID, "words": [],
    }
    failures = 0
    total = sum(len(word) for word in words)
    done = 0

    for word_index, word in enumerate(words):
        entries = []
        row: list[Path] = []
        for index, char in enumerate(word):
            params = build_params(
                schema, char, args.size,
                is_first=(index == 0), is_last=(index == len(word) - 1),
                overrides=overrides,
            )
            name = letter_filename(index, char, word_index if multiword else None)
            destination = out_dir / name
            done += 1
            print(f"[{done}/{total}] {char} -> {name}", flush=True)
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
            row.append(destination)
            entries.append({"index": index, "letter": char, "file": name,
                            "params": params, "report": report})
        manifest["words"].append({"index": word_index, "word": "".join(word),
                                  "letters": entries})
        if row:
            rows.append(row)

    if args.assembled and rows:
        assembled = write_assembled(rows, probe["plate_w"], probe["plate_h"],
                                    out_dir / "assembled.stl")
        print(f"assembled preview: {assembled.name} "
              f"({len(rows)} word(s) laid out in order — preview, not a print target)")
        manifest["assembled"] = assembled.name

    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    print(f"\n{total - failures}/{total} charms written to {out_dir}")
    if failures:
        print(f"{failures} failed", file=sys.stderr)
    return 1 if failures else 0


def entrypoint() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    entrypoint()
