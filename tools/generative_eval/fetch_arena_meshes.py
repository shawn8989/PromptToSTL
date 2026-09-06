#!/usr/bin/env python3
"""Fetch generated meshes from the 3D Arena benchmark for printability testing.

Every model in that dataset is run on the same input images, so outputs are
directly comparable. Run this where huggingface.co is reachable, then point
printability_gate.py at the download directory.

    pip install huggingface_hub
    python fetch_arena_meshes.py ./arena
    python printability_gate.py ./arena/TRELLIS.2-4B ./arena/Hunyuan3D-2.1 ./arena/Meshy-6
"""
from __future__ import annotations

import sys
from pathlib import Path

from huggingface_hub import hf_hub_download

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
    out = Path(argv[0]) if argv else Path("./arena")
    out.mkdir(parents=True, exist_ok=True)
    for model in MODELS:
        for item in ITEMS:
            rel = f"outputs/{model}/{item}.glb"
            try:
                path = hf_hub_download(
                    repo_id=REPO, filename=rel, repo_type="dataset",
                    local_dir=out,
                )
                print(f"ok   {model}/{item}.glb")
            except Exception as exc:
                print(f"MISS {model}/{item}.glb  ({type(exc).__name__})")
    print(f"\ndownloaded under {out}/outputs/<model>/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
