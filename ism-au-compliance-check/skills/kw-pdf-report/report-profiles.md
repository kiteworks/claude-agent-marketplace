# Report profiles

Use the assessment contract in SKILL.md for all new PDF, CSV and TXT reports.
Every profile requires a purpose, bounded conclusion, implications, decisions,
limitations and complete per-object check coverage. The profile changes the
content and evidence basis, never the shared brand or the meaning of a status.

Fill `profile_details` with the basis below, explicitly stating unknowns.
Do not invent a fact merely to fill a field. Findings reference actual checked
objects; missing evidence belongs in coverage/limitations and evidence requests.

Use each object's `facts` mapping for measured or observed family-specific
fields with units, reference event and provenance in the labels or values.
For storage, use integer `size_bytes` and `type: file`; the summary derives
logical file-byte totals from those rows, excluding folder aggregates and
reporting measured versus listed file counts. Never put unsupported totals only
in free-text conclusions. Use `partial` with inspected extent and reason when
extraction is truncated; valid observations from that portion remain linkable.

| Profile | Agents | Required basis and interpretation |
| --- | --- | --- |
| privacy | GDPR, CCPA, LGPD, DPDPA, VN-PDPL, ISO 27701 | Framework/version/jurisdiction; selected data categories; applicable retention policy and reference event; missing purpose/authorization context. Discuss potential effects on people. Pattern matches do not establish personal-data status or unlawful processing. No breach, DPIA, RoPA or compliance score inferred from a file scan. |
| hipaa | HIPAA | Applicable entity/context unknowns; potential ePHI vs validated status; sharing visibility; documentation evidence. Six-year required-documentation retention is a minimum, not a maximum file age. Do not run an old-file-as-violation check. |
| security | ISO 27001, SOC 2, FedRAMP, NIST CSF, CIS Controls, NIST 800-53, ISM AU, NZISM, NIS2 | Framework/version; selected controls and actual checks; significant control areas not assessed. Sharing-only scans cannot claim content inspection. No certification, SOC opinion, authorization or whole-framework readiness percentage. |
| cui | CMMC | Candidate markings; classification validation; CUI owner/context unknowns. Keywords do not establish CUI classification or certification readiness. |
| pci | PCI DSS | Framework version; possible cardholder-data categories; masked evidence; applicable retention policy; validation queue. No raw values, attestation or prohibited-storage conclusion from a term alone. |
| dora | DORA | Selected documentation; date field used; actual last-review evidence or explicit unknown; missing resilience/register/contract evidence. Creation age is not elapsed time since review. |
| export | ITAR, EAR | Framework/version; candidate classification markers; actual sharing visibility; unknown recipient/jurisdiction/authorization. No ECCN/USML/licensing/nationality inference from keywords or a generic location field. |
| ai | EU AI Act, ISO 42001, NIST AI RMF | Framework/version; document candidates; known system/purpose/owner or explicit unknowns; missing governance evidence. Document screening is not AI-system risk classification, model evaluation or conformity assessment. |
| accessibility | WCAG, Section 508 | Selected standard/version/target; formats and actual structural tests; barriers and affected-user implications; manual keyboard/screen-reader/read-order/alt-quality review still required. Tags present does not mean accessible. Do not claim full conformance. |
| sensitive-content | Sensitive Content Scanner | Terms/categories and method/version; pattern validity vs contextual confidence; content/OCR coverage. Count unique files separately from matches; never print matched values or secrets. |
| sharing | Sharing Auditor | Share origins; inherited object counts; known membership and unknowns; scope visibility. Keep the origin register distinct from the complete object ledger. Shared does not mean external/public/unauthorized. |
| retention | Retention Sweeper | Policy/version/threshold and reference event; age cohorts; purpose and hold status unknown when unavailable. Candidate review is not authority to delete. |
| storage | Storage Visualizer | Measured size units and scope; aggregation/versions limitations; capacity concentrations. Distinguish logical size, estimated opportunity and actually freed space; no unsupported cost savings. |
| duplicates | Duplicate Finder | Matching basis, group/keeper rationale, unknown fingerprints, proposed destination. Proposal and receipt differ; moved files have not freed storage. Inventory includes all enumerated objects, not just duplicate candidates. |
| contracts | Contract Radar | Search terms/purpose, candidate confidence, extraction coverage, owner-review queue. Discovery is not verified obligations/renewals; modified dates are not renewal dates. |
| invoices | Invoice Organizer | Extraction/OCR provenance; missing fields; duplicates; totals separately by currency; organization rule. Separate proposal from completed renames/moves; no financial/tax validation claim. |
| activity | Activity Digest | Exact interval/timezone; created vs modified file populations; scope and comparable prior snapshot if available. File metadata is not an access/download/deletion event audit log. Prefer brief layout. |
| naming | Naming Cleanup | Naming convention, real scope, before/after proposal, collisions and unresolved choices. Receipt includes actual outcomes and failures. |
| offboarding | Offboarding Content Finder | Identity-matching basis, searched scope, candidate owners and handover destination. Creator match is not current ownership; moving content is not access revocation or ownership transfer. |
| inbox | Inbox Triage | Source inbox/uploads folder, real destination taxonomy, filename-only vs content-aware classification and uncertainty. These are files/folders, not email/messages/attachments. |
| redaction | Redactor | Source-to-derivative identity, categories/method, supported formats, verification status and excluded content. Successful copy creation is not proof of irreversible removal. Never repeat removed values in the report. |

