# JS guide: ECMAScript feature coverage audit (ServiceNow scope)

**Date:** 2026-10-13
**Files changed:** `findtorontoevents.ca/servicenow/javascript/index.html`, `findtorontoevents.ca/servicenow/javascript/js-essentials.html`

## Why

Cross-checked every concept in the ServiceNow community article
["ECMAScript Features Supported in ServiceNow: A Comprehensive Overview"](https://www.servicenow.com/community/developer-articles/ecmascript-features-supported-in-servicenow-a-comprehensive/ta-p/2606145)
against our JavaScript guides (`index.html` §12 "ES6+ in ServiceNow" and the
`js-essentials.html` companion) and closed the gaps.

## What was missing

Grep audit of the 17 concepts in the article's feature list:

| Concept | index.html §12 (before) | js-essentials.html |
|---|---|---|
| Arrow functions | ✅ | ✅ |
| Block-scoped `let`/`const` | ✅ | ✅ |
| Template literals | ✅ | ✅ |
| Destructuring | ✅ | ✅ |
| Spread operator | ✅ | ✅ |
| Classes | ✅ (table row only) | ✅ |
| **Inheritance (`extends`/`super()`)** | ❌ no ES6 class code at all | row mentions it, no example |
| Modules | ✅ (SDK row) | ✅ |
| Promises | ✅ | ✅ |
| Default parameters | ✅ | ✅ |
| Rest parameters | ✅ | ✅ |
| **Object literal extensions (shorthand)** | ❌ | ✅ (row was named "Shorthand & computed keys") |
| **Enhanced object properties (method shorthand, computed keys)** | ❌ | ✅ |
| Async/await | ✅ | ✅ |
| **`Symbol` type** | ❌ (0 matches) | ✅ |
| Set and Map | ✅ | ✅ |
| Optional chaining `?.` | ✅ | ✅ |
| Nullish coalescing `??` | ✅ | ✅ |

Three concepts had **no ServiceNow support-status row** in the feature
reference table and no coverage at all in the main guide: object-literal
extensions / enhanced object properties, `Symbol`, and ES6 class inheritance.

## What was changed

`index.html` §12:

1. ES12 language-level cell now lists `extends`/`super`, object-literal
   shorthand & computed keys, and `Symbol`.
2. **Feature reference (ES12 mode)** table split/extended so every article
   concept maps to its own row: arrow functions · block-scoped `let`/`const` ·
   template literals · destructuring/rest/spread/default params · object-literal
   extensions & enhanced object properties · classes & inheritance ·
   Map/Set + optional chaining + nullish · `Symbol` · Promise/async ·
   Proxy/generators · ES modules. Verdicts: `Supported` in ES12 mode,
   `Not Supported` in ES5 Standards mode; `Promise`/`async` remain `Disallowed`
   in ES5 (matches the official matrix).
3. Added **example card 6 — ES6 Classes & Inheritance** (`class`,
   `extends`, `super()`) with an `EscalationPolicy` → `PriorityEscalation`
   worked example, plus the caution that GlideAjax-callable Script Includes
   still use the legacy `Class.create()` / `Object.extendsObject(...)` /
   `type:` wiring until verified on-instance.

`js-essentials.html` §6 table:

4. Renamed the shorthand row to **"Object-literal extensions + enhanced
   object properties"** and spelled out all three forms
   (`{ name, age, greet() {}, [key]: v }`).
5. Renamed the classes row to **"Classes & inheritance"** and added an inline
   `class Dog extends Animal { constructor(n) { super(n); } }` example with the
   `super()`-before-`this` rule.

## Not changed (already correct)

The article's 2023 "not supported" verdicts for **Promises, async/await and
modules are now outdated** — our guide already reflects the current platform
state (supported in ES12 mode, `Disallowed` only in ES5 Standards; ES modules
available via the ServiceNow SDK in scoped apps). Global-vs-scoped has been
superseded by per-application/per-script JavaScript mode, which §12 already
documents (Tokyo → Xanadu release history).

## Verification

- HTML tag-balance parse of both files: **0 errors, 0 unclosed tags**.
- Section-12 probe script: **all 18 concepts present, 0 missing**.
- `node --check` on the new example-6 snippet: **syntax OK**.
- Playwright smoke (headless Chromium, `file://` load of both pages):
  **SMOKE PASS** — every concept probe found in rendered DOM,
  0 page errors, 0 px horizontal overflow (`index.html`: 487 table rows,
  22 API cards).
