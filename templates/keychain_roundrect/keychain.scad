// keychain.scad (multi-line text)
// CLI example:
// openscad -o out.stl -D 'line1="SHUNATHON"' -D 'line2="OWENS"' -D 'emboss=1' keychain.scad

line1 = "YOUR NAME";
line2 = "";
line_gap = 8;
offset_x = 0;
offset_y = 0;
emblem_enabled = 0;
emblem_path = "";
emblem_scale = 0.25;
emblem_x = 12;
emblem_y = 0;
emblem_rot = 0;
emblem_depth = 1.2;
emboss = 1;           // 1=emboss, 0=engrave

// Base (mm)
w = 70;
h = 22;
th = 4;

// Hole (mm)
hole_d = 5.5;
hole_offset_x = 8;

// Text (mm)
text_size = 12;
text_height = 1.2;
pad_x = 8;            // left/right margin inside plate
pad_y = 5;            // top/bottom margin inside plate

$fn = 64;

module rounded_rect_2d(width, height, r) {
  minkowski() {
    square([width - 2*r, height - 2*r], center=true);
    circle(r=r);
  }
}

module base_plate() {
  linear_extrude(height=th)
    rounded_rect_2d(w, h, r=5);
}

module keychain_hole() {
  translate([-(w/2) + hole_offset_x, 0, 0])
    cylinder(h=th + 2, d=hole_d, center=false);
}

module line_text_3d(s, y) {
  translate([offset_x, offset_y + y, 0])
    linear_extrude(height=text_height)
      text(s, size=text_size, halign="center", valign="center");
}

module emblem_3d(z) {
  if (emblem_enabled == 1 && emblem_path != "") {
    translate([emblem_x, emblem_y, z])
      rotate([0, 0, emblem_rot])
        scale([emblem_scale, emblem_scale, 1])
          linear_extrude(height=emblem_depth)
            import(emblem_path);
  }
}

difference() {
  base_plate();

  // hole
  translate([0,0,-1]) keychain_hole();

  // engrave
  if (emboss == 0) {
    translate([0,0, th - text_height])
      union() {
        if (line2 == "") {
          line_text_3d(line1, 0);
        } else {
          line_text_3d(line1, line_gap / 2);
          line_text_3d(line2, -line_gap / 2);
        }
      }
  }
}

// emboss
if (emboss == 1) {
  translate([0,0, th])
    union() {
      if (line2 == "") {
        line_text_3d(line1, 0);
      } else {
        line_text_3d(line1, line_gap / 2);
        line_text_3d(line2, -line_gap / 2);
      }
    }
}

emblem_3d(th);
