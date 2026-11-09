# Wio Tracker L2 联想输入固件 — 编译指南（换机版）

本包是把「已改好的源码 + 全部环境坑的解决方案」打包出来，供你在另一台没有安全软件干扰的电脑上完成编译。

---

## 0. 这个包解决了什么问题

原机器（公司电脑）上有 **360安全卫士 + 联想电脑管家 + Windows Defender** 三套实时文件过滤，编译器每个进程只拿到 33% CPU，16 个线程里 10 个在闲置，编译速率只有 ~4 个目标文件/分钟。你换机后预计能快 3–10 倍。

代码本身**已经编译验证过**（`WordPredict.cpp` 已成功产出目标文件），剩下的只是第三方库的批量编译。

---

## 1. 目录结构

```
<root>\
  build.ps1                 编译/烧录脚本
  apply-ldf-patch.ps1       给 PlatformIO 打依赖扫描补丁（必做）
  partitions.csv            必须放在 firmware\ 下
  README.md                 本文件
  HANDOFF.md                完整上下文记忆（改动明细、所有坑）
  changed-files\            改动的完整文件副本（推荐用这个，不用打补丁）
    firmware\
      platformio.ini
      variants\esp32s3\seeed_wio_tracker_L2\platformio.ini
    device-ui\
      include\graphics\common\WordPredict.h
      include\graphics\view\TFT\TFTView_320x240.h
      source\graphics\common\WordPredict.cpp
      source\graphics\common\predict_wordlist.inc
      source\graphics\TFT\TFTView_320x240.cpp
  patches\                  git diff（如果你更习惯 git apply）
    firmware.diff
    device-ui.diff
  platformio-patch\piolib.py  打过补丁的 PlatformIO 依赖扫描实现
```

---

## 2. 先决条件

- Windows + PowerShell
- Python 3.9+（`python` 在 PATH 里）
- **网络**：首次编译会下载 pioarduino 平台和工具链，约 6–8 GB
- **路径必须是纯 ASCII**（不能有中文）。放在例如 `<WORKSPACE>\` 或 `D:\meshtastic-l2\`
- 磁盘至少 30 GB 空闲

---

## 3. 准备源码

### 3.1 拉取两个仓库（版本必须一致）

```powershell
cd <WORKSPACE>
git clone https://github.com/meshtastic/firmware.git firmware
git -C firmware checkout 9bcf0f776edabb3b2447db323323cf2c49835452

mkdir libs
git clone https://github.com/meshtastic/device-ui.git libs\device-ui
git -C libs\device-ui checkout a5b80d4d5708d0563ea9e0c0277dc8984e2fb952
```

> 为什么 `device-ui` 要放在 `libs\device-ui`？
> `firmware\platformio.ini` 里写的是 `lib_extra_dirs = ../libs`，PlatformIO 相对于项目目录解析它，也就是 `<root>\libs`。放错位置会报找不到 `meshtastic-device-ui`。

### 3.2 覆盖改动文件

把 `changed-files\firmware\*` 覆盖到 `firmware\`，把 `changed-files\device-ui\*` 覆盖到 `libs\device-ui\`。

```powershell
# 在本包根目录执行
Copy-Item changed-files\firmware\platformio.ini firmware\platformio.ini -Force
Copy-Item changed-files\firmware\variants\esp32s3\seeed_wio_tracker_L2\platformio.ini `
          firmware\variants\esp32s3\seeed_wio_tracker_L2\platformio.ini -Force

Copy-Item changed-files\device-ui\include\graphics\common\WordPredict.h `
          libs\device-ui\include\graphics\common\ -Force
Copy-Item changed-files\device-ui\include\graphics\view\TFT\TFTView_320x240.h `
          libs\device-ui\include\graphics\view\TFT\ -Force
Copy-Item changed-files\device-ui\source\graphics\common\WordPredict.cpp `
          libs\device-ui\source\graphics\common\ -Force
Copy-Item changed-files\device-ui\source\graphics\common\predict_wordlist.inc `
          libs\device-ui\source\graphics\common\ -Force
Copy-Item changed-files\device-ui\source\graphics\TFT\TFTView_320x240.cpp `
          libs\device-ui\source\graphics\TFT\ -Force
