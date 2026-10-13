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

## Second challenge on the same claim — re-verified against primary sources

The `{0}` positional form was challenged twice ("the {0} style parameter is NOT
valid"), so it was re-opened rather than defended from the earlier answer. Evidence
now includes an **executed example with real platform output**:

```
gs.warn('This is a message with {0}, {1}, {2}, {3}, {4} parameters', 'one', 'two', 'three', 'four', 'five');
//*** Script: This is a message with one, two, three, four, five parameters
```

— from the GlideSystem API reference, for `warn`, whose signature is identical to
`info`'s (`(String message, Object parm1 … parm5)`: five slots, zero-based → exactly
`{0}`…`{4}`, which is the wording now on the page). Corroborated by ServiceNow's own
GlideRecord example `gs.info('*** Total number of active incidents: {0}',
incident.getRowCount())`, by a practitioner's `gs.info('{0}\n\n{1}', prefix, message)`,
and by the community logging article's "the variable substitution order … is zero
based … gs.log is unique in that it allows us to pass the source".

**Conclusion: the page's `gs.info('P{0}: {1}', priority, summary)` line is correct and
was left standing.** What *doesn't* substitute is now struck through on the page with
`<s>`: `gs.log('P{0}: {1}', …)` (second argument is the source) and the template-literal
`` gs.info(`P${0}: ${1}`, …) `` ( `${0}` is the number 0). The block also carries the
executed `warn` example above as on-page proof, and the positional comment now says
"up to {4}".

Two of my own tool calls failed during this edit and are worth recording: `str_replace`
rejected the block twice because I had transcribed `${1}` as `{1}` — the fix was to
print the region with `repr()` and match the bytes instead of my memory.

## Round 3 — syntax pass, scrollbars, abbreviation glosses

Three requests: *double-check syntax*, *some sections are cut off — add scrollbars*,
and *the NPE section should spell the abbreviation out, and audit the rest*.

### 1. Syntax — every code block compiled, 0 hard errors

104 JavaScript blocks across the three pages, classified rather than pass/fail'd:

| class | count | meaning |
|---|---|---|
| parses as a script | 98 | copy-paste safe |
| parses as a module only | 1 | `js-essentials.html:398`, top-level `await` (ES2022 ESM) |
| function-body fragment | 4 | top-level `return` — legal only inside a method |
| pseudocode | 1 | `index.html:1416`, `{ ... }` placeholders |
| **hard syntax error** | **0** | |

`quiz-data.js` also passes `node --check`. The two blocks labelled as *files*
(`AnyMatch.scriptinclude`, the Script Include / Scheduled Job import card) got a
leading comment saying they are a function body, because `return` outside a function
is a SyntaxError if someone pastes the card as a whole script. The async block in
`js-essentials` now says its last two lines are top-level `await` (module context).

### 2. Scrollbars — the real clipping bug

`.api-card pre` had `max-height: 320px` **and `overflow-y: hidden`**: content taller
than 320 px was cut off with no way to scroll, which is exactly what was reported —
the `IncidentUtils` example lost ~137 px (about eight lines, including the
`callerMap.set(callerId, …)` line) and only the Copy button revealed it. Changed to
`overflow-y: auto`. The other `overflow: hidden` rules on the page (`header.hero`,
`.code-card`, `.kcheck details`) and the `nav.toc { max-height:40vh; overflow-y:auto }`
were checked and are not clipping code.

Verified with a dedicated Playwright check, run against `file://` **and against the
live URL**: no `pre` on any of the three pages is taller than its box without a
scrollable `overflow-y`, and the reported `callerMap.set(callerId` line is reachable
— it sits inside the block's viewport once scrolled to (`scrollTop` 6 of max 137).
**10/10 both times.**

### 3. Abbreviations — bracketed glosses at first use

User flagged `NPE`; a prose-only audit (code blocks stripped) then found the rest.
15 glosses added to `index.html`:

`NPE (NullPointerException)`, `Display BR (Business Rule)`, `OOB (out-of-the-box)`,
`BAU (business-as-usual)`, `KB (Knowledge Base)`, `JDBC (Java Database
Connectivity)`, `GMT (Greenwich Mean Time)`, `SLA (service-level agreement)`,
`CI (continuous integration)`, `CSA (Certified System Administrator)`, `PA
(Performance Analytics)`, `DEV (development) → UAT (user acceptance testing) → PROD
(production)`, `DOM (Document Object Model)`, `CMDB (Configuration Management
Database) & CSDM (Common Service Data Model)`, `ATF (Automated Test Framework)`.
Left alone as universally known: API, JSON, REST, HTML, DOM-adjacent terms, SQL, DB.
CIS-CSM / CIS-VR are course codes, not abbreviations. CAB and ITIL were already
spelled out adjacent to the acronym.

### 4. A regression I introduced, caught by the checks

The `js-essentials` module note initially contained a literal `<script
type="module">` inside a `<code>` block. HTML does **not** treat `<pre>` as raw text,
so that started a real `<script>` element and swallowed the rest of the page — the
row-count assertion failed (`§10 table has 17 rows, got=7`). Reverted to
`&lt;script type="module"&gt;`, which renders and copies back as the intended text.
This is the row-count check doing its job, not a weakened assertion.

## Deployment status (final)

- **Deployed** over FTP after each round, then fetched back and md5-compared:
  `index.html` **407796**, `js-interview.html` **20085**, `js-essentials.html` **43055**
  — all three live == local == HEAD. Server-side `SIZE` is asserted on every upload.
  (`index.html` went 406378 → 406996 → 407796 and `js-essentials.html` 42907 → 43055
  across rounds 1–3; `js-interview.html` has been 20085 since round 1.) Fetch with a
  browser UA; the site's WAF 412s the default `urllib`/curl UA.
- **Pushed** to `origin/fix/js-reference-accuracy-audit` (upstream set, remote SHA ==
  local). Contents: `f146acbed4` (the three fixes + this doc), `60e5667c1a` (this
  doc's final status), plus the pre-existing `c1707553a7` guards section the branch was
  cut from — all authored in Codebuff sessions; the repo's conflict-marker gate exits 0.
- **`js-essentials.html` committed on operator go-ahead** so the branch matches
  production byte-for-byte: 20 lines — the §7 "Set & Map gotchas" table, its
  Map-vs-object notice, and the 3 §10 rows. That is the content documented in
  `updates/2026-10-12-js-essentials-set-map-gotchas.md` and covered by the 71-check
  suite (§7 = 7 rows, §10 = 17 rows, every behavioural claim executed in Node), and
  it is byte-identical to what the live site has been serving all along.
- **Pushed commit == live** for all three pages: md5 of `git show HEAD:<file>` compared
  against the fetched live bytes.

## Harness note (exit status)

Both checkers now return a **non-zero exit code on failure** (`process.exitCode`),
so piping their output can no longer hide a red result. Proven by negative control:
copying the three pages to a temp root, deleting one ES6 star, rewording the `gs.log`
exception and deleting one §10 row makes the static checker exit 1 with **67/71 and
the 4 expected FAILs**, and the Playwright checker exit 1 with **14/16 and 2 expected
FAILs**. Against the real project both exit **0** (71/71, 16/16).
