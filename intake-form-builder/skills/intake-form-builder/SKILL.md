---
name: intake-form-builder
description: >
  Use when the user wants to build a Kiteworks intake/request form —
  trigger phrases include "build a form to collect X," "create an
  intake form for [purpose]," or "make a Kiteworks form for vendor
  onboarding/RFP responses/document collection." Direct action, not a
  preview/apply pair — the underlying tool requires an HTML preview and
  explicit user approval before anything is created.
metadata:
  version: "0.1.0"
---

Delegate to the `intake-form-builder` subagent, or follow this directly.

# Intake Form Builder

Confirmed live: `get_create_form_schema` returns a full field-type schema — `textContent`, `text`, `textarea`, `radio`, `checkbox`, `select`, `number`, `name`, `email`, `file`, `termsOfService`, `date`, `time`. This is real and rich enough for genuine use cases: vendor onboarding, security-questionnaire intake, signed-document collection (with a `termsOfService`/acknowledgment field plus a `file` upload field), RFP response collection, and so on.

## Workflow (do not skip steps)

1. **Discovery — don't skip to drafting fields on a vague brief.** If the user's request doesn't already answer these, ask before drafting anything:
   - **Purpose**: what is this form for (vendor onboarding, RFP response collection, signed-document/NDA collection, security questionnaire intake, a general request form, something else)? This shapes everything downstream.
   - **Audience**: internal team, or an external vendor/client/partner? External forms usually want a `name` + `email` field up front and plainer language; internal ones can assume more context.
   - **What information, field by field**: for each piece of information, ask (or infer and confirm) which field type fits — short answer (`text`), longer answer (`textarea`), a single choice (`radio`/`select`), multiple choice (`checkbox`), a number, a date, or a time. Don't default everything to free text if a structured type fits better — structured fields make the collected data far more usable afterward.
   - **File upload**: does this form need to collect a document (a signed contract, a completed questionnaire, a certificate)? If so, a `file` field is needed — ask what kind of document, so the field's label/instructions can say so.
   - **Acknowledgment / terms**: does the submitter need to accept something (an NDA, terms of service, a data-handling notice) before submitting? That's the `termsOfService` field type — ask if this applies rather than assuming it doesn't.
   - **Required vs. optional**: confirm which fields are must-answer (`isRequired: true`) vs. nice-to-have.
   - If the user says "whatever you think is best" for any of the above, propose a specific, sensible default explicitly and get a quick confirmation rather than silently deciding.
2. Call `get_create_form_schema` (or reuse the schema already known from this skill) to confirm field types available.
3. Draft the field list from the discovery answers.
4. **Required by the tool itself**: build a complete, neutrally-styled HTML preview of the form and show it to the user for review. Do not call `create_form` before this step.
5. Only after explicit user approval, call `create_form` with the approved `name` and `fields`.
6. Report the returned editor link back to the user plainly.

## Notes

- Field labels/instructions are capped at 500 characters, form name at 70 characters — check before submitting, don't let the call fail on a length limit.
- This is a direct-action skill, not part of the preview/apply pattern used elsewhere in this plugin — the tool's own mandatory preview-then-approve flow already provides the safety gate that preview/apply provides elsewhere.
- **Confirmed live** (with a genuine user-approved test form, not a fake scenario): `create_form` works exactly as documented across five field types tested at once (`name`, `email`, `select`, `file`, `termsOfService`), all accepted without error.
- **Two things the docs don't tell you, confirmed live:** (1) the created form is NOT filed under this plugin's `My Folder/Agents/` convention — Kiteworks stores it itself at `My Folder/Advanced Forms MCP/<name>.json`, outside your control; don't try to redirect it. (2) the returned `url` is a distinct editor link shape, `https://<tenant>/advancedform/gateway/app/load-from-json/<id>` — not the `/web/file/<id>` pattern `folder-scan` uses elsewhere. Report this URL back to the user exactly as returned; never reconstruct or guess this link format.
