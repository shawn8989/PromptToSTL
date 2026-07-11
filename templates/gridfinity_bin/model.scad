// gridfinity_bin/model.scad — Gridfinity-compatible open storage bin.
// Base pads follow the standard unit profile (bottom-up): 0.8 mm 45°
// chamfer → 1.8 mm straight → 2.15 mm 45° chamfer, 41.5 mm top footprint
// on a 42 mm pitch. Body height = units_h × 7 mm above the 4.75 mm base.

grid_x = 2;
grid_y = 1;
units_h = 3;
wall = 1.2;
floor_th = 2.2;
magnets = 0;

pitch = 42;
pad_top = 41.5;      // pad footprint at the top of the base profile
r_top = 3.75;
h_c1 = 0.8;          // bottom chamfer height (45°)
h_str = 1.8;         // straight section height
h_c2 = 2.15;         // top chamfer height (45°)
base_h = h_c1 + h_str + h_c2;   // 4.75

pad_mid = pad_top - 2 * h_c2;   // 37.2
pad_bot = pad_mid - 2 * h_c1;   // 35.6
r_mid = max(0.5, r_top - h_c2);
r_bot = max(0.3, r_mid - h_c1);

body_w = grid_x * pitch - 0.5;  // 0.25 mm clearance per side
body_d = grid_y * pitch - 0.5;
body_h = units_h * 7;

magnet_d = 6.5;
magnet_h = 2.4;
magnet_off = 13;     // magnet centers ±13 mm from pad center (26 mm spacing)

$fn = 48;

module rounded_rect(w, h, r) {
  rr = min(r, w/3, h/3);
  offset(r = rr) square([w - 2*rr, h - 2*rr], center = true);
}

module slab(w, r, z, h) {
  translate([0, 0, z]) linear_extrude(height = h) rounded_rect(w, w, r);
}

// One base pad: two hulled chamfers around a straight section
module base_pad() {
  hull() {
    slab(pad_bot, r_bot, 0, 0.01);
    slab(pad_mid, r_mid, h_c1, 0.01);
  }
  slab(pad_mid, r_mid, h_c1, h_str);
  hull() {
    slab(pad_mid, r_mid, h_c1 + h_str - 0.01, 0.01);
    slab(pad_top, r_top, base_h - 0.01, 0.01);
  }
}

module pads() {
  for (gx = [0 : grid_x - 1])
    for (gy = [0 : grid_y - 1])
      translate([(gx - (grid_x - 1) / 2) * pitch,
                 (gy - (grid_y - 1) / 2) * pitch, 0])
        base_pad();
}

module magnet_pockets() {
  for (gx = [0 : grid_x - 1])
    for (gy = [0 : grid_y - 1])
      for (mx = [-1, 1])
        for (my = [-1, 1])
          translate([(gx - (grid_x - 1) / 2) * pitch + mx * magnet_off,
                     (gy - (grid_y - 1) / 2) * pitch + my * magnet_off, -0.01])
            cylinder(d = magnet_d, h = magnet_h);
}

difference() {
  union() {
    pads();
    // body shell sits on the pads
    translate([-body_w/2, -body_d/2, base_h])
      linear_extrude(height = body_h)
        translate([body_w/2, body_d/2])
          rounded_rect(body_w, body_d, r_top);
  }
  // interior cavity
  translate([0, 0, base_h + floor_th])
    linear_extrude(height = body_h + 1)
      rounded_rect(body_w - 2*wall, body_d - 2*wall, max(0.5, r_top - wall));
  if (magnets == 1)
    magnet_pockets();
}
