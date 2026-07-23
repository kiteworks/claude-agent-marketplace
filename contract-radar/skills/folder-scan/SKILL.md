---
name: folder-scan
description: >
  Shared internal reference skill, not invoked by users directly. Other
  preview skills in this plugin (retention-sweeper-preview,
  storage-visualizer-preview, duplicate-finder-preview) read this file to
  learn the standard, safe way to walk a Kiteworks folder tree and search
  metadata. Read this before writing or modifying any preview skill in
  this plugin.
metadata:
  version: "0.1.0"
---

# folder-scan — shared metadata-walk helper

Read `../surface-gate/SKILL.md` first. **This skill is Tier B** (per that file): if subagent isolation isn't available on this surface, disclose that once per the standard wording and proceed directly — nothing in this skill needs local file access, so it is never Tier C.

Use the `Kiteworks` connector for every call in this skill. This is a read-only, metadata-only pattern: never call `delete_file`, `delete_folder`, `download_file_to_path`, `move_file`, `move_folder`, `read_file_contents`, `upload_file_from_path`, `rename_file`, `rename_folder`, `create_file_from_content`, or `create_folder` from a preview skill. Preview subagents should only be granted `get_folder_children`, `get_top_folders`, `get_user_info_whoami`, `search`, `search_files`, `search_folders` as tools.

## Resolving folders — a confirmed gotcha

`get_user_info_whoami` returns two different folder-like IDs: `mydirId` and `syncdirId`. **`mydirId` is a special "Tray" object, not a normal folder** — calling `create_folder` with `mydirId` as `parent_id` fails with `ERR_ENTITY_IS_MY_DIR`. The folder a user sees as "My Folder" in the Kiteworks UI is the object returned by `get_top_folders` with `name: "My Folder"`, whose `id` matches `syncdirId`. Always resolve "My Folder" this way — call `get_top_folders` (or `search_folders` with `path_contains: "My Folder"`) and use the matching folder's `id`, never `mydirId` directly.

## Require an explicit scope

Never scan blindly. Collect a folder (path or ID) or a search term from the user before making any call. Confirmed empirically: `search` / `search_files` / `search_folders` return `"No results found"` for unscoped queries — pass `parent_folder_id`, `path`, `path_contains`, or a real term every time. `content_contains` in particular needs a folder scope to return anything; do not rely on it as a tenant-wide search.

**Correction to an earlier version of this note:** `parent_folder_id` scoping is NOT shallow — re-tested more carefully and it **is** recursive into subfolders, confirmed live (`path_contains` scoped to a parent folder found a file two levels deep, in a subfolder's subfolder). The actual rule is narrower: **a query needs a real text term (`path_contains` or `content_contains`) to return anything at all — `parent_folder_id` plus only a date filter (`modified_after`/`before`, `created_after`/`before`) and no text term returns nothing**, the same empty result as a fully unscoped query. Confirmed by testing the exact same folder three ways: `parent_folder_id` alone → empty; `parent_folder_id` + date filter only → empty; `parent_folder_id` + `path_contains` + date filter → correct recursive results including a nested-subfolder match. So: `search_files`/`search_folders` are reliable and recursive for "find items matching a name/term" (optionally date-bounded) — but there's no way to ask "everything past a date, no name pattern" without a `get_folder_children` walk, because that use case has no text term to give it.

**`content_contains` specifically is a separate, more serious problem — confirmed non-functional, not just unverified.** Re-tested deliberately to rule out timing: an ultra-common word ("the") against multiple real PDFs created in 2014 (12 years old, fully scanned, `avStatus`/`dlpStatus`: "allowed") still returned nothing; a domain word ("kiteworks") against the same long-lived PDFs returned nothing; a 20-minute-old plain `.txt` file with the exact search term in its content returned nothing; trying the generic `search` tool with an explicit `search_type: "files"` instead of `search_files` made no difference. This rules out indexing latency and rules out the file being too new or the wrong type. Treat `content_contains` as **not working** via this connector, full stop, until someone confirms otherwise with Kiteworks — don't rely on it, and don't tell a user their content was scanned by it.

## Walking a folder tree

The single, correct mechanism for scanning a folder and everything beneath it is a bounded `get_folder_children` recursion — confirmed live and working (nested subfolders returned correctly with full metadata in one call per folder level). Every item it returns already carries `modified`, `created`, `isShared`, `creator`, and (for files) `fingerprint` — so date windows, sharing checks, and owner checks are all done by **filtering the walked results client-side**, not by pushing the filter to a search call. There is no server-side shortcut for a tree-wide date or term filter; don't design one in.

Bounded walk — do not exceed max_depth=25, max_pages=50, max_items=20000 for `get_folder_children` recursion. This is a best-effort walk, not guaranteed to reach every item. When any limit is hit, say so explicitly in the result: state how many folders/files were scanned, and present the result as partial coverage.

Call Kiteworks tools sequentially or in small batches (at most 5 in parallel) — large parallel bursts can fail at the connector proxy.

## Metadata fields worth using directly

Folder and file objects returned by `get_top_folders`/`get_folder_children`/`search*` already include useful signals without any extra call:
- `isShared` (boolean) — whether the item is shared. Use this directly for any sharing-related check; do not rely on `search_filter: 'shared'` with an empty query (confirmed to return no results without a scoped term).
- `fingerprint` — a 32-char lowercase hex content checksum, or the literal string `"Generating..."` while the backend computes it asynchronously on fresh uploads/new versions. Never treat a `"Generating..."` file as fingerprint-matched; report it separately as unverified.
- `avStatus` / `dlpStatus` — present on file objects (e.g. `"scanning"`, `"allowed"`). Useful for any content-safety-flavored check; don't assume every tenant surfaces these identically.
- `expire` / `maxFileLifeTime` — folder lifecycle settings (0 = no expiry configured).
- `creator` / `userId` — owner info, useful for ownership-based checks.

**Never** include a raw `fingerprint` value in output shown to the user — identify items by name/path only.

## Links

`search` / `search_files` / `search_folders` results include a real `url` field directly (confirmed live, e.g. `https://content.kiteworks.com/web/file/<id>`) — use it as-is when an item came from one of those calls, don't reconstruct it. `get_folder_children` results do **not** include a `url` field, so for items obtained by walking, build the link from the tenant's configured web origin (`KW_WEB_BASE`) plus the object id: `<base>/web/file/<id>` or `<base>/web/folder/<id>`. Never infer an origin from a filename or path. If neither a returned `url` nor a configured origin is available, tell the user the item can be opened in Kiteworks but show no link — never emit a bare, relative, or guessed URL.

## Disclaimer

Every result surfaced through this pattern is a best-effort, productivity-grade summary over Kiteworks metadata. It is not deterministic and must not be used as the sole basis for compliance, legal, or disposition decisions.
