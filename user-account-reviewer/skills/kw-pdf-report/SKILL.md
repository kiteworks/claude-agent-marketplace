---
name: kw-pdf-report
description: >
  Shared report builder for executive assessments, proposals and completion
  receipts. Use the validated assessment record to generate consistent PDF,
  text and complete inventory CSV deliverables.
metadata:
  version: "1.0.0"
---

# Executive reports

Use the version 2 assessment contract for new reports. Read
[report-profiles.md](report-profiles.md) for the report family's evidence rules.
Start from the complete, runnable [example](examples/assessment.json); replace
its illustrative facts with observed evidence. Never copy example conclusions.

Write for the decision maker. The executive summary answers four questions:
what was reviewed, what matters, what decision is needed, and what could not
be established. Use a conclusion of 2-4 sentences and 3-5 key points only
when warranted; use concise paragraphs and bullets. Keep filenames, check details and technical evidence
in the appendix. "Signals" and internal A–E detector labels are implementation
terms, not legal findings. Keep algorithm names, validation counts, signal
letters, checksums and extraction commands out of executive prose (write
"possible national identifiers", not "BSN-shaped, 11-test valid"). Use the applicable framework's terminology and
qualify automated observations as candidates requiring validation.

Writing rules:

- Group repeated file observations into themes: one finding per theme, never
  one per file; name at most 3 `example_object_ids`.
- Run `python scripts/branded_pdf.py metrics --json-file <spec.json>` before
  writing prose and quote its `total_size` / `size_by_object` values. Never
  write raw byte counts or KiB/MiB in prose; heed the `warnings` it prints.
- Credit a finding only to the checks that actually matched.
- An absent sharing flag is "Kiteworks reported no sharing flag", never "not
  exposed".
- Use the same timezone for all reports of one run.

## Authorized outputs and destination

Saving a PDF requires `upload_file_from_path` on the resolved connector.
When `connector-probe` reports it missing, use its approved plain-text
fallback wording, honor selected formats, and never relay a binary as text.

Read ../report-export/SKILL.md and honor the existing report preflight. Save
only authorized formats and destination; do not silently add CSV to a PDF-only
request. Report creation does not authorize moving, renaming, deleting or
changing source objects. A proposal describes possible work; a receipt states
verified results of separately authorized work.

**Inventory placement** is set in the record as `report_mode.inventory`:

- `companion` when CSV and PDF are both authorized: the PDF is the executive
  report and the file-by-file list goes to the CSV.
- `compact` (complete one-row-per-object table) when only PDF is authorized.
- `omitted_by_request` only when the user explicitly asked to leave the
  inventory out.
- `embedded` only for the legacy detailed appendix (legacy records).

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

## Write the record, then build

**Use the Write tool; never write .py helper files** or compose report text
through shell heredocs, printf or Python one-liners. Stage UTF-8 spec.json in
the user-private, connector-readable <base>/_kiteworks-report/ directory.

1. Populate spec.json from examples/assessment.json. Top-level fields are
   agent_name, report_title, scan_date, scope_caveat, assessment and optional
   presentation. The scan date is the date in run.assessed_at. The published
   legal footer is fixed; the scope caveat states this run's actual limits.
2. For authorized CSV/TXT outputs, derive them from the same record first:
   python scripts/branded_pdf.py export --json-file <base>/_kiteworks-report/spec.json --format csv --out <base>/_kiteworks-report/inventory.csv
   Use --format txt for a narrative text version. Export keeps the spec.
3. Build the PDF with
   python scripts/branded_pdf.py build --json-file <base>/_kiteworks-report/spec.json --out <base>/_kiteworks-report/report.pdf
   Add --keep-spec only if another authorized output still needs the record.
   With a saved companion CSV add
   `--delivery <base>/_kiteworks-report/delivery.json` (JSON: name, location,
   optional url, row_count, byte_size, delivery_status; it requires
   `report_mode.inventory` = `companion`, `row_count` must equal the inventory
   size, `url` must be https). The build output then lists `companion`.
   Successful build normally removes the staged spec. On validation failure
   it exits 2, keeps the record, and names the problem; correct the evidence
   or shape without fabricating facts.
4. Upload binary PDF using upload_file_from_path and verify the response size.
   Never relay binary data through base64 text. Report the saved names, sizes,
   links and any verification limits. Follow report-export for text-only
   connectors and scratch-lifecycle for optional download-back verification.
5. After the intended deliverables are safely saved, use
   python scripts/branded_pdf.py cleanup --dir <base>/_kiteworks-report
   Report kept paths. Preserve intended deliverables; scratch cleanup is not
   permission to delete source files or saved reports.

If the host has no Write tool, spec-append is the fallback for base64 chunks
of a spec, followed by build --spec. It is not the primary authoring path.

## Assessment contract

assessment.schema_version is 2. New reports MUST include `report_mode`,
`cover`, canonical priorities and a `kind` on every check. Records without
`report_mode` render in the legacy layout and are not for new reports.
Required fields:

