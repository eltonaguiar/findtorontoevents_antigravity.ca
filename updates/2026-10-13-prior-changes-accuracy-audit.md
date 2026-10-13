# 2026-10-13 — Accuracy audit of the previous session's JS-reference changes

Request: *"check your prior changes for accuracy — if any issues, change, validate, and get them fixed."*
Follow-up during the audit: *"gs.info('Priority {0}: {1}', …) — double check our page, as the {0} style parameter is NOT valid!"*

## Scope

The previous session's work was **uncommitted**, and the live site byte-matched local
before this audit (local == live, md5-identical for all three files):

| File | Status before audit |
|---|---|
| `findtorontoevents.ca/servicenow/javascript/js-interview.html` | modified, uncommitted, live-synced |
| `findtorontoevents.ca/servicenow/javascript/js-essentials.html` | modified, uncommitted, live-synced |
| `findtorontoevents.ca/servicenow/javascript/index.html` | modified, uncommitted, live-synced |
| `updates/2026-10-12-js-essentials-set-map-gotchas.md` | untracked (documents the above) |

Also spot-checked: the committed HEAD (`c1707553a7`, §2.5 Defensive Guards).

## What was verified as correct (no change needed)

- **All 26 behavioural claims** in the js-essentials Set/Map gotcha table (§7) and the
  §10 "gotchas that fail tests" table were **executed in Node 22**, not quoted:
  `.size` vs `.length`, `new Map({a:1})` → `TypeError: object is not iterable`,
  `new Map(Object.entries(obj))`, SameValueZero (`new Set([NaN]).size === 1`, two `{}`
  are distinct keys), `set[0]`/`map[0]` → `undefined`, insertion vs sorted order,
  `delete` during `for...of` skips no survivors while `add` can infinite-loop,
  WeakMap rejecting a string key / having no `size` / not being iterable,
  `Object.create(null)` prototype fix, `??` fallback rule, `undefined + 1` → `NaN`,
  emoji length 2 vs spread 1, `'aaa'.replace('a','b') === 'baa'`, sparse `new Array(26)`
  vs `.fill(0)`, `Math.max(...1e6)` range error. **All passed.**
- Structure: §7 gotcha table = 7 data rows, §10 = 17 data rows (14 → 17 as documented),
  `<div>`/`<table>`/`<section>`/`<p>`/`<span>`/`<h2>`/`<h3>` balance = 0 on all three files.
- `index.html` cross-links: nav "Essentials" entry, prereq-card link, §12 cross-link —
  all three render (a first-pass checker regex was too narrow; that was a checker bug,
  not a page defect).
- HEAD commit's `getRowCount()` caveat: corroborated by the official GlideRecord API
  reference ("getRowCount() may be incorrect"; COUNT(*) note naming `chooseWindow()` and
  `getRowCount()`), so the committed wording stands.

## Defects found and fixed

### 1. `js-interview.html` version-marker legend made a false ServiceNow claim

Said starred ES2015+ features "work … in ServiceNow's *ES12* / **ES5-standards** modes …
but not in Compatibility mode". That contradicts our own `index.html` §12 feature table,
which marks arrow functions / `let` / `const` / destructuring / rest-spread / `for...of` /
`Map` / `Set` as **Not Supported** in ES5 Standards mode. It also implied `at()` (ES2022)
is covered by ES12 mode, which is ECMAScript **2021**.

**Fixed:** the legend now says the deciding factor on the server is the script's
*JavaScript mode*, that ES12 (2021) covers the starred *syntax*, that ES5 Standards and
Compatibility modes reject ES6+ outright, and that `at()` postdates ES12 so individual
built-ins should be checked against the platform's feature-support matrix. It also now
names `??` (ES2020) alongside `const`/`let`, `for...of`, arrows and spread, instead of
implying the code samples are all ES2015.

### 2. Three rows contradicted the legend's "Unstarred rows are plain ES5"

- §4 *Prefix sum* — `new Array(n).fill(0)` (`Array.prototype.fill` is ES2015)
- §4 *Frequency map* — `object/Map count` (`Map` is ES2015)
- §4 *Sliding window* — `Set or count map` (`Set` is ES2015)

**Fixed:** each cell now carries the marker (18 → 21 stars in tables). Also moved the
`startsWith`/`endsWith` star to sit after the pair (both are ES2015) so it cannot be read
as "only `startsWith` needs ES6".

### 3. `index.html` §7 over-generalised the `gs.*` substitution rule

The callout said ServiceNow's "**`gs.*`** logging methods do their own substitution".
`gs.log()` does **not** — its documented signature is `log(String message, String source)`,
so a `{0}` there is written out literally.

