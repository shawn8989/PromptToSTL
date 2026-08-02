import type { ShapeDefinition, ShapeId } from '@/types';

// Heart shape using cubic bezier, natural size 100x100
function heartPath(w: number, h: number): string {
  const x = w / 2;
  // Classic heart parametric → bezier approximation
  return [
    `M ${x} ${h * 0.3}`,
    `C ${x} ${h * 0.15}, ${w * 0.05} ${h * 0.0}, ${w * 0.25} ${h * 0.0}`,
    `C ${w * 0.45} ${h * 0.0}, ${x} ${h * 0.15}, ${x} ${h * 0.3}`,
    `C ${x} ${h * 0.15}, ${w * 0.55} ${h * 0.0}, ${w * 0.75} ${h * 0.0}`,
    `C ${w * 0.95} ${h * 0.0}, ${w} ${h * 0.15}, ${w} ${h * 0.3}`,
    `C ${w} ${h * 0.55}, ${w * 0.8} ${h * 0.7}, ${x} ${h * 0.98}`,
    `C ${w * 0.2} ${h * 0.7}, ${w * 0.0} ${h * 0.55}, ${w * 0.0} ${h * 0.3}`,
    `Z`,
  ].join(' ');
}

// Regular n-gon
function polygonPath(w: number, h: number, sides: number, startAngle = 0): string {
  const cx = w / 2;
  const cy = h / 2;
  const rx = w / 2;
  const ry = h / 2;
  const pts = Array.from({ length: sides }, (_, i) => {
    const a = (startAngle + (i * 2 * Math.PI) / sides);
    return { x: cx + rx * Math.cos(a), y: cy + ry * Math.sin(a) };
  });
  return pts
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(3)} ${p.y.toFixed(3)}`)
    .join(' ') + ' Z';
}

// Circle via two arcs
function circlePath(w: number, h: number): string {
  const cx = w / 2;
  const cy = h / 2;
  const rx = w / 2;
  const ry = h / 2;
  return `M ${cx - rx} ${cy} A ${rx} ${ry} 0 1 0 ${cx + rx} ${cy} A ${rx} ${ry} 0 1 0 ${cx - rx} ${cy} Z`;
}

// Rectangle with rounded corners
function rectPath(w: number, h: number, r = 5): string {
  const rr = Math.min(r, w / 4, h / 4);
  return [
    `M ${rr} 0`,
    `L ${w - rr} 0`,
    `Q ${w} 0 ${w} ${rr}`,
    `L ${w} ${h - rr}`,
    `Q ${w} ${h} ${w - rr} ${h}`,
    `L ${rr} ${h}`,
    `Q 0 ${h} 0 ${h - rr}`,
    `L 0 ${rr}`,
    `Q 0 0 ${rr} 0`,
    `Z`,
  ].join(' ');
}

// Oval (ellipse via arcs)
function ovalPath(w: number, h: number): string {
  return circlePath(w, h); // ellipse with different w/h
}

// Generate text path using Canvas 2D measureText heuristic
// Returns an SVG path approximation using per-letter bounding rectangles
// For production, opentype.js is used; this is the fallback
export function generateTextShapePath(
  text: string,
  w: number,
  h: number
): string {
  // Simple approach: one rectangle per character with slight gaps
  const n = text.length;
  if (n === 0) return rectPath(w, h);
  const charW = w / n;
  const gap = charW * 0.05;
  const rects = Array.from({ length: n }, (_, i) => {
    const x = i * charW + gap;
    const cw = charW - 2 * gap;
    return rectPath(cw, h * 0.9)
      .replace(/M /g, `M ${x} ${h * 0.05} `)
      .split('M ')[1];
  });
  return rects.map((r) => `M ${r}`).join(' ');
}

export const SHAPES: Record<ShapeId, ShapeDefinition> = {
  heart: {
    id: 'heart',
    label: 'Heart',
    category: 'geometric',
    aspectRatio: 1,
    generatePath: (w, h) => heartPath(w, h),
  },
  circle: {
    id: 'circle',
    label: 'Circle',
    category: 'geometric',
    aspectRatio: 1,
    generatePath: (w, h) => circlePath(w, h),
  },
  square: {
    id: 'square',
    label: 'Square',
    category: 'geometric',
    aspectRatio: 1,
    generatePath: (w, h) => rectPath(w, h, w * 0.05),
  },
  rectangle: {
    id: 'rectangle',
    label: 'Rectangle',
    category: 'geometric',
    aspectRatio: 4 / 3,
    generatePath: (w, h) => rectPath(w, h, Math.min(w, h) * 0.05),
  },
  hexagon: {
    id: 'hexagon',
    label: 'Hexagon',
    category: 'geometric',
    aspectRatio: Math.cos(Math.PI / 6) * 2,
    generatePath: (w, h) => polygonPath(w, h, 6, -Math.PI / 2),
  },
  oval: {
    id: 'oval',
    label: 'Oval',
    category: 'geometric',
    aspectRatio: 4 / 3,
    generatePath: (w, h) => ovalPath(w, h),
  },
  text_mom: {
    id: 'text_mom',
    label: 'MOM',
    category: 'text',
    aspectRatio: 3 / 1,
    generatePath: (w, h) => generateTextShapePath('MOM', w, h),
  },
  text_dad: {
    id: 'text_dad',
    label: 'DAD',
    category: 'text',
    aspectRatio: 3 / 1,
    generatePath: (w, h) => generateTextShapePath('DAD', w, h),
  },
  text_love: {
    id: 'text_love',
    label: 'LOVE',
    category: 'text',
    aspectRatio: 4 / 1,
    generatePath: (w, h) => generateTextShapePath('LOVE', w, h),
  },
  text_family: {
    id: 'text_family',
    label: 'FAMILY',
    category: 'text',
    aspectRatio: 6 / 1,
    generatePath: (w, h) => generateTextShapePath('FAMILY', w, h),
  },
  text_baby: {
    id: 'text_baby',
    label: 'BABY',
    category: 'text',
    aspectRatio: 4 / 1,
    generatePath: (w, h) => generateTextShapePath('BABY', w, h),
  },
  text_custom: {
    id: 'text_custom',
    label: 'Custom Text',
    category: 'text',
    aspectRatio: 1,
    generatePath: (w, h) => rectPath(w, h),
  },
};

export function getShape(id: ShapeId): ShapeDefinition {
  return SHAPES[id];
}

export function getAllShapes(): ShapeDefinition[] {
  return Object.values(SHAPES);
}

export function getGeometricShapes(): ShapeDefinition[] {
  return getAllShapes().filter((s) => s.category === 'geometric');
}

export function getTextShapes(): ShapeDefinition[] {
  return getAllShapes().filter((s) => s.category === 'text');
}

// Rasterize an SVG path into a boolean mask using OffscreenCanvas
// Returns a Uint8Array of length width*height, 1 = inside shape, 0 = outside
export function rasterizeShapeMask(
  svgPath: string,
  width: number,
  height: number
): Uint8Array {
  const mask = new Uint8Array(width * height);

  // Use Path2D + OffscreenCanvas if available
  if (typeof OffscreenCanvas !== 'undefined') {
    const canvas = new OffscreenCanvas(width, height);
    const ctx = canvas.getContext('2d')!;
    const path = new Path2D(svgPath);
    ctx.fillStyle = '#fff';
    ctx.fill(path);
    const imgData = ctx.getImageData(0, 0, width, height);
    for (let i = 0; i < width * height; i++) {
      mask[i] = imgData.data[i * 4] > 128 ? 1 : 0;
    }
  } else {
    // Fallback: all inside (for SSR / non-browser)
    mask.fill(1);
  }

  return mask;
}
