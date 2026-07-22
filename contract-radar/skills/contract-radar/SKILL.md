---
name: contract-radar
description: >
  Use when the user wants to find contracts, agreements, or renewal-related
  documents in Kiteworks — trigger phrases include "find our contracts in
  X," "what agreements are in this folder," "contract radar," or "flag
  anything renewal-related." Scans and, on confirmation, writes a CSV +
  txt/pdf report. Single-phase: no separate "apply" step to ask for.
metadata:
  version: "1.0.3"
---

Delegate to the `contract-radar` subagent. Read `../folder-scan/SKILL.md` first, and `../term-sweep/SKILL.md` if a content deep-scan is confirmed.

# Contract Radar

## Why this is one phase, not two

This agent never touches candidate files — its only write action is a CSV + txt/pdf report. Folded into one scan-then-offer-to-save flow rather than a separate apply skill.

## Collect from the user

A folder scope (required). Term list is optional — default to `agreement, MSA, SOW, NDA, contract, renewal` if the user doesn't give one, but say so explicitly so they can override it.

## Sweep

Name/path match against the term list per `term-sweep`, always on. Surface `modified`/`created` dates on every candidate — contract radar is inherently about staleness/renewal timing, so dates matter even before any content check.

Content matching is a separate, opt-in "deep scan" (real per-file work — a download and parse per candidate, per `../content-extract/SKILL.md`): ask the user whether they want it, tell them roughly how many candidates are in scope, and only run it if they confirm. Respect `content-extract`'s per-run cap and disclose how many files were actually checked vs. in scope.

## Present the result, then actively offer to save it

Summary card: summary, term list used (and whether it was the default), name-match hits with last-modified dates, whether a content deep-scan ran and its hits if so, coverage, warnings — including that this is a **candidate list, not a verified inventory of active contracts** (a name/date match doesn't confirm the document is actually a current, executed agreement).

**Do not stop there and wait.** End by explicitly asking, e.g.: *"Want me to save this as a CSV + PDF report to `My Folder/Agents/Contract Radar/`?"*

## If confirmed, write the report

Read `../report-export/SKILL.md`. Default agent name: "Contract Radar".

Write CSV (name, path, term matched, last modified, link) and txt/pdf narrative including both caveats verbatim: the candidate-list-not-verified caveat above, and (if a content deep-scan ran) the content-search reliability caveat from `term-sweep`. Never touch candidate files — this agent's only write action is the report itself.
