---
name: surface-gate
description: >
  Shared internal reference skill, not invoked by users directly.
  folder-scan, report-export, and content-extract all read this file
  for the standard way to detect which Claude surface this conversation
  is running on (Cowork/Claude Code with subagents, vs. standard Chat
  without them) and what to tell the user when a capability this skill
  needs isn't available here. Read this before writing or modifying any
  of those three skills, or any new skill that delegates to a subagent
  or needs local file access.
metadata:
  version: "0.2.0"
---

# surface-gate — detect the surface, disclose or refuse honestly

Confirmed (Anthropic documentation): skills in a plugin run on every Claude surface — chat, Cowork, and Claude Code. **Hooks and subagents run only in Cowork and Claude Code; in standard Chat they don't exist at all, not degraded, just absent.** The Kiteworks MCP connector itself works on every surface (connectors work across claude.ai, desktop, Cowork, and mobile) — so the data and tool calls this plugin makes are fine anywhere; what changes per-surface is only the safety scaffolding around them.

## Step 1 — detect what's actually available, don't assume

Check the actual tool/agent list visible right now, the same way you'd check for anything else — don't guess from which product you think you're in.

- **Subagent isolation**: is a named subagent for this skill (e.g. `retention-sweeper-preview`) listed as an available agent to delegate to? If yes, you're on Cowork or Claude Code — delegate as the skill instructs. If no such subagent-delegation capability is listed at all, you're on a surface without it (standard Chat, most likely).
- **Local file access**: are native local file tools (Read/Write/Bash operating on real file paths) present *without* being namespaced under a separate connector like `Filesystem:...`? If yes, native local access exists (Cowork). If the only path to a local file is a distinct, separately-connected `Filesystem:` tool, or no local file tool exists at all, native local access is not available.

## Step 2 — pick the right response, per what THIS skill actually needs

Every skill that reads this file states which tier applies to it. There are three:

**Tier A — full support.** Both subagent isolation and (if needed) local file access are present. Proceed exactly as the skill's own instructions say, no extra disclosure needed.

**Tier B — degrade with disclosure.** Subagent isolation is missing, but this skill doesn't need local file access and doesn't do anything beyond its own documented, narrow write scope (this covers most preview and apply skills in this plugin — none of them are ever granted a delete tool in the first place, so the practical risk of running "directly" is modest).

**The disclosure itself must be hard to miss, not a soft aside.** A one-clause mention folded into a longer paragraph is not sufficient — confirmed by direct user feedback (2026-07-15) that a prior, softer version of this wording read as a quiet footnote rather than a real heads-up, and that this must generalize to every skill/agent in this plugin family that delegates to a subagent, not just be fixed in one place. Before doing anything else in the response — as its own standalone statement, first, never woven into other sentences — say, verbatim or close to it:

> *"Heads up: [this skill / agent name] normally runs isolated in its own dedicated subagent as a safety boundary. That isolation isn't available on this surface, so I'm running it directly in this conversation instead — its restrictions are enforced by me following instructions, not by the platform. For the full protection and reliability this is designed to run with, use Cowork or Claude Code instead."*

Then proceed with the task directly in the conversation. This is a recommendation to consider switching surfaces, not just a disclosure that the agent noted the limitation and moved on — the user should come away knowing both that something is reduced right now and that there's a straightforward way to get the full version. Do not compress this into a single subordinate clause, do not bury it after the substantive answer, and do not soften "use Cowork or Claude Code instead" into something vaguer like "this works better elsewhere."

**Tier C — refuse and redirect.** This skill needs a capability that is genuinely absent, not just less-enforced — right now that means: local file access for the binary-file path in `content-extract` (downloading and parsing PDFs/DOCX/etc. has nowhere to go without it). When this is the case, do not attempt a workaround or guess a path. Say plainly: *"This part of \[agent name\] isn't available here — it needs local file access to download and read \[file type\], which this surface doesn't have. Connect the Filesystem extension to enable it here, or run this from Claude Cowork or Claude Code, where it works natively."* If a `Filesystem:` connector tool exists but isn't actually connected/configured (as opposed to not existing at all), say that specifically — "installed but not connected" needs a different fix than "not installed," and collapsing them into one vague error wastes the user's time.

## Don't over-apply Tier C

Most of this plugin's skills are Tier B, not Tier C — losing subagent isolation is a real reduction in enforcement, but it isn't the same as the skill being unable to function. Reserve the hard refusal for cases where the actual mechanism (like local file access) doesn't exist, not just where the safety wall around it is thinner.
