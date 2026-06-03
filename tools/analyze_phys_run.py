import json
import math
import struct
import sys
from pathlib import Path


def contiguous_runs(values):
    if not values:
        return []
    runs = []
    start = prev = values[0]
    for value in values[1:]:
        if value == prev + 1:
            prev = value
        else:
            runs.append((start, prev, prev - start + 1))
            start = prev = value
    runs.append((start, prev, prev - start + 1))
    return runs


def read_binary_ply_positions(path):
    data = path.read_bytes()
    marker = b"end_header\n"
    header_end = data.index(marker) + len(marker)
    header = data[:header_end].decode("ascii", errors="replace")
    vertex_count = 0
    properties = []
    in_vertex = False
    for line in header.splitlines():
        parts = line.split()
        if parts[:2] == ["element", "vertex"]:
            vertex_count = int(parts[2])
            in_vertex = True
            continue
        if parts and parts[0] == "element" and parts[1] != "vertex":
            in_vertex = False
        if in_vertex and parts[:1] == ["property"]:
            properties.append((parts[1], parts[2]))

    fmt_map = {
        "float": ("f", 4),
        "float32": ("f", 4),
        "double": ("d", 8),
        "uchar": ("B", 1),
        "uint8": ("B", 1),
        "char": ("b", 1),
        "int": ("i", 4),
        "uint": ("I", 4),
    }
    fmt = "<"
    offsets = {}
    offset = 0
    for dtype, name in properties:
        code, size = fmt_map[dtype]
        offsets[name] = offset
        fmt += code
        offset += size
    stride = struct.calcsize(fmt)
    unpack = struct.Struct(fmt).unpack_from

    positions = []
    colors = []
    for i in range(vertex_count):
        row = unpack(data, header_end + i * stride)
        prop_index = {name: j for j, (_, name) in enumerate(properties)}
        positions.append((row[prop_index["x"]], row[prop_index["y"]], row[prop_index["z"]]))
        if {"f_dc_0", "f_dc_1", "f_dc_2"} <= set(prop_index):
            colors.append((row[prop_index["f_dc_0"]], row[prop_index["f_dc_1"]], row[prop_index["f_dc_2"]]))
    return positions, colors


def main():
    run = Path(sys.argv[1])
    payload = json.loads((run / "payload.json").read_text(encoding="utf-8"))
    manifest = json.loads((run / "physgaussian/super_motion/motion.physmotion.json").read_text(encoding="utf-8"))
    idx_path = run / "physgaussian/super_motion/indices.bin"
    idx_bytes = idx_path.read_bytes()
    indices = list(struct.unpack("<" + "I" * (len(idx_bytes) // 4), idx_bytes))
    idx_set = set(indices)

    print("model splats:", payload["source"]["numSplats"])
    print("motion active:", len(indices), "min:", min(indices), "max:", max(indices))
    print("motion first20:", indices[:20])
    print("motion last20:", indices[-20:])
    print("manifest:", manifest)
    runs = contiguous_runs(indices)
    print("motion contiguous runs:", len(runs), "largest:", sorted(runs, key=lambda item: item[2], reverse=True)[:8])

    for obj in payload["objects"]:
        values = obj.get("indices", [])
        obj_runs = contiguous_runs(values)
        print(
            "object",
            obj["objectId"],
            "body",
            obj.get("bodyId"),
            "count",
            len(values),
            "material",
            obj.get("material"),
            "fill",
            obj.get("fill"),
            "range",
            (min(values), max(values)) if values else None,
            "in_motion",
            sum(1 for value in values if value in idx_set),
            "runs",
            len(obj_runs),
            "largest",
            sorted(obj_runs, key=lambda item: item[2], reverse=True)[:5],
        )

    model_id = payload["modelId"]
    base_ply = Path("/root/autodl-tmp/ustc26mm/.phys_backend/models") / model_id / "model/point_cloud/iteration_0/point_cloud.ply"
    if not base_ply.exists():
        base_ply = Path("/root/autodl-tmp/ustc26mm/work/models") / model_id / "model/point_cloud/iteration_0/point_cloud.ply"
    if base_ply.exists():
        positions, colors = read_binary_ply_positions(base_ply)
        motion_bin = run / "physgaussian/super_motion/motion.bin"
        frame0 = struct.unpack("<" + "f" * (manifest["frameStrideBytes"] // 4), motion_bin.read_bytes()[: manifest["frameStrideBytes"]])
        diffs = []
        for compact_i, original_i in enumerate(indices[: min(len(indices), len(frame0) // 3)]):
            base = positions[original_i]
            pos = frame0[compact_i * 3 : compact_i * 3 + 3]
            diffs.append(math.dist(base, pos))
        if diffs:
            print("frame0-base diff max:", max(diffs), "mean:", sum(diffs) / len(diffs), "sample:", diffs[:10])
        for obj in payload["objects"][:4]:
            values = obj.get("indices", [])
            sample = values[: min(5, len(values))]
            print("object", obj["objectId"], "color sample", [(i, colors[i] if i < len(colors) else None) for i in sample])


if __name__ == "__main__":
    main()
