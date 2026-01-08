text = "EDGE TECH";
emboss = 1;
diameter = 90;
th = 4;
rim = 1;
rim_w = 3;
rim_h = 1.2;
text_size = 12;
text_height = 1.0;
pad = 6;

approx_char_w = text_size * 0.6;
estimated_width = len(text) * approx_char_w;
available_width = diameter - 2 * pad;
scale_factor = min(1, available_width / max(1, estimated_width));

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
    linear_extrude(height=text_height)
      scale([scale_factor, scale_factor, 1])
        text(text, size=text_size, halign="center", valign="center");
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
