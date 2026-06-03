#!/usr/bin/env python3
"""Create a tiny preview motion package from a static 3DGS PLY.

This is only for UI/playback testing. It copies the source PLY as `base.ply`
and writes a sinusoidal position-only motion cache with the same Gaussian count.
"""

from __future__ import annotations

import argparse
import json
import shutil
import struct
from pathlib import Path

import numpy as np


def _parse_header(stream) -> tuple[list[str], int, str, int]:
    header_lines: list[str] = []
    vertex_count = -1
    fmt = ""
    while True:
        line = stream.readline()
        if not line:
            raise ValueError("PLY header ended unexpectedly")
        text = line.decode("ascii").strip()
        header_lines.append(text)
        if text.startswith("format "):
            fmt = text.split()[1]
        if text.startswith("element vertex "):
            vertex_count = int(text.split()[2])
        if text == "end_header":
            break
    if vertex_count < 0:
        raise ValueError("PLY has no element vertex count")
    if fmt not in {"ascii", "binary_little_endian"}:
        raise ValueError(f"Unsupported PLY format: {fmt}")
    return header_lines, vertex_count, fmt, stream.tell()


def _vertex_properties(header_lines) -> list[tuple[str, str]]:
    props: list[tuple[str, str]] = []
    in_vertex = False
    for line in header_lines:
        if line.startswith("element "):
            in_vertex = line.startswith("element vertex ")
            continue
        if in_vertex and line.startswith("property "):
            parts = line.split()
            if len(parts) == 3:
                props.append((parts[1], parts[2]))
    return props


def read_ply_xyz(path: Path) -> np.ndarray:
    with path.open("rb") as stream:
        header, vertex_count, fmt, data_start = _parse_header(stream)
        props = _vertex_properties(header)
        names = [name for _, name in props]
        x_id, y_id, z_id = names.index("x"), names.index("y"), names.index("z")

        if fmt == "ascii":
            points = np.zeros((vertex_count, 3), dtype=np.float32)
            for i in range(vertex_count):
                values = stream.readline().decode("ascii").split()
                points[i] = [float(values[x_id]), float(values[y_id]), float(values[z_id])]
            return points

        type_map = {
            "char": ("b", 1),
            "uchar": ("B", 1),
            "short": ("h", 2),
            "ushort": ("H", 2),
            "int": ("i", 4),
            "uint": ("I", 4),
            "float": ("f", 4),
            "double": ("d", 8),
        }
        row_format = "<" + "".join(type_map[prop_type][0] for prop_type, _ in props)
        row_size = struct.calcsize(row_format)
        stream.seek(data_start)
        raw = stream.read(row_size * vertex_count)
        points = np.zeros((vertex_count, 3), dtype=np.float32)
        for i in range(vertex_count):
            values = struct.unpack_from(row_format, raw, i * row_size)
            points[i] = [values[x_id], values[y_id], values[z_id]]
        return points


def make_preview_motion(source_ply: Path, output_dir: Path, frames: int, frame_rate: int, amplitude: float) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = "base.ply"
    shutil.copyfile(source_ply, output_dir / base_name)

    positions = read_ply_xyz(source_ply)
    center = positions.mean(axis=0, keepdims=True)
    rel = positions - center
    radius = np.linalg.norm(rel, axis=1, keepdims=True)
    radius = radius / max(float(radius.max()), 1e-6)

    motion_path = output_dir / "motion.bin"
    with motion_path.open("wb") as stream:
        for frame in range(frames):
            phase = frame / max(frames - 1, 1) * np.pi * 2
            offset = np.zeros_like(positions)
            offset[:, 1:2] = np.sin(phase + radius * np.pi) * amplitude
            offset[:, 0:1] = np.cos(phase * 0.75 + radius * np.pi) * amplitude * 0.35
            frame_positions = np.ascontiguousarray(positions + offset, dtype=np.float32)
            stream.write(frame_positions.tobytes(order="C"))

    manifest = {
        "format": "phys-motion-v1",
        "base": base_name,
        "binary": motion_path.name,
        "frameCount": frames,
        "frameRate": frame_rate,
        "numSplats": int(positions.shape[0]),
        "attributes": ["position"],
        "frameStrideBytes": int(positions.shape[0] * 3 * np.dtype(np.float32).itemsize),
        "updateBounds": True,
    }
    (output_dir / "motion.physmotion.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote preview package to {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ply", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--frames", type=int, default=90)
    parser.add_argument("--frame-rate", type=int, default=30)
    parser.add_argument("--amplitude", type=float, default=0.03)
    args = parser.parse_args()
    make_preview_motion(args.ply, args.output_dir, args.frames, args.frame_rate, args.amplitude)


if __name__ == "__main__":
    main()
