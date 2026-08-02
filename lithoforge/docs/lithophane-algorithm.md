# Lithophane Generation Algorithm

## Overview

A lithophane is a translucent relief image that becomes visible when
backlit. Bright areas of the original photo correspond to thin regions
(more light passes through), while dark areas become thick (less light).

## Pipeline

### Step 1: Image Preprocessing

The raw photo is:
1. Resized to ≤ 1024px on the longest side using bilinear interpolation.
2. Converted to grayscale using luminance weighting: `L = 0.299R + 0.587G + 0.114B`.
3. Brightness-shifted: `v += brightness/100`
4. Contrast-stretched using the standard formula: `v = f*(v-0.5)+0.5` where
   `f = 259*(c+255) / (255*(259-c))`.
5. Gamma-corrected: `v = v^(1/gamma)`.
6. **Inverted** (toggle, default ON): `v = 1 - v`.
   This is the key step — in a lithophane, dark photo regions must become
   *thick* plastic so less light passes through.

### Step 2: Heightmap Construction

The preprocessed image is bilinearly downsampled to the target
heightmap resolution (`resolution` pixels/mm × inner plate dimensions).

Each pixel's luminance value `v ∈ [0,1]` maps to a Z-height:

```
Z = minThickness + v × (maxThickness - minThickness)
```

Default: minThickness = 0.8 mm, maxThickness = 3.0 mm.

### Step 3: Mesh Generation

A regular quad grid is built over the heightmap:
- Grid corners: `(hmW+1) × (hmH+1)` vertices
- Each vertex at `(borderWidth + col×cellW, borderWidth + row×cellH, Z[row][col])`
- Each quad → 2 CCW triangles for the top surface

The mesh also includes:
- **Bottom face**: flat at Z = 0, reverse-wound for outward normals
- **Side walls**: 4 perimeter edges connecting top surface to bottom

The inner dimensions are `plateWidth - 2×borderWidth` × `plateHeight - 2×borderWidth`.
The border is a raised frame at `maxThickness + 1mm` height (flat top, 4 walls,
connected to base).

### Step 4: STL Export

Triangles are serialised as binary STL:
- 80-byte ASCII header
- uint32 triangle count
- Per triangle: 3×float32 normal + 3×(3×float32) vertices + uint16 attribute (0)
- Total size: 84 + 50×N bytes

The resulting file is manifold (no holes) because:
- The top surface, bottom surface, and all 4 side walls share boundary edges.
- Every boundary edge appears exactly twice with opposite windings.

## Shape Masking (Phase 2)

For non-rectangular shapes, the heightmap is clipped by rasterising the
shape's SVG path into a boolean mask using `OffscreenCanvas` / `Path2D`.
Only quads fully inside the mask are emitted. The shape outline is extruded
as a closed wall ring.

## Viewing Tips

- **Solid mode**: standard lit material, good for checking surface detail
- **Backlit mode**: `MeshPhysicalMaterial` with `transmission: 0.6`, warm
  amber light from behind simulates an LED display

## Typical Print Settings

| Parameter       | Value     | Notes |
|-----------------|-----------|-------|
| minThickness    | 0.8 mm    | Minimum wall — must exceed nozzle diameter |
| maxThickness    | 3.0 mm    | Thicker = more contrast; slows print |
| borderWidth     | 3 mm      | Frame around lithophane |
| Infill          | 100%      | Required for opacity |
| Layer height    | 0.1 mm    | Finer detail |
| Material        | PLA/PETG  | White or natural (translucent filament) |
| Print orientation | Flat    | Face down on plate; or vertical for wall mount |
