# Wio Tracker L2 — 英文联想输入固件

给 **Seeed Wio Tracker L2**（ESP32-S3、16 MB Flash、320×240 TFT）的 Meshtastic device-ui 虚拟键盘加英文单词预测：输入前缀，键盘上方出现 3 个候选词，点击即补全并追加空格。

基于 Meshtastic firmware v2.8.3 + device-ui，词库 10000 词（按词频排序），编译与烧录均在 Windows 上完成并实测通过。

## 关键结果

| 项 | 值 |
|---|---|
| 目标环境 | `seeed_wio_tracker_L2-tft`，ESP32-S3，16 MB Flash |
| 词库 | 10000 词，`.flash.rodata` 76,015 B（74.2 KiB） |
| 候选 | 3 个；`hel` → `help / held / helpful`，`here` → `herein / hereby` |
| 固件 | app 3,946,400 B（分区 6.25 MiB，占用 60.2%） |
| 实测 | 31 次候选显示、点击「显示＝插入」全部一致、0 boot loop |
| 版本 | v1.0（3000 词稳定版）/ v1.1（10000 词，当前版） |

## 目录

| 路径 | 内容 |
|---|---|
| `firmware/` | Meshtastic firmware 源码（已还原上游 `platformio.ini`，去掉 `.pio/` 构建缓存）＋本项目新增的 `partitions.csv` |
| `libs/device-ui/` | 改动后的 device-ui：`WordPredict.h/.cpp`、`predict_wordlist.inc`、`TFTView_320x240.*` |
| `patches/` | 相对上游的改动 diff 与 PlatformIO LDF 补丁 |
| `scripts/` | 构建、离线依赖、打包、算法验证脚本 |
| `wordlist/` | 词频语料、v1.0 原词表、可复现生成脚本 |
| `releases/` | v1.0 / v1.1 的烧录镜像与一键烧录脚本 |
| `docs/` | 完整交接文档、构建状态、发布说明、内存分析 |
| `CHANGELOG.md` | 版本台账 |

**未打包**：PlatformIO 工具链（约 10 GB）、Python 虚拟环境、第三方依赖 zip、编译缓存、串口日志（含设备隐私）、带符号 elf、esptool 二进制、device-ui 的第三方地图瓦片包。

## 快速开始

### 1. 构建

```
python -m venv .venv
.venv/Scripts/pip install platformio==6.2.0
```

按 `patches/README.md` 打 LDF 补丁（venv 与 PlatformIO 的 penv 两处都要）。然后执行 `scripts/build.ps1`，或按 `scripts/README.md` 的说明配置离线依赖后构建。

> `scripts/` 里的脚本记录了构建机的环境适配流程，含 `<WORKSPACE>` / `<ESPRESSIF_TOOLS>` / `<USER_HOME>` 占位符，clone 后按你的路径替换。文档里的同类占位符同理。

### 2. 烧录

`releases/v1.1/flash.bat COM9`（需自备 `esptool`）。

**必须用 `--flash_mode dio`**：board json 写的是 `qio`，但 PlatformIO 生成镜像用的是 `dio`；按 `qio` 烧会 `TG0WDT_SYS_RST` 反复重启。详见 `docs/HANDOFF.md` 第 10.3 节。

### 3. 复现词库

```
python wordlist/build_wordlist.py
```

从 `wordlist/` 的两份语料 + v1.0 原词表生成 10000 词 `predict_wordlist.inc`，前 3000 词字节级不变，保证已验收候选零回退。

### 4. 验收

进消息输入界面敲 `hel`，候选栏应出现 `help / held / helpful`；点击后补全并带空格。敲 `here` 应出现 `herein / hereby`（10000 词版新增覆盖）。

## 已知项

- 固件含 `WordPredict:` 诊断日志（每次按键约 2 条 WARN），不影响 UI；需要安静版可去掉后重编
- `kMaxCandidates = 3` 未改；词库扩展只提升覆盖范围，不增加候选个数
- `hel` 出 `help / held / helpful`，`hello` 排第 4（词频顺序）
- 词表最长 14 字符，避免 320 px 三按钮栏文字截断

## 合规与隐私

各上游组件的许可证见 [`LICENSES.md`](LICENSES.md)。重新分发 GPL 组件时本仓库已同时提供对应源码。

导出时已清除设备 MAC、节点 ID、GPS 坐标、串口日志和本机用户目录路径。**首次公开前建议再自查一次**：`git grep -nE "COM[0-9]|22\.[0-9]{4,}|[0-9a-f]{2}(:[0-9a-f]{2}){5}"`。

一个已知残留：`releases/*.bin` 内嵌了**构建机工作区的编译路径字符串**（来自 Arduino core 的 `__FILE__` 断言信息），不含用户名、设备标识或位置信息。二进制无法安全改写（会破坏镜像 SHA256 校验）。若要求完全无痕，删除 `releases/` 目录、只保留源码自行编译即可。
