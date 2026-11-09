# L2 联想输入固件 — 稳定版 v1.0（2026-11-09）

本目录是**已实测通过的可回滚基线**。用户确认「很成功」后归档，勿在此目录内修改文件。

## 版本信息

| 项 | 值 |
|---|---|
| 版本 | `v1.0` / `backup_20261109_L2_wordpredict_v1.0` |
| 源码基线 | meshtastic/firmware v2.8.3 + device-ui + WordPredict |
| 目标环境 | `seeed_wio_tracker_L2-tft`（ESP32-S3, 16MB Flash） |
| 编译 | PlatformIO 6.2.0 + pioarduino 55.03.312，`BUILD_EXIT=0` |
| 功能状态 | 候选栏显示正常；点击候选「显示=点击=插入」6 次实测全一致；补全带空格；无 boot loop |
| 词表 | 3000 词，`.rodata` 21,307 B（20.8 KiB） |
| 已知项 | 固件含 `WordPredict:` 诊断 WARN 日志（不影响 UI）；`hel` → help/held/helpful，`hell` → hello |

## 固件清单与偏移

| 文件 | 偏移 | 大小 |
|---|---|---|
| `firmware/bootloader.bin` | 0x0 | 19,968 B |
| `firmware/partitions.bin` | 0x8000 | 3,072 B |
| `firmware/boot_app0.bin` | 0xe000 | 8,192 B |
| `firmware/firmware-seeed_wio_tracker_L2-tft-2.8.3.bin` | 0x10000 | 3,891,696 B |
| `firmware/littlefs-seeed_wio_tracker_L2-tft-2.8.3.bin` | 0xc90000 | 3,538,944 B |
| `firmware/firmware-seeed_wio_tracker_L2-tft-2.8.3.factory.bin` | 0x0 (合并镜像) | 3,957,232 B |

单文件烧录可用 `firmware/firmware-seeed_wio_tracker_L2-tft-2.8.3.factory.bin`（`write_flash 0x0`）。

## 烧录（本机直连 COM9）

```
flash.bat COM9
```

等价命令（注意：**必须 `--flash_mode dio`**，board json 的 qio 会导致 TG0WDT boot loop）：

```
esptool.exe --chip esp32s3 --port COM9 --baud 921600 --before default_reset --after hard_reset write_flash --flash_mode dio --flash_freq 80m --flash_size 16MB 0x0 firmware\bootloader.bin 0x8000 firmware\partitions.bin 0xe000 firmware\boot_app0.bin 0x10000 firmware\firmware-seeed_wio_tracker_L2-tft-2.8.3.bin 0xc90000 firmware\littlefs-seeed_wio_tracker_L2-tft-2.8.3.bin
```

## 分区与容量

| 分区 | 偏移 | 大小 | 当前占用 |
|---|---|---|---|
| `app0/app1` | 0x10000 / 0x650000 | 各 0x640000 (6.25 MiB) | app 3,891,696 B（59.4%），剩余 2,661,904 B |
| `spiffs` | 0xc90000 | 0x360000 (3.375 MiB) | littlefs 3,538,944 B（**100% 占满**） |

词表放在 app 的 `.rodata`（DROM，经 flash MMU 映射，不占 RAM）。详见 `HANDOFF.md` 第 13 节。

## 目录说明

- `firmware/`：5 个烧录分段 + 1 个合并镜像
- `src_snapshot/`：本版对应的 5 个改动源码（可复现编译）
- `debug/`：带符号 elf，用于崩溃回溯
- `SHA256SUMS.txt`：所有文件的 SHA256（`certutil -hashfile <file> SHA256` 校验）
- `flash.bat`：一键回滚

## 完整性校验

`18a5c36aa3a32ecb...`  debug/firmware-seeed_wio_tracker_L2-tft-2.8.3.elf
`f94c5d786a7a8fab...`  firmware/boot_app0.bin
`84bb365666003b05...`  firmware/bootloader.bin
`b4e11f3364460df8...`  firmware/firmware-seeed_wio_tracker_L2-tft-2.8.3.bin
`edb4ba5c7673d5a2...`  firmware/firmware-seeed_wio_tracker_L2-tft-2.8.3.factory.bin
`249e11a852123404...`  firmware/littlefs-seeed_wio_tracker_L2-tft-2.8.3.bin
`bd0f7954aca2ef7d...`  firmware/partitions.bin
`dcd4ac2c92c151c0...`  src_snapshot/TFTView_320x240.cpp
`bd46bf07ee7a434b...`  src_snapshot/TFTView_320x240.h
`0c5f42821f324522...`  src_snapshot/WordPredict.cpp
`7ae12c361c178812...`  src_snapshot/WordPredict.h
`2b2d49186dd1dc6c...`  src_snapshot/predict_wordlist.inc

生成时间：2026-11-09T12:03:21.775146+08:00
