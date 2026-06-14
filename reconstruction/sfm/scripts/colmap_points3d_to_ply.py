from __future__ import annotations

import argparse
import struct
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Point3D:
    xyz: tuple[float, float, float]
    rgb: tuple[int, int, int]
    error: float
    track_length: int


def read_points3d_bin(path: Path) -> list[Point3D]:
    points: list[Point3D] = []
    with path.open("rb") as f:
      num_points = struct.unpack("<Q", f.read(8))[0]
      header = struct.Struct("<QdddBBBdQ")
      track_item = struct.Struct("<ii")
      for _ in range(num_points):
          point_id, x, y, z, r, g, b, error, track_length = header.unpack(f.read(header.size))
          for _ in range(track_length):
              f.read(track_item.size)
          points.append(Point3D((x, y, z), (r, g, b), error, track_length))
    return points


def write_ascii_ply(path: Path, points: list[Point3D]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="ascii", newline="\n") as f:
        f.write("ply\n")
        f.write("format ascii 1.0\n")
        f.write(f"element vertex {len(points)}\n")
        f.write("property float x\n")
        f.write("property float y\n")
        f.write("property float z\n")
        f.write("property uchar red\n")
        f.write("property uchar green\n")
        f.write("property uchar blue\n")
        f.write("end_header\n")
        for point in points:
            x, y, z = point.xyz
            r, g, b = point.rgb
            f.write(f"{x:.8g} {y:.8g} {z:.8g} {r} {g} {b}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert COLMAP points3D.bin to an ASCII PLY point cloud.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    points = read_points3d_bin(args.input)
    write_ascii_ply(args.output, points)
    print(f"wrote {len(points)} points to {args.output}")


if __name__ == "__main__":
    main()
