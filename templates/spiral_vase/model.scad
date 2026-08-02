// spiral_vase/model.scad — twisted lobed vase.
// Exported SOLID: slice in your slicer's vase / spiral mode (0% infill,
// 0 top layers) for a fast single-wall watertight print.

base_d = 70;
vase_h = 140;
twist = 90;
lobes = 6;
lobe_depth = 0.12;
taper = 1.15;

// Lobed profile: r(a) = R * (1 - depth/2 + depth/2 * cos(lobes * a))
module lobed_2d() {
  R = base_d / 2;
  polygon([for (i = [0 : 179])
    let(a = i * 2,
        r = R * (1 - lobe_depth / 2 + (lobe_depth / 2) * cos(lobes * a)))
    [r * cos(a), r * sin(a)]]);
}

linear_extrude(height = vase_h, twist = twist, scale = taper,
               slices = max(60, vase_h), convexity = 10)
  lobed_2d();
