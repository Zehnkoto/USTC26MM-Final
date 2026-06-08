param(
    [string]$ManifestPath = "tools/workspace_manifest.json"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path ".").Path
$manifest = Get-Content -LiteralPath (Join-Path $repoRoot $ManifestPath) -Raw -Encoding UTF8 | ConvertFrom-Json
$localRoot = $manifest.localRoot
$sshKey = $manifest.ssh.identityFile
$sshPort = [string]$manifest.ssh.port
$sshHost = $manifest.ssh.host

function Invoke-Cloud {
    param([string]$Command)
    & ssh -i $sshKey -p $sshPort $sshHost $Command
}

function Invoke-CloudText {
    param([string]$Command)
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        $previousPreference = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            $output = Invoke-Cloud $Command 2>&1
            $exitCode = $LASTEXITCODE
        } finally {
            $ErrorActionPreference = $previousPreference
        }
        if ($exitCode -eq 0 -and $null -ne $output) {
            return (($output | ForEach-Object { "$_" }) -join "`n")
        }
        if ($attempt -lt 3) {
            Start-Sleep -Seconds 2
        }
    }
    return $null
}

function Get-LocalHash {
    param([string]$Path)
    $full = Join-Path $localRoot $Path
    if (-not (Test-Path -LiteralPath $full)) {
        return "MISSING"
    }
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $full).Hash.ToLowerInvariant()
}

Write-Host "== Workspace file hashes =="
$rows = @()
$remoteHashCommands = @()
foreach ($file in $manifest.files) {
    $remoteHashCommands += "if [ -f '$($file.cloud)' ]; then h=`$(sha256sum '$($file.cloud)'); echo '$($file.name)' `$`{h%% *`}; else echo '$($file.name) MISSING'; fi"
}
$remoteHashText = Invoke-CloudText ($remoteHashCommands -join "; ")
$remoteHashes = @{}
if ($null -ne $remoteHashText) {
    foreach ($line in ($remoteHashText -split "`n")) {
        $parts = $line.Trim() -split "\s+", 2
        if ($parts.Length -eq 2) {
            $remoteHashes[$parts[0]] = $parts[1]
        }
    }
}
foreach ($file in $manifest.files) {
    $localHash = Get-LocalHash $file.local
    $cloudHash = if ($remoteHashes.ContainsKey($file.name)) { $remoteHashes[$file.name] } else { "ERROR" }
    $rows += [pscustomobject]@{
        Name = $file.name
        Local = $localHash
        Cloud = $cloudHash
        Match = ($localHash -eq $cloudHash)
    }
}
$rows | Format-Table -AutoSize

Write-Host ""
Write-Host "== Cloud health =="
$health = Invoke-CloudText "curl -s '$($manifest.cloudHealthUrl)'; echo"
if ($null -eq $health) { Write-Host "ERROR" } else { Write-Host $health }

Write-Host ""
Write-Host "== Dist root hash =="
$distRoot = Join-Path $localRoot $manifest.localDist
if (Test-Path -LiteralPath $distRoot) {
    $localLines = Get-ChildItem -LiteralPath $distRoot -Recurse -File |
        Sort-Object { $_.FullName.Substring($distRoot.Length).TrimStart('\') -replace '\\','/' } |
        ForEach-Object {
            $rel = "./" + ($_.FullName.Substring($distRoot.Length).TrimStart('\') -replace '\\','/')
            $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLowerInvariant()
            "$hash  $rel"
        }
    $localManifestText = ($localLines -join "`n") + "`n"
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $localDistHash = [BitConverter]::ToString($sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($localManifestText))).Replace("-", "").ToLowerInvariant()
} else {
    $localDistHash = "MISSING"
}
$cloudDist = $manifest.cloudDist
$cloudDistText = Invoke-CloudText "cd '$cloudDist' && find . -path ./dist -prune -o -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum"
$cloudDistHash = if ($null -eq $cloudDistText) { "ERROR" } else { (($cloudDistText -split "`n" | Select-Object -First 1).Trim() -split "\s+")[0] }
[pscustomobject]@{
    LocalDistRoot = $localDistHash
    CloudDistRootExcludingNestedDist = $cloudDistHash
    Match = ($localDistHash -eq $cloudDistHash)
} | Format-List

Write-Host "== Key patch grep on cloud =="
$pattern = ($manifest.keyPatches -join "|")
$grep = Invoke-CloudText "grep -R -n -o -E '$pattern' '$($manifest.cloudRoot)/server/phys_backend.py' '$($manifest.cloudRoot)/supersplat-src-patched/src' '$($manifest.cloudRoot)/src/physgaussian-src/mpm_solver_warp/mpm_solver_warp.py' '$($manifest.cloudRoot)/supersplat-dist/index.js' 2>/dev/null | head -120"
if ($null -eq $grep) { Write-Host "ERROR" } else { Write-Host $grep }
