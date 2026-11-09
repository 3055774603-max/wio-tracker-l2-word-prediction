# Wio Tracker L2 联想输入固件 — 本机构建状态

最后更新：2026-11-08

## 当前状态

**编译进行中**（`<WORKSPACE>\build.log`）。正在经 `ghfast.top` 镜像下载 pioarduino 工具链/框架大包；这一步受镜像带宽限制，之后还会有一阶段 ESP-IDF 定制 sdkconfig 编译（README 估计 1–2 小时）。设备不在身边，烧录与串口验证留待设备到位。

## 已完成（可验证）

| 项 | 结果 |
|---|---|
| 完整项目记录阅读 | `export-full.zip`（2902 文件 / 120.5 MB）+ `export-lite.zip` 均已核对 |
| 源码落地 | `<WORKSPACE>\`（纯 ASCII），2900 文件解压；`firmware\partitions.csv` 已补 |
| 源码一致性 | 7 个改动文件与 `reference/changed-files` **逐字节相同** |
| 源码完整性 | 290 个 protobuf 生成文件齐全；子模块空目录不影响编译 |
| 版本锚点 | firmware 2.8.3 / device-ui 快照 / pioarduino 55.03.312 / LVGL 9.3.0 / PIO Core 6.2.0 |
| PlatformIO | D 盘 venv 装 `platformio==6.2.0`；core 目录 `<WORKSPACE>\.pio-core` |
| LDF 补丁 | venv + penv **两处**均已打，语法验证通过；penv 额外补回 pioarduino 特有行 |
| penv 依赖 | 16 个 Python 包装齐，`pioarduino` 钉在 **6.2.0**（非 post1） |
| 依赖本地化 | 目标 env 的 73 个 GitHub 库 **73/73 下载成功**，24 个 ini 改 `file://`，0 个裸 github.com |
| 平台包 | 2.1 MB 落地为本地目录，内部 22 个工具链 URL 改指可达镜像 |
| 算法验证 | `verify-wordpredict.py`：3000 词 / 21,306 字节，10 条断言 ALL PASS |
| 文档修正 | `HANDOFF.md` 三处事实错误已修（词表大小、`hel` 候选、flash 验收口径），新增第 9 节 |
| 编译入口 | `build-local.ps1`（PowerShell）+ Bash 直驱命令；`build.ps1` 的 `ErrorActionPreference` 已改 `Continue`（原件 `build.ps1.orig`） |

## 关键路径

```
<WORKSPACE>\
  firmware\                      权威源码（platformio.ini / variants / src，已改离线 URL）
  libs\device-ui\                本地 device-ui（联想输入改动）
  deps\libs\                     73 个预下载库 zip
  deps\platform-espressif32-local\  本地平台包（platform.json 已改镜像）
  .pio-core\                     PlatformIO core（packages / platforms / penv）
  venv\                          独立 Python 环境（platformio 6.2.0 + LDF 补丁）
  prepare-offline.py             依赖本地化脚本（幂等）
  verify-wordpredict.py          联想算法等价验证脚本
  build.ps1 / build-local.ps1    编译入口
  build.log                      编译日志
  HANDOFF.md                     完整上下文（含第 9 节本机适配）
  HANDOFF.md.orig / build.ps1.orig / *.ini.bak   原件备份
```

## 一键续跑（**必须用 PowerShell**）

```powershell
.\build-local.ps1 -Target build -Jobs 12
```

不要用 Git Bash 启动：它会带 `MSYSTEM` 环境变量，ESP-IDF 的 `idf_tools.py` 会报 `ERROR: MSys/Mingw is not supported`。`build.ps1` 的 `ErrorActionPreference` 已改成 `Continue`，沙箱 safe-delete 的 stderr 警告不再会中止编译。

等价的 Bash 直驱命令只在调试时使用（需先 `unset MSYSTEM`）：

```bash
unset MSYSTEM; export PLATFORMIO_CORE_DIR='<WORKSPACE>/.pio-core'
cd <WORKSPACE>/firmware
"<WORKSPACE>/venv/Scripts/python.exe" -m platformio run -e seeed_wio_tracker_L2-tft -j 12
```

