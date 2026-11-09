# 词表

| 文件 | 说明 |
|---|---|
| `google-10000-english.txt` | Peter Norvig 的 Google Web Trillion Word Corpus 前 10000 词（MIT） |
| `google-20k.txt` | 同仓 20000 词表，用于补足到 10000 个有效词 |
| `predict_wordlist_v1.0_3000words.inc` | v1.0 原始 3000 词表（复现基底） |
| `build_wordlist.py` | 可复现生成脚本 |

## 生成规则

```
python wordlist/build_wordlist.py
```

1. 前 3000 词**字节级保留**，保证已验收候选零回退
2. 追加词按同源词频降序，纯 `[a-z]`、2–14 字符、无重复
3. 精确过滤 114 个明确成人/粗俗词（网页语料 3000 名后集中出现）；`analysis` / `analog` / `adult` / `naked` 等中性词保留
4. 丢弃 >14 字符词，避免 320 px 三按钮候选栏文字截断
5. 输出 `libs/device-ui/source/graphics/common/predict_wordlist.inc`，10000 词、76,015 B

词表是 `static const char[]`，落在 `.flash.rodata`（DROM，flash MMU 映射），**不占 DRAM**。

## 为什么过滤

`google-10000-english` 来自网页语料，3000 名之后紧跟着一批成人站高频词。直接放进家用设备的候选栏不合适。过滤用**精确集合**而非子串匹配，避免误伤 `analysis`、`analyst`、`analog`、`canal`、`therapeutic` 等正常词。

## 已知边界

- `kMaxCandidates = 3`：词表再大也只显示前 3 个匹配词
- `kMaxWordLen = 16`（含 `\0`）：长于 15 字符的词会被静默丢弃，所以生成时限制 14
- `predict()` 线性扫描、凑满 3 个提前退出；10000 词最坏扫描约 74 KiB，实测无卡顿
- 若扩到 2–3 万词，建议加双字母前缀偏移索引（26×26×4 B ≈ 2.7 KiB）
