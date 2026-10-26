#!/usr/bin/env python3
"""Regression: an embedded source-map string is executable code, not a comment."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

app = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="somalier-assets-") as work:
    root = Path(work)
    source = root / "source/src/somalierpkg"
    cache = root / "cache"
    source.mkdir(parents=True)
    cache.mkdir()
    literal = 'const code = "/*# sourceMappingURL=".concat("test", " */");'
    raw = (literal + '\n/*# sourceMappingURL=standalone.map */\n//# sourceMappingURL=line.map\n').encode()
    (cache / "fixture.js").write_bytes(raw)
    manifest = root / "manifest.json"
    manifest.write_text(json.dumps([{"name": "fixture.js", "url": "https://example.invalid/fixture.js",
                                     "sha256": hashlib.sha256(raw).hexdigest()}]))
    for name in ("results.html", "ancestry.html", "abplot.html", "depthview.html"):
        (source / name).write_text('<head><script src="https://example.invalid/fixture.js"></script></head>')
    subprocess.run([sys.executable, str(app / "docker/embed-report-assets.py"),
                    str(root / "source"), str(cache), str(manifest)], check=True)
    for path in source.iterdir():
        result = path.read_text()
        assert literal in result, path
        assert "standalone.map" not in result and "line.map" not in result, path
print("report asset string preservation PASS")
