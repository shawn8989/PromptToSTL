// keychain.scad (auto-fit text)
// CLI example:
// openscad -o out.stl -D 'name="SHUNATHON OWENS"' -D 'emboss=1' keychain.scad

name = "YOUR NAME";
emboss = 1;           // 1=emboss, 0=engrave

// Base (mm)
w = 70;
h = 22;
th = 4;

// Hole (mm)
hole_d = 5.5;
hole_offset_x = 8;

// Text (mm)
text_size = 12;       // "desired" size; will be scaled down if needed
text_height = 1.2;
pad_x = 8;            // left/right margin inside plate
pad_y = 5;            // top/bottom margin inside plate

$fn = 64;

module rounded_rect_2d(width, height, r) {
  minkowski() {
    square([width - 2*r, height - 2*r], center=true);
    circle(r=r);
  }
}

module base_plate() {
  linear_extrude(height=th)
    rounded_rect_2d(w, h, r=5);
}

module keychain_hole() {
  translate([-(w/2) + hole_offset_x, 0, 0])
    cylinder(h=th + 2, d=hole_d, center=false);
}

// Create text as 2D so we can measure it
module text_2d(s) {
  text(s, size=text_size, halign="center", valign="center");
}

// Compute bounding box of text (2D)
function tx(s) = let(bb = textmetrics(s, size=text_size)) bb[0];
function ty(s) = let(bb = textmetrics(s, size=text_size)) bb[1];

// Fit scale so text stays inside plate area
function fit_scale(s) =
  let(av_w = w - 2*pad_x,
      av_h = h - 2*pad_y,
      t_w = max(1, tx(s)),
      t_h = max(1, ty(s)),
      sx = av_w / t_w,
      sy = av_h / t_h)
  min(1, sx, sy);

module fitted_text(s) {
  sc = fit_scale(s);

  // Clip to safe area so it never "runs off" the plate
  intersection() {
    // Safe area box
    square([w - 2*pad_x, h - 2*pad_y], center=true);

    // Scaled text
    scale([sc, sc, 1]) text_2d(s);
  }
}

module label_text_3d(s) {
  linear_extrude(height=text_height)
    fitted_text(s);
}

difference() {
  base_plate();

  // hole
  translate([0,0,-1]) keychain_hole();

  // engrave
  if (emboss == 0) {
    translate([0,0, th - text_height])
      label_text_3d(name);
  }
}

// emboss
if (emboss == 1) {
  translate([0,0, th])
    label_text_3d(name);
}