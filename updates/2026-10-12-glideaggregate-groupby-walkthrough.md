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
