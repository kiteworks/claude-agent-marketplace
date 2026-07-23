# Kiteworks Agents (Lite)

Productivity-grade (Lite) Kiteworks agents for Claude — direct-MCP, best-effort. NOT the audited Kiteworks compliance runtime, not audit-defensible, and not a basis for deletion decisions.

## Browse the catalog

**→ https://marketplace.kiteworks.com** — the full, always-current catalog with live examples, categories, and screenshots. This repository is the **install source**; the website is where you explore.

Recent additions and announcements: **https://marketplace.kiteworks.com/whats-new**

## Before you install — the short version

Kiteworks agents are provided **as is**. They are helpful, but they can be wrong. You are responsible for checking what an agent produces before you rely on it, and Kiteworks is not liable for outcomes from using them.

[Read the full install disclaimer](https://marketplace.kiteworks.com/legal/install-disclaimer) · Version `1.0` · Effective 2026-07-16

## Prerequisite — the Kiteworks connector

Every agent calls Kiteworks through a remote MCP connector referenced by the logical name `Kiteworks` — no URL or credential is bundled. In your Claude organization, add the remote MCP connector and name it `Kiteworks` (your Kiteworks admin provides the tenant-specific link). Without it the workflows have nothing to call.

## Install

Add this marketplace by URL, then install any agent by name:

```
/plugin marketplace add https://sggitlab.acc.guru/agent-marketplace/claude-agent-marketplace.git
/plugin install <agent>@kiteworks-lite
```

**Claude Desktop (single plugin):** download an `<agent>.plugin` bundle and upload it via **Customize → Personal plugins → Upload plugin** (or, org-wide, **Organization settings → Plugins → Add plugins → Upload a file**). If the uploader rejects `.plugin`, upload the identical `<agent>.zip`.

## Agents (15)

Explore and try each agent on the website — the list below links straight to each live page.

<details><summary>All 15 agents</summary>

| Agent | Version | Links |
|---|---|---|
| Activity Digest | `1.0.3` | [`./activity-digest/`](./activity-digest/) · [live](https://marketplace.kiteworks.com/catalog/activity-digest) |
| Contract Radar | `1.0.4` | [`./contract-radar/`](./contract-radar/) · [live](https://marketplace.kiteworks.com/catalog/contract-radar) |
| Document Summarizer | `0.5.1` | [`./document-summarizer/`](./document-summarizer/) · [live](https://marketplace.kiteworks.com/catalog/document-summarizer) |
| Duplicate Finder | `0.5.1` | [`./duplicate-finder/`](./duplicate-finder/) · [live](https://marketplace.kiteworks.com/catalog/duplicate-finder) |
| Folder Expiry Audit | `0.2.0` | [`./folder-expiry-audit/`](./folder-expiry-audit/) · [live](https://marketplace.kiteworks.com/catalog/folder-expiry-audit) |
| Inbox Triage | `0.5.1` | [`./inbox-triage/`](./inbox-triage/) · [live](https://marketplace.kiteworks.com/catalog/inbox-triage) |
| Intake Form Builder | `0.1.0` | [`./intake-form-builder/`](./intake-form-builder/) · [live](https://marketplace.kiteworks.com/catalog/intake-form-builder) |
| Invoice Organizer | `0.5.1` | [`./invoice-organizer/`](./invoice-organizer/) · [live](https://marketplace.kiteworks.com/catalog/invoice-organizer) |
| Naming Cleanup | `0.5.1` | [`./naming-cleanup/`](./naming-cleanup/) · [live](https://marketplace.kiteworks.com/catalog/naming-cleanup) |
| Offboarding Content Finder | `0.5.1` | [`./offboarding-content-finder/`](./offboarding-content-finder/) · [live](https://marketplace.kiteworks.com/catalog/offboarding-content-finder) |
| Redactor | `0.5.1` | [`./redactor/`](./redactor/) · [live](https://marketplace.kiteworks.com/catalog/redactor) |
| Retention Sweeper | `1.0.3` | [`./retention-sweeper/`](./retention-sweeper/) · [live](https://marketplace.kiteworks.com/catalog/retention-sweeper) |
| Sensitive Content Scanner | `1.3.0` | [`./sensitive-content-scanner/`](./sensitive-content-scanner/) · [live](https://marketplace.kiteworks.com/catalog/sensitive-content-scanner) |
| Sharing Auditor | `1.0.3` | [`./sharing-auditor/`](./sharing-auditor/) · [live](https://marketplace.kiteworks.com/catalog/sharing-auditor) |
| Storage Visualizer | `1.0.3` | [`./storage-visualizer/`](./storage-visualizer/) · [live](https://marketplace.kiteworks.com/catalog/storage-visualizer) |

</details>

## What's in this repo

- `.claude-plugin/marketplace.json` — the marketplace catalog (`kiteworks-lite`).
- `<agent>/` — the plugin directory (skills, agents, connector setup, per-agent README).
- `<agent>.plugin` and `<agent>.zip` — single-plugin bundles (identical bytes; `.zip` works around a Claude Desktop uploader that rejects `.plugin`).

## Notes

- Bundles are **unsigned** in this interim; install-source integrity rests on repository controls (branch protection on the published repo) until signed bundles land.

---
*Generated from the `kiteworks-agent-marketplace-lite` source — do not edit by hand; changes are overwritten on publish.*
