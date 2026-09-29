---
name: kw-pdf-report
description: >
  Shared internal reference skill, not invoked by users directly.
  report-export reads this file for the standard way to build a
  Kiteworks-branded, overlap-safe PDF report. Read this before writing
  or modifying report-export's PDF generation step, or any skill that
  builds a table inside a PDF.
metadata:
  version: "0.6.0"
---

# kw-pdf-report — shared branded PDF builder

The branded PDF requires `upload_file_from_path` on the resolved Kiteworks connector; when `connector-probe` reports it missing, do not attempt the PDF and use the report-export CSV + text path.

This skill's token table below is self-contained — it works standalone even where `kw-brand-visual` isn't installed, which matters since this plugin ships and installs independently of that skill. `kw-brand-visual` (a separate, marketing-owned skill, not bundled in this plugin) is the canonical source if you ever want to double-check a token value is still current; if it happens to be installed in the same environment, cross-check there directly by name, but never reference it via a `../<name>/SKILL.md`-style relative path — this plugin's build script auto-vendors anything referenced that way, and `kw-brand-visual` isn't part of this plugin's source tree to vendor. This skill adapts those tokens for a printed, light-background report rather than the dark web/deck canvas they were designed for.

## Why this exists as its own skill

Every agent's apply/save step needs to produce a PDF via `report-export`. Without a shared builder, each agent would hand-roll its own reportlab code — inconsistent branding, and each one re-discovering the same table-overlap bug independently. One shared script fixes both at once.

## Use the script, don't hand-roll reportlab tables

Run `scripts/branded_pdf.py` (via `Bash`) rather than writing ad hoc `reportlab` calls. It exposes:

- `build_branded_pdf(output_path, agent_name, report_title, sections, metadata, scope_caveat, fit_tier=None, operational_status=None, scope=None, limitations=None, recommended_next_steps=None)` — a full document: a full-bleed dark hero band holding **only** the real logo and an agent-name label (nothing else — no title, no folder name), then in the body: the descriptive `report_title` as a heading, optional **fit-tier / operational-status badge chips** right below it, a "Report details" block built from `metadata` (who ran it, what was scanned, when, coverage — with clickable links where relevant), an optional **Scope note box** (what was actually scanned, file types read vs. skipped, retention cutoff, which signals ran), one or more findings sections (each a heading + either a paragraph or a table), optional **Limitations** and **Recommended Next Steps** note boxes after the findings, and a fixed legal footer (injected from the marketplace install disclaimer on every publish) with page numbers.
- **`scope_caveat` is required for every PDF.** Pass the exact per-agent scope caveat from `report-export`; callers cannot supply or suppress the legal layer.

## Build the PDF: Write the spec, then `build --json-file`

This is the one supported flow, and it keeps report text out of the shell
entirely. Report text pushed through a shell fails in a few repeatable ways: a
heredoc chokes on an apostrophe or an unbalanced quote, `<`/`>` get stripped to
dodge shell quoting (one delivered report said "html lang attribute" instead of
the literal `<html lang>`), a non-ASCII em dash or curly quote mangles the file
encoding, or the Windows command-length limit forces a script into pieces. Any
one of them can quietly change what the report says.

**The rule: never write .py helper files, and never generate report text through
heredocs, `printf` or a Python one-liner.** Do not write a script that imports
this module either. Use the Write tool and this module's CLI:

1. **Pick the staging folder once per run**: `<base>/_kiteworks-report/`.
   `<base>` is a user-private local folder the Kiteworks connector can read for
   `upload_file_from_path`: the host folder `content-extract` uses as `--parent`
   when this run downloads files (on Windows, the `--long-path` output),
   otherwise the connector-readable folder you use for local files. The name
   must be exactly `_kiteworks-report`: your Write tool may only write `.json`,
   `.csv`, `.txt` and `.md` files directly inside a folder of that name, and
   every other path is refused.
2. **Write `spec.json` with the Write tool** at
   `<base>/_kiteworks-report/spec.json`: one UTF-8 JSON object shaped like the
   example below. Put report text in it exactly as it should read, with no
   manual escaping; literal `<html lang>`, apostrophes, "double quotes", an em
   dash, curly quotes and accented letters all render as written.
3. **Write the CSV with the Write tool** into the same folder
   (`<agent-name>-<YYYY-MM-DD>.csv`, see `report-export`).
