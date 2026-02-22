// Cuban link chain (BOSL2-based, clean-room)
// Requires lib/BOSL2 vendored in this repo.

include "../../lib/BOSL2/std.scad";
include "../../lib/BOSL2/beziers.scad";

// Chain layout
chain_layout_mode = "frame"; // line | ring | frame
chain_links = 54;
chain_auto_links = 1;
chain_spacing = 0;
chain_scale = 1; // overall link scale
ring_radius = 70;

// Frame path (for pendant wrap)
frame_gap = 6;
frame_corner_r = 18;

// Link geometry (bezier sweep)
link_cut = 2.4;
link_thickness = 5.2;
link_xr = 7.4;
link_yr = 10;
link_cd = 5.6;
link_ca = 45;

// Pendant plate
plate_enabled = 1;
plate_w = 60;
plate_h = 24;
plate_th = 4;
plate_radius = 4;
plate_offset_x = 0;
plate_offset_y = 0;
plate_auto_fit = 0;

// Bail (connector)
bail_enabled = 1;
bail_auto = 1;
bail_w = 12;
bail_h = 18;
bail_th = 4;
bail_radius = 3;
bail_gap = -2;
bail_offset_x = 0;
bail_offset_y = 0;

// Text
text_enabled = 1;
line1 = "CUSTOM";
line2 = "";
line3 = "";
text_size = 10;
text_height = 1.2;
line_gap = 8;
offset_x = 0;
offset_y = 0;
text_align = "center";
emboss = 1;

// Emblem
emblem_enabled = 0;
emblem_path = "";
emblem_scale = 0.25;
emblem_x = 0;
emblem_y = 0;
emblem_rot = 0;
emblem_mode = 1;
emblem_depth = 1.2;
emblem_auto_fit = 0;

// Misc
match_chain_thickness = 1;
$fa = 6;
$fs = 0.8;

// Derived
link_th = link_thickness * chain_scale;
bez_xr = link_xr * chain_scale;
bez_yr = link_yr * chain_scale;
bez_cd = link_cd * chain_scale;
cut_eff = link_cut * chain_scale;

plate_th_eff = match_chain_thickness == 1 ? link_th : plate_th;
bail_th_eff = match_chain_thickness == 1 ? link_th : bail_th;
emblem_depth_eff = match_chain_thickness == 1 ? link_th : emblem_depth;

module rounded_rect_2d(width, height, radius) {
  r_eff = min(radius, min(width, height) / 2);
  hull() {
    translate([ width/2 - r_eff,  height/2 - r_eff]) circle(r=r_eff);
    translate([-width/2 + r_eff,  height/2 - r_eff]) circle(r=r_eff);
    translate([ width/2 - r_eff, -height/2 + r_eff]) circle(r=r_eff);
    translate([-width/2 + r_eff, -height/2 + r_eff]) circle(r=r_eff);
  }
}

function chain_mode() =
  chain_layout_mode == "line" ? 0 :
  chain_layout_mode == "ring" ? 1 :
  chain_layout_mode == "frame" ? 2 :
  2;

function link_bezpath(xr, yr, cd, angle) =
  flatten([
    bez_begin([-xr, 0, 0], 90, cd, p=angle),
    bez_tang([0, yr, 0], 0, cd, p=180-angle),
    bez_tang([xr, 0, 0], -90, cd, p=angle),
    bez_tang([0, -yr, 0], 0, cd, p=-(180-angle)),
    bez_end([-xr, 0, 0], -90, cd, p=(180-angle))
  ]);

link_path = link_bezpath(bez_xr, bez_yr, bez_cd, link_ca);
link_vnf = bezpath_sweep(circle(r=link_th/2), link_path, splinesteps=12, closed=true);
link_bounds = pointlist_bounds(vnf_vertices(link_vnf));
link_dims = link_bounds[1] - link_bounds[0];
link_w = link_dims[0];
link_l = link_dims[1];
link_h = max(0.2, link_dims[2] - cut_eff * 2);

function frame_w() = plate_w + 2 * frame_gap + link_w;
function frame_h() = plate_h + 2 * frame_gap + link_w;
function frame_r() = min(frame_corner_r, min(frame_w(), frame_h()) / 2);

