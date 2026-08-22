// letter_charm — one letter on a uniform plate, with an NFC pocket,
// jigsaw tab/socket, optional magnets, a bail, and an optional chain.
//
// Every letter uses the SAME plate width for a given size, which is what makes
// the set work: a 25mm NFC tag fits behind a narrow "I", the jigsaw tabs always
// land in the same place so any letter mates with any other, and nothing
// depends on glyph metrics (OpenSCAD 2021.01 has no textmetrics()).

include <../../lib/BOSL2/std.scad>;

/* [Letter] */
letter          = "J";
font            = "";          // "" = OpenSCAD default; e.g. "Liberation Sans:style=Bold"
letter_size     = 26;          // glyph cap height, mm
letter_depth    = 1.6;         // raised height, or engraved depth when emboss=0
emboss          = 1;           // 1 = raised, 0 = engraved
letter_offset_x = 0;
letter_offset_y = 0;

/* [Plate] */
plate_w      = 40;
plate_h      = 50;
plate_th     = 4;
plate_radius = 4;

/* [NFC pocket] */
nfc_enabled = 1;
nfc_dia     = 26;              // 25mm sticker + fit clearance
nfc_depth   = 0.8;
nfc_offset_y = -6;             // biased away from the bail

/* [Jigsaw joint] */
joint_enabled   = 1;
joint_w         = 9;           // neck width
joint_depth     = 6;           // how far the tab protrudes
joint_head      = 13;          // widest part of the head
joint_clearance = 0.25;        // socket is grown by this
end_left        = 0;           // 1 = no socket (first letter of the word)
end_right       = 0;           // 1 = no tab   (last letter of the word)

/* [Magnets] */
magnet_enabled = 1;
magnet_dia     = 6.2;
magnet_depth   = 3.1;

/* [Bail] */
bail_enabled = 1;
bail_w       = 10;
bail_h       = 7;
bail_th      = 3;
bail_hole_d  = 4;
bail_gap     = 0.6;

/* [Chain] */
chain_style    = "none";       // none | cuban | round
chain_links    = 8;
link_clearance = 0.4;          // print-in-place gap between links
link_thickness = 3.2;
link_xr        = 4.6;
link_yr        = 6.2;
link_cd        = 3.4;
link_ca        = 45;
link_cut       = 1.4;

$fa = 6;
$fs = 0.8;

// ---------------------------------------------------------------- helpers

module rounded_rect_2d(width, height, radius) {
  r_eff = min(radius, min(width, height) / 2);
  hull() {
    translate([ width/2 - r_eff,  height/2 - r_eff]) circle(r=r_eff);
    translate([-width/2 + r_eff,  height/2 - r_eff]) circle(r=r_eff);
    translate([ width/2 - r_eff, -height/2 + r_eff]) circle(r=r_eff);
    translate([-width/2 + r_eff, -height/2 + r_eff]) circle(r=r_eff);
  }
}

// One profile drives both the tab and the socket, so they cannot drift apart.
// `grow` inflates it for the socket to create the fit clearance.
module joint_profile_2d(grow = 0) {
  neck = joint_w + 2 * grow;
  head = joint_head + 2 * grow;
  d    = joint_depth + grow;
  hull() {
    translate([0, 0]) square([0.01, neck], center = true);
    translate([d * 0.55, 0]) circle(d = head);
  }
}

module text_2d() {
  translate([letter_offset_x, letter_offset_y])
    if (font == "")
      text(letter, size = letter_size, halign = "center", valign = "center");
    else
      text(letter, size = letter_size, font = font, halign = "center", valign = "center");
}

// ---------------------------------------------------------------- body

module plate_2d() {
  union() {
    rounded_rect_2d(plate_w, plate_h, plate_radius);
    if (joint_enabled == 1 && end_right == 0)
      translate([plate_w / 2, 0]) joint_profile_2d(0);
  }
}