- report_mode: `{"inventory": ...}` with one of `companion`, `compact`,
  `omitted_by_request`, `embedded` (rule under Inventory placement above;
  `companion` also needs inventory_companion).
- cover: `title`, `scope_label`, optional `organization_label`. `scope_label`
  is the verbatim last path segments of the scanned scope, for example
  `DEMO Kestrelvane Group / 03 HR`; never translate or expand it ("03 HR" is
  not "Human Resources"). Set `organization_label` only when the user supplied
  it.
- profile: one ID from report-profiles.md; document_kind is assessment,
  proposal or receipt (default assessment).
- run: id and version; operator; scope; assessed_at and generated_at ISO
  timestamps with timezones; review_status; enumeration_complete boolean;
  unvisited_scope list (nonempty only when enumeration is incomplete).
  Record real identities and times. Say unavailable if identity was not
  exposed. Never imply a human reviewed an automated run. For automated runs
  set review_status to exactly:
  `Automated assessment · not reviewed by a person · findings need owner validation`
- executive: purpose and conclusion paragraphs; key_points and decisions
  nonempty bullet lists. If no decision is needed, explicitly say so and why.
  Explain business implications without turning scanner limits into claims
  that the organization lacks a policy or control.
- checks: records with unique id, plain-language label and actual method, plus
  `kind` (`content` or `metadata`, required in new mode) and optional
  `fact_keys`: numeric keys that every object with status `checked` for that
  check must carry in `facts` (for example `iban_count`). Record a checked
  zero as 0, never omit it.
- inventory: every enumerated object with unique id, name, type, optional
  source location/version and http(s) url. Each object has a checks list
  recording every configured check. Each check has id and status:
  checked with method; partial with method describing the inspected extent
  and reason explaining the remainder; skipped, failed, not_attempted or not_applicable with
  reason. "Checked" means the stated method completed, not that the object
  passed a compliance standard. Do not substitute the entire folder for a
  sampled population.
  Optional size_bytes is a nonnegative integer measurement; use type: file
  for file-size totals. Optional facts is a label-to-scalar map for actual
  family evidence (version, timestamp with meaning, duplicate group,
  proposed name/destination, currency/amount, etc.). Label units and provenance;
  use explicit unknown text where needed. These facts survive all exports.
  Storage totals derive only from measured file rows; folder aggregates are
  excluded to avoid double counting and missing sizes remain unknown.
- findings: records with id, title, observation, impact, confidence, priority,
  priority_reason, recommendation, object_ids and check_ids. In new mode priority is one of
  `critical`, `high`, `medium`, `low`, `info`. Optional
  `example_object_ids` (1-3 unique IDs from object_ids) names the examples the
  PDF shows. Optional
  criterion identifies the applicable control/article and interpretation.
  References must exist and refer to checked evidence, including only the
  inspected portion of a partial check. Unreadable content is
  a coverage limitation, not a content finding. Explain priority; never
  invent regulatory severity.
- actions: id, action, status (proposed/approved/completed/skipped/failed),
  finding_ids or a stated basis. Optional owner and target; absent values
  are printed as unassigned/not agreed. Completed actions require
  verification and completed_at. A proposal cannot claim executed actions.
- limitations: nonempty list stating actual coverage and evidence limits.
- profile_details: nonempty label-to-text mapping containing the applicable
  family-specific basis, parameters and unknowns in report-profiles.md.
- references: optional list of framework/policy sources and versions.

IDs are stable simple letters, digits, hyphens or underscores, at most 80
characters. Every finding refers back to its object and check; do not invent
duplicates to make the counts look larger. Counts are derived from the ledger.

Optional inventory_companion has authorized: true, name, location, report_id
and version. Its report_id/version must match run. This switches the PDF to
a companion reference while retaining linked evidence IDs; the inventory CSV
still contains the complete enumerated population. The renderer cannot verify
a remote upload: the agent must verify the saved companion before building.

## Layout and supported text

The full report has a cover, executive summary, linked contents, assessment
details, findings with implications, action plan, limitations, methodology and
complete inventory. Bookmarks and finding-to-evidence links support navigation.
The brief presentation keeps the same evidence and legal disclosures.

Optional presentation fields: layout (full or brief), page_size (A4 or
Letter), language (e.g. en-US), classification (e.g. Confidential).
Do not claim a classification that the user or policy did not establish.

Bundled Noto Sans preserves supported Latin, Greek and Cyrillic text. Unsupported
glyphs and right-to-left scripts fail explicitly rather than silently changing
filenames or evidence. If encountered, explain the limitation and use an
authorized UTF-8 TXT/CSV alternative; never silently transliterate identifiers.
Fonts are bundled with their license and attribution.

Language metadata, bookmarks and links improve access, but this renderer does
not yet produce a fully tagged PDF or claim PDF/UA conformance. A formal
accessible-PDF requirement needs a tagged renderer and assistive-technology
validation. Offer an authorized text alternative in the meantime.

## Compatibility

Legacy sections/metadata inputs and standard_metadata() remain supported for
existing integrations. Do not combine them with assessment. New report agents
must use the assessment record so coverage, findings and inventory stay aligned.
