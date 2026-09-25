---
name: term-sweep
description: >
  Shared internal reference skill, not invoked by users directly.
  sensitive-content-scanner and contract-radar both read this file for
  the standard way to sweep a Kiteworks folder for name/content term
  matches. Read this before writing or modifying either of those skills.
metadata:
  version: "0.6.0"
---

# term-sweep — shared keyword/content sweep helper

Read `../folder-scan/SKILL.md` first for scope, walk, and link rules.

## Two match modes

1. **Name/path match** — a term matches an item when it appears in the item's **full `path`**, folder names included, not only in its own file name. Run it in two parts and union the hits:
   - **Client-side over the walk (authoritative).** Do the bounded `get_folder_children` walk per `../folder-scan/SKILL.md` and match each term, case-insensitively, against the `path` of every record it returns, files and folders alike. A file inside `05 Engineering/Export Controlled/` matches the term "export controlled" through its folder even when its own name says nothing. Report for each hit whether the term matched the **file name** or a **folder name** in its path, so a reader can see why a neutrally named file was flagged.
   - **`search_files` with `parent_folder_id` + `path_contains: "<term>"` (supplementary).** Recursive into subfolders, but confirmed live 2026-09-24 (#272) that it matches the **file's own name only, never its parent folders**: `path_contains="export controlled"` returned 0 hits for 10 files sitting in a folder of that name. Use it as a cheap extra, never as the whole name/path match, and never describe it as matching folder names. It still helps when the walk hits its bounds, since it can reach files the walk did not.
   This is the default, always-on match mode. The walk is metadata-only, so it costs one call per folder level and no per-file work.

2. **Content match — real extraction, not server-side search.** `content_contains` returned no matches in the recorded deployment tests (tested deliberately across a 20-minute-old plain-text file with the exact term in it, multiple real PDFs from 2014 searched for both an ultra-common word and a domain word, and both the `search`/`search_files` tools — zero results every time; not an indexing-latency issue). Do not call `content_contains` at all. Instead, for genuine content-based matching, read `../content-extract/SKILL.md` and use it: for each candidate file (bounded per that skill's cap), extract its real text and check for the term(s) client-side yourself. This actually works, but it's real per-file work (a download and parse for binary formats), so treat it as an **opt-in "deep scan"**, not part of the default sweep — ask the user before running it, tell them roughly how many files are in scope, and respect `content-extract`'s cap and disclosure rules.

## Term lists

Collect the term list from the user (e.g. sensitive-content-scanner: "confidential", "SSN", "ITAR", client names; contract-radar: "agreement", "MSA", "SOW", "NDA"). Never invent a default list without asking — sensitivity/contract vocabulary is organization-specific.

## Built-in pattern presets — a third match mode, alongside name/path and custom-term content matching

Asking the user to type "SSN" as a term only catches a file that spells out the word "SSN" — it does nothing for a file that contains an actual SSN-*shaped* number. A real sensitive-content scanner should recognize common PII/secret *shapes*, not just the words people use to describe them.

Whenever a content deep-scan runs, also run `scripts/pii_patterns.py <extracted-text-file>` against the same extracted text (`--help` prints the full CLI). **The general built-in categories run by default** — there is no region-based opt-in gate: `ssn_shaped`, `bsn_shaped` (Dutch elfproef/11-test), `credit_card_luhn_valid` (Luhn), `iban_checksum_valid` (mod-97), `aws_access_key` (AKIA prefix). Each enabled category reports two counts: `valid` (checksum/shape-valid matches) and `context_confirmed` (the subset also near a relevant keyword within 60 characters, e.g. "SSN", "IBAN", "social security" — a second, independent signal on top of checksum validity, since checksums alone still have a non-trivial chance-pass rate). Never print the matched values themselves, only categories and counts.

**Framework-gated presets (#274, #291, #292).** Some shapes are a finding only under particular frameworks (personal data under a privacy framework, a plaintext secret under a security framework, a patient or provider identifier under HIPAA), so they run only when a `*-compliance-check` skill passes `--framework=<slug>` (the slug its own skill file names), or when the user selects them explicitly by key/region/type. Otherwise they come back as `skipped` with the frameworks that enable them:

| Category | Check | Enabled by `--framework=` |
|---|---|---|
| `aadhaar_verhoeff_valid` | 12 digits, first digit 2-9, Verhoeff check digit | `dpdpa` |
| `cpf_mod11_valid` | Brazil CPF, two mod-11 check digits | `lgpd` |
| `cnpj_mod11_valid` | Brazil CNPJ, two mod-11 check digits (numeric, or alphanumeric in its punctuated form) | `lgpd` |
| `vn_cccd_shaped` | 12 digits with a documented Vietnamese province-code prefix (no check digit exists, so lean on `context_confirmed`) | `vn-pdpl` |
| `email_address` | Email address shape | `gdpr`, `ccpa`, `lgpd`, `dpdpa`, `vn-pdpl`, `iso27701` |
| `geolocation_latlon` | Decimal lat/lon pair, 3+ decimals on both, in range (CCPA "precise geolocation"). Matches the bare `52.370, 4.895` form (which also covers adjacent lat,lon CSV columns) and labelled forms, latitude first: key/value (`lat: 52.370, lon: 4.895`, `latitude=52.370 longitude=4.895`, query strings) and JSON keys (`"lat": 52.370, "lng": 4.895`, values may be quoted). Each pair counts once. Lat and lon in non-adjacent CSV columns are not matched. Short labels such as `lat`/`lng` are not context keywords on their own | `ccpa` |
| `plaintext_credential` | A `password`/`passwd`/`pwd`/`secret`/`token`/`api_key` name (also prefixed, e.g. `DB_PASSWORD`, `client_secret`, `x-api-key`, or with a key suffix, e.g. `secret_key`, `AWS_SECRET_ACCESS_KEY`) followed by `=`, `:` or `:=` and a non-empty value that ends the line or field. Placeholder values do not count: `changeme`, `<redacted>`, `${VAR}`, `$VAR`, `{{ var }}`, `***`, `xxx`, `TODO`, `none`, empty or `""`. Prose such as `Password: must be at least 12 characters` does not match, and neither does an unquoted value that is a plain word, an identifier, a code reference (`config.api_key`, `getpass()`), a path or a short number. The name alone never confirms context: `context_confirmed` needs a keyword such as `username`, `login` or `bind` around it. Counts only, never the value | `soc2`, `cis-controls`, `iso27001`, `nist-800-53`, `sensitive-content-scanner` |
| `npi_luhn_valid` | US National Provider Identifier: 10 digits starting with 1 or 2, Luhn check digit computed with the `80840` prefix. Counted only with an NPI keyword (`NPI`, `National Provider`, as a whole word) within 60 characters, since one in ten 10-digit numbers passes the check | `hipaa` |
| `medical_record_number` | A 5-12 digit number (optionally with a 1-3 letter prefix, e.g. `KV-0048213`) directly after its label: `MRN`, `MRN #:`, `medical record (number)`, `Medical Record Number (MRN):`, `patient ID`. No checksum exists, so an unlabelled number never counts. `context_confirmed` needs a health-care word (`patient`, `hospital`, `diagnosis`, ...) around the label, not the label itself | `hipaa` |
| `health_plan_member_id` | A 6-20 character ID containing a digit, directly after a `health plan`/`health insurance`/`insurance (policy)`/`member`/`subscriber`/`beneficiary`/`Medicare`/`Medicaid` `ID`/`number` label (a bare `policy` label does not count; an ISO date is not an ID). No checksum exists, so an unlabelled value never counts. `context_confirmed` works as for `medical_record_number` | `hipaa` |

An unknown `--framework` slug is a hard error that names the valid ones, never a silent no-op.

**How results are presented matters more than which categories ran (2026-07-15).** An earlier version of this skill made `ssn_shaped`/`bsn_shaped` off-by-default because naming a country-specific category (e.g. "Dutch BSN") prominently in the chat narration, regardless of relevance, read as noisy and presumptuous. Direct user feedback: that overcorrected — the categories themselves should keep running by default (a scanner that quietly does less isn't better), the actual fix belongs in *how the result is narrated*:

- **Don't preamble-list every category before running.** Just run the deep scan; there's no need to announce "I'll check for SSN, BSN, credit card, IBAN, AWS key" up front.
- **In chat, name only the categories that got a hit**, plus a one-line total (e.g. "Checked 5 built-in patterns, 1 flagged: IBAN"). Count only the categories that ran, not the skipped ones. Zero-hit categories are not narrated by name in chat.
- **The full per-category breakdown — including every zero-hit category — always goes into the exported CSV/txt/pdf report**, per `report-export`'s "a clean result is real information" rule. That's the right place for the complete list, not the conversation.
- If the user asks what's being checked, or wants to narrow scope, answer plainly and offer the selector below — but don't volunteer the full list unprompted every run.

## Tag-based category selector, built to scale to dozens of categories

Every built-in category carries two selector tags in `pii_patterns.py`'s `CATEGORY_SPECS`: `region` (e.g. `"US"`, `"NL"`, or `None` if not tied to one country) and `type` (e.g. `"national_id"`, `"financial"`, `"credential"`). This is the mechanism for narrowing scope as the built-in library grows — expected to go well past 5 categories over time, and a flat "type one category name per flag" interface doesn't scale to dozens. Invoke `scripts/pii_patterns.py`'s `--categories` flag with a comma-separated selector, where each item is one of:

- an exact category key, e.g. `bsn_shaped`
- `region:<value>`, e.g. `region:US` — every category tagged that region
- `type:<value>`, e.g. `type:financial` — every category tagged that type

Items are unioned, e.g. `--categories=region:US,region:NL,aws_access_key`. Omit the flag (or pass `--categories=all`) to run every general built-in category — the default, always. `--framework=<slug>` adds that framework's gated presets on top of whatever `--categories` selected. An unrecognized category key, region, or type is a hard error from the script (exit 1, names the valid options), not a silent no-op.

Only offer this narrowing to the user proactively when it's clearly useful (e.g. they ask to scan for "just financial patterns," or the scan is large and they want to speed it up) — don't ask them to pick categories before every run; running everything by default is the right behavior for most scans.

## Custom regex mode (2026-07-13) — a further match mode, for patterns the built-in presets don't cover

The built-in categories are deliberately narrow and checksum-validated. For anything else with a defined shape — an internal employee ID like `EMP-\d{6}`, a project code, a partner-specific account number — the user can supply their own regex(es) and have them evaluated the same deterministic way, rather than the agent trying to eyeball extracted text for the pattern itself (which would mean reading raw content into its own reasoning, defeating the point of keeping it out of the conversation).

To use it: write the user's pattern(s) to a scratch JSON file as an array of `{"label": "...", "regex": "...", "context_keywords": [...]}` objects (`context_keywords` optional), then run `scripts/pii_patterns.py <extracted-text-file> <custom-patterns.json>`. The result gains a `"custom"` key: `{label: {"valid": N, "context_confirmed": N, "error": null|"..."}}`.

Safety properties, all live-verified:

- **A bad regex never crashes the run** — a `re.compile` failure is caught and reported as `"error": "invalid regex: ..."` for that pattern only, with `valid`/`context_confirmed` at 0.
- **A pathological regex can't hang the scan** — each pattern gets a 3-second wall-clock guard (`SIGALRM`-based); a catastrophically-backtracking pattern (e.g. `(a+)+$` against a long run of the wrong character) times out with a clear `"error"` instead of hanging.
- **Input is length-capped** (2,000,000 characters) before evaluation, with a `"note"` flag if truncation happened.
- Same privacy rule as everything else here: never print the matched value, only the count.

Ask the user for their regex and an optional label/context keywords the same way you'd ask for a term list — don't invent one.

## Running the scripts

Both scripts live in `scripts/` alongside this file and are invoked via `Bash` (`Read`/`Bash`/`Skill` tools, per `content-extract`'s verified parser execution path) against a scratch text file containing the extracted content — never paste extracted content into the conversation to run these checks manually.

## Connector tools this skill uses

- Calls: `get_folder_children`, `search_files`.
- Named only: `search`.

The Calls tools are granted to every agent that reads this skill: the
authoritative walk and the supplementary file-name match. `search` is named
only as a tool that returned no `content_contains` hits; this skill never
calls it. A content deep scan goes through `content-extract`, whose own
contract lists its tools.
