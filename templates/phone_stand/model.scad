// phone_stand/model.scad — L-profile desk stand: base + front lip + leaning
// back rest, with a cable slot through the lip. Print flat on the base.

w = 70;
depth = 78;
tilt = 65;           // degrees from horizontal; 90 = upright
rest_h = 90;
phone_th = 13;
lip_h = 16;
base_th = 5;
slot_w = 14;
lip_th = 5;
rest_th = 6;

$fn = 48;

// The phone leans on the rest, sitting in the slot between lip and rest.
rest_y = lip_th + phone_th;    // front face of the back rest at base level

module base() {
  translate([-w/2, 0, 0])
    cube([w, depth, base_th]);
}

module lip() {
  translate([-w/2, 0, 0])
    cube([w, lip_th, base_th + lip_h]);
}

module back_rest() {
  translate([0, rest_y, base_th - 0.1])
    rotate([tilt - 90, 0, 0])       // lean the top backwards
      translate([-w/2, 0, 0])
        cube([w, rest_th, rest_h]);
}

difference() {
  union() {
    base();
    lip();
    back_rest();
  }
  // charging-cable slot through the lip and base front, centered
  translate([-slot_w/2, -1, -1])
    cube([slot_w, lip_th + phone_th + 2, base_th + lip_h * 0.6 + 1]);
}
