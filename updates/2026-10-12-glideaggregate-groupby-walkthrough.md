# GlideAggregate groupBy walkthrough added to the ServiceNow JS guide (2026-10-12)

## What was requested

§4 of `findtorontoevents.ca/servicenow/javascript/index.html` had a
`groupBy()` example but no explanation of *what each line does*, what the
result set actually looks like, or how to read a group's values back out of
the aggregate loop. Added a full walkthrough at
`#agg-groupby-walkthrough` covering a two-column `groupBy('priority')` +
`groupBy('category')` rollup.

## What was added

| Block | Content |
|---|---|
| Code card `PriorityCategoryRollup.background` | `addAggregate('COUNT','priority')`, `groupBy('priority')`, `groupBy('category')`, `query()`, loop reading `agg.priority` / `agg.category` / `getAggregate('COUNT','priority')` |
| **Line by line — effect on the result set** | 9-row table: each source line, what it does, and its effect on the rows returned (single groupBy → 5 rows; second groupBy → one row per priority **+** category pair; `next()` advances per *group*, not per record) |
| **What the result set looks like** | 10-row Priority/Category/Count table (8, 4, 22, 15, 8, 41, 33, 13, 19, 6) with a **Total = 169** footer row, plus the note that priorities 1/2/3 repeat across categories — the whole point of a second `groupBy()` |
| **How `agg` behaves on each iteration** | 10-row iteration table mapping iteration number → `agg.priority` → `agg.category` → `getAggregate('COUNT','priority')` |
| **Pulling the group's values out properly** | Second code card using `getValue('priority')`, `getDisplayValue('priority')`, `agg.category.toString()`, `getDisplayValue('category')`, `parseInt(getAggregate(...),10)`, and an empty-category guard |
| Quick notes | 5 bullets: one `next()` per unique field combination; more `groupBy()` calls expand the result; order is not guaranteed (add `orderBy()` / `orderByAggregate()`); the read must match the declaration; `COUNT` with a field counts non-null values |

## Sources checked before writing

- Official **Zurich GlideAggregate API reference**
  (`servicenow.com/docs/r/zurich/api-reference/server-api-reference/c_GlideAggregateAPI.html`)
  — confirms `addAggregate(String agg, String name)` where *name* is
  "Optional for field name", that `COUNT` means "Count of the number of
  non-null values", and its own example uses `addAggregate('COUNT',
  'sys_mod_count')` → `getAggregate('COUNT', 'sys_mod_count')`, the same
  shape as the walkthrough.
- The same page's example output includes a group with a **blank** `category`
  and `COUNT: 4` — so empty group values still produce their own row. The
  walkthrough says to test for empty rather than assume a group is missing,
  rather than the (incorrect) claim that `groupBy` drops nulls.

## Verification

- Masked-tag balance across 29 tags → **0 mismatches**; no duplicate `id`s.
- `node --check` on all **85** `<pre><code>` blocks → the same **3**
  intentional non-parsing fragments as before (a `{ ... }` placeholder, a nav
  tree diagram, a `.map()` continuation). Both new blocks parse clean.
- Arithmetic: the 10 result-set counts sum to **169**, matching the footer.
- Browser (Playwright), **local and live**: 53 sections / 53 TOC links /
  **0 broken anchors** / **0 console errors**. Targeted DOM check on
  `#agg-groupby-walkthrough` returned 4 headings, 3 tables (9 / 11 / 10 body
  rows), 2 code cards, a 5-item notice, and **no horizontal table overflow**
  — identical on the deployed page.
- Deployed over FTP with a remote backup; served file byte-identical to local
  (**386,513 bytes, sha256 `7320ea08…`**).

## Follow-up: single-row aggregates with `setGroup(false)`

A follow-up contribution added the *ungrouped* half of the picture — a single
overall figure across a filtered slice rather than a row per group:

- New `h3#agg-single-row` **"One overall value: filter, don't group"** in §4:
  `addQuery('priority','1')` + `addAggregate('AVG'/'SUM', 'sys_mod_count')` +
  `setGroup(false)` + `query()`, reading back through `parseFloat()`.
- A notice stating what `setGroup(false)` is actually for, plus the two facts
  that trip people up: **`getAggregate()` returns a string** (wrap it before
  arithmetic) and **`priority` is stored as `'1'`** (`1 - Critical` is only the
  display label).
- An `h4` **"The same thing, still grouped"** — the same filter with
  `groupBy('category')`, the identical pattern to the walkthrough above, just a
  different aggregate function.

### Source check

`setGroup()` was verified as **real and documented** before being added, rather
than taken on trust:

- The official GlideAggregate API reference lists `setGroup(Boolean b)` and its
  companion **`setOrder(Boolean b)`**.
- The **Scoped** GlideAggregate page mirrors both.
- ServiceNow KB0852541: *"setGroup(boolean) - Sets whether the results are to be
grouped; setOrder(boolean) - Sets whether the results are to be sorted."*

The wording on the page is deliberately precise: with no `groupBy()` call,
GlideAggregate already returns one row, so `setGroup(false)` here is insurance
and the idiomatic write alongside `addHaving()` — not a prerequisite. The page
says that, rather than implying the query fails without it.

### Quiz kept in sync

Three questions added to the GlideAggregate category (now 10; bank total 65):

| id | sub | Asks |
|---|---|---|
| `ga-08` | basic | Which documented method collapses the result to a single row → `agg.setGroup(false)` |
| `ga-09` | basic | `getAggregate()` returns a string — wrap in `parseFloat()` before arithmetic |
| `ga-10` | group | The documented companion that turns sorting off → `agg.setOrder(false)` |

### Re-verification after this change

- Guide: 0 tag mismatches, no duplicate ids, `node --check` on **87** snippets
  with the same 3 intentional non-code failures, 53 sections / 53 TOC links /
  **0 broken anchors** / **0 console errors**.
- Targeted live DOM check on `#agg-single-row`: both code cards
  (`P1Churn.background`, `P1ChurnByCategory.background`), the "still grouped"
  `h4`, a notice quoting the documented signature, and `setOrder` present in the
  section — **0 console errors**.
- Quiz data: **65 questions, 0 problems**. Playwright **31/31 locally and 31/31
  live** (`QUIZ_EXIT=0`, `LIVE_QUIZ_EXIT=0`).
- Deployed with remote backups; `index.html` **390,218 bytes** and
  `quiz-data.js` **33,101 bytes**, both byte-identical to local.
