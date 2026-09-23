---
name: sharing-exposure
description: >
  Shared internal reference skill, not invoked by users directly. Every
  skill in this plugin that judges whether content is exposed through
  sharing (sharing-auditor, and Signal B of every *-compliance-check
  skill via compliance-mapping) reads this file for the one mechanism:
  read the scan root's own sharing flag, resolve the share origin above
  it when it is shared, and report exposure at the folder where the
  sharing starts. Read this before writing or modifying any
  sharing-related check.
metadata:
  version: "0.1.1"
---

# sharing-exposure — effective sharing exposure, resolved once per scan

Read `../folder-scan/SKILL.md` first; this skill only adds the sharing semantics on top of its walk. Same tools, same read-only rule, same call limits.

## What the connector actually tells you (confirmed live 2026-09-14)

- Sharing is a **folder** property. `get_top_folders` and `get_folder_children` folder records carry `isShared: true` when the folder is shared with other users (a membership exists beyond the owner, including folders shared *to* you). When a folder is not shared the key is **absent**, never `false`. `search_folders` hits carry the same fact as `is_shared`.
- **The flag cascades.** Every descendant folder of a shared folder reports `isShared: true`. So a folder's own flag already answers "is this folder, or anything above it, shared?" What it does not answer is *where* the sharing starts.
- **File records never carry the flag.** A file is exposed exactly when its containing folder is. A file shared directly (file-level share) is invisible to this mechanism; say so once in every report.
- Nothing on this connector says who the members are or whether they are internal or external. Never claim "external" sharing. Say "sharing exposure" or "in a shared folder tree".
- `path` on every folder and file record reads `Top folder/Subfolder/.../<own name>`, with no leading slash. Its first segment is the name the same folder has in `get_top_folders`, also for trees shared *to* you.
- `get_top_folders` is not a clean list of roots: it can include `deleted: true` records and folders whose `parentId` is not `"0"`. Ignore deleted records everywhere (walk, counts, matching). When matching a top-level name, require `parentId == "0"`.

## Vocabulary

- **shared**: the folder's flag is true.
- **exposed**: shared itself, or any ancestor shared; files inherit their folder.
- **share origin**: the topmost folder in a branch whose flag is true. For a shared scan root, the topmost shared ancestor.
- **origin depth**: how many levels above the scan root the share origin sits (parent = 1, grandparent = 2, 0 = the scan root itself).
- **visible top**: the top-level folder the ancestry walk reaches. `get_top_folders` is ACL-scoped, so this is the top of the scanning user's access, not the tenant root. Always say that folders above it are not visible.
- **exposure source**: `self`, or `ancestor "<name>" (<n> levels above the scan root)`, or `ancestor at or above the scan root (not resolved: <reason>)`.
- **not assessed**: the scan root's flag could not be read; Signal B has no verdict.

## Step 1: read the scan root's own flag (always, before the walk)

1. If you already hold the root's record from `get_top_folders` / `get_folder_children`, its `isShared` is the flag (absent = not shared). Done.
2. Otherwise call `get_folder_children(root_id)` (the walk needs its first page anyway). Take any child's `path` and strip the last segment: that is the root's path, and its last segment is the root's name.
3. Call `search_folders(path_contains=<root name>, search_type="folders")` and use **only** the hit whose `id` equals the root id (or whose `path` equals the root path). Its `is_shared` is the flag; absent or false means not shared. Ignore every other hit: `path_contains` is a substring match and also returns homonyms and descendants.
4. If the root has no children (so no path can be derived) and the user cannot supply the folder's path or name, report Signal B as **not assessed** and run the other signals. Never turn an unread flag into "not shared".

**Root not shared** (key absent or false): nothing above it is shared either (the flag cascades). Skip step 2. Zero extra calls.

## Step 2: root shared, so find the share origin (once per scan, never per item)

1. Split the root's `path` on `/`.
2. Segment 1: find it in `get_top_folders` by exact name among records with `parentId == "0"` that are not deleted. Page with the tool's top-level `offset` if `metadata.total` exceeds what came back. If more than one record matches, stop here: partially resolved, reason "ambiguous top-level name".
3. For each further segment, **while the previous level's flag is not true**, call `get_folder_children(parent_id=<matched id>, options={"name": "<segment>"})`. The name filter is server-side and returns the one matching folder; names are unique within a parent, so the match is deterministic.
4. **Stop at the first level whose flag is true.** That folder is the share origin; every level below it cascades true, so the remaining levels need no call. Record per level: name, id, flag, `creator.email`. The visible top is segment 1's record.
5. Caps: 25 levels, 3 pages per level. On a cap, a missing segment, a name mismatch, or an ambiguous top-level name, stop: the ancestry is *partially resolved*, the share origin is unknown, and the exposure source is `ancestor at or above the scan root (not resolved: <reason>)`. The root is still exposed; its own flag said so.

Cost: at most one call per level between the visible top and the scan root, plus pagination, once per scan. Sequential, paced per the rate-limit rule in `folder-scan`.

## Step 3: flag during the walk, report at the share origin only

Rule: an item is exposed if its own flag is true, or its parent folder is exposed, or the scan root is shared. Files inherit their containing folder.

Reporting collapses to the folder where sharing starts, because below it every row would say the same thing:

- **Scan root shared:** exactly one Signal B finding, placed at the share origin, or at the scan root itself when the origin is not resolved (the row then carries the "not resolved" exposure source, never depth 0). Its counts are the files and subfolders **under the scan root** that the walk saw, deleted items excluded. If a walk cap was hit, prefix the counts with "at least" and say the walk was partial. The share origin may hold far more than the scan root; the counts never describe the origin's whole tree. No per-item Signal B rows under the root.
- **Scan root not shared:** while walking, every subfolder whose flag is true and whose parent is not exposed is a share origin. One finding there (exposure source `self`) with the counts of its descendants, same counting rule; its descendants produce no Signal B rows. Files directly under an unexposed folder are never flagged.
- Other signals keep their per-item behaviour. This rule changes what Signal B reports, not how the walk runs.

## What every report says

Sharing-context lines (verbatim, fill the placeholders). Which lines apply:

- Always: `Sharing context: scan root "<root name>" is <shared | not shared (no sharing reported by Kiteworks) | not assessed (<reason>)>.`
- Only when the root is shared, exactly one of:
  - origin resolved: `Share origin: "<origin>" (<k> levels above the scan root; 0 = the scan root itself), creator <creator.email>. Ancestor chain walked from "<visible top>" (complete). Folders above the scanning user's own access are not visible to this scan.`
  - origin not resolved: `Share origin: not resolved (<reason>); the scan root's own flag is true, so the origin is at or above it. Ancestor chain walked from "<visible top, or the scan root when segment 1 failed>" (partially resolved: <reason>). Folders above the scanning user's own access are not visible to this scan.`
- Always: `Members: not visible on this connector.`

Finding row: `Exposed via <exposure source> (folder-level share). <N> files and <M> subfolders inherit this exposure.`

Limitation, always: `Sharing exposure is read from the folder-level isShared flag. It does not say who has access or whether they are internal or external. Directly shared files, and any sharing set above the top-level folder visible to the scanning user, are not detected.`

In any CSV or structured output, `share_origin`, `origin_depth` and `creator` are empty when the root is not shared or the origin is not resolved.

## Disclaimer

Every result surfaced through this pattern is a best-effort, productivity-grade summary over Kiteworks metadata. It is not deterministic and must not be used as the sole basis for compliance, legal, or disposition decisions.
