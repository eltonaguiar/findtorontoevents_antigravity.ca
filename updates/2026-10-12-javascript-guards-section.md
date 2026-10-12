# 2026-10-12 — JS page: §2.5 Defensive Guards (table / field / row / value)

## What was added

File: `findtorontoevents.ca/servicenow/javascript/index.html`
Section 2 (GlideRecord — CRUD Patterns) — new subsection
**`#gr-guards` — "2.5 Defensive Guards — table, field, row, value"**, placed
after `#gr-insert` (2.4) and before the closing of `#gliderecord`.

Content:

1. **Guard-order rule**: table → field → row → value. `isValid()` and
   `isValidField()` are dictionary (metadata) lookups with no DB round-trip,
   so they are cheap enough to run on every call.
2. **Guard reference table** (7 rows): table exists → `gr.isValid()`; field
   exists → `gr.isValidField('f')`; read permission → `gr.canRead()` /
   `GlideRecordSecure`; record found → `gr.next()` / `gr.get(sysId)` /
   `gr.hasNext()`; current record valid → `gr.isValidRecord()`; value empty →
   `gs.nil()` / `gr.field.nil()`; value read safely → `gr.getValue('f')`.
3. **Canonical worked example** (`CountMatches.scriptinclude`) — the supplied
   "Wreck it Ralph count" pattern with all five guard layers: `isValid()`,
   `isValidField()` ×2, `canRead()`, capped query (`setLimit(1000)`), and
   explicit zero handling.
4. **`getRowCount()` caveat notice** (best-practice correction — see below).
5. **"Does at least one match exist?" card** — `setLimit(1) + gr.next()`
   instead of counting, plus the single-record `gr.get('number', 'INC…')`
   boolean-guard form.
6. **Value-level guards card** — `getValue()` + `gs.nil()` after the row
   guard, with the "empty field vs missing field" `notice`.
7. **`try/catch` vs guard comparison** (`.anti` / `.good`) + a notice on when
   `try/catch` *is* right (JSON, REST, unexpected — cross-linked to §19).
8. **"What these guards do NOT cover"** `.danger` block: typos inside
   encoded-query strings (`glide.invalid_query.returns_no_rows=true`,
   cross-link §2.2), ACLs (cross-link §18), and rows deleted between `query()`
   and `update()`.
9. **5-question knowledge check** (page total 26 → 27 `.kcheck` blocks).

## Best-practice review of the supplied brief (what I corrected)

The brief was mostly right; three things were tightened against the official
API reference before publishing:

- **`getRowCount()` is not a true total.** The API reference states
  `getRowCount()` "may be incorrect" once `setLimit()` / `chooseWindow()` is
  used, and that **`setLimit()` also stops the `COUNT(*)`**. So the brief's
  `setLimit(1000)` + `getRowCount()` pattern yields a *capped* number
  (1000 for 40k matches) — correct as a safety cap, wrong as a total. The
  page now says so explicitly and points to **GlideAggregate** for real
  counts.
- **Permission guard added.** The brief checked table + field but never
  ACLs. Added `canRead()` / `GlideRecordSecure` (server-side `GlideRecord`
  bypasses ACLs — the page's §18 already documented this, so the guard table
  now links to it).
- **Counting when you only need yes/no.** The brief always counted; the page
  now teaches `setLimit(1) + next()` (and `gr.get()`'s boolean return) as the
  cheaper existence guard.

Confirmed accurate in the brief and kept: `isValid()` = table exists;
`isValidField()` = dictionary check, no DB hit; `gs.nil()` for
null/undefined/empty; `getValue()` preferred over `gr.field` (GlideElement
is always truthy — cross-link `#js-falsy`); `try/catch` reserved for
JSON/REST/unexpected errors.

## Verification

- **Static balance**: `<div>` depth 0 across the masked document; `section`,
  `table`, `ul` open/close counts equal. The single apparent unclosed
  `<details>` is inside a CSS comment ("click (native `<details>`, no JS)") —
  pre-existing, not markup.
- **Headless render (Playwright/Chromium)**: `#gr-guards` heading renders;
  the guard table renders with **7 rows** and headers Guard/Check/When to use
  it, positioned after the heading; 3 code cards + 2 comparison panes + 1
  danger block + 5 notices in section 2; knowledge check renders **5
  questions / 5 answers**; all cross-link targets
  (`#acl-security`, `#js-falsy`, `#error-handling`, `#glideaggregate`,
  `#gr-encoded`) resolve; **zero `pageerror` events**.
- **Regression**: `.kcheck` count 26 → 27 (only the new block added); no
  other section touched.

Not deployed: `python3 upload_javascript.py` was **not** run (FTP publish to
the live site is left for an explicit go-ahead).
