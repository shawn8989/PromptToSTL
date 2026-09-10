# Generative 3D evaluation

Research tooling for the question "can a generated mesh be printed?".
Nothing here is wired into the app; it exists to produce numbers before any
generative path is built.

## Why

Generative 3D models (TRELLIS, Hunyuan3D, Meshy) emit GLB/OBJ/PLY tuned for
rendering. "Watertight" is a vendor claim, and a mesh can satisfy every
standard topology test while being a hollow shell that cannot be printed.
`printability_gate.py` is the check that decides, and it treats wall
thickness and genus as first-class rather than trusting watertightness.

## Use

```bash
pip install huggingface_hub trimesh numpy scipy manifold3d rtree scikit-image networkx
python3 fetch_arena_meshes.py ./arena
python3 printability_gate.py ./arena
```

`rtree` and `scikit-image` are not optional. Without `rtree` the wall
thickness check cannot cast rays and reports every mesh as failing, which
looks identical to bad geometry.

Meshes come from `3d-arena/3d-arena` (MIT), where every model is run on the
same inputs, so results are directly comparable across vendors.

## Output

Per mesh, one of three verdicts: `pass_unmodified`, `pass_after_repair`, or
`unsalvageable`, plus the checks that failed and what repair cost in
fidelity. The tally of those three is the number that decides whether a
generative path is a feature or a demo.

## Known limits

- Scale is normalised, not judged. Generated meshes are unit-normalised, so
  every mesh is scaled to `TARGET_MM` (60 mm) before geometry is checked.
  Gating on delivered size would fail every generated mesh on a trivially
  fixable property and hide whether the geometry is sound. Real size still
  has to be supplied, exactly as `tapgraft` requires a caliper-measured
  `--height`; this tool cannot establish it.
- `min_wall_thickness` is sampled, not exact; exact thickness needs a medial
  axis. It is sized to catch paper-thin shells, not to certify a wall.
- trimesh's `fill_holes` closes only 3- and 4-edge holes, so the repair stage
  fixes far less than its name suggests.
