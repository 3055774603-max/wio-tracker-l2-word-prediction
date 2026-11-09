# 补丁说明

| 文件 | 说明 |
|---|---|
| `device-ui.diff` | 交接包中相对上游 device-ui 的**初版**改动（联想输入 + 3000 词表） |
| `firmware.diff` | 交接包中相对上游 firmware 的**初版**改动（`lib_extra_dirs`、变体配置等） |
| `piolib-ldf.patch` | PlatformIO Core 6.2.0 `platformio/builder/tools/piolib.py` 的 LDF 扫描补丁，unified diff 格式；`scripts/apply-ldf-patch.ps1` 用的是整文件替换版 |

## 后续修复已直接体现在源码里

上面两个 `.diff` 只对应初版。之后定位并修复的问题没有单独出 diff，改动都在 `libs/device-ui/` 中：

1. **LVGL 9 API**：`lv_textarea_del_char` → `lv_textarea_delete_char`（`TFTView_320x240.cpp` 的 `applyPrediction()`）
2. **候选栏不显示**：`updatePredictions()` 去掉 textarea 指针严格相等判断，改用实际发生文本变化的对象；`showKeyboard()` 去掉中段提前 `return`；候选栏改到 `lv_layer_top()` + 绝对坐标
3. **点击候选错位**：新增 `s_predictApplying` 守卫阻断编辑期间的递归刷新，新增独立 `s_predictLabels` 显示缓冲，点击前快照成局部 `word`
4. **词库扩展**：3000 → 10000 词（`wordlist/` 可复现）

源码包不含 `.git`，无法生成相对上游的权威 diff。改动点与根因分析见 `docs/HANDOFF.md` 第 10–14 节。

## 应用 LDF 补丁

`scripts/apply-ldf-patch.ps1` 会把补丁后的 `piolib.py` 整体替换到指定 Python 环境的 `platformio/builder/tools/` 下。**注意 PlatformIO 的 `penv` 与项目 venv 两处都要打**，否则 SCons 阶段扫不到本地库（见 `docs/HANDOFF.md` 第 9.3 节）。
