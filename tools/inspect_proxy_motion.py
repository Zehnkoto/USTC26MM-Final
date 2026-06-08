#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import struct
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: inspect_proxy_motion.py RUN_ID")
    run_id = sys.argv[1]
    root = Path("/root/autodl-tmp/ustc26mm/work/runs") / run_id / "physgaussian" / "super_motion"
    manifest = json.loads((root / "motion.physmotion.json").read_text(encoding="utf-8"))
    proxy = manifest["proxy"]
    group_count = int(proxy["groupCount"])
    frame_count = int(manifest["frameCount"])
    data = (root / "proxy_motion.bin").read_bytes()
    floats = struct.unpack("<" + "f" * (len(data) // 4), data)
    stride = group_count * 7
    first = floats[:stride]
    last = floats[(frame_count - 1) * stride : frame_count * stride]
    displacements = []
    for group_id in range(group_count):
        offset = group_id * 3
        dx = last[offset + 0] - first[offset + 0]
        dy = last[offset + 1] - first[offset + 1]
        dz = last[offset + 2] - first[offset + 2]
        displacements.append((math.sqrt(dx * dx + dy * dy + dz * dz), group_id, (dx, dy, dz)))
    moved = [item for item in displacements if item[0] > 1e-5]
    displacements.sort(reverse=True)
    print("run", run_id)
    print("group_count", group_count)
    print("moved_count", len(moved))
    print("preview", json.dumps(manifest.get("preview"), ensure_ascii=False, indent=2))
    print("top_displacements")
    for distance, group_id, vector in displacements[:10]:
        print(group_id, distance, vector)


if __name__ == "__main__":
    main()