4. **Build**: `python <this skill>/scripts/branded_pdf.py build --json-file
   <base>/_kiteworks-report/spec.json --out
   <base>/_kiteworks-report/<agent-name>-<YYYY-MM-DD>.pdf`. It prints one JSON
   line, `{"pdf": "<path>", "pages": <n>, "bytes": <n>, "spec_removed": true}`,
   and removes the spec it read from the staging folder (`--keep-spec` keeps
   it). A malformed spec exits 2 with one `error:` line naming the key and the
   expected shape; fix `spec.json` with the Write tool and build again (a
   failed build keeps the spec).
5. **Upload** the PDF and the CSV with `upload_file_from_path` and compare each
   response size with the local size (see `report-export`).
6. **Clean up** once you no longer need the local files, whether or not the
   upload succeeded: `python <this skill>/scripts/branded_pdf.py cleanup --dir
   <base>/_kiteworks-report`. It deletes the staged `.json`, `.csv`, `.txt`,
   `.md`, `.pdf` and `.b64` files, then the empty folder, and prints what it
   kept (anything else); report kept paths to the user.

`scope_caveat` is required and the published legal footer is fixed: no CLI flag
or spec key can override or omit it.

### spec.json: a complete example

Copy this shape; it builds as it stands. Every key is one of this module's
keyword arguments.

```json
{
  "agent_name": "Section 508 Compliance Check",
  "report_title": "Section 508 Compliance Report",
  "scan_date": "2026-09-28",
  "fit_tier": "accessibility",
  "operational_status": "operational",
  "metadata": [
    ["Folder scanned", {"text": "My Folder/Website", "url": "https://kiteworks.example.com/#/folder/123"}],
    ["Report saved in", {"text": "My Folder/Agents/Section 508 Compliance Check", "url": "https://kiteworks.example.com/#/folder/456"}],
    ["Scanned by", "Jane Doe (jane.doe@example.com)"],
    ["Generated", "2026-09-28"]
  ],
  "scope": ["12 HTML files read; 3 PDFs skipped (no text layer)."],
  "sections": [
    {
      "heading": "Summary",
      "paragraph": "4 of 12 pages lack the <html lang> attribute or a <title> element. It's the most common gap — “quick” to fix."
    },
    {
      "heading": "Flagged files",
      "table": {
        "data": [
          ["File", "Issue", "Link"],
          ["index.html", "missing <html lang>", {"text": "Open in Kiteworks", "url": "https://kiteworks.example.com/#/file/789"}],
          ["café-menu.html", "no <title> element", null]
        ],
        "col_widths_frac": [0.3, 0.4, 0.3]
      }
    }
  ],
  "limitations": ["No screen-reader test was run.", "Scripts and <canvas> content were not evaluated."],
  "recommended_next_steps": ["Add lang=\"en\" to every <html> element."],
  "scope_caveat": "Checked HTML markup only; did not render pages or test assistive technology."
}
```

The spec rules, which the build enforces:

- **Keys**: `agent_name`, `report_title`, `sections` and `scope_caveat` are
  required; `metadata`, `fit_tier`, `operational_status`, `scope`,
  `limitations`, `recommended_next_steps` and `scan_date` are optional. Any
  other key is refused. `output_path` is not a key; it comes from `--out`.
- **A section** is an object with a `heading` and a `paragraph`, a `table`, or
  both.
- **A table** is an object, never a bare list:
  `{"data": [header row, row, ...], "col_widths_frac": [...], "header": true}`.
  Every row has as many cells as the header row. `col_widths_frac` (optional)
  is one positive number per column; `header` defaults to `true`.
- **A cell**, and a `metadata` value, is text, a number, `null` (empty) or a
  link object `{"text": "...", "url": "https://..."}` (`http`, `https` or
  `mailto`). Use the link object for links; never write `<a href>` markup
  yourself. All other text is shown literally.
- **`metadata`** is a list of `[label, value]` rows; the output of
  `standard_metadata()` fits as it is. `scope`, `limitations` and
  `recommended_next_steps` are a string or a list of strings.

### Fallback for a host without the Write tool: `spec-append`

Use this only when the Write tool itself is unavailable in this host, never
because a write to another path was refused (write to `_kiteworks-report`
instead). It needs no file writes from you, because every chunk is plain-ASCII
base64:

