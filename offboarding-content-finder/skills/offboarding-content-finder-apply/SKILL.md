---
name: offboarding-content-finder-apply
description: >
  Use when the user has confirmed which owned items to stage for
  reassignment — trigger phrases include "move their files to a
  holding folder" or "stage that for reassignment."
metadata:
  version: "0.1.0"
---

Delegate to the `offboarding-content-finder-apply` subagent, passing only user-confirmed items and destination. Read `../report-export/SKILL.md`.

# Offboarding Content Finder — apply

Like Duplicate Finder, this agent relocates rather than deletes: move confirmed items into a holding folder (default `My Folder/Agents/Offboarding Content Finder/<Person Name>/`, or user-specified) using `move_file`/`move_folder`. Never delete. Require confirmation of the item set before moving — this is someone's real work product, treat it carefully.

Since preview now defaults to a tenant-wide sweep, the confirmed item set can span many different top-level folders. Keep the holding folder flat (don't try to recreate each item's original folder structure inside it) — the CSV's original-path column is what preserves where each item came from, not the destination layout.

## Steps

1. Create the holding folder if missing.
2. Move confirmed items into it.
3. Write a CSV (item, original path, new path, was-shared, link) and txt/pdf narrative (who this was for, what moved, where, disclaimer verbatim).
4. Report back plainly: what moved, where, and that the user/team should review and reassign ownership manually — this agent doesn't and can't change file ownership itself (no such tool exists).
