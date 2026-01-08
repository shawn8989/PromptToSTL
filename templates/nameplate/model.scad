line1 = "SHUNATHON";
line2 = "OWENS";
line3 = "";
emboss = 1;
w = 100;
h = 30;
th = 4;
corner_r = 5;
text_size = 14;
text_height = 1.2;
pad_x = 8;
pad_y = 6;
line_gap = 10;
offset_x = 0;
offset_y = 0;
holes = 0;
hole_d = 4;
hole_offset = 12;

module rounded_rect_2d(width, height, r) {
  r_clamped = min(r, min(width, height) / 2);
  if (r_clamped <= 0) {
    square([width, height], center=true);
  } else {
    offset(r=r_clamped) square([width - 2 * r_clamped, height - 2 * r_clamped], center=true);
  }
}

module base_plate() {
  linear_extrude(height=th)
    rounded_rect_2d(w, h, corner_r);
}

module hole_pair() {
  if (holes == 1) {
    for (x = [-1, 1]) {
      translate([x * (w / 2 - hole_offset), 0, 0])
        cylinder(d=hole_d, h=th + 0.2, $fn=64);
    }
  }
}

module text_line(str, y_offset) {
  translate([offset_x, offset_y + y_offset, th])
    linear_extrude(height=text_height)
      text(str, size=text_size, halign="center", valign="center");
}

module text_block() {
  if (line2 == "" && line3 == "") {
    text_line(line1, 0);
  } else if (line3 == "") {
    text_line(line1, line_gap / 2);
    text_line(line2, -line_gap / 2);
  } else {
    text_line(line1, line_gap);
    text_line(line2, 0);
    text_line(line3, -line_gap);
  }
}

if (emboss == 1) {
  difference() {
    union() {
      base_plate();
      text_block();
    }
    hole_pair();
  }
} else {
  difference() {
    base_plate();
    hole_pair();
    text_block();
  }
}
