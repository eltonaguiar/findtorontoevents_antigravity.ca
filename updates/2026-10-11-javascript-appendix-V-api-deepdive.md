# 2026-10-11 — Appendix V: Verified API Deep-Dive & Gotchas (bulk doc harvest)

## What was done

Harvested a large corpus of **real ServiceNow documentation** via the
FluidTopics content API (skill: `research/servicenow-docs-api`) and mined it for
authoritative API details, then added them to the JavaScript reference page.

Corpus fetched (23 curated pages, ~500 KB) + a full topic index across 160
English Zurich maps (saved `/tmp/sndocs/_topics_index.json`).

## Key findings integrated (all quoted/paraphrased from the docs)

### GlideRecord method gotchas
- **`setLimit()` implicitly calls `chooseWindow()`** → combining them can
  overwrite the window (`setLimit` wins if `chooseWindow` was called first).
  Also `setLimit` stops the `COUNT(*)`, so `setNoCount()` becomes unnecessary.
- **`getRowCount()`** — docs explicitly say to use `GlideAggregate` instead
  when you only need a count.
- **`setNoCount()`** — `chooseWindow()`/`getRowCount()` trigger a `COUNT(*)`
  that "can be slow on tables with a million+ records" (KB0817996).
- **`updateMultiple()`** — no multiple journal entries; `glide.db.forced.chunk.threshold`
  chunks large updates.
- **`deleteMultiple()`** — does **not** delete attachments; **do not use on
  tables with currency fields**; and **`setLimit()` does NOT limit it** (it
  deletes every record the query returned). Genuine data-loss trap.
- **`setWorkflow(false)`** — docs' warning: disabling BRs/script engines/audit
  "can have a significant impact… thoroughly test"; ignored for cascade delete.
- **`addEncodedQuery()`** — **an invalid query is silently partially applied**
  and "may return all records" (data-exposure/data-loss risk;
  `glide.invalid_query.returns_no_rows=true`).

### GlideAggregate
Full aggregate set: `COUNT, SUM, AVG, MIN, MAX, STDDEV, GROUP_CONCAT,
GROUP_CONCAT_DISTINCT`. Gotchas: currency fields use the **reference-currency
value**; on-prem needs DB time zone GMT/UTC; `groupBy()` callable repeatedly
for multi-group.

### g_form (GlideForm)
Docs' own guidance: **`setVisible()` and `setReadOnly()` → "use a UI Policy
instead whenever possible."** Also: `getValue()` supports MRVS via
`JSON.parse(...)`; `getReference(f, cb)` is async with a callback;
`addErrorMessage()` shows ~4s (not configurable).

### Client scripts
Docs: **"not a security measure… use ACLs or data policies."** They run on
forms/search pages, **not lists** (except `onCellEdit()`) and **not on mobile**;
strict mode by default.

### Business rules
Docs: they're a **"classic"** scripting solution — **"Use Workflow Studio for
any new process automation."**

### Debugging toolkit
System Dictionary, System Log, Debug Business Rule (Session Debug),
`gs.addInfoMessage()`, break scripts into pieces, watch table inheritance.

## Where it went

- **New Appendix V — "Verified API Deep-Dive & Gotchas"** (id
  `appendix-api-deepdive`): GlideRecord methods table, GlideAggregate set +
  example, g_form table, client-script restrictions, business-rule stance,
  debugging toolkit, and a 7-question knowledge check.
- **Folded into the existing GlideRecord section (2.2 Encoded Queries)**: a
  `notice` on the silent invalid-encoded-query trap.
- TOC entry "V. Verified API Deep-Dive"; badge bumped to
  "28 sections + 23-part appendix".

## Verification

- 52 TOC links resolve; 23 appendix sections; 22 knowledge-check blocks.
- Zero `pageerror` events locally and live.
- Live page carries `appendix-api-deepdive`, `setNoCount`, `GROUP_CONCAT`,
  and the silent-failure notice (8 matching strings).
- Deployed with `python3 upload_javascript.py`.

## Sources (Zurich release)

GlideRecord – Scoped / Global / Client; GlideAggregate – Scoped / Global;
GlideAjax – Client; GlideForm (g_form) – Client; Classic Business rules;
Client scripts; Client-side scripting / use cases; UI scripts; Instance Scan
(+ using/roles/checks); Data policy; Assignment rules; Scheduled jobs;
Flow action; custom email subflow. Method: `research/servicenow-docs-api`.

## Notes / limits

- All facts pinned to **Zurich** (the docs' current default release).
- No copyrighted doc text was bulk-copied into the page — the docs were used to
  **verify**, with short quotes as citations and the rest written in our own words.
- No personal contact details (phone numbers, meeting IDs, etc.) were added to
  the page.
