// Cuban link chain (improved)
// Layout modes: line, ring, frame

chain_layout = 2; // fallback: 0=line, 1=ring, 2=frame
chain_layout_mode = "frame"; // preferred: line | ring | frame

link_count = 44;
link_auto = 1;
link_outer_d = 16;
link_band = 5;
link_th = 4;
link_flatten = 0.6;
link_overlap = 0.45;
ring_radius = 60;

frame_auto = 1;
frame_gap = 6;
frame_w = 120;
frame_h = 90;
frame_corner_r = 14;

plate_enabled = 1;
plate_w = 50;
plate_h = 20;
plate_th = 3;
plate_radius = 3;
plate_offset_x = 0;
plate_offset_y = 0;

bail_enabled = 1;
bail_auto = 1;
bail_w = 10;
bail_h = 16;
bail_th = 3;
bail_radius = 2;
bail_gap = 0;
bail_offset_x = 0;
bail_offset_y = 0;

text_enabled = 1;
line1 = "CUSTOM";
line2 = "";
line3 = "";
text_size = 10;
text_height = 1.0;
line_gap = 8;
offset_x = 0;
offset_y = 0;
text_align = "center";
emboss = 1;

emblem_enabled = 0;
emblem_path = "";
emblem_scale = 0.25;
emblem_x = 0;
emblem_y = 0;
emblem_rot = 0;
emblem_mode = 1;
emblem_depth = 1.2;

$fn = 64;

module rounded_rect_2d(width, height, radius) {
  r_eff = min(radius, min(width, height) / 2);
  hull() {
    translate([ width/2 - r_eff,  height/2 - r_eff]) circle(r=r_eff);
    translate([-width/2 + r_eff,  height/2 - r_eff]) circle(r=r_eff);
    translate([ width/2 - r_eff, -height/2 + r_eff]) circle(r=r_eff);
    translate([-width/2 + r_eff, -height/2 + r_eff]) circle(r=r_eff);
  }
}

function _layout_mode() =
  chain_layout_mode == "line" ? 0 :
  chain_layout_mode == "ring" ? 1 :
  chain_layout_mode == "frame" ? 2 :
  chain_layout;

function _frame_w() = frame_auto == 1 ? (plate_w + 2 * frame_gap + link_outer_d) : frame_w;
function _frame_h() = frame_auto == 1 ? (plate_h + 2 * frame_gap + link_outer_d) : frame_h;
function _frame_r(w, h) = min(frame_corner_r, min(w, h) / 2);
function _arc_len(r) = r * PI / 2;
function _frame_perim(w, h, r) = 2 * (w - 2 * r) + 2 * (h - 2 * r) + 4 * _arc_len(r);
function _wrap(t, perim) = t - floor(t / perim) * perim;

function _frame_at(t, w, h, r) =
  let(
    r_eff = max(0.01, _frame_r(w, h)),
    seg1 = w - 2 * r_eff,
    seg2 = h - 2 * r_eff,
    arc = _arc_len(r_eff),
    perim = _frame_perim(w, h, r_eff),
    tt = _wrap(t, perim)
  )
  (tt < seg1) ? [ [-w/2 + r_eff + tt, h/2], 0 ] :
  (tt < seg1 + arc) ?
    let(
      a = 90 - (tt - seg1) / arc * 90,
      cx = w/2 - r_eff,
      cy = h/2 - r_eff
    )
    [ [cx + r_eff * cos(a), cy + r_eff * sin(a)], a - 90 ] :
  (tt < seg1 + arc + seg2) ?
    [ [w/2, h/2 - r_eff - (tt - seg1 - arc)], -90 ] :
  (tt < seg1 + 2 * arc + seg2) ?
    let(
      a = 0 - (tt - seg1 - arc - seg2) / arc * 90,
      cx = w/2 - r_eff,
      cy = -h/2 + r_eff
    )
    [ [cx + r_eff * cos(a), cy + r_eff * sin(a)], a - 90 ] :
  (tt < 2 * seg1 + 2 * arc + seg2) ?
    [ [w/2 - r_eff - (tt - seg1 - 2 * arc - seg2), -h/2], 180 ] :
  (tt < 2 * seg1 + 3 * arc + seg2) ?
    let(
      a = -90 - (tt - 2 * seg1 - 2 * arc - seg2) / arc * 90,
      cx = -w/2 + r_eff,
      cy = -h/2 + r_eff
    )
    [ [cx + r_eff * cos(a), cy + r_eff * sin(a)], a - 90 ] :
  (tt < 2 * seg1 + 3 * arc + 2 * seg2) ?
    [ [-w/2, -h/2 + r_eff + (tt - 2 * seg1 - 3 * arc - seg2)], 90 ] :
  let(
    a = 180 - (tt - 2 * seg1 - 3 * arc - 2 * seg2) / arc * 90,
    cx = -w/2 + r_eff,
    cy = h/2 - r_eff
  )
  [ [cx + r_eff * cos(a), cy + r_eff * sin(a)], a - 90 ];

