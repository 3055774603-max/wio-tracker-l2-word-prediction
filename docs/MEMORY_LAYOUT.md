# 内存分布与流畅性分析（v1.1）

数据来源：链接 map、`esp-idf-size` 与 elf section headers，均为实测。

## 16 MB Flash 分区

| 分区 | 偏移 | 大小 | 已用 | 占用率 |
|---|---|---|---|---|
| 引导区 / 分区表 / nvs / otadata | `0x0–0x10000` | 64 KB | 22.5 KB | — |
| app0 | `0x10000` | 6.25 MB | 3,946,400 B | 60.2% |
| app1 | `0x650000` | 6.25 MB | 0 | 0%（OTA 备用） |
| spiffs | `0xC90000` | 3.375 MB | 3,538,944 B | **100%** |
| coredump | `0xFF0000` | 64 KB | 0 | — |

app0 剩余 **2,607,200 B（2.49 MiB）**。spiffs 已被 littlefs 占满，所以词表只能放 app 的 `.rodata`。

## 运行时内存（`esp-idf-size` 官方口径）

| 类型 | 已用 | 上限 / 剩余 |
|---|---|---|
| Flash Code `.text` | 2,377,408 B | XIP @ `0x42000020` |
| Flash Data | 1,422,852 B | `.rodata` 1,422,596 + appdesc 256 |
| DIRAM | 209,435 B (61.3%) | 341,760 B / 剩 **132,325 B** |
| IRAM | 16,384 B (100%) | 16,384 B（专用块，IDF 常规布局） |
| RTC FAST / SLOW | 92 / 4 B | 8,192 / 7,680 B |
| PSRAM | — | 8 MB（LVGL 帧缓冲、堆扩展） |

`Total image size: 3,946,247 B`；`drom0_0_seg` 地址空间上限 32 MiB，实际 `.flash.rodata` 1.36 MiB，远未触顶。

**词表落点**：`kPredictWordList` = `0x128ef` = 76,015 B，位于 `.flash.rodata` → DROM `0x3c250120`，经 flash MMU 只读映射。词库 3000 → 10000 只让 Flash Data 增加 54.7 KB，**DIRAM 一个字节都没变**。

## 流畅性

### 1. 零 RAM 开销、零动态分配

词表不进 DRAM，不挤压 129 KiB 内部 heap 和 LVGL 帧缓冲。`out[3][16]`、`s_predictLabels[3][16]`、`predictMap[4]` 全是编译期定长；每次按键没有 `malloc/free`，不会造成堆碎片或停顿。

### 2. 算法提前退出

```
predict(prefix, out, 3)：从表头线性扫描，凑满 3 个匹配立即 return
最坏（无匹配）= 扫全表 76,015 B + 10000 词 × 平均 6.1 字符比较
按 240 MHz / flash cache 顺序命中估算 ≈ 1–2 ms  <<  16.7 ms（60 fps 一帧）
```

常见前缀的匹配词在按词频排序的表头，通常几十~几百字节就凑满 3 个。

### 3. 守卫把点击路径的全表扫描从 ~8 次降到 1 次

修复前删前缀 / 插入字符每个操作都同步发 `VALUE_CHANGED`，一次点击出现 `he / h / '' / h / he / her / here / here ` 共 8 次刷新（最多 8 次全表扫描）。`s_predictApplying` 期间事件直接 `return`，编辑结束只刷新 1 次。词表从 21 KB 变 74 KB，但点击路径扫描量反而从约 8×21 KB 降到 1×74 KB。

### 4. UI 侧不重建对象

候选栏常驻 `lv_layer_top()`，`set_map` 只换指针，`set_pos` / `set_width` / `move_foreground` 都是 O(1) 属性操作，`count=0` 只加 `HIDDEN`。14 字符上限避免长文本换行与裁剪。

### 5. 实测

10 分钟 962 行串口日志、31 次候选显示、4 次点击 `shown==inserted` 全一致、0 崩溃；按键与候选日志落在同一 0.01 s 时间戳。

## 边界

- 串口时间戳 10 ms 分辨率，只能证明「无明显卡顿」；1–2 ms 是按容量与主频的**量级估算**，未做 μs 级 CPU 计时
- textarea 与 keyboard 都注册了 `VALUE_CHANGED`，一次按键刷新 2 次，最坏 2 × 74 KiB ≈ 148 KiB 扫描。要极致优化可去掉 keyboard 触发，但需重新验证键盘驱动路径
- 扩到 2–3 万词时建议加双字母前缀索引，把线性扫描降到区段扫描
