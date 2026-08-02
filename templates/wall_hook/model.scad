// wall_hook/model.scad — back plate with two countersunk screw holes and a
// J-hook built from hulled spheres. Print with the plate flat on the bed
// (hook pointing up) or on its side with supports for max strength.

plate_w = 30;
plate_h = 60;
plate_th = 5;
hook_d = 9;
hook_reach = 28;
tip_up = 14;
screw_d = 4.2;

$fn = 48;

module rounded_plate() {
  r = 5;
  linear_extrude(height = plate_th)
    offset(r = r)
      square([plate_w - 2*r, plate_h - 2*r], center = true);
}

module screw_hole(y) {
  // through hole + countersink cone
  translate([0, y, -1])
    cylinder(h = plate_th + 2, d = screw_d);
  translate([0, y, plate_th - 2])
    cylinder(h = 2.01, d1 = screw_d, d2 = screw_d * 2.2);
}

// Hook arm: plate surface → out; tip: curls up.
// Plate lies in XY (wall plane), hook extends in +Z away from the wall.
hook_y = -plate_h / 2 + hook_d / 2 + 6;   // arm root near the plate bottom

module hook() {
  // arm out from the plate
  hull() {
    translate([0, hook_y, plate_th / 2]) sphere(d = hook_d);
    translate([0, hook_y, plate_th + hook_reach - hook_d / 2]) sphere(d = hook_d);
  }
  // tip rising parallel to the wall
  hull() {
    translate([0, hook_y, plate_th + hook_reach - hook_d / 2]) sphere(d = hook_d);
    translate([0, hook_y + tip_up, plate_th + hook_reach - hook_d / 2]) sphere(d = hook_d);
  }
}

difference() {
  union() {
    rounded_plate();
    hook();
  }
  screw_hole(plate_h / 2 - 8);
  screw_hole(hook_y + hook_d / 2 + 10);
}
