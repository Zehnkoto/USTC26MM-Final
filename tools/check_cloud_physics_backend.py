#!/usr/bin/env python3
from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path


BASE = "http://127.0.0.1:6006"
WORK = Path("/root/autodl-tmp/ustc26mm/work")


def post(path: str, payload: dict):
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        BASE + path,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def main() -> None:
    status, text = post(
        "/api/simulate",
        {
            "modelId": "proxy-pot-small",
            "objects": [],
            "simulation": {"frame_num": 2, "frame_dt": 0.02},
        },
    )
    print("simulate proxy-pot-small:", status)
    print(text[:1000])

    status, text = post(
        "/api/preview/voxel-rigid",
        {
            "modelId": "proxy-pot-small",
            "objects": [],
            "simulation": {
                "frame_num": 4,
                "frame_dt": 0.02,
                "preview": {
                    "dragHitIndex": 0,
                    "dragVelocity": [1.0, 0.0, 0.0],
                    "targetVoxelGroups": 64,
                },
            },
        },
    )
    print("preview proxy-pot-small:", status)
    print(text[:1000])
    if status == 200:
        data = json.loads(text)
        manifest_url = data["result"]["manifestUrl"]
        rel = manifest_url.removeprefix("/outputs/")
        manifest = json.loads((WORK / "runs" / rel).read_text(encoding="utf-8"))
        print("preview manifest preview:", json.dumps(manifest.get("preview"), ensure_ascii=False, indent=2))
        print("proxy:", json.dumps(manifest.get("proxy"), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
