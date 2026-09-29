#!/usr/bin/env python3
"""Native scratch ownership. Canonical source: scratch-foundation (component 1.0.0).

No device adapter is implied. Use only on a verified native filesystem with a
private parent directory and an executor authorized for the requested operation.
The recovery key lives in a user-only key file in the user profile, named by
run id and never beside the manifest; later commands find it by run id. The key
value is never printed. Losing the key file or a torn manifest requires manual
cleanup. This is not protection against a hostile process running as the same
OS user or an untrusted filesystem driver.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import secrets
import shlex
import socket
import stat
import subprocess
import sys
import time
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
# Interpreters count as launchers only directly above the helper (py.exe, the
# venv redirector); above a shell they are a long-lived host that owns the run.
INTERPRETERS = frozenset({"python", "pythonw", "py", "uv", "uvx"})
KEY_ENV = "KITEWORKS_SCRATCH_KEY"  # optional override, kept for compatibility
KEY_DIR_ENV = "KITEWORKS_SCRATCH_KEY_DIR"
RUN_ID = re.compile(r"[0-9a-f]{32}")
OWNER_ENV = "KITEWORKS_SCRATCH_OWNER_PID"
# Short-lived wrappers between the agent session and this helper: each tool call
# may get a fresh shell (Git Bash/MSYS, cmd, PowerShell) or interpreter launcher.
TRANSIENT_PARENTS = frozenset(
    {
        "bash",
        "sh",
        "dash",
        "zsh",
        "ksh",
        "fish",
        "cmd",
        "powershell",
        "pwsh",
        "conhost",
        "env",
        "nohup",
        "timeout",
        "xargs",
        "winpty",
        "python",
        "pythonw",
        "py",
        "uv",
        "uvx",
        # Per-call wrappers and sandboxes that exit with the tool call.
        "bwrap",
        "sudo",
        "doas",
        "nice",
        "ionice",
        "stdbuf",
        "script",
        "strace",
        "ltrace",
        "setsid",
        "flock",
        "time",
    }
)
MODE_REQUIRED = (
    "init requires an explicit cleanup mode: choose --mode delete --authorized for "
    "read-only runs, or --mode retain only when the user asked to keep files"
)


def key_dir() -> Path:
    """Per-user directory for run keys, outside every scratch folder."""
    override = os.environ.get(KEY_DIR_ENV)
    if override:
        return Path(os.path.abspath(override))
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local"
        return Path(base) / "Kiteworks" / "scratch-keys"
    base = os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state"
    return Path(base) / "kiteworks" / "scratch-keys"


def key_path(run_id: str) -> Path:
    if not RUN_ID.fullmatch(run_id):
        raise ValueError("invalid run id")
    return key_dir() / f"{run_id}.key"


def _current_user_sid():
    out = subprocess.run(
        ["whoami", "/user", "/fo", "csv", "/nh"],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    ).stdout
    sid = out.strip().rsplit(",", 1)[-1].strip().strip('"')
    if not sid.startswith("S-1-"):
        raise ValueError("could not read the current user SID")
    return sid


def _restrict_windows(path: Path, directory: bool) -> bool:
    """Replace inherited ACEs with one full-control ACE for the current user."""
    try:
        grant = f"*{_current_user_sid()}:" + ("(OI)(CI)F" if directory else "F")
        subprocess.run(
            ["icacls", str(path), "/inheritance:r", "/grant:r", grant],
            capture_output=True,
            timeout=30,
            check=True,
        )
        return True
    except (OSError, ValueError, subprocess.SubprocessError):
        return False


def _write_key_file(run_id: str, key: str) -> tuple[Path, str]:
    """Create the key file exclusively; return its path and protection level."""
    path = key_path(run_id)
    directory = path.parent
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
        raise ValueError("key directory is not a plain directory")
    if os.name == "nt":
        protected = _restrict_windows(directory, True)
    else:
        os.chmod(directory, 0o700)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    handle = os.open(path, flags, 0o600)
    try:
        os.write(handle, key.encode("ascii") + b"\n")
        os.fsync(handle)
    finally:
        os.close(handle)
    if os.name == "nt":
        protected = _restrict_windows(path, False) and protected
        # Without an explicit ACL the profile default applies (user, SYSTEM, admins).
        return path, "current-user-only" if protected else "profile-default"
    os.chmod(path, 0o600)
    return path, "0600"


def _has_key_file(root) -> bool:
    try:
        return os.path.lexists(key_path(Path(root).name))
    except ValueError:
        return False


def read_key_file(run_id: str) -> str:
    path = key_path(run_id)
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("key file is not a regular file")
        key = path.read_text(encoding="ascii").strip()
    except FileNotFoundError:
        raise ValueError(
            f"no key file for this run at {path}; without it the run cannot be "
            "authenticated and needs manual inspection"
        ) from None
    except (OSError, UnicodeDecodeError):
        raise ValueError(
            f"key file {path} is unreadable; the run needs manual inspection"
        ) from None
    if not re.fullmatch(r"[0-9a-f]{64}", key):
        raise ValueError(
            f"key file {path} is malformed; the run needs manual inspection"
        )
    return key


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


def _process_name(name: str) -> str:
    name = re.split(r"[\\/]", name)[-1].lower()
    name = name[:-4] if name.endswith(".exe") else name
    return re.sub(r"[\d.]+$", "", name) or name  # python3.12 -> python


def _windows_lookup():
    import ctypes
    from ctypes import wintypes

    class Entry(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", ctypes.c_wchar * 260),
        ]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.Process32FirstW.argtypes = [ctypes.c_void_p, ctypes.POINTER(Entry)]
    kernel.Process32NextW.argtypes = [ctypes.c_void_p, ctypes.POINTER(Entry)]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    snapshot = kernel.CreateToolhelp32Snapshot(0x2, 0)  # TH32CS_SNAPPROCESS
    if not snapshot or snapshot == ctypes.c_void_p(-1).value:
        return lambda pid: None
    table = {}
    try:
        entry = Entry()
        entry.dwSize = ctypes.sizeof(Entry)
        found = kernel.Process32FirstW(snapshot, ctypes.byref(entry))
        while found:
            table[entry.th32ProcessID] = (entry.th32ParentProcessID, entry.szExeFile)
            found = kernel.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel.CloseHandle(snapshot)
    return table.get


def _posix_lookup(pid):
    try:
        text = Path(f"/proc/{pid}/stat").read_text()
        close = text.rindex(")")
        return int(text[close + 2 :].split()[1]), text[text.index("(") + 1 : close]
    except (OSError, ValueError, IndexError):
        pass
    try:
        out = subprocess.run(
            ["ps", "-o", "ppid=", "-o", "comm=", "-p", str(pid)],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        ).stdout.split(None, 1)
        return int(out[0]), out[1].strip()
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return None


def resolve_owner_pid(
    explicit=None, *, environ=None, lookup=None, start=None, alive=None
):
    """Return the live, long-lived session process that owns a multi-call run.

    An explicit --owner-pid wins, then the KITEWORKS_SCRATCH_OWNER_PID override.
    Otherwise walk the real parent chain from this process, skipping shells and
    interpreter launchers (Git Bash/MSYS gives a fresh short-lived bash per call,
    and its $PPID is 1 or an MSYS-only PID, never a usable Windows PID).
    """
    environ = os.environ if environ is None else environ
    alive = _alive if alive is None else alive
    hint = (
        f"set {OWNER_ENV} to the process ID of the long-lived agent session "
        "(on Windows its Windows PID), or run the single-process Python API"
    )
    for source, value in (
        ("--owner-pid", explicit),
        (OWNER_ENV, environ.get(OWNER_ENV)),
    ):
        if value in (None, "", "auto"):
            continue
        try:
            pid = int(value)
        except (TypeError, ValueError):
            raise ValueError(f"{source} must be a process ID") from None
        if pid <= 1:
            raise ValueError(
                f"{source}={pid} is not a session process (Git Bash reports $PPID=1); "
                f"omit --owner-pid to resolve it automatically, or {hint}"
            )
        if not alive(pid):
            raise ValueError(
                f"{source}={pid} is not a live process on this host (a Git Bash/MSYS "
                f"PID is not a Windows PID); omit --owner-pid, or {hint}"
            )
        return pid
    if lookup is None:
        lookup = _windows_lookup() if os.name == "nt" else _posix_lookup
    pid = os.getppid() if start is None else start
    seen = set()
    after_shell = False
    while pid > 1 and pid not in seen and len(seen) < 64:
        seen.add(pid)
        info = lookup(pid)
        if info is None:
            break
        parent, name = info
        name = _process_name(name)
        interpreter_host = name in INTERPRETERS and after_shell
        if name not in TRANSIENT_PARENTS or interpreter_host:
            if alive(pid):
                return pid
            break
        after_shell = after_shell or name not in INTERPRETERS
        pid = parent
    raise ValueError(
        f"no long-lived session owner found in the parent process chain; {hint}"
    )


def _command(*args) -> str:
    """A copyable command: absolute script path, quoted forward-slash paths."""
    parts = ["python", Path(__file__).resolve().as_posix(), *args]
    return " ".join(shlex.quote(str(part)) for part in parts)


def _posix(path) -> str:
    return Path(os.path.abspath(path)).as_posix()


_MSYS_DRIVE = re.compile(r"^[\\/]([A-Za-z])(?:[\\/](.*))?$", re.DOTALL)


def _msys_to_windows(text: str) -> str:
    """Rewrite a Git Bash / MSYS drive path (``/c/Users/x``) to ``C:\\Users\\x``.

    Only Windows needs this translation: on a POSIX filesystem a leading
    ``/c/...`` is a real absolute path, not an MSYS spelling of a drive.
    Windows itself already treats forward and back slashes, and drive-letter
    case, as the same path, so nothing else needs rewriting here -- except
    that argparse's own ``type=Path`` already turns ``/c/...`` into
    ``\\c\\...`` (a plain root-relative path with ``c`` as an ordinary
    segment, not a drive) before this ever sees it, so both separators are
    accepted here.
    """
    if os.name != "nt":
        return text
    match = _MSYS_DRIVE.match(text)
    if not match:
        return text
    drive, rest = match.group(1).upper(), match.group(2) or ""
    return f"{drive}:\\{rest}"


_DRIVE = re.compile(r"^([A-Za-z]):(?=[\\/]|$)")


def _expand_short_name(absolute: str) -> str:
    """Expand a Windows 8.3 short name (``RICK~1.GOU``) to its long form.

    Same algorithm as extract_and_cleanup.py's ``long_path``: progressively
    resolve the longest existing prefix, so a not-yet-created (or already
    deleted) tail is returned unresolved rather than raising.
    ``GetLongPathNameW`` translates each existing component's own short name
    to its long name without dereferencing a reparse point sitting at any
    component -- unlike ``realpath``/``GetFinalPathNameByHandleW``, it never
    launders a junction into its target, so it is safe to call before
    ``_checked`` has had a chance to reject one.
    """
    if os.name != "nt" or "~" not in absolute:
        return absolute
    import ctypes

    size = 32768
    buffer = ctypes.create_unicode_buffer(size)
    head, tail = absolute, []
    while True:
        length = ctypes.windll.kernel32.GetLongPathNameW(head, buffer, size)
        if 0 < length < size:
            return os.path.join(buffer.value, *reversed(tail))
        parent, name = os.path.split(head)
        if not name or parent == head:
            return absolute
        tail.append(name)
        head = parent


def normalize_path(path) -> Path:
    """Absolute path, resolving every Windows path spelling but a symlink.

    Every path a caller can pass through this CLI must resolve to the same
    file: backslash or forward slash, an upper- or lower-case drive letter,
    an 8.3 short name, or the MSYS ``/c/...`` form Git Bash hands out.
    Windows already treats the first as identical to itself; the drive
    letter is upper-cased and any short name expanded here so a later plain
    string or Path comparison (this run's own recorded root, an owned
    artifact name) sees the identical spelling regardless of which of these
    named it. This never follows a symlink or reparse point -- that stays
    ``_checked``'s job, called separately wherever ownership is decided --
    so a malicious junction is still rejected, not silently resolved through.
    """
    text = _msys_to_windows(os.fspath(path))
    if os.name == "nt":
        text = _DRIVE.sub(lambda m: m.group(1).upper() + ":", text, count=1)
    return Path(_expand_short_name(os.path.abspath(text)))


STALE_KEY_AGE_SECONDS = 24 * 60 * 60


def sweep_stale_keys(now: float | None = None) -> list[str]:
    """Remove run key files old enough to treat as abandoned.

    A key file outlives its run only so a crash can be recovered from (see
    "Explicit recovery only" in the scratch-lifecycle SKILL); a run that
    finalizes cleanly removes its own key file (see ``finalize``). The key
    file cannot name the arbitrary ``--parent`` folder its run was created
    under, so there is no way to look its manifest up from here and confirm
    the run is actually gone -- age is the only signal available. Real runs
    finish in minutes to a few hours, so a key untouched for over 24h is
    treated as abandoned and removed. This never touches a manifest, a run
    directory or any document content, and makes no judgement at all about
    whether a run itself is done -- a run is still recovered explicitly, by
    root, never by age. A run that still needs recovery after its key is
    swept needs manual inspection, exactly as for any other lost key today.
    """
    now = time.time() if now is None else now
    removed = []
    try:
        entries = list(key_dir().iterdir())
    except FileNotFoundError:
        return removed
    for entry in entries:
        if entry.suffix != ".key" or not RUN_ID.fullmatch(entry.stem):
            continue
        try:
            info = entry.lstat()
        except OSError:
            continue
        if not stat.S_ISREG(info.st_mode):
            continue
        if now - info.st_mtime < STALE_KEY_AGE_SECONDS:
            continue
        try:
            entry.unlink()
        except OSError:
            continue
        removed.append(str(entry))
    return removed


def recovery_instruction(root) -> str:
    # Only --recover: the cleanup policy recorded at init (delete or retain) applies.
    return (
        _command("finalize", "--root", _posix(root), "--recover")
        + "  (the helper reads the run key from its key file itself; never put "
        "the key value in a command, message or report)"
    )


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
        persist_key=False,
    ):
        if mode not in MODES or (mode != "retain" and not authorized):
            raise ValueError("destructive cleanup requires prior authorization")
        sweep_stale_keys()  # best-effort; a fresh run is a natural time to tidy up
        owner_pid = os.getpid() if owner_pid is None else owner_pid
        if not isinstance(owner_pid, int) or owner_pid <= 1 or not _alive(owner_pid):
            raise ValueError("a verified live session owner is required")
        parent = normalize_path(parent)
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
        instance.key_file = instance.key_protection = instance.handle = None
        try:
            instance._initialize(
                run_id, location, mode, authorized, owner_pid, persist_key
            )
        except BaseException:
            # Remove only what this call created: its handle, manifest, key file
            # and the (then empty) fresh run directory.
            if instance.handle is not None:
                instance.handle.close()
            for created in (root / "manifest.json", instance.key_file):
                if created is not None:
                    try:
                        created.unlink()
                    except OSError:
                        pass
            try:
                root.rmdir()
            except OSError:
                pass
            raise
        return instance

    def _initialize(self, run_id, location, mode, authorized, owner_pid, persist_key):
        instance, root = self, self.root
        if persist_key:  # multi-call CLI: later commands find the key by run id
            instance.key_file, instance.key_protection = _write_key_file(
                run_id, instance.key
            )
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

    @classmethod
    def open(cls, root: Path, key: str | None = None, *, recover=False):
        """Open a run; without a key, read it from the run's key file."""
        root = normalize_path(root)
        _checked(root)
        if not key:
            key = read_key_file(root.name)
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
            # Holding the exclusive lock proves no operation is in progress. A
            # recorded operation whose process has exited crashed before close;
            # reclaim it. A live recorded process is refused (it may be PID reuse).
            if pid and _alive(pid):
                raise ValueError(
                    f"run is recorded as active in live process {pid}; "
                    "wait for it to finish, or inspect the run manually"
                )
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
        path = normalize_path(path)
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
        path = normalize_path(path)
        if path.parent != self.root or path.name not in self.data["artifacts"]:
            raise ValueError("path is not owned by this run")
        artifact = self.data["artifacts"][path.name]
        if (
            artifact["cleanup"] == "removed"
            and artifact["ownership"] == "released"
            and not os.path.lexists(path)
        ):
            # Already deleted by an earlier release (e.g. the extractor, then
            # the caller's own finally): a no-op, never a downgrade to failed.
            return {"path": str(path), **artifact}
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
        """Only registered files; unexpected entries are reported, never removed.

        Also removes the shared container directory once it is this run's own
        empty root that made it empty -- a plain rmdir, never recursive, and a
        silent no-op while another run still lives inside it.
        """
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
            container = self.root.parent
            try:
                # Windows requires the manifest handle closed before unlink.
                self._validate()
                (self.root / "manifest.json").unlink()
                self.root.rmdir()  # empty only
                result["cleanup_complete"] = not os.path.lexists(self.root)
                result["manifest"] = None
                # The run is gone; its key file has nothing left to protect.
                key_path(self.root.name).unlink(missing_ok=True)
            except OSError as exc:
                result["bookkeeping_error"] = type(exc).__name__
                # Caller must retain this result if the manifest itself was removed.
            same_container = container.name == "_kiteworks-content-tmp"
            if result["cleanup_complete"] and same_container:
                try:
                    container.rmdir()  # only when this was the last run inside it
                except OSError:
                    pass  # other runs still live in the shared container
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


