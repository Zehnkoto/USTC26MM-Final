#!/usr/bin/env bash
set -euo pipefail

source /etc/network_turbo || true

cd /root/autodl-tmp/ustc26mm/src/physgaussian-src
mkdir -p model

base="https://hf-mirror.com/datasets/deformsuite/squishy-assets-test/resolve/main"
files=(
  bread-trained.zip
  ficus_whitebg-trained.zip
  pillow2sofa_whitebg-trained.zip
  plane-trained.zip
  wolf_whitebg-trained.zip
)

for f in "${files[@]}"; do
  if [[ -s "model/${f}" ]]; then
    echo "SKIP ${f}"
  else
    echo "DOWNLOAD ${f}"
    curl -L --fail --retry 5 --retry-delay 5 -C - -o "model/${f}" "${base}/${f}"
  fi
  unzip -t "model/${f}" >"/tmp/${f}.test.log"
  unzip -oq "model/${f}" -d model
  echo "DONE ${f}"
done

project_root="${USTC26MM_ROOT:-/root/autodl-tmp/ustc26mm}"
register_script="${project_root}/tools/internal_dev/register_official_phys_models.py"
if [[ -f "${register_script}" ]]; then
  /root/miniconda3/envs/physgaussian/bin/python "${register_script}"
fi
