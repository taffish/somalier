#!/usr/bin/env python3
"""构建期保留实际 Nim 运行库声明，并拒绝锁定依赖的许可覆盖缺口。"""
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

root, cache, lock_path = map(Path, sys.argv[1:])
lock = json.loads(lock_path.read_text())["packages"]
manifest = json.loads((root / "nim-dependencies/manifest.json").read_text())
used = set()
runtime = root / "nim-runtime"
runtime.mkdir()
shutil.copyfile("/opt/nim/copying.txt", runtime / "COPYING.txt")
sources = {"COPYING.txt": "/opt/nim/copying.txt"}
for path in sorted(cache.glob("*.c")):
    name = path.name
    match = re.search(r"@spkgs2@s([^@]+)@s", name)
    if match:
        package_dir = match.group(1)
        matches = [package for package, item in lock.items()
                   if package_dir == f"{package}-{item['version']}-{item['checksums']['sha1']}"]
        if len(matches) != 1:
            raise SystemExit(f"unmapped compiled Nim dependency: {package_dir}")
        used.add(matches[0])
    if "@sopt@snim@s" not in name:
        continue
    relative = name.split("@sopt@snim@s", 1)[1].removesuffix(".c").replace("@s", "/")
    source = Path("/opt/nim") / relative
    prelude = []
    for line in source.read_text().splitlines(keepends=True):
        if line.strip() and not line.lstrip().startswith("#"):
            break
        prelude.append(line)
    text = "".join(prelude)
    if "copyright" in text.lower():
        filename = relative.replace("/", "_") + ".txt"
        (runtime / filename).write_text(text)
        sources[filename] = str(source)
for package in used:
    if not manifest["packages"][package]["files"]:
        raise SystemExit(f"compiled dependency without retained notices: {package}")
for name in ("lib_std_private_dragonbox.nim.txt", "lib_std_private_schubfach.nim.txt"):
    if not (runtime / name).is_file():
        raise SystemExit(f"missing expected Nim runtime attribution: {name}")
receipt = {"nim": "2.2.4", "compiled_packages": sorted(used), "files": [
    {"file": name, "source": source,
     "sha256": hashlib.sha256((runtime / name).read_bytes()).hexdigest()}
    for name, source in sorted(sources.items())]}
(runtime / "manifest.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(f"nim-notices compiled-packages={len(used)} runtime-notices={len(sources)} PASS")
