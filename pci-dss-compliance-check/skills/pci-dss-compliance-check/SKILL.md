---
name: pci-dss-compliance-check
description: >
  Use when the user asks to check Kiteworks content against PCI DSS --
  trigger phrases include `PCI DSS` `cardholder data` `CDE` `SAQ` `PAN` `tokenisation`. Scans and, on confirmation,
  writes a CSV + txt/pdf report. Single-phase: no separate "apply" step
  to ask for. Fit tier: Good -- see below for what this can and can't
  actually check.
metadata:
  version: "0.4.1"
---

Delegate to the `pci-dss-compliance-check` subagent on surfaces that support it (Claude Code, Cowork). If it reports no tools or fabricates results without tool calls, discard and check the `Kiteworks` connector. On other surfaces, follow this skill directly.

# PCI DSS Compliance Check -- fit tier: Good

Read `../compliance-mapping/SKILL.md` first for the shared mechanism (signals A/B/C/D, report shape, honesty framing) -- this skill only supplies framework-specific content, never its own scanning logic.

## What PCI DSS actually is

The payment card industry's data security standard for any organization that stores, processes, or transmits cardholder data.

## Signals this agent runs

Signals: **A, B, C**. Signal A's default term list for this framework: "cardholder data", "primary account number", "PAN", "CVV", "card verification" (plus the built-in PII/secret presets, plus anything the user adds). Signal C's retention threshold: **ask the user** -- Requirement 3.2.1 requires a documented cardholder-data retention/disposal policy but deliberately states no fixed number of its own (see below); this is bucket 2 of the general Signal C policy in `../compliance-mapping/SKILL.md`, the same pattern as GDPR.

## Control citations

Drawn directly from PCI DSS v4.0 (PCI Security Standards Council, March 2022), not the third-party GRC skill library.

- **Signal A** (sensitive-content exposure): Requirement 3 ("Protect Stored Account Data") sub-requirements 3.3 (do not store sensitive authentication data after authorization) and 3.4 (restrict access to PAN wherever it is stored) govern any cardholder-data-shaped content this signal finds.
- **Signal B** (sharing exposure): Requirement 3.5 (PAN is secured wherever it is stored, including in files sent outside the cardholder data environment) is the closest direct match for a file in a shared folder tree containing card data.
- **Signal C** (retention, ask-the-user): Requirement 3.2.1 ("Account data storage is kept to a minimum") requires organizations to implement a documented data retention and disposal policy that "limits data storage amount and retention time to that which is required for legal or regulatory, and/or business requirements," including a defined retention period with documented business justification, and a process for verifying at least every three months that data past its retention period has been securely deleted. PCI DSS itself states no fixed retention number here -- the standard requires *a* documented policy, not a specific duration -- so this scan asks the user for their own stated cardholder-data retention period rather than inventing one, per the general Signal C policy's bucket 2.
- **Considered and deliberately excluded: Requirement 10.5.1** (audit log history retained for at least 12 months) does state a fixed number, but it's a retention *floor* (keep logs for at least this long so they exist if needed), not a *ceiling* Signal C can check (flag a file once it's older than a threshold) -- see `../compliance-mapping/SKILL.md`'s floor-vs-ceiling policy. A file scan cannot detect logs that were deleted too early, so this requirement has no meaningful implementation here and correctly stays out of scope.

## What this doesn't check

Network segmentation, tokenization architecture, the SAQ/ROC process, quarterly vulnerability scanning, and audit-log retention (Requirement 10.5.1 -- a retention floor, not something a file-age check can verify) are outside file-scan visibility -- this only flags where card-data-shaped content (the built-in Luhn-validated credit-card pattern) appears to live, is shared, or is older than the user's own stated cardholder-data retention policy. It also cannot see who a shared folder is shared with, or whether they are internal or external; directly shared files, and any sharing set above the top-level folder visible to the scanning user, are not detected.

## Recommended next steps

- Complete the applicable SAQ or engage a QSA for a full Report on Compliance (ROC) -- this scan is not a substitute.
- Verify network segmentation actually isolates the cardholder data environment from the rest of the network.
- Confirm quarterly ASV vulnerability scans are current for any system holding flagged card data.
- Verify a documented cardholder-data retention and disposal policy actually exists and matches what this scan found in practice, including the Requirement 3.2.1 quarterly deletion-verification process -- this scan's age check is a proxy for "past your own stated policy," not proof the required disposal process is actually running.
- Confirm audit-log retention (Requirement 10.5.1, at least 12 months) separately -- this scan does not and cannot check it.

## Source

Adapted from the PCI DSS skill in the Claude Skills for Governance, Risk & Compliance library (`Sushegaad/Claude-Skills-Governance-Risk-and-Compliance`) -- <https://sushegaad.github.io/Claude-Skills-Governance-Risk-and-Compliance/> -- which offers much deeper advisory capability (policy/document drafting, licensing walkthroughs, breach-notification procedures) than a content-governance scan can ever provide.
