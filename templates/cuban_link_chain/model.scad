// Cuban link chain (simplified)

chain_layout = 0; // 0=line, 1=ring
link_count = 18;
link_outer_d = 18;
link_band = 5;
link_th = 4;
link_flatten = 0.7;
link_overlap = 0.35;
ring_radius = 60;

plate_enabled = 1;
plate_w = 50;
plate_h = 20;
plate_th = 3;
plate_radius = 3;
plate_offset_x = 0;
plate_offset_y = 0;

text_enabled = 1;
line1 = "CUSTOM";
line2 = "";
line3 = "";
text_size = 10;
text_height = 1.0;
line_gap = 8;
offset_x = 0;
offset_y = 0;
text_align = "center";
emboss = 1;

emblem_enabled = 0;
emblem_path = "";
emblem_scale = 0.25;
emblem_x = 0;
emblem_y = 0;
emblem_rot = 0;
emblem_mode = 1;
emblem_depth = 1.2;

$fn = 64;

module rounded_rect_2d(width, height, radius) {
  r_eff = min(radius, min(width, height) / 2);
  hull() {
    translate([ width/2 - r_eff,  height/2 - r_eff]) circle(r=r_eff);
    translate([-width/2 + r_eff,  height/2 - r_eff]) circle(r=r_eff);
    translate([ width/2 - r_eff, -height/2 + r_eff]) circle(r=r_eff);
    translate([-width/2 + r_eff, -height/2 + r_eff]) circle(r=r_eff);
  }
}

module link_shape() {
  inner_d = max(1, link_outer_d - 2 * link_band);
  scale([1, link_flatten, 1])
    difference() {
      cylinder(d=link_outer_d, h=link_th, center=true);
      cylinder(d=inner_d, h=link_th + 0.2, center=true);
    }
}

module chain_line() {
  pitch = link_outer_d * (1 - link_overlap);
  total = (link_count - 1) * pitch;
  for (i = [0 : link_count - 1]) {
    x = -total / 2 + i * pitch;
    translate([x, 0, 0])
      rotate([0, (i % 2) * 90, 0])
        link_shape();
  }
}

module chain_ring() {
  for (i = [0 : link_count - 1]) {
    angle = 360 / link_count * i;
    rotate([0, 0, angle])
      translate([ring_radius, 0, 0])
        rotate([0, (i % 2) * 90, 0])
          link_shape();
  }
}

module chain_body() {
  if (chain_layout == 1) {
    chain_ring();
  } else {
    chain_line();
  }
}

module plate_body() {
  if (plate_enabled == 1) {
    translate([plate_offset_x, plate_offset_y, 0])
      linear_extrude(height=plate_th, center=true)
        rounded_rect_2d(plate_w, plate_h, plate_radius);
  }
}

module line_text_3d(s, y) {
  translate([plate_offset_x + offset_x, plate_offset_y + offset_y + y, 0])
    linear_extrude(height=text_height)
      text(s, size=text_size, halign=text_align, valign="center");
}

module text_union() {
  if (plate_enabled == 1 && text_enabled == 1) {
    if (line2 == "" && line3 == "") {
      line_text_3d(line1, 0);
    } else if (line3 == "") {
      line_text_3d(line1, line_gap / 2);
      line_text_3d(line2, -line_gap / 2);
    } else {
      line_text_3d(line1, line_gap);
      line_text_3d(line2, 0);
      line_text_3d(line3, -line_gap);
    }
  }
}

module emblem_3d(z) {
  if (plate_enabled == 1 && emblem_enabled == 1 && emblem_path != "") {
    translate([plate_offset_x + emblem_x, plate_offset_y + emblem_y, z])
      rotate([0, 0, emblem_rot])
        scale([emblem_scale, emblem_scale, 1])
          linear_extrude(height=emblem_depth)
            import(emblem_path);
  }
}

module body() {
  union() {
    chain_body();
    plate_body();
  }
}

plate_top_z = plate_th / 2;

if (emboss == 1) {
  union() {
    difference() {
      body();
      if (emblem_mode == 0) {
        emblem_3d(plate_top_z - emblem_depth);
      }
    }
    translate([0, 0, plate_top_z]) text_union();
    if (emblem_mode == 1) {
      emblem_3d(plate_top_z);
    }
  }
} else {
  difference() {
    body();
    translate([0, 0, plate_top_z - text_height]) text_union();
    if (emblem_mode == 0) {
      emblem_3d(plate_top_z - emblem_depth);
    }
  }
  if (emblem_mode == 1) {
    emblem_3d(plate_top_z);
  }
}
