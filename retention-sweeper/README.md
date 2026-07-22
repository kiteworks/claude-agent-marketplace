# Retention Sweeper

`v1.0.3` · updated 2026-07-15

Finds files in a Kiteworks folder that are past a retention deadline you set, and can save a report of what it found.

**[View on the Kiteworks Agent Marketplace →](https://marketplace.kiteworks.com/catalog/retention-sweeper)** — live examples, screenshots, and full detail.

## Before you install — the short version

Kiteworks agents are provided **as is**. They are helpful, but they can be wrong. You are responsible for checking what an agent produces before you rely on it, and Kiteworks is not liable for outcomes from using them.

[Read the full install disclaimer](https://marketplace.kiteworks.com/legal/install-disclaimer) · Version `1.0` · Effective 2026-07-16

## What's new

Refreshed the branded report and the safety pre-check.

## Install

Add the marketplace once, then install this agent:

```
/plugin marketplace add https://sggitlab.acc.guru/agent-marketplace/claude-agent-marketplace
/plugin install retention-sweeper@kiteworks-lite
```

**Claude Desktop:** download `retention-sweeper.plugin` (or the identical `retention-sweeper.zip` if the uploader rejects `.plugin`) and upload it via **Customize → Personal plugins → Upload plugin**.

## Requires

A remote MCP connector named `Kiteworks` in your Claude organization — your Kiteworks admin provides the tenant-specific link. Without it the workflows have nothing to call.

## Try it

- “Find files in Archive older than the 7-year retention deadline”
- “Summarize what's overdue and save a report”

---
*Generated from the marketplace source — do not edit by hand; changes are overwritten on publish.*
