# USTC26MM Final

Interactive physics editing for Gaussian splatting scenes. This repository keeps
the project-owned integration code, backend bridge, overlay patches, and
developer tools needed to reproduce the current SuperSplat + PhysGaussian
workflow without committing local runtime data or full third-party checkouts.

## What This Project Contains

- A Python backend bridge in `server/` for loading scenes, running physics
  operations, and serving API requests.
- SuperSplat source overrides in `src-overrides/supersplat-src/` for the
  physics UI, motion worker, session state, and splat metadata integration.
- PhysGaussian source overrides in `src-overrides/physgaussian-src/` for MPM
  solver behavior, implicit/explicit stepping support, and transform decoding.
- Utility scripts in `tools/` for contract checks, workspace sync, and ablation
  experiment collection.
- Documentation in `docs/` describing usage, external libraries, citations, and
  workspace sync policy.

## What Is Not Included

The repository intentionally excludes generated or local-only content:

- Scene assets, datasets, model checkpoints, render outputs, videos, logs, and
  ablation result folders.
- Local SSH/cloud workspace manifests such as `tools/workspace_manifest.json`.
- Full upstream SuperSplat, PhysGaussian, or other third-party source trees.
- Python virtual environments, Node packages, build outputs, caches, and backup
  archives.

Use the template file `tools/workspace_manifest.example.json` if you need to set
up local/cloud sync on another machine.

## External Source Trees

This repo is designed as an overlay, not a vendor mirror. Download the upstream
projects separately, then copy or patch the files under `src-overrides/` into
the matching upstream paths.

See `docs/EXTERNAL_LIBS.md` for the recommended layout and synchronization
steps.

## Environment

Recommended baseline:

- Windows 10/11 or Linux with Python 3.10+
- CUDA-capable NVIDIA GPU for PhysGaussian simulation
- Node.js 18+ for the SuperSplat frontend
- Git and PowerShell or Bash

Install Python backend dependencies:

```powershell
cd server
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

For Linux/cloud deployment:

```bash
cd server
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Install frontend dependencies in a separate upstream SuperSplat checkout after
applying the overrides:

```bash
npm install
npm run build
```

## Run

Start the backend:

```powershell
cd server
python phys_backend.py --host 127.0.0.1 --port 8443
```

On a cloud Linux machine you can also adapt:

```bash
bash server/start_cloud.sh
```

Then start the SuperSplat development server from the upstream frontend checkout
where the overrides have been applied.

## Reproduce Checks And Experiments

Run the local implicit MPM contract checks:

```powershell
python tools/check_implicit_mpm_contracts.py
```

Run ablation experiments after configuring paths to your backend and scene data:

```powershell
python tools/run_ablation.py --help
python tools/collect_ablation_results.py --help
```

By default, experiment outputs should go under ignored folders such as
`outputs/`, `logs/`, or `reports/`.

## Upload Hygiene

Before committing, check:

```powershell
git status
git diff
git diff --cached
```

Only source code, documentation, templates, and lightweight scripts should be
staged. Local manifests, assets, checkpoints, rendered media, logs, and backup
packages should stay on disk but remain untracked.
