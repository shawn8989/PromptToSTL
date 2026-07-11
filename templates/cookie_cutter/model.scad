// cookie_cutter/model.scad — outline shell cutter: wide press flange at the
// bottom (print bed side), thin cutting wall rising above it.
// Food-safety note: print in PETG, wash cold, or use as a stamp template.

shape = "heart";     // "heart" | "star" | "circle" | "hexagon"
size = 70;
cut_h = 12;
cut_wall = 0.8;
flange_w = 4;
flange_h = 3;

$fn = 96;

function _hx(t) = 16 * pow(sin(t), 3);
function _hy(t) = 13*cos(t) - 5*cos(2*t) - 2*cos(3*t) - cos(4*t);

module heart_2d(w) {
  scale([w / 32, w / 29.5])
    translate([0, 2.25])
      polygon([for (i = [0 : 127]) let(t = i * 360 / 128) [_hx(t), _hy(t)]]);
}

module star_2d(w) {
  r_out = w / 2;
  r_in = r_out * 0.45;
  polygon([for (i = [0 : 9])
    let(a = 90 + i * 36, r = (i % 2 == 0) ? r_out : r_in)
    [r * cos(a), r * sin(a)]]);
}

module outline_2d() {
  if (shape == "heart") heart_2d(size);
  else if (shape == "star") star_2d(size);
  else if (shape == "hexagon") circle(d = size, $fn = 6);
  else circle(d = size);
}

module ring(w) {
  difference() {
    offset(r = w) outline_2d();
    outline_2d();
  }
}

union() {
  // press flange (bottom, wide)
  linear_extrude(height = flange_h)
    ring(flange_w);
  // cutting wall (thin, rises above the flange)
  linear_extrude(height = flange_h + cut_h)
    ring(cut_wall);
}
