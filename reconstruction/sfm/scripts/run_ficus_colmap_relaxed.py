from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from run_ficus_colmap_experiments import (
    RunConfig,
    analyze_models,
    export_txt,
    generate_pairs,
    image_count,
    prepare_run,
    resolve_colmap,
    run_command,
    run_feature,
    run_match,
    save_summary,
)


RELAXED_RUNS = [
    RunConfig("side_ring_k2_relaxed", "side", "matches_importer", "side_ring_k2.txt"),
    RunConfig("side_ring_k3_relaxed", "side", "matches_importer", "side_ring_k3.txt"),
    RunConfig("all_ring_top_sparse_relaxed", "all", "matches_importer", "all_ring_top_sparse.txt"),
    RunConfig("all_ring_top_k3_relaxed", "all", "matches_importer", "all_ring_top_sparse_k3.txt"),
    RunConfig("all_exhaustive_relaxed", "all", "exhaustive_matcher"),
]


RELAXED_MAPPER_ARGS = [
    "--Mapper.min_num_matches",
    "8",
    "--Mapper.init_min_num_inliers",
    "20",
    "--Mapper.init_min_tri_angle",
    "2",
    "--Mapper.abs_pose_min_num_inliers",
    "8",
    "--Mapper.abs_pose_min_inlier_ratio",
    "0.05",
    "--Mapper.tri_ignore_two_view_tracks",
    "0",
    "--Mapper.multiple_models",
    "1",
    "--Mapper.min_model_size",
    "2",
    "--Mapper.ba_refine_focal_length",
    "1",
    "--Mapper.ba_refine_extra_params",
    "1",
]


def run_mapper_relaxed(colmap: str, run_dir: Path) -> tuple[int, float]:
    return run_command(
        [
            colmap,
            "mapper",
            "--database_path",
            str(run_dir / "database.db"),
            "--image_path",
            str(run_dir / "images"),
            "--output_path",
            str(run_dir / "sparse"),
            *RELAXED_MAPPER_ARGS,
        ],
        run_dir / "logs" / "03_mapper_relaxed.log",
    )


def load_existing_rows(out_dir: Path) -> list[dict[str, object]]:
    path = out_dir / "reports" / "colmap_sfm_summary.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run relaxed COLMAP mapper profiles for generated ficus views.")
    parser.add_argument("--out-dir", type=Path, default=Path("colmap_gen_ficus_runs"))
    parser.add_argument("--colmap", default="colmap", help="COLMAP executable path or command name.")
    args = parser.parse_args()
    colmap = resolve_colmap(args.colmap)

    generate_pairs(args.out_dir)
    rows = [row for row in load_existing_rows(args.out_dir) if not str(row.get("run_name", "")).endswith("_relaxed")]

    for config in RELAXED_RUNS:
        run_dir = prepare_run(args.out_dir, config)
        row: dict[str, object] = {
            **asdict(config),
            "run_name": config.name,
            "run_dir": str(run_dir),
            "num_input_images": image_count(run_dir),
            "mapper_profile": "relaxed_generated_views",
            "mapper_args": " ".join(RELAXED_MAPPER_ARGS),
            "whether_failed": False,
            "failure_reason": "",
        }

        code, feat_time, feat_mode = run_feature(colmap, run_dir)
        row["runtime_feature_extraction"] = round(feat_time, 3)
        row["feature_mode"] = feat_mode
        if code != 0:
            row.update({"whether_failed": True, "failure_reason": "feature_extractor failed"})
            rows.append(row)
            save_summary(args.out_dir, rows)
            continue

        code, match_time, match_log = run_match(colmap, config, run_dir)
        row["runtime_matching"] = round(match_time, 3)
        row["matching_log"] = match_log
        if code != 0:
            row.update({"whether_failed": True, "failure_reason": f"{config.matcher} failed"})
            rows.append(row)
            save_summary(args.out_dir, rows)
            continue

        code, mapper_time = run_mapper_relaxed(colmap, run_dir)
        row["runtime_mapper"] = round(mapper_time, 3)
        if code != 0:
            row.update({"whether_failed": True, "failure_reason": "relaxed mapper failed"})
            rows.append(row)
            save_summary(args.out_dir, rows)
            continue

        best_model, metrics, num_models = analyze_models(colmap, run_dir)
        row["num_models_generated"] = num_models
        if best_model is None:
            row.update({"whether_failed": True, "failure_reason": "no analyzable sparse model"})
            rows.append(row)
            save_summary(args.out_dir, rows)
            continue

        export_txt(colmap, run_dir, best_model)
        registered = int(metrics.get("registered_images", 0))
        row.update(
            {
                "best_model_path": str(best_model),
                "num_registered_images": registered,
                "registration_ratio": round(registered / int(row["num_input_images"]), 4),
                "num_sparse_points": metrics.get("points", 0),
                "num_observations": metrics.get("observations", 0),
                "mean_track_length": metrics.get("mean_track_length", 0),
                "mean_observations_per_image": metrics.get("mean_observations_per_image", 0),
                "mean_reprojection_error": metrics.get("mean_reprojection_error", 0),
            }
        )
        (run_dir / "summary.json").write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
        rows.append(row)
        save_summary(args.out_dir, rows)


if __name__ == "__main__":
    main()
