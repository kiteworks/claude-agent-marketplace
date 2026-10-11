---
name: connector-probe
description: >
  Shared internal reference skill, run first by every marketplace agent.
  Resolves which MCP server is the Kiteworks connector, checks that the tools
  this run needs exist on it, and fixes what the agent says and does when one
  is missing, and says how to learn whether this user may call an
  admin-gated tool. Read before any Kiteworks call.
metadata:
  version: "1.4.0"
---

# connector-probe — resolve the connector, check its tools, degrade honestly

Generated from `connector-foundation/`; regenerate with
`python scripts/sync_connector_foundation.py`. Run this at the start of every
agent run, before the first Kiteworks call. Never reuse a result: the
connector, its transport and its enabled tools can change between runs.

## Resolve the connector

A server counts as the Kiteworks connector when either:

- its `mcp__<server>__` segment contains `kiteworks`, case-insensitive
  (`Kiteworks`, `kiteworks`,
  `claude_ai_Kiteworks_Content_MCP_limited_upload_download`, ...); or
- its server segment is a connection ID, a UUID such as
  `6af9e2af-b58b-429b-82dc-a67b80d38940` (how Claude Desktop names claude.ai
  directory connectors), **and** its tool list contains both `get_top_folders`
  and `get_user_info_whoami`. That pair is the fingerprint; a UUID-named
  server without it is not Kiteworks and must never be called.

The server name is whatever the user, their admin or the host chose; never
assume it is `Kiteworks`.

- Zero such servers: tell the user no Kiteworks connector is attached, state
  the rule in one sentence (an MCP server whose name contains `kiteworks`,
  or a connection-ID server exposing `get_top_folders` and
  `get_user_info_whoami`), and stop.
- One: use it.
- Several: prefer the one exposing both `upload_file_from_path` and
  `download_file_to_path`. Announce in one line which server was chosen and
  the tenant from `get_user_info_whoami`; for a UUID-named server name the
  tenant, since the ID means nothing to the user. Do not ask.

## Probe every tool this run needs

Check the resolved server's tool list for every tool this run will call, not
only the path tools. A tool exists when it is in that list; nothing else
counts. Never infer a tool from the server name, the host, the product name or
a previous run. Probe at every agent run; there is no cache.

## Login expired

An expired Kiteworks login answers every call with plain text, no structured
code: `failed to refresh token: API error 400: {"error": "invalid_grant", ...}`.
When any tool result or error contains `invalid_grant` or
`failed to refresh token`, the run is over: make no further tool call, save
nothing, do not retry (retries, parallel ones above all, do not help), and say
exactly this text:

```text
Your Kiteworks login has expired, so I stopped before changing or saving anything. Log in to Kiteworks again, then run me again.
```

If the run ends with a structured result block, report it in `tool_failures`
with the reason `invalid_grant`.

## Admin-gated tools

Some tools are advertised to every user but only work for a tenant admin:
the Kiteworks admin API answers everyone else with an in-band 403 error whose
body carries `ERR_ACCESS_ADMIN` or `ERR_ACCESS_ADMIN_COMPONENT`. The tool
list is identical for admins and other users, and `get_user_info_whoami`
carries no role flag, so a tool being listed never implies permission.

An agent that uses such a tool declares it in its body on one line, for
example `Admin-gated tools this agent uses: get_admin_activity.` Then:

- There is no separate probe call. The first real call to a declared
  read-only admin tool is the permission check: a 403 whose body carries
  `ERR_ACCESS_ADMIN` or `ERR_ACCESS_ADMIN_COMPONENT` means the signed-in
  user is not an admin on this tenant. Any other error is an ordinary tool
  error, not a permission answer.
