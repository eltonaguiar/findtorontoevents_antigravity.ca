# 2026-10-11 — Appendix E: documented the two update-set deploy methods + XML pitfalls

## What was requested

In the JavaScript reference page's Appendix E (Update Sets), clearly show the
**two ways to deploy** an update set:

1. **Retrieve → Preview → Commit** (connected instances)
2. **Import / upload the XML file**

…and properly document the limits of the XML method — that it can't be edited
directly, can conflict, etc. — and **why you avoid manually uploading XML**.

## What was added

File: `findtorontoevents.ca/servicenow/javascript/index.html` — section
`#appendix-update-sets`.

Three new subsections inserted after the existing step-by-step:

### "The two ways to deploy an update set"
A 2-column comparison table (Method 1 vs Method 2) across: what it is,
breadcrumb, prerequisites, whether preview is required, best-for, and risk
profile. Key points captured:
- **Method 1** (`Retrieved Update Sets → Retrieve from instance`): instances
  talk to each other; preferred default; lower risk because the source set is
  authoritative and versioned.
- **Method 2** (`Retrieved Update Sets → Import Update Set from XML`): you
  carry a `.xml` file; the only option across air-gapped / non-connected
  instances, vendors, or partners; higher risk.
- Both require **Preview → Commit**; importing alone applies nothing.

### "Method 2 in practice — importing an XML file"
A 6-step procedure: Export → carry the file → Import on target (lands as
*Retrieved*) → Preview → Commit → Verify.

### "Why you avoid hand-editing or blindly uploading XML"
A hazard table explaining the XML is an **artefact, not a source file**, with
the concrete failure modes:
- Cannot meaningfully edit by hand (escaped payloads + inter-record `sys_id`
  references; silent mis-loads).
- Conflicts / skipped records when the target's record is newer
  (`sys_update_xml` level) — the change is dropped without an error unless you
  read the preview.
- Version / release mismatch → references to fields/plugins that don't exist.
- Lost metadata & ordering → dependency sequence breaks (e.g. a table before
  its fields).
- No audit trail for a hand-carried file.
- Bypasses governance (skips connected-instance controls and often the change
  record) — looks like an out-of-band change.

Closing rule callout: export with *Export*, consume with *Import Update Set
from XML*; never open it in an editor; prefer Method 1 on connected instances;
always preview before commit.

### Supporting edit
Reworded the step-by-step "UAT" step to reference picking one of the two
methods, pointing to the new detail below.

## Verification

- **Structural (local regex):** Appendix E now has 7 `h3` headings (was 4),
  2 tables, 3 notices; the new sections parse cleanly.
- **Rendered (local, headless Chromium):** 7 `h3` in the section; the
  "Method 1 / Method 2" table is present; the hand-editing warning heading is
  present; **zero `pageerror` events**.
- **Visual:** two screenshots confirmed the two-column comparison table and the
  hazards table render cleanly on the dark theme, sidebar TOC intact.
- **Live (after deploy):** `curl` against
  https://findtorontoevents.ca/servicenow/javascript/index.html confirms
  "The two ways to deploy an update set", "Why you avoid hand-editing", the
  "Method 1 — Retrieve → Preview → Commit" / "Method 2 — Import/Upload XML
  file" headers, and the "Version / release mismatch" / "Bypasses governance"
  hazard rows are all present.

Deployed with `python3 upload_javascript.py`.

## Currency note

The exact menu labels and the `sys_update_xml` collision behaviour are described
from established platform behaviour; verify the precise menu wording against the
instance's release via docs.servicenow.com, as menu labels shift between
releases.
