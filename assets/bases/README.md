# Base meshes

Reusable base geometry that finished models are grafted onto. These are
*shared* assets — unlike `templates/<id>/`, a base here is not tied to one
template and is expected to be consumed by many.

Files in this directory are tracked in git despite the global `*.stl` rule in
`.gitignore` (see the `!assets/bases/*.stl` negation).

## `tap-handle-base-28mm.stl`

The standard base for custom 3D-printed beer tap handles. Generated geometry —
not derived from any third-party or client model.

Measured with `trimesh` (units are millimetres):

| Property | Value |
|---|---|
| Bounding box | 21.52 × 21.50 × 28.00 |
| Volume | 7672.01 mm³ |
| Triangles / vertices | 5082 / 2543 |
| Watertight | yes |
| Connected components | 1 |
| Sits on | `z = 0` (min Z is 0.0) |

Profile, sampled as the XY extent of vertices in each Z band:

| Z band | XY extent |
|---|---|
| 0–1 | 19.98 × 19.99 (foot flange) |
| 1–6 | 10.20 × 10.20 (lower shaft) |
| 9–11 | 19.03 × 18.94 (mid bulge) |
| 18–20 | 10.10 × 10.19 (upper shaft) |
| 27–28 | 21.52 × 21.50 (top face) |

### Mounting geometry

`tapgraft --report-only` derives this base's mounting pocket as:

```
diameter 8.526 mm, depth 19.000 mm, mounting face -Z, protected wall 4.000 mm
```

Reproduce it with any scan mesh (`--scan` is required even in report-only mode):

```bash
tapgraft --report-only \
  --scan <any-scan.stl> \
  --base assets/bases/tap-handle-base-28mm.stl
```
