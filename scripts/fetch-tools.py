"""Pre-fetch remaining pioarduino tool packages and pin platform.json to file://.

The GitHub mirror is unstable for large assets (PlatformIO's downloader fails
mid-stream). curl with retries is used instead, then both platform.json copies
(the local source dir and the installed core copy) are rewritten to local files.
Idempotent: valid archives are skipped.
"""
import concurrent.futures
import json
import os
import shutil
import subprocess
import zipfile

ROOT = r"<WORKSPACE>"
CORE = os.path.join(ROOT, ".pio-core")
TOOLS = os.path.join(ROOT, "deps", "tools")
os.makedirs(TOOLS, exist_ok=True)
PJS = [
    os.path.join(ROOT, "deps", "platform-espressif32-local", "platform.json"),
    os.path.join(CORE, "platforms", "espressif32", "platform.json"),
]
CURL = shutil.which("curl") or "curl"


def installed_keys():
    out = set()
    pkgdir = os.path.join(CORE, "packages")
    if os.path.isdir(pkgdir):
        for name in os.listdir(pkgdir):
            out.add(name.split("@", 1)[0].lower())
    return out


def valid(path):
    if not os.path.isfile(path) or os.path.getsize(path) < 1000:
        return False
    if path.endswith(".zip"):
        return zipfile.is_zipfile(path)
    with open(path, "rb") as f:
        head = f.read(6)
    return head.startswith(b"\xfd7zXZ") or head.startswith(b"\x1f\x8b")


def fetch(item):
    key, url = item
    dst = os.path.join(TOOLS, url.rsplit("/", 1)[-1])
    if valid(dst):
        return key, dst, "cached", os.path.getsize(dst)
    tmp = dst + ".part"
    for attempt in range(4):
        try:
            subprocess.run(
                [CURL, "-sS", "-L", "-f", "--retry", "3", "--retry-all-errors",
                 "--retry-delay", "2", "--connect-timeout", "30", "--max-time", "900",
                 "-o", tmp, url],
                check=True, capture_output=True, timeout=920,
            )
            if valid(tmp):
                os.replace(tmp, dst)
                return key, dst, "ok", os.path.getsize(dst)
        except Exception:
            pass
        if os.path.isfile(tmp):
            os.remove(tmp)
    return key, None, "FAILED", 0


def main():
    installed = installed_keys()
    data = json.load(open(PJS[0], encoding="utf-8"))
    todo = [(k, v["version"]) for k, v in data["packages"].items()
            if isinstance(v.get("version"), str)
            and v["version"].startswith("http")
            and k.lower() not in installed]
    print("installed packages:", len(installed), "| remaining to fetch:", len(todo), flush=True)
    for k, u in todo:
        print("  ", k, u.rsplit("/", 1)[-1], flush=True)

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        for r in ex.map(fetch, todo):
            results.append(r)
            print("  %-8s %10d  %s" % (r[2], r[3], os.path.basename(r[1] or "?")), flush=True)
    bad = [r for r in results if not r[1]]
    print("fetched:", len(results) - len(bad), "failed:", len(bad), flush=True)

    mapping = {}
    for key, path, _st, _sz in results:
        if path:
            mapping[dict(todo)[key]] = "file://" + path.replace("\\", "/")

    for pj in PJS:
        if not os.path.isfile(pj):
            print("missing platform.json:", pj); continue
        bak = pj + ".orig"
        if not os.path.isfile(bak):
            shutil.copyfile(pj, bak)
        d = json.load(open(pj, encoding="utf-8"))
        n = 0
        for v in d.get("packages", {}).values():
            ver = v.get("version", "")
            if isinstance(ver, str) and ver in mapping:
                v["version"] = mapping[ver]; n += 1
        with open(pj, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=4)
        print("rewrote", n, "URLs in", pj, flush=True)

    left = [v["version"] for v in json.load(open(PJS[1], encoding="utf-8"))["packages"].values()
            if isinstance(v.get("version"), str) and v["version"].startswith("http")]
    print("remaining remote package URLs:", len(left), flush=True)
    for u in left:
        print("   ", u, flush=True)
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
