---
name: invoice-organizer-preview
description: >
  Use when the user wants to find, read, and organize invoices or receipts
  in a Kiteworks folder for expense/tax prep -- trigger phrases include
  "organize my receipts," "find invoices in X folder and rename them,"
  "extract vendor/amount/date from these receipts," or "get my receipts
  ready for taxes." Read-only: proposes renames and a categorized CSV,
  creates and changes nothing.
metadata:
  version: "0.2.0"
---

Delegate to the `invoice-organizer-preview` subagent. If you already are that subagent, do not delegate again: follow this skill directly. When the subagent returns a `NOT_CONTENT_CHECKED_HANDOFF` block, the delegating session (never the subagent itself) follows `../content-extract/COORDINATOR.md` before reporting. Read `../folder-scan/SKILL.md` and `../content-extract/SKILL.md` first. Read `scripts/ocr_extract.py`'s own docstring before using it -- it's this skill's own OCR fallback, not part of `content-extract`.

# Invoice & Receipt Organizer — preview

## Inspiration and honest scope

Directly inspired by ComposioHQ's community "Invoice Organizer" Claude skill (reads PDFs/images/scans, extracts vendor/date/amount/invoice-number, renames consistently, exports a CSV). This is the weakest-fitting agent in this plugin family against Kiteworks' actual security/compliance pitch -- it's a general productivity win, not a differentiator -- but it's cheap to build well because nearly everything it needs already exists: `folder-scan` for the walk, `content-extract` for real text out of PDFs/docx/xlsx, `report-export` for the CSV/narrative, and the same two-phase preview/apply shape as `naming-cleanup` and `redactor`.

**Not live-tested against a real Kiteworks tenant's actual receipts in this session** -- unlike several other agents in this family, there was no real invoice/receipt folder available to test against. The field-extraction and OCR mechanics below were built and verified against synthetic test files (a rendered receipt image, an image-only PDF made from it, and a real text-layer PDF) in this session's own sandbox, not against real-world messy data. Say so if asked, and treat the confidence tiers below as genuinely necessary, not decorative -- this is a domain (receipt OCR) with real, well-documented failure rates even in mature commercial tools.

## Collect from the user

1. **Folder scope** (required, per `folder-scan`).
2. **Category scheme** — ask once, don't assume: offer the IRS Schedule C-aligned set below (the most common, well-documented U.S. small-business/freelancer expense taxonomy) as the default, or let the user supply their own category list, or say "don't categorize, just extract fields." Categorization is inherently jurisdiction-specific — never silently assume U.S. tax law applies.
3. **Filename convention** — default to `YYYY-MM-DD_Vendor_Amount.ext` (ISO date first so files sort chronologically, which every bookkeeping source consulted for this agent converges on as the standard). Ask if the user wants the invoice/receipt number instead of or in addition to the amount, or a different order entirely — never assume silently, same rule `naming-cleanup` already follows.
4. **OCR opt-in** — extracting from a real text layer (PDF/docx/xlsx/csv/txt) is cheap and always on. OCR (for photographed receipts and scanned image-only PDFs) is real per-file compute work, same bounded-and-disclosed treatment as `content-extract`'s binary path — mention it will run automatically for image-shaped candidates but is capped like everything else here.

## Schedule C-aligned category set (the default, if the user doesn't supply their own)

Advertising; Car and truck expenses; Commissions and fees; Contract labor; Insurance (other than health); Interest; Legal and professional services; Office expense; Rent or lease; Repairs and maintenance; Supplies; Taxes and licenses; Travel; Meals (flag as 50%-deductible, not 100% — a real, commonly-missed distinction); Utilities; Other expenses. This is a well-documented, standard U.S. Schedule C taxonomy (lines 8–27) — not invented for this agent. If the user's receipts are clearly non-U.S. or they say so, offer a generic neutral set instead (Software/Subscriptions, Office Supplies, Travel, Meals & Entertainment, Utilities, Professional Services, Equipment, Other) rather than forcing Schedule C on them.

## Step 1 — walk and identify candidates

Per `folder-scan`: candidates are any file that could plausibly be an invoice or receipt — don't pre-filter by filename (receipts are rarely named predictably; "IMG_4821.jpg" is a completely normal receipt photo). In scope: `.pdf`, `.docx`, `.xlsx`, `.txt`, `.csv`, and image files (`.jpg`, `.jpeg`, `.png`, `.tiff`, `.bmp`, `.gif`, `.heic`, `.heif`). Flag but exclude from extraction: legacy `.doc`/`.ppt`/`.xls` (no reliable extraction path confirmed in this sandbox for these — flag as "unsupported format, needs manual entry," don't guess) and any file whose `avStatus`/`dlpStatus` (via `get_file_metadata`, same check `document-summarizer` does) isn't clean/allowed — skip and report separately, never extract from a file that hasn't cleared scanning.

