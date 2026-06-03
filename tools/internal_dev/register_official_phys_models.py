#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path


ROOT = Path("/root/autodl-tmp/ustc26mm")
PHYS_MODEL_ROOT = ROOT / "src/physgaussian-src/model"
WORK_MODELS_ROOT = ROOT / "work/models"
CONFIG_ROOT = ROOT / "src/physgaussian-src/config"

MODELS = {
    "bread-sample": ("bread-trained", "tear_bread_config.json"),
    "ficus-sample": ("ficus_whitebg-trained", "ficus_config.json"),
    "pillow2sofa-sample": ("pillow2sofa_whitebg-trained", "pillow2sofa_config.json"),
    "plane-sample": ("plane-trained", "plane_config.json"),
    "vasedeck-sample": ("vasedeck_whitebg-trained", "vasedeck_config.json"),
    "wolf-sample": ("wolf_whitebg-trained", "wolf_config.json"),
}


def iteration_number(path: Path) -> int:
    try:
        return int(path.parent.name.split("_")[-1])
    except ValueError:
        return -1


def link_or_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        target.unlink()
    try:
        os.link(source, target)
    except OSError:
        shutil.copy2(source, target)


def register(model_id: str, model_folder: str, config_name: str) -> None:
    model_root = PHYS_MODEL_ROOT / model_folder
    point_clouds = sorted(
        (model_root / "point_cloud").glob("iteration_*/point_cloud.ply"),
        key=iteration_number,
    )
    if not point_clouds:
        return

    base_ply = point_clouds[-1]
    iteration = base_ply.parent.name
    model_dir = WORK_MODELS_ROOT / model_id
    preview_ply = model_dir / "model/point_cloud" / iteration / "point_cloud.ply"
    link_or_copy(base_ply, preview_ply)

    record = {
        "modelId": model_id,
        "kind": "official-physgaussian",
        "uploadName": f"{model_folder}.zip",
        "modelRoot": str(model_root),
        "basePly": str(base_ply),
        "basePlyUrl": f"/models/{model_id}/model/point_cloud/{iteration}/point_cloud.ply",
        "basePlyName": base_ply.name,
        "officialConfig": str(CONFIG_ROOT / config_name),
    }
    (model_dir / "model.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(f"registered {model_id}: {base_ply}")


def main() -> None:
    for model_id, (model_folder, config_name) in MODELS.items():
        register(model_id, model_folder, config_name)


if __name__ == "__main__":
    main()
