// mini_planter/model.scad — tapered vessel with drainage holes.
// facets >= ~96 renders round; 5-10 gives a low-poly faceted look.

bottom_d = 60;
pot_h = 65;
top_scale = 1.35;
wall = 2.4;
floor_th = 3;
facets = 96;
drain_holes = 3;
drain_d = 6;

// Inner taper chosen to keep wall thickness roughly constant top to bottom
inner_bottom_d = bottom_d - 2 * wall;
inner_scale = (bottom_d * top_scale - 2 * wall) / inner_bottom_d;

difference() {
  // outer shell
  linear_extrude(height = pot_h, scale = top_scale)
    circle(d = bottom_d, $fn = facets);

  // cavity
  translate([0, 0, floor_th])
    linear_extrude(height = pot_h, scale = inner_scale)
      circle(d = inner_bottom_d, $fn = facets);

  // drainage holes in a ring (single center hole if count == 1)
  if (drain_holes > 0) {
    ring_r = (drain_holes == 1) ? 0 : inner_bottom_d / 5;
    for (i = [0 : drain_holes - 1])
      rotate([0, 0, i * 360 / drain_holes])
        translate([ring_r, 0, -1])
          cylinder(h = floor_th + 2, d = drain_d, $fn = 32);
  }
}
