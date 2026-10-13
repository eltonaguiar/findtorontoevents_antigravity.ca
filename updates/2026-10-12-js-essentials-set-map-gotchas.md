# 2026-10-12 — JS Essentials page: Set & Map gotchas section

## What was added

File: `findtorontoevents.ca/servicenow/javascript/js-essentials.html`

From the supplied Set/Map + ES6 notes brief:

1. **§7 new subsection "Set & Map gotchas"** — 7-row gotcha table:
   - `.size`, not `.length` (`.length` is `undefined`)
   - `new Map({a:1})` throws — constructor wants an iterable of pairs;
     use `new Map(Object.entries(obj))`
   - **SameValueZero** comparison: `NaN` equals itself in a Set
     (`new Set([NaN]).size === 1`), but two `{}` literals are different keys
   - No index access: `set[0]` / `map[0]` are `undefined`
   - Insertion order, not sorted order
   - Mutating while iterating (see correction below)
   - WeakSet/WeakMap object-keys-only, not iterable
   Plus a `.notice` card on Map vs plain-object lookup tables (insertion
   order, O(1) `.size`, no `Object.prototype` collisions, non-string keys
   vs `JSON.stringify`).
2. **§10 "Gotchas that fail tests" table — 3 new rows** (14 → 17):
   `new Map(obj)` → `TypeError`, `.length` on Set/Map → `undefined`,
   object keys compared by reference.

## What was already covered (not duplicated)

The brief's ES6 array-methods table (map/filter/reduce/forEach/find/
findIndex/some/every/flat/flatMap/includes), map-vs-reduce guidance, and the
ES6 syntax rundown (destructuring, spread, template literals, classes,
async/await) already exist in §2/§6 of the page and were left untouched.

## Correction to the brief

The brief said "mutating while iterating can skip items or throw in some
engines." Verified in Node 22: `delete` during `for...of` over a Set is
spec-safe and skips no survivors (`[1,2,3,4,5]` minus evens → `[1,3,5]`).
The real hazard is `add`/`set` during iteration — new items get visited
(potential infinite loop). The page states the corrected version.

## Verification

- Every behavioural claim executed in Node 22 (Map ctor TypeError message,
  `Object.entries` form, `.size` vs `.length`, SameValueZero with NaN and
  object refs, `set[0]` → undefined, insertion vs sorted order, delete/add
  during iteration, WeakMap not iterable, reduce grouping).
- Static: `<div>` balance 0 (pre/code masked), `<table>` balance 0,
  §7 gotcha table 7 data rows, §10 17 data rows (was 14).
- Headless (Playwright/Chromium): `Set & Map gotchas` h3 renders, the
  Map-vs-object notice renders, **zero `pageerror` events**.

## Follow-up 1 — cross-linking (2026-10-12)

- `index.html` (JavaScript Reference) had no link to `js-essentials.html`
  (the sibling pages all link to it). Added:
  1. An "Essentials" entry to the shared `sn-lnav` header.
  2. A link in the "If you are new to JavaScript" prereq card.
  3. A cross-link in §12 (ES6) intro pointing to the companion page for
     plain-JS material (arrays, destructuring, spread, Map/Set gotchas).
- Verified: div/section balance 0; headless nav link + 2 in-page links
  render, zero page errors. Deployed via `upload_javascript.py`; FTP size
  match 402961; live HTTP 200 with all three markers found.
- `js-essentials.html` already shares the family design system (`sn-lnav`,
  card, palette, tables) and links back to the Reference — no restyling
  needed.

## Follow-up 2 — ES6 version stars on js-interview.html (2026-10-12)

- Added an ES6+ marker: a purple superscript star `✳`
  (`--accent`-independent `#c084fc`, glow, hover tooltip with exact
  version), a `.es6-legend` notice explaining the marker and the
  Compatibility-mode caveat, and 18 starred table cells covering every
  ES2015+ feature on the page (`at` ES2022, spread ES2015, `includes` /
  `startsWith` / `repeat` ES2015, `replaceAll` ES2021, `padStart` ES2017,
  `codePointAt` ES2016, `Set`/`Map` ES2015, `Array.fill` ES2015, arrow
  sort ES2015). Unstarred rows are plain ES5.
- Verified: div/table balance 0; 18 stars in tables + legend; computed
  color rgb(192,132,252); zero page errors. Deployed via FTP (size match
  19504); live HTTP 200 with 21 `es6-star` occurrences and the legend.

## Deployment (2026-10-12, on explicit go-ahead)

- Uploaded `js-essentials.html` via FTP with the same flow as
  `upload_javascript.py` (that script publishes `index.html` only).
- FTP `SIZE` check: local 42907 = remote 42907.
- Live verified: `https://findtorontoevents.ca/servicenow/javascript/js-essentials.html`
  returns HTTP 200, 42907 bytes (note: the site's WAF 412s the default
  `urllib` user-agent — fetch with a browser UA, e.g. curl).
- All six new markers present live: "Set & Map gotchas", SameValueZero,
  `new Map(Object.entries(obj))`, "object is not iterable", the
  Map-vs-plain-object notice, and the "Object keys in a Set/Map" §10 row.
