# Duplicate Finder

`v0.5.1` · updated 2026-07-15

Finds duplicate files in a Kiteworks folder and, once you approve, moves the extra copies to a review folder so you can reclaim space.

**[View on the Kiteworks Agent Marketplace →](https://marketplace.kiteworks.com/catalog/duplicate-finder)** — live examples, screenshots, and full detail.

## Before you install — the short version

Kiteworks agents are provided **as is**. They are helpful, but they can be wrong. You are responsible for checking what an agent produces before you rely on it, and Kiteworks is not liable for outcomes from using them.

[Read the full install disclaimer](https://marketplace.kiteworks.com/legal/install-disclaimer) · Version `1.0` · Effective 2026-07-16

## What's new

Refreshed the branded report and the safety pre-check.

## Install

Add the marketplace once, then install this agent:

```
/plugin marketplace add https://sggitlab.acc.guru/agent-marketplace/claude-agent-marketplace
/plugin install duplicate-finder@kiteworks-lite
```

**Claude Desktop:** download `duplicate-finder.plugin` (or the identical `duplicate-finder.zip` if the uploader rejects `.plugin`) and upload it via **Customize → Personal plugins → Upload plugin**.

## Requires

A remote MCP connector named `Kiteworks` in your Claude organization — your Kiteworks admin provides the tenant-specific link. Without it the workflows have nothing to call.

## Try it

- “Find duplicate files in the Marketing Assets folder”
- “Move the duplicate copies to a review folder for me to check”

---
*Generated from the marketplace source — do not edit by hand; changes are overwritten on publish.*
