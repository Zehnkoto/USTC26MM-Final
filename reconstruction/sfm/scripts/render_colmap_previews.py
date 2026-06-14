from __future__ import annotations

from pathlib import Path
import struct

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


OUT = Path(r"C:\MM_final_hw\colmap_gen_ficus_runs")


def read_points3d(path: Path) -> np.ndarray:
    pts = []
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 4:
                pts.append([float(parts[1]), float(parts[2]), float(parts[3])])
    return np.asarray(pts, dtype=float)


def read_ply_vertices(path: Path) -> np.ndarray:
    with path.open("rb") as f:
        header = []
        vertex_count = 0
        binary_little_endian = False
        while True:
            line = f.readline().decode("ascii", errors="replace").strip()
            header.append(line)
            if line == "format binary_little_endian 1.0":
                binary_little_endian = True
            if line.startswith("element vertex"):
                vertex_count = int(line.split()[-1])
            if line == "end_header":
                break
        if binary_little_endian:
            data = []
            # COLMAP PLY vertices are x y z nx ny nz red green blue.
            record = struct.Struct("<ffffffBBB")
            for _ in range(vertex_count):
                chunk = f.read(record.size)
                if len(chunk) != record.size:
                    break
                vals = record.unpack(chunk)
                data.append([vals[0], vals[1], vals[2]])
            return np.asarray(data, dtype=float)
        data = []
        for _ in range(vertex_count):
            line = f.readline().decode("ascii", errors="replace").strip()
            if not line:
                continue
            parts = line.split()
            data.append([float(parts[0]), float(parts[1]), float(parts[2])])
    return np.asarray(data, dtype=float)


def render(points: np.ndarray, title: str, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(7, 6), dpi=160)
    ax = fig.add_subplot(111, projection="3d")
    if len(points) > 0:
        if len(points) > 20000:
            rng = np.random.default_rng(0)
            points = points[rng.choice(len(points), 20000, replace=False)]
        ax.scatter(points[:, 0], points[:, 1], points[:, 2], s=1.5, c=points[:, 2], cmap="viridis")
        center = points.mean(axis=0)
        span = max(np.ptp(points[:, 0]), np.ptp(points[:, 1]), np.ptp(points[:, 2]), 1e-6)
        for setter, c in zip([ax.set_xlim, ax.set_ylim, ax.set_zlim], center):
            setter(c - span / 2, c + span / 2)
    ax.set_title(title)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")
    ax.view_init(elev=22, azim=-58)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def main() -> None:
    screenshots = OUT / "reports" / "screenshots"
    tasks = [
        (
            read_points3d,
            OUT / "runs" / "side_ring_k3_relaxed" / "sparse_txt" / "points3D.txt",
            "side_ring_k3_relaxed sparse",
            screenshots / "side_ring_k3_sparse.png",
        ),
        (
            read_points3d,
            OUT / "runs" / "all_ring_top_k3_relaxed" / "sparse_txt" / "points3D.txt",
            "all_ring_top_k3_relaxed sparse",
            screenshots / "all_ring_top_sparse_sparse.png",
        ),
        (
            read_ply_vertices,
            OUT / "runs" / "all_ring_top_k3_relaxed" / "dense" / "fused.ply",
            "all_ring_top_k3_relaxed fused",
            screenshots / "best_dense_fused.png",
        ),
    ]
    for reader, src, title, dst in tasks:
        if src.exists():
            pts = reader(src)
            render(pts, title, dst)


if __name__ == "__main__":
    main()
