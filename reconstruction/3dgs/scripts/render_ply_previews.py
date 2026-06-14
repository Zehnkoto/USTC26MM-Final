from __future__ import annotations

import argparse
import math
import re
import struct
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


SH_C0 = 0.28209479177387814


@dataclass(frozen=True)
class PlyCloud:
    name: str
    positions: np.ndarray
    colors: np.ndarray | None
    color_source: str
    vertex_count: int
    path: Path


PLY_TYPES = {
    "char": ("b", 1),
    "int8": ("b", 1),
    "uchar": ("B", 1),
    "uint8": ("B", 1),
    "short": ("h", 2),
    "int16": ("h", 2),
    "ushort": ("H", 2),
    "uint16": ("H", 2),
    "int": ("i", 4),
    "int32": ("i", 4),
    "uint": ("I", 4),
    "uint32": ("I", 4),
    "float": ("f", 4),
    "float32": ("f", 4),
    "double": ("d", 8),
    "float64": ("d", 8),
}


def parse_header(path: Path) -> tuple[str, int, list[tuple[str, str]], int]:
    with path.open("rb") as f:
        first = f.readline().decode("ascii", errors="replace").strip()
        if first != "ply":
            raise ValueError(f"{path} is not a PLY file")
        fmt = ""
        vertex_count = 0
        properties: list[tuple[str, str]] = []
        in_vertex = False
        while True:
            line_bytes = f.readline()
            if not line_bytes:
                raise ValueError(f"{path} has no end_header")
            line = line_bytes.decode("ascii", errors="replace").strip()
            if line.startswith("format "):
                fmt = line.split()[1]
            elif line.startswith("element "):
                parts = line.split()
                in_vertex = parts[1] == "vertex"
                if in_vertex:
                    vertex_count = int(parts[2])
            elif in_vertex and line.startswith("property "):
                parts = line.split()
                if parts[1] == "list":
                    raise ValueError(f"{path} uses list vertex properties, unsupported for this quick preview")
                properties.append((parts[2], parts[1]))
            elif line == "end_header":
                return fmt, vertex_count, properties, f.tell()


def read_ply(path: Path) -> PlyCloud:
    fmt, vertex_count, properties, data_offset = parse_header(path)
    names = [name for name, _type in properties]

    if vertex_count == 0:
        return PlyCloud(path.stem, np.empty((0, 3), dtype=np.float32), None, "empty", 0, path)

    if not {"x", "y", "z"}.issubset(names):
        raise ValueError(f"{path} has no x/y/z vertex properties")

    values: dict[str, np.ndarray] = {}

    if fmt == "ascii":
        data = np.loadtxt(path, skiprows=count_header_lines(path), max_rows=vertex_count)
        if data.ndim == 1:
            data = data.reshape(1, -1)
        for i, name in enumerate(names):
            values[name] = data[:, i]
    elif fmt == "binary_little_endian":
        dtype_fields = []
        struct_fmt = "<"
        for name, typ in properties:
            if typ not in PLY_TYPES:
                raise ValueError(f"unsupported PLY property type {typ} in {path}")
            code, _size = PLY_TYPES[typ]
            dtype_fields.append((name, np_dtype(typ)))
            struct_fmt += code
        record = struct.Struct(struct_fmt)
        arrays = {name: [] for name in names}
        with path.open("rb") as f:
            f.seek(data_offset)
            for _ in range(vertex_count):
                chunk = f.read(record.size)
                if len(chunk) != record.size:
                    break
                row = record.unpack(chunk)
                for name, value in zip(names, row):
                    arrays[name].append(value)
        for name, vals in arrays.items():
            values[name] = np.asarray(vals)
    else:
        raise ValueError(f"unsupported PLY format {fmt} in {path}")

    positions = np.stack([values["x"], values["y"], values["z"]], axis=1).astype(np.float32)
    colors, source = infer_colors(values)
    return PlyCloud(path.stem, positions, colors, source, len(positions), path)


def count_header_lines(path: Path) -> int:
    count = 0
    with path.open("rb") as f:
        for line in f:
            count += 1
            if line.decode("ascii", errors="replace").strip() == "end_header":
                return count
    raise ValueError(f"{path} has no end_header")


