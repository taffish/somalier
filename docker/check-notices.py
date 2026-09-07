#!/usr/bin/env python3
"""离线、只读、轻量验证实际分发的许可文件与锁定依赖身份。"""
import hashlib
import json
from pathlib import Path

root = Path("/opt/somalier/share/licenses")
lock_file = Path("/opt/somalier/share/doc/somalier/nimble.lock")
manifest = json.loads((root / "nim-dependencies/manifest.json").read_text())
lock = json.loads(lock_file.read_text())["packages"]
if hashlib.sha256(lock_file.read_bytes()).hexdigest() != manifest["lock_sha256"]:
    raise SystemExit("notice inventory does not match nimble.lock")
if set(manifest["packages"]) != set(lock):
    raise SystemExit("notice inventory has different dependency membership")
count = 0
for package, item in manifest["packages"].items():
    if (item["commit"], item["version"]) != (lock[package]["vcsRevision"], lock[package]["version"]):
        raise SystemExit(f"notice version differs: {package}")
    for entry in item["files"]:
        path = root / "nim-dependencies" / entry["file"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise SystemExit(f"notice checksum mismatch: {path}")
        count += 1
runtime = json.loads((root / "nim-runtime/manifest.json").read_text())
for package in runtime["compiled_packages"]:
    if not manifest["packages"][package]["files"]:
        raise SystemExit(f"compiled package has no retained notice: {package}")
for entry in runtime["files"]:
    path = root / "nim-runtime" / entry["file"]
    if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
        raise SystemExit(f"Nim runtime notice checksum mismatch: {path}")
for package in ("libopenblas0-pthread", "libhts3t64", "python3.13"):
    path = Path("/usr/share/doc") / package / "copyright"
    if not path.is_file() or path.stat().st_size == 0:
        raise SystemExit(f"missing Debian runtime copyright: {package}")
if hashlib.sha256((root / "BOOST-1.0.txt").read_bytes()).hexdigest() != "c9bff75738922193e67fa726fa225535870d2aa1059f91452c411736284ad566":
    raise SystemExit("Boost license checksum mismatch for Nim floating point runtime")
print(f"notices=locked-nim-{count}-runtime-{len(runtime['files'])}-debian PASS")
