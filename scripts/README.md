# 构建脚本

这些脚本记录的是**构建机（Windows + 本机 PlatformIO 环境）上的实际流程**，不是开箱即用的通用工具。

## 路径占位符

导出时把所有本机绝对路径替换成了占位符，clone 后按你的环境替换：

| 占位符 | 原值含义 |
|---|---|
| `<WORKSPACE>` | 工作区根目录（`firmware/` 与 `libs/` 的父目录） |
| `<ESPRESSIF_TOOLS>` | 本机 ESP-IDF 工具链根目录（用于填 pioarduino 空壳 `tool-cmake` / `tool-ninja` 包） |
| `<USER_HOME>` | 当前用户主目录 |

`docs/` 下的交接文档也做了同样替换。

## 脚本用途

| 脚本 | 作用 |
|---|---|
| `build.ps1` | 原始构建入口（`-Target build` / `upload` / `monitor`） |
| `build-local.ps1` | 本机适配版：设置 `PLATFORMIO_CORE_DIR`、隔离 `IDF_PATH`、注入工具链 PATH、成功后自动打包 |
| `apply-ldf-patch.ps1` | 应用 `patches/piolib-ldf.patch` 对应的整文件补丁 |
| `prepare-offline.py` | 把 `platformio.ini` 里的 GitHub 依赖预下载到本地并改写为 `file://`（离线编译） |
| `fetch-tools.py` | 预下载 pioarduino 工具链包 |
| `package-delivery.py` | 合并烧录镜像、算 SHA256、生成拷贝即用的烧录包 |
| `verify-wordpredict.py` | 不依赖固件的联想算法等价验证 |
| `wordlist_build.py` | 归档版词表生成脚本（引用归档目录结构）；本仓库请用 `wordlist/build_wordlist.py` |

## 标准构建顺序

```
1. python -m venv .venv && .venv/Scripts/pip install platformio==6.2.0
2. 用 apply-ldf-patch.ps1 打 LDF 补丁（venv 与 PlatformIO penv 两处）
3. python scripts/prepare-offline.py      # 可选：离线依赖本地化
4. 执行 scripts/build.ps1 -Target build -Jobs 12
5. python scripts/package-delivery.py    # 可选：生成烧录包
```

> 本仓库的 `firmware/platformio.ini` **已还原成上游 URL**，可直接联网构建；`prepare-offline.py` 是给无法直连 GitHub 的环境用的。

**烧录必须用 `--flash_mode dio`**（`docs/HANDOFF.md` 第 10.3 节：用 qio 会触发 `TG0WDT_SYS_RST` boot loop）。
