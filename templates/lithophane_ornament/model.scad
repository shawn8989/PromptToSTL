// lithophane_ornament/model.scad
// Round photo lithophane with a hanger hole. Fallback path — the app
// normally builds this template with the native Python mesher
// (src/core/litho_mesh.py, shape "ornament"), which is ~700x faster.

photo_path    = "";
photo_cols    = 200;
photo_rows    = 200;
diameter      = 75;
frame_width   = 4;
hole_d        = 4;
hole_ring     = 2.5;
min_thickness = 0.8;
max_thickness = 3.0;
base_height   = 1.2;

inner_d = diameter - 2 * frame_width;
hole_cy = diameter/2 - hole_d/2 - max(frame_width, 3);

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

difference() {
  union() {
    // Base plate
    linear_extrude(height = base_height)
      circle(d = diameter, $fn = 128);

    // Frame ring
    translate([0, 0, base_height])
      linear_extrude(height = max_thickness)
        difference() {
          circle(d = diameter, $fn = 128);
          circle(d = inner_d, $fn = 128);
        }

    // Lithophane fill
    translate([0, 0, base_height])
      litho_fill();

    // Reinforcement ring around the hanger hole
    translate([0, hole_cy, 0])
      linear_extrude(height = base_height + max_thickness)
        circle(d = hole_d + 2 * hole_ring, $fn = 64);
  }

  // Hanger hole
  translate([0, hole_cy, -1])
    cylinder(h = base_height + max_thickness + 2, d = hole_d, $fn = 48);
}
