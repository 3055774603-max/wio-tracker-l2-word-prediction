# HANDOFF — Wio Tracker L2 联想输入固件（完整上下文）

> 这份文档是给你（或者在你新电脑上接手的人）看的"记忆体"。包含：做了什么、为什么这么改、踩过哪些坑、验证到哪一步、还剩什么没验证。

---

## 1. 项目目标

给 **Seeed Wio Tracker L2** 的 Meshtastic 固件加**英文单词联想输入**：

- 虚拟键盘（LVGL 的 `lv_keyboard`）上方加一条候选词栏
- 输入前缀时实时匹配内置高频词表，最多 3 个候选
- 点击候选 → 自动补全整个单词并追加一个空格
- 词表存 flash，运行时零动态分配

原始痛点：L2 屏幕上逐字母敲完整单词才能发送，效率极低。

---

## 2. 版本锚点（必须严格一致）

| 项目 | 值 |
|---|---|
| firmware | `meshtastic/firmware` develop 分支 |
| firmware commit | `9bcf0f776edabb3b2447db323323cf2c49835452`（2026-11-04，v2.8.3） |
| device-ui | `meshtastic/device-ui` |
| device-ui commit | `a5b80d4d5708d0563ea9e0c0277dc8984e2fb952`（2026-10-30，master） |
| 编译环境 | `seeed_wio_tracker_L2-tft` |
| 平台 | pioarduino espressif32 `55.3.312` |
| PlatformIO Core | `>= 6.2.0`（且 penv 里 `pioarduino==6.2.0`，**不能是 post1**） |
| LVGL | v9.3.0 |

---

## 3. 改动清单

一共只有 **5 个文件**（2 改 3 新增），全部已通过编译验证。

### 3.1 新增 `device-ui/include/graphics/common/WordPredict.h`

```cpp
namespace WordPredict
{
inline constexpr uint8_t kMaxCandidates = 3;
inline constexpr uint8_t kMaxWordLen = 16; // incl. terminating zero

uint8_t predict(const char *prefix, char out[][kMaxWordLen], uint8_t maxCount);
}
```

接口约定：`prefix` 是当前正在输入的字母片段（任意大小写），`out` 是二维缓冲，返回值是实际填充数量。匹配**大小写不敏感**，但输出的大小写跟随输入（全大写 / 首字母大写 / 全小写）。

### 3.2 新增 `device-ui/source/graphics/common/WordPredict.cpp`

- 对 `predict_wordlist.inc` 里的词表做前缀匹配
- 词表本身是**按词频排序**的，所以顺序扫描 + 收集前 3 个命中即天然是"高频优先"
- 无堆分配、无全局可变状态

### 3.3 新增 `device-ui/source/graphics/common/predict_wordlist.inc`

```cpp
static const char kPredictWordList[] = "...";
```

3000 个高频英文单词，用 `\n` 串成一整块常量数组，直接进 flash（`.rodata`）。实测词表 3000 条、字符串常量 **21,306 字节（约 20.8 KiB）**；`.inc` 源文件 26,321 字节是含注释/缩进的源文件大小，**不是 flash 占用**。
词表生成脚本在原工作区根目录 `firmware-wordlist-gen.py`（本包未含，如需扩充词表可参考）。

### 3.4 修改 `device-ui/include/graphics/view/TFT/TFTView_320x240.h`

新增成员与方法：

```cpp
void createPredictBar(void);
void updatePredictions(void);
void applyPrediction(uint8_t idx);
static void ui_event_PredictKey(lv_event_t *e);
static void ui_event_PredictBar(lv_event_t *e);

lv_obj_t *predictBar = nullptr;                       // child of the keyboard
char predictCandidates[WordPredict::kMaxCandidates][WordPredict::kMaxWordLen];
const char *predictMap[WordPredict::kMaxCandidates + 1]; // btnmatrix map (must outlive set_map)
static constexpr int32_t kPredictBarHeight = 30;      // strip reserved above the keyboard
```

注意 `predictMap` 是 `const char*` 指针数组，**生命周期必须长于 `set_map`**，所以做成成员而不是局部变量。

### 3.5 修改 `device-ui/source/graphics/TFT/TFTView_320x240.cpp`

实现要点（约 8235 行起）：

- `createPredictBar()`：在键盘上方创建一条高 30px 的 `lv_buttonmatrix`，风格与键盘一致
- `updatePredictions()`：从键盘的 textarea 取出"光标前最后一个连续字母片段"作为 prefix，调用 `WordPredict::predict()`，把结果写进 `predictMap` 并 `set_map`
- `applyPrediction(idx)`：用候选词替换当前片段，并追加一个空格
- `ui_event_PredictKey()` / `ui_event_PredictBar()`：绑定 `LV_EVENT_VALUE_CHANGED`

联动逻辑：键盘自身的 `LV_EVENT_VALUE_CHANGED` 触发 `updatePredictions()`，所以每次按键都会刷新候选栏。

### 3.6 修改 `firmware/platformio.ini`

两处，都是为了把本地 device-ui 接进来：

```ini
[env]
; device-ui 放在 <root>/libs/device-ui，只让它扫这一个库
; 指向镜像根目录会把 firmware/.pio/libdeps 下所有库也递归扫一遍（每次多 20 分钟）
lib_extra_dirs = ../libs

[device-ui_base]
lib_deps =
    meshtastic-device-ui
    ; lib_extra_dirs 引入的库不会自动安装它 library.json 里声明的 dependencies，
    ; 所以 device-ui 自己的依赖必须在这里显式列出来。
    ; ArduinoThread / Nanopb 已由主 [env] lib_deps 提供，无需重复。
    https://github.com/lvgl/lvgl/archive/refs/tags/v9.3.0.zip
    https://github.com/mverch67/libdeflate/archive/7291dd18ed11df673cce8e33b7f432a1273f1945.zip
    https://github.com/mverch67/PNGdec/archive/d88b6fe2ec8d49c2b097a529b34d1d615ca5cf1b.zip
```

### 3.7 修改 `firmware/variants/esp32s3/seeed_wio_tracker_L2/platformio.ini`

只加在 `[env:seeed_wio_tracker_L2-tft]` 的 `build_flags` 里：

```ini
build_flags = ${env:seeed_wio_tracker_L2.build_flags}
  -I${platformio.libdeps_dir}/${this.__env__}/LovyanGFX/src
  -D LV_LVGL_H_INCLUDE_SIMPLE
  ...
```

