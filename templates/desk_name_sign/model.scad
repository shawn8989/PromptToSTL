// desk_name_sign/model.scad — triangular wedge with text on the angled face.
// Side profile: flat bottom (depth), vertical back rising to sign_h, and a
// slanted front face (the hypotenuse) carrying the text.

line1 = "SHUNATHON OWENS";
line2 = "";
emboss = 1;
part = "all";   // "all" | "base" | "text" — multi-color part export
w = 150;
sign_h = 40;
depth = 34;
face_h = 48;          // slant-face height (set by schema; ~hypot(sign_h, depth))
text_size = 12;   // the app's layout engine overrides this to fit
line_gap = 14;
text_height = 1.5;
offset_x = 0;
offset_y = 0;

$fn = 48;

// Slant angle of the face, measured from the ground plane
phi = atan2(sign_h, depth);

module wedge() {
  hull() {
    translate([-w/2, 0, 0]) cube([w, depth, 0.01]);   // bottom slab
    translate([-w/2, 0, 0]) cube([w, 0.01, sign_h]);  // back edge
  }
}

// Places children flat on the slanted face (local XY = face plane,
// local +Z = outward face normal)
module on_face() {
  translate([0, depth/2, sign_h/2])
    rotate([-phi, 0, 0])
      children();
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

if (emboss == 1) {
  if (part != "text") wedge();
  if (part != "base") on_face() text_block();
} else {
  difference() {
    wedge();
    on_face() translate([0, 0, -text_height]) text_block();
  }
}
