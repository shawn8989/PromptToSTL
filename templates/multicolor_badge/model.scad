// Multicolor Badge — 2-color FDM print
//
// PRINTING INSTRUCTIONS:
//   Single-extruder:  Set a filament/color change pause in your slicer at layer height = base_thick mm.
//                     Print base in Color A, then swap to Color B for the text layer.
//   Multi-material:   Export the two bodies as separate STLs using your slicer's split feature,
//                     or use the slicer's paint/color tool to assign colors per region.
//
// The base plate is printed in the first color.
// The raised text / emblem is printed in the second color.

w          = 70;      // badge width (mm)
h          = 30;      // badge height (mm)
base_thick = 2.0;     // base plate thickness (mm) — filament change at this height
text_height= 1.2;     // raised text / emblem height above the base
corner_r   = 4.0;     // corner radius

// Text
line1       = "YOUR TEXT";
line2       = "";
text_size   = 12;
line_gap    = 8;
pad_x       = 5;
pad_y       = 4;
text_align  = "center";
emboss      = 1;      // 1 = text raised (emboss), 0 = text sunken (engrave)
offset_x    = 0;
offset_y    = 0;

// Emblem
emblem_enabled = 0;
emblem_path    = "";
emblem_kind    = "svg";
emblem_scale   = 0.25;
emblem_x       = 0;
emblem_y       = 0;
emblem_rot     = 0;
emblem_mode    = 1;
emblem_depth   = 1.2;
emblem_invert  = 0;

$fa = 4; $fs = 0.6;

function text_anchor(align) =
    align == "left"  ? "left" :
    align == "right" ? "right" : "center";

module rounded_plate(pw, ph, thick, r) {
    hull() {
        for (dx = [-1, 1], dy = [-1, 1]) {
            translate([dx * (pw/2 - r), dy * (ph/2 - r), 0])
            cylinder(r = r, h = thick, $fn = 32);
        }
    }
}

module text_2d(line, size, align) {
    text(line, size = size, halign = text_anchor(align), valign = "center", $fn = 24);
}

module text_body() {
    if (emboss == 1) {
        // Raised text on top of base
        translate([offset_x, offset_y, base_thick])
        linear_extrude(height = text_height)
        union() {
            if (line1 != "")
                translate([0, (line2 != "" ? line_gap/2 : 0), 0])
                text_2d(line1, text_size, text_align);
            if (line2 != "")
                translate([0, -(line_gap/2), 0])
                text_2d(line2, text_size, text_align);
        }
    } else {
        // Engraved text — cut into the base
        translate([0, 0, -0.01])
        linear_extrude(height = text_height + 0.01)
        union() {
            if (line1 != "")
                translate([offset_x, offset_y + (line2 != "" ? line_gap/2 : 0), 0])
                text_2d(line1, text_size, text_align);
            if (line2 != "")
                translate([offset_x, offset_y - line_gap/2, 0])
                text_2d(line2, text_size, text_align);
        }
    }
}

module emblem_shape() {
    if (emblem_kind == "heightmap" && emblem_path != "") {
        scale([emblem_scale, emblem_scale, emblem_depth / 2])
        translate([0, 0, 1])
        surface(file = emblem_path, center = true);
    } else if (emblem_path != "") {
        scale([emblem_scale, emblem_scale, 1])
        linear_extrude(height = emblem_depth)
        import(emblem_path);
    }
}

module emblem_body() {
    if (emblem_enabled == 1 && emblem_path != "") {
        translate([emblem_x, emblem_y, base_thick])
        rotate([0, 0, emblem_rot])
        emblem_shape();
    }
}

// Base plate (Color A)
difference() {
    rounded_plate(w, h, base_thick, corner_r);
    if (emboss == 0) text_body();
}

// Raised elements (Color B — printed after filament change at base_thick)
if (emboss == 1) {
    text_body();
    emblem_body();
}