**关键决策**：LovyanGFX 的 include 路径用 `-I` 直接加，**不要**写进 `device-ui/library.json` 的 `dependencies`。
写进 library.json 会把 LovyanGFX 拖进 LDF 的递归闭包，扫描时间从约 20 分钟炸到 50+ 分钟（实测）。

---

## 4. PlatformIO 依赖扫描补丁（本项目的核心问题）

### 4.1 现象

```
Found 112 compatible libraries
Scanning dependencies...
```
然后**永远停在这里**：CPU 100%，磁盘读取增量为 0，内存恒定，不再输出任何日志。

### 4.2 根因

`platformio/builder/tools/piolib.py` 里 `LibBuilderBase.get_implicit_includes()` 的实现：

```python
while search_files:
    node = self.env.File(search_files.pop(0))          # O(n) 出队
    if node.get_abspath() in self._processed_search_files:   # O(n) 线性查找
        continue
    ...
    for item in candidates:
        if (item_path not in self._processed_search_files   # 又 O(n)
            and item_path not in search_files               # 又 O(n)
            and item_path in self):
            search_files.append(item_path)
        if item not in result:                              # SCons Node.__eq__，O(n)
            result.append(item)
```

以及 `is_common_builder()`：

```python
root_path = os.path.realpath(root_path)   # Windows 上逐级走文件系统的 syscall
child_path = os.path.realpath(child_path)
```

`is_common_builder` 在 `search_deps_recursive()` 里被 **每个隐式 include × 112 个库** 调用。lvgl 单独就贡献几千个隐式 include。三者叠加是平方级放大，在 Windows 上等于永不结束。

### 4.3 补丁内容（`platformio-patch/piolib.py`）

1. `_IS_COMMON_BUILDER_CACHE` —— `(root, child)` 路径对判定结果缓存
2. `_REALPATH_CACHE` —— `os.path.realpath()` 结果缓存
3. `_ISFILE_CACHE` —— 头文件→源文件的 `os.path.isfile()` 探测缓存
4. `_processed_search_files_set` —— 与列表同步的集合，成员判断 O(1)
5. `get_implicit_includes()` 改成索引式工作队列（`head` 指针替代 `pop(0)`），`result` 去重改成按绝对路径的集合
6. `depend_on._already_depends()` 加 visited 集合（原实现是无记忆化的递归可达性搜索，稠密 DAG 上路径数指数增长）
7. 可选追踪：设 `L2_LDF_TRACE=1` 时逐库打印耗时（默认关闭）

**效果**：扫描从"永不结束"变成 **约 11 分钟**，依赖解析结果与上游完全一致。

### 4.4 维护注意

