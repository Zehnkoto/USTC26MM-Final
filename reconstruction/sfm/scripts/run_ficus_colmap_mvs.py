from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from run_ficus_colmap_experiments import resolve_colmap, run_command


DEFAULT_CANDIDATES = ["all_ring_top_k3_relaxed", "side_ring_k3_relaxed"]


def run_mvs(colmap: str, out_dir: Path, run_name: str) -> dict[str, object]:
    run_dir = out_dir / "runs" / run_name
    summary_path = run_dir / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    best_model = Path(summary["best_model_path"])
    dense = run_dir / "dense"
    if dense.exists():
        shutil.rmtree(dense)
    dense.mkdir(parents=True)

    result: dict[str, object] = {
        "run_name": run_name,
        "best_model_path": str(best_model),
        "dense_dir": str(dense),
        "mvs_selected_reason": "best sparse candidates only",
    }

    code, dur = run_command(
        [
            colmap,
            "image_undistorter",
            "--image_path",
            str(run_dir / "images"),
            "--input_path",
            str(best_model),
            "--output_path",
            str(dense),
            "--output_type",
            "COLMAP",
            "--max_image_size",
            "1600",
        ],
        run_dir / "logs" / "05_image_undistorter.log",
    )
    result["runtime_image_undistorter"] = round(dur, 3)
    result["image_undistorter_status"] = code
    if code != 0:
        result["mvs_failed"] = True
        result["failure_reason"] = "image_undistorter failed"
        return result

    code, dur = run_command(
        [
            colmap,
            "patch_match_stereo",
            "--workspace_path",
            str(dense),
            "--workspace_format",
            "COLMAP",
            "--PatchMatchStereo.geom_consistency",
            "1",
            "--PatchMatchStereo.max_image_size",
            "1200",
            "--PatchMatchStereo.gpu_index",
            "0",
            "--PatchMatchStereo.cache_size",
            "8",
        ],
        run_dir / "logs" / "06_patch_match_stereo.log",
    )
    result["runtime_patch_match_stereo"] = round(dur, 3)
    result["patch_match_stereo_status"] = code
    if code != 0:
        result["mvs_failed"] = True
        result["failure_reason"] = "patch_match_stereo failed"
        return result

    code, dur = run_command(
        [
            colmap,
            "stereo_fusion",
            "--workspace_path",
            str(dense),
            "--workspace_format",
            "COLMAP",
            "--input_type",
            "geometric",
            "--output_path",
            str(dense / "fused.ply"),
            "--StereoFusion.cache_size",
            "8",
            "--StereoFusion.use_cache",
            "1",
        ],
        run_dir / "logs" / "07_stereo_fusion.log",
    )
    result["runtime_stereo_fusion"] = round(dur, 3)
    result["stereo_fusion_status"] = code
    result["fused_ply"] = str(dense / "fused.ply")
    result["fused_ply_exists"] = (dense / "fused.ply").exists()
    result["fused_ply_size"] = (dense / "fused.ply").stat().st_size if (dense / "fused.ply").exists() else 0
    result["mvs_failed"] = not result["fused_ply_size"]
    if result["mvs_failed"]:
        result["failure_reason"] = "stereo_fusion did not produce a non-empty ply"
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run MVS for selected generated-ficus COLMAP sparse models.")
    parser.add_argument("--out-dir", type=Path, default=Path("colmap_gen_ficus_runs"))
    parser.add_argument("--colmap", default="colmap", help="COLMAP executable path or command name.")
    parser.add_argument("--run", action="append", dest="runs", help="Run name to process; repeatable.")
    args = parser.parse_args()
    colmap = resolve_colmap(args.colmap)
    runs = args.runs or DEFAULT_CANDIDATES

    results = []
    for run_name in runs:
        result = run_mvs(colmap, args.out_dir, run_name)
        results.append(result)
        (args.out_dir / "reports").mkdir(parents=True, exist_ok=True)
        (args.out_dir / "reports" / "colmap_mvs_summary.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
