---
name: folder-expiry-audit
description: >
  Use when the user asks about folder expiration/lifecycle settings in
  Kiteworks — trigger phrases include "which folders don't have an
  expiry set," "folder lifecycle audit," or "expiring folder check."
  Read-only report; does not and currently cannot configure expiry.
metadata:
  version: "0.1.0"
---

Delegate to the `folder-expiry-audit` subagent. Read `../folder-scan/SKILL.md` first.

# Folder Expiry Audit

## Important: this is audit-only, by confirmed necessity, not choice

An earlier design for this agent planned a "set up auto-expiring folders" action using `create_folder`'s `expire`/`fileLifetime` parameters. Live-tested twice (an ISO date string, then a numeric epoch-seconds string) — both times the created folder came back with `expire: 0` and `maxFileLifeTime: 0`, i.e. the parameters were silently ignored by this connector. There is also no separate "update folder settings" tool anywhere in this connector's tool set — so there is currently no path at all, via this connector, to configure folder expiry. Do not tell the user this agent can set an expiry on a folder. If the user asks for that, say plainly: this connector cannot configure folder expiry (create-time param is ignored, no update tool exists), and doing so would require the Kiteworks web UI directly or a fix from Kiteworks engineering.

## The read side is now verified live, not assumed

Earlier versions of this skill were honest that the read side had never actually been checked against a folder with a real, non-default policy — every test folder we'd created ourselves showed `expire: 0` / `maxFileLifeTime: 0`, which left open the possibility the read side was just as broken as the write side. That's now resolved: scanning all 69 top-level folders in this tenant found one real outlier — "Nomination List" reports `maxFileLifeTime: 9999` while every other one of the 69 reports `0`. That's a genuine, distinct, non-default value, not a stuck placeholder, so `maxFileLifeTime` is confirmed to reflect real per-folder configuration when read back.

Caveat worth keeping: `expire` itself was observed as `0` on every single folder checked (top-level and several levels of subfolders), including the one folder with a real `maxFileLifeTime`. That's consistent with "this tenant doesn't use hard expiration dates, only max-file-lifetime-day policies" rather than proof that `expire` itself is broken — report `expire: 0` as "not configured in this tenant" language, not as a suspected bug, unless a future run turns up a genuine non-zero `expire` value somewhere.

## What this agent does

Collect a folder scope from the user. Walk it and report each subfolder's `expire`/`maxFileLifeTime` values as returned by the API — a non-zero value means a real policy is configured; `0` means not configured (or, for `expire` specifically, possibly just not a setting this tenant uses). This is read-only signal reporting, useful for spotting folders that were configured with expiry through the Kiteworks UI directly (which works even though this connector's create-time path doesn't), not a way to fix anything through this agent.

## Present the result

Summary card: summary, folders with an expiry configured vs. not (call out any non-zero `maxFileLifeTime`/`expire` explicitly since they're rare and meaningful), coverage, and the write-side limitation stated plainly as a warning.
