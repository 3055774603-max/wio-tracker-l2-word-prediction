@echo off
setlocal
cd /d "%~dp0"
set PORT=%~1
if "%PORT%"=="" set PORT=COM9
set "ESPTOOL=esptool.exe"
where esptool.exe >nul 2>nul
if errorlevel 1 (
  if exist "%~dp0esptool.exe" (
    set "ESPTOOL=%~dp0esptool.exe"
  ) else (
    echo [FAIL] esptool.exe not found. Install esptool or place esptool.exe in this folder.
    exit /b 1
  )
)
echo ==========================================================
echo  L2 word prediction v1.1 - flash to %PORT%
echo  dio / 80m / 16MB / 921600
echo ==========================================================
echo Press Ctrl+C to abort, or
pause
"%ESPTOOL%" --chip esp32s3 --port %PORT% --baud 921600 --before default_reset --after hard_reset write_flash --flash_mode dio --flash_freq 80m --flash_size 16MB 0x0 bootloader.bin 0x8000 partitions.bin 0xe000 boot_app0.bin 0x10000 firmware-seeed_wio_tracker_L2-tft-2.8.3.bin 0xc90000 littlefs-seeed_wio_tracker_L2-tft-2.8.3.bin
if errorlevel 1 ( echo [FAIL] flash failed & exit /b 1 )
echo [DONE] v1.1 flashed.
exit /b 0
