from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path


SIDE_IDS = [str(i) for i in range(12)]
TOP_IDS = ["A", "B", "C"]
ALL_IDS = SIDE_IDS + TOP_IDS
IMAGE_EXTS = [".png", ".jpg", ".jpeg", ".JPG", ".JPEG", ".PNG"]


@dataclass
class RunConfig:
    name: str
    image_set: str
    matcher: str
    pairs_file: str | None = None
    lightglue: bool = False


RUNS = [
    RunConfig("side_ring_k1", "side", "matches_importer", "side_ring_k1.txt"),
    RunConfig("side_ring_k2", "side", "matches_importer", "side_ring_k2.txt"),
    RunConfig("all_ring_top_sparse", "all", "matches_importer", "all_ring_top_sparse.txt"),
    RunConfig("all_exhaustive", "all", "exhaustive_matcher"),
    RunConfig("all_sequential", "all", "sequential_matcher"),
    RunConfig("all_ring_top_sparse_lightglue", "all", "matches_importer", "all_ring_top_sparse.txt", True),
]


def resolve_colmap(value: str) -> str:
    path = Path(value)
    if path.is_absolute() or len(path.parts) > 1:
        if not path.exists():
            raise FileNotFoundError(path)
        return str(path)
    resolved = shutil.which(value)
    if not resolved:
        raise FileNotFoundError(f"Cannot find COLMAP executable '{value}'. Set --colmap or add it to PATH.")
    return resolved


def run_command(cmd: list[str], log_path: Path, cwd: Path | None = None) -> tuple[int, float]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    with log_path.open("w", encoding="utf-8", errors="replace") as log:
        log.write("$ " + " ".join(cmd) + "\n\n")
        log.flush()
        proc = subprocess.run(cmd, cwd=cwd, stdout=log, stderr=subprocess.STDOUT)
    return proc.returncode, time.perf_counter() - start


def find_image(src: Path, stem: str) -> Path:
    for ext in IMAGE_EXTS:
        path = src / f"{stem}{ext}"
        if path.exists():
            return path
    raise FileNotFoundError(f"missing image for {stem} in {src}")


def copy_images(src: Path, out: Path) -> dict[str, dict[str, str]]:
    out.mkdir(parents=True, exist_ok=True)
    for sub in ["images_all", "images_side", "pairs", "runs", "logs", "reports"]:
        (out / sub).mkdir(parents=True, exist_ok=True)

    mapping: dict[str, dict[str, str]] = {}
    for stem in ALL_IDS:
        source = find_image(src, stem)
        if stem.isdigit():
            new_name = f"view_{int(stem):03d}{source.suffix.lower()}"
            shutil.copy2(source, out / "images_side" / new_name)
        else:
            new_name = f"view_{stem}{source.suffix.lower()}"
        shutil.copy2(source, out / "images_all" / new_name)
        mapping[stem] = {
            "source_name": source.name,
            "images_all": str(out / "images_all" / new_name),
            "images_side": str(out / "images_side" / new_name) if stem.isdigit() else "",
        }

    (out / "name_mapping.json").write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
    return mapping


def generate_pairs(out: Path) -> None:
    import sys

    script = Path(__file__).with_name("generate_ficus_pairs.py")
    subprocess.run([sys.executable, str(script), "--out-dir", str(out / "pairs")], check=True)


def prepare_run(out: Path, config: RunConfig) -> Path:
    run_dir = out / "runs" / config.name
    if run_dir.exists():
        shutil.rmtree(run_dir)
    (run_dir / "logs").mkdir(parents=True)
    (run_dir / "sparse").mkdir()
    (run_dir / "dense").mkdir()

    image_src = out / ("images_side" if config.image_set == "side" else "images_all")
    shutil.copytree(image_src, run_dir / "images")
    if config.pairs_file:
        shutil.copy2(out / "pairs" / config.pairs_file, run_dir / "pairs.txt")
    return run_dir


def option_supported(colmap: str, command: str, option_name: str) -> bool:
    proc = subprocess.run(
        [colmap, command, "-h"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return option_name in proc.stdout


def run_feature(colmap: str, run_dir: Path) -> tuple[int, float, str]:
    base = [
        colmap,
        "feature_extractor",
        "--database_path",
        str(run_dir / "database.db"),
        "--image_path",
        str(run_dir / "images"),
        "--ImageReader.single_camera",
        "1",
        "--FeatureExtraction.use_gpu",
        "1",
        "--FeatureExtraction.gpu_index",
        "0",
        "--FeatureExtraction.max_image_size",
        "1600",
        "--SiftExtraction.max_num_features",
        "4096",
    ]
    code, dur = run_command(base, run_dir / "logs" / "01_feature_extractor.log")
    if code == 0:
        return code, dur, "gpu"
    cpu = base.copy()
    cpu[cpu.index("--FeatureExtraction.use_gpu") + 1] = "0"
    code, cpu_dur = run_command(cpu, run_dir / "logs" / "01_feature_extractor_cpu.log")
    return code, dur + cpu_dur, "cpu_fallback"


def run_match(colmap: str, config: RunConfig, run_dir: Path) -> tuple[int, float, str]:
    common = [
        "--FeatureMatching.use_gpu",
        "1",
        "--FeatureMatching.gpu_index",
        "0",
        "--FeatureMatching.guided_matching",
        "0",
        "--FeatureMatching.max_num_matches",
        "8192",
    ]
    if config.lightglue:
        common = ["--FeatureMatching.type", "SIFT_LIGHTGLUE", *common]

    if config.matcher == "matches_importer":
        cmd = [
            colmap,
            "matches_importer",
            "--database_path",
            str(run_dir / "database.db"),
            "--match_list_path",
            str(run_dir / "pairs.txt"),
            "--match_type",
            "pairs",
            *common,
        ]
        log = "02_matches_importer_lightglue.log" if config.lightglue else "02_matches_importer.log"
    elif config.matcher == "exhaustive_matcher":
        cmd = [colmap, "exhaustive_matcher", "--database_path", str(run_dir / "database.db"), *common]
        log = "02_exhaustive_matcher.log"
    elif config.matcher == "sequential_matcher":
        cmd = [
            colmap,
            "sequential_matcher",
            "--database_path",
            str(run_dir / "database.db"),
            "--SequentialMatching.overlap",
            "2",
            "--SequentialMatching.loop_detection",
            "1",
            *common,
        ]
        log = "02_sequential_matcher.log"
    else:
        raise ValueError(config.matcher)
    code, dur = run_command(cmd, run_dir / "logs" / log)
    return code, dur, log


def run_mapper(colmap: str, run_dir: Path) -> tuple[int, float]:
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
        ],
        run_dir / "logs" / "03_mapper.log",
    )


