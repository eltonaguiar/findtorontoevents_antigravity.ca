# ServiceNow JS guide — hallucination audit against official docs (2026-10-12)

## What was broken

`findtorontoevents.ca/servicenow/javascript/index.html` was audited code-block by
code-block (84 `<pre>` blocks) against official `servicenow.com` resources, because a
reported snippet turned out to be invented:

```js
var enc = new GlideEncodedQuery();
enc.setQueryTerm('active', '=', 'true');
```

There is **no** `GlideEncodedQuery` class and **no** `setQueryTerm()`. Both were
fabricated, and the whole of section 3 was built on them.

An incoming third-party audit report was itself checked against the official docs
before acting on it — roughly half its claims were wrong (details in §4).

## 1. Confirmed hallucinations — fixed

| Location | Invented / wrong | Replaced with |
|---|---|---|
| §3 (TOC + section) | `new GlideEncodedQuery()`, `setQueryTerm()`, `enc.getQuery()` | Rewrote as **"3. Building Encoded Queries"**: `addQuery()` chain, encoded-query string + `addEncodedQuery()`, and the real fluent **`GlideQuery`** builder |
| GlideAggregate card | `#ga.orderByAggregate('COUNT');` — leading `#` was a **JS SyntaxError** | `ga.orderByAggregate('COUNT', 'priority');` (documented `(agg, field)` signature) |
| GlideAggregate card | `ga.setDesc(true)` — not a GlideAggregate method | `ga.orderByDesc('priority')` |
| GlideDateTime card | `gdt.subtractDays(3)` — doesn't exist | `gdt.addDays(-3)` with an explanatory comment |
| GlideDateTime card | `getDayOfWeek(); // 1=Sun ... 7=Sat` | `// 1=Mon ... 7=Sun (official)` |
| GlideDateTime card | `gdt.getHours/getMinutes/getSeconds()` — absent from GlideDateTime | `gdt.getLocalTime().getHours()` (+ `getMinutes()`) |
| GlideList card (§6) | `getSelectedRows()`, `getRowCount()`, `getTotalRows()`, `getViewName()`, `sortBy()`, `clearFilter()`, `refreshWithOrderBy(args)`, `showHideGroups(bool)` | Only documented GlideList2 methods: `getChecked/getTableName/getQuery/getView`, `sort()/sortDescending()/setOrderBy()`, `refresh()`, `refreshWithOrderBy()` (no args), `setFilter()` / `setFilter('')` |
| g_user card (§9) | `hasRoles('itil','incident_manager')` — `hasRoles(Boolean)` takes a boolean, not roles | `hasRoleFromList('itil,incident_manager')` for "any of", plus `hasRoles(true)` for "has any role" |
| GlideAjax getXML block | fabricated response attrs `error` / `elapsed_ms` | documented `answer` attribute only + null guard |
| Import-set block (App. B) | `loadImportSetTable(dataSourceSysId, table, file)` — wrong signature; `new ImportSetTransformer()` + `setTransformMapId()`/`setImportSetID()`/`transform()` — no such class | `loader.getImportSetGr(dsGr)` → `loader.loadImportSetTable(importSetGr, dsGr)`, with a note that no `ImportSetTransformer` class is documented |
| Workflow BR (App. H) | `new GlideDateTime(a) < new GlideDateTime(b)` — compares stringified objects | `end.before(now)` (documented comparison API) |
| §14 prose | `gr.getValue()` returns `''` for empty / `undefined` for bad field | docs: returns **`null`** for *both*; use `isValidField()` to distinguish |
| Join block | `jq.addCondition('sys_id','=', <groupSysId>)` — non-JS placeholder | `groupSysId` |

## 2. Bugs found beyond the reported one

- **Unclosed `<ul>` in §28 References** (line 2413) — the links list was never closed;
  a `<p>` followed directly. Present on the live page too. Fixed (and an unescaped
  `&` → `&amp;` in the same `<li>`).
- The `#ga.` line meant **every copy-paste of the GlideAggregate card failed to parse**.

## 3. Deliberately *not* changed (report accused these wrongly)

| Report claim | Official evidence |
|---|---|
| `getDisplayValueInternal()` "not documented" | Listed in both the Script-Sandbox evaluator and Guarded-script API tables, plus its own API-reference entry |
| `showFieldMsg(...,'warning')` invalid | GlideForm docs: valid values are `error; info; warning` |
| "getXMLWait unavailable to scoped apps" misleading | GlideAjax docs state it verbatim |
| Xanadu ES12-default claim "fabricated" | Docs: "When you create new scripts, ECMAScript 2021 (ES12) mode is turned on by default regardless of the mode configured for the application" |
| `javascript:gs.daysAgoStart(7)` in `addQuery()` risky | ServiceNow's own Scripting Guide uses this form |
| Replace §3 with `GlideQueryCondition` | Real class, but it is the condition object `addQuery()` returns, not a query builder — used `GlideQuery` instead |

Added the reviewer's correct nuance on `getDisplayValueInternal()` as a visible
notice in §5: for ~95% of work use `getValue()` (background) or `getDisplayValue()`
(user-facing); `getDisplayValueInternal()` keeps the user's timezone but switches to
the system format — niche, deliberate, not a default.

## 4. Verification

- **Structure**: masked-tag balance check (comments/`<pre>`/`<script>`/`<style>` blanked)
  across 29 tags → **0 mismatches** (the `<ul>` fix closed the one real defect).
- **JS syntax**: all 84 blocks extracted and run through `node --check`. Remaining 3
  non-parse results are intentional: a `{ ... }` placeholder, a nav tree diagram, and
  the page's own inline `<script>` (which parses clean).
- **API evidence**: GlideDateTime, GlideList2, GlideUser, GlideForm, GlideAjax,
  GlideAggregate, GlideQuery, GlideRecord — official `servicenow.com` API references,
  Script Sandbox evaluator list, and Guarded-script allowed-API list.
- **Local browser (Playwright)**: 53 sections / 53 TOC links / **0 broken anchors** /
  **0 console errors**; screenshots of §3, §5, §6 reviewed visually.
- **Live**: uploaded over FTP with a remote backup
  (`index.html.bak-20261012-audit`); served file **byte-identical** to local
  (369,089 bytes, sha256 `df797a13…`). Live browser re-run: same 53/53/0/0 result,
  invented-API scan empty, TOC jump lands on §3, copy button returns "Copied!".

## 5. Files

- `findtorontoevents.ca/servicenow/javascript/index.html` — the fix
- `updates/2026-10-12-servicenow-js-hallucination-audit.md` — this doc

Note: the file also carries ~3,100 lines from the earlier same-day TOC/appendix
reorg that was deployed live but never committed — that content was already
published and documented in `2026-10-12-techfinds-apple-videos-toc-news-api-fix.md`
§3, so it rides along in this commit.
