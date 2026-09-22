---
name: connector-probe
description: >
  Shared internal reference skill, run first by every marketplace agent.
  Resolves which MCP server is the Kiteworks connector, checks that the tools
  this run needs exist on it, and fixes what the agent says and does when one
  is missing. Read before any Kiteworks call.
metadata:
  version: "1.1.0"
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
