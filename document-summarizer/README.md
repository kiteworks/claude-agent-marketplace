# Document Summarizer

`v0.5.1` · updated 2026-07-15

Find and summarize documents stored in Kiteworks (docx, pdf, pptx, xlsx, and text formats) directly in chat, with compliance-aware handling of sensitivity labels and PII.

**[View on the Kiteworks Agent Marketplace →](https://marketplace.kiteworks.com/catalog/document-summarizer)** — live examples, screenshots, and full detail.

## Before you install — the short version

Kiteworks agents are provided **as is**. They are helpful, but they can be wrong. You are responsible for checking what an agent produces before you rely on it, and Kiteworks is not liable for outcomes from using them.

[Read the full install disclaimer](https://marketplace.kiteworks.com/legal/install-disclaimer) · Version `1.0` · Effective 2026-07-16

## What's new

Refreshed the branded report and the safety pre-check.

## Install

Add the marketplace once, then install this agent:

```
/plugin marketplace add https://sggitlab.acc.guru/agent-marketplace/claude-agent-marketplace.git
/plugin install document-summarizer@kiteworks-lite
```

**Claude Desktop:** download `document-summarizer.plugin` (or the identical `document-summarizer.zip` if the uploader rejects `.plugin`) and upload it via **Customize → Personal plugins → Upload plugin**.

## Requires

A remote MCP connector named `Kiteworks` in your Claude organization — your Kiteworks admin provides the tenant-specific link. Without it the workflows have nothing to call.

## Try it

- “Summarize the Q3 board deck in the Finance folder”
- “Summarize the signed contract PDF and save the summary”

---
*Generated from the marketplace source — do not edit by hand; changes are overwritten on publish.*
