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
pip install huggingface_hub trimesh numpy scipy manifold3d rtree scikit-image
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

- Scale cannot be gated. A generated mesh is unit-normalised and its real
  size is unknowable by inspection; `plausible_mm_scale` catches only the
  obvious case. Real size has to be supplied, exactly as `tapgraft` requires
  a caliper-measured `--height`.
- `min_wall_thickness` is sampled, not exact; exact thickness needs a medial
  axis. It is sized to catch paper-thin shells, not to certify a wall.
- trimesh's `fill_holes` closes only 3- and 4-edge holes, so the repair stage
  fixes far less than its name suggests.
