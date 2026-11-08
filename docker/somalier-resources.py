#!/usr/bin/env python3
"""Explicit resource setup; no implicit downloads during analysis."""
import argparse
from contextlib import contextmanager, ExitStack
import json
import os
from pathlib import Path
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


CATCH = {signal.SIGHUP, signal.SIGINT, signal.SIGTERM}


@contextmanager
def defer_signals():
    mask = signal.pthread_sigmask(signal.SIG_BLOCK, CATCH)
    try:
        yield
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, mask)


def inode(path):
    meta = path.lstat()
    return meta.st_dev, meta.st_ino


class Owned:
    """Remove only recorded objects, through pinned parents, in reverse creation order."""
    def __init__(self, stack):
        self.stack = stack
        self.nodes = []
        self.staged = False

    def pin(self, path):
        fd = os.open(path, os.O_DIRECTORY | os.O_NOFOLLOW | os.O_RDONLY)
        self.stack.callback(os.close, fd)
        return Path(f"/proc/self/fd/{fd}")

    def directory(self, parent, name=None):
        with defer_signals():
            if name is None:
                path = Path(tempfile.mkdtemp(prefix=".stage-", dir=parent))
            else:
                path = parent / name
                path.mkdir(mode=0o700)
            handle = self.pin(path)
            self.nodes.append((path, inode(path), True, self.staged))
            return handle

    @contextmanager
    def file(self, path):
        with defer_signals():
            stream = path.open("xb")
            self.stack.callback(stream.close)
            self.nodes.append((path, inode(path), False, self.staged))
        with stream:
            yield stream

    def write(self, path, text):
        with self.file(path) as stream:
            stream.write(text.encode("utf-8"))

    def cleanup(self, promoted):
        problems = []
        for path, ident, directory, staged in reversed(self.nodes):
            if promoted and staged:
                continue
            try:
                if inode(path) != ident:
                    raise ValueError("entry was replaced")
                path.rmdir() if directory else path.unlink()
            except FileNotFoundError:
                continue
            except (ValueError, OSError) as exc:
                problems.append(f"{path.name}: {exc}")
        if problems:
            raise ValueError("unexpected/replaced recovery data retained: " + "; ".join(problems))


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
        if not identity.startswith("local-") or source is None or not args.sha256 or not (args.license_note or "").strip():
            raise ValueError("local sites require ID local-*, --source, --sha256 and --license-note recording your authorized use/sharing")
        if not re.fullmatch(r"[a-f0-9]{64}", args.sha256):
            raise ValueError("--sha256 must contain 64 lowercase hex digits")
        if not source.is_file():
            raise ValueError("local sites source must be a regular file")
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
        if receipt["resource"] != identity or receipt["source"] != item:
            raise ValueError("existing resource identity differs; choose a new immutable ID/root")
        print("already installed; no writes or download")
        return
    root.mkdir(parents=True, exist_ok=True)
    stack = ExitStack()
    txn = Owned(stack)
    published_inode = None
    promoted = False
    public_target = target
    try:
        parent = txn.pin(root)
        target = parent / identity
        try:
            lock = txn.directory(parent, f".{identity}.lock")
        except FileExistsError:
            raise ValueError(f"installation lock exists in {root}; inspect its owner before manual recovery") from None
        txn.write(lock / "owner.json", json.dumps({"pid": os.getpid(), "time": time.time()}))
        required = item["bytes"] + item["expanded_bytes"] + 67108864
        if shutil.disk_usage(root).free < required:
            raise ValueError(f"insufficient space; require at least {required} free bytes")
        if source is None:
            cache = parent / ".downloads"
            cache.mkdir(mode=0o700, exist_ok=True)
            cs = cache.lstat()
            if not stat.S_ISDIR(cs.st_mode) or cs.st_uid != os.getuid() or stat.S_IMODE(cs.st_mode) != 0o700:
                raise ValueError("download cache must be a private owned 0700 physical directory")
            cache = txn.pin(cache)
            source = cache / (item["sha256"] + ".part")
            existed = source.exists()
            fd = os.open(source, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
            stack.callback(os.close, fd)
            ss = os.fstat(fd)
            if not stat.S_ISREG(ss.st_mode) or ss.st_nlink != 1 or ss.st_uid != os.getuid():
                raise ValueError("download partial must be an owned regular non-linked file")
            source = Path(f"/proc/self/fd/{fd}")
            if ss.st_size >= item["bytes"]:
                if ss.st_size != item["bytes"] or digest(source) != item["sha256"]:
                    raise ValueError("corrupt download cache: inspect the exact catalog .part file; nothing was overwritten")
            else:
                print(f"downloading resource={identity} resume={existed}", flush=True)
                subprocess.run(["curl", "--fail", "--location", "--proto", "=https", "--proto-redir", "=https",
                                "--retry", "3", "--retry-all-errors", "--connect-timeout", "30",
                                "--max-time", "900", "--continue-at", "-", "--output", str(source), item["url"]],
                               pass_fds=(fd,), check=True)
        if source.stat().st_size != item["bytes"] or digest(source) != item["sha256"]:
            raise ValueError("source bytes/checksum mismatch; nothing promoted; cached download retained for diagnosis")
        txn.staged = True
        stage = txn.directory(lock)
        stage_entry = txn.nodes[-1][0]
        payload_dir = None
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
                    if payload_dir is None:
                        payload_dir = txn.directory(stage, "1kg-somalier")
                    if member.isdir():
                        if tuple(path.parts) != ("1kg-somalier",):
                            raise ValueError("unexpected archive directory")
                    else:
                        if len(path.parts) != 2:
                            raise ValueError("unexpected nested archive member")
                        dest = payload_dir / path.name
                        if not member.name.endswith(".somalier"):
                            raise ValueError("unexpected ancestry archive member")
                        with archive.extractfile(member) as src, txn.file(dest) as out:
                            shutil.copyfileobj(src, out)
        else:
            with source.open("rb") as raw:
                suffix = ".vcf.gz" if raw.read(2) == b"\x1f\x8b" else ".vcf"
            with txn.file(stage / ("sites" + suffix)) as stream:
                shutil.copyfile(source, f"/proc/self/fd/{stream.fileno()}")
        receipt = {"schema": SCHEMA, "resource": identity, "source": item,
                   "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "uid": os.getuid(), "analysis_network": "none", "members": item["files"]}
        txn.write(stage / "resource.json", json.dumps(receipt, sort_keys=True, indent=2) + "\n")
        files = sorted(p for p in stage.rglob("*") if p.is_file())
        txn.write(stage / "SHA256SUMS", "".join(f"{digest(p)}  {p.relative_to(stage)}\n" for p in files))
        txn.write(stage / "READY", digest(stage / "SHA256SUMS") + "\n")
        for path, ident, directory, staged in txn.nodes:
            if not staged:
                continue
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                st = os.fstat(fd)
                if (st.st_dev, st.st_ino) != ident:
                    raise ValueError("staging object replaced; refusing permission change")
                os.fchmod(fd, 0o755 if directory else 0o644)
            finally:
                os.close(fd)
        verify(stage, identity)
        if target.exists() or target.is_symlink():
            raise ValueError("target appeared during install; refusing overwrite")
        # The handle is a procfs link; compare its directory, not its link inode.
        st = stage.stat()
        published_inode = (st.st_dev, st.st_ino)
        rst = parent.stat()
        if inode(stage_entry) != published_inode or inode(root) != (rst.st_dev, rst.st_ino):
            raise ValueError("transaction parent or staging changed; refusing promotion")
        promote(stage_entry, target)
        promoted = True
        print(f"installed resource={identity} root={public_target}; analysis must bind it read-only")
    finally:
        with defer_signals():
            try:
                if not promoted and published_inode is not None:
                    try:
                        promoted = inode(target) == published_inode
                    except FileNotFoundError:
                        pass
                txn.cleanup(promoted)
            finally:
                stack.close()


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
        signal.signal(signal.SIGHUP, interrupted)
        signal.signal(signal.SIGINT, interrupted)
        signal.signal(signal.SIGTERM, interrupted)
        main()
    except (ValueError, OSError, EOFError, TypeError, KeyError, tarfile.TarError, subprocess.CalledProcessError) as exc:
        print(f"somalier-resources: {exc}", file=sys.stderr)
        sys.exit(1)
