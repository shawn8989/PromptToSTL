// luggage_tag/model.scad — rounded tag with strap slot + 2 text lines.

line1 = "S. OWENS";
line2 = "+1 555 0100";
emboss = 1;
part = "all";   // "all" | "base" | "text" — multi-color part export
w = 85;
h = 50;
th = 3;
corner_r = 6;
slot_w = 18;         // slot length (vertical)
slot_h = 5;          // slot width (horizontal)
slot_zone = 22;      // reserved zone at the left edge for the slot
text_size = 11;
line_gap = 12;
text_height = 1.0;
offset_x = 0;
offset_y = 0;

$fn = 64;

module rounded_rect_2d(width, height, r) {
  rr = min(r, width / 3, height / 3);
  offset(r = rr) square([width - 2*rr, height - 2*rr], center = true);
}

// Vertical stadium-shaped slot near the left edge
module strap_slot_2d() {
  translate([-w/2 + slot_zone/2, 0])
    hull() {
      translate([0,  slot_w/2 - slot_h/2]) circle(d = slot_h);
      translate([0, -slot_w/2 + slot_h/2]) circle(d = slot_h);
    }
}

module line_text_3d(s, y) {
  translate([offset_x, offset_y + y, 0])
    linear_extrude(height = text_height)
      text(s, size = text_size, halign = "center", valign = "center");
}

module text_block() {
  if (line2 == "") line_text_3d(line1, 0);
  else {
    line_text_3d(line1, line_gap / 2);
    line_text_3d(line2, -line_gap / 2);
  }
}

difference() {
  union() {
    if (part != "text")
      linear_extrude(height = th)
        rounded_rect_2d(w, h, corner_r);
    if (emboss == 1 && part != "base")
      translate([0, 0, th]) text_block();
  }
  translate([0, 0, -1])
    linear_extrude(height = th + 2)
      strap_slot_2d();
  if (emboss == 0)
    translate([0, 0, th - text_height]) text_block();
}
