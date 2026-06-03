#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path


ROOT = Path("/root/autodl-tmp/ustc26mm")
MODEL_ID = "ficus-sample-7000"
MODEL_ROOT = ROOT / "src/physgaussian-src/model/ficus_whitebg-trained"
BASE_PLY = MODEL_ROOT / "point_cloud/iteration_7000/point_cloud.ply"
CONFIG = ROOT / "src/physgaussian-src/config/ficus_config.json"
MODEL_DIR = ROOT / "work/models" / MODEL_ID
PREVIEW_PLY = MODEL_DIR / "model/point_cloud/iteration_7000/point_cloud.ply"


def link_or_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        target.unlink()
    try:
        os.link(source, target)
    except OSError:
        shutil.copy2(source, target)


def main() -> None:
    if not BASE_PLY.exists():
        raise FileNotFoundError(BASE_PLY)
    if not CONFIG.exists():
        raise FileNotFoundError(CONFIG)

    link_or_copy(BASE_PLY, PREVIEW_PLY)
    record = {
        "modelId": MODEL_ID,
        "kind": "official-physgaussian",
        "uploadName": "ficus_whitebg-trained.zip",
        "modelRoot": str(MODEL_ROOT),
        "basePly": str(BASE_PLY),
        "basePlyUrl": f"/models/{MODEL_ID}/model/point_cloud/iteration_7000/point_cloud.ply",
        "basePlyName": BASE_PLY.name,
        "officialConfig": str(CONFIG),
    }
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    (MODEL_DIR / "model.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
