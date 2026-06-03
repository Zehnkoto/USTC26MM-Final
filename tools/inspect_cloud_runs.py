from __future__ import annotations

import json
from pathlib import Path


ROOT = Path("/root/autodl-tmp/ustc26mm/work/runs")


def tail(path: Path, limit: int = 1600) -> str:
    try:
        return path.read_text(errors="ignore")[-limit:].replace("\n", " | ")
    except Exception as exc:
        return f"<read failed: {exc}>"


def main() -> None:
    runs = []
    if ROOT.exists():
        for path in ROOT.iterdir():
            if path.is_dir():
                runs.append((path.stat().st_mtime, path))
    runs.sort(reverse=True)

    print(f"runs_root={ROOT}")
    for _mtime, run_dir in runs[:15]:
        print(f"\n--- {run_dir.name}")
        meta_path = run_dir / "run.json"
        if meta_path.exists():
            try:
                data = json.loads(meta_path.read_text(errors="ignore"))
            except Exception as exc:
                data = {"read_error": str(exc)}
            keys = [
                "runId",
                "status",
                "progress",
                "configMode",
                "modelId",
                "error",
                "returnCode",
                "startedAt",
                "updatedAt",
            ]
            print(json.dumps({key: data.get(key) for key in keys}, ensure_ascii=False))
        else:
            print("no run.json")

        for rel in [
            "physgaussian/stdout.log",
            "physgaussian/stderr.log",
            "stdout.log",
            "stderr.log",
            "payload.json",
        ]:
            path = run_dir / rel
            if path.exists():
                print(f"{rel}: {tail(path)}")


if __name__ == "__main__":
    main()
