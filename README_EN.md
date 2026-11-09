# Wio Tracker L2 — English Word Prediction Firmware

**English** | [简体中文](README.md)

English word prediction for the Meshtastic device-ui virtual keyboard on the **Seeed Wio Tracker L2** (ESP32-S3, 16 MB Flash, 320×240 TFT): type a prefix, 3 candidate words appear above the keyboard, tap one to complete and append a space.

Based on Meshtastic firmware v2.8.3 + device-ui, with a 10,000-word dictionary (frequency-ordered). Built and flash-verified on Windows.

## Key Results

| Item | Value |
|---|---|
| Target environment | `seeed_wio_tracker_L2-tft`, ESP32-S3, 16 MB Flash |
| Word list | 10,000 words, `.flash.rodata` 76,015 B (74.2 KiB) |
| Candidates | 3; `hel` → `help / held / helpful`, `here` → `herein / hereby` |
| Firmware | app 3,946,400 B (partition 6.25 MiB, 60.2% used) |
| Field test | 31 candidate displays, tap-to-insert 100% consistent, 0 boot loops |
| Versions | v1.0 (3,000 words, stable) / v1.1 (10,000 words, current) |

## Repository Layout

| Path | Contents |
|---|---|
| `firmware/` | Meshtastic firmware source (upstream `platformio.ini` restored, `.pio/` build cache removed) + this project's `partitions.csv` |
| `libs/device-ui/` | Modified device-ui: `WordPredict.h/.cpp`, `predict_wordlist.inc`, `TFTView_320x240.*` |
| `patches/` | Diffs against upstream + PlatformIO LDF patch |
| `scripts/` | Build, offline-dependency, packaging and algorithm-verification scripts |
| `wordlist/` | Frequency corpora, v1.0 original word list, reproducible generation script |
| `releases/` | v1.0 / v1.1 flash images and one-click flash script |
| `docs/` | Full handoff documentation, build status, release notes, memory analysis |
| `CHANGELOG.md` | Version ledger |

**Not included**: PlatformIO toolchain (~10 GB), Python venvs, third-party dependency zips, build caches, serial logs (contain device privacy), symbol-carrying ELF files, esptool binary, device-ui third-party map tile packs.

## Quick Start

### 1. Build

```
python -m venv .venv
.venv/Scripts/pip install platformio==6.2.0
```

Apply the LDF patch per `patches/README.md` (must be applied to **both** the venv and PlatformIO's `penv`). Then run `scripts/build.ps1`, or configure offline dependencies per `scripts/README.md`.

> Scripts in `scripts/` record the build machine's environment setup and contain `<WORKSPACE>` / `<ESPRESSIF_TOOLS>` / `<USER_HOME>` placeholders — replace them with your own paths after cloning. The docs use the same placeholders.

### 2. Flash

`releases/v1.1/flash.bat COM9` (bring your own `esptool`).

**You must flash with `--flash_mode dio`**: the board JSON says `qio`, but PlatformIO produces images for `dio`; flashing with `qio` causes repeated `TG0WDT_SYS_RST` boot loops. See `docs/HANDOFF.md` section 10.3.

### 3. Reproduce the Word List

```
python wordlist/build_wordlist.py
```

Generates the 10,000-word `predict_wordlist.inc` from the two corpora in `wordlist/` plus the v1.0 original list. The first 3,000 words stay byte-for-byte identical, so accepted candidates never regress.

### 4. Verify

Open the message input screen and type `hel` — the candidate strip should show `help / held / helpful`; tapping completes the word and adds a space. Type `here` to see `herein / hereby` (new coverage in the 10,000-word version).

## Known Items

- The firmware emits `WordPredict:` diagnostic logs (~2 WARN lines per keystroke); harmless to the UI — remove and rebuild if you want a quiet build
- `kMaxCandidates = 3` is unchanged; growing the word list only improves coverage, not the number of candidates
- `hel` returns `help / held / helpful`, with `hello` ranked 4th (by frequency)
- The longest word is 14 characters, avoiding text truncation in the 320 px three-button strip

## Licensing & Privacy

Licenses of upstream components are listed in [`LICENSES.md`](LICENSES.md). Corresponding source code is provided in this repository for all redistributed GPL components.

Device MAC addresses, node IDs, GPS coordinates, serial logs and local user-directory paths were removed before export. **A final self-check before publishing is recommended**: `git grep -nE "COM[0-9]|22\.[0-9]{4,}|[0-9a-f]{2}(:[0-9a-f]{2}){5}"`.

One known residue: `releases/*.bin` embeds **build-machine workspace compile path strings** (from Arduino core `__FILE__` assertions) — no usernames, device identifiers or location data. The binaries cannot be safely rewritten (it would break the image SHA256 verification). If you need zero traces, delete the `releases/` directory and build from source yourself.
