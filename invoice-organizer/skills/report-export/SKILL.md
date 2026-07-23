---
name: report-export
description: >
  Shared internal reference skill, not invoked by users directly. Every
  apply skill in this plugin (retention-sweeper-apply,
  storage-visualizer-apply, duplicate-finder-apply) reads this file to
  learn the standard way to write a CSV and a txt/pdf report into
  Kiteworks. Read this before writing or modifying any apply skill in
  this plugin.
metadata:
  version: "0.5.0"
---

# report-export — shared CSV + txt/pdf writer

Read `../surface-gate/SKILL.md` first. **This skill is Tier B**: no apply skill in this plugin is ever granted a delete tool, and every write here is narrow and documented (create a folder, write a file) — so if subagent isolation isn't available, disclose that once and proceed directly rather than refusing. This skill never needs local file access, so it is never Tier C.

Use the `Kiteworks` connector for writes: `create_folder`, `create_file_from_content` (plain-text CSV/txt), `upload_file_from_path` (any binary artifact — see the corrected rule below). Apply subagents should only be granted the specific write tools they need (`create_folder`, `create_file_from_content`, `upload_file_from_path`, plus `move_file` only for agents whose apply step relocates files, e.g. duplicate-finder-apply). Never grant `delete_file` or `delete_folder` to any apply subagent in this plugin — no agent here deletes anything itself.

## Corrected 2026-07-14, live-verified — never base64-encode-and-paste a binary file into `create_file_from_content`

An earlier version of this skill said to base64-encode a generated PDF/docx and pass it via `create_file_from_content`'s `content` argument with `encoding: "base64"`. **Don't do this.** Live-tested while building `document-summarizer`'s .docx save-back: a real ~14KB base64 string, hand-copied from one tool call's output into the next tool call's `content` argument, arrived corrupted twice in a row — once truncated (reported success, but the uploaded file wasn't even a valid zip), once with a chunk of the string duplicated (reported success, wrong byte count). Both looked like clean successes; only a byte-for-byte re-download-and-diff caught them. Retyping/relaying a large base64 blob as literal text between tool calls is not reliable in this environment, regardless of file size — a small file can hit this too, it's just less likely to visibly break.

