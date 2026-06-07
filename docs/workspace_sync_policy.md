# Workspace Sync Policy

The repository should not commit machine-specific workspace settings. Use the
example manifest as a template and keep the real manifest local.

## Local Manifest

1. Copy `tools/workspace_manifest.example.json` to
   `tools/workspace_manifest.json`.
2. Fill in local paths, cloud root, SSH host, SSH port, and identity file.
3. Keep the real manifest untracked. It is ignored by `.gitignore`.

## What May Be Synced

- Project source files under `server/`, `src-overrides/`, `tools/`, and `docs/`.
- Lightweight configuration templates.
- Small scripts required for setup, validation, or experiment reproduction.

## What Should Stay Local

- Private SSH keys, hostnames, usernames, and live service URLs.
- Scene assets, datasets, checkpoints, rendered media, videos, and logs.
- Backup archives, recovery packages, temporary scripts, caches, and build
  output folders.
- Full upstream repositories such as SuperSplat or PhysGaussian.

## Cloud Runtime Paths

Scripts may contain documented example cloud roots, but upload commits should
not include personal Windows paths, private key paths, or live endpoint URLs.

If a cloud path is required by a script, make it configurable through the local
manifest or command-line options.
