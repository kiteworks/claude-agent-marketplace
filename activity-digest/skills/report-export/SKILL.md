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
  version: "1.0.0"
---

# report-export — shared CSV + txt/pdf writer

Read `../surface-gate/SKILL.md` first. **This skill is Tier B**: no apply skill in this plugin is ever granted a delete tool, and every write here is narrow and documented (create a folder, write a file) — so if subagent isolation isn't available, disclose that once and proceed directly rather than refusing. Plain-text export needs no local access. Binary uploads and optional download-back verification require a verified connector-visible mapping; apply Tier C if that capability is unavailable.

Use the resolved Kiteworks connector (see `connector-probe`) for writes: `create_folder`, `create_file_from_content` (plain-text CSV/txt), `upload_file_from_path` (any binary artifact — see the corrected rule below). On a connector without `upload_file_from_path` the save step follows `connector-probe`: offer the CSV + text version with its approved copy and do not attempt a PDF. Apply subagents should only be granted the specific write tools they need (`create_folder`, `create_file_from_content`, `upload_file_from_path`, plus `move_file` only for agents whose apply step relocates files, e.g. duplicate-finder-apply). Never grant `delete_file` or `delete_folder` to any apply subagent in this plugin — local scratch cleanup uses only the separately authorized executor in `../scratch-lifecycle/SKILL.md`.

## Corrected 2026-07-14, live-verified — never base64-encode-and-paste a binary file into `create_file_from_content`

An earlier version of this skill said to base64-encode a generated PDF/docx and pass it via `create_file_from_content`'s `content` argument with `encoding: "base64"`. **Don't do this.** Live-tested while building `document-summarizer`'s .docx save-back: a real ~14KB base64 string, hand-copied from one tool call's output into the next tool call's `content` argument, arrived corrupted twice in a row — once truncated (reported success, but the uploaded file wasn't even a valid zip), once with a chunk of the string duplicated (reported success, wrong byte count). Both looked like clean successes; only a byte-for-byte re-download-and-diff caught them. Retyping/relaying a large base64 blob as literal text between tool calls is not reliable in this environment, regardless of file size — a small file can hit this too, it's just less likely to visibly break.

**The fix: use `upload_file_from_path` for every binary artifact (PDF, docx, xlsx, pptx, or any other non-text output), never `create_file_from_content` + base64.** Write intended deliverables to a verified connector-readable destination and call `upload_file_from_path(parent_id, source)` directly. Preserve intended reports, summaries, redacted copies and audit exports. Verify at minimum the upload response size against actual local size; report that as size verification, not byte-for-byte equality. Optional download-back verification must follow `../scratch-lifecycle/SKILL.md`: disclose destinations/transfers before downloading, reserve an `upload_verification` artifact before the write, compare bytes in the verified execution location, then release that copy in a finally block and finalize the run. If its download or cleanup executor is unavailable, skip the optional download and accurately report the verification limit. Never delete the intended deliverable during scratch cleanup. `create_file_from_content` (plain UTF-8, no `encoding` argument) remains correct and reliable for the CSV/txt artifacts below — those are typically small and are generated as literal text already, not relayed as an opaque encoded blob.

## Destination convention

Every agent writes into `My Folder/Agents/<Agent Name>/`, created on first use if missing:

1. Resolve the real "My Folder" id per `folder-scan`'s gotcha (use the `get_top_folders` entry named "My Folder" / `syncdirId` — never `mydirId`, which rejects `create_folder`).
2. Look for a child folder named "Agents" under it (`get_folder_children`); create it if absent.
3. Look for a child folder named after this agent (e.g. "Retention Sweeper") under "Agents"; create it if absent.
4. If the user specifies a different destination folder, use that instead.

Never create a folder or write a file without the user confirming the formats and destination first — collected up front by the report preflight below, never by a question asked in the middle of a subagent run.

## What to write, every time

Write only the formats the report preflight selected, into the destination folder, using a deterministic, collision-safe name (append a numeric suffix, e.g. `-2`, if a same-named file already exists — never overwrite):

