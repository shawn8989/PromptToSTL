// Lithophane — backlit image panel
// Image is passed as a grayscale .dat heightmap (values 0.0-1.0, inverted: 0=bright/thin, 1=dark/thick)
//
// Print tip: orient vertically, use 100% infill, white/natural PLA, backlight with LED strip.

width     = 90;    // total panel width (mm)
height    = 70;    // total panel height (mm)
min_thick = 0.6;   // thinnest point — bright pixels (mm)
max_thick = 3.0;   // thickest point — dark pixels (mm)
border    = 3.0;   // frame border width (mm); set 0 for no frame

dat_file  = "";    // path to .dat heightmap (set by app)
dat_w     = 100;   // pixel columns in dat_file
dat_h     = 75;    // pixel rows in dat_file

$fa = 3; $fs = 0.5;

inner_w = width  - 2 * border;
inner_h = height - 2 * border;

thick_range = max_thick - min_thick;

module litho_surface() {
    // surface() reads 0.0-1.0 values → scale z to thick_range, offset by min_thick
    translate([-inner_w/2, -inner_h/2, min_thick])
    scale([inner_w / max(1, dat_w - 1),
           inner_h / max(1, dat_h - 1),
           thick_range])
    surface(file = dat_file, center = false, convexity = 15);
}

module base_fill() {
    // Solid slab that closes the bottom below the surface mesh
    translate([0, 0, min_thick / 2])
    cube([inner_w, inner_h, min_thick], center = true);
}

module frame() {
    if (border > 0) {
        difference() {
            cube([width, height, max_thick], center = true);
            cube([inner_w, inner_h, max_thick + 0.01], center = true);
        }
    }
}

// Main
translate([0, 0, max_thick / 2]) {
    if (dat_file != "") {
        base_fill();
        litho_surface();
    } else {
        // Placeholder slab when no image is loaded
        cube([inner_w, inner_h, max_thick], center = true);
    }
    frame();
}
