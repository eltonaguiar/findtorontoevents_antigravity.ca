# 2026-10-11 — JS page: "Common gotchas & misconceptions" section

## What was added

File: `findtorontoevents.ca/servicenow/javascript/index.html`
Section 12 (ES6+ in ServiceNow) — new subsection **`#js-gotchas` — "Common
gotchas & misconceptions (JS + ServiceNow)"**.

Method-verified against the official ServiceNow API docs (GlideRecord – Scoped)
via the `servicenow-docs-api` skill, plus standard JS behaviour.

### A. GlideRecord return types (the headline gotcha)
Table of what each call actually returns and the misconception:
- **`gr.get()` → Boolean** (found/not found), *not* the record. One-arg form is
  treated as a sys_id and **falls back to matching the display value** if no
  sys_id matches (so `gr.get('INC0010001')` can succeed by number).
- `gr.next()` → Boolean; **fails if the table has a field named `next`** → use
  `_next()`.
- `gr.query()` → void; **fails if a field is named `query`** → use `_query()`.
- `gr.insert()` → sys_id String or `null`; `gr.update()` → sys_id (and inserts
  if absent); `gr.deleteRecord()` → Boolean; `gr.isValid()` → Boolean.

### B. Value vs display value; a GlideElement is always truthy
- `getValue()` (raw) vs `getDisplayValue()` (human-readable) — comparing them
  is a silent miss.
- `if (gr.short_description)` is always true (element object) → use `.nil()`.
- `getRefRecord()` returns an **empty GlideRecord, not null**, for empty refs.

### C. Number/value coercion traps
`"0"` truthy vs `0` falsy; `NaN !== NaN`; `parseInt` radix + silent truncation;
`==` vs `===`; `5 + '5'` concatenation.

### D. Arrays & objects
`typeof []==='object'`; `typeof null==='object'`; default sort is lexicographic
(`[10,9,1].sort()` → `[1,10,9]`); `[]===[]` false; GlideRecord isn't an iterable.

### E. ServiceNow runtime traps
Client scripts can't query (use GlideAjax); GlideAjax answers are strings;
no `window`/DOM server-side; different globals (`g_form` client vs `gs`/GlideRecord
server); `current.update()` in a before-BR; N+1 + `getRowCount()`; invalid
encoded queries partially applied; ES mode gates modern syntax; journal fields
& `changes()` in ACL scripts.

### F. Historical behaviours
`document.all` falsy; `void 0`; implicit globals in sloppy mode; hoisting vs
temporal dead zone.

Plus a 7-question knowledge check.

## Verification

- Whole-document div depth = 0 (masking `<pre>`/`<code>` samples).
- Rendered (headless): `#js-gotchas` present, 7 headings inside, `gr.get()`
  return-type content present, knowledge checks now 26, TOC 53 links resolve;
  **zero `pageerror` events**.
- Live after deploy: `id="js-gotchas"`, "Common gotchas", "GlideElement is
  always truthy", and the knowledge check all present.

Deployed with `python3 upload_javascript.py`.
