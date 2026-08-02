#!/usr/bin/env python3
"""Apply human-readable labels, units, groups and help text to every template
parameter, and hide the ones users can't meaningfully set.

Run after adding or changing a template:

    python scripts/apply_param_docs.py

Params land in one of these groups, which drives how app.py lays out the form:
  Text / Dimensions / Style  — shown inline (the settings people actually tune)
  Emblem / Advanced          — collapsed expanders (fine-tuning, rarely needed)
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Params the user cannot usefully set: either the app computes and overwrites
# them, or another control (a file uploader, a snap dropdown) owns them.
HIDE = {
    "offset_x", "offset_y",              # computed from the schema's text_box
    "emblem_enabled", "emblem_path",     # set by the SVG uploader
    "text_box_w", "text_box_h",          # duplicates of the computed text area
    "text_box_offset_x", "text_box_offset_y",
    "debug",                             # developer flag
    "photo_path", "photo_cols", "photo_rows",
}

# name -> (label, unit, group, help)
D: dict[str, tuple[str, str, str, str]] = {
    # ── Text ────────────────────────────────────────────────────────────────
    "line1": ("Line 1", "", "Text", "The main line of text."),
    "line2": ("Line 2", "", "Text", "A second line. Leave blank for one line."),
    "line3": ("Line 3", "", "Text", "A third line. Leave blank to skip it."),
    "text_size": ("Max text size", "mm", "Text",
                  "Cap on letter height. Text is shrunk automatically if it "
                  "doesn't fit, so this is a maximum, not a fixed size."),
    "line_gap": ("Line spacing", "mm", "Text",
                 "Vertical gap between lines. Reduced automatically if the "
                 "lines won't fit."),
    "text_align": ("Text alignment", "", "Style", "Left, centred, or right."),
    "text_anchor_y": ("Vertical position", "", "Style",
                      "Whether the text block sits at the top, middle, or "
                      "bottom of the plate."),
    "text_enabled": ("Include text", "", "Text",
                     "Turn the text off to get a plain blank design."),
    "qr_text": ("URL or text", "", "Text",
                "What the QR code opens or says when scanned."),

    # ── Style / finish ──────────────────────────────────────────────────────
    "emboss": ("Raised text", "", "Style",
               "1 = text sticks out of the surface, 0 = text is cut into it. "
               "Raised text is easier to print and to colour differently."),
    "text_height": ("Text height", "mm", "Style",
                    "How far the letters stick out (or how deep they're cut). "
                    "About 1 mm is plenty."),
    "shape": ("Shape", "", "Style", "The outline of the design."),
    "facets": ("Smoothness", "", "Style",
               "How many flat sides make the curve. 96+ looks perfectly round; "
               "6–10 gives a deliberately faceted, low-poly look."),

    # ── Dimensions ──────────────────────────────────────────────────────────
    "w": ("Width", "mm", "Dimensions", "Overall width."),
    "h": ("Height", "mm", "Dimensions", "Overall height."),
    "th": ("Thickness", "mm", "Dimensions",
           "How thick the plate is. 3–4 mm is sturdy for a tag or keychain."),
    "width": ("Width", "mm", "Dimensions", "Overall width."),
    "height": ("Height", "mm", "Dimensions", "Overall height."),
    "depth": ("Depth", "mm", "Dimensions", "Front-to-back depth of the base."),
    "size": ("Size", "mm", "Dimensions", "Overall size across."),
    "diameter": ("Diameter", "mm", "Dimensions", "Width across the circle."),
    "corner_r": ("Corner rounding", "mm", "Dimensions",
                 "How rounded the corners are. 0 gives sharp corners."),
    "tag_w": ("Tag width", "mm", "Dimensions", "Width of the tag."),
    "sign_h": ("Sign height", "mm", "Dimensions", "How tall the sign stands."),
    "plate_w": ("Plate width", "mm", "Dimensions", "Width of the backing plate."),
    "plate_h": ("Plate height", "mm", "Dimensions", "Height of the backing plate."),
    "plate_th": ("Plate thickness", "mm", "Dimensions", "How thick the backing plate is."),
    "base_th": ("Base thickness", "mm", "Advanced", "Thickness of the base slab."),
    "base_thick": ("Base thickness", "mm", "Advanced", "Thickness of the base layer."),
    "base_height": ("Base thickness", "mm", "Advanced",
                    "Solid backing behind the image. Keep at least 1 mm so the "
                    "print is strong."),

    # ── Padding / margins ───────────────────────────────────────────────────
    "pad": ("Edge padding", "mm", "Advanced", "Space kept clear around the text."),
    "pad_x": ("Side padding", "mm", "Advanced",
              "Clear space left and right of the text."),
    "pad_y": ("Top/bottom padding", "mm", "Advanced",
              "Clear space above and below the text."),
    "text_margin_x": ("Safe margin (sides)", "mm", "Advanced",
                      "Extra inset the text is kept inside horizontally."),
    "text_margin_y": ("Safe margin (top/bottom)", "mm", "Advanced",
                      "Extra inset the text is kept inside vertically."),
    "text_block_center_y": ("Nudge text up/down", "mm", "Advanced",
                            "Shift the whole text block vertically. 0 = centred."),

    # ── Holes / mounting ────────────────────────────────────────────────────
    "hole_d": ("Hole diameter", "mm", "Dimensions",
               "Size of the hole. ~4 mm suits a split ring or a screw."),
    "hole_offset": ("Hole inset", "mm", "Advanced",
                    "How far the holes sit in from the edge."),
    "hole_margin": ("Hole inset", "mm", "Advanced",
                    "How far the mounting holes sit in from the edge."),
    "holes": ("Add mounting holes", "", "Style", "1 = add screw holes, 0 = none."),
    "mount_holes": ("Add mounting holes", "", "Style",
                    "1 = add holes for wall screws, 0 = none."),
    "hole_ring": ("Hole reinforcement", "mm", "Advanced",
                  "Extra material ringing the hanger hole so it doesn't tear."),
    "screw_d": ("Screw hole diameter", "mm", "Advanced",
                "Match your screws — 4.2 mm suits a common #8 screw."),

    # ── Borders / rims / frames ─────────────────────────────────────────────
    "border": ("Border width", "mm", "Dimensions", "Plain edge around the image."),
    "border_w": ("Border width", "mm", "Dimensions",
                 "Width of the raised frame around the edge."),
    "border_th": ("Border height", "mm", "Advanced",
                  "How far the frame stands proud of the surface."),
    "frame_width": ("Frame width", "mm", "Dimensions",
                    "Solid border around the photo. Also what you hold, so "
                    "don't go below ~3 mm."),
    "rim": ("Raised rim", "", "Style",
            "1 = add a lip around the edge to catch drips, 0 = flat."),
    "rim_w": ("Rim width", "mm", "Advanced", "How wide the rim is."),
    "rim_h": ("Rim height", "mm", "Advanced", "How far the rim stands up."),

    # ── Lithophane ──────────────────────────────────────────────────────────
    "min_thickness": ("Thinnest layer", "mm", "Advanced",
                      "Where the photo is brightest. Thinner = brighter, but "
                      "below ~0.8 mm it gets fragile."),
    "max_thickness": ("Thickest layer", "mm", "Advanced",
                      "Where the photo is darkest. Thicker = more contrast, "
                      "but slower to print."),
    "min_thick": ("Thinnest layer", "mm", "Advanced",
                  "Where the photo is brightest. Thinner = brighter."),
    "max_thick": ("Thickest layer", "mm", "Advanced",
                  "Where the photo is darkest. Thicker = more contrast."),
    "heart_w": ("Heart width", "mm", "Dimensions", "Width of the heart."),
    "heart_h": ("Heart height", "mm", "Dimensions", "Height of the heart."),
    "letter_section_w": ("Letter panel width", "mm", "Dimensions",
                         "Width of each letter panel beside the photo."),
    "letter_size": ("Letter size", "mm", "Style", "Height of the big letters."),
    "letter_height": ("Letter height", "mm", "Style",
                      "How far the letters stick out."),
    "section_gap": ("Panel gap", "mm", "Advanced",
                    "Spacing between the letter panels and the heart."),

    # ── Magnets ─────────────────────────────────────────────────────────────
    "magnet_d": ("Magnet diameter", "mm", "Style",
                 "Pocket size — add ~0.4 mm to your magnet's size for a snug fit."),
    "magnet_depth": ("Magnet pocket depth", "mm", "Style",
                     "How deep the magnet sinks in. Slightly less than the "
                     "magnet's thickness so it sits flush."),
    "magnet_count": ("Number of magnets", "", "Style",
                     "More magnets hold heavier things."),
    "magnets": ("Add magnet pockets", "", "Style",
                "1 = add pockets underneath for magnets, 0 = none."),

    # ── Phone stand ─────────────────────────────────────────────────────────
    "tilt": ("Recline angle", "°", "Style",
             "90° stands the phone upright; lower values lean it back further."),
    "rest_h": ("Back rest height", "mm", "Dimensions",
               "How far up the back support reaches."),
    "phone_th": ("Phone slot width", "mm", "Style",
                 "Your phone's thickness including its case. 13 mm fits most."),
    "lip_h": ("Front lip height", "mm", "Style",
              "The ledge the phone rests on. Taller holds more securely but "
              "covers more of the screen."),
    "slot_w": ("Cable slot width", "mm", "Style",
               "Gap for a charging cable to pass through."),
    "slot_h": ("Strap slot width", "mm", "Dimensions",
               "Thickness of the slot the strap threads through."),
    "slot_zone": ("Strap slot area", "mm", "Advanced",
                  "Space reserved at the end for the strap slot."),

    # ── Wall hook ───────────────────────────────────────────────────────────
    "hook_d": ("Hook thickness", "mm", "Style",
               "How chunky the hook is. Thicker carries more weight."),
    "hook_reach": ("Hook reach", "mm", "Style",
                   "How far the hook sticks out from the wall."),
    "tip_up": ("Hook tip rise", "mm", "Style",
               "How far the tip curls up, stopping things sliding off."),

    # ── Planter / vase ──────────────────────────────────────────────────────
    "bottom_d": ("Base diameter", "mm", "Dimensions", "Width across the bottom."),
    "base_d": ("Base diameter", "mm", "Dimensions", "Width across the bottom."),
    "pot_h": ("Height", "mm", "Dimensions", "How tall the pot is."),
    "vase_h": ("Height", "mm", "Dimensions", "How tall the vase is."),
    "top_scale": ("Flare", "", "Style",
                  "How much wider the top is than the base. 1.0 = straight "
                  "sides, 1.35 = classic flower-pot flare."),
    "taper": ("Flare", "", "Style",
              "Top width relative to the base. Above 1 flares outward, below 1 "
              "narrows."),
    "wall": ("Wall thickness", "mm", "Dimensions",
             "How thick the sides are. ~2.4 mm is watertight and strong."),
    "floor_th": ("Floor thickness", "mm", "Dimensions", "How thick the bottom is."),
    "drain_holes": ("Drainage holes", "", "Style",
                    "How many holes in the bottom. 0 makes it watertight."),
    "drain_d": ("Drainage hole size", "mm", "Advanced", "Diameter of each hole."),
    "twist": ("Twist", "°", "Style",
              "How far the profile rotates from bottom to top. 0 = no twist."),
    "lobes": ("Number of lobes", "", "Style", "How many ridges run up the side."),
    "lobe_depth": ("Lobe depth", "", "Style",
                   "How pronounced the ridges are. 0 = smooth cylinder."),

    # ── Cookie cutter ───────────────────────────────────────────────────────
    "cut_h": ("Cutting depth", "mm", "Dimensions",
              "How deep it cuts — should exceed your dough thickness."),
    "cut_wall": ("Cutting edge thickness", "mm", "Advanced",
                 "Thinner cuts more cleanly but is more fragile. 0.8 mm is a "
                 "good balance."),
    "flange_w": ("Press flange width", "mm", "Advanced",
                 "The wide rim you push down on."),
    "flange_h": ("Press flange height", "mm", "Advanced",
                 "How tall the pressing rim is."),

    # ── Gridfinity ──────────────────────────────────────────────────────────
    "grid_x": ("Grid units wide", "", "Dimensions",
               "Each unit is 42 mm — the Gridfinity standard."),
    "grid_y": ("Grid units deep", "", "Dimensions", "Each unit is 42 mm."),
    "units_h": ("Height units", "", "Dimensions",
                "Each unit is 7 mm tall, on top of the 4.75 mm base."),

    # ── Badge / bail ────────────────────────────────────────────────────────
    "bail_enabled": ("Add hanging loop", "", "Style",
                     "1 = add a loop for a chain or keyring, 0 = none."),
    "bail_d": ("Loop diameter", "mm", "Style", "Size of the hanging loop."),
    "bail_thick": ("Loop thickness", "mm", "Advanced", "How chunky the loop is."),
    "bail_w": ("Loop width", "mm", "Advanced", "Width of the hanging loop."),
    "bail_h": ("Loop height", "mm", "Advanced", "Height of the hanging loop."),
    "bail_th": ("Loop thickness", "mm", "Advanced", "Thickness of the loop."),
    "bail_radius": ("Loop rounding", "mm", "Advanced", "Corner rounding on the loop."),
    "bail_gap": ("Loop gap", "mm", "Advanced", "Gap between the loop and the plate."),
    "bail_auto": ("Auto-place loop", "", "Advanced",
                  "1 = position the loop automatically, 0 = use the offsets below."),
    "bail_offset_x": ("Loop nudge (across)", "mm", "Advanced",
                      "Manual horizontal adjustment. Needs auto-place off."),
    "bail_offset_y": ("Loop nudge (up/down)", "mm", "Advanced",
                      "Manual vertical adjustment. Needs auto-place off."),

    # ── Cuban link chain ────────────────────────────────────────────────────
    "chain_layout_mode": ("Chain layout", "", "Style",
                          "How the chain is arranged around the pendant."),
    "chain_links": ("Number of links", "", "Style",
                    "Used when auto-fit links is off."),
    "chain_auto_links": ("Auto-fit links", "", "Style",
                         "1 = work out the link count from the plate size."),
    "chain_spacing": ("Link spacing", "mm", "Advanced", "Gap between links."),
    "chain_scale": ("Chain scale", "", "Style", "Overall size of the links."),
    "ring_radius": ("Ring radius", "mm", "Advanced",
                    "Radius the chain follows when laid in a ring."),
    "frame_gap": ("Frame gap", "mm", "Advanced",
                  "Space between the chain and the plate edge."),
    "frame_corner_r": ("Frame corner rounding", "mm", "Advanced",
                       "Corner rounding of the path the chain follows."),
    "link_cut": ("Link opening", "mm", "Advanced", "Size of the gap in each link."),
    "link_thickness": ("Link thickness", "mm", "Advanced", "How thick each link is."),
    "link_xr": ("Link width", "mm", "Advanced", "Half-width of a link."),
    "link_yr": ("Link height", "mm", "Advanced", "Half-height of a link."),
    "link_cd": ("Link curve depth", "mm", "Advanced", "Shapes the link's curve."),
    "link_ca": ("Link curve angle", "°", "Advanced", "Shapes the link's curve."),
    "match_chain_thickness": ("Match plate to chain", "", "Advanced",
                              "1 = make the plate as thick as the chain."),
    "plate_enabled": ("Include plate", "", "Style",
                      "1 = add a pendant plate inside the chain, 0 = chain only."),
    "plate_radius": ("Plate corner rounding", "mm", "Advanced",
                     "Corner rounding of the pendant plate."),
    "plate_auto_fit": ("Auto-size plate", "", "Style",
                       "1 = size the plate to the text automatically."),
    "plate_shape_mode": ("Plate shape", "", "Style", "Outline shape of the pendant."),
    "plate_outline_pad": ("Plate outline padding", "mm", "Advanced",
                          "Extra margin when the plate follows the text outline."),
    "plate_outline_round": ("Plate outline rounding", "mm", "Advanced",
                            "Smoothing applied to the outline shape."),
    "plate_offset_x": ("Plate nudge (across)", "mm", "Advanced",
                       "Manual horizontal adjustment of the plate."),
    "plate_offset_y": ("Plate nudge (up/down)", "mm", "Advanced",
                       "Manual vertical adjustment of the plate."),
    "emblem_auto_fit": ("Auto-fit emblem", "", "Emblem",
                        "1 = scale the emblem to the plate automatically."),

    # ── Emblem (all render inside the collapsed Emblem section) ─────────────
    "emblem_snap": ("Emblem position", "", "Emblem",
                    "Snap the emblem to a spot on the plate. Choose 'custom' "
                    "to place it by hand with the X/Y values below."),
    "emblem_autocenter": ("Auto-centre emblem", "", "Emblem",
                          "1 = centre it exactly when position is 'center'."),
    "emblem_scale": ("Emblem size", "", "Emblem",
                     "Scale factor for the uploaded SVG. 0.25 = quarter size."),
    "emblem_depth": ("Emblem height", "mm", "Emblem",
                     "How far the emblem stands out of (or cuts into) the surface."),
    "emblem_mode": ("Raised emblem", "", "Emblem",
                    "1 = emblem sticks out, 0 = it's cut into the surface."),
    "emblem_rot": ("Emblem rotation", "°", "Emblem", "Turn the emblem."),
    "emblem_x": ("Emblem X", "mm", "Emblem",
                 "Left/right position. Only used when Emblem position is 'custom'."),
    "emblem_y": ("Emblem Y", "mm", "Emblem",
                 "Up/down position. Only used when Emblem position is 'custom'."),
}


def main() -> int:
    changed = missing = 0
    unknown: set[str] = set()
    for d in sorted((ROOT / "templates").iterdir()):
        if not d.is_dir() or not (d / "schema.json").exists():
            continue
        path = d / "schema.json"
        schema = json.loads(path.read_text())
        for name, spec in schema.get("params", {}).items():
            if name in HIDE:
                spec["hidden"] = True
                continue
            entry = D.get(name)
            if entry is None:
                if not spec.get("hidden"):
                    unknown.add(name)
                    missing += 1
                continue
            label, unit, group, help_text = entry
            spec["label"] = label
            spec["group"] = group
            spec["help"] = help_text
            if unit:
                spec["unit"] = unit
            else:
                spec.pop("unit", None)
        path.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n")
        changed += 1

    print(f"updated {changed} schemas")
    if unknown:
        print(f"\n{missing} visible params with no entry in D:")
        for n in sorted(unknown):
            print("   ", n)
        return 1
    print("every visible parameter is documented ✓")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
