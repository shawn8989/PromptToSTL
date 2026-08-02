// Wall Plaque with decorative border frame and optional mounting holes

w          = 120;   // overall width (mm)
h          = 60;    // overall height (mm)
th         = 5.0;   // base thickness (mm)
border_w   = 5.0;   // border frame width (mm)
border_th  = 1.5;   // how much the border frame is raised above the base (mm)
corner_r   = 6.0;   // outer corner radius (mm)
mount_holes= 1;     // 1 = include mounting holes
hole_d     = 4.5;   // mounting hole diameter (mm)
hole_margin= 8.0;   // hole center distance from edge (mm)

// Text
line1      = "YOUR NAME";
line2      = "";
line3      = "";
text_size  = 14;
text_height= 1.2;
line_gap   = 9;
pad_x      = 6;
pad_y      = 5;
text_align = "center";
emboss     = 1;
offset_x   = 0;
offset_y   = 0;

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

$fa = 4; $fs = 0.5;

inner_r = max(0, corner_r - border_w);

function text_anchor(align) =
    align == "left"  ? "left" :
    align == "right" ? "right" : "center";

// Z-centered in both branches: spans -thick/2 .. +thick/2.
// (The rounded branch used to start at z=0, which shifted the whole plate
// up by thick/2 — burying the text and stopping the mounting holes from
// cutting through.)
module rounded_plate(pw, ph, r, thick) {
    if (r <= 0) {
        cube([pw, ph, thick], center = true);
    } else {
        hull() {
            for (dx = [-1, 1], dy = [-1, 1]) {
                translate([dx * (pw/2 - r), dy * (ph/2 - r), -thick/2])
                cylinder(r = r, h = thick, $fn = 48);
            }
        }
    }
}

module border_frame() {
    if (border_w > 0 && border_th > 0) {
        difference() {
            translate([0, 0, th + border_th/2])
            rounded_plate(w, h, corner_r, border_th);

            translate([0, 0, th + border_th/2 - 0.01])
            rounded_plate(w - 2*border_w, h - 2*border_w, inner_r, border_th + 0.02);
        }
    }
}

module text_line(line, y_off) {
    translate([offset_x, offset_y + y_off, 0])
    text(line, size = text_size,
         halign = text_anchor(text_align), valign = "center", $fn = 24);
}

module text_2d() {
    active = (line1 != "" ? 1 : 0) + (line2 != "" ? 1 : 0) + (line3 != "" ? 1 : 0);
    y0 = (active > 1) ? (active - 1) * line_gap / 2 : 0;
    if (line1 != "") text_line(line1, y0);
    if (line2 != "") text_line(line2, y0 - line_gap);
    if (line3 != "") text_line(line3, y0 - 2*line_gap);
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

// Base
difference() {
    translate([0, 0, th/2])
    rounded_plate(w, h, corner_r, th);

    // Engraved text
    if (emboss == 0) {
        translate([0, 0, th + 0.01])
        linear_extrude(height = text_height + 0.02, center = false)
        mirror([0, 0, 0]) text_2d();
    }

    // Mounting holes
    if (mount_holes == 1) {
        for (dx = [-1, 1]) {
            translate([dx * (w/2 - hole_margin), 0, -0.01])
            cylinder(d = hole_d, h = th + 0.02, $fn = 24);
        }
    }
}

// Border frame
border_frame();

// Embossed text
if (emboss == 1) {
    translate([0, 0, th])
    linear_extrude(height = text_height)
    text_2d();
}

// Emblem
if (emblem_enabled == 1 && emblem_path != "") {
    translate([emblem_x, emblem_y, th])
    rotate([0, 0, emblem_rot])
    emblem_shape();
}
