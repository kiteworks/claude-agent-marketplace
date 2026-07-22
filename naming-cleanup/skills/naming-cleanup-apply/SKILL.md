---
name: naming-cleanup-apply
description: >
  Use when the user has confirmed which renames to apply — trigger
  phrases include "rename those" or "apply the naming cleanup."
metadata:
  version: "0.1.0"
---

Delegate to the `naming-cleanup-apply` subagent, passing only user-confirmed old-name→new-name pairs. Read `../report-export/SKILL.md`.

# Naming Cleanup — apply

Confirmed live: `rename_file` works cleanly (tested renaming a file in place; metadata updated, path reflects new name). Require per-item confirmation before renaming — never bulk-rename an entire flagged list on one blanket "yes."

## Steps

1. For each confirmed item, call `rename_file` (or `rename_folder`) with the confirmed new name.
2. Write a CSV (old name, new name, path, link) and txt/pdf narrative (what was renamed, what was skipped, disclaimer verbatim) into `Agents/Naming Cleanup/` (or user destination).
3. Report back plainly what changed.