def _emit(result, key, stream=None):
    """Print JSON; the key value is redacted as a last line of defense."""
    text = json.dumps(result)
    if len(key) >= 16:
        text = text.replace(key, "[redacted]")
    print(text, file=stream or sys.stdout)


def _explain_incomplete(result, root):
    retained = [
        item["path"]
        for item in result["artifacts"]
        if item["cleanup"] in {"retained_by_user", "pending"}
    ]
    if retained:
        result["retained"] = retained
        result["next_step"] = (
            "These files are local copies of downloaded content. Unless the user "
            "explicitly asked to keep them, run: "
            + _command("finalize", "--root", _posix(root), "--mode", "delete")
            + " --authorized"
        )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=["init", "reserve", "release", "finalize", "inventory", "sweep"],
    )
    parser.add_argument("--parent", type=Path)
    parser.add_argument("--location")
    parser.add_argument(
        "--owner-pid",
        help=f"session owner PID; default auto (parent chain, or {OWNER_ENV})",
    )
    parser.add_argument("--root", type=Path)
    parser.add_argument("--role", choices=sorted(ROLES))
    parser.add_argument("--suffix", default="")
    parser.add_argument("--path", type=Path)
    # init requires --mode; later calls without it apply the recorded policy.
    parser.add_argument("--mode", choices=sorted(MODES))
    parser.add_argument("--authorized", action="store_true", default=None)
    parser.add_argument("--recover", action="store_true")
    args = parser.parse_args(argv)
    key = os.environ.get(KEY_ENV, "")  # optional override; default is the key file
    if args.action == "init" and not args.mode:
        parser.error(MODE_REQUIRED)
    try:
        if args.action == "sweep":
            _emit({"removed": sweep_stale_keys()}, "")
            return 0
        if args.action == "init":
            if not args.parent or not args.location:
                parser.error("init requires --parent and --location")
            with ScratchRun.create(
                args.parent,
                location=args.location,
                mode=args.mode,
                authorized=bool(args.authorized),
                owner_pid=resolve_owner_pid(args.owner_pid),
                persist_key=True,
            ) as run:
                key = run.key  # redact it from anything printed below
                _emit(
                    {
                        "root": str(run.root),
                        "key_file": str(run.key_file),
                        "key_file_protection": run.key_protection,
                        "owner_pid": run.data["owner_pid"],
                        "mode": run.data["mode"],
                        "recovery": recovery_instruction(run.root),
                    },
                    key,
                )
            return 0
        if not args.root:
            parser.error("--root is required")
        if key and _has_key_file(args.root):
            key = ""  # a leftover export must not shadow this run's key file
        with ScratchRun.open(args.root, key or None, recover=args.recover) as run:
            key = run.key
            # Recorded permission covers only the recorded mode; another mode
            # (e.g. truncate after a delete-only grant) needs its own --authorized.
            authorized = args.authorized
            if authorized is None and args.mode not in (None, run.data["mode"]):
                authorized = False
            if args.action == "reserve":
                if not args.role:
                    parser.error("reserve requires --role")
                result = {"path": str(run.reserve(args.role, args.suffix))}
            elif args.action == "release":
                if not args.path:
                    parser.error("release requires --path")
                result = run.release(args.path, mode=args.mode, authorized=authorized)
            elif args.action == "finalize":
                result = run.finalize(mode=args.mode, authorized=authorized)
            else:
                result = {"artifacts": run.inventory()}
            if args.action == "finalize" and not result["cleanup_complete"]:
                _explain_incomplete(result, args.root)
            _emit(result, key)
            if args.action == "finalize":
                return 0 if result["cleanup_complete"] else 3
            if args.action == "release":
                return 0 if result["cleanup"] == "removed" else 3
            return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        report = {
            "cleanup_complete": False,
            "error": type(exc).__name__,
            "root": str(args.root),
            "action": "manual inspection required",
        }
        if isinstance(exc, ValueError):
            report["reason"] = str(exc)  # our own messages; never document text
        if "explicit recovery" in str(exc):
            report["action"] = "explicit recovery"
            report["recovery"] = recovery_instruction(args.root)
        if not key and args.root:
            try:  # redact the file key too, should any message ever carry it
                key = read_key_file(Path(args.root).name)
            except ValueError:
                pass
        _emit(report, key, sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
