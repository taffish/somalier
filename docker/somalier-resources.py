#!/usr/bin/env python3
"""Somalier 显式资源安装：固定下载或用户授权的本地 sites，不在分析时联网。"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time

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
    if path.is_absolute() or ".." in path.parts or not re.fullmatch(r"[A-Za-z0-9_./+-]+", name):
        raise ValueError(f"unsafe member name: {name}")
    return path


def verify(root):
    if not root.is_dir() or root.is_symlink():
        raise ValueError("resource root must be a physical directory")
    sums, ready = root / "SHA256SUMS", root / "READY"
    if not sums.is_file() or not ready.is_file() or digest(sums) != ready.read_text().strip():
        raise ValueError("missing or damaged READY/SHA256SUMS; use a fresh installation root")
    listed = []
    for line in sums.read_text().splitlines():
        checksum, name = line.split("  ", 1)
        safe_relative(name)
        path = root / name
        if not re.fullmatch(r"[a-f0-9]{64}", checksum) or path.is_symlink() or not path.is_file():
            raise ValueError(f"invalid inventory member: {name}")
        if root not in path.resolve().parents or digest(path) != checksum:
            raise ValueError(f"resource member checksum mismatch: {name}")
        listed.append(name)
    receipt = json.loads((root / "resource.json").read_text())
    if receipt.get("schema") != SCHEMA or "resource.json" not in listed:
        raise ValueError("unsupported resource receipt")
    expected = set(listed) | {"READY", "SHA256SUMS"}
    actual = {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() or p.is_symlink()}
    if actual != expected or any(p.is_symlink() for p in root.rglob("*")):
        raise ValueError("extra/missing member or symlink in resource root")
    identity = receipt["resource"]
    payloads = [name for name in listed if name != "resource.json"]
    if len(listed) != len(set(listed)) or receipt.get("members") != len(payloads):
        raise ValueError("duplicate inventory entry or incorrect member count")
    source = receipt["source"]
    if identity in CATALOG:
        item = CATALOG[identity]
        if source != item or len(payloads) != item["files"]:
            raise ValueError("resource receipt does not match the fixed catalog")
        if any(not name.startswith("1kg-somalier/") or not name.endswith(".somalier") for name in payloads):
            raise ValueError("unexpected fixed resource member")
        if sum((root / name).stat().st_size for name in payloads) != item["expanded_bytes"]:
            raise ValueError("fixed resource size differs from catalog")
    elif isinstance(identity, str) and re.fullmatch(r"local-[A-Za-z0-9_.-]+", identity):
        if payloads not in (["sites.vcf"], ["sites.vcf.gz"]):
            raise ValueError("local resource must contain exactly one sites VCF")
        path = root / payloads[0]
        if (source.get("kind") != "sites" or source.get("format") != "file"
                or source.get("files") != 1 or not source.get("license")
                or source.get("sha256") != digest(path)
                or source.get("bytes") != path.stat().st_size
                or source.get("expanded_bytes") != path.stat().st_size):
            raise ValueError("local resource source identity differs from payload")
    else:
        raise ValueError("unknown resource identity")
    print(f"verified resource={identity} files={len(listed)-1}")
    return receipt


def install(args):
    identity = args.resource
    if not identity or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", identity):
        raise ValueError("choose an explicit safe --resource ID; use list to see the catalog")
    item = CATALOG.get(identity)
    source = Path(args.source).resolve() if args.source else None
    if item is None:
        if not identity.startswith("local-") or source is None or not args.sha256 or not args.license_note:
            raise ValueError("local sites require ID local-*, --source, --sha256 and --license-note recording your authorized use/sharing")
        if not re.fullmatch(r"[a-f0-9]{64}", args.sha256):
            raise ValueError("--sha256 must contain 64 lowercase hex digits")
        item = {"kind": "sites", "format": "file", "sha256": args.sha256,
                "bytes": source.stat().st_size, "expanded_bytes": source.stat().st_size,
                "files": 1, "license": args.license_note, "url": "user-authorized-local-file"}
    root = Path(args.resource_root).resolve()
    target = root / identity
    if args.dry_run:
        print(json.dumps({"resource": identity, "target": str(target), "source": item,
                          "required_free_bytes": item["bytes"] + item["expanded_bytes"] + 67108864,
                          "network": "none" if source else "explicit HTTPS download",
                          "existing": "full inventory verified; never overwritten"}, indent=2))
        return
    if target.exists() or target.is_symlink():
        receipt = verify(target)
        if receipt["resource"] != identity or receipt["source"]["sha256"] != item["sha256"]:
            raise ValueError("existing resource identity differs; choose a new immutable ID/root")
        print("already installed; no writes or download")
        return
    root.mkdir(parents=True, exist_ok=True)
    lock = root / f".{identity}.lock"
    try:
        lock.mkdir(mode=0o700)
    except FileExistsError:
        raise ValueError(f"installation lock exists: {lock}; do not remove until its owner is confirmed inactive") from None
    stage = None
    try:
        (lock / "owner.json").write_text(json.dumps({"pid": os.getpid(), "time": time.time()}))
        required = item["bytes"] + item["expanded_bytes"] + 67108864
        if shutil.disk_usage(root).free < required:
            raise ValueError(f"insufficient space; require at least {required} free bytes")
        if source is None:
            cache = root / ".downloads"
            cache.mkdir(mode=0o700, exist_ok=True)
            source = cache / (item["sha256"] + ".part")
            if source.exists() and source.stat().st_size >= item["bytes"]:
                if source.stat().st_size != item["bytes"] or digest(source) != item["sha256"]:
                    raise ValueError(f"corrupt download cache: {source}; remove only this exact file after inspection")
            else:
                print(f"downloading resource={identity} resume={source.exists()}", flush=True)
                subprocess.run(["curl", "--fail", "--location", "--proto", "=https", "--proto-redir", "=https",
                                "--retry", "3", "--retry-all-errors", "--connect-timeout", "30",
                                "--max-time", "900", "--continue-at", "-", "--output", str(source), item["url"]], check=True)
        if source.stat().st_size != item["bytes"] or digest(source) != item["sha256"]:
            raise ValueError("source bytes/checksum mismatch; nothing promoted; cached download retained for diagnosis")
        stage = Path(tempfile.mkdtemp(prefix=f".{identity}.stage-", dir=root))
        if item["format"] == "tar.gz":
            with tarfile.open(source, "r:gz") as archive:
                members = archive.getmembers()
                files = [m for m in members if m.isfile()]
                if len(files) != item["files"] or sum(m.size for m in files) != item["expanded_bytes"]:
                    raise ValueError("archive inventory count/size differs from fixed resource")
                for member in members:
                    path = safe_relative(member.name)
                    if path.parts[0] != "1kg-somalier" or not (member.isdir() or member.isfile()):
                        raise ValueError("archive contains unexpected path/type")
                    dest = stage / str(path)
                    if member.isdir():
                        dest.mkdir(parents=True, exist_ok=True)
                    else:
                        if not member.name.endswith(".somalier"):
                            raise ValueError("unexpected ancestry archive member")
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        with archive.extractfile(member) as src, dest.open("xb") as out:
                            shutil.copyfileobj(src, out)
        else:
            suffix = ".vcf.gz" if source.name.endswith(".gz") else ".vcf"
            import gzip
            opener = gzip.open if suffix.endswith(".gz") else open
            with opener(source, "rt") as handle:
                if not handle.readline().startswith("##fileformat=VCF"):
                    raise ValueError("local sites must be a VCF or gzip VCF")
            shutil.copyfile(source, stage / ("sites" + suffix))
        receipt = {"schema": SCHEMA, "resource": identity, "source": item,
                   "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "uid": os.getuid(), "analysis_network": "none", "members": item["files"]}
        (stage / "resource.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
        files = sorted(p for p in stage.rglob("*") if p.is_file())
        (stage / "SHA256SUMS").write_text("".join(f"{digest(p)}  {p.relative_to(stage)}\n" for p in files))
        (stage / "READY").write_text(digest(stage / "SHA256SUMS") + "\n")
        for path in stage.rglob("*"):
            path.chmod(0o755 if path.is_dir() else 0o644)
        stage.chmod(0o755)
        verify(stage)
        if target.exists():
            raise ValueError("target appeared during install; refusing overwrite")
        stage.rename(target)
        stage = None
        print(f"installed resource={identity} root={target}; analysis must bind it read-only")
    finally:
        if stage is not None:
            shutil.rmtree(stage)
        (lock / "owner.json").unlink(missing_ok=True)
        lock.rmdir()


def main():
    parser = argparse.ArgumentParser(description="Install fixed Somalier resources explicitly; analysis never downloads resources.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="show fixed catalog; nothing is downloaded")
    check = sub.add_parser("verify", help="verify every installed member, offline and read-only")
    check.add_argument("root")
    get = sub.add_parser("install", help="atomic fixed resource or authorized local-sites installation")
    get.add_argument("--resource", required=True)
    get.add_argument("--resource-root", required=True, help="writable parent; wrapper installation bind is /resource-install")
    get.add_argument("--source", help="optional local archive; required for local-* sites")
    get.add_argument("--sha256", help="required checksum for local-* sites")
    get.add_argument("--license-note", help="local-sites authorization/attribution; does not grant rights")
    get.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    os.umask(0o022)
    if args.command == "list":
        print(json.dumps(CATALOG, indent=2))
    elif args.command == "verify":
        verify(Path(args.root).resolve())
    else:
        install(args)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, tarfile.TarError, subprocess.CalledProcessError) as exc:
        print(f"somalier-resources: {exc}", file=sys.stderr)
        sys.exit(1)