- `python scripts/branded_pdf.py spec-append --spec <path.json.b64> --b64 <chunk>`
  appends one base64 chunk (`A-Za-z0-9+/=` only, roughly 6000 characters or
  fewer) to `<path.json.b64>`, creating the file on the first call. Call it once
  per chunk, in order; a non-base64 character is rejected with a clear error.
- `python scripts/branded_pdf.py build --spec <path.json.b64> --out <file.pdf>`
  joins the chunks, decodes them as the same UTF-8 JSON spec and builds it,
  exactly like `build --json-file`.

The base64 below decodes to a spec whose paragraph reads "12 of 340 files
flagged, including one with a <title> tag in its name." The literal `<title>`
survives untouched.

```bash
python scripts/branded_pdf.py spec-append --spec /tmp/report.json.b64 --b64 "eyJhZ2VudF9uYW1lIjogIlNlbnNpdGl2ZSBDb250ZW50IFNjYW5uZXIiLCAicmVwb3J0X3RpdGxlIjogIlNlbnNpdGl2ZSBDb250ZW50IFNjYW4gUmVwb3J0IiwgInNlY3Rpb25zIjogW3siaGVhZGluZyI6ICJTdW1tYXJ5IiwgInBhcmFncmFwaCI6ICIxMiBvZiAz"
python scripts/branded_pdf.py spec-append --spec /tmp/report.json.b64 --b64 "NDAgZmlsZXMgZmxhZ2dlZCwgaW5jbHVkaW5nIG9uZSB3aXRoIGEgPHRpdGxlPiB0YWcgaW4gaXRzIG5hbWUuIn1dLCAic2NvcGVfY2F2ZWF0IjogIlNjYW5uZWQgZmlsZSBuYW1lcyBhbmQgY29udGVudHMgb25seTsgZGlkIG5vdCBldmFsdWF0ZSBwZXJtaXNzaW9ucy4ifQ=="
python scripts/branded_pdf.py build --spec /tmp/report.json.b64 --out /tmp/report.pdf
# {"pdf": "/tmp/report.pdf", "pages": 1, "bytes": 4821}
```

## Badges and note boxes — added 2026-07-14 for the `*-compliance-check` family, usable by any agent

Two new, optional, brand-consistent building blocks, added to close a real gap: reports could describe a fit tier or a "what this doesn't check" paragraph in the *skill's own documentation*, which a report reader never sees. Now they render directly in the PDF.

- **`fit_tier`** (`"strong"|"good"|"light"|"accessibility"|"minimal"`, case-insensitive) and **`operational_status`** (`"operational"|"partially operational"|"not yet operational"`) each render as a small chip right under the report title. Fit tier always uses the neutral Mist-background/Electric-Indigo-text/Electric-Indigo-outline treatment (same visual language as table headers). Operational status uses the same neutral treatment for "Operational," but switches to a Signal Gold fill for "Partially operational" / "Not yet operational" — the brand's own secondary accent, used here exactly the way `visual-foundations.md` scopes it ("sparingly," an attention case), so an agent that isn't fully working yet visually stands out from one that is, without inventing a new warning color the brand doesn't have.
- **`scope`, `limitations`, `recommended_next_steps`** (each a string or a list of bullet strings) render as a matched set of left-rule note boxes (`_note_box()` — a single-cell table with a 2.5pt Electric Indigo `LINEBEFORE` rule and a `--bg-paper-soft` fill, since reportlab has no native "bordered callout" flowable). `scope` renders once, right after "Report details," before any findings. `limitations` and `recommended_next_steps` render in that order, immediately after all findings sections, before the required scope caveat. The legal layer is fixed in every page footer and is not a caller argument. Passing a list (not a single string) is preferred whenever there's more than one distinct point — the box renders each item as its own bulleted line rather than one run-on paragraph.

Any agent in this plugin can use these four kwargs, not just `*-compliance-check` — they're the general-purpose "here's the fit tier and here's what this run did/didn't cover" building blocks, `compliance-mapping`'s consumers are simply the first and most systematic users of all five together.

