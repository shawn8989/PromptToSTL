/**
 * Lithophane generation core.
 *
 * Algorithm overview:
 * 1. Receive a preprocessed grayscale image (as ImageData or Uint8ClampedArray).
 * 2. Build a heightmap: each pixel → Z value in [minThickness, maxThickness] mm.
 *    Dark pixels = high Z (thick plastic, less light passes through).
 * 3. Rasterize the chosen shape into a boolean mask at the same resolution.
 * 4. Build a top surface mesh (grid of quads, each quad = 2 triangles).
 *    - Only emit quads that are fully inside the mask.
 * 5. Build a flat bottom surface at Z = 0.
 * 6. Build side walls connecting the perimeter of the shape outline.
 * 7. Optionally add a raised border frame around the shape.
 * 8. Return an array of Triangle objects ready for STL export.
 *
 * Coordinate system: X+ right, Y+ up, Z+ toward viewer.
 * Origin is at the bottom-left of the plate in XY, Z=0 is the flat back face.
 */

import type { HeightmapData, LithophaneSettings, Triangle, Vec3 } from '@/types';
import type { ShapeId } from '@/types';

// ---- Heightmap extraction -----------------------------------------------

/** Convert RGBA pixel data (from canvas) to a normalised grayscale heightmap. */
export function imageDataToHeightmap(
  rgba: Uint8ClampedArray,
  imgWidth: number,
  imgHeight: number,
  targetWidth: number,
  targetHeight: number
): HeightmapData {
  // Bilinear downsample + grayscale
  const data = new Float32Array(targetWidth * targetHeight);

  for (let ty = 0; ty < targetHeight; ty++) {
    for (let tx = 0; tx < targetWidth; tx++) {
      // Map target pixel to source image coordinates
      const sx = (tx / (targetWidth - 1)) * (imgWidth - 1);
      const sy = (ty / (targetHeight - 1)) * (imgHeight - 1);

      const x0 = Math.floor(sx);
      const y0 = Math.floor(sy);
      const x1 = Math.min(x0 + 1, imgWidth - 1);
      const y1 = Math.min(y0 + 1, imgHeight - 1);
      const fx = sx - x0;
      const fy = sy - y0;

      const sample = (x: number, y: number): number => {
        const idx = (y * imgWidth + x) * 4;
        const r = rgba[idx];
        const g = rgba[idx + 1];
        const b = rgba[idx + 2];
        // Luminance-weighted grayscale
        return (0.299 * r + 0.587 * g + 0.114 * b) / 255;
      };

      const v00 = sample(x0, y0);
      const v10 = sample(x1, y0);
      const v01 = sample(x0, y1);
      const v11 = sample(x1, y1);

      // Bilinear interpolation
      const value =
        v00 * (1 - fx) * (1 - fy) +
        v10 * fx * (1 - fy) +
        v01 * (1 - fx) * fy +
        v11 * fx * fy;

      data[ty * targetWidth + tx] = value;
    }
  }

  return { width: targetWidth, height: targetHeight, data };
}

// ---- Triangle helpers ---------------------------------------------------

function normal(a: Vec3, b: Vec3, c: Vec3): Vec3 {
  const ux = b.x - a.x, uy = b.y - a.y, uz = b.z - a.z;
  const vx = c.x - a.x, vy = c.y - a.y, vz = c.z - a.z;
  const nx = uy * vz - uz * vy;
  const ny = uz * vx - ux * vz;
  const nz = ux * vy - uy * vx;
  const len = Math.sqrt(nx * nx + ny * ny + nz * nz) || 1;
  return { x: nx / len, y: ny / len, z: nz / len };
}

function tri(a: Vec3, b: Vec3, c: Vec3): Triangle {
  return { a, b, c, normal: normal(a, b, c) };
}

// ---- Main generation function -------------------------------------------

export interface GenerationOptions {
  shapeId: ShapeId;
  customText?: string;
  heightmap: HeightmapData;
  settings: LithophaneSettings;
}

