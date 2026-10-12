# ServiceNow JS quiz rebuilt: categories, subcategory filters and mixed mode (2026-10-12)

## What was there

`findtorontoevents.ca/servicenow/javascript/quiz.html` was 222 lines with **three
hardcoded GlideRecord questions**, each with its own inline `checkQn()` function
doing exact string comparison. Adding a fourth question meant writing a fourth
function, and correct answers were rejected for trivial formatting differences
(`gr.getRowCount ()`, curly quotes, a trailing semicolon).

## What it is now

### `quiz-data.js` (new) — the question bank

A single `window.SN_QUIZ` object holding:

- **7 categories**, one per API area, each with an icon, accent colour, blurb and
  2–3 subcategory tags:

  | Category | Subcategories | Questions |
  |---|---|---|
  | GlideRecord | Querying · Reading fields · Insert/update/delete | 11 |
  | Encoded Queries & GlideQuery | Filter strings · Conditions & OR logic · GlideQuery | 8 |
  | GlideAggregate | Counts & sums · Grouping | 7 |
  | GlideDateTime | Create & read · Arithmetic · Compare | 8 |
  | GlideAjax & Script Includes | Client side · Script Include side | 8 |
  | g_form & Client Scripts | Field control · Messages · onChange/onSubmit | 10 |
  | GlideSystem (gs) | User & roles · Utilities · Logging & messaging | 10 |

  **62 questions total.**

- **Every question is standalone and coding-specific** — you type the actual API
  call. No question requires knowledge from another category, so a category works
  as a self-contained practice set.

- Question shape: `{ id, cat, sub, type, q, ph, accept[], answer, hint }`.
  `accept` is a list of valid forms; `answer` is the canonical one shown on
  failure and in the answer key. **Adding questions is a plain append** — no HTML
  change, no new function.

### `quiz.html` (rewritten) — picker + runner

- **Category picker**: a Mixed card plus a card per category showing its blurb,
  question count and clickable subcategory chips (with per-sub counts).
- **Runner**: the full question list for the chosen category, or for one
  subcategory, or a **mixed sample of 10 that always includes at least one
  question from every category**. Per question: input, Check, Hint, live
  correct/incorrect marking with the canonical answer on failure. Sticky score
  pill + progress bar, Reveal answers, Reset, and a collapsible answer key.
- **Loose answer matching**: both sides go through the same normaliser (curly
  quotes → straight, all whitespace stripped, trailing `;` dropped), with a
  second looser pass that also strips a leading `var x = ` assignment. **Case is
  still significant**, because JavaScript is.
- Kept the existing visual language (nebula background, `.sn-lnav` shared header,
  dark glass card). The header's "Quiz" link is now marked `aria-current`
  instead of the JavaScript Reference link.

### `index.html` (two labels)

"GlideRecord Quiz" → "JavaScript Quiz" in the nav, and the CTA now describes the
category system.

## Bugs found by testing and fixed

1. **`byCat` used outside its branch.** `start()` built `byCat` only inside the
   `if (catIds.length > 1)` arm but referenced it in the subtitle for *all* paths,
   so opening a single category threw a `ReferenceError` and the runner never
   rendered. Replaced with a distinct-category count computed from `state.list`.
2. **`.hidden` was losing to `.key-list { display: grid }`.** Both are
   single-class selectors, and `.hidden` was declared *earlier* in the stylesheet,
   so the later rule won. The answer key's class and button label toggled but it
   **never actually hid**. Fixed by moving `.hidden` to the end of the sheet with
   `!important`. Caught only because the test asserted `getComputedStyle(...).display`
   rather than trusting the class name.
3. **Nested interactive elements.** The first version put `<span role="button">`
   subcategory chips inside a `<button>` category card. Restructured to a
   `<div class="cat-card">` holding a `.cat-open` button and separate `.sub-chip`
   buttons; a test now asserts `document.querySelectorAll('button button').length === 0`.

## Verification

- **Data integrity** (`node`): 62 questions, 0 problems — no duplicate ids, every
  `cat`/`sub` resolves, every `answer` appears in its own `accept` list, no empty
  or missing fields. `node --check` clean.
- **Browser (Playwright), local *and* live**: **31/31 assertions pass**, `QUIZ_EXIT=0`
  and `LIVE_QUIZ_EXIT=0`. Covers picker structure (7 cards, 1 Mixed, 19 chips, no
  nested interactive elements), category open, correct/incorrect marking, the
  canonical answer on failure, quote/whitespace/semicolon normalisation, the
  `var`-prefix loose pass, **case still rejecting**, hint toggle, score pill,
  progress bar, answer-key open/close with a computed `display:none` assertion,
  subcategory filtering, mixed mode (10 questions spanning every category),
  Enter-to-check, reset, and **0 console errors**.
- **Guide still clean** after the label edits: 0 tag mismatches, 53/53 TOC
  anchors, 0 console errors.
- **Deployed** over FTP with remote backups (`*.bak-20261012-quiz`); all three
  files byte-identical to local: `quiz.html` 23,997 bytes, `quiz-data.js` 31,661
  bytes, `index.html` 386,724 bytes.

## Answer accuracy

Every answer was checked against the official ServiceNow API references and
against the corrections already in `index.html`
(`2026-10-12-servicenow-js-hallucination-audit.md`): `orderByDesc` not
`setDesc`, `addDays(-3)` not `subtractDays`, `getRowCount`/`getUniqueValue`/
`isValidField` real, `addAggregate(agg, name)` two-arg form, `getXMLWait`
unavailable to scoped apps, `GlideQueryCondition` returned by `addQuery()` with
no constructor, `getDayOfWeek()` 1=Mon…7=Sun.

## Limitations

Answers are matched, not executed — there is no ServiceNow instance available, so
the snippets are validated against documentation and JavaScript syntax, never run
on-platform.