def np_dtype(typ: str) -> str:
    if typ in {"float", "float32"}:
        return "<f4"
    if typ in {"double", "float64"}:
        return "<f8"
    if typ in {"uchar", "uint8"}:
        return "u1"
    if typ in {"char", "int8"}:
        return "i1"
    if typ in {"ushort", "uint16"}:
        return "<u2"
    if typ in {"short", "int16"}:
        return "<i2"
    if typ in {"uint", "uint32"}:
        return "<u4"
    if typ in {"int", "int32"}:
        return "<i4"
    raise ValueError(typ)


def infer_colors(values: dict[str, np.ndarray]) -> tuple[np.ndarray | None, str]:
    if {"red", "green", "blue"}.issubset(values):
        colors = np.stack([values["red"], values["green"], values["blue"]], axis=1).astype(np.float32)
        if colors.max(initial=0) > 1.0:
            colors /= 255.0
        return np.clip(colors, 0, 1), "rgb"
    if {"f_dc_0", "f_dc_1", "f_dc_2"}.issubset(values):
        colors = np.stack([values["f_dc_0"], values["f_dc_1"], values["f_dc_2"]], axis=1).astype(np.float32)
        colors = colors * SH_C0 + 0.5
        return np.clip(colors, 0, 1), "sh_dc"
    return None, "height"


def height_colors(z: np.ndarray) -> np.ndarray:
    if len(z) == 0:
        return np.empty((0, 3), dtype=np.float32)
    zmin, zmax = float(np.min(z)), float(np.max(z))
    t = (z - zmin) / max(zmax - zmin, 1e-6)
    low = np.array([0.10, 0.35, 0.85], dtype=np.float32)
    mid = np.array([0.10, 0.70, 0.48], dtype=np.float32)
    high = np.array([0.95, 0.78, 0.20], dtype=np.float32)
    colors = np.where(
        (t[:, None] < 0.5),
        low + (mid - low) * (t[:, None] * 2.0),
        mid + (high - mid) * ((t[:, None] - 0.5) * 2.0),
    )
    return colors


def render_cloud(cloud: PlyCloud, out_path: Path, width: int = 1200, height: int = 900) -> None:
    bg = np.array([247, 249, 252], dtype=np.uint8)
    image = np.zeros((height, width, 3), dtype=np.uint8)
    image[:, :] = bg

    if cloud.vertex_count == 0:
        img = Image.fromarray(image)
        draw = ImageDraw.Draw(img)
        font = load_font(30)
        draw.text((40, 40), cloud.name, fill=(32, 40, 52), font=font)
        draw.text((40, 92), "empty point cloud", fill=(145, 57, 57), font=load_font(22))
        img.save(out_path)
        return

    pts = cloud.positions.astype(np.float32)
    finite = np.isfinite(pts).all(axis=1)
    pts = pts[finite]
    colors = cloud.colors[finite] if cloud.colors is not None else height_colors(pts[:, 2])
    if len(pts) == 0:
        render_cloud(PlyCloud(cloud.name, pts, None, "empty", 0, cloud.path), out_path, width, height)
        return

    max_points = 220_000
    if len(pts) > max_points:
        rng = np.random.default_rng(7)
        idx = rng.choice(len(pts), size=max_points, replace=False)
        pts = pts[idx]
        colors = colors[idx]

    center = (pts.min(axis=0) + pts.max(axis=0)) * 0.5
    span = float(np.max(pts.max(axis=0) - pts.min(axis=0)))
    span = max(span, 1e-6)
    pts = (pts - center) / span

    yaw = math.radians(-38)
    pitch = math.radians(24)
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    x = cy * pts[:, 0] - sy * pts[:, 1]
    y = sy * pts[:, 0] + cy * pts[:, 1]
    z = pts[:, 2]
    yp = cp * y - sp * z
    depth = sp * y + cp * z

    margin = 0.13
    scale = (1.0 - 2.0 * margin) * min(width, height)
    sx = (width * 0.5 + x * scale).astype(np.int32)
    sy_img = (height * 0.53 - yp * scale).astype(np.int32)
    keep = (sx >= 0) & (sx < width) & (sy_img >= 0) & (sy_img < height)
    sx, sy_img, depth, colors = sx[keep], sy_img[keep], depth[keep], colors[keep]
    order = np.argsort(depth)
    sx, sy_img, colors = sx[order], sy_img[order], colors[order]
    rgb = (np.clip(colors, 0, 1) * 255).astype(np.uint8)

    radius = 3 if cloud.vertex_count < 1_000 else 2 if cloud.vertex_count < 20_000 else 1
    offsets = [(0, 0)]
    if radius >= 2:
        offsets += [(-1, 0), (1, 0), (0, -1), (0, 1)]
    if radius >= 3:
        offsets += [(-1, -1), (-1, 1), (1, -1), (1, 1), (-2, 0), (2, 0), (0, -2), (0, 2)]
    for dx, dy in offsets:
        xx = sx + dx
        yy = sy_img + dy
        ok = (xx >= 0) & (xx < width) & (yy >= 0) & (yy < height)
        image[yy[ok], xx[ok]] = rgb[ok]

    img = Image.fromarray(image)
    draw = ImageDraw.Draw(img)
    label = f"{cloud.name}  |  {cloud.vertex_count:,} pts  |  color={cloud.color_source}"
    draw.rectangle((24, 22, width - 24, 76), fill=(247, 249, 252), outline=(214, 220, 230))
    draw.text((42, 38), label, fill=(28, 35, 48), font=load_font(22))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)


