---
name: inbox-triage-preview
description: >
  Use when the user wants help filing new items sitting in an
  inbox/uploads/unsorted Kiteworks folder — trigger phrases include
  "triage my inbox folder," "help me file these uploads," or "where
  should these files go." Read-only: proposes destinations, moves nothing.
metadata:
  version: "0.2.0"
---

Delegate to the `inbox-triage-preview` subagent. Read `../folder-scan/SKILL.md` and `../content-extract/SKILL.md` first.

# Inbox Triage — preview

## Collect from the user

The inbox/uploads folder to triage (required), and the destination tree to file into (a parent folder whose subfolders represent the target taxonomy — walk it with `get_folder_children` to learn the real folder names, never invent folder names that don't exist).

## Propose, don't guess blindly

**Pass 1 — always runs, free:** for each item, propose a destination subfolder based on file name, and for text-readable files (txt, csv, json, xml, md, log), also use `read_file_contents` directly per `content-extract`'s text-file path — no cost, works on every surface. State a confidence per item (clear match vs. uncertain).

**Pass 2 — content-aware classification for binary files, now wired in (2026-07-13):** earlier versions of this agent stopped at filename-only for binaries (pdf/docx/pptx/xlsx), which is most of what a real inbox actually contains — filename alone is a weak signal f