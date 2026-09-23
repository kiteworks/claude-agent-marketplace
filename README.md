# Kiteworks Agents (Lite)

Productivity-grade (Lite) Kiteworks agents for Claude — direct-MCP, best-effort. NOT the audited Kiteworks compliance runtime, not audit-defensible, and not a basis for deletion decisions.

## Browse the catalog

**→ https://agents.kiteworks.com** — the full, always-current catalog with live examples, categories, and screenshots. This repository is the **install source**; the website is where you explore.

Recent additions and announcements: **https://agents.kiteworks.com/whats-new**

> **By installing or using this agent you accept the Kiteworks Agent Marketplace terms: https://agents.kiteworks.com/legal/marketplace-terms**

## Before you install — the short version

Kiteworks agents are intended for business and professional use. They use AI to generate their output automatically and are provided "as is", without warranty, to the maximum extent permitted by applicable law. Outputs are not professional advice and are not a compliance certification or legal determination of compliance with any framework. You are solely responsible for reviewing outputs before relying on them. No agent is FedRAMP authorized, and none are within the scope of Kiteworks' ISO 27001 certification or SOC 2 report. Installing or using any agent means you accept the full terms: https://agents.kiteworks.com/legal/marketplace-terms

[Read the full terms](https://agents.kiteworks.com/legal/marketplace-terms) · Version `2.0` · Effective 2026-08-15

## Prerequisite — the Kiteworks connector

Every agent calls Kiteworks through a remote MCP connector referenced by the logical name `Kiteworks` — no URL or credential is bundled. In your Claude organization, add the remote MCP connector and name it `Kiteworks` (your Kiteworks admin provides the tenant-specific link). Without it the workflows have nothing to call.

## Install

Add this marketplace by URL, then install any agent by name:

```
/plugin marketplace add https://github.com/kiteworks/claude-agent-marketplace.git
/plugin install <agent>@kiteworks-lite
```

**Claude Desktop (single plugin):** download an `<agent>.plugin` bundle and upload it via **Customize → Personal plugins → Upload plugin** (or, org-wide, **Organization settings → Plugins → Add plugins → Upload a file**). If the uploader rejects `.plugin`, upload the identical `<agent>.zip`.

## Agents (41)

Explore and try each agent on the website — the list below links straight to each live page.

<details><summary>All 41 agents</summary>

| Agent | Version | Links |
|---|---|---|
| Activity Digest | `1.1.1` | [`./activity-digest/`](./activity-digest/) · [live](https://agents.kiteworks.com/catalog/activity-digest) |
| CCPA Compliance Check | `1.2.2` | [`./ccpa-compliance-check/`](./ccpa-compliance-check/) · [live](https://agents.kiteworks.com/catalog/ccpa-compliance-check) |
| CIS Controls Compliance Check | `1.2.2` | [`./cis-controls-compliance-check/`](./cis-controls-compliance-check/) · [live](https://agents.kiteworks.com/catalog/cis-controls-compliance-check) |
| CMMC Compliance Check | `1.2.2` | [`./cmmc-compliance-check/`](./cmmc-compliance-check/) · [live](https://agents.kiteworks.com/catalog/cmmc-compliance-check) |
| Contract Radar | `1.1.1` | [`./contract-radar/`](./contract-radar/) · [live](https://agents.kiteworks.com/catalog/contract-radar) |
| Document Summarizer | `0.6.1` | [`./document-summarizer/`](./document-summarizer/) · [live](https://agents.kiteworks.com/catalog/document-summarizer) |
| DORA Compliance Check | `1.2.2` | [`./dora-compliance-check/`](./dora-compliance-check/) · [live](https://agents.kiteworks.com/catalog/dora-compliance-check) |
| DPDPA Compliance Check | `1.2.2` | [`./dpdpa-compliance-check/`](./dpdpa-compliance-check/) · [live](https://agents.kiteworks.com/catalog/dpdpa-compliance-check) |
| Duplicate Finder | `0.6.1` | [`./duplicate-finder/`](./duplicate-finder/) · [live](https://agents.kiteworks.com/catalog/duplicate-finder) |
| EAR Compliance Check | `1.2.2` | [`./ear-compliance-check/`](./ear-compliance-check/) · [live](https://agents.kiteworks.com/catalog/ear-compliance-check) |
| EU AI Act Compliance Check | `1.2.2` | [`./eu-ai-act-compliance-check/`](./eu-ai-act-compliance-check/) · [live](https://agents.kiteworks.com/catalog/eu-ai-act-compliance-check) |
| FedRAMP Compliance Check | `1.2.2` | [`./fedramp-compliance-check/`](./fedramp-compliance-check/) · [live](https://agents.kiteworks.com/catalog/fedramp-compliance-check) |
| Folder Expiry Audit | `0.3.1` | [`./folder-expiry-audit/`](./folder-expiry-audit/) · [live](https://agents.kiteworks.com/catalog/folder-expiry-audit) |
| GDPR Compliance Check | `1.2.2` | [`./gdpr-compliance-check/`](./gdpr-compliance-check/) · [live](https://agents.kiteworks.com/catalog/gdpr-compliance-check) |
| HIPAA Compliance Check | `1.2.2` | [`./hipaa-compliance-check/`](./hipaa-compliance-check/) · [live](https://agents.kiteworks.com/catalog/hipaa-compliance-check) |
| Inbox Triage | `0.6.1` | [`./inbox-triage/`](./inbox-triage/) · [live](https://agents.kiteworks.com/catalog/inbox-triage) |
| Intake Form Builder | `0.2.0` | [`./intake-form-builder/`](./intake-form-builder/) · [live](https://agents.kiteworks.com/catalog/intake-form-builder) |
| Invoice Organizer | `0.6.1` | [`./invoice-organizer/`](./invoice-organizer/) · [live](https://agents.kiteworks.com/catalog/invoice-organizer) |
| ISM (Australia) Compliance Check | `1.2.2` | [`./ism-au-compliance-check/`](./ism-au-compliance-check/) · [live](https://agents.kiteworks.com/catalog/ism-au-compliance-check) |
| ISO 27001 Compliance Check | `1.2.2` | [`./iso27001-compliance-check/`](./iso27001-compliance-check/) · [live](https://agents.kiteworks.com/catalog/iso27001-compliance-check) |
| ISO 27701 Compliance Check | `1.2.2` | [`./iso27701-compliance-check/`](./iso27701-compliance-check/) · [live](https://agents.kiteworks.com/catalog/iso27701-compliance-check) |
| ISO 42001 Compliance Check | `1.2.2` | [`./iso42001-compliance-check/`](./iso42001-compliance-check/) · [live](https://agents.kiteworks.com/catalog/iso42001-compliance-check) |
| ITAR Compliance Check | `1.2.2` | [`./itar-compliance-check/`](./itar-compliance-check/) · [live](https://agents.kiteworks.com/catalog/itar-compliance-check) |
| LGPD Compliance Check | `1.2.2` | [`./lgpd-compliance-check/`](./lgpd-compliance-check/) · [live](https://agents.kiteworks.com/catalog/lgpd-compliance-check) |
| Naming Cleanup | `0.6.1` | [`./naming-cleanup/`](./naming-cleanup/) · [live](https://agents.kiteworks.com/catalog/naming-cleanup) |
| NIS2 Compliance Check | `1.2.2` | [`./nis2-compliance-check/`](./nis2-compliance-check/) · [live](https://agents.kiteworks.com/catalog/nis2-compliance-check) |
| NIST AI RMF Compliance Check | `1.2.2` | [`./nist-ai-rmf-compliance-check/`](./nist-ai-rmf-compliance-check/) · [live](https://agents.kiteworks.com/catalog/nist-ai-rmf-compliance-check) |
| NIST CSF Compliance Check | `1.2.2` | [`./nist-csf-compliance-check/`](./nist-csf-compliance-check/) · [live](https://agents.kiteworks.com/catalog/nist-csf-compliance-check) |
| NIST SP 800-53 Compliance Check | `1.2.2` | [`./nist-800-53-compliance-check/`](./nist-800-53-compliance-check/) · [live](https://agents.kiteworks.com/catalog/nist-800-53-compliance-check) |
| NZISM Compliance Check | `1.2.2` | [`./nzism-compliance-check/`](./nzism-compliance-check/) · [live](https://agents.kiteworks.com/catalog/nzism-compliance-check) |
| Offboarding Content Finder | `0.6.1` | [`./offboarding-content-finder/`](./offboarding-content-finder/) · [live](https://agents.kiteworks.com/catalog/offboarding-content-finder) |
| PCI DSS Compliance Check | `1.2.2` | [`./pci-dss-compliance-check/`](./pci-dss-compliance-check/) · [live](https://agents.kiteworks.com/catalog/pci-dss-compliance-check) |
| Redactor | `0.6.1` | [`./redactor/`](./redactor/) · [live](https://agents.kiteworks.com/catalog/redactor) |
| Retention Sweeper | `1.1.1` | [`./retention-sweeper/`](./retention-sweeper/) · [live](https://agents.kiteworks.com/catalog/retention-sweeper) |
| Section 508 Compliance Check | `1.1.2` | [`./section-508-compliance-check/`](./section-508-compliance-check/) · [live](https://agents.kiteworks.com/catalog/section-508-compliance-check) |
| Sensitive Content Scanner | `1.4.1` | [`./sensitive-content-scanner/`](./sensitive-content-scanner/) · [live](https://agents.kiteworks.com/catalog/sensitive-content-scanner) |
| Sharing Auditor | `1.2.1` | [`./sharing-auditor/`](./sharing-auditor/) · [live](https://agents.kiteworks.com/catalog/sharing-auditor) |
| SOC 2 Compliance Check | `1.2.2` | [`./soc2-compliance-check/`](./soc2-compliance-check/) · [live](https://agents.kiteworks.com/catalog/soc2-compliance-check) |
| Storage Visualizer | `1.1.1` | [`./storage-visualizer/`](./storage-visualizer/) · [live](https://agents.kiteworks.com/catalog/storage-visualizer) |
| Vietnam PDPL Compliance Check | `1.2.2` | [`./vn-pdpl-compliance-check/`](./vn-pdpl-compliance-check/) · [live](https://agents.kiteworks.com/catalog/vn-pdpl-compliance-check) |
| WCAG Compliance Check | `1.1.2` | [`./wcag-compliance-check/`](./wcag-compliance-check/) · [live](https://agents.kiteworks.com/catalog/wcag-compliance-check) |

</details>

## Licence and export

- Agent source code in this repository is licensed under the **Apache License 2.0** — see [`LICENSE`](./LICENSE). That licence governs your rights in this code. Third-party components a plugin imports are covered by their own licences.
- These plugins are prompt and script bundles with no cryptographic functionality of their own: **EAR99**, no encryption-related filing.
- Use of the agents and this repository is subject to U.S. export control and sanctions law, including the EAR and OFAC sanctions programs.

## What's in this repo

- `.claude-plugin/marketplace.json` — the marketplace catalog (`kiteworks-lite`).
- `LICENSE` — Apache License 2.0.
- `<agent>/` — the plugin directory (skills, agents, connector setup, per-agent README).
- `<agent>.plugin` and `<agent>.zip` — single-plugin bundles (identical bytes; `.zip` works around a Claude Desktop uploader that rejects `.plugin`).

## Notes

- Bundles are **unsigned** in this interim; install-source integrity rests on repository controls (branch protection on the published repo) until signed bundles land.

---
*Generated from the `kiteworks-agent-marketplace-lite` source — do not edit by hand; changes are overwritten on publish.*
