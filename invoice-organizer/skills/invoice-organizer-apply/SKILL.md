---
name: invoice-organizer-apply
description: >
  Use when the user has confirmed which invoice/receipt renames (and,
  optionally, category-folder sorting) to apply from an
  invoice-organizer-preview result -- trigger phrases include "rename
  those receipts" or "apply the invoice organizer." Never call without a
  confirmed per-item list.
metadata:
  version: "0.1.0"
---

Delegate to the `invoice-organizer-apply` subagent, passing only the user-confirmed file list (with each file's extracted fields and proposed new name). Read `../report-export/SKILL.md` first.

# Invoice & Receipt Organizer — apply

## Never touches Low-confidence files

Only act on files the preview step marked High or Medium confidence AND the user explicitly confirmed. A Low-confidence file that the user hand-corrects in conversation (e.g. "the total is actually $54.10, go ahead") is fine to include — the gate is explicit confirmation, not the tier label alone once a human has verified it.

## Steps

1. **Rename**, per confirmed item: `rename_file` with the confirmed new name (same mechanism `naming-cleanup-apply` already uses, confirmed live there). Require per-item confirmation before renaming — never bulk-rename an entire proposed list on one blanket "yes," same rule every two-phase agent in this family follows.
2. **Optional category-folder sorting**: only if the user asked for it in preview. If so, `move_file` each confirmed, renamed item into `<destination>/<Category>/` (create the category subfolder if missing, via `create_folder`). Ask for the destination root explicitly if not already given — never invent one. If the user didn't ask for folder sorting, skip this step entirely; renaming in place is the default.
3. **Export the CSV**, per `report-export`'s destination/disclaimer convention, into `My Folder/Agents/Invoice Organizer/` (or the user's specified destination). Columns: original filename, new filename, vendor, date, invoice/receipt number, subtotal, tax, tip, total, currency, payment method (already masked by preview — never re-derive or print a raw number here either), category, confidence tier, possible-duplicate flag, link. Include every processed item, not just the ones that got renamed, with a status column noting skips (AV/DLP-blocked, unsupported format, Low-confidence-excluded).
4. **Write the narrative** (txt or pdf per the user's preference, via `../kw-pdf-report/SKILL.md` for pdf) with the standard `report-export` metadata block (`standard_metadata()`) plus this agent's own rows: category scheme used, filename convention used, count by confidence tier, OCR-derived count, currency-mix note if applicable. Embed **both** disclaimers verbatim: the standard `report-export` one and the tax-specific one from `invoice-organizer-preview` ("best-effort extracted/OCR'd values, not verified accounting data — reconcile against your bank/card statement before filing taxes").
5. Report back plainly what was renamed, moved (if applicable), and where the CSV/narrative landed — plus a reminder of how many files still need manual review and why.

## No delete tool, ever

This agent only renames, optionally moves, and writes new report files — it is never granted `delete_file` or `delete_folder`, consistent with every apply agent in this plugin family.
