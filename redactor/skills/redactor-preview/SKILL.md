---
name: redactor-preview
description: >
  Use when the user wants to remove or replace specific text across
  documents in Kiteworks before doing anything — trigger phrases include
  "redact [term] from X," "replace 'Rick Goud' with 'John Doe' in these
  files," "find and replace across this folder," or "redact PII from
  these documents." Read-only: proposes what would change and in which
  files, creates and changes nothing.
metadata:
  version: "0.3.0"
---

Delegate to the `redactor-preview` subagent. Read `../content-extract/SKILL.md` first, and `../term-sweep/SKILL.md` if the user wants built-in PII pattern redaction rather than a literal term.

# Redactor — preview

## Why this is a separate agent, not a mode of the scanner agents

Creating a modified copy of a document's actual content is the most consequential write action in this whole plugin family — more so than a report or even a move. It deserves its own real preview/apply gate rather than being folded into `sensitive-content-scanner` (which never touches file content, only reports on it). It's also generically useful outside PII: replacing any literal string in any set of documents, redaction or not.

## Two modes — ask the user which they mean

1. **Literal find-and-replace**: the user supplies an exact search string and a replacement (e.g. "Rick Goud" → "John Doe"). The string is already known to the user — it's fine to show match counts and location context (page/paragraph/cell reference) since there's no confidentiality concern in the term itself. Still never dump full surrounding file content into chat.
2. **Pattern-based redaction**: the user wants built-in PII categories or a custom term list replaced with a placeholder (e.g. `[REDACTED-SSN]`). All built-in categories are available by default, same as `sensitive-content-scanner` — don't single out a country-specific one (e.g. Dutch BSN) as needing separate confirmation. If the user wants a narrower set, offer `term-sweep`'s tag-based `--categories` selector (exact category, `region:`, `type:`, or `all`). Follow `term-sweep`'s privacy rule exactly — never print the matched value, only counts per category/term.

Ask which mode, the term list or PII categories, the replacement value or placeholder, and the folder scope (required).

## Collect the destination

A destination folder for the redacted copies (required, distinct from the source folder — this agent never overwrites or replaces the original file, no move/rename/delete tool exists here or in apply).

## Sweep and assess format support — be honest about confidence, don't overclaim

Find candidate files per `folder-scan`/`term-sweep`'s name/content matching. For each candidate, determine format support before proposing it:

- **txt, csv, json, xml, md, log**: plain string replace. High confidence.
- **docx, xlsx, pptx**: real text replacement via `python-docx`/`openpyxl`/`python-pptx` (run through `Bash`, install with `--break-system-packages` if not already present), editing runs/cells/text frames directly. High confidence, preserves formatting reasonably well.
- **pdf**: **flag as lower confidence.** True redaction means removing the underlying text object, not just drawing a box over it — a box-only overlay leaves the original text extractable underneath, which is a real compliance failure, not a cosmetic one. Unless a verified library path for true text-object removal is confirmed working in this sandbox, do not silently attempt a lossy redaction — tell the user PDFs in scope need manual review/redaction instead, and exclude them from the proposed apply set by default (offer to attempt anyway only if the user explicitly accepts the caveat).
- **doc, ppt, xls (legacy binary)**: unsupported — flag and ask the user to convert to the modern format first.

## Present the result, then let the user decide on apply

Summary card: mode used, term/pattern and replacement, per-file candidate list with match count and format-support tier (high-confidence / needs-manual-review / unsupported), destination folder, coverage, warnings. Do not create anything yet.

End with an explicit next step, e.g.: *"Want me to create redacted copies of the N high-confidence files in [destination]? The M PDF/legacy files need manual handling."* Hand the confirmed-per-file list forward for apply exactly like the other real preview/apply agents in this family.
