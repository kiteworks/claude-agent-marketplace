# Redactor

`v0.5.1` · updated 2026-07-15

Finds and replaces specific text -- like a name or other sensitive information -- across documents in a Kiteworks folder, and creates redacted copies once you approve. Originals are never changed.

**[View on the Kiteworks Agent Marketplace →](https://marketplace.kiteworks.com/catalog/redactor)** — live examples, screenshots, and full detail.

## Before you install — the short version

Kiteworks agents are provided **as is**. They are helpful, but they can be wrong. You are responsible for checking what an agent produces before you rely on it, and Kiteworks is not liable for outcomes from using them.

[Read the full install disclaimer](https://marketplace.kiteworks.com/legal/install-disclaimer) · Version `1.0` · Effective 2026-07-16

## What's new

Improved the redaction preview and term matching; refreshed the branded report and safety pre-check.

## Install

Add the marketplace once, then install this agent:

```
/plugin marketplace add https://sggitlab.acc.guru/agent-marketplace/claude-agent-marketplace.git
/plugin install redactor@kiteworks-lite
```

**Claude Desktop:** download `redactor.plugin` (or the identical `redactor.zip` if the uploader rejects `.plugin`) and upload it via **Customize → Personal plugins → Upload plugin**.

## Requires

A remote MCP connector named `Kiteworks` in your Claude organization — your Kiteworks admin provides the tenant-specific link. Without it the workflows have nothing to call.

## Try it

- “Redact the name 'Jane Smith' from documents in the Case Files folder”
- “Create the redacted copies”

---
*Generated from the marketplace source — do not edit by hand; changes are overwritten on publish.*
