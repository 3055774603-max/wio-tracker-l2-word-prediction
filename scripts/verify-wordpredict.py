"""Equivalent-model verification of device-ui WordPredict.cpp.

This machine has no host C++ compiler, so the C++ algorithm is transcribed
line-for-line into Python and exercised against the actual flash word list.
Any assertion failure means the firmware logic (not the model) needs review.
"""
import json
import os
import re

ROOT = r"<WORKSPACE>/libs/device-ui/source/graphics/common"
INC = os.path.join(ROOT, "predict_wordlist.inc")
CPP = os.path.join(ROOT, "WordPredict.cpp")
KMAX = 16

src = open(INC, encoding="utf-8").read()
body = src.split("static const char kPredictWordList[] =", 1)[1]
literals = re.findall(r'"((?:[^"\\]|\\.)*)"', body)
blob = "".join(literals).replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")
words = [w for w in blob.split("\n") if w]

print("=== word list ===")
print("count:", len(words))
print("bytes (incl separators):", len(blob.encode()))
print("longest word:", max(len(w) for w in words), "->", max(words, key=len))
print("all [a-z] lowercase:", all(re.fullmatch(r"[a-z]+", w) for w in words))
print("duplicates:", len(words) - len(set(words)))
print("words >= KMAX (silently skipped by algorithm):", [w for w in words if len(w) >= KMAX][:10])
print("first 15:", words[:15])


def lower(c):
    return chr(ord(c) + 32) if "A" <= c <= "Z" else c


def predict(prefix, max_count=3):
    """Line-for-line transcription of WordPredict::predict()."""
    if max_count == 0 or not prefix:
        return []
    prefix_len = len(prefix)
    if prefix_len == 0 or prefix_len >= KMAX - 1:
        return []
    lower_prefix = [lower(c) for c in prefix]
    all_upper = True
    for i in range(prefix_len):
        if lower_prefix[i] == prefix[i]:
            all_upper = False
    first_upper = ("A" <= prefix[0] <= "Z") and not all_upper
    out = []
    for w in words:
        if len(out) >= max_count:
            break
        if len(w) > prefix_len and len(w) < KMAX and all(lower(w[i]) == lower_prefix[i] for i in range(prefix_len)):
            if all_upper:
                s = "".join(chr(ord(w[i]) - 32) for i in range(len(w)))
            elif first_upper:
                s = chr(ord(w[0]) - 32) + w[1:]
            else:
                s = w
            out.append(s)
    return out


print("\n=== behaviour tests ===")
cases = [
    ("hel", 3), ("HEL", 3), ("Hel", 3), ("th", 3), ("wor", 3),
    ("", 3), ("a" * 15, 3), ("123", 3), ("zzzz", 3), ("hel", 1),
]
for p, n in cases:
    print(f"  predict({p!r:20s}, {n}) -> {predict(p, n)}")

print("\n=== assertions ===")
res = predict("hel", 3)
assert len(res) == 3, "hel should yield 3 candidates"
assert all(w.lower().startswith("hel") for w in res), "all candidates must match prefix"
assert predict("HEL", 3) == [w.upper() for w in res], "ALL-CAPS prefix -> ALL-CAPS output"
assert predict("Hel", 3) == [w.capitalize() for w in res], "Capitalized prefix -> Capitalized output"
assert predict("", 3) == [], "empty prefix -> no candidates"
assert predict("a" * 15, 3) == [], "prefix >= KMAX-1 -> no candidates"
assert len(predict("hel", 1)) == 1, "maxCount respected"
assert predict("zzzz", 3) == [], "nonsense prefix -> no candidates"
assert max(len(w) for w in words) < KMAX, "no word may be silently dropped"
assert len(words) == len(set(words)), "word list must not contain duplicates"
# candidates must be in descending word-frequency order (= list order)
idx = [words.index(w.lower()) for w in res]
assert idx == sorted(idx), "candidates must keep frequency order"
print("  ALL PASS")

print("\n=== HANDOFF claim check (hel -> hello/help/held) ===")
for w in ("hello", "help", "held"):
    print(f"  {w:6s} in list: {w in words}   in hel candidates: {w in res}")

with open(r"<WORKSPACE>/_wordpredict-verify.json", "w", encoding="utf-8") as f:
    json.dump({"word_count": len(words), "bytes": len(blob.encode()),
               "hel_candidates": res, "cases": {f"{p}|{n}": predict(p, n) for p, n in cases}},
              f, indent=2)