export function generateLithoMesh(opts: GenerationOptions): Triangle[] {
  const { heightmap, settings } = opts;
  const {
    minThickness,
    maxThickness,
    plateWidth,
    plateHeight,
    borderWidth,
  } = settings;

  const hmW = heightmap.width;
  const hmH = heightmap.height;
  const hmData = heightmap.data;

  // Physical size of each pixel cell in mm
  // The lithophane fills the shape interior; we fit it within plateWidth × plateHeight
  // minus the border on each side.
  const innerW = plateWidth - borderWidth * 2;
  const innerH = plateHeight - borderWidth * 2;
  const cellW = innerW / hmW;
  const cellH = innerH / hmH;

  // Pixel → world coords (bottom-left origin)
  // X: borderWidth + col*cellW
  // Y: borderWidth + row*cellH
  // Z: computed from heightmap

  // Rasterise shape mask at heightmap resolution (unused in Phase 1, reserved for Phase 2)
  // const shapeDef = getShape(shapeId);
  // const svgPath = shapeDef.generatePath(hmW, hmH);

  // We need to rasterize server-side or client-side.
  // The mask is computed in the browser via canvas; here we just build geometry
  // for the full heightmap and the caller provides a pre-rasterised mask.
  // For single-shape export we pass maskFn.
  const triangles: Triangle[] = [];

  // Helper to get Z height from heightmap value (0=dark=tall)
  // Lithophane: bright pixel → thin → low Z; dark pixel → thick → high Z
  // Since we already inverted in preprocessing, high value = thick.
  const getZ = (hmValue: number): number =>
    minThickness + hmValue * (maxThickness - minThickness);

  // Build vertex grid
  // Vertices are at grid corners (hmW+1) × (hmH+1)
  const verts: Vec3[][] = Array.from({ length: hmH + 1 }, (_, row) =>
    Array.from({ length: hmW + 1 }, (_, col) => {
      // Interpolate height from surrounding pixels
      const px = Math.min(col, hmW - 1);
      const py = Math.min(row, hmH - 1);
      const hmVal = hmData[py * hmW + px];
      const x = borderWidth + col * cellW;
      const y = borderWidth + row * cellH;
      const z = getZ(hmVal);
      return { x, y, z };
    })
  );

  // Bottom vertex grid (Z = 0)
  const bottomVerts: Vec3[][] = Array.from({ length: hmH + 1 }, (_, row) =>
    Array.from({ length: hmW + 1 }, (_, col) => {
      const x = borderWidth + col * cellW;
      const y = borderWidth + row * cellH;
      return { x, y, z: 0 };
    })
  );

  // Top surface quads
  for (let row = 0; row < hmH; row++) {
    for (let col = 0; col < hmW; col++) {
      const tl = verts[row][col];
      const tr = verts[row][col + 1];
      const bl = verts[row + 1][col];
      const br = verts[row + 1][col + 1];
      // Two triangles per quad (CCW when viewed from +Z)
      triangles.push(tri(tl, bl, br));
      triangles.push(tri(tl, br, tr));
    }
  }

  // Bottom surface (flat at Z=0, normals pointing -Z)
  for (let row = 0; row < hmH; row++) {
    for (let col = 0; col < hmW; col++) {
      const tl = bottomVerts[row][col];
      const tr = bottomVerts[row][col + 1];
      const bl = bottomVerts[row + 1][col];
      const br = bottomVerts[row + 1][col + 1];
      // Reversed winding for outward-facing normal (-Z)
      triangles.push(tri(tl, br, bl));
      triangles.push(tri(tl, tr, br));
    }
  }

  // Side walls — left edge (x = borderWidth)
  for (let row = 0; row < hmH; row++) {
    const top0 = verts[row][0];
    const top1 = verts[row + 1][0];
    const bot0 = bottomVerts[row][0];
    const bot1 = bottomVerts[row + 1][0];
    triangles.push(tri(top0, bot0, bot1));
    triangles.push(tri(top0, bot1, top1));
  }

  // Right edge
  for (let row = 0; row < hmH; row++) {
    const top0 = verts[row][hmW];
    const top1 = verts[row + 1][hmW];
    const bot0 = bottomVerts[row][hmW];
    const bot1 = bottomVerts[row + 1][hmW];
    triangles.push(tri(top0, bot1, bot0));
    triangles.push(tri(top0, top1, bot1));
  }

  // Bottom edge (row = 0)
  for (let col = 0; col < hmW; col++) {
    const top0 = verts[0][col];
    const top1 = verts[0][col + 1];
    const bot0 = bottomVerts[0][col];
    const bot1 = bottomVerts[0][col + 1];
    triangles.push(tri(top0, top1, bot1));
    triangles.push(tri(top0, bot1, bot0));
  }

  // Top edge (row = hmH)
  for (let col = 0; col < hmW; col++) {
    const top0 = verts[hmH][col];
    const top1 = verts[hmH][col + 1];
    const bot0 = bottomVerts[hmH][col];
    const bot1 = bottomVerts[hmH][col + 1];
    triangles.push(tri(top0, bot1, top1));
    triangles.push(tri(top0, bot0, bot1));
  }

  return triangles;
}

// ---- Image preprocessing (browser-side) ---------------------------------

export interface PreprocessingOptions {
  brightness: number;  // -100 to 100
  contrast: number;    // -100 to 100
  gamma: number;       // 0.1 to 3.0
  invert: boolean;
}

/** Apply brightness/contrast/gamma/invert to RGBA pixel data in place. */
export function applyPreprocessing(
  data: Uint8ClampedArray,
  opts: PreprocessingOptions
): void {
  const { brightness, contrast, gamma, invert } = opts;

  // Precompute LUT for speed (0-255)
  const lut = new Uint8ClampedArray(256);
  for (let i = 0; i < 256; i++) {
    let v = i / 255;

    // Brightness: linear shift
    v = v + brightness / 100;

    // Contrast: S-curve around 0.5
    const c = (contrast / 100) * 2.55;
    const f = (259 * (c + 255)) / (255 * (259 - c));
    v = f * (v - 0.5) + 0.5;

    // Gamma correction
    v = Math.pow(Math.max(0, v), 1 / gamma);

    // Invert
    if (invert) v = 1 - v;

    lut[i] = Math.round(Math.min(255, Math.max(0, v * 255)));
  }

  for (let i = 0; i < data.length; i += 4) {
    // Convert to grayscale first, then apply LUT
    const gray = Math.round(0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2]);
    const val = lut[gray];
    data[i] = val;
    data[i + 1] = val;
    data[i + 2] = val;
    // Alpha unchanged
  }
}
