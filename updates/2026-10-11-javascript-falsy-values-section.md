# 2026-10-11 — JS page: falsy values section (+ two HTML bugs fixed)

## What was added

File: `findtorontoevents.ca/servicenow/javascript/index.html`
Section 12 (ES6+ in ServiceNow) — new subsection **`#js-falsy` — "Falsy values
— the complete list (and the traps)"**.

Content (from the supplied brief, plus a ServiceNow-specific angle):

1. **The 8 falsy values** table: `false`, `0`, `-0`, `0n` (BigInt zero), `""`,
   `null`, `undefined`, `NaN` — with types and descriptions.
2. **Browser footnote**: deprecated `document.all` is also treated as falsy
   (not applicable on the ServiceNow server).
3. **"What is NOT falsy"** table — `[]`, `{}`, `" "`, `"false"` all evaluate to
   `true`, with the reason each bites.
4. **ServiceNow trap callout**: a `GlideElement` is an object and always truthy —
   `if (gr.short_description)` is always true; use `.nil()` or
   `getValue('field')`. Also notes `getValue()` returns `""` (falsy) for empty
   fields but `undefined` only for bad field names.
5. **`Boolean()` / `!!` coercion** code card.
6. **`??` vs `||` comparison** (`.anti` / `.good`) — `||` loses valid `0`/`""`,
   `??` only falls back for null/undefined, with the rule of thumb (and the
   ES12-mode requirement for `??`).
7. 5-question **knowledge check**.

## Bugs fixed along the way (both pre-existing from earlier edits)

- A **stray, unclosed `<div class="notice">`** at the start of the "Modern
  JavaScript ↔ ServiceNow" bridge subsection (left over from the prior
  insertion, which had also eaten the opening tag of the "Scoped App
  Requirement" notice).
- The **"Scoped App Requirement" notice** was missing its `<div class="notice">`
  wrapper.
- The **ES6-bridge knowledge-check block** was missing its closing `</div>`
  (the falsy insert had landed before it).

Result: the `<section id="es6">` div tree and the **whole document** now
balance to depth 0 (verified by masking `<pre>`/`<code>` samples so literal
markup inside examples isn't miscounted).

## Verification

- Div-balance: es6 section depth 0; whole-document depth 0.
- Rendered (headless): `#js-falsy` present, the 8-row falsy table + 4-row
  NOT-falsy table render, the `??`/`||` comparison renders, knowledge checks
  now total 25; **zero `pageerror` events**.
- Live after deploy: the four new markers ("Falsy values — the complete list",
  "What is NOT falsy", "nullish coalescing", "Knowledge check — Falsy values")
  are all present.

Deployed with `python3 upload_javascript.py`.