**The fix: use `upload_file_from_path` for every binary artifact (PDF, docx, xlsx, pptx, or any other non-text output), never `create_file_from_content` + base64.** Write the file to a real path inside this session's own mounted/working folder (the same path convention `content-extract` now uses for downloads — a real Windows path under the outputs/working directory, reachable by both this session's own tools and the Kiteworks connector), then call `upload_file_from_path(parent_id, source)` directly on that path — no base64 round-trip, no large string to relay between calls. Verify with a byte-for-byte check afterward (download the just-uploaded file back and diff, or at minimum compare `size` in the upload response against the local file's real size) before telling the user the write succeeded. `create_file_from_content` (plain UTF-8, no `encoding` argument) remains correct and reliable for the CSV/txt artifacts below — those are typically small and are generated as literal text already, not relayed as an opaque encoded blob.

## Destination convention

Every agent writes into `My Folder/Agents/<Agent Name>/`, created on first use if missing:

1. Resolve the real "My Folder" id per `folder-scan`'s gotcha (use the `get_top_folders` entry named "My Folder" / `syncdirId` — never `mydirId`, which rejects `create_folder`).
2. Look for a child folder named "Agents" under it; create it if absent.
3. Look for a child folder named after this agent (e.g. "Retention Sweeper") under "Agents"; create it if absent.
4. If the user specifies a different destination folder, use that instead — confirm it with the user before writing either way.

Never create a folder or write a file without the user confirming the action and destination first.

## What to write, every time

Write files per run into the destination folder, using a deterministic, collision-safe name (append a numeric suffix, e.g. `-2`, if a same-named file already exists — never overwrite):

1. **`<agent-name>-<YYYY-MM-DD>.csv`** — every row of detailed results. Ask the user whether the CSV should contain only flagged/actionable items or the full scanned set with a flag column — default to full scanned set with a boolean/status column when the user hasn't said.
2. **`<agent-name>-<YYYY-MM-DD>.txt`** (or **`.pdf`** if the user prefers a non-editable format — build it via `kw-pdf-report`, then upload the local file with `upload_file_from_path`, never base64 through `create_file_from_content` — see the corrected rule above) — a human-readable narrative: summary counts, top items, coverage/truncation caveats, and the disclaimer below.
3. Embed both layers verbatim in the txt/PDF narrative and as two `# ...` comment header lines atop the CSV:
   - **Legal layer (generated from the install disclaimer at publish time):** Kiteworks agents are provided **as is**. They are helpful, but they can be wrong. You are responsible for checking what an agent produces before you rely on it, and Kiteworks is not liable for outcomes from using them.
   - **Scope caveat for this agent:** This Invoice Organizer report is a best-effort analysis based only on the Kiteworks content and metadata scanned. It may be incomplete or inaccurate, and does not evaluate unscanned systems, legal obligations, or tenant retention policy; review results before acting.
   For PDF, pass the scope caveat as `scope_caveat` to `build_branded_pdf()`; the legal layer is fixed by the published builder and cannot be omitted by a caller.
4. If no file is exported, append both layers to the final chat response whenever it presents completed assessment or scan results.

## Every report must say who ran it and what it covered

A report that only shows findings, with no record of who ran it or what was scanned for, is missing basic audit context. Every txt/pdf report must state, near the top, before any findings: the folder/scope (with a link to it, if the connector exposes one), who ran it (`get_user_info_whoami`), the generated date, where the report itself was saved (with a link), and the scan-specific parameters (term list, PII pattern categories, retention threshold, time window — whichever apply to that agent). For PDF this is `kw-pdf-report`'s `metadata` block, built via `standard_metadata()` (see below); for txt, put the same facts as a plain-text "Report details:" block before the narrative.

## Generic vs. agent-specific metadata — the formal split

Every agent's Report details block has the same shape: a fixed generic part (scope, output location, who, when) that is identical across all 13 agents, plus a small agent-specific part that only that one agent needs. This is not just a convention — `kw-pdf-report`'s `standard_metadata()` function is the single implementation of the generic part, so no agent hand-rolls it:

- **Generic (via `standard_metadata()`, same for every agent)**: the scope being acted on (folder, mailbox, person — `scope_label` lets each agent phrase this row appropriately, e.g. "Folder scanned" vs. "Person" vs. "Mailbox reviewed"), linked to the resource in Kiteworks when a link is available; where the report itself was saved, also linked; who ran it; when it was generated.
- **Agent-specific (appended by each agent after calling `standard_metadata()`)**: whatever extra facts only that agent's scan produced — sensitive-content-scanner appends "Terms / patterns checked"; retention-sweeper would append the retention threshold; activity-digest would append the time window; naming-cleanup would append the naming convention applied. Add these as plain `(label, value)` tuples appended to the list `standard_metadata()` returns.

## PDF generation

When the user wants a PDF rather than txt, read `../kw-pdf-report/SKILL.md` and generate it via `../kw-pdf-report/scripts/branded_pdf.py` — never a generic ad hoc `reportlab`/`pdf`-skill call. This gets four things for free that a one-off call won't: consistent Kiteworks brand structure (the real logo, the documented dark hero band, the real print/paper tokens — not a guessed palette), cell text that actually word-wraps inside table columns instead of overflowing into the next one, a standard place for the who-ran-it/what-it-covered facts with real clickable Kiteworks links, and the generic/agent-specific metadata split above handled consistently.

Build the metadata list via `standard_metadata(scope_label, scope_name, scanned_by, generated_on, scope_link=, output_folder_name=, output_folder_link=)`, then append this agent's own specific rows before passing the combined list to `build_branded_pdf`'s `metadata` argument. `report_title` must stay generic (e.g. "Sensitive Content Scan Report") — never the specific folder name; that belongs in `metadata`. The hero band itself carries only the logo and the agent name — never the report title or any scope-specific text, which is what caused a visual overlap/redundancy bug once (see `kw-pdf-report/SKILL.md`'s correction note). `build_branded_pdf` already writes the PDF to a local path — pass that same path straight to `upload_file_from_path`, per the corrected rule above; never base64-encode it into `create_file_from_content`.

## Confirm before every write

Steps, in order: (1) build the result set in the preview phase; (2) show the user counts + a sample and ask them to confirm the action and destination; (3) only then create any folder or file. Never chain preview → apply without an explicit user confirmation in between.
