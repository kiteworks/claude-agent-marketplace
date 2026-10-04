---
name: naming-cleanup-preview
description: >
  Use when the user wants to clean up inconsistent or version-sprawled
  file names in Kiteworks — trigger phrases include "clean up naming in
  X," "find version sprawl," or "these file names are a mess." Read-only.
metadata:
  version: "0.2.0"
---

Delegate to the `naming-cleanup-preview` subagent. If you already are that subagent, do not delegate again: follow this skill directly. Read `../folder-scan/SKILL.md` first.

# Naming Cleanup — preview

## Collect from the user

A folder scope (required).

## Flag, don't fix yet

Walk the folder and flag: version-sprawl patterns (e.g. "final", "final_v2", "FINAL_FINAL", "copy", "v1"/"v2"/"v3" siblings of the same base name), and inconsistent naming (mixed case/date-format conventions across otherwise-similar files). For each flagged group, propose a standardized name, but do not assume — ask the user's naming convention if they haven't stated one.

## Present the result

Summary card: summary, flagged groups with proposed standardized name, coverage, warnings. Hand the confirmed-per-item renames forward for apply.

## Save a proposal separately

This preview has no Kiteworks write access and cannot save a report itself. Return the complete assessment ledger to the main conversation. When the user requests a saved proposal, the main conversation collects the report preflight and calls this plugin's report-only agent. Saving a proposal does not run apply or authorize source changes.

## Evidence handoff for reports

Retain every enumerated object and every configured check in the version 2
assessment ledger, including failed/skipped checks and unvisited scope.
Use profile `naming`. Explain purpose, conclusion, implications and
proposed actions. Return that record to the main conversation along with
the preview. The caller invokes `naming-cleanup-report` to save the authorized
proposal. It must not substitute an apply run for a reporting request.