1. **`<agent-name>-<YYYY-MM-DD>.csv`**, only if authorized — the complete enumerated inventory with per-check statuses, reasons and finding IDs, derived from the same assessment record as the narrative. An explicitly requested findings-only export is a separately named derivative; it is not the complete inventory. Never add a companion format without authorization.
2. **`<agent-name>-<YYYY-MM-DD>.txt`** and/or **`.pdf`** (whichever the preflight selected; the PDF is the non-editable one — build it via `kw-pdf-report`, then upload the local file with `upload_file_from_path`, never base64 through `create_file_from_content` — see the corrected rule above) — a human-readable narrative: summary counts, top items, coverage/truncation caveats, and the disclaimer below.
3. Embed both layers verbatim in the txt/PDF narrative and as two `# ...` comment header lines atop the CSV:
   - **Legal layer (generated from the install disclaimer at publish time):** This report was generated by an AI agent and is not a compliance certification, audit opinion, or legal determination of compliance with any law, standard or framework, nor legal advice. It reflects only the files and inputs actually scanned on {scan_date} and may be incomplete or inaccurate. Provided "as is", without warranty to the extent permitted by applicable law — verify independently before relying on it or sharing it with an auditor or regulator. Full terms: https://agents.kiteworks.com/legal/marketplace-terms
   - **Scope caveat for this agent:** This Activity Digest report is a best-effort analysis based only on the Kiteworks content and metadata scanned. It may be incomplete or inaccurate, and does not evaluate unscanned systems, legal obligations, or tenant retention policy; review results before acting.
   The legal layer contains a `{scan_date}` placeholder. Replace it with the date this scan actually ran, as `YYYY-MM-DD` — the same date used in the file names above. Never leave the placeholder in an exported file, and never substitute a different date: the sentence states what the report covers, so a wrong date misstates the scope of the scan rather than just looking untidy.
   For PDF, pass the scope caveat as `scope_caveat` to `build_branded_pdf()` and the scan date as `scan_date`; the legal layer is fixed by the published builder and cannot be omitted by a caller, and the builder fills the date itself (defaulting to today when `scan_date` is not passed).
4. If no file is exported, append both layers to the final chat response whenever it presents completed assessment or scan results.

## Executive narrative and evidence

Document Summarizer retains its source-linked TXT/DOCX workflow and its own
format instructions. It does not become a compliance assessment or gain a PDF
workflow through this shared reference.

Use the version 2 assessment record in ../kw-pdf-report/SKILL.md and the
appropriate report-profiles.md family. Lead with a cover and executive summary:
purpose, conclusion, coverage, key findings and decisions requested. The body
explains observations, business implications and prioritized actions. Put
detailed methods and the complete enumerated inventory in appendices.
Do not describe internal "signals" as statutory terminology or present the
absence of detected matches as compliance.

The run record supplies stable report ID/version, scope, operator, assessment
and generation times, completeness and review status. profile_details records
the actual parameters, policy/framework version, source/output location and
unknowns. Source links belong to the inventory. Filenames and sensitive evidence
should appear only where needed; avoid raw personal-data excerpts.

Coverage counts come from the same inventory used by CSV, TXT and PDF.
Every object records every configured check, including failures and exclusions.
Enumerated is not the same as content-inspected. List unvisited scope separately
and never estimate an unknown denominator. No finding may reference unchecked
content. Owners and deadlines remain proposed until confirmed.

**Inventory placement** is set in the record as `report_mode.inventory`:

- `companion` when CSV and PDF are both authorized: the PDF is the executive
  report and the file-by-file list goes to the CSV.
- `compact` (complete one-row-per-object table) when only PDF is authorized.
- `omitted_by_request` only when the user explicitly asked to leave the
  inventory out.
- `embedded` only for the legacy detailed appendix.

Never claim a companion that was not saved, and never truncate silently.

**CSV-first publication**, in order:

1. `export --format csv`.
2. Save the CSV with `upload_file_from_path`, using the collision-safe name
   `<agent-name>-<date>.csv`.
3. Compare the response size with the local size.
4. Take the stable link from `links.web_url` / `permalink` of the saved file,
   from the save response or from `get_folder_children` on the destination
   matched by file id. Never use `get_download_link` (temporary) and never
   construct a URL by hand.
5. Write `delivery.json` (Write tool, staging folder) with the saved name,
   location, link, row count (the `objects` value printed by export), local
   byte size and `size_verified`.
6. Run `build ... --delivery <base>/_kiteworks-report/delivery.json`.
7. Upload the PDF.

If no stable link is available, omit `url`; the PDF then shows name, location
and report ID without a link. If the PDF upload fails after the CSV succeeded,
report exactly which files exist; on retry, reuse the already-saved CSV (same
report ID/version in its first lines) instead of uploading a second copy.
Connectors without `upload_file_from_path` produce no PDF; the existing
CSV/TXT fallback through `create_file_from_content` applies unchanged.

## PDF generation

Use ../kw-pdf-report/scripts/branded_pdf.py and the shared assessment contract.
Legacy standard_metadata()/sections remain for existing integrations, not new
agent reports. The shared renderer owns brand assets, typography, page breaks,
navigation, tables, metadata and legal disclosures. Report titles are generic;
scope belongs on the cover and in report details. Use the actual assessment
date for scan_date. See kw-pdf-report for supported scripts and the current
tagged-PDF accessibility limitation.

### Stage with the Write tool, build with `build --json-file`

**The rule: never write .py helper files, and never generate report text through
heredocs, `printf` or a Python one-liner.** Report text pushed through a shell
is how apostrophes, `<`/`>`, non-ASCII characters and the Windows
command-length limit have quietly changed delivered reports (see
`kw-pdf-report/SKILL.md`). Every local file of a report run goes through the
Write tool into one staging folder instead:

1. The staging folder is `<base>/_kiteworks-report/`, where `<base>` is a
   user-private local folder the connector can read for
   `upload_file_from_path` (the `content-extract` host folder when the run
   downloads files). Your Write tool is limited to `.json`, `.csv`, `.txt`
   and `.md` files directly inside a folder named exactly
   `_kiteworks-report`; every other path is refused.
