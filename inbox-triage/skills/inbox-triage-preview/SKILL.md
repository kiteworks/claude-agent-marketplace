---
name: inbox-triage-preview
description: >
  Use when the user wants help filing new items sitting in an
  inbox/uploads/unsorted Kiteworks folder — trigger phrases include
  "triage my inbox folder," "help me file these uploads," or "where
  should these files go." Read-only: proposes destinations, moves nothing.
metadata:
  version: "0.2.1"
---

Delegate to the `inbox-triage-preview` subagent. If you already are that subagent, do not delegate again: follow this skill directly. Read `../folder-scan/SKILL.md` and `../content-extract/SKILL.md` first.

# Inbox Triage — preview

## Collect from the user

The inbox/uploads folder to triage (required), and the destination tree to file into (a parent folder whose subfolders represent the target taxonomy — walk it with `get_folder_children` to learn the real folder names, never invent folder names that don't exist).

## Propose, don't guess blindly

**Pass 1 — always runs, free:** for each item, propose a destination subfolder based on file name, and for text-readable files (txt, csv, json, xml, md, log), also use `read_file_contents` directly per `content-extract`'s text-file path — no cost, works on every surface. State a confidence per item (clear match vs. uncertain).

**Pass 2 — content-aware classification for binary files, now wired in (2026-07-13):** earlier versions of this agent stopped at filename-only for binaries (pdf/docx/pptx/xlsx), which is most of what a real inbox actually contains — filename alone is a weak signal for most of it. Now extracts real text via `content-extract`'s binary path (pikepdf/python-docx/python-pptx/openpyxl) and classifies off actual content rather than just the name — same confidence scale as Pass 1 (clear match vs. uncertain), but now grounded in what the file actually says, not a guess from its filename.

## Present the result

Summary card: summary, proposed destination per item with confidence tier and which pass produced it (filename-only vs. content-aware), coverage, warnings. Hand the confirmed item→destination pairs forward for apply.
