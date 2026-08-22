"""letter_charm geometry tests.

The joint is the part that can silently be wrong: a tab and socket can each
look fine alone and still not fit. These render real letters and check that two
of them actually nest without colliding.
"""
from __future__ import annotations

import math
import shutil

import pytest
import trimesh

from src.charmset.cli import (
    build_params,
    letter_filename,
    parse_words,
    required_plate_th,
)
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
    """An open-pocket charm is one shell. (A sealed pocket adds an interior
    void shell by design, so shell-counting only applies to `open`.)"""
    out, _ = _render(tmp_path, "O", nfc_cover="open")
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


def test_nfc_pocket_is_a_complete_circle(tmp_path):
    """The pocket must not be clipped by the jigsaw socket.

    The socket is cut into the -X edge and reaches ~10mm inward. A pocket
    centred on the plate overlapped it by 3.19mm and printed as a bitten-off
    circle. The template now auto-centres the pocket in the clear region, so
    the removed volume should match a full cylinder to within facet rounding —
    a loose tolerance here is exactly what hid the original bug.
    """
    import math

    without, params = _render(tmp_path / "n0", "O", nfc_enabled=0)
    with_pocket, _ = _render(tmp_path / "n1", "O", nfc_enabled=1, nfc_cover="sealed")

    removed = abs(trimesh.load_mesh(without, force="mesh").volume) - abs(
        trimesh.load_mesh(with_pocket, force="mesh").volume
    )
    expected = math.pi * (params["nfc_dia"] / 2) ** 2 * params["nfc_depth"]
    assert removed == pytest.approx(expected, rel=0.02), (
        f"pocket removed {removed:.1f}mm^3 of an expected {expected:.1f}mm^3 — "
        "something is clipping the circle"
    )


@pytest.mark.parametrize("cover", ["open", "sealed", "lid"])
def test_every_nfc_cover_mode_builds(tmp_path, cover):
    out, _ = _render(tmp_path / cover, "O", nfc_cover=cover)
    assert validate_stl(out)["ok"]


def test_lid_mode_emits_a_separate_cap(tmp_path):
    """`lid` must produce a second body, or there is nothing to cover with."""
    plain, _ = _render(tmp_path / "p", "O", nfc_cover="open")
    lidded, _ = _render(tmp_path / "l", "O", nfc_cover="lid")

    plain_parts = len(trimesh.load_mesh(plain, force="mesh").split(only_watertight=False))
    lid_parts = len(trimesh.load_mesh(lidded, force="mesh").split(only_watertight=False))
    assert lid_parts == plain_parts + 1, "no lid disc was generated"


def test_magnet_slots_actually_remove_material(tmp_path):
    """Guards a placement bug: the slots once sat outside the plate entirely
    (x = -23.3 on a plate ending at -20) and cut nothing at all."""
    # The baseline must match on everything but the slots. Magnet mode squares
    # off its mating edges and the plate is auto-thickened to fit the magnets,
    # so pin plate_radius and plate_th or the comparison measures those instead.
    on, params = _render(tmp_path / "m1", "O", join_mode="magnet", plate_radius=0)
    off, _ = _render(tmp_path / "m0", "O", join_mode="none", plate_radius=0,
                     plate_th=params["plate_th"])

    removed = abs(trimesh.load_mesh(off, force="mesh").volume) - abs(
        trimesh.load_mesh(on, force="mesh").volume
    )
    slots = 2 * params["magnet_count"]
    one_slot = math.pi * (params["magnet_dia"] / 2) ** 2 * params["magnet_depth"]
    assert removed == pytest.approx(slots * one_slot, rel=0.05), (
        f"magnet slots removed {removed:.1f}mm^3 of an expected "
        f"{slots * one_slot:.1f}mm^3 — wrong count, or placed outside the solid?"
    )


