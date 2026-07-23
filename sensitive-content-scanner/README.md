# Sensitive Content Scanner

`v1.3.0` · updated 2026-07-15

Scans a Kiteworks folder for sensitive terms and common PII (like SSNs, credit card numbers, and IBANs) before you share it, and can save a report.

**[View on the Kiteworks Agent Marketplace →](https://marketplace.kiteworks.com/catalog/sensitive-content-scanner)** — live examples, screenshots, and full detail.

## Before you install — the short version

Kiteworks agents are provided **as is**. They are helpful, but they can be wrong. You are responsible for checking what an agent produces before you rely on it, and Kiteworks is not liable for outcomes from using them.

[Read the full install disclaimer](https://marketplace.kiteworks.com/legal/install-disclaimer) · Version `1.0` · Effective 2026-07-16

## What's new

Improved sensitive-term and PII detection; refreshed the branded report and safety pre-check.

## Install

Add the marketplace once, then install this agent:

```
/plugin marketplace add https://sggitlab.acc.guru/agent-marketplace/claude-agent-marketplace.git
/plugin install sensitive-content-scanner@kiteworks-lite
```

**Claude Desktop:** download `sensitive-content-scanner.plugin` (or the identical `sensitive-content-scanner.zip` if the uploader rejects `.plugin`) and upload it via **Customize → Personal plugins → Upload plugin**.

## Requires

A remote MCP connector named `Kiteworks` in your Claude organization — your Kiteworks admin provides the tenant-specific link. Without it the workflows have nothing to call.

## Try it

- “Scan the Vendor Share folder for PII before I send it”
- “How many files are clean and safe to share?”

---
*Generated from the marketplace source — do not edit by hand; changes are overwritten on publish.*