def load_font(size: int) -> ImageFont.ImageFont:
    for name in ("arial.ttf", "C:/Windows/Fonts/arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("_")


def make_contact_sheet(items: list[tuple[str, Path]], output: Path, thumb_w: int = 420, thumb_h: int = 330) -> None:
    cols = 3
    rows = math.ceil(len(items) / cols)
    sheet = Image.new("RGB", (cols * thumb_w, rows * thumb_h), (238, 242, 247))
    font = load_font(18)
    for i, (label, path) in enumerate(items):
        img = Image.open(path).convert("RGB")
        img.thumbnail((thumb_w - 24, thumb_h - 58))
        x = (i % cols) * thumb_w
        y = (i // cols) * thumb_h
        sheet.paste(img, (x + (thumb_w - img.width) // 2, y + 12))
        draw = ImageDraw.Draw(sheet)
        draw.text((x + 16, y + thumb_h - 36), label[:42], fill=(31, 40, 55), font=font)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)


def default_ply_paths() -> list[Path]:
    base = Path(r"C:\MM_final_hw\plant_sfm_roma_3dgs_extended_20260615_042246\downloads\ply")
    paths = [
        Path(r"C:\MM_final_hw\colmap_official_ficus_train100_exhaustive\official_ficus_train100_exhaustive_best_sfm_sparse_points3D.ply"),
        Path(r"C:\MM_final_hw\colmap_official_ficus_train100\official_ficus_train100_sfm_sparse_points3D.ply"),
    ]
    paths.extend(sorted(base.glob("*.ply")))
    seen = set()
    unique = []
    for path in paths:
        key = str(path).lower()
        if path.exists() and key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def main() -> None:
    parser = argparse.ArgumentParser(description="Render local PLY files to PNG point-cloud previews.")
    parser.add_argument("--out", type=Path, default=Path(r"C:\MM_final_hw\ply_model_previews"))
    parser.add_argument("--ply", type=Path, action="append", default=[])
    args = parser.parse_args()

    paths = args.ply or default_ply_paths()
    args.out.mkdir(parents=True, exist_ok=True)
    rendered: list[tuple[str, Path]] = []
    failures: list[str] = []
    for path in paths:
        try:
            cloud = read_ply(path)
            out_path = args.out / f"{safe_name(path.stem)}.png"
            render_cloud(cloud, out_path)
            rendered.append((path.stem, out_path))
            print(f"rendered {path.name}: {cloud.vertex_count} points -> {out_path}")
        except Exception as exc:
            failures.append(f"{path}: {exc}")
            print(f"FAILED {path}: {exc}")
    if rendered:
        make_contact_sheet(rendered, args.out / "contact_sheet.png")
        print(f"contact sheet -> {args.out / 'contact_sheet.png'}")
    if failures:
        (args.out / "failures.txt").write_text("\n".join(failures), encoding="utf-8")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