def test_jigsaw_and_magnets_are_alternatives(tmp_path):
    """Choosing one joining style must not leave traces of the other.

    Magnet mode is a flat butt joint: no protruding tab, so the part is exactly
    plate-width. Jigsaw mode carries no magnet slots.
    """
    magnet, params = _render(tmp_path / "mag", "O", join_mode="magnet")
    jig, _ = _render(tmp_path / "jig", "O", join_mode="jigsaw")

    magnet_w = trimesh.load_mesh(magnet, force="mesh").extents[0]
    assert magnet_w == pytest.approx(params["plate_w"], abs=0.1), (
        "magnet mode must have flat edges, not a jigsaw tab"
    )
    assert trimesh.load_mesh(jig, force="mesh").extents[0] > params["plate_w"] + 5

    bare, _ = _render(tmp_path / "bare", "O", join_mode="none",
                      plate_th=params["plate_th"], plate_radius=0)
    jig_full, _ = _render(tmp_path / "jf", "O", join_mode="jigsaw",
                          plate_th=params["plate_th"], plate_radius=0,
                          end_left=1, end_right=1)
    # With both ends capped a jigsaw charm is a plain plate; if magnet slots
    # were still being cut it would be lighter than the no-joint version.
    assert abs(trimesh.load_mesh(jig_full, force="mesh").volume) == pytest.approx(
        abs(trimesh.load_mesh(bare, force="mesh").volume), rel=0.02
    ), "jigsaw mode is still cutting magnet slots"


def test_magnet_slots_stay_inside_the_plate(tmp_path):
    """A slot lies axis-along-X, so its diameter spans the thickness.

    At plate_th == magnet_dia the cylinder is tangent to both faces, which
    OpenSCAD reports as a non-manifold surface. The plate must be thickened.
    """
    out, params = _render(tmp_path / "t", "O", join_mode="magnet")
    assert params["plate_th"] >= params["magnet_dia"] + 2 * params["magnet_wall"]

    mesh = trimesh.load_mesh(out, force="mesh")
    assert mesh.is_watertight, "magnet slot broke through the plate faces"


def test_thin_plates_are_thickened_for_magnets():
    """The small preset's 3mm plate cannot hold any magnet unaided."""
    schema, _ = load_template("letter_charm")
    thin = build_params(schema, "I", "small", False, False, {"join_mode": "magnet"})
    assert thin["plate_th"] == pytest.approx(required_plate_th(thin))
    assert required_plate_th({**thin, "join_mode": "jigsaw"}) == 0.0


def test_two_magnet_letters_butt_without_overlapping(tmp_path):
    """Flat edges must meet exactly at plate_w, forming one continuous word."""
    left, params = _render(tmp_path / "a", "J", is_first=True, join_mode="magnet")
    right, _ = _render(tmp_path / "b", "O", join_mode="magnet")

    a = trimesh.load_mesh(left, force="mesh")
    b = trimesh.load_mesh(right, force="mesh")
    b.apply_translation([params["plate_w"], 0, 0])

    collision = trimesh.boolean.intersection([a, b], engine="manifold")
    volume = 0.0 if collision.is_empty else abs(collision.volume)
    assert volume < 0.5, f"butted plates overlap by {volume:.2f}mm^3"

    gap = b.bounds[0][0] - a.bounds[1][0]
    assert abs(gap) < 0.1, f"a {gap:.2f}mm seam would be visible between letters"


def test_words_split_on_whitespace():
    assert parse_words(["JOIN LINKS"]) == [list("JOIN"), list("LINKS")]
    assert parse_words(["HELLO", "WORLD 2026"]) == [
        list("HELLO"), list("WORLD"), list("2026")
    ]
    assert parse_words(["   "]) == []


def test_filenames_are_safe_and_distinct_across_words():
    """Arbitrary text reaches the filesystem: "/" must not escape the out dir,
    and the same letter in two words must not collide."""
    a = letter_filename(0, "J", word_index=0)
    b = letter_filename(0, "J", word_index=1)
    assert a != b
    slash = letter_filename(1, "/")
    assert "/" not in slash
    amp = letter_filename(2, "&")
    assert "/" not in amp and amp.endswith(".stl")


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
