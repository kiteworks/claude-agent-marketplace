# Invoice Organizer

`v0.5.1` · updated 2026-07-15

Finds invoices and receipts in a Kiteworks folder (including photos and scans), pulls out vendor, date, amount, and tax info, and -- once you approve -- renames them consistently and gives you a categorized spreadsheet for expenses or taxes.

**[View on the Kiteworks Agent Marketplace →](https://marketplace.kiteworks.com/catalog/invoice-organizer)** — live examples, screenshots, and full detail.

## Before you install — the short version

Kiteworks agents are provided **as is**. They are helpful, but they can be wrong. You are responsible for checking what an agent produces before you rely on it, and Kiteworks is not liable for outcomes from using them.

[Read the full install disclaimer](https://marketplace.kiteworks.com/legal/install-disclaimer) · Version `1.0` · Effective 2026-07-16

## What's new

Refreshed the branded report and the safety pre-check.

## Install

Add the marketplace once, then install this agent:

```
/plugin marketplace add https://sggitlab.acc.guru/agent-marketplace/claude-agent-marketplace
/plugin install invoice-organizer@kiteworks-lite
```

**Claude Desktop:** download `invoice-organizer.plugin` (or the identical `invoice-organizer.zip` if the uploader rejects `.plugin`) and upload it via **Customize → Personal plugins → Upload plugin**.

## Requires

A remote MCP connector named `Kiteworks` in your Claude organization — your Kiteworks admin provides the tenant-specific link. Without it the workflows have nothing to call.

## Try it

- “Organize the invoices in my Receipts folder”
- “Rename them consistently and give me an expense spreadsheet”

---
*Generated from the marketplace source — do not edit by hand; changes are overwritten on publish.*