## Step 2 — get real text out of each candidate

- Text-based (`.txt`, `.csv`): `read_file_contents` directly, per `content-extract`.
- `.pdf`, `.docx`, `.xlsx`: per `content-extract`'s binary path — `content-extract` now OCRs image-only PDFs and images too (#295), but this agent keeps its own script for HEIC support and its confidence tiers. Use `scripts/ocr_extract.py --root <run> --source <owned-source> --out <reserved-text>` instead of a bare `pdftotext` call for every PDF in scope — it does the same text-layer extraction `content-extract` would, but automatically falls back to OCR rasterization when the text layer is empty (the scanned-receipt-saved-as-PDF case), and reports which path it took (`"method": "text_layer"` vs `"ocr_pdf_rasterized"`) so you can set the confidence tier correctly in Step 4.
- Image files (.jpg/.png/.tiff/.bmp/.gif/.webp) use the same owned-source/output OCR call. HEIC/HEIF uses pillow-heif/Pillow when installed, with a pre-reserved PNG conversion artifact released in finally. A missing decoder returns heic_unsupported; offer a user-converted PNG/JPG or an authorized decoder installation before retrying once. Missing OCR tools are an explicit unavailable result.
- Follow `../scratch-lifecycle/SKILL.md` for destinations, disclosure, grants and cleanup. Reserve text before OCR and keep the original through text-layer/OCR fallback. The script tracks each rasterized page before creation, releases pages/source in finally blocks under the run policy, and returns only metadata to stdout. Read owned text internally, then release it and finalize. A deletion denial never triggers truncation; list residual paths/statuses. The OCR cap is 100 pages per PDF with bounded subprocess timeouts.
- Same per-run cap as `content-extract` (default 30 files; OCR is heavier per-file than a text-layer read, so don't raise this cap casually). Disclose the cap and how many files were actually processed vs. in scope.

## Step 3 — extract fields from the real text

For each file with usable extracted text, pull (reasoning over the extracted text yourself — there's no deterministic field-extraction library for this, unlike the masking step below):

- **Vendor/merchant name**
- **Date** — normalize to `YYYY-MM-DD`. If the date format is ambiguous (e.g. `01/02/2026` could be Jan 2 or Feb 1) and nothing in the text disambiguates it (no month name, no other dated reference), don't guess — flag the file for manual confirmation of the date rather than silently picking one convention. If the document prints no invoice/receipt date at all (e.g. a cloud bill that shows only a billing period, or a hotel receipt that shows only the stay dates), leave the date blank, note the period beside it, and ask the user which date to file it under: a missing date is a question for the user, not a reason to doubt an amount that was read cleanly.
- **Invoice/receipt number**, if present
- **Subtotal, tax/VAT, tip/gratuity** (if itemized separately), and **total amount** — if the total can't be confidently located, leave it blank and flag the file; never fabricate a number.
- **Currency** — the symbol/code actually printed. If none is visible, mark `"currency": "unspecified"` rather than assuming USD or the user's own locale. If a folder mixes currencies, flag it explicitly in the summary — never sum amounts across currencies into one total.
- **Payment method** — cash/credit/debit/check, and a masked card reference if a card number appears in the extracted text. **Before this field goes into any output** (summary card, CSV, chat), run it through `scripts/mask_sensitive_numbers.py` — this deterministically masks any Luhn-valid card number to `•••• <last4>`, any SSN-shaped number to `***-**-<last4>`, and any IBAN (printed in groups or compact, whenever a known country code starts a run of exactly that country's IBAN length, or when such an IBAN is glued straight onto the next field, e.g. `NL91ABNA0417164300BIC`, and its checksum passes) to the country code plus last 4, e.g. `NL•• •••• 4300`. It does not require the IBAN checksum to pass, so an OCR-garbled IBAN is masked too, never printed in full. Run the same script over any IBAN you show from an invoice's bank details, not only the payment-method field. This is the same never-print-the-real-value discipline `term-sweep`'s PII patterns already apply elsewhere in this plugin, reused here because a printed receipt often carries a full or near-full card number even when nobody asked for it. Don't rely on your own judgment to remember not to paste the raw number — run the script.
- **Category** — map vendor/description to the agreed category scheme. Uncertain mappings get "Other"/"Uncategorized," not a confident-looking guess.

## Step 4 — confidence tier per file, stated honestly

- **High** — real text layer (`"method": "text_layer"` from the OCR script, or a docx/xlsx/txt/csv source), vendor and total found cleanly, and the date found cleanly or not printed on the document at all (Step 3).
- **Medium** — OCR-derived (`"method": "ocr_image"` or `"ocr_pdf_rasterized"`), but vendor and total (and the date, if one is printed) were still found with reasonable confidence. Label these "OCR-derived — verify against the original before relying on it," every time, not just once in a caveat paragraph.
- **Low / needs manual review** — any of: the OCR script reported a near-empty-result warning, the total couldn't be confidently located, the date is ambiguous (two plausible readings, per Step 3) and nothing in the text settles it, the receipt appears handwritten, the extracted text is a foreign language you're not confident parsing amounts/dates in, or the file is a legacy `doc`/`ppt`/`xls` format. Never include a Low-confidence file's numbers in a proposed rename or category total — surface it with what little was found (if anything) and require explicit manual entry/confirmation, never a bulk "looks right" inclusion. A date that is simply not printed is not a Low trigger: tier the file on its vendor and total, and list the date as an open question.

## Step 5 — a cheap, real duplicate check (not a replacement for `duplicate-finder`)

Within this run's own results, flag any two files with the same vendor + same date + same total as "possible duplicate receipt" (e.g. a receipt photographed twice, or a paper receipt plus its emailed PDF copy) — a real, useful signal that falls out of the fields already extracted, at no extra cost. Flag two files the same way when the folder listing or file metadata shows the same content fingerprint (a byte-identical copy such as `receipt.pdf` and `receipt (1).pdf`). This is deliberately not the same thing as `duplicate-finder`'s content-fingerprint matching (two different photos of the same paper receipt won't fingerprint-match, since they're different image bytes) — recommend running `duplicate-finder` on the same folder too if the user wants an actual byte-level duplicate check; don't claim this catches everything it would.

## Step 6 — propose renames and present the result

Per the agreed convention (default `YYYY-MM-DD_Vendor_Amount.ext`), propose a new filename for every High/Medium-confidence file (a file with no printed date gets its rename once the user has answered the date question). Sanitize vendor names for filesystem safety (strip `/\:*?"<>|`, collapse whitespace to underscores).

Summary card: counts (scanned / candidates / skipped-AV-DLP / skipped-unsupported-format / High / Medium / Low), a sample of extracted rows (file, vendor, date, total, currency, category, confidence), per-currency totals, possible-duplicate flags, currency-mix warning if applicable, extraction-cap disclosure, coverage note, and the standard disclaimer plus the tax-specific one below.

**Currency totals — fixed rules, so the same folder always gives the same figures:**

- One total per printed currency. Never add currencies together and never convert them.
- Every High or Medium file's total goes into its currency's total. A missing date does not change that: an amount read cleanly from the document's own text counts, and the missing date is reported separately as a question for the user. Never report a currency total of 0.00 while a High or Medium amount in that currency exists.
- Low-confidence amounts (Step 4) and `unspecified`-currency amounts stay out of the totals. List them separately under the totals, with what was read, as "not in the totals — needs your confirmation".
- Each group of possible duplicates (Step 5) counts once: the first file by filename is in the total, the others are listed as duplicates and left out of it. You may also give the figure with the duplicates included, clearly labelled, but the headline total counts each receipt once.

**Tax-specific disclaimer, every time, not just once:** *"These are best-effort extracted/OCR'd values, not verified accounting data. Reconcile totals against your bank or card statement before using this for tax filing or bookkeeping. Currency was read from what's printed on each receipt, not verified against live exchange rates."*

End by actively offering apply for the confirmed High + Medium set: *"Want me to rename these N files and export the categorized CSV? The M Low-confidence files need your input first — want to review those now?"* Never bundle Low-confidence files into a "looks good, proceeding" default.

## Save a proposal separately

This preview has no Kiteworks write access and cannot save a report itself. Return the complete assessment ledger to the main conversation. When the user requests a saved proposal, the main conversation collects the report preflight and calls this plugin's report-only agent. Saving a proposal does not run apply or authorize source changes.

## Evidence handoff for reports

Retain every enumerated object and every configured check in the version 2
assessment ledger, including failed/skipped checks and unvisited scope.
Use profile `invoices`. Explain purpose, conclusion, implications and
proposed actions. Return that record to the main conversation along with
the preview. The caller invokes `invoice-organizer-report` to save the authorized
proposal. It must not substitute an apply run for a reporting request.