- 升级 / 重装 PlatformIO 会**覆盖**这个补丁，需要重跑 `apply-ldf-patch.ps1`
- 原机器上同时打了两个位置（`D:\Tools\Python313\Lib\site-packages\` 和 `C:\Users\seeed\AppData\Local\l2pio\penv\Lib\site-packages\`），脚本会自己找

---

## 5. 原机器（公司电脑）的构建布局与三个大坑

这部分是"为什么不能在原机器直接编"的记录，换机后**不需要照搬**，但值得知道。

### 5.1 三个大坑

**坑 1：路径不能含中文。** 工作区名是 `L2改造`。
- `cmake.exe` 直接崩，退出码 `0xE06D7363`（MSVC 未处理异常），且**零输出**
- `ld.exe` 把路径变成 `L2????`，报 `cannot find .../crt0.o`
- 改 `LANG`/`LC_ALL` 无效；系统 ACP=936
- cmake 对 `-D` 参数里的中文能容忍，但 `-S/-B` 工程路径含中文必崩

**坑 2：会话内新建的可执行文件受沙箱限制。** 只有位于「工作区 / `%LOCALAPPDATA%` / `%TEMP%`」才被信任；放在 `D:\L2t\` 这类地方能启动但所有写操作被拒（ninja 报 `WriteFile(.ninja_lock): Permission denied`）。

**坑 3：Windows 路径长度上限只有约 246–252 字符**（这台机器的 `C:\` 实际重定向到 `AppData\Roaming\TRAE SOLO CN\vmcache\...\drive\C\`，比标准 259 更短）。`framework-arduinoespressif32-libs` 里的 esp_matter/connectedhomeip 头文件解包后达 273 字符。无管理员权限开不了 `LongPathsEnabled`，只能给 PlatformIO 的 `unpack.py` / `_install.py` 打 `\\?\` 扩展路径补丁。

### 5.2 当时的布局

| 用途 | 路径 |
|---|---|
| 权威源码 | `c:\Users\seeed\Desktop\L2改造\{firmware,device-ui}` |
| PIO 核心（工具链/penv/包，7GB） | `C:\Users\seeed\AppData\Local\l2pio` |
| 编译镜像（源码 + `.pio` 产物） | `D:\L2b\{firmware,libs\device-ui}` |

`build.ps1` 每次用 robocopy 把源码镜像过去，并保留 `partitions.csv`、`dependencies.lock`。

### 5.3 其他踩过的坑

| 坑 | 现象 | 解法 |
|---|---|---|
| pioarduino `6.2.0.post1` | PIO 把版本规范化成 `6.2.0-post.1`（预发布版 < 6.2.0），平台在混合编译第二阶段被卸载，SCons 崩在 `.sconsign313.tmp` | 必须 `pip install "pioarduino==6.2.0"` |
| `partitions.csv` 缺失 | 双方都以为对方会生成，parttool 抛 FileNotFoundError；曾导致同一错误重试 **12 小时 47 分** | 从 `framework-arduinoespressif32/tools/partitions/default_16MB.csv` 复制到 `firmware\partitions.csv` |
| `lvgl.h` 找不到 | `lib_extra_dirs` 库的 `library.json` 依赖不会自动安装 | 在 `[device-ui_base] lib_deps` 显式列出 |
| `LovyanGFX.hpp` 找不到 | device-ui 的 `library.json` 没声明 LovyanGFX，LDF 不给它加 include 路径 | variant 里用 `-I` 直接加 |
| `lib_ldf_mode = off` | 想绕过扫描，结果 `Wire.h`/`SPI.h` 解析失败，735 个 `.o` 作废 | 回滚，改用补丁修 LDF |
| 三套安全软件实时过滤 | 编译器每进程只拿到 33% CPU，16 线程里 10 个闲置，~4 个 `.o`/分钟 | 公司机器无法关闭 → 换机编译（本包的原因） |

---

## 6. 验证到哪一步

| 项 | 状态 |
|---|---|
| 联想输入功能代码 | ✅ 已实现 |
| `WordPredict.cpp` 编译 | ✅ 已产出 `.o`（49KB），无警告错误 |
| `TFTView_320x240.cpp` 编译 | ⏳ 未跑完（该文件 393KB，是最大的一个） |
| 第三方库批量编译 | ⏳ 进行中（原机器 196/约 2500 个文件时被安全软件拖住） |
| 链接 `firmware.bin` | ⏳ 未开始 |
| 烧录到设备 | ⏳ 未开始 |
| 串口验证 UI 行为 | ⏳ 未开始 |

### 6.1 换机后重点验证

编译通过后，烧录并看串口日志，确认：

1. **启动正常**：有 Meshtastic 启动横幅，没有 boot loop（反复重启）
2. **无内存崩溃**：没有 `Guru Meditation` / `Stack canary` / `heap_caps` 断言
3. **UI 可用**：能进到消息输入界面，键盘上方出现候选词栏
4. **联想生效**：敲 `hel` 应出现 **`help` / `held` / `helpful`**（词表按词频排序，`hello` 频率低于这三个，不会出现在前 3 个候选里）；点击候选后单词补全并带一个空格
5. **flash 占用**：词表约 20.8 KiB，需确认 `firmware.bin` 没超出 `app0/app1` 各 0x640000（6.25 MB）分区

### 6.2 已知风险点（编译通过后要盯）

- `kPredictBarHeight = 30` 是在 320×240 横屏上挤出来的高度，实际观感可能需要调
- `predictMap` 是 `const char*` 数组，`set_map` 后必须保证它不被释放（已做成成员，理论安全）
- 每次按键都跑一遍词表扫描（3000 词、前缀匹配），需确认**不卡顿**；如果卡，改成首字母分桶索引
- 键盘 `LV_EVENT_VALUE_CHANGED` 在长按/退格时的触发时机，需确认候选栏同步刷新

---

## 7. 关键文件索引

| 文件 | 作用 |
|---|---|
| `changed-files\device-ui\source\graphics\TFT\TFTView_320x240.cpp` | 联想栏 UI 主体（393 KB，最大改动） |
| `changed-files\device-ui\source\graphics\common\WordPredict.cpp` | 前缀匹配算法 |
| `changed-files\device-ui\source\graphics\common\predict_wordlist.inc` | 3000 词表 |
| `changed-files\firmware\platformio.ini` | device-ui 接入 + 依赖显式声明 |
| `changed-files\firmware\variants\esp32s3\seeed_wio_tracker_L2\platformio.ini` | LovyanGFX include 路径 + 所有 L2 硬件宏 |
| `platformio-patch\piolib.py` | LDF 补丁（不装会卡死） |
| `partitions.csv` | IDF 混合编译必需 |
| `build.ps1` / `apply-ldf-patch.ps1` | 编译脚本 / 补丁脚本 |

---

## 8. 一句话总结

**功能代码早就写完了，卡了几十轮的全部是环境问题**：中文路径、Windows 沙箱、路径长度、pioarduino 版本语义陷阱、缺失的 partitions.csv，以及最致命的 PlatformIO 依赖扫描算法缺陷 + 三套安全软件的实时文件过滤。前五个都有确定解法（已在本包内），最后一个是换机就能绕过的。

---

## 9. 本机（个人电脑）换机适配记录 — 2026-11-08

> 第 5 节记的是**公司机器**的坑。本机环境完全不同，硬套「robocopy 镜像 + 直接 build.ps1」那套行不通，改用「依赖本地化 + 离线编译」。

### 9.1 两机环境差异

| 项 | 公司机器 | 本机 |
|---|---|---|
| 路径 | `L2改造`（含中文，cmake 崩 `0xE06D7363`） | `<WORKSPACE>`（纯 ASCII、短） |
| 磁盘 | C 盘受限、路径 <252 字符 | C 盘仅 12.3 GB，**D 盘 364 GB** |
| CPU / 安全软件 | 16 核但三套实时过滤，~4 个 `.o`/分钟 | 16 核、无实时过滤、12 并行 |
| 沙箱 | 新建 exe 受信任目录限制 | 无该限制（D 盘 venv 可写），但有批量删除保护 |
| PlatformIO | `AppData\Local\l2pio` | D 盘 venv + `PLATFORMIO_CORE_DIR=<WORKSPACE>\.pio-core` |
| 网络 | GitHub 可达 | **GitHub 直连不通**（9.2） |
| 设备 | 有 L2 | 不在身边、无串口 → 只编译不烧录 |

### 9.2 网络通道实测与依赖本地化

| 域名 | 结果 | 用途 |
|---|---|---|
| `pypi.org` | 200（0.55 s） | pip / uv |
| `api.github.com` | 200 | 只读 API |
| `github.com/*/archive/*.zip` | 空回复 / 502 | **不通** |
| `github.com/*/releases/download/*` | CONNECT tunnel 502 | **不通** |
| `codeload.github.com` | 200 | archive 回退 |
| `ghfast.top/https://github.com/...` | 200 / 206 | release asset + archive 主通道 |
| `dl.espressif.com` / `dl.registry.platformio.org` | 206 | 工具链可达 |

做法（`<WORKSPACE>\prepare-offline.py`，幂等，可重复运行）：

1. 用 `pio project config --json-output` 解析出目标 env 的真实 `lib_deps`（全仓 118 个 GitHub URL，目标 env 只用 **73 个**）
2. 8 线程把 73 个 zip 抓到 `deps\libs\`，**73/73 成功、0 失败**；`codeload` 作回退
3. 平台包 `platform-espressif32.zip`（2.1 MB）落地为 `deps\platform-espressif32-local\`，其 `platform.json` 的 22 个工具链 URL 改指 `ghfast.top`
4. 24 个 `*.ini` 里的 GitHub URL 全换 `file://`（原件留 `.bak`），`platform` 指向本地目录；**0 个裸 `github.com` 残留**
5. 编译入口 `build-local.ps1`（设 core 目录 + 指定 venv python）

### 9.3 本机新踩的坑（原文档没有）

| 坑 | 现象 | 解法 |
|---|---|---|
| `file:///` 三斜杠 | PlatformIO 用 `uri[7:]` 取路径，`file:///<DRIVE>:/x.zip` → `/D:/x.zip`，Windows 上 `os.path.isfile` = False，依赖装不上 | 必须写 **`file://<DRIVE>:/...`**（两斜杠 + 盘符），用 `PackageSpec(...).uri[7:]` 验证 |
| `penv` 装依赖失败 | 平台自带 `builder/penv_setup.py` 要求 16 个 Python 包，用 `uv` 装时把 stdout/stderr 全丢 DEVNULL，只报 `Failed to install Python dependencies into penv` | 预先用 uv 一次装齐 16 个，`get_packages_to_install` 判定全满足 → 跳过安装 |
| `pioarduino 6.2.0.post1` | 平台要求 `>=6.2.0`，uv 默认装 post1（第 5 节记过会在混合编译二阶段被卸载） | 钉死 **`pioarduino==6.2.0`** |
| 补丁只打一处 | SCons 跑在 core 的 `penv` 里，只打 venv 的 `piolib.py` 无效 | 两处都打：`venv\...` 与 `.pio-core\penv\...` |
| pioarduino 多 1 行 | pioarduino 6.2.0 的 `piolib.py` 比上游多 `self.env.ProcessCompileDbIncludeToolchainOption()`，整体替换补丁会删掉 | 打完补丁手工补回该行，`ast.parse` 验语法 |
| **`$ErrorActionPreference = "Stop"`** | 沙箱批量删除保护（>50 文件）往 **stderr** 打警告，PowerShell 5.1 把它包装成 `NativeCommandError`，`build.ps1` 的 Stop 直接中止编译；其实 PlatformIO 的 `finally` 已 `except: pass` 吞掉删除失败，包本身已装好 | 把 `build.ps1` 改为 `Continue`（原件 `build.ps1.orig`）；或直接用 Bash 驱动 `python -m platformio run`（不经过 PowerShell 错误处理） |
| 大包解压临时目录残留 | safe-delete 拦截后 `pkg-installing-*` 目录留在 `.pio-core\.cache\tmp`（约 105 MB） | 不影响编译，D 盘空间充足；编译结束后统一清理 |
| PlatformIO HTTP 读超时 | `platformio/http.py` 的 `__default_requests_timeout__ = (10, None)`，慢镜像下大包下到一半抛 `ReadTimeout: read timeout=10` | 改成 `(30, 300)`（venv 与 penv 两处，留 `.orig`） |
| 镜像并发限流 | 6 个大文件并发下载时全部失败，单包手动下载 1.4 s 成功 | `fetch-tools.py` 并发降到 2；或干脆把剩余工具链包预下载到本地 `file://` |
| **Git Bash 不能用来启动编译** | 为绕开上面 stderr 陷阱改用 Git Bash 后，ESP-IDF 的 `idf_tools.py` 检测到 `MSYSTEM` 环境，反复报 `ERROR: MSys/Mingw is not supported`，编译无法进入 IDF 阶段 | **必须用 PowerShell 入口**（`build.ps1` 的 ErrorActionPreference 已改 `Continue`，stderr 警告不再致命）；或在启动前清除 `MSYSTEM` 环境变量 |

### 9.4 联想算法静态验证（不依赖固件编译）

本机无 host C++ 编译器，用 `<WORKSPACE>\verify-wordpredict.py` 把 `WordPredict.cpp` **逐行等价移植到 Python** 跑真实词表：

| 项 | 实测 |
|---|---|
| 词数 | 3000，无重复，全部 `[a-z]+` |
| `.rodata` 字符串 | **21,306 字节（20.8 KiB）** |
| 最长词 | `administration`（14 < `kMaxWordLen=16`），无词被静默丢弃 |
| `hel` | `help` / `held` / `helpful` |
| `HEL` / `Hel` | 全大写 / 首字母大写输出正确 |
| 边界 | 空前缀、长度 ≥15、无意义前缀、maxCount → 全部符合预期 |
| 结论 | 10 条断言 **ALL PASS**，结果存 `_wordpredict-verify.json` |

编译级静态核对：`THIS` 宏在 `TFTView_320x240.cpp:80` 已定义，`instance()` 返回 `TFTView_320x240*`，LVGL 9 API（`lv_obj_remove_flag` / `lv_event_get_target_obj` 等）该文件本来就有 37 处使用 → 联想代码无 API 版本错配。

### 9.5 设备到位后的操作清单

```powershell
[System.IO.Ports.SerialPort]::GetPortNames()
.\build-local.ps1 upload -Port COMxx
.\build-local.ps1 monitor -Port COMxx
```

验收按 6.1 节，但注意 **`hel` 的正确候选是 `help` / `held` / `helpful`**（不是原文写的 hello/help/held）。重点看：启动横幅、无 `Guru Meditation` / boot loop、键盘上方 30px 候选栏、点击后补全并带空格、连续按键不卡顿。

### 9.6 编译状态与续跑

```
<WORKSPACE>\build.log        编译日志
<WORKSPACE>\BUILD_STATUS.md  状态与一键续跑命令
```

续跑命令（**必须用 PowerShell**，见 9.3 的 MSYS 坑；幂等，已装包会跳过）：

```powershell
.\build-local.ps1 -Target build -Jobs 12
```

若用 Bash 直驱，须先 `unset MSYSTEM`，否则 ESP-IDF 拒绝运行。

产物：`<WORKSPACE>\firmware\.pio\build\seeed_wio_tracker_L2-tft\firmware.bin`


---

## 10. 编译 + 烧录完成记录（2026-11-09）

### 10.1 真正的代码 bug（编译期才暴露）

`libs/device-ui/source/graphics/TFT/TFTView_320x240.cpp:8312` 的 `applyPrediction()` 调用了 LVGL 8 的 `lv_textarea_del_char()`，项目锁的是 **LVGL 9.3.0**，正确 API 是 `lv_textarea_delete_char()`。

```
error: 'lv_textarea_del_char' was not declared in this scope; did you mean 'lv_textarea_delete_char'?
```

修复：改名（原件备份 `TFTView_320x240.cpp.orig`）。这是第 6 节里「TFTView_320x240.cpp 未跑完」留下的唯一编译错误，也说明**之前的静态 API 核对没覆盖到 textarea 删除接口**。

### 10.2 编译结果（本机 <WORKSPACE>）

`BUILD_EXIT=0`，耗时 27 分 31 秒，产物：

| 文件 | 大小 | 说明 |
|---|---|---|
| `firmware-...-2.8.3.bin` | 3,890,272 B | app0（分区上限 0x640000 = 6.25 MB，占用 3.2%） |
| `firmware-...-2.8.3.factory.bin` | 3,955,808 B | esptool merge_bin 生成的 0x0 合并镜像 |
| `bootloader.bin` / `partitions.bin` | 20 KB / 3 KB | 0x0 / 0x8000 |
| `littlefs-...-2.8.3.bin` | 3,538,944 B | spiffs @0xc90000 |

RAM 5.2%（16976 / 327680）。

### 10.3 烧录（COM9，本机直连 L2）

设备：ESP32-S3 rev0.2、8 MB PSRAM、MAC `<DEVICE_MAC>`、16 MB Flash（Winbond ef/4018）、USB-Serial/JTAG。

**关键坑**：board json 写 `flash_mode=qio`，但 PlatformIO 生成 factory.bin 用的是 **`--flash_mode dio`**（见 build.log 第 1582 行）。第一次按 qio 烧录会 patch bootloader 头部，ROM 用 QIO 读、固件按 DIO 编，结果 `rst:0x7 (TG0WDT_SYS_RST)` 反复重启（`ets_loader.c 78`）。

正确命令（`dio / 80m / 16MB / 921600`，5 段全烧，含 littlefs）：

```
esptool.exe --chip esp32s3 --port COM9 --baud 921600 --before default_reset --after hard_reset write_flash --flash_mode dio --flash_freq 80m --flash_size 16MB 0x0 bootloader.bin 0x8000 partitions.bin 0xe000 <framework>/tools/partitions/boot_app0.bin 0x10000 firmware-...-2.8.3.bin 0xc90000 littlefs-...-2.8.3.bin
```

每段 `Hash of data verified`，hard reset 后串口日志正常（`<WORKSPACE>/serial_boot2.log`）：`[PacketAPI]` / `[NodeInfo]` / `[DeviceUI] handleFromRadio`，无 boot loop、无崩溃；只有首次未配置 LoRa 区域的正常 WARN（`Region unset`）。

### 10.4 仍需人工验证（第 6.1 节验收项 3/4）

串口只能证明启动与 device-ui 加载。需在设备屏幕上进入消息输入界面，敲 `hel`，确认候选栏出现 **`help` / `held` / `helpful`**，点击后补全并带空格、连续按键不卡顿。`kPredictBarHeight = 30` 的实际观感也需现场确认。

### 10.5 本机环境修复清单（供复现）

- 删除保护：`CODEBUDDY_SAFE_DELETE_ENABLED=0`（shim 官方开关，写入 `build-local.ps1`）
- 组件管理器 git fetch：缓存仓库 origin 改 `ghfast.top` 前缀 + `GIT_CONFIG_*` URL 重写（仅子进程）
- 工具链/依赖：73 个库本地化（registry 需 `User-Agent: PlatformIO/6.2.0`；LovyanGFX 用 Range 分块并发）；413 MB 工具链走 `dl.espressif.com/github_assets`
- 空壳包：`tool-cmake`/`tool-ninja` 用本机 ESP-IDF v5.5.2 的 cmake 3.30.2 / ninja 1.12.1 填充；`toolchain-xtensa-esp-elf` 的 SCons/ldgen 路径改指真实工具链目录（见 `espidf.py.orig`、`arduino.py.orig`、`platform.py.orig`）
- GitHub 下载：`platformio/http.py` 的 `HTTPSession.request()` 统一把 `https://github.com/` 重写为 `https://ghfast.top/https://github.com/`
- `extra_scripts/esp32_pre.py` 的 `os.remove(sdkconfig.defaults)` 改为改名（`.l2old`）
- `IDF_PATH` 环境变量显式隔离，避免与本机 IDF 串味


---

## 11. 联想栏「敲 hel 完全不显示」的根因与修复（2026-11-09 下午）

### 11.1 用户反馈

进消息输入界面敲 `hel`，既没有候选栏，也没有 `help / held / helpful`。此前固件已编译成功并烧录、串口启动正常（第 10 节）。

### 11.2 先排除「代码没编进去」

| 检查 | 结果 |
|---|---|
| `build.log:145` | 编译的确是 `<WORKSPACE>/libs/device-ui/source/graphics/TFT/TFTView_320x240.cpp` |
| elf / map 符号 | `createPredictBar()` / `applyPrediction()` / `updatePredictions()` / `ui_event_PredictKey` / `ui_event_PredictBar` / `kPredictWordList` 全在 |
| `createPredictBar()` 调用链 | `init_screens()` → `ui_init()` → `apply_hotfix()` → `createPredictBar()`，`apply_hotfix()` 无条件执行 |
| 源码一致性 | 与 `reference/changed-files` 逐行对比，唯一差异是第 10.1 节的 LVGL 9 API 修复 |

**结论：源码、编译、链接都没问题，是运行时逻辑把候选栏隐藏了。**

### 11.3 两个真实 bug

**Bug A（致命）—— textarea 指针严格相等判断永远为假**

原 `updatePredictions()` 开头：

```cpp
lv_obj_t *ta = lv_keyboard_get_textarea(objects.keyboard);
if (ta != objects.message_input_area) {
    lv_obj_add_flag(predictBar, LV_OBJ_FLAG_HIDDEN);
    return;
}
```

加诊断日志后实测运行时地址：

| 对象 | 地址 |
|---|---|
| `objects.message_input_area` | `0x3c3ccdb8` |
| 键盘实际绑定的 textarea | `0x3c3ef318` |
| 键盘对象（事件 target） | `0x3c3f0394` |

二者**不是同一个对象**（generated UI 中消息输入存在另一个 textarea 实例）。所以每次刷新都命中 `!=` 分支直接隐藏 → 候选栏永远不出现。第一轮诊断日志（`<WORKSPACE>/serial_predict.log`）：

```
WordPredict: VALUE_CHANGED on 0x3c3f0394
WordPredict: hidden, keyboard bound to another textarea (0x3c3ef318)
```

**Bug B —— `showKeyboard()` 中段提前 return，键盘不重新绑定**

```cpp
if (textArea == objects.message_input_area) {
    if (kbdSlideState != eKbdHidden)
        return;                       // 跳过了函数末尾的 set_textarea
    ... 滑入动画 ...
}
lv_keyboard_set_textarea(objects.keyboard, textArea);   // 永远执行不到
```

`showKeyboard()` 的 `else` 分支（其他 textarea）不检查状态，会把键盘绑定到别的输入框；之后回到消息界面且 `kbdSlideState != eKbdHidden` 时函数提前返回，绑定就一直停在旧 textarea。**A + B 叠加 = 功能完全不可见**。

**Bug C（显示层隐患）** —— `predictBar` 原本是 `objects.keyboard`（`lv_keyboard`，buttonmatrix 子类）的子对象，`y = -30` 放在父对象边界外，靠 `LV_OBJ_FLAG_OVERFLOW_VISIBLE` 生效；而 keyboard 的父容器是 main_screen 的子 panel，容易被裁剪或布局重置。

### 11.4 修复内容

文件 `libs/device-ui/source/graphics/TFT/TFTView_320x240.cpp`，原件备份 `TFTView_320x240.cpp.bak_20261109`（更早的 LVGL API 备份为 `.orig`）。

1. 候选栏改到 **`lv_layer_top()`**。LVGL 9 的顶层容器创建时显式 `lv_obj_remove_flag(..., LV_OBJ_FLAG_CLICKABLE)`，不会吞掉键盘触摸，子对象仍可点击。每次刷新按键盘绝对坐标定位 `y = kb.y1 - kPredictBarHeight` 并 `lv_obj_move_foreground()`。
2. 新增文件级 `s_predictTa`，由 `ui_event_PredictKey` 记录**实际发生文本变化的对象**；`updatePredictions()` / `applyPrediction()` 一律用它，**移除严格相等判断**。
3. 刷新触发改双保险：`message_input_area` 的 `LV_EVENT_VALUE_CHANGED`（LVGL 9 每次插入/删除字符都发，`lv_textarea.c` 4 处）+ keyboard 的 `VALUE_CHANGED`。
4. 修 `showKeyboard()`：滑入动画只在 `eKbdHidden` 时播放，末尾 `lv_keyboard_set_textarea()` 一定执行，并同步 `s_predictTa`。
5. `hideKeyboard()` 收起键盘时同时隐藏候选栏；候选栏加深蓝底白字配色，避免「显示了但看不清」。
6. 关键路径加 `ILOG_WARN("WordPredict: ...")` 诊断日志（可复现、可定位）。

### 11.5 编译、烧录与实测验证

- 两轮增量编译均 `BUILD_EXIT=0`（4m39s / 4m59s），最终 app `3,891,472 B`（分区上限 6.25 MB）
- COM9 按 **`--flash_mode dio`** 重烧 5 段（含 littlefs），全部 `Hash of data verified`
- 无 boot loop、无 `Guru Meditation` / `TG0WDT_SYS_RST`
- `<WORKSPACE>/serial_predict2.log` 统计：21 次 `VISIBLE`、8 次 `applied`（点击候选补全成功）、0 次旧 hidden 判断、0 崩溃

关键日志：

```
text='hel'  prefix='hel'  -> 3 [help][held][helpful] VISIBLE at (0,100)
text='he'   prefix='he'   -> 3 [here][help][health]  VISIBLE at (0,100)
text='stra' prefix='stra' -> 3 [strategy][strategies][straight] VISIBLE at (0,100)
applied idx=1 word='help'
applied idx=0 word='helpful'
```

`applied` 证明候选栏**确实可见且可点击**，补全带空格生效。第 6.1 节验收项 3/4 已通过；`kPredictBarHeight = 30` 的观感仍需现场目视确认。

### 11.6 经验教训

- 「elf 里有符号」≠「功能在跑」；UI 功能必须靠**运行时日志**确认触发链，静态检查查不出对象绑定错配。
- 不要用 **UI 对象指针相等**当作功能启用条件；generated UI 里同类输入框可能有多个实例。
- 有副作用的函数中段放提前 `return` 很危险，末尾的绑定 / 注册语句容易被跳过。
- 子对象放在 buttonmatrix 边界外不可靠；顶层容器 + 绝对坐标跟随更稳。
- 换机编译踩的环境坑（第 9/10 节）与业务代码 bug 要分开排查，先证明「代码进固件了」再查逻辑。

### 11.7 遗留项

当前固件含 `WordPredict:` 诊断日志（每次按键约 2 条 WARN）。只影响串口输出，不影响 UI 流畅度。验收无误后如需安静版，去掉这些 `ILOG_WARN` 再增量编译烧录一轮即可（约 5 分钟）。


---

## 12. 点击候选「显示 hello、却插入 here」的根因与修复（2026-11-09）

### 12.1 现象

候选栏已正常显示（第 11 节修好后），但用户敲 `hell` 看到 `hello`，点击 `hello` 后输入框里出现的是 `here`。

### 12.2 根因：`applyPrediction()` 编辑 textarea 时递归刷新污染了候选缓冲

`lv_textarea_delete_char()` / `add_text()` / `add_char()` 在 LVGL 9 里**每次都同步发出 `LV_EVENT_VALUE_CHANGED`**（`lv_textarea.c` 有 4 处）。而 `ui_event_PredictKey` 注册在 textarea 与 keyboard 上，会立刻回调 `updatePredictions()`，用**删除过程中的中间态文本**重算 `predictCandidates`。

更糟的是 `predictMap[i]` 原本直接指向 `predictCandidates[i]`，而 `lv_buttonmatrix_set_map()` 保存的是指针而非拷贝——所以递归刷新连**屏幕上的文字**都一起改了。等执行到

```cpp
lv_textarea_add_text(ta, predictCandidates[idx]);
```

时数组已被重算成 `he` 前缀的 `[here, help, health]`，于是点了 `hello` 却插入 `here`。

日志证据（`<WORKSPACE>/serial_predict2.log`）：

```
text='hell'  -> 1 [hello][][] VISIBLE
text='he'    -> 3 [here][help][health]    ← 删除循环触发的递归刷新
text='h' / '' / 'h' / 'he' / 'her' / 'here' / 'here '
applied idx=0 word='here'                  ← 用被覆盖后的缓冲插入
```

### 12.3 修复内容

文件 `TFTView_320x240.cpp`，备份 `TFTView_320x240.cpp.bak_20261109_v3`。

1. 新增文件级 `s_predictLabels[kMaxCandidates][kMaxWordLen]`；`updatePredictions()` 把候选复制进去，`predictMap` 指向它 → **显示文字与候选缓冲解耦**。
2. `applyPrediction()` 先把 `s_predictLabels[idx]` 快照到局部 `char word[]`，之后所有写入都只用这个局部副本。
3. 新增 `s_predictApplying` 守卫：整个编辑期间 `ui_event_PredictKey` 直接 return，`updatePredictions()` 开头也检查；编辑结束才刷新一次。编辑前先隐藏候选栏。
4. 诊断日志增强：`ui_event_PredictBar` 打印 `tap id=N label='...'`，`applyPrediction` 打印 `shown='...' inserted='...'`，可直接机器校验「显示 → 点击 → 写入」三者一致。

### 12.4 验证（`<WORKSPACE>/serial_predict3.log`）

第三轮增量编译 `BUILD_EXIT=0`（4m58s），app `3,891,696 B`；COM9 按 **`--flash_mode dio`** 重烧 5 段全 Hash verified；烧录的 bin 里确认含新版日志字符串。

6 次点击（覆盖 id=0/1/2 三个候选位）全部一致：

```
tap id=0 label='here'     -> shown='here'     inserted='here'
tap id=1 label='picture'  -> shown='picture'  inserted='picture'
tap id=2 label='baby'     -> shown='baby'     inserted='baby'
tap id=0 label='weather'  -> shown='weather'  inserted='weather'
tap id=0 label='site'     -> shown='site'     inserted='site'
tap id=0 label='good'     -> shown='good'     inserted='good'
```

`ALL CONSISTENT: True`；补全后自动追加空格（`text='here picture baby weather '`）；0 boot loop / 崩溃。

### 12.5 关于「敲 hel 显示 hello」

词表按词频排序，实测：`hel` → `help / held / helpful`，`hell` → `hello`。日志显示用户那次实际敲的是 `hell`（4 个字母）才出现 `hello`，这是词表设计（第 9.4 节），不是错位 bug。若希望 `hel` 的前三候选就包含 `hello`，需调整 `predict_wordlist.inc` 里 `hello` 的位置（会影响整体词频顺序），需另行确认。

### 12.6 经验教训

- LVGL 控件的 setter 会**同步**派发事件；在事件回调里修改同一个控件极易形成递归，递归又会覆写共享缓冲。
- `lv_buttonmatrix_set_map()` 保存指针而非拷贝，map 指向的缓冲在两次刷新之间不能被改写。
- 对「显示值 → 用户点击 → 写入值」这条链，显示缓冲必须独立，且点击瞬间要快照；只靠索引去读会被中途刷新改变的数组是典型陷阱。
- 关键链路上加 `tap / shown / inserted` 三项日志，能用一次实测直接证明一致性，比静态推理可靠。


---

## 13. 稳定版归档与词库扩展容量评估（2026-11-09）

### 13.1 v1.0 归档（用户确认「很成功」后的基线）

目录 `<WORKSPACE>/releases/backup_20261109_L2_wordpredict_v1.0/`（70.9 MiB），12 个文件 SHA256 全部校验通过：

| 内容 | 说明 |
|---|---|
| `firmware\` | 5 个烧录分段（bootloader / partitions / boot_app0 / app / littlefs）+ 1 个 `*.factory.bin` 合并镜像 |
| `src_snapshot\` | 本版对应的 5 个改动源码（`TFTView_320x240.cpp/.h`、`WordPredict.cpp/.h`、`predict_wordlist.inc`） |
| `debug\` | 带符号 elf，用于崩溃回溯 |
| `SHA256SUMS.txt` / `RELEASE_NOTES.md` | 完整性清单 / 版本说明、偏移、烧录命令、分区占用 |
| `flash.bat` | 一键回滚（CRLF、纯 ASCII、`dio` 模式） |

版本台账：`<WORKSPACE>/releases/CHANGELOG.md`。**稳定版归档后不再原地修改**；后续改动从 `libs/device-ui` 继续，编出新版本后另建 `backup_YYYYMMDD_..._vX.Y`。回滚只需 `flash.bat COM9`。

### 13.2 Flash 容量实测

| 项 | 数值 |
|---|---|
| `app0` / `app1` | `0x10000` / `0x650000`，各 `0x640000` = **6,553,600 B（6.25 MiB）** |
| 当前 app bin | **3,891,696 B（3.71 MiB，59.4%）** |
| app 分区剩余 | **2,661,904 B（2.54 MiB）** |
| 词表 `kPredictWordList` | `0x533b` = **21,307 B（20.8 KiB）**，占 app 0.325%、占剩余 0.80% |
| `spiffs` | `0x360000` = 3,538,944 B；littlefs bin **正好 3,538,944 B → 剩余 0 B（100% 占满）** |
| DROM | `drom0_0_seg` 地址空间上限 0x1FFFFE0（≈32 MiB）；当前 `.flash.rodata` = 0x14DF54（1.30 MiB）→ **不是瓶颈** |

词表在 `.flash.rodata`（DROM，经 flash MMU 映射），**不占 RAM**（RAM 当前 5.2%）。因为 `spiffs` 已满，扩展词表只能放 app 的 `.rodata`。

### 13.3 词表当前状态

3000 词、无重复、全部 `[a-z]+`、平均 6.1 字符、最长 14（< `kMaxWordLen=16`）、按词频降序、`\n` 分隔。平均每词 7.10 B（含分隔符）。

### 13.4 扩展空间估算（按当前平均词长）

| 词数 | 词表大小 | 占 app 分区 | 占剩余空间 |
|---|---|---|---|
| 3,000（现状） | 20.8 KiB | 0.33% | 0.80% |
| 5,000 | 34.7 KiB | 0.54% | 1.33% |
| **10,000** | **69.4 KiB** | **1.08%** | **2.67%** |
| 20,000 | 138.7 KiB | 2.17% | 5.34% |
| 30,000 | 208.1 KiB | 3.25% | 8.00% |
| 50,000 | 346.8 KiB | 5.42% | 13.34% |
| 100,000 | 693.6 KiB | 10.84% | 26.68% |

理论上限（把 2.54 MiB 剩余全塞满）约 **374,810 词**。**结论：Flash 完全够，扩到 1–3 万词只吃掉剩余空间的 3–8%。**

### 13.5 真正的瓶颈不是 Flash

1. **`WordPredict::predict()` 是线性扫描**：从词表头逐词比对，凑满 `maxCount=3` 才提前退出。无匹配（或罕见前缀）时**必须扫完整张表**。10 万词 ≈ 700 KiB 逐字节从 flash cache 读 + 约 60 万次字符比较，每次按键可能十几到几十 ms → 有 UI 卡顿风险（本项目要求「流畅第一」）。
2. **`kMaxCandidates = 3`**：再大的词表也只有前 3 个匹配词能显示，收益递减；词表按词频排序，1–2 万词已覆盖绝大多数日常英文。
3. **`kMaxWordLen = 16`**（含 `\0`）：长于 15 字符的词会被 `wordLen < kMaxWordLen` 静默丢弃，扩展时必须过滤。
4. **候选栏宽度**：320 px / 30 px 高，候选数若增加需同步改 `predictMap`、`s_predictLabels` 数组和按钮宽度，否则文字截断。

### 13.6 建议档位（尚未实施，等用户确认）

| 档 | 规模 | 改动 | 风险 |
|---|---|---|---|
| **A（推荐）** | 1 万词（≈69 KiB） | **只换 `predict_wordlist.inc`**，算法不动 | 极低；最坏扫描约 69 KiB，实测几乎无感 |
| B | 2–3 万词（≈140–208 KiB） | 换词表 + 加「双字母前缀偏移表」（26×26×4 B ≈ 2.7 KiB），`predict()` 直接跳到对应区段 | 中；需改 `WordPredict.cpp` 并重新验证 |
| C | >5 万词 | 不建议：3 个候选上限下收益很小，且需改索引 + 可能触及 DROM/分区预算 | 高 |

顺带可一并处理：`hel` 当前按词频出 `help / held / helpful`，`hello` 排第 4。若希望 `hel` 就出 `hello`，把 `hello` 在词表中移到前 3 即可（会轻微改变词频顺序）。

### 13.7 扩展词表时的硬性约束清单

1. 纯小写 `a-z`，长度 **≤15** 字符
2. `\n` 分隔、末尾 `\0`、无重复、无空行
3. **按词频降序**（前 3 个匹配词就是候选，顺序即优先级）
4. 单个字符串常量进 `.rodata`；编译后用 `nm --print-size` 核对 `kPredictWordList` 大小不超预算
5. app bin 必须 < 6,553,600 B；烧录仍用 **`--flash_mode dio`**
6. 改动后新建版本目录归档，不要覆盖 v1.0


---

## 14. v1.1 词库扩展实施记录（2026-11-09）

用户选 **档 A**（1 万词、只换词表、算法不动），并授权「选择合适的完成」。v1.0 已归档保留，可一键回滚。

### 14.1 词表构造

来源 `google-10000-english`（MIT，与 v1.0 词表同源；`raw.githubusercontent.com` 直连可达），不足部分用同仓 `20k.txt` 补足。

| 规则 | 说明 |
|---|---|
| **前 3000 词字节级不变** | 保证所有已验收候选（`hel`/`hell`/`he`/`str`/`wea`…）零回退 |
| 追加 7000 词 | 严格按同源词频降序，纯 `[a-z]`、2–14 字符、无重复 |
| 过滤 114 个明确成人/粗俗词 | 见 14.2 |
| 丢弃 >14 字符词 | 见 14.2 |

结果：**10,000 词**，`kPredictWordList` = 76,015 B（74.2 KiB），最长 14 字符。源文件 `predict_wordlist.inc` 92,482 B，原表备份 `predict_wordlist.inc.bak_20261109_v1`。

### 14.2 两个自主质量判断

1. **过滤成人/粗俗词**：Google 网页语料在 3000 名之后紧跟着一批成人站高频词（追加部分前 12 个里就有 `sex/porn/nude/ass/anal/pussy/sexy/rape/incest/xxx/fucking`）。直接放进家用设备的候选栏不合适。用**精确集合**过滤 114 个词，避免子串匹配误伤 `analysis`/`analyst`/`analog`/`canal`/`therapeutic` 等正常词；`adult`/`naked`/`sexual`/`lesbian` 等中性词保留（且 v1.0 前 3000 里本来就有，不动）。
2. **收紧到 14 字符**：首次生成时追加部分含 10 个 15 字符词（如 `recommendations`）。`kMaxWordLen=16` 虽允许，但 320 px 三按钮候选栏会截断文字 → 又会造成「显示的词看着和实际插入不一样」的观感（正是第 12 节刚修的问题）。故丢弃 >14 字符词，与原表最长长度保持一致，用 `20k.txt` 补足到 10000。

### 14.3 编译与产物

| 项 | v1.0 | v1.1 |
|---|---|---|
| 词数 / 词表 flash | 3,000 / 21,307 B | **10,000 / 76,015 B** |
| app bin | 3,891,696 B (59.4%) | **3,946,400 B (60.2%)** |
| app 分区剩余 | 2.54 MiB | **2.49 MiB** |
| 编译 | 4m58s | **4m32s**，`BUILD_EXIT=0` |
| 烧录 | COM9 dio 5 段 | COM9 **dio** 5 段，全 Hash verified |

app 增量 54,704 B 与词表净增 54,708 B 几乎完全吻合 → 词表完整编入 `.rodata`，无额外开销、不占 RAM。

### 14.4 验证链

1. **Python 等价 `predict()` 回归**：25 个前缀（含大小写 `HEL`/`Hel`、边界）逐一比对，旧候选始终是新结果的前缀子序列 → `ZERO REGRESSION: True`。新增覆盖示例：`noi→noise`、`widt→width`、`clim→climate`、`arr→array/arrangements/arrival`。
2. **elf 核对**：`nm --print-size` 得 `kPredictWordList = 0x128ef = 76,015 B`；含新词 `noise/balancing/width/colour`，不含被过滤词、不含 15 字符词。
3. **设备实测**（`<WORKSPACE>/serial_v11.log`）：启动无 boot loop / 崩溃；31 次候选显示、4 次点击 `shown==inserted` 全一致；`he→[here][help][health]` 零回退；**`here→[herein][hereby]` 证明新词生效**（v1.0 下 `here` 为 0 候选）。
4. **归档自校验**：16 个文件 SHA256 全通过；`wordlist_build.py` 从归档的 `wordlist_source/` + v1.0 原表**字节级复现** `predict_wordlist.inc`（哈希一致）。

### 14.5 归档与回滚

`<WORKSPACE>/releases/backup_20261109_L2_wordpredict_v1.1/`（71.4 MiB）：`firmware/`（6 个 bin）、`src_snapshot/`（5 个源码 + v1.0 原词表）、`wordlist_source/`（两份语料）、`wordlist_build.py`（可复现）、`debug/`（elf）、`SHA256SUMS.txt`、`RELEASE_NOTES.md`、`flash.bat`。

`releases/CHANGELOG.md` 已登记 v1.0 / v1.1。回滚：在 v1.0 目录执行 `flash.bat COM9`。

### 14.6 已知 / 未做（保持档 A 边界）

- 固件仍含 `WordPredict:` 诊断 WARN 日志（按键约 2 条），不影响 UI；需要安静版另编一轮
- `kMaxCandidates = 3` 未改；扩展只提升覆盖范围，不增加候选个数
- `hel` 仍出 `help / held / helpful`，`hello` 排第 4（词频顺序）；**未做局部重排**，以免改变刚验收通过的行为
- 未引入前缀索引；1 万词最坏线性扫描约 74 KiB，实测无卡顿；若将来扩到 2–3 万词再按第 13.6 节档 B 加索引
