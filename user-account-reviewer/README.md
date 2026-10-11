# User Account Reviewer

`v0.1.1` · updated 2026-10-10

Lets a Kiteworks admin review the user accounts in their tenant in plain language. It builds a user roster and flags locked or unverified accounts, pending password resets and suspended accounts that still have active sessions or devices, and shows how users are spread across profiles. Where the connector returns it for your tenant, it also flags external users, dormant accounts (90 days by default), accounts that never signed in and likely wasted licences; anything it cannot read is reported as not determinable, never as zero. It also reconciles the tenant against an HR list (a CSV in a Kiteworks folder you name), and checks which profile a new hire would get. It saves an access-review PDF with an attestation page for the reviewer's sign-off, access-review.csv, and proposed-changes.csv with suggested account changes for a reviewer to decide on. It needs a Kiteworks admin account and is read-only: proposed changes are a proposal only, and nothing in your tenant is changed. It does not sync with LDAP or SCIM directories and does not run scheduled reviews. Reviewing user accounts processes personal data about your staff. Involve your data protection officer and, where one exists, your works council.

**[View on the Kiteworks Agent Marketplace →](https://agents.kiteworks.com/catalog/user-account-reviewer)** — live examples, screenshots, and full detail.

> **By installing or using this agent you accept the Kiteworks Agent Marketplace terms: https://agents.kiteworks.com/legal/marketplace-terms**

## Before you install — the short version

Kiteworks agents are intended for business and professional use. They use AI to generate their output automatically and are provided "as is", without warranty, to the maximum extent permitted by applicable law. Outputs are not professional advice and are not a compliance certification or legal determination of compliance with any framework. You are solely responsible for reviewing outputs before relying on them. No agent is FedRAMP authorized, and none are within the scope of Kiteworks' ISO 27001 certification or SOC 2 report. Installing or using any agent means you accept the full terms: https://agents.kiteworks.com/legal/marketplace-terms

[Read the full terms](https://agents.kiteworks.com/legal/marketplace-terms) · Version `2.0` · Effective 2026-08-15

## What's new

First general release. Review your Kiteworks user accounts, reconcile them with an HR list and save an access-review PDF with a sign-off page. Needs a Kiteworks admin account; read-only.

## Install

Add the marketplace once, then install this agent:

```
/plugin marketplace add https://github.com/kiteworks/claude-agent-marketplace.git
/plugin install user-account-reviewer@kiteworks-lite
```

**Claude Desktop:** download `user-account-reviewer.plugin` and upload it via **Customize → Personal plugins → Upload plugin**.

## Requires

A remote MCP connector named `Kiteworks` in your Claude organization — your Kiteworks admin provides the tenant-specific link. Without it the workflows have nothing to call.

## Try it

- “Run our quarterly user access review”
- “Which accounts are locked, unverified or waiting on a password reset?”
- “Reconcile our tenant against HR-export-2026-09.csv in HR Exports”

---
*Generated from the marketplace source — do not edit by hand; changes are overwritten on publish.*
