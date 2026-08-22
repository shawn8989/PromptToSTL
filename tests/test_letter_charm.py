"""letter_charm geometry tests.

The joint is the part that can silently be wrong: a tab and socket can each
look fine alone and still not fit. These render real letters and check that two
of them actually nest without colliding.
"""
from __future__ import annotations

import shutil

import pytest
import trimesh

from src.charmset.cli import build_params, letter_filename
from src.core.catalog import load_template
from src.core.runner import run_openscad
from src.core.validate import validate_stl

OPENSCAD = shutil.which("openscad")
pytestmark = pytest.mark.skipif(OPENSCAD is None, reason="OpenSCAD not installed")


def _render(tmp_path, char, is_first=False, is_last=False, **overrides):
    schema, scad = load_template("letter_charm")
    params = build_params(schema, char, "large", is_first, is_last, overrides)
    out = tmp_path / f"{char}.stl"
    run_openscad(OPENSCAD, scad, out, params)
    return out, params


def test_charm_is_a_single_watertight_solid(tmp_path):
    out, _ = _render(tmp_path, "O")
    report = validate_stl(out)
    assert report["ok"], report
    assert report["watertight"], "a charm must be watertight to slice cleanly"
    assert len(trimesh.load_mesh(out, force="mesh").split(only_watertight=False)) == 1


def test_end_letters_lose_their_outer_joint(tmp_path):
    """First letter has no socket, last has no tab, so the word ends flat."""
    middle, params = _render(tmp_path / "m", "N")
    last, _ = _render(tmp_path / "l", "S", is_last=True)

    middle_w = trimesh.load_mesh(middle, force="mesh").extents[0]
    last_w = trimesh.load_mesh(last, force="mesh").extents[0]

    assert last_w == pytest.approx(params["plate_w"], abs=0.1), "last letter should be plate-width"
    assert middle_w > last_w + 5, "a middle letter must carry a protruding tab"


def test_two_letters_nest_without_colliding(tmp_path):
    """The real check: tab enters socket, and the solids do not interfere.

    Zero intersection volume proves they physically fit; the X overlap proves
    they are actually engaged rather than merely parked next to each other.
    """
    left, params = _render(tmp_path / "a", "J", is_first=True)
    right, _ = _render(tmp_path / "b", "O")

    a = trimesh.load_mesh(left, force="mesh")
    b = trimesh.load_mesh(right, force="mesh")
    b.apply_translation([params["plate_w"], 0, 0])  # slide the socket onto the tab

    overlap = a.bounds[1][0] - b.bounds[0][0]
    assert overlap > 5, f"tab and socket barely engage (only {overlap:.2f}mm)"

    collision = trimesh.boolean.intersection([a, b], engine="manifold")
    volume = 0.0 if collision.is_empty else abs(collision.volume)
    assert volume < 1.0, f"tab collides with socket by {volume:.2f}mm^3 — joint will not close"


def test_nfc_pocket_is_present_at_the_requested_size(tmp_path):
    """Volume must drop by roughly the pocket's cylinder when NFC is enabled."""
    without, params = _render(tmp_path / "n0", "O", nfc_enabled=0)
    with_pocket, _ = _render(tmp_path / "n1", "O", nfc_enabled=1)

    removed = abs(trimesh.load_mesh(without, force="mesh").volume) - abs(
        trimesh.load_mesh(with_pocket, force="mesh").volume
    )
    import math

    expected = math.pi * (params["nfc_dia"] / 2) ** 2 * params["nfc_depth"]
    assert removed == pytest.approx(expected, rel=0.15), (
        f"pocket removed {removed:.1f}mm^3, expected about {expected:.1f}mm^3"
    )


def test_repeated_letters_get_distinct_filenames():
    """JOINLINKS repeats I, N and K — naming by character alone loses files."""
    names = {letter_filename(i, c) for i, c in enumerate("JOINLINKS")}
    assert len(names) == 9


@pytest.mark.parametrize("style", ["cuban", "round"])
def test_chain_styles_actually_produce_links(tmp_path, style):
    """Guards a silent failure: BOSL2 torus() returns EMPTY geometry on
    OpenSCAD 2021.01, so `round` once rendered a chain with no links while
    still reporting success. Any style must measurably lengthen the part.
    """
    bare, _ = _render(tmp_path / "bare", "O", chain_style="none")
    chained, _ = _render(tmp_path / style, "O", chain_style=style, chain_links=8)

    bare_len = trimesh.load_mesh(bare, force="mesh").extents[1]
    chained_len = trimesh.load_mesh(chained, force="mesh").extents[1]

    assert chained_len > bare_len + 20, (
        f"chain_style='{style}' added only {chained_len - bare_len:.1f}mm — links are missing"
    )
