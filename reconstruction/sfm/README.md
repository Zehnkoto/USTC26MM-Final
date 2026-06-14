# SfM / COLMAP Tools

This folder contains project-owned scripts for generated ficus multi-view COLMAP
experiments.

## Scripts

- `generate_ficus_pairs.py`: builds ring and sparse top-view matching graphs.
- `run_ficus_colmap_experiments.py`: runs feature extraction, matching, mapper,
  sparse analysis, and TXT export.
- `run_ficus_colmap_relaxed.py`: repeats selected runs with relaxed mapper
  thresholds for generated images.
- `run_ficus_colmap_mvs.py`: runs MVS only for selected good sparse models.
- `colmap_points3d_to_ply.py`: converts COLMAP `points3D.bin` to ordinary PLY.
- `write_ficus_colmap_report.py`: writes a markdown summary from CSV/JSON
  outputs.

Install COLMAP separately and pass paths through command-line arguments. Do not
commit generated databases, dense workspaces, logs, or PLY outputs.
