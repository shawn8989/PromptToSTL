line1 = "EDGE TECH";
line2 = "";
emboss = 1;
diameter = 90;
th = 4;
rim = 1;
rim_w = 3;
rim_h = 1.2;
text_size = 12;
text_height = 1.0;
pad = 6;
line_gap = 10;
offset_x = 0;
offset_y = 0;
emblem_enabled = 0;
emblem_path = "";
emblem_scale = 0.25;
emblem_x = 0;
emblem_y = 0;
emblem_rot = 0;
emblem_mode = 1;
emblem_depth = 1.2;

module base() {
  cylinder(d=diameter, h=th, $fn=128);
}

module rim_ring() {
  if (rim == 1) {
    translate([0, 0, th])
      difference() {
        cylinder(d=diameter, h=rim_h, $fn=128);
        cylinder(d=diameter - 2 * rim_w, h=rim_h + 0.1, $fn=128);
      }
  }
}

module top_text_3d() {
  translate([0, 0, th])
    union() {
      if (line2 == "") {
        translate([offset_x, offset_y, 0])
          linear_extrude(height=text_height)
            text(line1, size=text_size, halign="center", valign="center");
      } else {
        translate([offset_x, offset_y + line_gap / 2, 0])
          linear_extrude(height=text_height)
            text(line1, size=text_size, halign="center", valign="center");
        translate([offset_x, offset_y - line_gap / 2, 0])
          linear_extrude(height=text_height)
            text(line2, size=text_size, halign="center", valign="center");
      }
    }
}

module emblem_3d(z) {
  if (emblem_enabled == 1 && emblem_path != "") {
    translate([emblem_x, emblem_y, z])
      rotate([0, 0, emblem_rot])
        scale([emblem_scale, emblem_scale, 1])
          linear_extrude(height=emblem_depth)
            import(emblem_path);
  }
}

if (emboss == 1) {
  union() {
    base();
    rim_ring();
    top_text_3d();
    if (emblem_mode == 1) {
      emblem_3d(th);
    }
  }
} else {
  difference() {
    union() {
      base();
      rim_ring();
    }
    top_text_3d();
    if (emblem_mode == 0) {
      emblem_3d(th - emblem_depth);
    }
  }
}
