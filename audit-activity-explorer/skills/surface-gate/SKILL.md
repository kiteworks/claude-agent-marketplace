---
name: surface-gate
description: >
  Shared internal capability gate for isolation, folder acquisition, download
  mapping, parsing and cleanup on Chat, cloud/local Cowork and Claude Code.
metadata:
  version: "0.3.1"
---

# surface-gate — verify capabilities before choosing a path

Generated from `scratch-foundation/`, component 1.0.0.
Product labels and a shared Chat/Cowork interface do not establish filesystem or
permission capabilities. Check actual tools and their execution locations.

## Step 1 — verify and recover access where supported

- Subagent isolation: if you are already running as the plugin's named agent
  (its agent file is your instructions), isolation is satisfied: do not delegate
  again and give no Tier B notice. The agent has no delegation tool by design.
  Otherwise use the named subagent if delegation is available. Missing
  hooks/subagents means missing isolation, not missing code execution.
- Separate the source connector device, host storage, parser sandbox/VM/cloud,
  readable mapping/staging and cleanup executor. Chat may execute code and create
  files in a private sandbox; a local MCP host path is not automatically readable
  there. Cloud Cowork uses a device connection; local Cowork may use a Linux VM.
  Native Read/Write/Bash alone does not prove host access.
- Inspect actual device/folder tool schemas. Use get_device_info when present.
  Reuse a suitable existing authorized folder without another grant request.
  Otherwise try the available folder-access request once, describe the location
  and scope accurately, then recheck the grant. Never require a new grant when
  native access already suffices.
- Test a non-sensitive write/read round trip through the actual mapping and
  check the actual parser's supported input formats before any binary download.
  Folder-grant tools alone are insufficient. Also verify cleanup capability and
  applicable authorization; `../scratch-lifecycle/SKILL.md` defines that contract.
- Denied/unanswered access, a prompt that cannot complete, disconnected/revoked
  device access, VM-unavailable execution, unreadable staging, or no format parser
  are explicit acquisition failures. No new binary downloads in those cases.
  A web/mobile-origin Cowork session may restrict local access; opening it on
  Desktop is not proof of a grant. Do not invent a bridge or guess a path.

## Step 2 — respond according to what the task needs

**Tier A — full support.** Required mechanisms have been verified, including
isolation when requested. Proceed, preserving the binary scratch disclosure.

**Tier B — degrade with disclosure.** Subagent isolation is absent (the skill
runs in the main conversation, not as its named agent) but the actual task
mechanisms are available. Before doing anything else in the response, as
its own standalone statement, verbatim or close to it:

> Heads up: [skill / agent name] normally runs isolated in its own dedicated
> subagent as a safety boundary. That isolation isn't available on this surface,
> so I'm running it directly in this conversation instead — its restrictions are
> enforced by me following instructions, not by the platform. For the full
> protection and reliability this is designed to run with, use Cowork or Claude
> Code with subagent isolation enabled.

Then proceed within the skill's narrow scope. Do not bury the disclosure after
results. Missing isolation does not justify a claim that Chat cannot parse files.

**Tier C — unavailable after recovery.** State the actual missing or failed
capability: connector absent versus installed but disconnected, access denied,
device offline, unavailable VM, unreadable mapping, or unsupported format/parser.
Explain the applicable remedy without promising that switching products fixes it.
Offer metadata-only matching where useful; a summarizer says it cannot summarize
this binary. Keep content coverage distinct from filename/path matching.

Do not over-apply Tier C. Most metadata skills can run in Tier B; binary extraction
may also work in Chat with verified tools. Folder access and permanent deletion
are separate permissions. Never bypass the device deletion approval by using
another executor; retain/report scratch if authorization is declined.
