"""Build the self-contained flash package. RUNS ON THE BUILD MACHINE ONLY.

Output: <WORKSPACE>//delivery//L2_predict_flash_v1//  <- copy this whole folder.
The package contains NO sources, NO build tools, NO compiler, NO Python, NO installer.
"""
import datetime
import hashlib
import json
import os
import shutil
import sys

ROOT = r"<WORKSPACE>"
BUILD = os.path.join(ROOT, "firmware", ".pio", "build", "seeed_wio_tracker_L2-tft")
OUT = os.path.join(ROOT, "delivery", "L2_predict_flash_v1")
TPL = os.path.join(ROOT, "delivery", "template")
ESPTOOL = os.path.join(ROOT, "delivery", "_tools", "esptool-dist",
                       "esptool-windows-amd64", "esptool.exe")
LICENSE = os.path.join(ROOT, "delivery", "_tools", "esptool-dist",
                       "esptool-windows-amd64", "LICENSE")
DEFAULT_LAYOUT = [("bootloader.bin", 0x0), ("partitions.bin", 0x8000),
                  ("boot_app0.bin", 0xE000), ("firmware.bin", 0x10000)]
CHIP, FLASH_SIZE, BAUD = "esp32s3", "16MB", "921600"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def read_flasher_args():
    p = os.path.join(BUILD, "flasher_args.json")
    if not os.path.isfile(p):
        return None
    try:
        d = json.load(open(p, encoding="utf-8"))
        out = []
        for off, name in d.get("flash_files", {}).items():
            off = int(off, 16) if isinstance(off, str) else int(off)
            path = os.path.join(BUILD, os.path.basename(name))
            if os.path.isfile(path):
                out.append((os.path.basename(name), off, path))
        return sorted(out, key=lambda x: x[1]) or None
    except Exception as e:
        print("WARN flasher_args.json:", e)
        return None


def collect_images():
    args = read_flasher_args()
    if args:
        print("offsets from flasher_args.json:", [(n, hex(o)) for n, o, _ in args])
        return args
    return [(n, o, os.path.join(BUILD, n)) for n, o in DEFAULT_LAYOUT
            if os.path.isfile(os.path.join(BUILD, n))]


def merge_images(images, dest):
    end = max(off + os.path.getsize(p) for _, off, p in images)
    buf = bytearray(b"\xff" * end)
    for _, off, p in images:
        data = open(p, "rb").read()
        buf[off:off + len(data)] = data
    open(dest, "wb").write(buf)
    return len(buf)


def write_bat(path, text):
    body = text.replace("\r\n", "\n").replace("\n", "\r\n")
    open(path, "wb").write(body.encode("ascii"))


def main():
    for required in (ESPTOOL,) + tuple(os.path.join(TPL, n) for n in
                     ("flash.bat", "verify.bat", "check_device.bat", "README.md")):
        if not os.path.isfile(required):
            print("FATAL missing:", required)
            return 2
    images = collect_images()
    if not images or not any(n == "firmware.bin" for n, _, _ in images):
        print("FATAL: firmware.bin not built yet in", BUILD)
        print("Finish the compile on this machine, then re-run this script.")
        return 3

    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    fwdir = os.path.join(OUT, "firmware")
    os.makedirs(fwdir)
    shutil.copyfile(ESPTOOL, os.path.join(OUT, "esptool.exe"))
    if os.path.isfile(LICENSE):
        shutil.copyfile(LICENSE, os.path.join(OUT, "LICENSE-esptool.txt"))
    for name, _, path in images:
        shutil.copyfile(path, os.path.join(fwdir, name))
    merged = os.path.join(fwdir, "L2_full.bin")
    total = merge_images(images, merged)
    print("merged L2_full.bin:", total, "bytes (0x%X)" % total)

    for name in ("flash.bat", "verify.bat", "check_device.bat"):
        write_bat(os.path.join(OUT, name),
                  open(os.path.join(TPL, name), encoding="ascii").read())
    shutil.copyfile(os.path.join(TPL, "README.md"), os.path.join(OUT, "README.md"))

    targets = ["esptool.exe", "firmware/L2_full.bin"] + ["firmware/" + n for n, _, _ in images]
    hashes = {}
    for rel in targets:
        p = os.path.join(OUT, rel.replace("/", os.sep))
        hashes[rel.replace("/", "\\")] = {"sha256": sha256(p), "size": os.path.getsize(p)}
    with open(os.path.join(OUT, "SHA256SUMS.txt"), "w", encoding="ascii", newline="\r\n") as f:
        for rel, meta in hashes.items():
            f.write("%s *%s\n" % (meta["sha256"], rel))

    manifest = {
        "package": "L2_predict_flash_v1",
        "generated_on_build_machine": True,
        "generated_at": datetime.datetime.now().astimezone().isoformat(),
        "requires_on_target": {
            "network": False, "install_software": False, "python": False,
            "environment_variables": False, "admin_rights": False,
            "compiler_or_build_tools": False, "build_execution": False,
            "only_action": "flash",
        },
        "compatibility": {
            "os": "Windows 10/11 x64",
            "path": "pure ASCII, no spaces (e.g. C://L2flash)",
            "chip": CHIP, "flash_size": FLASH_SIZE,
            "board": "seeed_wio_tracker_L2",
            "esptool": "5.6.0 official standalone win-amd64",
            "serial_driver": "must already exist on target PC (COM port visible)",
        },
        "source_versions": {
            "firmware": "meshtastic/firmware 9bcf0f776edabb3b2447db323323cf2c49835452 (v2.8.3)",
            "device_ui": "meshtastic/device-ui a5b80d4d5708d0563ea9e0c0277dc8984e2fb952 + WordPredict",
            "platformio_core": "6.2.0", "pioarduino_platform": "55.03.312",
        },
        "flash_layout": [{"file": "firmware/" + n, "offset": "0x%X" % off,
                          "size": os.path.getsize(p)} for n, off, p in images],
        "merged_image": {"file": "firmware\\L2_full.bin", "offset": "0x0",
                         "size": total, "sha256": hashes["firmware\\L2_full.bin"]["sha256"]},
        "files": hashes,
        "flash_command": ("esptool.exe --chip esp32s3 --port <COM> --baud %s "
                          "--before default_reset --after hard_reset write_flash "
                          "--flash_mode dio --flash_freq 80m --flash_size %s "
                          "0x0 firmware\\L2_full.bin" % (BAUD, FLASH_SIZE)),
        "pre_flash_checks": [
            "verify.bat -> RESULT: PASS (files + SHA256 + esptool runs)",
            "check_device.bat <COM> -> chip is ESP32-S3, flash size 16MB",
            "COM port visible and free; USB data cable; stable power",
        ],
        "post_flash_acceptance": [
            "Meshtastic boot banner, no boot loop / Guru Meditation",
            "prediction bar above keyboard; 'hel' -> help / held / helpful",
            "tapping a candidate completes the word + trailing space",
        ],
    }
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print("\nPACKAGE:", OUT)
    for base, _d, files in os.walk(OUT):
        for fn in sorted(files):
            fp = os.path.join(base, fn)
            print("  %-42s %10d B" % (os.path.relpath(fp, OUT), os.path.getsize(fp)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
