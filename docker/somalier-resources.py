#!/usr/bin/env python3
"""Explicit resource setup; no implicit downloads during analysis."""
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
import signal
import stat
import ctypes

sys.path.insert(0, "/opt/somalier/lib")
from resource_validation import CATALOG, SCHEMA, digest, safe_relative, verify


def promote(source, target):
    # Linux renameat2 refuses even an empty competing directory or dangling link.
    libc = ctypes.CDLL(None, use_errno=True)
    rename = libc.renameat2
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(-100, os.fsencode(source), -100, os.fsencode(target), 1) != 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code), str(target))

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
        receipt = verify(target, identity)
        if receipt["resource"] != identity or receipt["source"]["sha256"] != item["sha256"]:
            raise ValueError("existing resource identity differs; choose a new immutable ID/root")
        print("already installed; no writes or download")
        return
    root.mkdir(parents=True, exist_ok=True)
    lock = root / f".{identity}.lock"
    owned = None
    stage = None
    old_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})
    try:
        try:
            lock.mkdir(mode=0o700)
            owned = (lock.lstat().st_dev, lock.lstat().st_ino)
        except FileExistsError:
            raise ValueError(f"installation lock exists: {lock}; inspect its owner before manual recovery") from None
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)
        (lock / "owner.json").write_text(json.dumps({"pid": os.getpid(), "time": time.time()}))
        required = item["bytes"] + item["expanded_bytes"] + 67108864
        if shutil.disk_usage(root).free < required:
            raise ValueError(f"insufficient space; require at least {required} free bytes")
        if source is None:
            cache = root / ".downloads"
            cache.mkdir(mode=0o700, exist_ok=True)
            cs = cache.lstat()
            if not stat.S_ISDIR(cs.st_mode) or cs.st_uid != os.getuid() or stat.S_IMODE(cs.st_mode) != 0o700:
                raise ValueError("download cache must be a private owned 0700 physical directory")
            source = cache / (item["sha256"] + ".part")
            if source.exists() or source.is_symlink():
                ss = source.lstat()
                if not stat.S_ISREG(ss.st_mode) or ss.st_nlink != 1 or ss.st_uid != os.getuid():
                    raise ValueError("download partial must be an owned regular non-linked file")
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
        stage = Path(tempfile.mkdtemp(prefix=f".{identity}.stage-", dir=lock))
        if item["format"] == "tar.gz":
            with tarfile.open(source, "r:gz") as archive:
                members = archive.getmembers()
                files = [m for m in members if m.isfile()]
                if len(files) != item["files"] or sum(m.size for m in files) != item["expanded_bytes"]:
                    raise ValueError("archive inventory count/size differs from fixed resource")
                for member in members:
                    path = safe_relative(member.name.rstrip("/"))
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
        verify(stage, identity)
        if target.exists() or target.is_symlink():
            raise ValueError("target appeared during install; refusing overwrite")
        promote(stage, target)
        stage = None
        print(f"installed resource={identity} root={target}; analysis must bind it read-only")
    finally:
        # Only this transaction's inode may be removed. Old staging stays untouched.
        signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})
        try:
            if owned is not None:
                if (not lock.is_symlink() and lock.is_dir()
                        and (lock.lstat().st_dev, lock.lstat().st_ino) == owned):
                    shutil.rmtree(lock)
                else:
                    raise ValueError("lock ownership changed; retained all recovery data")
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)


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
        receipt = verify(Path(args.root))
        print(f"verified resource={receipt['resource']} files={receipt['members']}")
    else:
        install(args)


if __name__ == "__main__":
    try:
        def interrupted(signum, frame):
            raise SystemExit(128 + signum)
        signal.signal(signal.SIGINT, interrupted)
        signal.signal(signal.SIGTERM, interrupted)
        main()
    except (ValueError, OSError, KeyError, tarfile.TarError, subprocess.CalledProcessError) as exc:
        print(f"somalier-resources: {exc}", file=sys.stderr)
        sys.exit(1)
