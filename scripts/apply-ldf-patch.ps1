# =============================================================================
# Installs the patched PlatformIO dependency-finder (piolib.py).
#
# WHY THIS IS NEEDED
# ------------------
# Stock PlatformIO hangs on "Scanning dependencies..." for this project.
# piolib.py implements the library dependency scan with:
#   * list.pop(0) work queue                      -> O(n) per pop
#   * `item in search_files` / `in _processed_*`  -> O(n) linear list scans
#   * `item not in result`                        -> SCons Node.__eq__ on every
#                                                   candidate, i.e. O(n) per item
#   * is_common_builder() calling os.path.realpath() twice per miss, evaluated
#     once per (implicit include x library builder) pair
# With 112 libraries and lvgl's several thousand implicit includes this becomes
# effectively non-terminating: the process sits at 100% CPU, performs ZERO disk
# I/O, keeps a flat memory footprint, and never prints another line.
#
# The patched file adds memoisation, set-based membership, an index-based work
# queue and cached realpath/isfile probes. Scan time went from "never finishes"
# to ~11 minutes, with identical dependency results.
#
# Usage:  .\apply-ldf-patch.ps1 [-Python python]
# =============================================================================

param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

$src = Join-Path $PSScriptRoot "platformio-patch\piolib.py"
if (-not (Test-Path $src)) {
    throw "patched piolib.py not found: $src"
}

$candidates = @()

# 1) the PlatformIO package that this interpreter actually imports
try {
    $coreDir = & $Python -c "import platformio, os; print(os.path.dirname(platformio.__file__))" 2>$null
    if ($LASTEXITCODE -eq 0 -and $coreDir) {
        $candidates += Join-Path $coreDir "builder\tools\piolib.py"
    }
} catch {
    Write-Host "WARNING: could not resolve the platformio package with '$Python'"
}

# 2) the core dir's own penv (SCons runs out of it on some setups)
$coreRoots = @()
if ($env:PLATFORMIO_CORE_DIR) { $coreRoots += $env:PLATFORMIO_CORE_DIR }
$coreRoots += (Join-Path $env:USERPROFILE ".platformio")
foreach ($cr in $coreRoots) {
    $p = Join-Path $cr "penv\Lib\site-packages\platformio\builder\tools\piolib.py"
    if (Test-Path $p) { $candidates += $p }
}

if (-not $candidates) {
    throw "No piolib.py found. Install PlatformIO first (pip install 'platformio>=6.2.0'), then re-run."
}

$patched = 0
foreach ($target in $candidates) {
    if (-not (Test-Path $target)) { continue }

    $content = Get-Content $target -Raw
    if ($content -match "_IS_COMMON_BUILDER_CACHE") {
        Write-Host "already patched: $target"
        $patched++
        continue
    }

    Copy-Item $target "$target.orig" -Force
    Copy-Item $src $target -Force

    $dir = Split-Path $target
    Get-ChildItem $dir -Filter "piolib*.pyc" -Recurse -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue

    Write-Host "patched: $target  (backup: $target.orig)"
    $patched++
}

if ($patched -eq 0) {
    throw "Nothing was patched."
}

Write-Host ""
Write-Host "Done. Verify with:"
Write-Host "  $Python -c `"import ast;print('ok' if ast.parse(open(r'$($candidates[0])',encoding='utf-8').read()) else '')`""
Write-Host ""
Write-Host "NOTE: reinstalling or upgrading PlatformIO overwrites this patch. Re-run this script afterwards."