- `standard_metadata(scope_label, scope_name, scanned_by, generated_on, scope_link=None, output_folder_name=None, output_folder_link=None)` — builds the **generic** rows of the Report details block that are identical in shape across every agent in this plugin: the scope (folder/person/mailbox, whatever `scope_label` names it), where the report itself was saved, who ran it, and when. Both the scope and the output-folder rows render as real clickable Kiteworks links when a `*_link` URL is passed. Call this first, then extend the returned list with this agent's own specific rows (e.g. `[("Terms / patterns checked", "...")]` for sensitive-content-scanner, or a retention threshold, time window, person name for others) before passing the combined list to `build_branded_pdf`'s `metadata` argument. This is the formal generic-vs-agent-specific split: **generic** = scope, output location, who, when (same function, same order, every agent); **agent-specific** = whatever extra rows that one agent's SKILL.md appends.
- `safe_table(data, col_widths_frac=None, header=True)` — returns a ready-to-insert reportlab `Table` flowable. **This is the fix for cell text overlapping**: it wraps every cell's text in a `Paragraph` (via a small helper style) before handing it to `Table`, instead of passing raw strings. A cell is text, a number, `null` or a link object `{"text": ..., "url": ...}`, which renders as a real link (see the spec rules above).

**`report_title` must stay generic/branded** (e.g. "Sensitive Content Scan Report") — never put the specific folder name, date, or person in it. Those are scope-specific facts and belong in `metadata`, rendered in the Report Details block, not in the title or the hero. Rick caught the folder-in-header version of this directly ("folder name scanned should not be in header, but below").

**Corrected 2026-07-14 — the hero and the title were overlapping/redundant.** An earlier version put the agent name in the hero as an eyebrow AND put a near-identical descriptive title ("Sensitive Content Scan Report") right below it in the hero too — Rick caught the visual overlap and the redundancy directly ("'SENSITIVE CONTENT SCANNER' and 'Sensitive Content Scan Report' overlap and are very similar"). Fixed by making the hero pure brand real-estate — logo + agent-name label, nothing else, ever — and moving `report_title` into the body as the very first thing on the page, where there's no shared vertical space to fight over.

**`metadata` must always include who ran it and what it covered, and now includes real links.** At minimum, via `standard_metadata()`: folder/scope (linked), where the report was saved (linked), "Scanned by" (from `get_user_info_whoami`), "Generated" (date) — plus each agent's own scan-specific parameters (term list, PII categories, retention threshold, time window — whichever apply). Rick asked for this twice: first the who/what audit context ("the person who scanned this and what we scanned for?!"), then the actual clickable folder links ("can we generically add links to the scanned kiteworks folder and folder this report was generated in"). Links render in the brand's own `--fg-link` color (`#4D60FB`, same value as Electric Indigo); in a spec, write a link as a `{"text": ..., "url": ...}` object, never as markup.

## Why the table overlap happened, and the exact rule that prevents it

A `reportlab` `Table` does **not** word-wrap plain strings — a raw string cell only wraps if you gave it a `Paragraph` object instead, which carries its own word-wrap logic and lets the table compute a correct row height. Pass a bare string in a narrow column and long text either overflows past the column into the next one (visually "overlapping") or gets silently clipped, depending on the style. That's what happened.

**The rule, permanently:** never call `Table(data, ...)` directly with plain strings in `report-export`'s PDF step or any agent-specific PDF code in this plugin. Always go through `safe_table()`, which:

1. Wraps every cell (including header cells) in `Paragraph(text, cell_style)`, so long text wraps within its column instead of overflowing.
2. Computes `colWidths` proportional to each column's max content length when not given explicitly, and always scales the total to fit within the page's printable width (page width minus margins) — a table that's simply too wide for the page is the other common cause of visual overlap/clipping.
3. Sets `repeatRows=1` so a header row repeats correctly on page breaks instead of a table silently continuing headerless.
4. Uses a modest, consistent font size (9pt body, 9pt bold header) and generous cell padding (6pt) — cramped padding is a secondary contributor to a "text is touching the next cell" look even when wrapping is technically correct.

If a table has a genuinely long free-text column (e.g. a file path or a narrative note), pass an explicit narrower `col_widths` for the short columns (status, count, date) and let the remaining width go to that column — don't split width evenly across columns of very different natural lengths.

## Brand structure — corrected 2026-07-14 to follow kw-brand-visual's OWN documented rules, not a guess

An earlier version of this skill invented its own light-mode palette and sizes instead of reading `kw-brand-visual`'s actual print-specific rules. Rick caught this ("that PDF is not the new Kiteworks brand style"). Fixed by reading `rules/logo-usage.md`, `rules/typography.md`, and `references/colors-and-type.css` in full — not just the SKILL.md's own quick-reference table — and using exactly what they specify for printable documents:

