# Source Overrides

This directory contains the project-specific source changes that must be copied
over the upstream repositories during a full deployment.

The repository intentionally does not vendor complete copies of SuperSplat or
PhysGaussian. Clone those upstream projects first, then overlay these files:

- `src-overrides/supersplat-src/` -> `supersplat-src/`
- `src-overrides/physgaussian-src/` -> `physgaussian-src/`

On Linux/macOS:

```bash
rsync -a src-overrides/supersplat-src/ ../supersplat-src/
rsync -a src-overrides/physgaussian-src/ ../physgaussian-src/
```

On Windows PowerShell:

```powershell
Copy-Item -Recurse -Force .\src-overrides\supersplat-src\* ..\supersplat-src\
Copy-Item -Recurse -Force .\src-overrides\physgaussian-src\* ..\physgaussian-src\
```

Keep generated outputs, trained models, logs, and simulation binaries outside
this directory.
