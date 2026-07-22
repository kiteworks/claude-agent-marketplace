---
name: document-summarizer
description: >
  Use when the user asks to summarize, review, or explain what's in a file
  stored in Kiteworks — trigger phrases include "summarize X.docx in
  Kiteworks," "what's in the file at [path]," "give me the gist of that
  file," or any request to find and summarize a named document,
  spreadsheet, or presentation that lives in Kiteworks rather than being
  pasted or uploaded directly into the conversation. Do NOT use this for
  files already attached to the conversation — those can be read directly,
  no Kiteworks lookup needed.
metadata:
  version: "0.2.0"
---

Delegate to the `document-summarizer` subagent. If it reports no tools available, or returns a summary without making any Kiteworks tool calls, treat the result as fabricated, discard it, and ask the user to check the `Kiteworks` connector is connected. On other surfaces, follow this skill directly.

Read `../content-extract/SKILL.md` first for how binary files (.docx, .pdf, .pptx, .xlsx) actually get their text out — this agent never re-implements that bridge itself.

## Where this agent came from

Ported and rebuilt from an alpha `kiteworks-document-summarizer` plugin Rick had in a separate personal marketplace repo (`github.com/rickgoud/kw-claude-marketplace`). That version's good ideas are kept (see below); its infrastructure is replaced with this project's already-hardened shared skills rather than duplicated:

- The alpha shipped its own `kw-binary-file-bridge` skill (a Filesystem-extension-based bridge for standard Chat, with a real disclosed limitation: no delete, only overwrite). This project's `content-extract` already solves the same problem more completely — it's surface-aware via `surface-gate`, uses `/tmp` (not the undeletable outputs mount) on the Cowork path, enforces a file-size cap before downloading, and bounds how many files get extracted per run. No reason to carry a second implementation of the same bridge.
- The alpha had no subagent at all — it was a bare skill. This agent follows this project's standard pattern instead: a real subagent with a scoped tool list, so a run that silently didn't call any Kiteworks tool can be caught and discarded rather than trusted.

## Kept from the alpha, because they're genuinely good and don't exist elsewhere in this plugin yet

- **Check the file before reading it.** Call `get_file_metadata` and look at `avStatus`/`dlpStatus` before summarizing — confirmed live 2026-07-14 that this Kiteworks tenant's `get_file_metadata` really does return both fields (its own tool description undersells this, listing only "filename, size, dates, type, and owner"). If either status isn't a clean "allowed," say so and stop rather than summarizing a file that hasn't cleared scanning. A sensitivity/classification label (e.g. an MSIP tag) was NOT present in this tenant's metadata payload when checked live — if a future tenant's metadata does expose one, surface it in the summary; don't assume it's always there.
- **Ambiguous match → ask, don't guess.** If a name/description search returns more than one candidate, list path + last-modified for each and ask which one.
- **Never reproduce sensitive identifiers verbatim in the summary.** Government IDs, full financial account numbers, credentials, or similarly sensitive strings get described generically ("a sample ID number"), never quoted — even if the source is explicitly a test file. Same spirit as `term-sweep`'s "never print matched values," generalized to free-text summarization.
- **Traceable by default.** Every summary states the file's path and last-modified date, and restates the AV/DLP check result (and sensitivity label, if one existed) alongside the summary — not just logged internally.
- **Proportional length, no upfront length question.** Default to a sentence or two for a short file, a short paragraph plus a few key-point bullets for a longer one. Offer to go shorter/longer/more detailed after, don't ask before.

## Corrected from the alpha

The alpha's Step 1 said to search "using the name or description the user gave" without flagging a real gotcha this project already hit and documented in `folder-scan`: **`content_contains` on `search`/`search_files` is confirmed non-functional on this connector.** Match on `path_contains` or an exact `path`, never `content_contains` — if the user's file description sounds like a content query rather than a name/path, say plainly that Kiteworks search can't do that and ask for the file by name or folder instead.

## Step 1 — Find the file

`search_files` (or `search`) with `path_contains` on the name/description the user gave, optionally narrowed with `parent_folder_id` if the user named a folder.

- **Exactly one match:** proceed.
- **Multiple matches:** list candidate paths + last-modified and ask which one.
- **No matches:** say so plainly, ask for a more specific name or folder — never invent a result.

## Step 2 — Check the file

`get_file_metadata` on the matched file. `avStatus`/`dlpStatus` must both read as clean/allowed before proceeding — if either shows scanning-in-progress, blocked, or flagged, tell the user and stop. Note any sensitivity/classification field if present.

## Step 3 — Get the content

Text-based (`.txt`, `.csv`, `.json`, `.xml`, `.md`, `.log`): read directly per `content-extract`'s text path. Binary (`.docx`, `.pdf`, `.pptx`, `.xlsx`, `.doc`, `.ppt`, `.xls`): route through `content-extract`'s binary path (it already picks Cowork-native vs. Filesystem-extension-bridge vs. Tier C correctly for the current surface). Anything else (encrypted, image-only scans without OCR, unrecognized format): say plainly that this format isn't supported yet — don't attempt a partial read.

## Step 4 — Write the summary

Proportional length (see above); never quote sensitive identifiers verbatim; always restate path, last-modified, and the Step 2 check result alongside the summary.

## Step 5 — Actively offer to save it, don't wait passively

End by asking, e.g.: *"Want me to save this summary back to Kiteworks?"* If yes, ask .txt or .docx, and confirm the destination — **default to the same folder as the source file** (a deliberate difference from this plugin's usual `My Folder/Agents/<Agent Name>/` convention: a document summary is a companion to one specific file, not a row in a bulk scan report, so it belongs next to what it summarizes unless the user says otherwise). Only write once confirmed.

- **.txt:** `create_file_from_content`, UTF-8, with a short header (`Summary of: <path>`, `Generated: <date>`, `Summarized by: <get_user_info_whoami>`) above the summary text.
- **.docx:** use the `docx` skill's full creation process, **including its render-and-verify step**, before uploading. Only after visual verification, `upload_file_from_path` straight to the Kiteworks destination — **never base64-encode it into `create_file_from_content`.** Live-tested 2026-07-14: a hand-copied base64 string of the built docx was corrupted twice in two different ways between tool calls (once truncated, once with a chunk duplicated), each time reporting a clean success with a plausible-looking response — only a byte-for-byte re-download-and-diff caught it. `upload_file_from_path` uploads straight from the local file, no string relay, no corruption risk; verify afterward by checking the response's `size` matches the local file's real size (or re-download and diff for a higher-stakes write). See `../report-export/SKILL.md`'s corrected rule — same fix, same root cause, applies everywhere in this plugin that writes a binary file.
