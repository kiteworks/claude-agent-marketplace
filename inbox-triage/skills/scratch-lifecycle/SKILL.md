---
name: scratch-lifecycle
description: >
  Shared internal contract for ownership, permissions and finalization of temporary
  document artifacts, including optional upload verification copies.
metadata:
  version: "1.0.0"
---

# Owned scratch lifecycle

Generated from `scratch-foundation/`, component 1.0.0. This contract covers local
scratch only; never request remote Kiteworks delete_file/delete_folder permissions.

## Capability and permission boundary

Record the actual source connector device, host destination, extraction location,
mapping/staging transfer, parser and cleanup executor before downloading.
Inspect available tool descriptions/schemas: call get_device_info when exposed;
do not invent that tool or require it in an already usable native environment.
A device permission request is not a delete operation. No device adapter is
shipped or claimed live-verified by this component.

Reuse suitable authorized folders. If necessary use the available folder-access
request once for the narrowest suitable folder, then recheck the grant and mapping.
Denial, timeout, unavailable prompt, disconnected device or revoked access means
no new download. Opening a web/mobile-origin Cowork session on Desktop does not
prove local access.

Before downloading disclose actual destinations, transfers, processing and
cleanup limits. For Cowork, honor the explicit approval requirement for permanent
deletion. Inspect the actual permission tool's scope and duration; batch any newly
required request once for the narrowest eligible run-owned scope and disclose
its actual breadth/lifetime. Do not invent a recursive or persistent grant.
An already applicable cleanup grant needs no repeated prompt.

Use only the executor authorized to reach that location. Failed mount unlink
does not establish host deletion is impossible; inspect a supported device
executor, but never switch executors to bypass required permission.
If permission is declined/unanswered, **do not truncate**. Default to retention
with paths/statuses and manual cleanup instructions. Explicitly authorized
truncate-only compatibility may be offered separately; zero bytes is not removal
or secure erasure. Even ordinary deletion says nothing about backups, sync history
or platform-managed account/conversation copies.

## Native executor contract

The Python helper supports a verified native private filesystem, not an arbitrary
FUSE/device bridge. Check private directory access controls first; Unix mode 0700
does not set a Windows ACL. Use a user-private Windows folder with verified ACLs.
Reject links/junctions/reparse points and shared writable roots. A hostile process
with the same OS identity or malicious filesystem driver is outside this boundary.

Each run has `_kiteworks-content-tmp/<run-uuid>/manifest.json`. Opaque relative
paths carry roles, ownership identity, execution host/location and cleanup states.
Bookkeeping never contains document text. The manifest is authenticated with a
random recovery key that is never stored beside it or in a deliverable. `init`
writes the key to a key file in the user profile, outside every scratch folder
(Windows: `%LOCALAPPDATA%\Kiteworks\scratch-keys\<run-id>.key`, with an ACL for
the current user only; elsewhere `~/.local/state/kiteworks/scratch-keys/`, mode
0600). Later commands find it by run id, so you never pass the key anywhere.
Complete cleanup removes the key file. If `init` reports
`key_file_protection: profile-default`, the explicit ACL could not be set and
the profile's default access applies; say so to the user. Without the key file,
automatic recovery is unavailable and manual inspection is required.

**Never show the key.** No command prints the key value, and you must never read
the key file into chat, a result, a report, a log or a command. A recovery
instruction refers to "the key file" and never contains the value. Error output
carries a key-free `recovery` command where one applies; copy it as it is.
`KITEWORKS_SCRATCH_KEY` remains only as an optional override for older callers.

The executable ships at `scripts/scratch_lifecycle.py` alongside this skill
(and alongside content-extract's parser). Run it with Python:

- `init --parent <verified-private-folder> --location <device-and-execution-location> --mode delete --authorized`
  returns root, key file path and protection, and the resolved `owner_pid`.
  `--mode` is required; `init` without it fails. The session owner must be a
  live, long-lived session process on the same device. By default the helper
  finds it itself: it walks the real parent chain and skips shells and
  interpreter launchers (Git Bash/MSYS bash, cmd, PowerShell, python). Do not
  pass `--owner-pid $PPID`: under Git Bash `$PPID` is 1 or an MSYS-only PID.
  If the helper cannot find an owner, set `KITEWORKS_SCRATCH_OWNER_PID` to the
  Windows (or POSIX) PID of the agent session process, or pass `--owner-pid`.
  Never start a keeper process (`Start-Sleep`, `sleep`, a background shell) to
  act as the owner. If no real owner can be established, this multi-call CLI is
  unsupported; use the single-process native Python API only when that executor
  is available.
  At the end of a read-only run, delete is the default: pass
  `--mode delete --authorized` at `init`, after any required platform deletion
  approval. Use `--mode retain` only when the user explicitly asked to keep the
  copies, or when the platform declined or did not answer the deletion
  permission; then report every retained path. `--mode truncate --authorized`
  requires separate explicit overwrite authorization. Flags assert a verified
  decision; they never replace a runtime permission prompt. Later calls without
  `--mode`/`--authorized` apply the policy recorded at `init`.
- `reserve --root <run> --role download --suffix .pdf` persists a plan before
  exclusive file creation and returns its opaque path. Valid roles: download,
  retry, staging, text, partial, ocr, parser_temp, upload_verification.
  Never register intended deliverables. Every retry/staging location needs its
  own reservation and ownership manifest; remote locations require a verified
  executor running there, not a guessed path in this manifest.
- `release --root <run> --path <owned-file> --mode delete --authorized` verifies
  identity, deletes one file and checks absence. Truncation uses the same checks.
  In a Python consumer use `try/finally: run.release(path)` with its authorized
  run policy. Releasing a file already `removed` (and still absent) is a
  no-op. Otherwise missing/replaced/planned-only files stay failed, not DONE.
- `finalize --root <run> --mode delete --authorized` releases remaining owned
  files, keeps unexpected entries, and removes only its owned empty run directory
  after bookkeeping. It never removes the reused container/root recursively.
  Preserve returned JSON if a bookkeeping removal fails. Exit 3 means incomplete
  cleanup; list pending, truncated, retained_by_user and failed artifacts and any
  unexpected files. State exactly which paths the user should inspect/remove
  manually; never suggest deleting a whole reused parent.

Always finalize in a consumer finally block after releasing needed text/originals.
If `finalize` lists `retained` files and the user did not ask to keep them, run
the returned `next_step` delete command. Downloaded tenant documents must not be
left on disk by default. Explicit retain mode does no destructive operation. A successful parser cannot
convert failed cleanup into completion. A hard kill, torn manifest, bridge loss
or lost recovery key has no automatic guarantee.

## Explicit recovery only

No wildcard discovery, age-based sweep, hook-only backstop or directory-wide
destructive cleanup. Select exactly one known manifest and use the original key.
`finalize --root <selected-run> --recover --mode delete --authorized` obtains a
nonblocking exclusive manifest lock, authenticates root/paths/identities and
refuses a recorded live session owner or active operation (including PID reuse).
The session owner remains recorded between CLI calls; closing an operation does
not end the session lease. Age alone is irrelevant. If an earlier call crashed
and left a stale `active_pid`, the next call reclaims the run automatically once
that process has exited; no recovery flag is needed while the owner lives.
Revalidate applicable authorization for recovery. Corrupt manifests, changed
devices, active runs and missing keys require manual inspection. Other runs and
unexpected files remain untouched.
