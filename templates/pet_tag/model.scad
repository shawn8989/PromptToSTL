// pet_tag/model.scad — round / bone / heart pet ID tag with ring hole.

line1 = "MAX";
line2 = "";
shape = "bone";        // "bone" | "round" | "heart"
emboss = 1;
part = "all";          // "all" | "base" | "text" — multi-color part export
tag_w = 40;
th = 3;
hole_d = 4;
text_size = 9;
line_gap = 6;
text_height = 1.0;
offset_x = 0;
offset_y = 0;

$fn = 64;

// Parametric heart (same curve as the lithophane templates)
function _hx(t) = 16 * pow(sin(t), 3);
function _hy(t) = 13*cos(t) - 5*cos(2*t) - 2*cos(3*t) - cos(4*t);

module heart_2d(w, h) {
  scale([w / 32, h / 29.5])
    translate([0, 2.25])
      polygon([for (i = [0 : 127]) let(t = i * 360 / 128) [_hx(t), _hy(t)]]);
}

module bone_2d(w, h) {
  r = h / 4;
  union() {
    hull() {
      translate([-w/2 + r,  h/2 - r]) circle(r = r);
      translate([-w/2 + r, -h/2 + r]) circle(r = r);
    }
    hull() {
      translate([w/2 - r,  h/2 - r]) circle(r = r);
      translate([w/2 - r, -h/2 + r]) circle(r = r);
    }
    square([w - 2*r, h * 0.55], center = true);
  }
}

tag_h = (shape == "bone") ? tag_w * 0.55 : tag_w;

module tag_2d() {
  if (shape == "round")
    circle(d = tag_w);
  else if (shape == "heart")
    heart_2d(tag_w, tag_w);
  else
    bone_2d(tag_w, tag_h);
}

// Hanger boss sits at the top edge of the shape
boss_r = hole_d / 2 + 2;
boss_y = tag_h / 2 - boss_r * 0.4;

module line_text_3d(s, y) {
  translate([offset_x, offset_y + y, 0])
    linear_extrude(height = text_height)
      text(s, size = text_size, halign = "center", valign = "center");
}

module text_block() {
  if (line2 == "") line_text_3d(line1, 0);
  else {
    line_text_3d(line1, line_gap / 2);
    line_text_3d(line2, -line_gap / 2);
  }
}

difference() {
  union() {
    if (part != "text") {
      linear_extrude(height = th) tag_2d();
      // hanger boss
      translate([0, boss_y, 0])
        linear_extrude(height = th)
          circle(r = boss_r);
    }
    if (emboss == 1 && part != "base")
      translate([0, 0, th]) text_block();
  }
  // ring hole
  translate([0, boss_y, -1])
    cylinder(h = th + 2, d = hole_d);
  // engrave
  if (emboss == 0)
    translate([0, 0, th - text_height]) text_block();
}
