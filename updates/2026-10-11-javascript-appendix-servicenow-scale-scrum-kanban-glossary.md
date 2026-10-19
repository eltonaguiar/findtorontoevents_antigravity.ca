# 2026-10-11 — JavaScript appendix: ServiceNow-specific scale answer, real Scrum/Kanban definitions, glossary

## What was wrong (user feedback)

Two things in the new appendix weren't good enough:

1. **Scrum vs Kanban** was a bare comparison table — it never *defined* either
   term, and left acronyms (PO, WIP, BAU, SLA) unexplained.
2. **The "100,000 inbound API requests" answer** was generic cloud-industry
   advice — it literally named *SQS/Kafka/MSK/gateway*. The user's point:
   "we are talking about ServiceNow specifics, so research ServiceNow specific
   solutions, not generic API requests." The user also asked that **every
   abbreviation or technology be explained** rather than dropped in.

## What was changed

File: `findtorontoevents.ca/servicenow/javascript/index.html`

### 1. Appendix M (Agile) — Scrum and Kanban now properly defined

Replaced the single comparison table with:

- **"What Scrum and Kanban actually are"** — a `.callout` definition of each
  framework, followed by a bulleted list of its key terms, each explained:
  - Scrum: Sprint, Product Owner (PO), Scrum Master, Product/Sprint Backlog,
    Increment, Ceremonies, Velocity, Story Point.
  - Kanban: Kanban board, WIP (Work In Progress) limit, Lead time, Cycle time,
    Throughput, Pull system.
- **"Scrum vs Kanban — side by side"** — the comparison table, now with an
  "Aspect" header column and two extra rows (Commitment, Change during cycle).
- A `.notice` on how to run both at once on a platform team.

### 2. Appendix O — the 100k-requests answer rewritten ServiceNow-specific

Removed all generic cloud terms (SQS, Kafka, MSK, gateway). The rewrite now
uses only ServiceNow mechanisms and explains why each ServiceNow limit bites:

- The three ServiceNow limits that actually break: **REST API rate limits
  (semaphore pools** — <code>com.glide.rest.api.semaphore</code> /
  <code>com.glide.scripted_rest.semaphore</code>), **worker/node thread
  exhaustion**, and the **transaction-quota governor**
  (<code>glide.script.transaction_quota.*</code>).
- The answer, in ServiceNow terms: land data in an **Import Set / staging
  table** (<code>sys_data_source</code> → <code>sys_import_set_row</code> /
  <code>u_*</code> staging) via a **Scheduled Job**, or accept a batched
  payload at a **Scripted REST API** that returns <code>202 Accepted</code> and
  inserts to staging; then drain asynchronously with a **Scheduled Job** /
  **Async Business Rule** / **Event Queue + Script Action** in bounded batches.
  Coalesce on an external key; raise the semaphore only after the queue
  absorbs the burst; observe via the **Transaction Log** (<code>429</code>s) and
  Event Queue depth.
- Added an on-section **"Glossary (expand every acronym)"** table covering API,
  REST, SOAP, semaphore pool, transaction quota, Import Set, staging table,
  Scheduled Job, Event Queue / Script Action, Async Business Rule, Coalesce,
  Idempotent, PA.

### 3. Updated Appendix P interview answer

The "100k inbound requests" Q&A bullet now gives the ServiceNow-specific answer
(Import Set / staging / Scheduled Job / Event Queue / semaphore / transaction
quota) instead of naming SQS/Kafka.

### 4. New Appendix Q — Glossary of Terms & Acronyms (whole-page reference)

Added a TOC entry (Q) and a two-table glossary so **every** abbreviation used
anywhere on the page is spelled out once: platform/API terms (API, REST, SOAP,
Table API, Scripted REST API, semaphore, transaction quota, GlideRecord,
GlideAjax, gs, sys_id, CMDB, CI, CSDM, IRE, ITBM, SPM, PA, Flow Designer,
Workflow Editor, Import Set, Transform Map, Coalesce, Update Set, OOB, ATF,
ACL, UI/Data Policy, Session Debug, stats.do, Transaction Log, Event Queue,
Scheduled Job) and Agile/architecture terms (Scrum, Kanban, WIP, Sprint, PO,
BAU, SLA, PTO, RSU, SDE, CSA, SKU, CAB, ITIL, worker thread, idempotent,
circuit-breaker, dead-letter queue) — 57 rows total.

Also bumped the hero badge to "28 sections + 17-part appendix".

## Verification

- **TOC integrity:** 47 `nav.toc` links, zero missing targets.
- **Content:** 18 `section[id^=appendix-]`; Appendix O contains no
  Kafka/SQS/MSK/gateway/Amazon strings (checked by grep and by DOM scan);
  Appendix M has the definition callouts; Appendix Q has 57 glossary rows.
- **Rendered (local + live, headless Chromium):** zero `pageerror` events;
  the Scrum/Kanban callouts, lists and comparison table render cleanly on the
  dark theme (confirmed visually).
- **Live (after deploy):** `curl` shows the glossary, the "What Scrum and
  Kanban actually are" heading and "semaphore" present; and **zero**
  Kafka/SQS strings.

Deployed with `python3 upload_javascript.py`.

## Currency note

ServiceNow's semaphore/transaction-quota property names and defaults are
release-dependent; the *pattern* is stable, but the exact property strings
should be verified against the instance's release in docs.servicenow.com.