def parse_analyzer(text: str) -> dict[str, float]:
    patterns = {
        "registered_images": r"Registered images:\s+(\d+)",
        "points": r"Points:\s+(\d+)",
        "observations": r"Observations:\s+(\d+)",
        "mean_track_length": r"Mean track length:\s+([0-9.]+)",
        "mean_observations_per_image": r"Mean observations per image:\s+([0-9.]+)",
        "mean_reprojection_error": r"Mean reprojection error:\s+([0-9.]+)px",
    }
    metrics: dict[str, float] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            value = float(match.group(1))
            metrics[key] = int(value) if value.is_integer() else value
    return metrics


def analyze_models(colmap: str, run_dir: Path) -> tuple[Path | None, dict[str, float], int]:
    sparse = run_dir / "sparse"
    models = [p for p in sparse.iterdir() if p.is_dir()] if sparse.exists() else []
    best: Path | None = None
    best_metrics: dict[str, float] = {}
    for model in models:
        log_path = run_dir / "logs" / f"04_model_analyzer_{model.name}.log"
        code, _ = run_command([colmap, "model_analyzer", "--path", str(model)], log_path)
        if code != 0:
            continue
        metrics = parse_analyzer(log_path.read_text(encoding="utf-8", errors="replace"))
        if best is None or metrics.get("registered_images", 0) > best_metrics.get("registered_images", 0):
            best = model
            best_metrics = metrics
    if best is not None:
        shutil.copy2(run_dir / "logs" / f"04_model_analyzer_{best.name}.log", run_dir / "logs" / "04_model_analyzer.log")
    return best, best_metrics, len(models)


def export_txt(colmap: str, run_dir: Path, best_model: Path) -> int:
    out = run_dir / "sparse_txt"
    out.mkdir(exist_ok=True)
    code, _ = run_command(
        [colmap, "model_converter", "--input_path", str(best_model), "--output_path", str(out), "--output_type", "TXT"],
        run_dir / "logs" / "08_model_converter_txt.log",
    )
    return code


def image_count(run_dir: Path) -> int:
    return len([p for p in (run_dir / "images").iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg"}])


def save_summary(out: Path, rows: list[dict[str, object]]) -> None:
    reports = out / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "colmap_sfm_summary.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    fieldnames = sorted({key for row in rows for key in row})
    with (reports / "colmap_sfm_summary.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run COLMAP matching-graph experiments for generated ficus views.")
    parser.add_argument("--image-dir", type=Path, default=Path("data"), help="Directory containing images named 0..11,A,B,C.")
    parser.add_argument("--out-dir", type=Path, default=Path("colmap_gen_ficus_runs"))
    parser.add_argument("--colmap", default="colmap", help="COLMAP executable path or command name.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    colmap = resolve_colmap(args.colmap)
    copy_images(args.image_dir, args.out_dir)
    generate_pairs(args.out_dir)

    env_log = args.out_dir / "logs" / "00_environment.log"
    with env_log.open("w", encoding="utf-8", errors="replace") as f:
        for cmd in ([colmap, "-h"], ["nvidia-smi"]):
            f.write("$ " + " ".join(cmd) + "\n")
            try:
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
                f.write(proc.stdout + "\n")
            except Exception as exc:
                f.write(f"{type(exc).__name__}: {exc}\n")

    supports_lightglue = option_supported(colmap, "matches_importer", "SIFT_LIGHTGLUE")
    rows: list[dict[str, object]] = []

    for config in RUNS:
        run_dir = prepare_run(args.out_dir, config)
        row: dict[str, object] = {
            **asdict(config),
            "run_name": config.name,
            "run_dir": str(run_dir),
            "num_input_images": image_count(run_dir),
            "whether_failed": False,
            "failure_reason": "",
        }
        if config.lightglue and not supports_lightglue:
            row.update({"whether_failed": True, "failure_reason": "SIFT_LIGHTGLUE option not supported"})
            rows.append(row)
            save_summary(args.out_dir, rows)
            continue

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

        code, mapper_time = run_mapper(colmap, run_dir)
        row["runtime_mapper"] = round(mapper_time, 3)
        if code != 0:
            row.update({"whether_failed": True, "failure_reason": "mapper failed"})
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
