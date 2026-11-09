# =============================================================================
# Meshtastic Wio Tracker L2 - build & flash helper (portable)
#
# Expected layout (this script sits at the root):
#   <root>\
#     build.ps1              <- this file
#     partitions.csv         <- auto-created if missing
#     firmware\              <- meshtastic/firmware @ 9bcf0f77
#     libs\device-ui\        <- meshtastic/device-ui @ a5b80d4d (patched)
#
# device-ui MUST live in <root>\libs\device-ui because firmware\platformio.ini
# sets `lib_extra_dirs = ../libs`. PlatformIO resolves that relative to the
# project directory, i.e. to <root>\libs.
#
# Usage:
#   .\build.ps1                       # compile
#   .\build.ps1 upload -Port COM52    # compile and flash
#   .\build.ps1 monitor -Port COM52   # serial monitor
#   .\build.ps1 clean                 # remove build output
#   .\build.ps1 build -Jobs 8         # limit parallelism
#
# Keep this file ASCII-only: Windows PowerShell 5.1 reads .ps1 files as ANSI
# unless they carry a UTF-8 BOM, and non-ASCII bytes break the parser.
# =============================================================================

param(
    [ValidateSet("build", "upload", "monitor", "clean")]
    [string]$Target = "build",
    [string]$Port = "",
    [string]$EnvName = "seeed_wio_tracker_L2-tft",
    [int]$Jobs = 0,
    [string]$Python = "python"
)

$ErrorActionPreference = "Continue"  # L2: native stderr (e.g. sandbox safe-delete warnings) must not abort the build

$root = $PSScriptRoot
$fw = Join-Path $root "firmware"
$dui = Join-Path $root "libs\device-ui"

if (-not (Test-Path $fw)) {
    throw "firmware\ not found next to this script: $fw"
}
if (-not (Test-Path $dui)) {
    throw "libs\device-ui not found: $dui`nPlatformIO resolves lib_extra_dirs=../libs relative to firmware\, so device-ui must be at <root>\libs\device-ui."
}

# The board declares board_build.partitions = default_16MB.csv, while the
# generated sdkconfig.defaults asks ESP-IDF for "partitions.csv". Neither the
# Arduino nor the IDF builder creates <project>\partitions.csv, so the IDF half
# of the hybrid build fails with a FileNotFoundError. Materialise it.
$part = Join-Path $fw "partitions.csv"
if (-not (Test-Path $part)) {
    $tmpl = Get-ChildItem "$env:USERPROFILE\.platformio" -Recurse -Filter "default_16MB.csv" -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($tmpl) {
        Copy-Item $tmpl.FullName $part -Force
        Write-Host "created partitions.csv from $($tmpl.FullName)"
    } else {
        Write-Host "WARNING: partitions.csv is missing and default_16MB.csv was not found."
        Write-Host "         The first build will download the framework; re-run afterwards."
    }
}

if ($Jobs -le 0) {
    $Jobs = [Environment]::ProcessorCount
}

$pioArgs = @("-m", "platformio")

switch ($Target) {
    "build" {
        $pioArgs += @("run", "-e", $EnvName, "-j", $Jobs)
    }
    "upload" {
        $pioArgs += @("run", "-e", $EnvName, "-j", $Jobs, "-t", "upload")
        if ($Port) { $pioArgs += @("--upload-port", $Port) }
    }
    "monitor" {
        $pioArgs += @("device", "monitor", "-b", "115200")
        if ($Port) { $pioArgs += @("-p", $Port) }
    }
    "clean" {
        $pioArgs += @("run", "-e", $EnvName, "-t", "clean")
    }
}

Write-Host "==> $Python $($pioArgs -join ' ')"
Write-Host "==> jobs: $Jobs   env: $EnvName"

Push-Location $fw
try {
    & $Python @pioArgs
} finally {
    $code = $LASTEXITCODE
    Pop-Location
}

if ($Target -eq "build" -or $Target -eq "upload") {
    $binDir = Join-Path $fw ".pio\build\$EnvName"
    if (Test-Path $binDir) {
        Get-ChildItem $binDir -Filter "firmware*.bin" -ErrorAction SilentlyContinue | ForEach-Object {
            Write-Host "firmware image: $($_.FullName)  ($([int]($_.Length/1KB)) KB)"
        }
    }
}

exit $code
