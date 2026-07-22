---
name: redactor-apply
description: >
  Use when the user confirms creating redacted/find-replaced copies from
  a redactor-preview result — trigger phrases include "create those
  redacted copies" or "go ahead and replace it." Never call without a
  confirmed file list, replacement, and destination.
metadata:
  version: "0.2.0"
---

Delegate to the `redactor-apply` subagent after confirming the file list, replacement, and destination. Read `../content-extract/SKILL.md` and `../report-export/SKILL.md`.

# Redactor — apply

## Never touches originals

This agent only ever creates new files. No move, rename, or delete tool is granted — the original file is never modified, moved, or removed, regardless of mode.

## For each confirmed high-confidence file

1. `download_file_to_path` the original to a `/tmp` scratch path (collision-safe temp name, per `content-extract`) — **never the session's outputs/working-folder mount**, which has no delete support at all (confirmed live) and would leave every downloaded original stranded plus trigger a delete-permission prompt per file.
2. Apply the replacement with the matching library: plain string replace for text files; `python-docx`/`openpyxl`/`python-pptx` for docx/xlsx/pptx, editing runs/cells/text frames so surrounding formatting survives.
3. `upload_file_from_path` the modified copy into the confirmed destination folder — never back into the source folder, never reusing the original file's name unmodified (append a suffix, e.g. `-redacted`, to make it visually obvious this is a derived copy).
4. Delete the local scratch copies when done via Bash (`rm -f`) — `/tmp` genuinely supports deletion, so this succeeds silently, no permission prompt.

If the user explicitly accepted the PDF caveat from preview, attempt the same download/replace/upload flow for PDFs but repeat the true-redaction caveat in the result; otherwise skip PDFs entirely and leave them in the "needs manual review" list.

## Always write a manifest — this is the audit trail

Read `../report-export/SKILL.md` for the destination/disclaimer convention, but the primary product here is the redacted files, not a report about them — write the manifest alongside, not instead of, the copies.

Write a CSV (original file name/path/link, redacted copy name/link, match count, replacement used [or placeholder if pattern mode], method — text-replace/docx/xlsx/pptx/pdf-attempted, confidence tier) and a short txt/pdf narrative (mode, term/pattern and replacement, counts, which files were skipped and why, the PDF caveat verbatim if any PDFs were in scope). Default agent name: "Redactor".

## Present the result

Confirm what was created and where, with links to both the manifest and the redacted copies' containing folder. State plainly that originals were left untouched.
