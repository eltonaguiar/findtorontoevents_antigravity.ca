# 2026-10-11 — New Appendix S: Table Joins & Encoded-Query Cookbook

## What was requested

Add a few table-join syntaxes and/or encoded-query shortcuts to the JavaScript
reference page, as their **own dedicated appendix section**.

## What was added

File: `findtorontoevents.ca/servicenow/javascript/index.html`
Section: `#appendix-joins` — "Appendix S — Table Joins & Encoded-Query Cookbook"
(section-chip "Query Power"), placed after Appendix R and linked from the TOC
as "S. Joins & Encoded Queries".

Nine sub-parts, each with runnable server-side examples and/or tables:

1. **Dot-walking (implicit joins)** — `caller_id.department.name`,
   `caller_id.manager.active`; reading with `getDisplayValue()`; the N+1 cost
   warning.
2. **`addJoinQuery()` — explicit joins** — signature
   `addJoinQuery(table, fieldFromCurrent, fieldInJoinedTable)`, chaining
   `.addCondition()` / `.addOrCondition()` on the returned join.
3. **OR groups / NOT** — `addOrCondition()` for OR within a group; `!=` for NOT.
4. **Encoded-query operator table** — the full set: `=`,`!=`, `STARTSWITH`,
   `ENDSWITH`, `LIKE`/`NOTLIKE`, `IN`/`NOT IN`, `ISEMPTY`/`ISNOTEMPTY`,
   `>=`/`<=`, `BETWEEN a@b`, `RELATIVE` rolling windows, `SAMEAS`/`NSAMEAS`,
   `DYNAMIC<filter_sys_id>`, `VALCHANGES`/`CHANGESFROM`/`CHANGESTO`, and
   `^` / `^OR` / `^NQ`.
5. **Build & replay encoded queries** — string-building, dot-walk joins inside
   strings, `^OR`, `addEncodedQuery`, `new GlideRecord(table, query)`,
   `getEncodedQuery()`.
6. **Handy helpers table** — `addActiveQuery()`, `addNullQuery()`,
   `addNotNullQuery()`, `addDomainQuery()`, `orderBy`/`orderByDesc`,
   `setLimit`/`chooseWindow`, `getEncodedQuery()`.
7. **`GlideFilter`** — evaluate a stored condition string against a record
   (`new GlideFilter(cond, 'title').match(gr, true)`).
8. **Date shortcuts table** — `gs.daysAgoStart(7)`,
   `gs.beginningOfThisMonth()`, `gs.beginningOfLastMonth()`,
   `gs.beginningOfToday()`, and the `RELATIVEGE@day@ago@7` form.
9. **Joins with GlideAggregate** — count grouped by a dot-walked field.

Plus a performance callout (constrain the base table first, prefer indexed
reference fields for the join, no dot-walk in loops, GlideAggregate for counts)
and a 7-question **knowledge check** block matching the rest of the appendix.

Also: TOC entry added and the hero badge bumped to
"28 sections + 20-part appendix".

## Verification

- **TOC integrity:** 49 `nav.toc` links, zero missing targets.
- **Structure:** 20 `section[id^=appendix-]`; Appendix S contains 3 tables
  (24 rows), 6 code cards, and a 7-question knowledge check; **zero
  `pageerror`** events locally and live.
- **Visual:** screenshots confirm the section header, dot-walk/`addJoinQuery`
  code blocks, the OR-group and encoded-operator tables, and the callouts all
  render cleanly on the dark theme with the sidebar TOC intact.
- **Live after deploy:** `curl` shows `appendix-joins`,
  "Table Joins & Encoded-Query Cookbook", `addJoinQuery`, `addOrCondition` and
  `GlideFilter` present.

Deployed with `python3 upload_javascript.py`.

## Currency note

These operators/APIs are core and stable, but a few (e.g. `addJoinQuery`
behaviour on very large tables) are performance-sensitive per release — verify
against the instance's release if the query is on a hot path.