- **Structure**: `logo-usage.md`'s documented placement rule for "Solution brief / one-pager" is "White, inline SVG, height:22px, top-left of dark hero header." That's a specific, real structural rule — a dark header band, not a plain light page throughout. `branded_pdf.py` builds that: a full-bleed `--kw-deep-space` (`#050821`) band drawn directly on the canvas (spanning the entire page width, edge to edge — a flowable placed inside the normal margins can't reach past them, which is why an earlier version wasn't actually full-bleed), holding **only** the real logo and an agent-name eyebrow label in white, with real spacing between them — then the body switches to the light paper tokens below, starting with the descriptive report title. The hero never carries the report title itself (see the correction note above).
- **Hero texture**: `visual-foundations.md`'s "Background Layers (hero surfaces)" recipe calls for "soft radial glows, blur 110-140px, blue + violet, low opacity, behind everything." `assets/hero-bg.png` is a pre-rendered static background applying exactly that recipe (blue glow behind the logo, subtle violet glow opposite), not a flat single-color rectangle. (Note: that same file explicitly scopes true glass/blur panels to "web and slides only... brief panels use flat fills only" — so the hero band gets the documented glow texture, but the body below stays flat, per that rule.)
- **Colors on the paper body**: taken from `colors-and-type.css`'s own light-theme token block (`--bg-paper: #FFFFFF`, `--bg-paper-soft: #E8EAF4` for zebra striping, `--fg-paper-1: #050821` for body text, `--border-paper: #D1D5DC` for grid lines) — not invented hex values.
- **Table header**: corrected again after Rick flagged the first fix ("still has a color kiteworks does not use") — `visual-foundations.md` says Electric Indigo is "used for glass glow and accent — never as a flat fill." A solid indigo block behind an entire header row isn't that pattern. Table headers now use `--kw-mist` (`#EFF2FF`, a documented neutral tint) as a flat background with Electric Indigo, uppercase, bold text — accent as a label color, not a giant fill — plus a 1.2pt Electric Indigo rule under the header row.
- **Sizes**: taken directly from `typography.md`'s own "Solution Brief / Print Type Scale" table (hero title ~20–28px, section title 16px, body copy 10px, small/table body 8–8.5px, eyebrow 9px) — not arbitrary point sizes.

## Logo — the real asset, not a reconstruction

The real `logo-kiteworks-white.svg` asset is rasterized (via `librsvg`/ImageMagick, high-resolution) into `assets/kw-logo-white.png` and bundled with this skill, then placed in the hero band exactly as `logo-usage.md` specifies. This follows that skill's hard rule directly: "never reconstruct the logo from shapes or text." If `assets/kw-logo-white.png` is ever missing, `branded_pdf.py` falls back to a plain "Kiteworks" text label rather than failing — but that fallback is a degraded case, not the intended output, and should prompt re-checking that the asset shipped correctly.

Never reference `kw-brand-visual` itself via a `../<name>/SKILL.md`-style relative path from this skill — this plugin's build script auto-vendors anything referenced that way, and `kw-brand-visual` isn't part of this plugin's source tree (this broke the build once already). Re-rasterizing the logo from that skill's assets is a manual, occasional step, not a runtime dependency.

## Fonts — an honest substitution, not a false claim

Brand type (Host Grotesk, Geist Mono) are web fonts loaded via a Google Fonts `<link>` — that mechanism doesn't exist in a `reportlab`-generated PDF, and this plugin doesn't bundle licensed font binaries. `branded_pdf.py` uses `Helvetica`/`Helvetica-Bold` (clean sans-serif, closest built-in match to Host Grotesk's role) for headings/body, and `Courier` for the mono/label role Geist Mono plays (table headers, metadata, eyebrows) — same structural roles as the brand system, not a pixel-identical font. State this plainly if asked whether the PDF is "on brand" — colors, layout, structure, and the real logo now all follow the documented brand system; the exact typeface substitution is the one deliberate, disclosed exception. If exact-font fidelity is ever required, that needs actual licensed TTF files bundled into this skill's assets and registered via `reportlab.pdfbase.pdfmetrics.registerFont` — a real but bigger lift, only worth doing if this substitution turns out not to be good enough in practice.
