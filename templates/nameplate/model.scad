line1 = "SHUNATHON";
line2 = "OWENS";
line3 = "";
emboss = 1;
w = 100;
h = 30;
th = 4;
corner_r = 5;
text_size = 14;
text_height = 1.2;
pad_x = 8;
pad_y = 6;
line_gap = 10;
text_block_center_y = 0;
offset_x = 0;
offset_y = 0;
debug = 0;
emblem_enabled = 0;
emblem_path = "";
emblem_scale = 0.25;
emblem_x = 0;
emblem_y = 0;
emblem_rot = 0;
emblem_mode = 1;
emblem_depth = 1.2;
holes = 0;
hole_d = 4;
hole_offset = 12;

module rounded_rect_2d(width, height, r) {
  r_clamped = min(r, min(width, height) / 2);
  if (r_clamped <= 0) {
    square([width, height], center=true);
  } else {
    offset(r=r_clamped) square([width - 2 * r_clamped, height - 2 * r_clamped], center=true);
  }
}

module base_plate() {
  linear_extrude(height=th)
    rounded_rect_2d(w, h, corner_r);
}

module hole_pair() {
  if (holes == 1) {
    for (x = [-1, 1]) {
      translate([x * (w / 2 - hole_offset), 0, 0])
        cylinder(d=hole_d, h=th + 0.2, $fn=64);
    }
  }
}

module text_line(str, y_offset) {
  translate([offset_x, offset_y + y_offset, th])
    linear_extrude(height=text_height)
      text(str, size=text_size, halign="center", valign="center");
}

function line_index(l1, l2, l3, which) =
  which == 1 ? (l1 != "" ? 0 : -1) :
  which == 2 ? (l2 != "" ? (l1 != "" ? 1 : 0) : -1) :
  (l3 != "" ? ((l1 != "" ? 1 : 0) + (l2 != "" ? 1 : 0)) : -1);

function line_count(l1, l2, l3) =
  (l1 != "" ? 1 : 0) + (l2 != "" ? 1 : 0) + (l3 != "" ? 1 : 0);

function offset_for_index(idx, count) =
  count <= 1 ? 0 :
  count == 2 ? (idx == 0 ? line_gap / 2 : -line_gap / 2) :
  (idx == 0 ? line_gap : (idx == 1 ? 0 : -line_gap));

function estimate_factor(s) =
  len(s) * 0.6;

function fit_scale(s) =
  let(safe_w = (w - 2 * pad_x) * 0.92,
      est_w = max(1, text_size * estimate_factor(s)))
  min(1, safe_w / est_w);

module text_line_scaled(str, y_offset) {
  translate([offset_x, offset_y + y_offset, th])
    linear_extrude(height=text_height)
      scale([fit_scale(str), fit_scale(str), 1])
        text(str, size=text_size, halign="center", valign="center");
}

module text_block() {
  count = line_count(line1, line2, line3);
  idx1 = line_index(line1, line2, line3, 1);
  idx2 = line_index(line1, line2, line3, 2);
  idx3 = line_index(line1, line2, line3, 3);

  if (line1 != "") {
    if (debug == 1) {
      echo("line1_safe_w", (w - 2 * pad_x) * 0.92);
      echo("line1_est_w", max(1, text_size * estimate_factor(line1)));
    }
    text_line_scaled(line1, text_block_center_y + offset_for_index(idx1, count));
  }
  if (line2 != "") {
    if (debug == 1) {
      echo("line2_safe_w", (w - 2 * pad_x) * 0.92);
      echo("line2_est_w", max(1, text_size * estimate_factor(line2)));
    }
    text_line_scaled(line2, text_block_center_y + offset_for_index(idx2, count));
  }
  if (line3 != "") {
    if (debug == 1) {
      echo("line3_safe_w", (w - 2 * pad_x) * 0.92);
      echo("line3_est_w", max(1, text_size * estimate_factor(line3)));
    }
    text_line_scaled(line3, text_block_center_y + offset_for_index(idx3, count));
  }
}

module emblem_2d() {
  translate([emblem_x, emblem_y, 0])
    rotate([0, 0, emblem_rot])
      scale([emblem_scale, emblem_scale, 1])
        import(emblem_path);
}

module emblem_3d(z) {
  if (emblem_enabled == 1 && emblem_path != "") {
    translate([0, 0, z])
      linear_extrude(height=emblem_depth)
        emblem_2d();
  }
}

module base_body() {
  linear_extrude(height=th)
    rounded_rect_2d(w, h, corner_r);
}

if (emboss == 1) {
  difference() {
    union() {
      base_plate();
      text_block();
    }
    hole_pair();
    if (emblem_mode == 0) {
      emblem_3d(th - emblem_depth);
    }
  }
  if (emblem_mode == 1) {
    emblem_3d(th);
  }
} else {
  difference() {
    base_plate();
    hole_pair();
    text_block();
    if (emblem_mode == 0) {
      emblem_3d(th - emblem_depth);
    }
  }
  if (emblem_mode == 1) {
    emblem_3d(th);
  }
}
