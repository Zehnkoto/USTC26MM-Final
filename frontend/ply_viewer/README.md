# SfM/MVS PLY Viewer

Local Three.js viewer for ordinary SfM/MVS `.ply` point clouds. These are not
3DGS splat PLY files and will not open in SuperSplat as Gaussian splats.

## Run

```bash
npm install
npm run dev
```

Open `http://127.0.0.1:5178`.

Preset PLY paths can be configured locally in `server/presets.js` or loaded with
the file picker. Do not commit local output paths or point-cloud files.
