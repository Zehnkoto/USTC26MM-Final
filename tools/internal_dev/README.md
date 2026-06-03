# Internal Development Data Tools

This directory contains helper scripts used by project members on the shared
server while developing and reproducing demo runs.

These scripts are intentionally separated from the general-purpose tools because
they assume that third-party sample assets are already present on the server, or
that an internal developer is allowed to download those assets separately.

No trained model, PLY, checkpoint, motion cache, or sample dataset is committed
with this repository.

## Scripts

- `download_phys_models.sh` downloads selected PhysGaussian/DeformSuite sample
  assets into the server's PhysGaussian model directory. Use it only when you
  have permission to fetch and use those assets. The current helper uses the
  `deformsuite/squishy-assets-test` mirror URL recorded in the script.
- `register_official_phys_models.py` registers official sample model folders
  already present under `/root/autodl-tmp/ustc26mm/src/physgaussian-src/model`.
- `register_ficus_7000.py` registers the ficus iteration-7000 sample under the
  internal `modelId = ficus-sample-7000`.
- `make_preview_motion.py` creates a synthetic motion package from a static PLY
  for UI/playback debugging. It is not a PhysGaussian simulation result.
- `inspect_recent_preview_runs.py` inspects recent server preview runs for
  debugging drag/proxy playback behavior.

For public/project submission use, cite the upstream dataset or sample model
source and keep the actual data outside Git.
