# 2026-10-11 — Appendices T & U: reusable code / platform standards + low-code first

## What was requested

Add a section covering **reusable code / overall platform coding** (UI Script
Includes, Instance Scan to prevent `eval()` and similar violations like
client-side GlideRecord, Decision Tables, Assignment Rules, Subflows), document
them, research **no-code / low-code alternatives to coding**, list **what to
avoid**, cover **reusable Flow Actions**, and dig into **top architectural
findings / elite-partner patterns**.

## Research

ServiceNow's live docs remain JS-rendered and sign-in-walled (docs.servicenow.com
redirects to a loading SPA; developer.servicenow.com needs auth), so detail pages
couldn't be scraped. The content was built from established ServiceNow platform
behaviour — these mechanisms (UI Scripts, Instance Scan, Decision Tables,
Assignment Rules, Flow Actions/Subflows, App Engine Studio, clean-core guidance)
are stable and well-documented. A currency note is included.

## What was added

File: `findtorontoevents.ca/servicenow/javascript/index.html`

### Appendix T — "Reusable Code & Platform Coding Standards"
- **Reusable-code toolbox** table (Script Include, **UI Script Include**,
  Flow Action, Subflow, Decision Table, Scripted REST, Script Action) with
  side + purpose + table.
- **UI Script Includes & the page-load trap** — global UI Scripts load on every
  page (a latency tax); mark them **on-demand** by default.
- **Flow Actions & Subflows** — reusable logic at the no-code layer, with a
  worked Flow Action Script-step example (typed inputs/outputs).
- **Decision Tables & Assignment Rules** table — declarative tool vs the
  scripted thing it replaces (routing, visibility, validation, SLA, email).
- **Instance Scan** — what it is (scan checks / suites / findings /
  suppressions / baselines), breadcrumb, and a table of the high-value checks
  including **`eval()`/`new Function()`/string setTimeout**, **client-side
  GlideRecord**, **direct DOM manipulation**, scripting in UI/Data policies,
  hard-coded sys_ids/URLs, unbounded queries, OOTB edits.
- **Platform coding-standards checklist** (the L6-defended list).
- 6-question knowledge check.

### Appendix U — "No-Code / Low-Code First & What to Avoid"
- **The decision ladder** — OOTB → config/UI policy → declarative logic →
  Flow Designer → custom script (climb from the top; justify each step down).
- **No-code/low-code alternatives** table — "you're about to write… → consider
  first → why" covering field defaults, UI/Data Policies, Flow Designer,
  Decision Tables, Assignment Rules, Notifications, SLAs, Reports/PA,
  IntegrationHub spokes, **App Engine Studio**, **Playbooks**, Templates.
- **What to avoid** table with the fix for each (eval, client GlideRecord, DOM
  manipulation, scripting in policies, N+1, getRowCount, recursive
  `current.update()`, hard-coded ids/creds, OOTB edits, wrong-engine business
  rules, global scope, fat global UI Scripts, `gs.log` in prod, sync calls).
- **Elite-partner / top architectural findings** — clean core, configuration
  over code, single service layer, standards-as-automation, governance/naming,
  async-by-default, ACL-first, upgrade rehearsal, document-the-why.
- An interview one-liner and a 6-question knowledge check.

TOC entries added ("T. Reusable Code & Standards", "U. Low-Code First & What to
Avoid"); hero badge bumped to "28 sections + 22-part appendix".

## Verification

- **TOC integrity:** 51 `nav.toc` links, zero missing targets.
- **Structure:** 22 `section[id^=appendix-]`; Appendix T has 4 tables,
  Appendix U has 3 tables; 21 `.kcheck` blocks total; **zero `pageerror`**
  events locally and live.
- **Visual:** screenshot of Appendix U confirms the decision-ladder flow
  diagram, the alternatives table and the headings render cleanly on the dark
  theme.
- **Live after deploy:** `curl` shows `appendix-reuse` + `appendix-lowcode`,
  "Reusable Code & Platform Coding Standards", "No-Code / Low-Code First",
  "clean core", "Instance Scan" (19×) and "UI Script" (11×).

Deployed with `python3 upload_javascript.py`.

## Currency note

ServiceNow renames/moves features between releases (e.g. Decision Tables, the
ITBM→SPM rename, Playbooks vs Workflow). The **patterns** are durable; verify
exact menu labels and table names against the instance's release.
