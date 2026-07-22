---
name: inbox-triage-apply
description: >
  Use when the user has reviewed inbox triage proposals and confirmed
  which items to file where — trigger phrases include "file those" or
  "move the confirmed ones."
metadata:
  version: "0.1.0"
---

Delegate to the `inbox-triage-apply` subagent, passing only user-confirmed item→destination pairs. Read `../report-export/SKILL.md` for the export half.

# Inbox Triage — apply

Confirmed live: `move_file` works cleanly (tested moving a file between two Kiteworks folders; path and metadata updated correctly). Still: **never move an item the user hasn't explicitly confirmed** — this agent moves real, possibly important files, unlike the review-only moves in Duplicate Finder. Require per-item confirmation, not a single blanket "yes to all."

## Steps

1. For each confirmed item, call `move_file` to its confirmed destination.
2. Write a CSV (item, from-path, to-path, confidence at proposal time, link) and a txt/pdf narrative (what moved, what was left unfiled and why, disclaimer verbatim) into `Agents/Inbox Triage/` (or user destination), per `report-export`.
3. Report back plainly what moved where, and what's still sitting unfiled.
