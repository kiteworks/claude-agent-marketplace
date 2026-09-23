# ISM (Australia) Compliance Check

`v1.2.2` · updated 2026-09-23

Checks a Kiteworks folder for classification-marked content and external sharing under Australia's ISM, and saves a report. Most of ISM is outside what this can check; it says so.

**[View on the Kiteworks Agent Marketplace →](https://agents.kiteworks.com/catalog/ism-au-compliance-check)** — live examples, screenshots, and full detail.

> **By installing or using this agent you accept the Kiteworks Agent Marketplace terms: https://agents.kiteworks.com/legal/marketplace-terms**

## Before you install — the short version

Kiteworks agents are intended for business and professional use. They use AI to generate their output automatically and are provided "as is", without warranty, to the maximum extent permitted by applicable law. Outputs are not professional advice and are not a compliance certification or legal determination of compliance with any framework. You are solely responsible for reviewing outputs before relying on them. No agent is FedRAMP authorized, and none are within the scope of Kiteworks' ISO 27001 certification or SOC 2 report. Installing or using any agent means you accept the full terms: https://agents.kiteworks.com/legal/marketplace-terms

[Read the full terms](https://agents.kiteworks.com/legal/marketplace-terms) · Version `2.0` · Effective 2026-08-15

## What's new

Maintenance release: internal skill metadata cleanup.

## Install

Add the marketplace once, then install this agent:

```
/plugin marketplace add https://github.com/kiteworks/claude-agent-marketplace.git
/plugin install ism-au-compliance-check@kiteworks-lite
```

**Claude Desktop:** download `ism-au-compliance-check.plugin` (or the identical `ism-au-compliance-check.zip` if the uploader rejects `.plugin`) and upload it via **Customize → Personal plugins → Upload plugin**.

## Requires

A remote MCP connector named `Kiteworks` in your Claude organization — your Kiteworks admin provides the tenant-specific link. Without it the workflows have nothing to call.

## Try it

- “Check the Vendor Share folder for the Australian ISM exposure risks”
- “Summarize this folder's the Australian ISM exposure and save a report”

---
*Generated from the marketplace source — do not edit by hand; changes are overwritten on publish.*
