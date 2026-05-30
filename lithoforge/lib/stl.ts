/**
 * Binary STL exporter.
 *
 * Format: 80-byte header | uint32 triangle count |
 *   per triangle: float32[3] normal, float32[3]*3 vertices, uint16 attr (0)
 * Total: 84 + 50 * triangleCount bytes
 */

import type { Triangle } from '@/types';

const HEADER_BYTES = 80;
const TRIANGLE_BYTES = 50; // 12 floats * 4 bytes + 2 attr bytes

export function trianglesToBinarySTL(triangles: Triangle[]): ArrayBuffer {
  const count = triangles.length;
  const buffer = new ArrayBuffer(HEADER_BYTES + 4 + count * TRIANGLE_BYTES);
  const view = new DataView(buffer);

  // Header: ASCII "LithoForge STL" padded to 80 bytes
  const header = 'LithoForge STL export';
  for (let i = 0; i < HEADER_BYTES; i++) {
    view.setUint8(i, i < header.length ? header.charCodeAt(i) : 0);
  }

  // Triangle count
  view.setUint32(HEADER_BYTES, count, true);

  let offset = HEADER_BYTES + 4;

  for (const t of triangles) {
    // Normal
    view.setFloat32(offset, t.normal.x, true); offset += 4;
    view.setFloat32(offset, t.normal.y, true); offset += 4;
    view.setFloat32(offset, t.normal.z, true); offset += 4;
    // Vertex A
    view.setFloat32(offset, t.a.x, true); offset += 4;
    view.setFloat32(offset, t.a.y, true); offset += 4;
    view.setFloat32(offset, t.a.z, true); offset += 4;
    // Vertex B
    view.setFloat32(offset, t.b.x, true); offset += 4;
    view.setFloat32(offset, t.b.y, true); offset += 4;
    view.setFloat32(offset, t.b.z, true); offset += 4;
    // Vertex C
    view.setFloat32(offset, t.c.x, true); offset += 4;
    view.setFloat32(offset, t.c.y, true); offset += 4;
    view.setFloat32(offset, t.c.z, true); offset += 4;
    // Attribute byte count
    view.setUint16(offset, 0, true); offset += 2;
  }

  return buffer;
}

export function downloadSTL(triangles: Triangle[], filename: string): void {
  const buffer = trianglesToBinarySTL(triangles);
  const blob = new Blob([buffer], { type: 'application/octet-stream' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename.endsWith('.stl') ? filename : `${filename}.stl`;
  a.click();
  URL.revokeObjectURL(url);
}
