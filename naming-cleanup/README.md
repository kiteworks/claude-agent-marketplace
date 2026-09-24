# Naming Cleanup

`v0.6.2` · updated 2026-09-24

Cleans up inconsistent or version-sprawled file names in a Kiteworks folder, and renames them once you approve.

**[View on the Kiteworks Agent Marketplace →](https://agents.kiteworks.com/catalog/naming-cleanup)** — live examples, screenshots, and full detail.

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
/plugin install naming-cleanup@kiteworks-lite
```

**Claude Desktop:** download `naming-cleanup.plugin` and upload it via **Customize → Personal plugins → Upload plugin**.

## Requires

A remote MCP connector named `Kiteworks` in your Claude organization — your Kiteworks admin provides the tenant-specific link. Without it the workflows have nothing to call.

## Try it

- “Clean up the inconsistent file names in the Reports folder”
- “Apply the approved renames”

---
*Generated from the marketplace source — do not edit by hand; changes are overwritten on publish.*
