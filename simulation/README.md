# Simulation Backend

The simulation integration uses:

- `server/phys_backend.py` for the FastAPI bridge and model/run management.
- `src-overrides/physgaussian-src/` for modified PhysGaussian solver files.
- `src-overrides/supersplat-src/` for frontend controls and motion playback.

Explicit MPM follows PhysGaussian. The implicit path is a project
implementation inspired by i-PhysGaussian-style Newton/GMRES ideas rather than a
direct copy of that code. PBMPM follows the Position-Based Material Point Method
local/global idea and exposes `strength_scale`, relaxation, and bounded inner
iteration controls.
