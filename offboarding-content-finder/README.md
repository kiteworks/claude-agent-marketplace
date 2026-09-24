# Offboarding Content Finder

`v0.6.1` · updated 2026-09-23

Finds everything a departing or transferring employee owns across Kiteworks, and moves confirmed items to a holding folder for review.

**[View on the Kiteworks Agent Marketplace →](https://agents.kiteworks.com/catalog/offboarding-content-finder)** — live examples, screenshots, and full detail.

> **By installing or using this agent you accept the Kiteworks Agent Marketplace terms: https://agents.kiteworks.com/legal/marketplace-terms**

## Before you install — the short version

Kiteworks agents are intended for business and professional use. They use AI to generate their output automatically and are provided "as is", without warranty, to the maximum extent permitted by applicable law. Outputs are not professional advice and are not a compliance certification or legal determination of compliance with any framework. You are solely responsible for reviewing outputs before relying on them. No agent is FedRAMP authorized, and none are within the scope of Kiteworks' ISO 27001 certification or SOC 2 report. Installing or using any agent means you accept the full terms: https://agents.kiteworks.com/legal/marketplace-terms

[Read the full terms](https://agents.kiteworks.com/legal/marketplace-terms) · Version `2.0` · Effective 2026-08-15

## What's new

Treats files whose security scan is still running as "scan pending" instead of unreadable, and paces Kiteworks calls so large folders finish

## Install

Add the marketplace once, then install this agent:

```
/plugin marketplace add https://github.com/kiteworks/claude-agent-marketplace.git
/plugin install offboarding-content-finder@kiteworks-lite
```

**Claude Desktop:** download `offboarding-content-finder.plugin` and upload it via **Customize → Personal plugins → Upload plugin**.

## Requires

A remote MCP connector named `Kiteworks` in your Claude organization — your Kiteworks admin provides the tenant-specific link. Without it the workflows have nothing to call.

## Try it

- “Find everything owned by jdoe@example.com across Kiteworks”
- “Move the confirmed items to the Offboarding Hold folder”

---
*Generated from the marketplace source — do not edit by hand; changes are overwritten on publish.*
