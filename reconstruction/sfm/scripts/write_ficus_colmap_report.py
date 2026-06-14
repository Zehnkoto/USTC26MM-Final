from __future__ import annotations

import csv
import json
from pathlib import Path


def md_table(rows: list[dict[str, str]]) -> str:
    cols = [
        "run_name", "image_set", "matcher", "num_input_images",
        "num_registered_images", "registration_ratio", "num_sparse_points",
        "mean_reprojection_error", "runtime_feature_extraction",
        "runtime_matching", "runtime_mapper", "num_models_generated",
        "whether_failed",
    ]
    lines = ["|" + "|".join(cols) + "|", "|" + "|".join(["---"] * len(cols)) + "|"]
    for row in rows:
        lines.append("|" + "|".join(str(row.get(c, "")) for c in cols) + "|")
    return "\n".join(lines)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Write a COLMAP generated-ficus report from summary files.")
    parser.add_argument("--out-dir", type=Path, default=Path("colmap_gen_ficus_runs"))
    args = parser.parse_args()
    out = args.out_dir

    with (out / "reports" / "colmap_sfm_summary.csv").open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    mvs_path = out / "reports" / "colmap_mvs_summary.json"
    mvs = json.loads(mvs_path.read_text(encoding="utf-8")) if mvs_path.exists() else []

    text = f"""# COLMAP Generated Ficus Multi-view Report

The input is a generated multi-view plant set: `0-11` are side orbit views and
`A/B/C` are high/top views. Because the images are generated, cross-view leaf
and texture consistency is weaker than in real camera captures.

## Matching Strategies

- side ring k=1/k=2/k=3;
- sparse top-view anchors;
- exhaustive matcher baseline;
- sequential matcher reference;
- optional LightGlue when supported by the installed COLMAP build.

## SfM Results

{md_table(rows)}

## MVS Results

"""
    for item in mvs:
        text += f"- `{item.get('run_name', '')}`: fused size {item.get('fused_ply_size', 0)} bytes\n"

    text += "\nGenerated databases, logs, dense workspaces, and PLY files are not committed.\n"
    report = out / "reports" / "colmap_generated_ficus_report.md"
    report.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
