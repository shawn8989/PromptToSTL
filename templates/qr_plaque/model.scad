// qr_plaque/model.scad — fallback plate only.
// The app builds this template with the native Python mesher
// (src/core/litho_mesh.py + src/core/qr.py); OpenSCAD has no QR generator,
// so this fallback renders just the blank plate with border.

plate_w = 80;
plate_h = 80;
size = 80;
frame_width = 3;
corner_r = 3;
base_height = 3;
max_thickness = 0.6;
min_thickness = 0.01;
qr_text = "";
photo_path = "";
photo_cols = 200;
photo_rows = 200;

module rounded_rect(w, h, r) {
  rr = min(r, w/4, h/4);
  offset(r = rr) square([w - 2*rr, h - 2*rr], center = true);
}

union() {
  linear_extrude(height = base_height)
    rounded_rect(size, size, corner_r);
  // border ring at relief height
  translate([0, 0, base_height])
    linear_extrude(height = max_thickness)
      difference() {
        rounded_rect(size, size, corner_r);
        rounded_rect(size - 2*frame_width, size - 2*frame_width,
                     max(0, corner_r - frame_width));
      }
}