2. Write `spec.json` there with the Write tool using the complete
   `../kw-pdf-report/examples/assessment.json` example and profile instructions.
   Record facts once; do not hand-roll different populations per format.
3. Derive authorized CSV/TXT first with
   `python ../kw-pdf-report/scripts/branded_pdf.py export --json-file
   <base>/_kiteworks-report/spec.json --format csv --out
   <base>/_kiteworks-report/inventory.csv` (or `--format txt`).
   This keeps the record for the PDF. On a text-only host with no local
   executor, compose the authorized text output from the same ledger.
4. Build (with a saved companion CSV, first follow CSV-first publication above
   and add `--delivery <base>/_kiteworks-report/delivery.json`):
   `python ../kw-pdf-report/scripts/branded_pdf.py build --json-file
   <base>/_kiteworks-report/spec.json --out
   <base>/_kiteworks-report/<agent-name>-<YYYY-MM-DD>.pdf`. It prints
   `{"pdf": ..., "pages": ..., "bytes": ..., "spec_removed": true}` and
   removes the staged spec. A malformed spec exits 2 with an `error:` line
   naming the expected shape; fix the spec with the Write tool and rerun.
5. Upload only the selected formats with `upload_file_from_path` into the confirmed
   destination and compare the response sizes with the local sizes. For a
   txt report without a PDF, or on a connector without
   `upload_file_from_path`, write the CSV/txt with `create_file_from_content`
   as described above instead.
6. Clean up: `python ../kw-pdf-report/scripts/branded_pdf.py cleanup --dir
   <base>/_kiteworks-report` deletes the staged files and the empty folder and
   lists anything it kept. Run it once the local files are no longer needed,
   whether or not the upload succeeded, and report any kept path.

`scope_caveat` is still required and the published legal footer is still
fixed, exactly as above. Only when the host has no Write tool at all, fall
back to `branded_pdf.py spec-append` (base64 chunks, then `build --spec`) as
`../kw-pdf-report/SKILL.md` describes.

## Report preflight — ask before the scan, never mid-run

A plugin agent runs as a subagent. A subagent cannot ask the user anything: it
has no `AskUserQuestion`, and a reply the main conversation passes along
afterwards arrives second-hand, so a careful agent cannot accept it as the
user's confirmation. An agent that finishes its scan and then asks "want me to
save this?" deadlocks — the report never gets written. So the question is asked
once, by the main conversation, **before** the agent starts:

1. **Main conversation, before delegating:** ask which report to save, as one
   multi-select question — with `AskUserQuestion` (`multiSelect: true`) where
   the host has it, otherwise as a short numbered list in plain text. The
   options are exactly:
   - **CSV** — every row of detailed results (recommended with PDF)
   - **PDF** — executive report (when CSV is also selected, the file-by-file list goes to the CSV)
   - **TXT** — plain-text narrative report
   - **No saved report** — results in the chat only

   In the same call, confirm the destination: `My Folder/Agents/<Agent Name>/`
   (the default) or a folder the user names. If the user picks "No saved
   report" together with a format, ask again; never guess which one they meant.
   A plugin whose report formats differ (e.g. document-summarizer's .txt/.docx)
   lists its own formats instead, with the same "No saved report" option.
2. **Hand the answer to the agent** at the top of its task prompt, in exactly
   this shape:

   ```text
   Report preflight (asked of the user before this run):
   - formats: csv, pdf
   - destination: My Folder/Agents/<Agent Name>/
   ```

   `formats` lists any of `csv`, `pdf`, `txt` (or the plugin's own formats), or
   is `none`.
3. **The agent:** that block **is** the user's confirmation. When the scan is
   done, write exactly the listed formats to that destination without asking
   again, then report what was written (file names, sizes, links). With
   `formats: none`, or with no block at all, write nothing: present the results
   and end by saying that a saved report can be requested by running the agent
   again. Never end a run with a question that waits for the user's answer.

Two-phase plugins keep report writing separate from source mutations. Collect
the report preflight before a proposal report is requested; delegate report
creation to the report-only agent. Saving a proposal never invokes the apply
agent or grants move/rename/update rights. After separately authorized actions,
the apply agent may save a completion receipt with verified outcomes and the
same report preflight. A receipt cannot reuse proposed actions as completed.

When no subagent is used (the host cannot run one), the main conversation
follows the skill itself and still asks the preflight question before the scan.

## Connector tools this skill uses

- Calls: `get_top_folders`, `get_folder_children`, `create_folder`,
  `create_file_from_content`, `upload_file_from_path`, `get_user_info_whoami`.
- Named only: `move_file`, `delete_file`, `delete_folder`, `get_download_link`.

The Calls tools are granted to every agent that reads this skill: resolving
and creating the destination folder, writing the CSV/txt, uploading a binary
report, and naming who ran it. `move_file` belongs only to apply agents whose
own skill relocates files; this skill never calls it. The delete tools are
never granted to an agent that follows this skill. `get_download_link` is named only to forbid it: its links are temporary, so a report never references one.
