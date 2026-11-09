# Local build entry point for this machine (D: drive, offline deps).
# Wraps build.ps1 with the D-drive PlatformIO core and the D-drive venv.
param(
    [ValidateSet("build", "upload", "monitor", "clean")]
    [string]$Target = "build",
    [string]$Port = "",
    [int]$Jobs = 0
)

$env:PLATFORMIO_CORE_DIR = '<WORKSPACE>\.pio-core'
$env:IDF_PATH = ''
$env:IDF_TOOLS_PATH = '<WORKSPACE>\.pio-core'
# The WorkBuddy sitecustomize shim redirects os.remove/shutil.rmtree to the
# Recycle Bin and blocks bulk deletes. Build tools must be able to clean their
# own temp dirs; the shim provides this official opt-out for child processes.
$env:CODEBUDDY_SAFE_DELETE_ENABLED = '0'
# pioarduino's tool-cmake / tool-ninja packages are metadata-only shells
# (normally populated by idf_tools.py). Reuse the local ESP-IDF v5.5.2 tools.
$env:PATH = '<WORKSPACE>\.pio-core\tools\toolchain-xtensa-esp-elf\bin;<ESPRESSIF_TOOLS>\tools\tools\cmake\3.30.2\bin;<ESPRESSIF_TOOLS>\tools\tools\ninja\1.12.1;' + $env:PATH
# ESP-IDF Component Manager runs `git fetch origin` against GitHub, which is
# unreachable here. Rewrite GitHub URLs to a reachable mirror for child git
# processes only (no global git config changes).
$env:GIT_CONFIG_COUNT = '1'
$env:GIT_CONFIG_KEY_0 = 'url.https://ghfast.top/https://github.com/.insteadOf'
$env:GIT_CONFIG_VALUE_0 = 'https://github.com/'
$env:PLATFORMIO_SETTING_ENABLE_TELEMETRY = 'No'
& '<WORKSPACE>\build.ps1' -Target $Target -Port $Port -Jobs $Jobs -Python '<WORKSPACE>\venv\Scripts\python.exe'
$code = $LASTEXITCODE
# Auto-package the self-contained flash delivery on a successful build.
if ($code -eq 0 -and (Test-Path '<WORKSPACE>\firmware\.pio\build\seeed_wio_tracker_L2-tft\firmware.bin')) {
    Write-Host '==> build succeeded, generating flash delivery package...'
    & '<WORKSPACE>\venv\Scripts\python.exe' '<WORKSPACE>\package-delivery.py'
}
exit $code
