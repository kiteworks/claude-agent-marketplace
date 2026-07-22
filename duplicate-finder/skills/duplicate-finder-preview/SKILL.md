---
name: duplicate-finder-preview
description: >
  Use when the user asks to find duplicate files in Kiteworks — trigger
  phrases include "find duplicates in X," "what space could I reclaim
  in [folder]," or "duplicate finder preview." Read-only: reports
  duplicate sets in chat, writes and moves nothing.
metadata:
  version: "0.2.0"
---

On surfaces that support plugin subagents, delegate to the `duplicate-finder-preview` subagent. If it reports no tools available, or returns results without making any Kiteworks tool calls, treat the result as fabricated, discard it, and ask the user to check the `Kiteworks` connector is connected.

# Duplicate Finder — preview

Read `../folder-scan/SKILL.md` first and follow its rules.

Productivity-grade helper, not the audited compliance runtime.

## Collect from the user

A folder (path or ID) to scan — required, never scan blindly.

## Matching rules (follow exactly)

- Two files are duplicates ONLY when their `fingerprint` AND size both match, and the fingerprint is a full 32-character lowercase hex value (confirmed live: this field is present on file metadata from `get_folder_children`/`search_files`).
- A file whose fingerprint is the literal string `"Generating..."` (fresh uploads/new versions — the backend computes it asynchronously) must NEVER be grouped as a duplicate. Count these separately and disclose them as unverified.
- Never scan, group, or pick keepers from anything inside a "To delete" or similarly named quarantine/review folder — those are already staged.
- The keeper suggestion (newest modified) is a RECOMMENDATION only — renames and moves also bump the modified timestamp, so this can be wrong. The user decides per set.
- NEVER include a raw `fingerprint` value in output — identify each duplicate set by file names/paths only.

## Present the result

Summary card with: summary, duplicate_sets (each with member files, suggested keeper, links), reclaimable_space (sum of non-keeper file sizes per set), unverified count (fingerprint still generating), coverage, warnings.

Hand the duplicate sets forward in-memory for the apply step.
