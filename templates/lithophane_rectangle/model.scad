// lithophane_rectangle/model.scad
// Rectangular lithophane photo frame with optional rounded corners.
// Print flat (Z=0 face on bed). Display against a backlight.

photo_path    = "";
photo_cols    = 200;
photo_rows    = 200;
plate_w       = 100;
plate_h       = 75;
min_thickness = 0.8;
max_thickness = 3.0;
frame_width   = 4;
corner_r      = 4;
base_height   = 1.2;

inner_w = plate_w - 2 * frame_width;
inner_h = plate_h - 2 * frame_width;
inner_r = max(0, corner_r - frame_width);

module rounded_rect(w, h, r) {
  rr = min(r, w/4, h/4);
  offset(r = rr) square([w - 2*rr, h - 2*rr], center = true);
}

module litho_fill() {
  intersection() {
    union() {
      linear_extrude(height = min_thickness)
        rounded_rect(inner_w, inner_h, inner_r);

      if (photo_path != "") {
        translate([0, 0, min_thickness])
          scale([inner_w / photo_cols,
                 inner_h / photo_rows,
                 (max_thickness - min_thickness) / 255.0])
            surface(file = photo_path, center = true, invert = false, convexity = 4);
      } else {
        linear_extrude(height = max_thickness - min_thickness)
          rounded_rect(inner_w, inner_h, inner_r);
      }
    }
    linear_extrude(height = max_thickness + 1)
      rounded_rect(inner_w, inner_h, inner_r);
  }
}

union() {
  // Base plate
  linear_extrude(height = base_height)
    rounded_rect(plate_w, plate_h, corner_r);

  // Frame ring
  translate([0, 0, base_height])
    linear_extrude(height = max_thickness)
      difference() {
        rounded_rect(plate_w, plate_h, corner_r);
        rounded_rect(inner_w, inner_h, inner_r);
      }

  // Lithophane fill
  translate([0, 0, base_height])
    litho_fill();
}
