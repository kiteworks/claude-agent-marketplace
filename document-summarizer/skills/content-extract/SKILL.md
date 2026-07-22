---
name: content-extract
description: >
  Shared internal reference skill, not invoked by users directly.
  term-sweep reads this file for the standard way to get a real file's
  actual text content out of Kiteworks, now that `content_contains`
  search is confirmed non-functional (see folder-scan). Read this
  before writing or modifying term-sweep or any skill that needs real
  file content rather than just name/path/metadata.
metadata:
  version: "0.3.0"
---

# content-extract — shared text-content retrieval helper

Adapted from `kiteworks-document-summarizer`'s `kw-binary-file-bridge` skill (that plugin's own docs explicitly say to copy the file into any plugin that needs it — there's no cross-plugin import mechanism in this plugin system).

Read `../surface-gate/SKILL.md` first. **This skill has mixed tiers, decided per file type:**
- The text-based path below needs no local file access at all — it's always Tier A/B regardless of surface, since `read_file_contents` returns content straight into the conversation.
- The binary path below needs local file access to land the downloaded bytes somewhere readable. **This is Tier C when local file access isn't available** — do the surface-gate detection before attempting a binary extraction, and if there's no native local access and no connected `Filesystem:` bridge, give the Tier C message rather than guessing a path or silently skipping the file.

## Two paths depending on file type

1. **Text-based files** (txt, csv, json, xml, md, log): call `read_file_contents` directly with the file's `id`. No download, no local file interaction, works identically on every surface. Check `get_file_metadata` first if the file might be large — `read_file_contents` warns it consumes context space.

2. **Binary files** (pdf, docx, pptx, xlsx, doc, ppt, xls, and similar): `read_file_contents` rejects these outright, so getting real text out needs a local file access step. Two paths depending on the surface (per `surface-gate`'s detection):

   **Cowork / Claude Code path (native local file access already available):**
   - Check `get_file_metadata` first — skip anything above a sane size cap (e.g. 20MB) rather than downloading it.
   - **Corrected 2026-07-14, live-verified — `/tmp` does NOT work as a `download_file_to_path` target.** An earlier version of this skill said to use a `/tmp` path. Live testing showed the Kiteworks connector's `download_file_to_path` tool runs as a process on the user's own machine (Windows), not inside Claude's Linux sandbox — a `/tmp/...` target reports a fully successful write (correct byte count) but the file lands somewhere the sandbox's own `Bash`/`Read` tools can never reach; a bare relative filename fails loudly instead (`Access is denied`, a Windows error string). The one target that actually works and is reachable afterward: **a path inside one of this session's own mounted/working folders** (the outputs/working directory Claude was given for this task, expressed as a real Windows path, e.g. `C:\Users\<user>\...\outputs\content-extract-<unix_timestamp>-<original_filename>.<ext>`) — confirmed live: the file appeared at the matching path under the sandbox's own mount and a format-skill tool (`pdftotext`) successfully extracted real text from it.
   - Use a unique per-run filename (`content-extract-<unix_timestamp>-<original_filename>`) to avoid collisions, same as the standard-Chat path below.
   - **Occasional transient read-after-write staleness:** once during live testing, a file that `download_file_to_path` reported writing successfully read back as 0 bytes / an empty stream on the very next tool call, then read correctly on a fresh download to a new filename moments later — consistent with this environment's known tool/filesystem view desync (see the `plugin-frontmatter-validation` memory). If a format-skill read immediately fails on a freshly-downloaded file, retry the download once to a new filename before concluding the source file itself is bad.
   - Read the downloaded file with native local tools and process it with the matching format skill already available in this environment (`pdf`, `docx`, `pptx`, `xlsx`) to get plain text out.
   - **Cleanup limitation, same as the standard-Chat path below — real deletion is NOT possible here either.** The only reachable download target (the session's own outputs/working mount) is a FUSE mount with no delete/unlink support at all (confirmed live — `rm`/`os.remove` fail with "Operation not permitted" on every file there, even ones just created). Scrub the temp file's *content* when done (overwrite with empty content, e.g. `: > <path>` via Bash) rather than attempting to delete it, and say so plainly if a user asks about cleanup — don't imply full removal. This corrects an earlier version of this skill, which claimed "Cowork's tools aren't limited the way the Chat-side extension is... real deletion is possible here" — that claim was wrong; both paths share the identical disclosed limitation now.

   **Standard Chat path (only a separate `Filesystem:` connector, if any, can reach a local path):**
   - Check whether a `Filesystem:list_allowed_directories`-style tool is available at all. Two distinct failure modes need two distinct messages (don't collapse them): not installed at all → tell the user this needs the Filesystem extension added; installed but not connected/configured → tell them to connect or reconfigure it. Give the surface-gate Tier C message either way before proceeding further.
   - If it is connected: pick an allowed directory, download there with a unique temp filename, bridge it into Claude's own sandbox with that extension's copy-in tool, then process it with the matching format skill.
   - Cleanup limitation on this path: the Filesystem extension typically can't delete, only overwrite content — say so plainly rather than implying full removal, and mention the leftover path.

   **Neither path available** (no native local access and no `Filesystem:` connector at all): this is the genuine Tier C case. Don't guess a path or invent a bridge — give the surface-gate Tier C message and fall back to name/path matching only for this file.

## This is real, per-file work — bound it

Unlike a (hypothetical working) server-side content search, this touches one file at a time: a metadata check, possibly a download, possibly a format-specific parse. Do not run it against every file in a large folder.

- Cap the number of files actually extracted per run (default 30, let the user raise or lower it) and say so explicitly in the result.
- Prioritize candidates sensibly when over the cap: most-recently-modified first, unless the user says otherwise.
- Always disclose the cap and how many files were actually checked vs. how many were in scope — this is the same partial-coverage discipline as the bounded walk in `folder-scan`.

## Privacy

Never surface the raw extracted text in chat or in any export — use it only to check for term matches internally, then discard it. Report only: file name, path, which term matched, and that the match came from real extracted content (vs. a name/path match). This is the same non-disclosure discipline `term-sweep` and `sensitive-content-scanner` already follow for pattern matches (never print matched values, only categories/counts), applied here to full extracted document text rather than just regex matches.