- On that 403, say which capability is lost, in one sentence, in outcome
  language, at the moment it matters ("I cannot read the activity log on this
  connection, so who changed each item is not shown"), then continue with
  the user-level path. Say it once per run, do not retry the tool, and do
  not call another admin tool to check again.
- A declared admin tool that changes something (create, assign, update) is
  never used to learn a permission. The read-only admin tool declared beside
  it goes first, as part of the task; the write follows only after that read
  succeeded.
- Never infer admin status from `get_user_info_whoami`, from the tool being
  listed, from the user's job title, or from a previous run.
- Do not add a confirmation question of your own before an admin-gated call
  (a delegated run cannot ask). Tools that need one carry it server-side
  (`confirmation_token`): the server either prompts the user itself or tells
  you to relay its question, and you follow what it returns. Relaying or
  resending that token is never the user's consent: it is not a human
  approval. Agents that write as an admin gate those writes through their
  guard hook, never through the server token.

An admin-gated tool that is missing from the tool list altogether is handled
like any other missing tool (below), not as a permission answer.

## Admin-only agents

An agent whose body carries the line `This agent needs a Kiteworks admin.`
(besides its `Admin-gated tools this agent uses: ...` line) has no useful
user-level path. On the first 403 carrying `ERR_ACCESS_ADMIN` or
`ERR_ACCESS_ADMIN_COMPONENT` it ends the admin path: it says this text with
its own capability and alternatives filled in, and stops without calling
another admin tool:

```text
This needs a Kiteworks admin: {capability}. What you can do instead: {alternatives}.
```

Agents without that line keep the continue-with-the-user-path rule above.

## Transport and destructive tools

Classify the connection once per run, from the tool list alone:

- `remote` when neither `download_file_to_path` nor `upload_file_from_path`
  is listed, else `local`.
- `destructive tools enabled` when `create_user`, `reset_user_totp` or
  `move_file` is listed (the local server only lists them when started with
  destructive tools on), else not enabled.

An action that needs an unlisted tool is reported as unavailable on this
connection in one sentence (see "Any other missing tool") and is never
attempted through another tool.

## Silent while nothing is lost

If every needed tool exists, say nothing about connectors: no preamble, no
caveat, no mention of this skill.

## Scan step without `download_file_to_path`

Proceed. Text files (csv, txt, json, xml, md, log) are still read with
`read_file_contents`. PDF, Word, Excel and other binary rows are listed by
name, size, owner and sharing only and marked "not content-checked"; findings
about those files are limited accordingly. Say so once, as a header note
before the scan starts, with exactly this text:

```text
Note before I start: over this Kiteworks connection I can read text files (csv, txt, json, xml, md, log) but not the contents of PDF, Word or Excel files, because it cannot download them to this computer for parsing. Those files will be listed by name, size, owner and sharing only, marked "not content-checked". Findings about them are limited accordingly. Proceeding on that basis.
```

## Save step without `upload_file_from_path`

Do not attempt the PDF. Offer the CSV and the text report and wait for the
answer before writing anything, with exactly this text:

```text
I can save this as a CSV and a text report. A PDF is not possible over this Kiteworks connection: it runs remotely and cannot upload a file from this computer, and I will not paste an encoded PDF into a text file because that corrupts silently.
Want the CSV and text version now? If you need the PDF, the local Kiteworks MCP server for Claude Code supports it. Setup guide: agents.kiteworks.com/install/kiteworks-mcp
```

## Never fake a capability

- No base64 through `create_file_from_content`; it corrupts silently.
- No filename matching described as content analysis.
- No claiming a tool exists because the server name suggests it.
- No call to any tool on a UUID-named server before its tool list has shown
  the `get_top_folders` + `get_user_info_whoami` fingerprint.

## Any other missing tool

A tool can be hidden by the admin's OAuth scopes, by `KW_MCP_ENABLED_TOOLS` on
the server, or by a Claude Desktop per-tool permission. When one this run needs
is missing, say which capability is lost in one sentence at the moment it
matters, in outcome language ("I cannot move files on this connection, so the
review-folder step is skipped"), then continue with what is possible.

## Connector tools this skill uses

- Calls: `get_user_info_whoami`.
- Named only: `get_top_folders`, `read_file_contents`, `download_file_to_path`, `upload_file_from_path`, `create_file_from_content`, `get_admin_activity`, `create_user`, `reset_user_totp`, `move_file`.

Every agent is granted `get_user_info_whoami`: this skill uses it to name the
tenant. The named tools belong to the agent's own steps; this skill only
checks whether the connector lists them.
