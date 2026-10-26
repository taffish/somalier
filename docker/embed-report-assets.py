#!/usr/bin/env python3
"""Inline upstream HTML assets without changing statistics or interactions."""
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess
import sys

source, cache, manifest = map(Path, sys.argv[1:])
cache.mkdir(parents=True, exist_ok=True)
templates = [source / "src/somalierpkg" / name for name in
             ("results.html", "ancestry.html", "abplot.html", "depthview.html")]
content = {p: p.read_text() for p in templates}
for item in json.loads(manifest.read_text()):
    asset = cache / item["name"]
    if not asset.exists():
        subprocess.run(["curl", "--fail", "--location", "--retry", "5",
                        "--retry-all-errors", "--connect-timeout", "30", "--max-time", "300",
                        item["url"], "-o", str(asset)], check=True)
    raw = asset.read_bytes()
    if hashlib.sha256(raw).hexdigest() != item["sha256"]:
        raise SystemExit(f"report asset checksum mismatch: {asset.name}")
    text = re.sub(r"(?m)^//# sourceMappingURL=.*$", "", raw.decode())
    # Match only standalone directives, never text inside JavaScript strings.
    text = re.sub(r"(?m)^[ \t]*/\*# sourceMappingURL=[^\r\n]*\*/[ \t]*$", "", text)
    if item.get("kind") == "license":
        credit = f'<template data-taffish-license="{asset.name}">{html.escape(text)}</template>'
        content = {p: value.replace("</head>", credit + "\n</head>") for p, value in content.items()}
        continue
    url = item.get("replaces", item["url"])
    if asset.suffix == ".js":
        old = f'<script src="{url}"></script>'
        text = re.sub(r"</script", r"<\\/script", text, flags=re.I)
        new = f'<script data-taffish-asset="{asset.name}">\n{text}\n</script>'
    else:
        old = f'<link rel="stylesheet" href="{url}">'
        new = f'<style data-taffish-asset="{asset.name}">\n{text}\n</style>'
    if not any(old in value for value in content.values()):
        raise SystemExit(f"upstream template changed: {url}")
    content = {p: value.replace(old, new) for p, value in content.items()}
for path, value in content.items():
    if re.search(r'<(?:script|link)\b[^>]*(?:src|href)=["\']https?://', value):
        raise SystemExit(f"unresolved browser runtime dependency: {path}")
    path.write_text(value)
    print(f"offline-template={path.name} bytes={path.stat().st_size}")