function _link_count(perim) =
  link_auto == 1 ? max(4, floor(perim / (link_outer_d * (1 - link_overlap)))) : link_count;

module link_shape() {
  inner_d = max(1, link_outer_d - 2 * link_band);
  scale([1, link_flatten, 1])
    difference() {
      cylinder(d=link_outer_d, h=link_th, center=true);
      cylinder(d=inner_d, h=link_th + 0.2, center=true);
    }
}

module chain_line() {
  pitch = link_outer_d * (1 - link_overlap);
  total = (link_count - 1) * pitch;
  for (i = [0 : link_count - 1]) {
    x = -total / 2 + i * pitch;
    translate([x, 0, 0])
      rotate([0, (i % 2) * 90, 0])
        link_shape();
  }
}

module chain_ring() {
  for (i = [0 : link_count - 1]) {
    angle = 360 / link_count * i;
    rotate([0, 0, angle])
      translate([ring_radius, 0, 0])
        rotate([0, (i % 2) * 90, 0])
          link_shape();
  }
}

module chain_frame() {
  w = _frame_w();
  h = _frame_h();
  r = _frame_r(w, h);
  perim = _frame_perim(w, h, r);
  count = _link_count(perim);
  step = perim / count;
  for (i = [0 : count - 1]) {
    t = i * step;
    info = _frame_at(t, w, h, r);
    pos = info[0];
    ang = info[1];
    translate([pos[0], pos[1], 0])
      rotate([0, 0, ang])
        rotate([0, (i % 2) * 90, 0])
          link_shape();
  }
}

module chain_body() {
  if (_layout_mode() == 1) {
    chain_ring();
  } else if (_layout_mode() == 2) {
    chain_frame();
  } else {
    chain_line();
  }
}

module plate_body() {
  if (plate_enabled == 1) {
    translate([plate_offset_x, plate_offset_y, 0])
      linear_extrude(height=plate_th, center=true)
        rounded_rect_2d(plate_w, plate_h, plate_radius);
  }
}

module bail_body() {
  if (bail_enabled == 1) {
    w = _frame_w();
    h = _frame_h();
    bx = bail_auto == 1 ? 0 : bail_offset_x;
    by = bail_auto == 1 ? (h / 2 - bail_h / 2 - bail_gap) : bail_offset_y;
    translate([plate_offset_x + bx, plate_offset_y + by, 0])
      linear_extrude(height=bail_th, center=true)
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
          linear_extrude(height=emblem_depth)
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

plate_top_z = plate_th / 2;

if (emboss == 1) {
  union() {
    difference() {
      body();
      if (emblem_mode == 0) {
        emblem_3d(plate_top_z - emblem_depth);
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
      emblem_3d(plate_top_z - emblem_depth);
    }
  }
  if (emblem_mode == 1) {
    emblem_3d(plate_top_z);
  }
}
