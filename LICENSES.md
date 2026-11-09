# 许可证与署名

本仓库是**在多个上游开源项目之上做修改**的产物。请分别遵守各组件许可证。

| 组件 | 版本 / 来源 | 许可证 | 许可证文件 |
|---|---|---|---|
| Meshtastic firmware | v2.8.3，`meshtastic/firmware` | **GPL-3.0** | `firmware/LICENSE` |
| device-ui | `meshtastic/device-ui`（本地 fork） | `library.json` 声明 `GPL-3.0 AND BSD-3-Clause AND Apache-2.0 AND MIT` | `libs/device-ui/LICENSE` |
| LVGL | 9.3.0（构建时由 PlatformIO 拉取，未打包） | MIT | 上游仓库 |
| google-10000-english | `first20hours/google-10000-english`（10k + 20k 词表） | MIT | 上游仓库 |
| PlatformIO Core | 6.2.0（`patches/piolib-ldf.patch` 的原始文件来源） | Apache-2.0 | 上游仓库 |
| pioarduino / arduino-esp32 / ESP-IDF | 构建时下载，未打包 | 各自上游许可证 | 上游仓库 |
| esptool | 烧录工具，未打包 | 上游许可证 | 上游仓库 |

## 本项目新增内容

- `libs/device-ui/include/graphics/common/WordPredict.h`
- `libs/device-ui/source/graphics/common/WordPredict.cpp`
- `libs/device-ui/source/graphics/common/predict_wordlist.inc`
- `libs/device-ui/source/graphics/TFT/TFTView_320x240.cpp` / `.h` 中的联想输入改动
- `firmware/partitions.csv`
- `patches/`、`scripts/`、`wordlist/`、`docs/` 中的原创内容

这些改动建立在 GPL-3.0 的 device-ui / firmware 之上，**随对应上游许可证一同分发**。

## 二进制分发说明

`releases/` 下的 `.bin` 是包含 GPL-3.0 组件的编译产物。按 GPL-3.0 要求，分发二进制时必须同时提供对应完整源码 —— 本仓库已包含 `firmware/`、`libs/device-ui/` 及构建脚本，满足该条件。若只单独转发 `releases/` 里的 bin，请附上本仓库地址。

## 未打包的第三方二进制

以下内容**有意不包含**在本仓库，避免许可证混杂与体积膨胀：

- PlatformIO 工具链、ESP-IDF 框架、73 个 Arduino 库 zip（构建时按 `platformio.ini` 拉取）
- esptool 独立可执行文件、`boot_app0.bin` 之外的烧录工具
- device-ui 的 `maps/*.zip` 第三方地图瓦片数据
- 带符号 elf、串口日志、Python 虚拟环境

需要它们请从各自上游获取。
