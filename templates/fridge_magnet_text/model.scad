// fridge_magnet_text/model.scad — text plate with magnet pockets in the back.
// Print text-side up; glue disc magnets into the pockets on the underside.

line1 = "GROCERIES";
line2 = "";
emboss = 1;
w = 70;
h = 30;
th = 4;
corner_r = 5;
magnet_d = 10.4;
magnet_depth = 2.2;
magnet_count = 2;
text_size = 10;   // the app's layout engine overrides this to fit
line_gap = 10;
text_height = 1.2;
offset_x = 0;
offset_y = 0;

$fn = 64;

module rounded_rect_2d(width, height, r) {
  rr = min(r, width / 3, height / 3);
  offset(r = rr) square([width - 2*rr, height - 2*rr], center = true);
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

// Magnet pocket X positions, spread across the plate
function pocket_x(i) =
  (magnet_count == 1) ? 0
    : -w/2 + (w / (magnet_count + 1)) * (i + 1);

difference() {
  union() {
    linear_extrude(height = th)
      rounded_rect_2d(w, h, corner_r);
    if (emboss == 1)
      translate([0, 0, th]) text_block();
  }
  // magnet pockets, cut into the underside
  for (i = [0 : magnet_count - 1])
    translate([pocket_x(i), 0, -0.5])
      cylinder(h = magnet_depth + 0.5, d = magnet_d);
  if (emboss == 0)
    translate([0, 0, th - text_height]) text_block();
}
