// lithophane_circle/model.scad
// Circular lithophane photo frame — single solid piece.
// Print flat (Z=0 face on bed). Display against a backlight.

photo_path    = "";
photo_cols    = 200;
photo_rows    = 200;
diameter      = 80;
min_thickness = 0.8;
max_thickness = 3.0;
frame_width   = 4;
base_height   = 1.2;

inner_d = diameter - 2 * frame_width;

module litho_fill() {
  intersection() {
    union() {
      linear_extrude(height = min_thickness)
        circle(d = inner_d, $fn = 128);

      if (photo_path != "") {
        translate([0, 0, min_thickness])
          scale([inner_d / photo_cols,
                 inner_d / photo_rows,
                 (max_thickness - min_thickness) / 255.0])
            surface(file = photo_path, center = true, invert = false, convexity = 4);
      } else {
        linear_extrude(height = max_thickness - min_thickness)
          circle(d = inner_d, $fn = 128);
      }
    }
    linear_extrude(height = max_thickness + 1)
      circle(d = inner_d, $fn = 128);
  }
}

union() {
  // Base plate
  linear_extrude(height = base_height)
    circle(d = diameter, $fn = 128);

  // Frame ring
  translate([0, 0, base_height])
    linear_extrude(height = max_thickness)
      difference() {
        circle(d = diameter, $fn = 128);
        circle(d = inner_d,  $fn = 128);
      }

  // Lithophane fill
  translate([0, 0, base_height])
    litho_fill();
}
