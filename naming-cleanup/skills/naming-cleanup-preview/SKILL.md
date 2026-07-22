---
name: naming-cleanup-preview
description: >
  Use when the user wants to clean up inconsistent or version-sprawled
  file names in Kiteworks — trigger phrases include "clean up naming in
  X," "find version sprawl," or "these file names are a mess." Read-only.
metadata:
  version: "0.2.0"
---

Delegate to the `naming-cleanup-preview` subagent. Read `../folder-scan/SKILL.md` first.

# Naming Cleanup — preview

## Collect from the user

A folder scope (required).

## Flag, don't fix yet

Walk the folder and flag: version-sprawl patterns (e.g. "final", "final_v2", "FINAL_FINAL", "copy", "v1"/"v2"/"v3" siblings of the same base name), and inconsistent naming (mixed case/date-format conventions across otherwise-similar files). For each flagged group, propose a standardized name, but do not assume — ask the user's naming convention if they haven't stated one.

## Present the result

Summary card: summary, flagged groups with proposed standardized name, coverage, warnings. Hand the confirmed-per-item renames forward for apply.
