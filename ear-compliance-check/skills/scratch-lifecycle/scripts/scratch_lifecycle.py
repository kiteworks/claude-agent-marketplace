#!/usr/bin/env python3
"""Native scratch ownership. Canonical source: scratch-foundation (component 1.0.0).

No device adapter is implied. Use only on a verified native filesystem with a
private parent directory and an executor authorized for the requested operation.
The recovery key belongs in caller memory, never beside the manifest. Losing it
or a torn manifest requires manual cleanup. This is not protection against a
hostile process running as the same OS user or an untrusted filesystem driver.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import secrets
import socket
import stat
import sys
import uuid
from pathlib import Path

ROLES = {
    "download",
    "retry",
    "staging",
    "text",
    "partial",
    "ocr",
    "parser_temp",
    "upload_verification",
}
NAME = re.compile(r"[0-9a-f]{32}(\.[a-z0-9]{1,12})?")
MODES = {"retain", "delete", "truncate"}


def _checked(path: Path):
    """Reject links/reparse points in every existing ancestor, without resolving."""
    path = Path(os.path.abspath(path))
    for part in (*reversed(path.parents), path):
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError(f"link/reparse point is not owned: {part}")
    return path.lstat()


def _identity(info):
    return [info.st_dev, info.st_ino, getattr(info, "st_birthtime_ns", None)]


def _payload(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _lock(handle):
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _alive(pid):
    if pid <= 0:
        return True
    if os.name == "nt":
        # os.kill(pid, 0) is unsafe on Windows (TerminateProcess for non-signals).
        import ctypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return ctypes.get_last_error() != 87  # absent only, deny on access error
        try:
            exit_code = ctypes.c_ulong()
            kernel.GetExitCodeProcess.argtypes = [
                ctypes.c_void_p,
                ctypes.POINTER(ctypes.c_ulong),
            ]
            if not kernel.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return True
            return exit_code.value == 259  # STILL_ACTIVE
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass
    return True


class ScratchRun:
    """One locked manifest, opaque files, authenticated explicit reopen/recovery."""

    @classmethod
    def create(
        cls,
        parent: Path,
        *,
        location: str,
        mode="retain",
        authorized=False,
        owner_pid=None,
    ):
        if mode not in MODES or (mode != "retain" and not authorized):
            raise ValueError("destructive cleanup requires prior authorization")
        owner_pid = os.getpid() if owner_pid is None else owner_pid
        if not isinstance(owner_pid, int) or owner_pid <= 0 or not _alive(owner_pid):
            raise ValueError("a verified live session owner is required")
        parent = Path(os.path.abspath(parent))
        if not stat.S_ISDIR(_checked(parent).st_mode):
            raise ValueError("parent must be a verified private directory")
        container = parent / "_kiteworks-content-tmp"
        try:
            container.mkdir(mode=0o700)
        except FileExistsError:
            if not stat.S_ISDIR(_checked(container).st_mode):
                raise ValueError("scratch container is not a directory")
        _checked(container)
        run_id = uuid.uuid4().hex
        root = container / run_id
        root.mkdir(mode=0o700)  # exclusive; never reuse a pre-existing run
        instance = cls()
        instance.root = root
        instance.key = secrets.token_hex(32)
        instance.handle = (root / "manifest.json").open("x+b")
        instance.handle.write(b" ")
        instance.handle.flush()
        _lock(instance.handle)
        instance.data = {
            "schema": 1,
            "component": "1.0.0",
            "run_id": run_id,
            "root": str(root),
            "root_identity": _identity(_checked(root)),
            "manifest_identity": _identity(os.fstat(instance.handle.fileno())),
            "host": socket.gethostname(),
            "location": location,
            "active_pid": os.getpid(),
            "owner_pid": owner_pid,
            "mode": mode,
            "authorized": authorized,
            "artifacts": {},
        }
        instance._save()
        return instance

    @classmethod
    def open(cls, root: Path, key: str, *, recover=False):
        root = Path(os.path.abspath(root))
        _checked(root)
        manifest = root / "manifest.json"
        info = _checked(manifest)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError("invalid manifest file")
        instance = cls()
        instance.root, instance.key = root, key
        instance.handle = manifest.open("r+b")
        try:
            _lock(instance.handle)
            if _identity(os.fstat(instance.handle.fileno())) != _identity(info):
                raise ValueError("manifest replaced while opening")
            instance.handle.seek(0)
            envelope = json.load(instance.handle)
            data = envelope["data"]
            signature = hmac.new(
                bytes.fromhex(key), _payload(data), hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(signature, envelope["mac"]):
                raise ValueError("manifest authentication failed")
            instance.data = data
            instance._validate()
            owner_alive = _alive(data["owner_pid"])
            if recover and owner_alive:
                raise ValueError("session owner is still active")
            if not recover and not owner_alive:
                raise ValueError("session owner ended; explicit recovery is required")
            pid = data["active_pid"]
            if pid:
                if not recover or _alive(pid):
                    raise ValueError("run is active or needs explicit recovery")
            instance.data["active_pid"] = os.getpid()
            instance._save()
        except BaseException:
            instance.handle.close()
            raise
        return instance

    def _validate(self):
        data = self.data
        if (
            data["schema"] != 1
            or data["root"] != str(self.root)
            or data["run_id"] != self.root.name
            or self.root.parent.name != "_kiteworks-content-tmp"
            or data["host"] != socket.gethostname()
            or _identity(_checked(self.root)) != data["root_identity"]
            or _identity(_checked(self.root / "manifest.json"))
            != data["manifest_identity"]
        ):
            raise ValueError("run location/identity changed")
        for name, artifact in data["artifacts"].items():
            if not NAME.fullmatch(name) or artifact["role"] not in ROLES:
                raise ValueError("invalid owned artifact")

    def _save(self):
        self._validate()
        envelope = {
            "data": self.data,
            "mac": hmac.new(
                bytes.fromhex(self.key), _payload(self.data), hashlib.sha256
            ).hexdigest(),
        }
        self.handle.seek(0)
        self.handle.write(_payload(envelope))
        self.handle.truncate()
        self.handle.flush()
        os.fsync(self.handle.fileno())

    def reserve(self, role: str, suffix: str = "") -> Path:
        """Persist a plan BEFORE exclusive creation; never adopt an existing file."""
        self._validate()
        if role not in ROLES or (
            suffix and not re.fullmatch(r"\.[a-z0-9]{1,12}", suffix)
        ):
            raise ValueError("invalid role or suffix")
        name = uuid.uuid4().hex + suffix
        artifact = {
            "role": role,
            "ownership": "planned",
            "identity": None,
            "cleanup": "pending",
        }
        if name in self.data["artifacts"]:
            raise ValueError("artifact name already registered")
        self.data["artifacts"][name] = artifact
        self._save()
        path = self.root / name
        try:
            with path.open("xb") as handle:
                artifact["identity"] = _identity(os.fstat(handle.fileno()))
                artifact["ownership"] = "created"
            self._save()
        except BaseException:
            # Planned/uncertain artifacts are never eligible for destruction.
            artifact["cleanup"] = "failed"
            self._save()
            raise
        return path

    def check(self, path: Path) -> dict:
        self._validate()
        path = Path(os.path.abspath(path))
        if path.parent != self.root or path.name not in self.data["artifacts"]:
            raise ValueError("path is not owned by this run")
        artifact = self.data["artifacts"][path.name]
        if artifact["ownership"] != "created":
            raise ValueError("creation/ownership was not confirmed")
        info = _checked(path)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or _identity(info) != artifact["identity"]
        ):
            raise ValueError("artifact identity changed")
        return artifact

    def release(self, path: Path, *, mode=None, authorized=None) -> dict:
        mode = self.data["mode"] if mode is None else mode
        authorized = self.data["authorized"] if authorized is None else authorized
        if mode not in MODES:
            raise ValueError("unknown cleanup mode")
        self._validate()
        path = Path(os.path.abspath(path))
        if path.parent != self.root or path.name not in self.data["artifacts"]:
            raise ValueError("path is not owned by this run")
        artifact = self.data["artifacts"][path.name]
        try:
            self.check(path)
            if mode == "retain" or not authorized:
                artifact["cleanup"] = "retained_by_user"
            elif mode == "delete":
                path.unlink()
                if os.path.lexists(path):
                    raise OSError("path still present after deletion")
                artifact["cleanup"] = "removed"
                artifact["ownership"] = "released"
            else:
                # Validate the opened file too, before destructive truncation.
                with path.open("r+b") as handle:
                    if _identity(os.fstat(handle.fileno())) != artifact["identity"]:
                        raise ValueError("artifact changed while opening")
                    self.check(path)
                    handle.truncate(0)
                    handle.flush()
                    os.fsync(handle.fileno())
                    if os.fstat(handle.fileno()).st_size != 0:
                        raise OSError("truncation not verified")
                self.check(path)
                artifact["cleanup"] = "truncated"
        except (OSError, ValueError) as exc:
            artifact["cleanup"] = "failed"
            # Do not store document text or parser stderr in bookkeeping.
            artifact["error"] = type(exc).__name__
        self._save()
        return {"path": str(path), **artifact}

    def inventory(self):
        self._validate()
        return [
            {"path": str(self.root / name), **artifact}
            for name, artifact in self.data["artifacts"].items()
        ]

    def finalize(self, *, mode=None, authorized=None):
        """Only registered files; unexpected entries are reported, never removed."""
        for item in self.inventory():
            if item["cleanup"] == "removed" and os.path.lexists(item["path"]):
                self.data["artifacts"][Path(item["path"]).name]["cleanup"] = "failed"
                self._save()
            elif item["cleanup"] != "removed":
                self.release(Path(item["path"]), mode=mode, authorized=authorized)
        outcomes = self.inventory()
        expected = set(self.data["artifacts"]) | {"manifest.json"}
        unexpected = [str(p) for p in self.root.iterdir() if p.name not in expected]
        complete = all(item["cleanup"] == "removed" for item in outcomes)
        result = {
            "artifacts": outcomes,
            "unexpected": unexpected,
            "cleanup_complete": False,
            "manifest": str(self.root / "manifest.json"),
        }
        effective_mode = self.data["mode"] if mode is None else mode
        permission = self.data["authorized"] if authorized is None else authorized
        if complete and not unexpected and effective_mode == "delete" and permission:
            self._validate()
            self.close()
            try:
                # Windows requires the manifest handle closed before unlink.
                self._validate()
                (self.root / "manifest.json").unlink()
                self.root.rmdir()  # empty only; never remove the reused container
                result["cleanup_complete"] = not os.path.lexists(self.root)
                result["manifest"] = None
            except OSError as exc:
                result["bookkeeping_error"] = type(exc).__name__
                # Caller must retain this result if the manifest itself was removed.
        return result

    def close(self):
        if not self.handle.closed:
            try:
                self.data["active_pid"] = None
                self._save()
            finally:
                self.handle.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        # Consumer must explicitly finalize once deliverable/fallback use has ended.
        self.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=["init", "reserve", "release", "finalize", "inventory"]
    )
    parser.add_argument("--parent", type=Path)
    parser.add_argument("--location")
    parser.add_argument("--owner-pid", type=int)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--role", choices=sorted(ROLES))
    parser.add_argument("--suffix", default="")
    parser.add_argument("--path", type=Path)
    parser.add_argument("--mode", choices=sorted(MODES), default="retain")
    parser.add_argument("--authorized", action="store_true")
    parser.add_argument("--recover", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.action == "init":
            if not args.parent or not args.location or not args.owner_pid:
                parser.error("init requires --parent, --location and --owner-pid")
            with ScratchRun.create(
                args.parent,
                location=args.location,
                mode=args.mode,
                authorized=args.authorized,
                owner_pid=args.owner_pid,
            ) as run:
                print(json.dumps({"root": str(run.root), "key": run.key}))
            return 0
        if not args.root:
            parser.error("--root is required")
        key = os.environ.get("KITEWORKS_SCRATCH_KEY", "")
        with ScratchRun.open(args.root, key, recover=args.recover) as run:
            if args.action == "reserve":
                if not args.role:
                    parser.error("reserve requires --role")
                result = {"path": str(run.reserve(args.role, args.suffix))}
            elif args.action == "release":
                if not args.path:
                    parser.error("release requires --path")
                result = run.release(
                    args.path, mode=args.mode, authorized=args.authorized
                )
            elif args.action == "finalize":
                result = run.finalize(mode=args.mode, authorized=args.authorized)
            else:
                result = {"artifacts": run.inventory()}
            print(json.dumps(result))
            if args.action == "finalize":
                return 0 if result["cleanup_complete"] else 3
            if args.action == "release":
                return 0 if result["cleanup"] == "removed" else 3
            return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(
            json.dumps(
                {
                    "cleanup_complete": False,
                    "error": type(exc).__name__,
                    "root": str(args.root),
                    "action": "manual inspection required",
                }
            ),
            file=sys.stderr,
        )
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
