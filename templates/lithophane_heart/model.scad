// lithophane_heart/model.scad
// Heart-shaped lithophane photo frame — single solid piece.
// Print flat (Z=0 face on bed). Display against a backlight, flat side
// toward the light source. Dark areas of the original photo print thick
// (pre-inverted by image_prep.py) so less light passes through them.
//
// Coordinate convention: centered at XY origin, Z grows up.

photo_path   = "";
photo_cols   = 200;
photo_rows   = 200;
heart_w      = 80;
heart_h      = 80;
min_thickness = 0.8;
max_thickness = 3.0;
frame_width   = 4;
base_height   = 1.2;

// ── Heart polygon ────────────────────────────────────────────────────────────
// Standard parametric heart:  x = 16·sin³t,  y = 13·cos t − 5·cos 2t − 2·cos 3t − cos 4t
// Angle t in degrees (OpenSCAD trig uses degrees).
// Approximate bounding box: x ∈ [−16, 16], y ∈ [−17, 12.5]  →  width≈32, height≈29.5
// We centre the shape in its bounding box then scale to the requested size.

function _hx(t) = 16 * pow(sin(t), 3);
function _hy(t) = 13*cos(t) - 5*cos(2*t) - 2*cos(3*t) - cos(4*t);

// Sample N=128 points, scale to (w × h), centred at the bounding-box midpoint.
module heart_2d(w, h) {
  N = 128;
  // Natural bbox centre: x=0, y=(-17+12.5)/2 ≈ -2.25
  // Natural bbox size:  32 × 29.5  →  normalise by 32 and 29.5
  scale([w / 32, h / 29.5])
    translate([0, 2.25])
      polygon([for (i = [0 : N-1])
        let(t = i * 360 / N)
        [_hx(t), _hy(t)]
      ]);
}

// ── Derived dimensions ───────────────────────────────────────────────────────
inner_w = heart_w - 2 * frame_width;
inner_h = heart_h - 2 * frame_width;

// ── Lithophane fill module ───────────────────────────────────────────────────
// Placed at Z=0 within this module; caller translates to base_height.
module litho_fill() {
  // Floor at min_thickness ensures no gaps at bright (thin) pixel areas.
  // Surface heightmap sits on top of the floor.
  intersection() {
    union() {
      // Solid floor: min_thickness tall, heart-shaped
      linear_extrude(height = min_thickness)
        heart_2d(inner_w, inner_h);

      // Heightmap: pixel value 0→0mm, 255→(max−min) mm, offset by min_thickness
      if (photo_path != "") {
        translate([0, 0, min_thickness])
          scale([inner_w  / photo_cols,
                 inner_h  / photo_rows,
                 (max_thickness - min_thickness) / 255.0])
            surface(file = photo_path, center = true, invert = false, convexity = 4);
      } else {
        // Placeholder when no photo is loaded — flat plate at max_thickness
        linear_extrude(height = max_thickness - min_thickness)
          heart_2d(inner_w, inner_h);
      }
    }
    // Clip rectangular surface to heart silhouette
    linear_extrude(height = max_thickness + 1)
      heart_2d(inner_w, inner_h);
  }
}

// ── Main solid ───────────────────────────────────────────────────────────────
union() {
  // 1. Full-heart base plate (entire silhouette, base_height thick)
  linear_extrude(height = base_height)
    heart_2d(heart_w, heart_h);

  // 2. Frame ring above the base (outer heart minus inner heart)
  translate([0, 0, base_height])
    linear_extrude(height = max_thickness)
      difference() {
        heart_2d(heart_w, heart_h);
        heart_2d(inner_w, inner_h);
      }

  // 3. Lithophane fill inside the frame
  translate([0, 0, base_height])
    litho_fill();
}
