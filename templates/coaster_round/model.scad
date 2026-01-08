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

if (emboss == 1) {
  union() {
    base();
    rim_ring();
    top_text_3d();
  }
} else {
  difference() {
    union() {
      base();
      rim_ring();
    }
    top_text_3d();
  }
}
