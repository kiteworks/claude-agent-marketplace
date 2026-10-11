# Activity Explorer

`v0.1.1` · updated 2026-10-10

Lets a Kiteworks admin ask about the Kiteworks audit log in plain language, or save a report. It reads the log in 30-day windows for any period up to 12 months, and says how far back it could reach. Ask in chat for aggregated answers (up to 50 rows), save a report as a PDF with CSVs, review one person's activity with a stated purpose such as a ticket or incident reference, or follow the history of files and folders you can see. Breakdowns cover activity category, event type, app, success or failure, internal or external user, profile, and day and hour, plus an always-present section on AI-agent activity. Rule-based flags, with no scores, mark unusual daily volume, repeated failures, activity outside working hours and bulk downloads. It is admin-only and read-only, never shows IP addresses or locations, and saved reports that name people need your approval first. These are observations from your audit log: not a real-time alert, not a login or settings-change report and not a complete forensic record. Per-person activity review can count as employee monitoring in some countries. Involve your data protection officer and, where one exists, your works council before using the person view.

**[View on the Kiteworks Agent Marketplace →](https://agents.kiteworks.com/catalog/audit-activity-explorer)** — live examples, screenshots, and full detail.

> **By installing or using this agent you accept the Kiteworks Agent Marketplace terms: https://agents.kiteworks.com/legal/marketplace-terms**

## Before you install — the short version

Kiteworks agents are intended for business and professional use. They use AI to generate their output automatically and are provided "as is", without warranty, to the maximum extent permitted by applicable law. Outputs are not professional advice and are not a compliance certification or legal determination of compliance with any framework. You are solely responsible for reviewing outputs before relying on them. No agent is FedRAMP authorized, and none are within the scope of Kiteworks' ISO 27001 certification or SOC 2 report. Installing or using any agent means you accept the full terms: https://agents.kiteworks.com/legal/marketplace-terms

[Read the full terms](https://agents.kiteworks.com/legal/marketplace-terms) · Version `2.0` · Effective 2026-08-15

## What's new

First general release. Ask the Kiteworks audit log who did what in plain language, for any period up to 12 months, and save a PDF report with CSVs. Needs a Kiteworks admin account; read-only.

## Install

Add the marketplace once, then install this agent:

```
/plugin marketplace add https://github.com/kiteworks/claude-agent-marketplace.git
/plugin install audit-activity-explorer@kiteworks-lite
```

**Claude Desktop:** download `audit-activity-explorer.plugin` and upload it via **Customize → Personal plugins → Upload plugin**.

## Requires

A remote MCP connector named `Kiteworks` in your Claude organization — your Kiteworks admin provides the tenant-specific link. Without it the workflows have nothing to call.

## Try it

- “Give me last quarter's activity report for the audit committee”
- “What did AI agents do on our tenant this month, and did any of it fail?”
- “What did ana.ruiz@example.com do in the last 30 days?”

---
*Generated from the marketplace source — do not edit by hand; changes are overwritten on publish.*