**Fixed:** the paragraph now names `gs.info()` / `gs.warn()` / `gs.error()` /
`gs.debug()` and quotes their documented signature
`(String message, Object parm1, Object parm2, Object parm3, Object parm4, Object parm5)`
— five substitution parameters, `{0}`…`{4}`, beyond which you concatenate — and states
the `gs.log()` exception explicitly.

## The user's `gs.info` claim — checked, and it does not hold for `gs.info`

The `gs.info('Priority {0}: {1}', agg.priority, agg.getAggregate('COUNT'))` example at
`index.html:1144` (and the matching quiz answer `gs-08`, the §7 logging card, the
group-by example at 1290/1293, and `gs.error(… {0} … {1} …)` at 2650) is **valid**:

- Official docs signature, GlideSystem **Scoped**: `info(String message, Object parm1,
  Object parm2, Object parm3, Object parm4, Object parm5)` — "Writes an info message to
  the system log". Same shape for `warn`, `error`, `debug`.
- ServiceNow's own GlideRecord reference uses the form in an example:
  `gs.info('*** Total number of active incidents: {0}', incident.getRowCount())`.
- Practitioner report of it running: `gs.info('{0}\n\n{1}', prefix, message)`.

So the page keeps the `{0}` form. The one legitimate version of the objection —
`gs.log(msg, source)` — is now documented on the page (defect 3 above), so the blanket
"`gs.*`" phrasing that would have made the user's reading correct is gone.

## Verification (after the fixes)

- `/tmp/verify_prior_changes.mjs` — **71/71 checks pass**: 26 executed Node claims,
  tag balance on all three files, row counts, 21 stars in tables, legend wording
  (old claim absent, new claim present), "no unstarred ES6+ row", all three
  `js-essentials` cross-links, and the new `gs.*`/`gs.log` paragraph.
- `/tmp/headless_check.mjs` (Playwright/Chromium, `file://`) — **14/14 checks pass**:
  zero `pageerror`/console errors on all three pages; legend renders with the mode rule;
  21 stars render in tables at `rgb(192,132,252)`; Set & Map gotchas heading, §10's 17
  rows and the Map-vs-object notice render; 3 `js-essentials` links render (1 in
  `nav.sn-lnav`); key anchors (`#es6`, `#glidesystem`, `#glideaggregate`, `#gr-guards`,
  `#acl-security`) all resolve.

## Follow-up — is `var category = ga.getValue('category') || 'None';` needed?

Asked during the audit; answered **on the page itself**, in the GlideAggregate
section of `index.html` (new `.notice` after the multi-column-grouping notes).

**Verdict: yes for the empty group — but `||`, not `??`, and only if the field is
really grouped.**

- **Empty keys are their own group, not missing rows.** Evidence: the official
  `GlideAggregate` example output (fetched from servicenow.com during this audit)
  contains a `CATEGORY:` line with nothing after it and `COUNT: 4`; the community
  background-script thread shows `… incidents with a category of ` (blank) and
  `Classification =[]` the same way. So `getValue('category') === ''` is a real,
  expected row — the guard is justified.
- **`||` is the right operator, `??` is not.** `getValue()` returns a string and the
  missing value is `''`. `'' ?? 'None'` stays `''` (`??` only covers
  `null`/`undefined`); `'' || 'None'` gives `'None'`. Because `''` is the only falsy
  string, a legitimate `'0'` group value survives `||` — but guard *before* any
  `parseInt`, or a real `0` collapses.
- **Blank on every row is a missing `groupBy()`, not a missing value.** The classic
  case: the community thread's author read a field she had `addAggregate`d but never
  `groupBy`d, and it came back blank on every iteration; the accepted fix was to add
  the `groupBy()`. The guard hides that structural bug, so the notice says to check
  `groupBy()` first.
- **Alternative: filter instead of label.** `ga.addQuery('category', '!=', '')`
  removes the blank group entirely — no guard needed, at the cost of those records
  leaving the rollup.

Verified after the edit: 71/71 static+Node checks, tag balance 0 (`div` 506/506,
`section` 53/53, `table` 67/67, `tr` 522/522, `td` 1223/1223, `p` 148/148, `ul` 41/41,
`li` 381/381, `h4` 57/57 …), and **16/16 Playwright checks** (zero page errors, the
new notice renders with the `??`-vs-`||` rule, all anchors resolve).

## Deployment status

- `js-essentials.html` — **unmoved** (no edits in this audit), still byte-matches live.
- `index.html` (403481 local vs 402961 live) and `js-interview.html` (20085 vs 19504)
  are **fixed locally but not uploaded** — FTP publish awaits an explicit go-ahead, as
  does the git commit (the tree still carries other sessions' uncommitted work, so the
  commit must be a clean branch containing only these files).
