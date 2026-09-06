#!/usr/bin/env python3
"""Fetch generated meshes from the 3D Arena benchmark for printability testing.

Every model in that dataset is run on the same input images, so outputs are
directly comparable across vendors.

    pip install huggingface_hub trimesh numpy scipy manifold3d rtree scikit-image
    python3 fetch_arena_meshes.py ./arena
    python3 printability_gate.py ./arena

Set HF_TOKEN first if you have one. Unauthenticated Hub requests are rate
limited, and the client retries a 429 with silent backoff, which is
indistinguishable from a hang when pulling forty files in a row.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

REPO = "3d-arena/3d-arena"
MODELS = ["TRELLIS.2-4B", "Hunyuan3D-2.1", "Meshy-6", "Meshy-5"]

# Compact single objects: the realistic tap-handle-topper case. Deliberately
# excludes multi-object scenes, which no printable-object pipeline would send.
ITEMS = [
    "A_heart_made_of_wood",
    "a_baby_penguin",
    "a_cat_statue",
    "a_hammer",
    "a_green_pepper",
    "a_bowl",
    "a_ball",
    "a_chest",
    "a_fox",
    "a_half-full_pitcher_of_stout",
]


def main(argv: list[str]) -> int:
    from huggingface_hub import hf_hub_download

    out = Path(argv[0]) if argv else Path("./arena")
    out.mkdir(parents=True, exist_ok=True)

    if not (os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")):
        print("note: no HF_TOKEN set; downloads are rate limited and may stall\n",
              file=sys.stderr, flush=True)

    total = len(MODELS) * len(ITEMS)
    done = failed = 0
    started = time.time()

    for model in MODELS:
        (out / model).mkdir(parents=True, exist_ok=True)
        for item in ITEMS:
            done += 1
            rel = f"outputs/{model}/{item}.glb"
            # Announce BEFORE the download, not after: a large file with no
            # output looks identical to a hung process.
            print(f"[{done:>2}/{total}] {model}/{item}.glb ... ",
                  end="", flush=True)
            t = time.time()
            try:
                src = hf_hub_download(repo_id=REPO, filename=rel,
                                      repo_type="dataset")
                dest = out / model / f"{item}.glb"
                if not dest.exists():
                    dest.write_bytes(Path(src).read_bytes())
                mb = dest.stat().st_size / 1e6
                print(f"{mb:.1f} MB in {time.time() - t:.1f}s", flush=True)
            except Exception as exc:
                failed += 1
                print(f"FAILED {type(exc).__name__}: {str(exc)[:70]}", flush=True)

    print(f"\n{done - failed}/{total} files in {time.time() - started:.0f}s "
          f"-> {out}/<model>/", flush=True)
    if failed:
        print(f"{failed} failed; rerun to resume (completed files are cached)",
              flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
