# Naming Cleanup

`v0.5.1` · updated 2026-07-15

Cleans up inconsistent or version-sprawled file names in a Kiteworks folder, and renames them once you approve.

**[View on the Kiteworks Agent Marketplace →](https://marketplace.kiteworks.com/catalog/naming-cleanup)** — live examples, screenshots, and full detail.

## Before you install — the short version

Kiteworks agents are provided **as is**. They are helpful, but they can be wrong. You are responsible for checking what an agent produces before you rely on it, and Kiteworks is not liable for outcomes from using them.

[Read the full install disclaimer](https://marketplace.kiteworks.com/legal/install-disclaimer) · Version `1.0` · Effective 2026-07-16

## What's new

Refreshed the branded report and the safety pre-check.

## Install

Add the marketplace once, then install this agent:

```
/plugin marketplace add https://sggitlab.acc.guru/agent-marketplace/claude-agent-marketplace.git
/plugin install naming-cleanup@kiteworks-lite
```

**Claude Desktop:** download `naming-cleanup.plugin` (or the identical `naming-cleanup.zip` if the uploader rejects `.plugin`) and upload it via **Customize → Personal plugins → Upload plugin**.

## Requires

A remote MCP connector named `Kiteworks` in your Claude organization — your Kiteworks admin provides the tenant-specific link. Without it the workflows have nothing to call.

## Try it

- “Clean up the inconsistent file names in the Reports folder”
- “Apply the approved renames”

---
*Generated from the marketplace source — do not edit by hand; changes are overwritten on publish.*
