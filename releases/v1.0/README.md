# 固件 v1.0

烧录命令见 `flash.bat`（需自备 `esptool`，官方独立版或 `pip install esptool`）。

| 文件 | 偏移 |
|---|---|
| `bootloader.bin` | 0x0 |
| `partitions.bin` | 0x8000 |
| `boot_app0.bin` | 0xe000 |
| `firmware-...-2.8.3.bin` | 0x10000 |
| `littlefs-...-2.8.3.bin` | 0xc90000 |
| `firmware-...factory.bin` | 0x0（合并镜像，单文件烧录） |

**必须 `--flash_mode dio`**；board json 里的 `qio` 会导致 TG0WDT boot loop。详见 `docs/HANDOFF.md` 第 10.3 节。
