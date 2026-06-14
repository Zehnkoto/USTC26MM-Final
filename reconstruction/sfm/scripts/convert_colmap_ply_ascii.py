from __future__ import annotations

import argparse
import struct
from pathlib import Path


def read_binary_colmap_ply(path: Path):
    with path.open("rb") as f:
        vertex_count = 0
        while True:
            line = f.readline().decode("ascii", errors="replace").strip()
            if line.startswith("element vertex"):
                vertex_count = int(line.split()[-1])
            if line == "end_header":
                break
        record = struct.Struct("<ffffffBBB")
        vertices = []
        for _ in range(vertex_count):
            chunk = f.read(record.size)
            if len(chunk) != record.size:
                break
            vertices.append(record.unpack(chunk))
    return vertices


def write_ascii_ply(path: Path, vertices) -> None:
    with path.open("w", encoding="ascii", newline="\n") as f:
        f.write("ply\n")
        f.write("format ascii 1.0\n")
        f.write(f"element vertex {len(vertices)}\n")
        for prop in ["x", "y", "z", "nx", "ny", "nz"]:
            f.write(f"property float {prop}\n")
        for prop in ["red", "green", "blue"]:
            f.write(f"property uchar {prop}\n")
        f.write("end_header\n")
        for x, y, z, nx, ny, nz, r, g, b in vertices:
            f.write(f"{x:.8g} {y:.8g} {z:.8g} {nx:.8g} {ny:.8g} {nz:.8g} {r} {g} {b}\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    vertices = read_binary_colmap_ply(args.input)
    write_ascii_ply(args.output, vertices)


if __name__ == "__main__":
    main()
