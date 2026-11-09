"""Prepare an offline build for seeed_wio_tracker_L2-tft on this machine.

GitHub is unreachable here, while codeload.github.com and the ghfast.top
mirror are reachable. This script:

  1. downloads every GitHub archive used by the target env into deps/libs/
  2. unpacks the pioarduino platform zip into a local directory and rewrites
     its internal package URLs to the reachable mirror
  3. rewrites all firmware *.ini GitHub URLs to file:// URIs (with .bak copies)
  4. points `platform =` at the local platform directory

It is idempotent: valid downloads are skipped on re-run.
"""
import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile

ROOT = r"<WORKSPACE>"
FW = os.path.join(ROOT, "firmware")
DEPS = os.path.join(ROOT, "deps")
LIBS = os.path.join(DEPS, "libs")
PLATFORM_DIR = os.path.join(DEPS, "platform-espressif32-local")
PLATFORM_ZIP = os.path.join(DEPS, "platform-espressif32.zip")
MIRROR = "https://ghfast.top/"
CURL = shutil.which("curl") or "curl"

os.makedirs(LIBS, exist_ok=True)


def log(*a):
    print(*a, flush=True)


def cfg():
    with open(os.path.join(ROOT, "_env_config.json"), encoding="utf-8") as f:
        return dict(json.load(f))


def target_lib_deps():
    env = dict(cfg()["env:seeed_wio_tracker_L2-tft"])
    return [d.strip() for d in env.get("lib_deps", []) if isinstance(d, str)]


def gh_urls(deps):
    return sorted({d for d in deps if d.startswith("https://github.com/")})


def zip_name(url):
    parts = url.split("/")
    owner, repo = parts[3], parts[4]
    ref = parts[-1].replace(".zip", "")
    tag = "%s__%s__%s" % (owner, repo, ref[:24])
    tag = re.sub(r"[^A-Za-z0-9_.-]", "_", tag)
    return tag[:70] + "__" + hashlib.md5(url.encode()).hexdigest()[:8] + ".zip"


def codeload_fallback(url):
    """https://github.com/O/R/archive/<ref>.zip -> codeload .../zip/<ref>"""
    m = re.match(r"https://github\.com/([^/]+)/([^/]+)/archive/(.+)\.zip$", url)
    if not m:
        return None
    owner, repo, ref = m.groups()
    if ref.startswith("refs/"):
        return "https://codeload.github.com/%s/%s/zip/%s" % (owner, repo, ref)
    # bare tag / commit sha; codeload resolves bare refs too
    return "https://codeload.github.com/%s/%s/zip/%s" % (owner, repo, ref)


def fetch(url):
    dst = os.path.join(LIBS, zip_name(url))
    if os.path.isfile(dst) and zipfile.is_zipfile(dst) and os.path.getsize(dst) > 100:
        return url, dst, "cached", os.path.getsize(dst)
    tmp = dst + ".part"
    attempts = [MIRROR + url]
    fb = codeload_fallback(url)
    if fb:
        attempts.append(fb)
    err = ""
    for src in attempts:
        try:
            subprocess.run(
                [CURL, "-sS", "-L", "--max-time", "120", "-o", tmp, src],
                check=True, capture_output=True, timeout=130,
            )
            if zipfile.is_zipfile(tmp) and os.path.getsize(tmp) > 100:
                os.replace(tmp, dst)
                return url, dst, "ok", os.path.getsize(dst)
            err = "not a zip / empty"
        except Exception as e:  # noqa: BLE001
            err = str(e)[:120]
        if os.path.isfile(tmp):
            os.remove(tmp)
    return url, None, "FAILED: " + err, 0


def main():
    urls = gh_urls(target_lib_deps())
    log("target env GitHub deps:", len(urls))
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        for r in ex.map(fetch, urls):
            results.append(r)
            log("  %-9s %8d  %s" % (r[2][:9], r[3], os.path.basename(r[1] or "")))
    bad = [r for r in results if r[1] is None]
    log("downloaded: %d, failed: %d" % (len(results) - len(bad), len(bad)))
    for u, _, status, _ in bad:
        log("  FAIL", u, status)

    url_map = {u: "file:///" + d.replace("\\", "/") for u, d, _, _ in results if d}
    with open(os.path.join(DEPS, "lib-url-map.json"), "w", encoding="utf-8") as f:
        json.dump(url_map, f, indent=2)

    # --- local platform ---
    if not os.path.isdir(PLATFORM_DIR):
        with zipfile.ZipFile(PLATFORM_ZIP) as z:
            z.extractall(DEPS)
        src = os.path.join(DEPS, "platform-espressif32-55.03.312-1")
        shutil.move(src, PLATFORM_DIR)
    pj = os.path.join(PLATFORM_DIR, "platform.json")
    with open(pj, encoding="utf-8") as f:
        pdata = json.load(f)
    n = 0
    for v in pdata.get("packages", {}).values():
        ver = v.get("version", "")
        if isinstance(ver, str) and ver.startswith("https://github.com/"):
            v["version"] = MIRROR + ver
            n += 1
    with open(pj, "w", encoding="utf-8") as f:
        json.dump(pdata, f, indent=4)
    log("platform.json rewritten package URLs:", n)

    # --- rewrite ini files (only target-relevant URLs become file://) ---
    rewritten = {}
    for base, _dirs, files in os.walk(FW):
        if ".pio" in base:
            continue
        for fn in files:
            if not fn.endswith(".ini"):
                continue
            path = os.path.join(base, fn)
            with open(path, encoding="utf-8") as f:
                text = f.read()
            if "https://github.com/" not in text:
                continue
            new = text
            for u, local in url_map.items():
                new = new.replace(u, local)
            # platform package: local directory
            new = new.replace(
                "https://github.com/pioarduino/platform-espressif32/releases/download/55.03.312-1/platform-espressif32.zip",
                "file:///" + PLATFORM_DIR.replace("\\", "/"),
            )
            # anything else (other boards) -> mirror, so no github.com remains
            new = new.replace("https://github.com/", MIRROR + "https://github.com/")
            if new != text:
                bak = path + ".bak"
                if not os.path.isfile(bak):
                    shutil.copyfile(path, bak)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new)
                rewritten[os.path.relpath(path, FW)] = text.count("https://github.com/")
    log("ini files rewritten:", len(rewritten))
    for k, v in rewritten.items():
        log("  ", k, v, "URLs")
    log("remaining raw github.com refs in firmware ini:")
    left = subprocess.run(
        ["grep", "-rl", "https://github.com/", FW, "--include=*.ini"],
        capture_output=True, text=True,
    ).stdout.strip()
    log(left or "  (none)")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
