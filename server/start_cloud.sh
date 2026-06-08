#!/usr/bin/env bash
set -euo pipefail

cd /root/autodl-tmp/ustc26mm
source /root/miniconda3/etc/profile.d/conda.sh
conda activate physgaussian

export PYTHONPATH=/root/autodl-tmp/ustc26mm
export PHYSGAUSSIAN_ROOT=/root/autodl-tmp/ustc26mm/src/physgaussian-src
export SUPERSPLAT_DIST=/root/autodl-tmp/ustc26mm/supersplat-dist
export PHYS_WORK_ROOT=/root/autodl-tmp/ustc26mm/work
export PYTHON_BIN=/root/miniconda3/envs/physgaussian/bin/python

exec python -m uvicorn server.phys_backend:app --host 0.0.0.0 --port 6006
