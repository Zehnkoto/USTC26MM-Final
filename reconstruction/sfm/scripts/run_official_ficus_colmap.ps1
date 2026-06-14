param(
    [Parameter(Mandatory=$true)]
    [string]$SourceRoot,
    [string]$OutputRoot = "colmap_official_ficus_train100",
    [string]$ColmapExe = "colmap",
    [ValidateSet("sequential", "exhaustive")]
    [string]$Matcher = "sequential"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Get-Location).Path
if (Test-Path -LiteralPath $ColmapExe) {
    $env:PATH = (Split-Path -Parent $ColmapExe) + ";" + $env:PATH
}

$images = Join-Path $OutputRoot "images"
$sparse = Join-Path $OutputRoot "sparse"
$sparseTxt = Join-Path $OutputRoot "sparse_txt"
$logs = Join-Path $OutputRoot "logs"
$reports = Join-Path $OutputRoot "reports"
$database = Join-Path $OutputRoot "database.db"
$summary = Join-Path $reports "official_ficus_train100_colmap_summary.md"
$featureLog = Join-Path $logs "01_feature_extractor.log"
$matcherLog = Join-Path $logs "02_sequential_matcher.log"
if ($Matcher -eq "exhaustive") {
    $matcherLog = Join-Path $logs "02_exhaustive_matcher.log"
}
$mapperLog = Join-Path $logs "03_mapper.log"
$analyzerLog = Join-Path $logs "04_model_analyzer.log"
$converterLog = Join-Path $logs "05_model_converter_txt.log"
$plyLog = Join-Path $logs "06_points3d_to_ply.log"

function Run-Step {
    param(
        [string]$StepName,
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$LogPath
    )
    $stdoutPath = "$LogPath.stdout"
    $stderrPath = "$LogPath.stderr"
    $process = Start-Process -FilePath $FilePath -ArgumentList $Arguments -NoNewWindow -Wait -PassThru `
        -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
    $stdout = if (Test-Path -LiteralPath $stdoutPath) { Get-Content -LiteralPath $stdoutPath -Raw } else { "" }
    $stderr = if (Test-Path -LiteralPath $stderrPath) { Get-Content -LiteralPath $stderrPath -Raw } else { "" }
    @(
        "### $StepName"
        "exit_code=$($process.ExitCode)"
        ""
        "### stdout"
        $stdout
        ""
        "### stderr"
        $stderr
    ) | Set-Content -LiteralPath $LogPath -Encoding UTF8
    Remove-Item -LiteralPath $stdoutPath, $stderrPath -Force -ErrorAction SilentlyContinue
    if ($process.ExitCode -ne 0) {
        throw "$StepName failed with exit code $($process.ExitCode). See $LogPath"
    }
}

New-Item -ItemType Directory -Force -Path $images, $sparse, $sparseTxt, $logs, $reports | Out-Null

$sourceImages = Get-ChildItem -LiteralPath (Join-Path $SourceRoot "train") -File |
    Where-Object { $_.Extension -ieq ".png" } |
    Sort-Object {
        if ($_.BaseName -match "^r_(\d+)$") { [int]$Matches[1] } else { [int]::MaxValue }
    }

if ($sourceImages.Count -eq 0) {
    throw "No train PNG images found in $SourceRoot"
}

foreach ($image in $sourceImages) {
    Copy-Item -LiteralPath $image.FullName -Destination (Join-Path $images $image.Name) -Force
}

$introBlock = @"
# Official Ficus COLMAP run

- Started: $(Get-Date -Format o)
- Source dataset: $SourceRoot
- Image subset: train split, $($sourceImages.Count) RGB PNG images, 800x800.
- Reason for subset: full train split is complete for NeRF-synthetic training and should fit a 30-minute local COLMAP smoke/baseline run; test depth/normal files are excluded.
- Matcher: $Matcher.
- COLMAP: $ColmapExe

"@
$introBlock | Set-Content -LiteralPath $summary -Encoding UTF8

Run-Step "feature_extractor" $ColmapExe @(
    "feature_extractor",
    "--database_path", $database,
    "--image_path", $images,
    "--ImageReader.single_camera", "1",
    "--FeatureExtraction.use_gpu", "1",
    "--FeatureExtraction.max_image_size", "1200",
    "--SiftExtraction.max_num_features", "4096"
) $featureLog

if ($Matcher -eq "sequential") {
    Run-Step "sequential_matcher" $ColmapExe @(
        "sequential_matcher",
        "--database_path", $database,
        "--SequentialMatching.overlap", "10",
        "--SequentialMatching.loop_detection", "1",
        "--FeatureMatching.use_gpu", "1",
        "--FeatureMatching.guided_matching", "0",
        "--FeatureMatching.max_num_matches", "8192"
    ) $matcherLog
} else {
    Run-Step "exhaustive_matcher" $ColmapExe @(
        "exhaustive_matcher",
        "--database_path", $database,
        "--FeatureMatching.use_gpu", "1",
        "--FeatureMatching.guided_matching", "0",
        "--FeatureMatching.max_num_matches", "8192"
    ) $matcherLog
}

Run-Step "mapper" $ColmapExe @(
    "mapper",
    "--database_path", $database,
    "--image_path", $images,
    "--output_path", $sparse
) $mapperLog

$models = Get-ChildItem -LiteralPath $sparse -Directory | Sort-Object Name
$bestModel = $models | Select-Object -First 1
if (-not $bestModel) {
    Add-Content -LiteralPath $summary -Encoding UTF8 -Value "`n## Result`n`nMapper produced no sparse model.`n"
    exit 2
}

Run-Step "model_analyzer" $ColmapExe @(
    "model_analyzer",
    "--path", $bestModel.FullName
) $analyzerLog

Run-Step "model_converter" $ColmapExe @(
    "model_converter",
    "--input_path", $bestModel.FullName,
    "--output_path", $sparseTxt,
    "--output_type", "TXT"
) $converterLog

$pointsBin = Join-Path $bestModel.FullName "points3D.bin"
$pointsPly = Join-Path $OutputRoot "official_ficus_train100_sfm_sparse_points3D.ply"
Run-Step "points3d_to_ply" "python" @(
    (Join-Path $repoRoot "tools\colmap_points3d_to_ply.py"),
    $pointsBin,
    $pointsPly
) $plyLog

$analyzer = Get-Content -LiteralPath $analyzerLog -Raw
$resultBlock = @"

## Result

- Finished: $(Get-Date -Format o)
- Sparse model: $($bestModel.FullName)
- Sparse PLY: $pointsPly
- Database: $database

## COLMAP model analyzer

~~~text
$analyzer
~~~
"@
$resultBlock | Add-Content -LiteralPath $summary -Encoding UTF8

Write-Output $summary
