// lithophane_mom/model.scad
// Single-piece MOM display: M — heart-lithophane — M on a shared base plate.
// Print flat (Z=0 face on bed). Display against a backlight.
// The letters are embossed on the base; the heart section shows your photo.

photo_path        = "";
photo_cols        = 200;
photo_rows        = 200;
heart_w           = 38;
heart_h           = 44;
letter_section_w  = 28;
section_gap       = 3;
letter_size       = 26;
letter_height     = 1.8;
min_thickness     = 0.8;
max_thickness     = 3.0;
frame_width       = 3;
base_height       = 1.2;

// ── Heart polygon (same formula as lithophane_heart) ─────────────────────────
function _hx(t) = 16 * pow(sin(t), 3);
function _hy(t) = 13*cos(t) - 5*cos(2*t) - 2*cos(3*t) - cos(4*t);

module heart_2d(w, h) {
  scale([w / 32, h / 29.5])
    translate([0, 2.25])
      polygon([for (i = [0 : 127]) let(t = i * 360 / 128) [_hx(t), _hy(t)]]);
}

// ── Derived ──────────────────────────────────────────────────────────────────
inner_w    = heart_w - 2 * frame_width;
inner_h    = heart_h - 2 * frame_width;
total_w    = 2 * letter_section_w + heart_w + 2 * section_gap;
plate_h    = heart_h;  // all sections share the same height
left_cx    = -(letter_section_w / 2 + section_gap + heart_w / 2);
right_cx   =  (letter_section_w / 2 + section_gap + heart_w / 2);

// ── Heart lithophane fill ─────────────────────────────────────────────────────
module litho_fill() {
  intersection() {
    union() {
      linear_extrude(height = min_thickness)
        heart_2d(inner_w, inner_h);
      if (photo_path != "") {
        translate([0, 0, min_thickness])
          scale([inner_w  / photo_cols,
                 inner_h  / photo_rows,
                 (max_thickness - min_thickness) / 255.0])
            surface(file = photo_path, center = true, invert = false, convexity = 4);
      } else {
        linear_extrude(height = max_thickness - min_thickness)
          heart_2d(inner_w, inner_h);
      }
    }
    linear_extrude(height = max_thickness + 1)
      heart_2d(inner_w, inner_h);
  }
}

// ── Heart section (frame + fill) ─────────────────────────────────────────────
module heart_section() {
  // Base plate for the heart section (heart silhouette)
  linear_extrude(height = base_height)
    heart_2d(heart_w, heart_h);

  // Frame ring above base
  translate([0, 0, base_height])
    linear_extrude(height = max_thickness)
      difference() {
        heart_2d(heart_w, heart_h);
        heart_2d(inner_w, inner_h);
      }

  // Lithophane fill
  translate([0, 0, base_height])
    litho_fill();
}

// ── Letter section ────────────────────────────────────────────────────────────
module letter_section(ltr) {
  // Rectangular base panel
  linear_extrude(height = base_height)
    square([letter_section_w, plate_h], center = true);

  // Embossed letter centred on the panel
  translate([0, 0, base_height])
    linear_extrude(height = letter_height)
      text(ltr,
           size   = letter_size,
           font   = "Liberation Sans:style=Bold",
           halign = "center",
           valign = "center");
}

// ── Full assembly ─────────────────────────────────────────────────────────────
union() {
  // Left M
  translate([left_cx, 0, 0])
    letter_section("M");

  // Centre heart lithophane
  heart_section();

  // Right M
  translate([right_cx, 0, 0])
    letter_section("M");

  // Thin connector strips filling the gaps between sections at base level
  // (ensures the base plate is one continuous solid)
  translate([-(section_gap / 2 + heart_w / 2), 0, 0])
    linear_extrude(height = base_height)
      square([section_gap, plate_h], center = true);

  translate([(section_gap / 2 + heart_w / 2), 0, 0])
    linear_extrude(height = base_height)
      square([section_gap, plate_h], center = true);
}
