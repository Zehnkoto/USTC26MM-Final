from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


def pair_id_to_image_ids(pair_id: int) -> tuple[int, int]:
    image_id2 = pair_id % 2147483647
    image_id1 = (pair_id - image_id2) // 2147483647
    return image_id1, image_id2


def rows_count(blob: bytes | None) -> int:
    if not blob:
        return 0
    return len(blob) // 8


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    con = sqlite3.connect(str(args.database))
    cur = con.cursor()
    images = {row[0]: row[1] for row in cur.execute("select image_id, name from images")}

    pairs = []
    for pair_id, rows, data in cur.execute("select pair_id, rows, data from two_view_geometries"):
        image_id1, image_id2 = pair_id_to_image_ids(pair_id)
        pairs.append(
            {
                "image1": images.get(image_id1, str(image_id1)),
                "image2": images.get(image_id2, str(image_id2)),
                "verified_rows": int(rows or 0),
                "blob_rows_estimate": rows_count(data),
            }
        )
    pairs.sort(key=lambda x: x["verified_rows"], reverse=True)

    summary = {
        "database": str(args.database),
        "num_images": len(images),
        "num_verified_pairs": len(pairs),
        "num_pairs_with_inliers": sum(1 for p in pairs if p["verified_rows"] > 0),
        "max_verified_rows": max([p["verified_rows"] for p in pairs], default=0),
        "pairs": pairs,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    con.close()


if __name__ == "__main__":
    main()
