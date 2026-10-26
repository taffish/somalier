"""Shared, read-only validation for host discovery and container installation."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys

SCHEMA = "taffish.somalier.resource.v1"
CATALOG = {
    "1kg-3479773": {
        "url": "https://zenodo.org/api/records/3479773/files/1kg.somalier.tar.gz/content",
        "sha256": "b2b7959cfd6d37d1ac7a96e03aeb13707cfe84e5c3a208329220712a935c5a1e",
        "bytes": 82856769, "expanded_bytes": 533870328, "files": 2504,
        "license": "CC-BY-4.0", "doi": "10.5281/zenodo.3479773",
        "attribution": "Brent Pedersen, somalier files for thousand genomes high-coverage VCF for 2504 samples, dataset v0.2.3 (2019).",
        "kind": "ancestry-sketches", "format": "tar.gz",
    }
}


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def safe_relative(name):
    path = PurePosixPath(name)
    if (not isinstance(name, str) or path.is_absolute()
            or any(p in ("", ".", "..") for p in name.split("/"))
            or not re.fullmatch(r"[A-Za-z0-9_./+-]+", name)):
        raise ValueError(f"unsafe member name: {name}")
    return path


def strict_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate receipt key: {key}")
            result[key] = value
        return result
    return json.loads(path.read_text(), object_pairs_hook=pairs)


def verify(root, expected_id=None):
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("resource root must resolve to a directory")
    actual, directories = set(), set()
    for base, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            p = Path(base) / name
            mode = p.lstat().st_mode
            rel = str(p.relative_to(root))
            safe_relative(rel)
            if stat.S_ISDIR(mode):
                directories.add(rel)
            elif stat.S_ISREG(mode):
                actual.add(rel)
            else:
                raise ValueError(f"non-regular member or symlink: {rel}")
    if not {"READY", "SHA256SUMS", "resource.json"}.issubset(actual):
        raise ValueError("missing READY/SHA256SUMS/resource.json")
    sums = root / "SHA256SUMS"
    if (root / "READY").read_text() != digest(sums) + "\n":
        raise ValueError("damaged READY/SHA256SUMS")
    listed = []
    for line in sums.read_text().splitlines():
        checksum, name = line.split("  ", 1)
        safe_relative(name)
        if (not re.fullmatch(r"[a-f0-9]{64}", checksum) or name not in actual
                or name in ("READY", "SHA256SUMS") or name in listed):
            raise ValueError(f"invalid inventory member: {name}")
        if digest(root / name) != checksum:
            raise ValueError(f"resource member checksum mismatch: {name}")
        listed.append(name)
    if "resource.json" not in listed or actual != set(listed) | {"READY", "SHA256SUMS"}:
        raise ValueError("extra/missing inventory member")
    expected_dirs = {str(parent) for name in listed for parent in PurePosixPath(name).parents
                     if str(parent) != "."}
    if directories != expected_dirs:
        raise ValueError("extra/missing resource directory")
    receipt = strict_json(root / "resource.json")
    if receipt.get("schema") != SCHEMA:
        raise ValueError("unsupported resource receipt")
    identity, source = receipt.get("resource"), receipt.get("source")
    if not isinstance(identity, str) or not isinstance(source, dict):
        raise ValueError("invalid resource/source identity")
    if expected_id and identity != expected_id:
        raise ValueError("selected resource identity mismatch")
    payloads = [n for n in listed if n != "resource.json"]
    if type(receipt.get("members")) is not int or receipt["members"] != len(payloads):
        raise ValueError("incorrect member count")
    if identity in CATALOG:
        item = CATALOG[identity]
        if source != item or len(payloads) != item["files"]:
            raise ValueError("resource receipt differs from fixed catalog")
        if any(not re.fullmatch(r"1kg-somalier/[A-Za-z0-9_.+-]+\.somalier", n) for n in payloads):
            raise ValueError("unexpected fixed resource member")
        if sum((root / n).stat().st_size for n in payloads) != item["expanded_bytes"]:
            raise ValueError("fixed resource expanded size differs from catalog")
    elif re.fullmatch(r"local-[A-Za-z0-9_.-]+", identity):
        if payloads not in (["sites.vcf"], ["sites.vcf.gz"]):
            raise ValueError("local resource must contain exactly one sites VCF")
        path = root / payloads[0]
        if (source.get("kind") != "sites" or source.get("format") != "file"
                or type(source.get("files")) is not int or source["files"] != 1
                or not isinstance(source.get("license"), str) or not source["license"].strip()
                or source.get("sha256") != digest(path)
                or type(source.get("bytes")) is not int or source["bytes"] != path.stat().st_size
                or type(source.get("expanded_bytes")) is not int or source["expanded_bytes"] != path.stat().st_size
                or source.get("url") != "user-authorized-local-file"):
            raise ValueError("local resource source identity differs from payload")
    else:
        raise ValueError("unknown resource identity")
    return receipt


if __name__ == "__main__":
    try:
        verify(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"somalier-resources: {exc}", file=sys.stderr)
        sys.exit(1)
