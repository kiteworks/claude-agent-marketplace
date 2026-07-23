# Inbox Triage

`v0.5.1` · updated 2026-07-15

Sorts files sitting in a Kiteworks inbox or uploads folder into the right project folders, and moves them once you approve the matches.

**[View on the Kiteworks Agent Marketplace →](https://marketplace.kiteworks.com/catalog/inbox-triage)** — live examples, screenshots, and full detail.

## Before you install — the short version

Kiteworks agents are provided **as is**. They are helpful, but they can be wrong. You are responsible for checking what an agent produces before you rely on it, and Kiteworks is not liable for outcomes from using them.

[Read the full install disclaimer](https://marketplace.kiteworks.com/legal/install-disclaimer) · Version `1.0` · Effective 2026-07-16

## What's new

Refreshed the branded report and the safety pre-check.

## Install

Add the marketplace once, then install this agent:

```
/plugin marketplace add https://sggitlab.acc.guru/agent-marketplace/claude-agent-marketplace.git
/plugin install inbox-triage@kiteworks-lite
```

**Claude Desktop:** download `inbox-triage.plugin` (or the identical `inbox-triage.zip` if the uploader rejects `.plugin`) and upload it via **Customize → Personal plugins → Upload plugin**.

## Requires

A remote MCP connector named `Kiteworks` in your Claude organization — your Kiteworks admin provides the tenant-specific link. Without it the workflows have nothing to call.

## Try it

- “Sort the files in my Uploads inbox into the right project folders”
- “Move the confirmed matches”

---
*Generated from the marketplace source — do not edit by hand; changes are overwritten on publish.*
