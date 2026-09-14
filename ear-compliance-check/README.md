# EAR Compliance Check

`v1.1.0` · updated 2026-09-14

Scans a Kiteworks folder for export-controlled technology descriptions and external/foreign sharing under EAR, and saves a report. ECCN classification is outside what this can check; it says so.

**[View on the Kiteworks Agent Marketplace →](https://agents.kiteworks.com/catalog/ear-compliance-check)** — live examples, screenshots, and full detail.

> **By installing or using this agent you accept the Kiteworks Agent Marketplace terms: https://agents.kiteworks.com/legal/marketplace-terms**

## Before you install — the short version

Kiteworks agents are intended for business and professional use. They use AI to generate their output automatically and are provided "as is", without warranty, to the maximum extent permitted by applicable law. Outputs are not professional advice and are not a compliance certification or legal determination of compliance with any framework. You are solely responsible for reviewing outputs before relying on them. No agent is FedRAMP authorized, and none are within the scope of Kiteworks' ISO 27001 certification or SOC 2 report. Installing or using any agent means you accept the full terms: https://agents.kiteworks.com/legal/marketplace-terms

[Read the full terms](https://agents.kiteworks.com/legal/marketplace-terms) · Version `2.0` · Effective 2026-08-15

## What's new

added 1 file(s); updated 3 file(s)

## Install

Add the marketplace once, then install this agent:

```
/plugin marketplace add https://github.com/kiteworks/claude-agent-marketplace.git
/plugin install ear-compliance-check@kiteworks-lite
```

**Claude Desktop:** download `ear-compliance-check.plugin` (or the identical `ear-compliance-check.zip` if the uploader rejects `.plugin`) and upload it via **Customize → Personal plugins → Upload plugin**.

## Requires

A remote MCP connector named `Kiteworks` in your Claude organization — your Kiteworks admin provides the tenant-specific link. Without it the workflows have nothing to call.

## Try it

- “Check the Vendor Share folder for EAR exposure risks”
- “Summarize this folder's EAR exposure and save a report”

---
*Generated from the marketplace source — do not edit by hand; changes are overwritten on publish.*
