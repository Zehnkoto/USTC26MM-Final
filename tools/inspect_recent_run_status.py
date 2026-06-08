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
    for run in runs[:20]:
        record = read_json(run / "run.json") or read_json(run / "status.json")
        payload = read_json(run / "payload.json") or {}
        if not record:
            continue
        print("===", run.name, "===")
        print("model:", record.get("modelId") or payload.get("modelId"))
        print("status:", record.get("status"), "progress:", record.get("progress"), "mode:", record.get("configMode"))
        error = record.get("error")
        if error:
            print("error:", str(error)[:1200])
        stderr = record.get("stderrTail")
        if stderr:
            print("stderr_tail:", str(stderr)[-1200:])


if __name__ == "__main__":
    main()
