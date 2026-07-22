---
name: duplicate-finder-apply
description: >
  Use when the user confirms which duplicate sets to act on — trigger
  phrases include "move those duplicates to review," "clean up the
  duplicates we found," or "export that duplicate report." Requires a
  preview to have already run in this conversation, and per-set
  confirmation before moving anything.
metadata:
  version: "0.1.0"
---

On surfaces that support plugin subagents: gather duplicate sets via the `duplicate-finder-preview` subagent first, confirm the action AND destination with the user PER SET (which file(s) to move, which to keep in place), then delegate the mechanical move + write to the `duplicate-finder-apply` subagent.

# Duplicate Finder — apply

Read `../report-export/SKILL.md` first for the CSV/txt/pdf convention. Default agent name for the folder convention: "Duplicate Finder".

This agent's apply step does two things, unlike Retention Sweeper and Storage Visualizer:

1. **Moves confirmed duplicate files into a review folder** — default `My Folder/Agents/Duplicate Finder/Review/`, or a user-specified location — using `move_file`. Never delete anything; the user deletes manually from the review folder after checking it. Only move files the user has explicitly confirmed per duplicate set (never bulk-move an entire result without per-set confirmation, since the "newest modified = keeper" heuristic can be wrong).
2. **Writes the CSV + txt/pdf report** exactly as `report-export` specifies, including which files were moved, where, and a Kiteworks link to the review folder so the user can jump straight to it.

## Steps

1. For each duplicate set, confirm with the user which file(s) to move (defaults to all non-keeper copies, but the user can override the keeper choice).
2. Create the review folder if missing.
3. `move_file` each confirmed duplicate into it.
4. Write the CSV (columns: duplicate-set id, file name, original path, moved-to path, size, keeper yes/no) and the txt/pdf narrative (sets found, reclaimable space, what was moved, link to the review folder, disclaimer verbatim).
5. Report back clearly: what moved, where, and that nothing was deleted — the user reviews and deletes manually.