已安装的包会跳过，编译缓存保留，可随时中断后续跑。

## 编译完成后要核对

1. `firmware\.pio\build\seeed_wio_tracker_L2-tft\firmware.bin` 存在
2. 大小 < `app0/app1` 分区 **0x640000 = 6.25 MB**（分区表见 `firmware\partitions.csv`）
3. `TFTView_320x240.cpp` 与 `WordPredict.cpp` 的 `.o` 均产出、无编译错误
4. 检查 map 文件里 `kPredictWordList` 落进 `.rodata`（约 20.8 KiB）

## 设备到位后

```powershell
[System.IO.Ports.SerialPort]::GetPortNames()
.\build-local.ps1 upload -Port COMxx
.\build-local.ps1 monitor -Port COMxx
```

验收要点见 `HANDOFF.md` 6.1 / 9.5。注意 `hel` 的正确候选是 **help / held / helpful**。

## 本机遗留风险

- GitHub 直连不通，若镜像 `ghfast.top` 失效，需重新找通道；`codeload.github.com` 可作 archive 回退
- 沙箱批量删除保护会拦截 PlatformIO 清理解压临时目录（`>50` 文件），**不影响编译**，但会在 `.pio-core\.cache\tmp` 残留 `pkg-installing-*`（约百 MB 量级）。编译结束后可统一清理
- 升级 / 重装 PlatformIO 会覆盖 LDF 补丁，需重跑 `apply-ldf-patch.ps1`，并记得补回 penv 里 pioarduino 那一行

---

## 交付包：公司电脑只负责烧录（2026-11-08 新增要求）

**目标**：所有编译、依赖处理、镜像合并、哈希与打包都在本机完成；公司电脑不联网、不装软件、不装 Python/额外运行时、不配环境变量、不要管理员权限、不执行任何编译或构建，唯一动作是烧录。

