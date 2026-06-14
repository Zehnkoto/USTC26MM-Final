# USTC26MM Final

This repository contains the curated source code for the USTC 2026 MM final project. 

## Layout

- `server/`: FastAPI backend bridge for SuperSplat-to-PhysGaussian simulation.
- `src-overrides/`: minimal modified files to apply to upstream SuperSplat and
  PhysGaussian checkouts.
- `tools/`: physics validation and ablation utilities from the CG Final project.
- `reconstruction/sfm/`: COLMAP matching-graph, SfM/MVS, point-cloud export, and
  reporting scripts.
- `reconstruction/3dgs/`: RoMa/COLMAP/3DGS orchestration and preview scripts.
- `frontend/ply_viewer/`: local Three.js viewer for ordinary SfM/MVS PLY point
  clouds. It is not a 3DGS splat viewer.
- `frontend/supersplat_physics_patch/`: notes pointing to the SuperSplat patch
  overlay in `src-overrides/supersplat-src/`.
- `simulation/`: notes for the physical simulation backend and solver variants.
- `paper/`: LaTeX source and selected figures needed by the current report.
- `docs/`: code inventory, experiment notes, and open-source attribution.

## Upstream Projects

- SuperSplat: https://github.com/playcanvas/supersplat
- PhysGaussian: https://github.com/XPandora/PhysGaussian
- COLMAP: https://github.com/colmap/colmap
- 3D Gaussian Splatting: https://github.com/graphdeco-inria/gaussian-splatting
- RoMa: https://github.com/Parskatt/RoMa

We do not vendor full third-party repositories. Only project-owned scripts and
small overlay files are included.

## Main Modifications

- SuperSplat physics frontend: simulation panel, Gaussian region selection,
  fixed/movable area controls, solver/material parameter controls, backend
  submission, and motion package playback.
- PhysGaussian overlay: explicit MPM integration, implicit MPM-inspired
  Newton/GMRES path, PBMPM local-global stepping, PBMPM `strength_scale`,
  `n_min`/`n_max`, and relaxation parameter wiring.
- Reconstruction tooling: COLMAP matching graph experiments, generated-view
  relaxed mapper runs, MVS selection, sparse point export, RoMa/COLMAP/3DGS
  comparison scripts, and PLY preview tooling.

## Excluded

Excluded by design: `node_modules/`, `dist/`, `build/`, `outputs/`, `runs/`,
`dense/`, checkpoints, model weights, `.ply`, `.bin`, `.h5`, `.pt`, `.pth`,
videos, zip/tar packages, logs, caches, and personal path manifests.
