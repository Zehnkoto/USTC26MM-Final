from __future__ import annotations

import argparse
from pathlib import Path


SIDE_NAMES = [f"view_{i:03d}.png" for i in range(12)]
TOP_NAMES = ["view_A.png", "view_B.png", "view_C.png"]
ANCHORS = ["view_000.png", "view_003.png", "view_006.png", "view_009.png"]


def add_pair(pairs: set[tuple[str, str]], a: str, b: str) -> None:
    if a == b:
        return
    pairs.add(tuple(sorted((a, b))))


def side_ring(k: int) -> list[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for i, name in enumerate(SIDE_NAMES):
        for step in range(1, k + 1):
            add_pair(pairs, name, SIDE_NAMES[(i + step) % len(SIDE_NAMES)])
    return sorted(pairs)


def all_ring_top_sparse() -> list[tuple[str, str]]:
    pairs = set(side_ring(2))
    for i, a in enumerate(TOP_NAMES):
        for b in TOP_NAMES[i + 1 :]:
            add_pair(pairs, a, b)
        for anchor in ANCHORS:
            add_pair(pairs, a, anchor)
    return sorted(pairs)


def all_ring_top_sparse_k3() -> list[tuple[str, str]]:
    pairs = set(side_ring(3))
    for i, a in enumerate(TOP_NAMES):
        for b in TOP_NAMES[i + 1 :]:
            add_pair(pairs, a, b)
        for anchor in ANCHORS:
            add_pair(pairs, a, anchor)
    return sorted(pairs)


def write_pairs(path: Path, pairs: list[tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for a, b in pairs:
            f.write(f"{a} {b}\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()

    out_dir: Path = args.out_dir
    write_pairs(out_dir / "side_ring_k1.txt", side_ring(1))
    write_pairs(out_dir / "side_ring_k2.txt", side_ring(2))
    write_pairs(out_dir / "side_ring_k3.txt", side_ring(3))
    write_pairs(out_dir / "all_ring_top_sparse.txt", all_ring_top_sparse())
    write_pairs(out_dir / "all_ring_top_sparse_k3.txt", all_ring_top_sparse_k3())


if __name__ == "__main__":
    main()