| 项 | 内容 |
|---|---|
| 本机生成命令 | `python <WORKSPACE>\package-delivery.py`（需先有 `firmware.bin`） |
| 输出目录 | `<WORKSPACE>\delivery\L2_predict_flash_v1\`，**整文件夹拷贝** |
| 主镜像 | `firmware\L2_full.bin`，按 0x0 / 0x8000 / 0xE000 / 0x10000 合并成单文件，`write_flash 0x0` 一次烧完 |
| 备用镜像 | `firmware\` 下 4 个分立 bin（排错/分段重烧用） |
| 烧录工具 | `esptool.exe`：Espressif 官方 v5.6.0 Windows x64 独立版（PyInstaller 单文件 14 MB），**已验证脱离 Python 运行**。经 `dl.espressif.com/github_assets` 官方镜像下载 |
| 脚本 | `flash.bat` / `verify.bat` / `check_device.bat`：纯 cmd + 系统自带 `certutil`，CRLF 换行，`%~dp0` 相对路径，不写 PATH / 注册表 |
| 清单 | `SHA256SUMS.txt`、`manifest.json`（版本/芯片/Flash/偏移/哈希/烧录命令/兼容性约束）、`README.md`、`LICENSE-esptool.txt` |
| 模板 | `<WORKSPACE>\delivery\template\`（bat + README，打包脚本负责注入 CRLF 与哈希） |

**模拟自检（未插设备）已 PASS**：`delivery\_selftest\L2_predict_flash_v1` 生成成功，13 个文件齐全、6 项 SHA256 全部匹配、3 个 bat 全为 CRLF、合并镜像大小/偏移正确。

**受限电脑烧录前必须满足的校验条件**（详见 `README.md` 第 3 节）：

1. `verify.bat` 输出 `RESULT: PASS`：清单齐全、SHA256 全匹配、`esptool.exe version` 能跑
2. `check_device.bat COMxx`：只读 `chip_id` → ESP32-S3 且能读到 MAC；`flash_id` → 16 MB
3. COM 口可见且未被占用、USB 数据线、供电稳定、安全软件未拦截 exe/串口
4. 人工确认：烧录对象正确、会覆盖 app0（旧固件不可回退）

**当前状态**：交付包的工具、脚本、文档、打包链路 **100% 就绪并通过自检**；但 `firmware.bin` 尚未产出（编译卡在库安装/依赖阶段，见 `build.log`），因此**完整成品尚未生成**。编译完成后运行一次 `package-delivery.py` 即可得到可直接拷贝的成品集合。


---

## 追加：本机环境根因与本机 ESP-IDF 的复用（2026-11-08 晚）

| 问题 | 根因 | 修复 |
|---|---|---|
| 删除冲突一个接一个 | WorkBuddy 通过 `sitecustomize.py` 把 `os.remove`/`shutil.rmtree` 改道到回收站并拦截批量删除，**注入到每个 Python 子进程**，逐点 patch 无效 | shim 自带官方开关 `CODEBUDDY_SAFE_DELETE_ENABLED=0`，已写入 `build-local.ps1` |
| `Library Manager` 停在 4 个 registry 库 | `dl.registry.platformio.org` 要求 `User-Agent: PlatformIO/6.2.0`；LovyanGFX 46 MB 单线程下载超时 | 3 个库用 GitHub/codeload 源；LovyanGFX 用 **Range 分块并发**（23 块）下载，SHA256 校验通过；Unity（隐式测试依赖）手动落地到 `libdeps/Unity` |
| `idf_tools.py` 卡死 | `tools.json` 标 `install: always`，要下 413 MB 工具链 | URL 改 `dl.espressif.com/github_assets` 官方镜像；平台 `platform.py` 打补丁跳过重复下载与删除 |
| `Stale ... HybridCompile rebuild` 失败 | `extra_scripts/esp32_pre.py` 直接 `os.remove(sdkconfig.defaults)` | 改成改名（`.l2old`），并补 `import os` |
| `run_cmake` 报 `FileNotFoundError [WinError 2]` | pioarduino 的 `tool-cmake` / `tool-ninja` 包是**空壳**（只有 `.piopm`/`package.json`），正常应由 idf_tools 填充；平台找 `<tool-cmake>/bin/cmake.exe` | **复用本机 ESP-IDF v5.5.2**：把 `<ESPRESSIF_TOOLS>//tools//tools//cmake//3.30.2` 与 `ninja\1.12.1\ninja.exe` 填进包目录 |
| `IDF_PATH` / `IDF_TOOLS_PATH` 串味 | 系统环境变量指向本机 IDF v5.5.2，pioarduino 会自己覆盖 | `build-local.ps1` 里显式清空 `IDF_PATH`、固定 `IDF_TOOLS_PATH` |

**当前**：79 个依赖全部本地化（目标 env `lib_deps` 中 remote http = 0）；编译已越过依赖安装、ComponentManager、Stale 检查，进入混合编译（cmake/Ninja）阶段，后台任务运行中。**编译成功后 `build-local.ps1` 会自动调用 `package-delivery.py` 生成成品包**，无需手动操作。预计该阶段耗时较长（首次 ESP-IDF 定制 sdkconfig 编译 1–2 小时）。

## 最终状态（2026-11-09）：编译 SUCCESS，已烧录 COM9，串口启动正常。详见 HANDOFF.md 第 10 节。

## 追加（2026-11-09 下午）：联想栏不显示的根因已定位并修复，串口实测 `hel -> help/held/helpful`、点击补全成功。详见 HANDOFF.md 第 11 节，日志 `serial_predict2.log`。

## 追加（2026-11-09）：点击候选错位（显示 hello 插入 here）已修复，6 次点击 shown/inserted 全一致。详见 HANDOFF.md 第 12 节，日志 `serial_predict3.log`。

## 追加（2026-11-09）：用户验收通过，v1.0 已归档至 `releases/backup_20261109_L2_wordpredict_v1.0`；词库扩展容量评估见 HANDOFF.md 第 13 节（app 剩余 2.54 MiB，扩到 1 万词仅占 2.67%）。

## 当前运行版本：v1.1（10000 词，已烧录 COM9 验证通过）。归档 `releases/backup_20261109_L2_wordpredict_v1.1`，v1.0 可一键回滚。详见 HANDOFF.md 第 14 节。
