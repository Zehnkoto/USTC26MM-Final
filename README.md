# USTC26MM-Final

SuperSplat + PhysGaussian integrated physics simulation project.

This repository keeps only the project-specific source, tools, and
documentation needed to reproduce the current prototype. It does not include
generated simulation outputs, trained models, sample datasets, server backups,
full upstream copies of SuperSplat and PhysGaussian, or nested third-party
reference checkouts.

## Contents

- `server/` - FastAPI bridge between the SuperSplat frontend and PhysGaussian.
- `src-overrides/` - source files that should be overlaid onto upstream
  SuperSplat and PhysGaussian checkouts, including the local PBMPM rewrite in
  the PhysGaussian/Warp MPM path.
- `tools/` - cloud sync, health check, run inspection, and motion/trace
  debugging utilities.
- `tools/internal_dev/` - internal helper scripts for server-side sample data
  registration and preview debugging. They do not include sample data.
- `docs/` - project documentation.

## Documentation

- [使用说明](docs/USAGE.md)
- [引用说明](docs/CITATIONS.md)
- [工作完成情况与内容介绍](docs/WORK_SUMMARY.md)

## Current Preview

The current cloud preview/API entry is:

```text
https://u1002897-ak8t-c0a1825e.westb.seetacloud.com:8443/
```

`8448` is not the active preview port for the current deployment.