module bail_body() {
  if (bail_enabled == 1) {
    translate([0, plate_h / 2 + bail_h / 2 - bail_gap, 0])
      linear_extrude(height = bail_th, center = true)
        difference() {
          rounded_rect_2d(bail_w, bail_h, bail_h / 2.5);
          circle(d = bail_hole_d);
        }
  }
}

module cutaways() {
  // Jigsaw socket on the -X edge.
  if (joint_enabled == 1 && end_left == 0)
    translate([-plate_w / 2, 0, 0])
      linear_extrude(height = plate_th + 2, center = true)
        joint_profile_2d(joint_clearance);

  // NFC pocket, opening on the back face (-Z).
  if (nfc_enabled == 1)
    translate([0, nfc_offset_y, -plate_th / 2 - 0.01])
      cylinder(d = nfc_dia, h = nfc_depth + 0.01);

  // Magnet pockets: one in the tab, one behind the socket, so a tab meeting a
  // socket puts two magnets face to face.
  if (magnet_enabled == 1) {
    if (end_right == 0)
      translate([plate_w / 2 + joint_depth * 0.55, 0, 0])
        rotate([0, 90, 0])
          cylinder(d = magnet_dia, h = magnet_depth, center = true);
    if (end_left == 0)
      translate([-plate_w / 2 - joint_depth * 0.55, 0, 0])
        rotate([0, 90, 0])
          cylinder(d = magnet_dia, h = magnet_depth, center = true);
  }

  if (emboss == 0)
    translate([0, 0, plate_th / 2 - letter_depth])
      linear_extrude(height = letter_depth + 0.01)
        text_2d();
}

module charm() {
  difference() {
    union() {
      linear_extrude(height = plate_th, center = true) plate_2d();
      bail_body();
      if (emboss == 1)
        translate([0, 0, plate_th / 2])
          linear_extrude(height = letter_depth)
            text_2d();
    }
    cutaways();
  }
}

// ---------------------------------------------------------------- chain

cut_eff = min(link_cut, link_thickness / 2 - 0.1);
bez_xr  = max(0.5, link_xr);
bez_yr  = max(0.5, link_yr);
bez_cd  = max(0.1, link_cd);
link_th = max(0.4, link_thickness);

function link_bezpath(xr, yr, cd, angle) =
  flatten([
    bez_begin([-xr, 0, 0], 90, cd, p=angle),
    bez_tang([0, yr, 0], 0, cd, p=180-angle),
    bez_tang([xr, 0, 0], -90, cd, p=angle),
    bez_tang([0, -yr, 0], 0, cd, p=-(180-angle)),
    bez_end([-xr, 0, 0], -90, cd, p=(180-angle))
  ]);

link_path   = link_bezpath(bez_xr, bez_yr, bez_cd, link_ca);
link_vnf    = bezpath_sweep(circle(r=link_th/2), link_path, splinesteps=12, closed=true);
link_bounds = pointlist_bounds(vnf_vertices(link_vnf));
link_dims   = link_bounds[1] - link_bounds[0];
link_w      = link_dims[0];
link_l      = link_dims[1];
link_h      = max(0.2, link_dims[2] - cut_eff * 2);

function link_step() = (link_l + link_th * 0.25) * 0.5 + link_clearance;

module cuban_link() {
  intersection() {
    vnf_polyhedron(link_vnf);
    cube([link_w, link_l, link_h], center=true);
  }
}

module round_link() {
  // Native rotate_extrude rather than BOSL2 torus(): on OpenSCAD 2021.01
  // torus() returns empty geometry, which silently produced a chain with no
  // links at all.
  rotate_extrude(convexity = 4)
    translate([link_yr, 0])
      circle(r = link_th / 2);
}

module one_link() {
  if (chain_style == "round") round_link(); else cuban_link();
}

module chain_body() {
  if (chain_style != "none" && chain_links > 0) {
    start_y = plate_h / 2 + bail_h + link_step();
    for (i = [0 : chain_links - 1])
      translate([0, start_y + i * link_step(), 0])
        zrot(i % 2 == 0 ? 0 : 90)
          one_link();
  }
}

// ---------------------------------------------------------------- output

charm();
chain_body();
