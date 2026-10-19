# 2026-10-11 — JS page: gr.get() both overloads documented

## What was added

File: `findtorontoevents.ca/servicenow/javascript/index.html`, in the
"Common gotchas" subsection (section 12, `#js-gotchas`), a new block
**"A.1 gr.get() — both overloads, in full"**:

- **One parameter (by sys_id)** — runnable example:
  `if (gr.get('a1b2c3…')) { gs.info(gr.short_description); }`, plus the docs
  reminder that a single arg falls back to matching the **display value**.
- **Two parameters (fieldName, value)** — runnable example:
  `if (gr.get('number', 'INC0001234')) { gs.info(gr.priority); }`.
- **Multiple-match caveat** (docs): *"If multiple records are found, the first
  record is used."* → when the value isn't unique, use `addQuery()` +
  `setLimit(1)` + `query()` instead, shown inline.
- Updated the `gr.get()` **knowledge-check answer** to name both overloads.

## Verification

- Rendered (headless): "both overloads", `gr.get('a1b2c3d4e5f6g7h8i9j0')`, and
  `gr.get('number', 'INC0001234')` all present; **zero `pageerror` events**.
- Whole-document div depth = 0.
- Live after deploy: all four markers present ("both overloads",
  `gr.get('a1b2c3d4e5f6g7h8i9j0')`, `gr.get('number', 'INC0001234')`,
  "first record is used").

Deployed with `python3 upload_javascript.py`.
