---
name: offboarding-content-finder-preview
description: >
  Use when the user wants to find content owned by a departed or
  transferring employee in Kiteworks — trigger phrases include "find
  [person]'s files before they leave," "offboarding content check for
  [name]," "what does [email] own," or "sweep the tenant for [name]'s
  files." Defaults to a tenant-wide sweep across all top-level folders,
  not a single folder. Read-only.
metadata:
  version: "0.3.0"
---

Delegate to the `offboarding-content-finder-preview` subagent. If you already are that subagent, do not delegate again: follow this skill directly. Read `../folder-scan/SKILL.md` first.

# Offboarding Content Finder — preview

## A confirmed limitation, and the fix built for it (2026-07-13)

There is no server-side "owner" or "creator" filter on `search`/`search_files`/`search_folders` (confirmed against the tool schema) — this agent must walk with `get_folder_children` and filter client-side on each item's `creator`/`userId` field (confirmed present on real folder/file objects).

**Earlier versions of this agent required the user to already name a single folder to check.** That defeats the actual point of an offboarding sweep — the real question is "what does this person own, anywhere," not "what do they own in the one folder I happened to guess." Fixed: this agent now defaults to a **tenant-wide sweep** across every top-level folder, not a single-folder check.

## Collect from the user

The departed/transferring person's name or email (required). Ask, don't assume, whether they want:

- **Tenant-wide sweep (default, recommended)** — every top-level folder from `get_top_folders`, each walked and filtered.
- **Narrower scope** — a specific folder or subtree the user already has in mind, if they'd rather not wait on a full sweep.

## Walk and filter

Walk the chosen scope with `get_folder_children`, matching each item's `creator`/`userId` field against the name or email given (case-insensitive; check both fields, since which one is populated varies by endpoint). Never rely on folder or file naming as a proxy for ownership — only the actual `creator`/`userId` field counts as a match.

## Page every listing and report coverage

Page every `get_top_folders` and `get_folder_children` call as `../folder-scan/SKILL.md` sets out under "Page every listing call": `limit` and `offset`, until the folder's `metadata.total` is reached (without a `total`, until a page comes back empty or short). A top-level folder counts as swept only when every folder beneath it was fully listed.

The result carries the folder-scan coverage block: pages walked (listing calls made), folders and files examined per top-level folder (counted from each record's `type`, adding up to the totals), and every cap hit, skip or error by path.

Never report "0 items owned" when any folder in scope is incomplete or skipped. Say the sweep is incomplete instead: no owned items were found in the folders that were fully listed, name the folders that were not, and say the person may own content there.

## Present the result

Summary card: summary, matched items (path, type, which field matched, last-modified), folders swept vs. skipped, the coverage block, warnings. Hand the confirmed item set forward for apply (staging into a holding folder for reassignment) if the user wants to act on it.
