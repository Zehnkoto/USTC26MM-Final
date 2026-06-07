param(
    [switch]$Apply,
    [switch]$Build,
    [switch]$CleanDist,
    [string]$ManifestPath = "tools/workspace_manifest.json"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path ".").Path
$manifest = Get-Content -LiteralPath (Join-Path $repoRoot $ManifestPath) -Raw -Encoding UTF8 | ConvertFrom-Json
$localRoot = $manifest.localRoot
$sshKey = $manifest.ssh.identityFile
$sshPort = [string]$manifest.ssh.port
$sshHost = $manifest.ssh.host
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backup = "$($manifest.cloudRoot)/.tmp/sync-backup-$stamp"

function Run-Step {
    param([string]$Description, [scriptblock]$Action)
    Write-Host "== $Description =="
    if ($Apply) {
        & $Action
    } else {
        Write-Host "DRY RUN"
    }
}

if ($Build) {
    Run-Step "Build local SuperSplat dist" {
        Push-Location (Join-Path $localRoot "supersplat-src")
        try {
            & npm.cmd run build
        } finally {
            Pop-Location
        }
    }
}

Write-Host "Apply: $Apply"
Write-Host "Backup: $backup"

Run-Step "Create cloud backup" {
    $commands = @(
        "mkdir -p '$backup/server' '$backup/supersplat-src-patched/src/ui/scss' '$backup/src/physgaussian-src/mpm_solver_warp' '$backup/src/physgaussian-src/utils'",
        "cp '$($manifest.cloudRoot)/server/phys_backend.py' '$backup/server/' 2>/dev/null || true",
        "cp '$($manifest.cloudRoot)/supersplat-src-patched/src/ui/bottom-toolbar.ts' '$backup/supersplat-src-patched/src/ui/' 2>/dev/null || true",
        "cp '$($manifest.cloudRoot)/supersplat-src-patched/src/ui/physics-panel.ts' '$backup/supersplat-src-patched/src/ui/' 2>/dev/null || true",
        "cp '$($manifest.cloudRoot)/supersplat-src-patched/src/ui/scss/physics-panel.scss' '$backup/supersplat-src-patched/src/ui/scss/' 2>/dev/null || true",
        "cp '$($manifest.cloudRoot)/supersplat-src-patched/src/editor.ts' '$backup/supersplat-src-patched/src/' 2>/dev/null || true",
        "cp '$($manifest.cloudRoot)/supersplat-src-patched/src/physics-session.ts' '$backup/supersplat-src-patched/src/' 2>/dev/null || true",
        "cp '$($manifest.cloudRoot)/supersplat-src-patched/src/phys-motion.ts' '$backup/supersplat-src-patched/src/' 2>/dev/null || true",
        "cp '$($manifest.cloudRoot)/supersplat-src-patched/src/phys-motion-worker.ts' '$backup/supersplat-src-patched/src/' 2>/dev/null || true",
        "cp '$($manifest.cloudRoot)/supersplat-src-patched/src/splat.ts' '$backup/supersplat-src-patched/src/' 2>/dev/null || true",
        "cp '$($manifest.cloudRoot)/src/physgaussian-src/mpm_solver_warp/mpm_solver_warp.py' '$backup/src/physgaussian-src/mpm_solver_warp/' 2>/dev/null || true",
        "cp '$($manifest.cloudRoot)/src/physgaussian-src/mpm_solver_warp/mpm_utils.py' '$backup/src/physgaussian-src/mpm_solver_warp/' 2>/dev/null || true",
        "cp '$($manifest.cloudRoot)/src/physgaussian-src/mpm_solver_warp/warp_utils.py' '$backup/src/physgaussian-src/mpm_solver_warp/' 2>/dev/null || true",
        "cp '$($manifest.cloudRoot)/src/physgaussian-src/utils/decode_param.py' '$backup/src/physgaussian-src/utils/' 2>/dev/null || true",
        "cp '$($manifest.cloudRoot)/src/physgaussian-src/gs_simulation.py' '$backup/src/physgaussian-src/' 2>/dev/null || true",
        "tar -czf '$backup/supersplat-dist.tar.gz' -C '$($manifest.cloudDist)' . 2>/dev/null || true"
    ) -join "; "
    & ssh -i $sshKey -p $sshPort $sshHost $commands
}

foreach ($file in $manifest.files) {
    $local = Join-Path $localRoot $file.local
    $remote = $file.cloud
    Run-Step "Upload $($file.name)" {
        & ssh -i $sshKey -p $sshPort $sshHost "mkdir -p '$(Split-Path -Parent $remote)'"
        & scp -i $sshKey -P $sshPort $local "${sshHost}:$remote"
    }
}

$archive = Join-Path $repoRoot ".tmp/supersplat-dist-sync.tar.gz"
Run-Step "Pack local dist" {
    New-Item -ItemType Directory -Force -Path (Join-Path $repoRoot ".tmp") | Out-Null
    if (Test-Path -LiteralPath $archive) {
        Remove-Item -LiteralPath $archive -Force
    }
    tar -czf $archive -C (Join-Path $localRoot $manifest.localDist) .
}

Run-Step "Upload and unpack dist" {
    & scp -i $sshKey -P $sshPort $archive "${sshHost}:$($manifest.cloudRoot)/.tmp/supersplat-dist-sync.tar.gz"
    if ($CleanDist) {
        & ssh -i $sshKey -p $sshPort $sshHost "find '$($manifest.cloudDist)' -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +; tar -xzf '$($manifest.cloudRoot)/.tmp/supersplat-dist-sync.tar.gz' -C '$($manifest.cloudDist)'"
    } else {
        & ssh -i $sshKey -p $sshPort $sshHost "tar -xzf '$($manifest.cloudRoot)/.tmp/supersplat-dist-sync.tar.gz' -C '$($manifest.cloudDist)'"
    }
}

Run-Step "Restart cloud backend with canonical environment" {
    & ssh -i $sshKey -p $sshPort $sshHost "cd '$($manifest.cloudRoot)' && /root/miniconda3/envs/physgaussian/bin/python restart_remote_frontend.py"
}

Write-Host "Done. Run tools/check_workspace_consistency.ps1 to verify."
