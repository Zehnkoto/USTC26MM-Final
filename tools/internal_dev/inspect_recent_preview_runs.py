#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path("/root/autodl-tmp/ustc26mm/work/runs")


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def main() -> None:
    runs = sorted(
        [path for path in ROOT.iterdir() if path.is_dir()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    shown = 0
    for run in runs:
        payload = read_json(run / "payload.json")
        manifest = read_json(run / "physgaussian" / "super_motion" / "motion.physmotion.json")
        if not payload or not manifest:
            continue
        preview = manifest.get("preview") or {}
        if not preview.get("dragMode"):
            continue
        objects = payload.get("objects") or []
        body_counts: dict[int, int] = {}
        object_summaries = []
        for part in objects:
            body_id = int(part.get("bodyId", part.get("objectId", -1)) or -1)
            indices = part.get("indices") or []
            body_counts[body_id] = body_counts.get(body_id, 0) + len(indices)
            object_summaries.append(
                {
                    "objectId": part.get("objectId"),
                    "bodyId": part.get("bodyId"),
                    "name": part.get("name"),
                    "material": (part.get("material") or {}).get("material") if isinstance(part.get("material"), dict) else part.get("material"),
                    "indices": len(indices),
                }
            )
        print("===", run.name, "===")
        print("modelId:", payload.get("modelId"))
        print("objects:", len(objects), "body_counts:", body_counts)
        print("preview:", json.dumps(preview, ensure_ascii=False, indent=2))
        print("object_summaries:", json.dumps(object_summaries[:8], ensure_ascii=False, indent=2))
        shown += 1
        if shown >= 8:
            break


if __name__ == "__main__":
    main()
