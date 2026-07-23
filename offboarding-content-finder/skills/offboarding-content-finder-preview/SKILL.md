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
  version: "0.2.0"
---

Delegate to the `offboarding-content-finder-preview` subagent. Read `../folder-scan/SKILL.md` first.

# Offboarding Content Finder — preview

## A confirmed limitation, and the fix built for it (2026-07-13)

There is no server-side "owner" or "creator" filter on `search`/`search_files`/`search_folders` (confirmed against the tool schema) — this agent must walk with `get_folder_children` and filter client-side on each item's `creator`/`userId` field (confirmed present on real folder/file objects).

**Earlier versions of this agent required the user to already name a single folder to check.** That defeats the actual point of an offboarding sweep — the real question is "what does this person own, anywhere," not "what do they own in the one folder I happened to guess." Fixed: this agent now defaults to a **tenant-wide sweep** across every top-level folder, not a single-folder check.

## Collect from the user

The departed/transferring person's name or email (required). Ask, don't assume, whether they want:
- **Tenant-wide sweep (default, recommended)** — every top-level folder from `get_top_folders`, each walked and filtered.
- **Narrowe