```

### 3.3 放 partitions.csv

```powershell
Copy-Item partitions.csv firmware\partitions.csv -Force
```

> 缺这个文件会让 ESP-IDF 那一半的混合编译直接失败（`Partition table CSV file ... not found`），而且报错完全不指向根因。

---

## 4. 安装 PlatformIO 并打补丁

```powershell
# PlatformIO Core 必须 >= 6.2.0（pioarduino 平台要求）
python -m pip install "platformio>=6.2.0"
python -m platformio --version

# 打依赖扫描补丁（不做这步会在 "Scanning dependencies..." 卡死）
.\apply-ldf-patch.ps1
```

补丁做了什么（详见 `HANDOFF.md` 第 4 节）：给 PlatformIO 的 `piolib.py` 加记忆化、集合查找、索引式工作队列和 realpath 缓存。**扫描从"永不结束"变成约 11 分钟，依赖结果完全一致。**

---

## 5. 编译

```powershell
.\build.ps1
```

首次运行会：
1. 下载 pioarduino espressif32 平台（55.3.312）
2. **阶段一**：从源码编译定制 sdkconfig 的 ESP-IDF —— 这一步很慢（1–2 小时），成果会缓存到
   `<core>\packages\framework-arduinoespressif32-libs\esp32s3\{lib,ld,sdkconfig}`（175 个 .a）
3. **阶段二**：编译 Arduino + Meshtastic 应用层 + device-ui

只要 `memory_type=qio_opi spiram=oct` 这个 cache key 不变，阶段一后续都会跳过。

产物：`firmware\.pio\build\seeed_wio_tracker_L2-tft\firmware.bin`

> **如果卡在 `Scanning dependencies...` 超过 20 分钟且磁盘无读取**：补丁没生效。
> 重跑 `.\apply-ldf-patch.ps1`，并确认输出里显示 "patched: ..."。
> 调试时可设 `$env:L2_LDF_TRACE=1`，补丁会逐库打印耗时。

---

## 6. 烧录

```powershell
# 先确认端口
[System.IO.Ports.SerialPort]::GetPortNames()

.\build.ps1 upload -Port COM52
```

烧录后看日志：

```powershell
.\build.ps1 monitor -Port COM52
```

---

## 7. 编译失败时的排查顺序

| 症状 | 原因 | 处理 |
|---|---|---|
| `Scanning dependencies...` 卡死，CPU 100%，磁盘 0 读取 | piolib 补丁未生效 | 重跑 `apply-ldf-patch.ps1` |
| `Partition table CSV file ... not found` | 缺 `firmware\partitions.csv` | 从本包复制过去 |
| 平台在编译中途被"卸载"，随后 `.sconsign*.tmp` FileNotFoundError | penv 里装的是 `pioarduino==6.2.0.post1`（被 semver 当成预发布版 < 6.2.0） | `pip install "pioarduino==6.2.0"` |
| `lvgl.h: No such file or directory` | `lib_extra_dirs` 引入的库不会自动安装它 `library.json` 里的依赖 | `platformio.ini` 的 `[device-ui_base] lib_deps` 已显式列出 lvgl/libdeflate/PNGdec（本包已含） |
| `LovyanGFX.hpp: No such file or directory` | device-ui 的 `library.json` 没声明 LovyanGFX，LDF 不给它加 include 路径 | variant 的 `build_flags` 里已用 `-I${platformio.libdeps_dir}/.../LovyanGFX/src`（本包已含）。**不要**改回写进 library.json，那会把扫描时间炸到 50+ 分钟 |
| 路径含中文时 `cmake` 崩溃 `0xE06D7363` 或 `ld` 报 `cannot find crt0.o` | 工具链对非 ASCII 路径无解 | 项目必须放在纯英文路径 |

---

## 8. 编完之后要做什么

1. 把 `firmware\.pio\build\seeed_wio_tracker_L2-tft\firmware.bin` 带回
2. 或者直接在自己电脑上烧录，然后把串口日志（`build.ps1 monitor` 的输出）贴回来
3. 重点看日志里有没有：启动横幅、`[WordPredict]` 相关输出、崩溃/重启循环
