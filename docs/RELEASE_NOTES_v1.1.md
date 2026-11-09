# L2 联想输入固件 — v1.1：词库扩展（2026-11-09）

用户确认 v1.0「很成功」后，按档 A 扩展词库。**唯一代码改动是 `predict_wordlist.inc`**，算法、UI、烧录参数全部不变。

## 相对 v1.0 的变化

| 项 | v1.0 | v1.1 |
|---|---|---|
| 词数 | 3,000 | **10,000** |
| `kPredictWordList` | 21,307 B (20.8 KiB) | **76,015 B (74.2 KiB)** |
| app bin | 3,891,696 B (59.4%) | **3,946,400 B (60.2%)** |
| app 分区剩余 | 2.54 MiB | **2.49 MiB** |
| 最长词 | 14 | 14 |

## 词表构造规则

1. 来源 `google-10000-english`（MIT）与主仓同源；不足部分用同仓 `20k.txt` 补足
2. **前 3000 词字节级不变** → 所有已验收候选（`hel`/`hell`/`he`/`str`/`wea`…）零回退
3. 追加部分按严格词频降序，纯 `[a-z]`、2–14 字符、无重复
4. 精确过滤 114 个明确成人/粗俗词（网页语料 3000 名后集中出现）；中性词 `analysis`/`analog`/`adult`/`naked` 等保留
5. 丢弃 >14 字符词，避免 320px 三按钮候选栏文字截断
6. `wordlist_build.py` + `wordlist_source/` 可完整复现本词表；`src_snapshot/predict_wordlist_v1.0_3000words.inc` 是原表备份

## 验证

- 编译 `BUILD_EXIT=0`（4m32s）；elf 中 `kPredictWordList` = `0x128ef` = 76,015 B
- elf 内含新增词 `noise/balancing/width/colour`，不含被过滤词，不含 >14 字符词
- COM9 按 **dio** 烧录 5 段全 Hash verified；串口 0 boot loop / 崩溃
- `serial_v11.log`：31 次候选显示、4 次点击 `shown==inserted` 全一致
- 新词生效证据：`here -> herein / hereby`（v1.0 下 `here` 为 0 候选）
- Python 等价算法对 25 个前缀回归：旧候选始终是新结果的前缀子序列 → **ZERO REGRESSION**

## 固件清单与烧录

| 文件 | 偏移 | 大小 |
|---|---|---|
| `firmware/bootloader.bin` | 0x0 | 19,968 B |
| `firmware/partitions.bin` | 0x8000 | 3,072 B |
| `firmware/boot_app0.bin` | 0xe000 | 8,192 B |
| `firmware/firmware-seeed_wio_tracker_L2-tft-2.8.3.bin` | 0x10000 | 3,946,400 B |
| `firmware/littlefs-seeed_wio_tracker_L2-tft-2.8.3.bin` | 0xc90000 | 3,538,944 B |
| `firmware/firmware-seeed_wio_tracker_L2-tft-2.8.3.factory.bin` | 0x0 (合并镜像) | 4,011,936 B |

一键：`flash.bat COM9`（**必须 dio**）。回滚到 v1.0：在 `backup_20261109_L2_wordpredict_v1.0` 目录执行其 `flash.bat`。

## 已知项

- 固件仍含 `WordPredict:` 诊断 WARN 日志（每次按键约 2 条），不影响 UI；需要安静版可去掉后再编一轮
- `kMaxCandidates = 3` 未改；词表扩展只提升覆盖范围，不增加候选个数
- `hel` 仍出 `help / held / helpful`，`hello` 排第 4（词频顺序）；如需让 `hel` 出 `hello` 需局部调整词表顺序

生成时间：2026-11-09T12:17:14.603671+08:00