function link_step() = (link_l + link_th * 0.25) * 0.5 + chain_spacing;

module link_geom() {
  intersection() {
    vnf_polyhedron(link_vnf);
    cube([link_w, link_l, link_h], center=true);
  }
}

module chain_frame() {
  path = rect([frame_w(), frame_h()], rounding=frame_r());
  if (chain_auto_links == 1) {
    path_copies(path, spacing=link_step(), closed=true)
      zrot(90)
        link_geom();
  } else {
    path_copies(path, n=chain_links, closed=true)
      zrot(90)
        link_geom();
  }
}

module chain_ring() {
  path = circle(r=ring_radius);
  if (chain_auto_links == 1) {
    path_copies(path, spacing=link_step(), closed=true)
      zrot(90)
        link_geom();
  } else {
    path_copies(path, n=chain_links, closed=true)
      zrot(90)
        link_geom();
  }
}

module chain_line() {
  len = max(10, chain_links * link_step());
  path = [[-len/2, 0], [len/2, 0]];
  if (chain_auto_links == 1) {
    path_copies(path, spacing=link_step(), closed=false)
      zrot(90)
        link_geom();
  } else {
    path_copies(path, n=chain_links, closed=false)
      zrot(90)
        link_geom();
  }
}

module chain_body() {
  if (chain_mode() == 0) {
    chain_line();
  } else if (chain_mode() == 1) {
    chain_ring();
  } else {
    chain_frame();
  }
}

module plate_body() {
  if (plate_enabled == 1) {
    translate([plate_offset_x, plate_offset_y, 0])
      linear_extrude(height=plate_th_eff, center=true)
        rounded_rect_2d(plate_w, plate_h, plate_radius);
  }
}

module bail_body() {
  if (bail_enabled == 1) {
    bx = bail_auto == 1 ? 0 : bail_offset_x;
    by = bail_auto == 1 ? (frame_h()/2 - bail_h/2 - bail_gap) : bail_offset_y;
    translate([plate_offset_x + bx, plate_offset_y + by, 0])
      linear_extrude(height=bail_th_eff, center=true)
        rounded_rect_2d(bail_w, bail_h, bail_radius);
  }
}

module line_text_3d(s, y) {
  translate([plate_offset_x + offset_x, plate_offset_y + offset_y + y, 0])
    linear_extrude(height=text_height)
      text(s, size=text_size, halign=text_align, valign="center");
}

module text_union() {
  if (plate_enabled == 1 && text_enabled == 1) {
    if (line2 == "" && line3 == "") {
      line_text_3d(line1, 0);
    } else if (line3 == "") {
      line_text_3d(line1, line_gap / 2);
      line_text_3d(line2, -line_gap / 2);
    } else {
      line_text_3d(line1, line_gap);
      line_text_3d(line2, 0);
      line_text_3d(line3, -line_gap);
    }
  }
}

module emblem_3d(z) {
  if (plate_enabled == 1 && emblem_enabled == 1 && emblem_path != "") {
    translate([plate_offset_x + emblem_x, plate_offset_y + emblem_y, z])
      rotate([0, 0, emblem_rot])
        scale([emblem_scale, emblem_scale, 1])
          linear_extrude(height=emblem_depth_eff)
            import(emblem_path);
  }
}

module body() {
  union() {
    chain_body();
    plate_body();
    bail_body();
  }
}

plate_top_z = plate_th_eff / 2;

if (emboss == 1) {
  union() {
    difference() {
      body();
      if (emblem_mode == 0) {
        emblem_3d(plate_top_z - emblem_depth_eff);
      }
    }
    translate([0, 0, plate_top_z]) text_union();
    if (emblem_mode == 1) {
      emblem_3d(plate_top_z);
    }
  }
} else {
  difference() {
    body();
    translate([0, 0, plate_top_z - text_height]) text_union();
    if (emblem_mode == 0) {
      emblem_3d(plate_top_z - emblem_depth_eff);
    }
  }
  if (emblem_mode == 1) {
    emblem_3d(plate_top_z);
  }
}