## Family structure

| Family | Layout and size | Notes |
| --- | --- | --- |
| Compliance (privacy, hipaa, security, ...) | full, 5-7 pages for a small scope | `<category>_count` fact keys where counts are checked |
| sensitive-content | full, 4-6 pages | `<category>_count` fact keys |
| storage | brief, 2-3 pages | Must contain: total size card text, file count and measured coverage, a shared / not-shared measured breakdown, largest folders, top files and file types, and one recommendation. No capacity alarm when the footprint is immaterial. Needs no fact keys (uses `size_bytes`). |
| Other operational families | brief by default | |

Suggested canonical `fact_keys`: privacy, pci and sensitive-content use
`<category>_count`, for example `bsn_count`, `iban_count`, `ssn_count`,
`card_count`. A checked zero must be recorded as 0.

## Proposals and receipts

Use `document_kind: proposal` for proposed changes and `receipt` for outcomes.
Report export does not authorize a move, rename or redaction. Completed actions
require recorded verification and completion timestamp. An owner or target that
is not agreed stays unassigned/not agreed. Include approval state and dependencies
in the action basis; retain before/after object references in profile details or
the source field of inventory objects. The execution evidence must establish the
reported outcome; never turn a recommendation into a completed action.

Document Summarizer remains TXT/DOCX; Folder Expiry Audit and Intake Form Builder
do not gain a PDF workflow merely because other reports use this contract.

## Writing and review

The executive summary answers four questions: what was reviewed, what matters,
what decision is needed, and what could not be established. Use a conclusion of
2-4 sentences and 3-5 key points only when warranted. Keep algorithm names,
validation counts, signal letters, checksums and extraction commands out of
executive prose ("possible national identifiers", not "BSN-shaped, 11-test
valid"). Group repeated file observations into themes: one finding per theme,
never one per file. Run `branded_pdf.py metrics --json-file ...` before writing
prose and quote its `total_size` / `size_by_object`; never write raw byte counts
or KiB/MiB, and heed the build `warnings`. Credit a finding only to checks that
matched. An absent sharing flag is "Kiteworks reported no sharing flag", never
"not exposed". Use one timezone for all reports of a run.

Use plain-language themes, connected explanations and concise bullets. The main
finding must answer what was observed, why it matters, what remains uncertain
and what should happen next. Priorities need reasons; confidence is not severity.
No invented legal conclusions, affected-person counts, monetary impact, owners,
dates, management responses or comparisons. Keep internal check IDs, detailed
OCR/skips and full filenames in the appendix when possible. Show material
coverage gaps in the executive summary. Review the PDF at normal reading size
and validate the evidence references before upload.
