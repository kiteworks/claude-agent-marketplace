---
name: sensitive-content-scanner
description: >
  Use when the user wants to sweep a Kiteworks folder for sensitive
  terms — trigger phrases include "scan for sensitive content in X,"
  "find files mentioning [term]," or "sensitive content scan." Scans
  and, on confirmation, writes a CSV + txt/pdf report. Single-phase: no
  separate "apply" step to ask for.
metadata:
  version: "1.3.0"
---

Delegate to the `sensitive-content-scanner` subagent. Read `../term-sweep/SKILL.md` first — it has the confirmed caveat about `content_contains` reliability; do not skip it.

# Sensitive Content Scanner

## Why this is one phase, not two

This agent never touches flagged files — its only write action is a CSV + txt/pdf report. A separate apply skill didn't protect against anything real, so scanning and (on confirmation) saving are now one flow, one agent.

## Collect from the user

A folder scope (required) and a term list (required — never assume a default list; sensitivity vocabulary is organization-specific, e.g. "confidential", "SSN", "ITAR", a client name).

## Sweep

Always run the name/path match per `term-sweep` — fast, one call, always on.

Content matching is a separate, opt-in "deep scan": ask the user whether they want it (it's real per-file work — a download and parse per candidate file, per `../content-extract/SKILL.md`), tell them roughly how many files are in scope, and only run it if they confirm. Respect `content-extract`'s per-run cap and disclose how many files were actually checked vs. in scope.

## Built-in PII/secret pattern presets — all run by default

This is what makes this agent an actual *sensitive-content* scanner rather than just a keyword search the user has to fully configure themselves. Whenever the content deep-scan runs, also run `../term-sweep/SKILL.md`'s built-in pattern presets (`scripts/pii_patterns.py`) against the same extracted text, alongside whatever custom terms the user gave. **Every built-in category runs by default** — mention once, briefly, that this happens and that it can be turned off if the user only wants their own term list; don't ask them to pick categories up front or single out any one category (e.g. a country-specific one) as needing special permission.

**Keep the narration terse.** Don't preamble-list every category before running (per `term-sweep`'s presentation rule). In the summary card, name only the categories that actually got a hit, plus a one-line total count of categories checked. The full per-category breakdown — including zero-hit categories — goes into the exported report, not the chat turn. If the user asks what's checked, or wants to scan for a narrower subset (e.g. "just financial patterns," or by region), offer `term-sweep`'s tag-based `--categories` selector (`region:<value>`, `type:<value>`, exact category names, or `all`) — but only when they ask or it's clearly useful, not as a standing question before every scan.

Each category also carries a `context_confirmed` count alongside its raw `valid` count — whether a relevant keyword (e.g. "BSN," "SSN," "IBAN," "card number") appeared within 60 characters of the match. A shape/checksum-valid match with no nearby keyword still counts as a hit (real PII is often unlabeled), but report both numbers so the user can see how many hits also have contextual support, not just checksum validity.

## Custom regex — for anything the built-in categories don't cover

If the user has their own pattern in mind (an internal ID shape, a partner account number, anything with a defined structure), ask for the regex, a label, and optionally context keywords, and run it through `term-sweep`'s custom regex mode (`scripts/pii_patterns.py`'s second, optional argument) alongside whatever else is running. A bad regex or a pathological one is reported as a per-pattern error, not a crash — surface that plainly if it happens rather than silently dropping the pattern.

## Present the result, then actively offer to save it

Summary card: summary, term list used, name-match hits, whether a content deep-scan ran and its hits if so (or "not run — ask to include a content scan" if the user didn't opt in), how many built-in pattern categories were checked with which ones (if any) were flagged (name the hits, not the whole list), coverage, warnings.

**Do not stop there and wait.** End by explicitly asking, e.g.: *"Want me to save this as a CSV + PDF report to `My Folder/Agents/Sensitive Content Scanner/`?"*

## If confirmed, write the report

Read `../report-export/SKILL.md`. Default agent name: "Sensitive Content Scanner". Never touches flagged files, never prints matched text or matched pattern values (per `term-sweep`), and the report must repeat the content-search reliability caveat.

Write CSV (name, path, term or pattern-category matched, match type name/custom-content/built-in-pattern, link) and txt/pdf narrative including the caveat verbatim. State every built-in category that was checked, with both its `valid` and `context_confirmed` counts, even for the ones with zero hits — a clean result is itself useful information in the saved report, even though the chat summary only names the flagged ones.
