// Round Badge / Button with optional bail (keyring loop)

diameter   = 50;    // badge diameter (mm)
th         = 4.0;   // base thickness (mm)
border_w   = 4.0;   // decorative border ring width (mm)
border_th  = 1.0;   // border ring raised height (mm)
bail_enabled = 1;   // 1 = include keyring bail at top
bail_d     = 6.0;   // bail outer diameter (mm)
bail_thick = 2.0;   // bail wall thickness (mm)

// Text
line1      = "YOUR TEXT";
line2      = "";
text_size  = 10;
text_height= 1.2;
line_gap   = 8;
pad_x      = 4;
pad_y      = 4;
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

$fa = 2; $fs = 0.4;

r = diameter / 2;

function text_anchor(align) =
    align == "left"  ? "left" :
    align == "right" ? "right" : "center";

module disc(radius, height) {
    cylinder(r = radius, h = height, center = false, $fn = 96);
}

module border_ring() {
    if (border_w > 0 && border_th > 0) {
        translate([0, 0, th])
        difference() {
            disc(r, border_th);
            disc(r - border_w, border_th + 0.01);
        }
    }
}

module bail() {
    if (bail_enabled == 1) {
        bail_r = bail_d / 2;
        translate([0, r + bail_r - bail_thick/2, th/2])
        difference() {
            cylinder(r = bail_r, h = th, center = true, $fn = 48);
            cylinder(r = bail_r - bail_thick, h = th + 0.01, center = true, $fn = 48);
            // open bottom to connect flush with badge
            translate([0, -bail_r, 0])
            cube([bail_d, bail_d, th + 0.01], center = true);
        }
    }
}

module text_2d() {
    y0 = (line2 != "") ? line_gap / 2 : 0;
    translate([offset_x, offset_y, 0]) {
        if (line1 != "")
            translate([0, y0, 0])
            text(line1, size = text_size, halign = text_anchor(text_align), valign = "center", $fn = 24);
        if (line2 != "")
            translate([0, y0 - line_gap, 0])
            text(line2, size = text_size, halign = text_anchor(text_align), valign = "center", $fn = 24);
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

// Base disc
difference() {
    disc(r, th);
    if (emboss == 0) {
        translate([0, 0, th + 0.01])
        linear_extrude(height = text_height + 0.02)
        text_2d();
    }
}

// Border ring
border_ring();

// Bail
bail();

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
