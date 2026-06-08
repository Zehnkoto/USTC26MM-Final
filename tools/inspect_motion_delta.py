#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import struct
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: inspect_motion_delta.py RUN_ID_OR_RUN_DIR")

    arg = Path(sys.argv[1])
    run_dir = arg if arg.exists() else Path("/root/autodl-tmp/ustc26mm/work/runs") / sys.argv[1]
    motion_dir = run_dir / "physgaussian" / "super_motion"
    manifest = json.loads((motion_dir / "motion.physmotion.json").read_text(encoding="utf-8"))
    motion_path = motion_dir / manifest["binary"]
    index_path = motion_dir / manifest.get("indices", "indices.bin")

    attrs = manifest.get("attributes") or ["position"]
    floats_per = sum(4 if attr == "rotation" else 3 for attr in attrs)
    stride = int(manifest["frameStrideBytes"])
    frame_count = int(manifest["frameCount"])
    if frame_count < 2:
        raise SystemExit("frameCount < 2")

    index_count = 0
    if index_path.exists():
        index_count = index_path.stat().st_size // 4
    else:
        index_count = int(manifest["numSplats"])
    count = stride // 4 // floats_per

    with motion_path.open("rb") as stream:
        first_bytes = stream.read(stride)
        stream.seek((frame_count - 1) * stride)
        last_bytes = stream.read(stride)

    first = struct.unpack("<" + "f" * (len(first_bytes) // 4), first_bytes)
    last = struct.unpack("<" + "f" * (len(last_bytes) // 4), last_bytes)

    deltas: list[tuple[float, int, tuple[float, float, float]]] = []
    for i in range(count):
        a = i * floats_per
        dx = last[a + 0] - first[a + 0]
        dy = last[a + 1] - first[a + 1]
        dz = last[a + 2] - first[a + 2]
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)
        deltas.append((dist, i, (dx, dy, dz)))

    moved = [item for item in deltas if item[0] > 1e-5]
    deltas.sort(reverse=True)
    print("run", run_dir.name)
    print("manifest attrs", attrs)
    print("frame_count", frame_count, "stride", stride, "floats_per", floats_per)
    print("motion_count", count, "index_count", index_count)
    print("moved_count", len(moved), "moved_ratio", len(moved) / max(count, 1))
    print("max_delta", deltas[0][0] if deltas else 0)
    print("top")
    for dist, compact_i, vec in deltas[:10]:
        print(compact_i, dist, vec)


if __name__ == "__main__":
    main()
