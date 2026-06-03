#!/usr/bin/env python3
from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path


BASE = "http://127.0.0.1:6006"
WORK = Path("/root/autodl-tmp/ustc26mm/work")


def post(path: str, payload: dict) -> tuple[int, str]:
    request = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def load_recent_payload(run_id: str) -> dict:
    return json.loads((WORK / "runs" / run_id / "payload.json").read_text(encoding="utf-8"))


def manifest_for(result_text: str) -> dict:
    result = json.loads(result_text)
    rel = result["result"]["manifestUrl"].removeprefix("/outputs/")
    return json.loads((WORK / "runs" / rel).read_text(encoding="utf-8"))


def main() -> None:
    # cb067a58bab9 was a user run where object_1=obstacle and object_2=jelly
    # shared bodyId=1, and the old proxy preview incorrectly moved both.
    payload = load_recent_payload("cb067a58bab9")
    payload["simulation"]["preview"]["dragObjectId"] = 2
    payload["simulation"]["preview"]["dragHitIndex"] = 3892
    status, text = post("/api/preview/voxel-rigid", payload)
    print("drag jelly status", status)
    print(text[:600])
    if status == 200:
        manifest = manifest_for(text)
        print("jelly preview", json.dumps(manifest.get("preview"), ensure_ascii=False, indent=2))

    payload = load_recent_payload("30a0e3c5420f")
    payload["simulation"]["preview"]["dragObjectId"] = 1
    payload["simulation"]["preview"]["dragHitIndex"] = 706
    status, text = post("/api/preview/voxel-rigid", payload)
    print("drag obstacle status", status)
    print(text[:600])


if __name__ == "__main__":
    main()
