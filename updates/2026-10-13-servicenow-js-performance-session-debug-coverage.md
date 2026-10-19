# 2026-10-13 — Performance & session-debugging coverage on the ServiceNow JS reference

Request: *"ensure you have coverage on our javascript page, on methods to test and tweak
performance across client script / server side, and narrow down the performance issue under
various scenarios, e.g. infinite loop or very long latency issue, the clock icon thing, and
enable session debugging and why to enable it, and clarify what page to check in session
debugging e.g. if incident form is slow, how to debug."*

File: `findtorontoevents.ca/servicenow/javascript/index.html`
408,213 → **434,087 bytes**, md5 `35b234687c2c04db0a837fa34cd0ff91` →
`332b9ad75d72edda6717ec790f28589b`. Before this session the file was clean against HEAD
(`git show HEAD:<path>` = `35b234687c2c04db0a837fa34cd0ff91`, 408,213 bytes) and byte-identical
to the live site, so the diff in this session is exactly this work (+202 / −31 lines).

## 1. What the page already had, and what it got wrong

The page covered slowness in **Appendix F** (breadcrumbs + clock notice) and **Appendix F2**
(an 8-step playbook). Audited against official docs before writing anything, seven claims did
not hold:

| Where | Claim on the page | Reality (source) |
|---|---|---|
| App. F notice | "the small clock indicator **in the banner**" | The **Response Time Indicator** is a clock **at the end of many forms and lists**: total / network / server / browser ms; not shown for the first transaction of a session nor for paging/sort; disabled by `glide.ui.response_time`. [Response time on forms](https://www.servicenow.com/docs/r/platform-administration/platform-performance/c_ResponseTimeOnForms.html) |
| App. F table | `stats.do` (or `?stats=true`) = "per-page stats … business-rule cost" | `stats.do` is the **instance/node** stats page (threads, memory, background workers, long-running thread stacks), reached via System Diagnostics → Stats or by typing `stats.do` in the filter. `?stats=true` found nowhere — removed. |
| App. F, F2, KCs (×4) | "Right-click banner → Session Debug" | Documented path is **All → System Diagnostics → Session Debug** (choose flags, *Enable All* / *Disable All*). |
| App. F2 step 6 + KC | flag **"Debug Client Scripts"** | Not in the official Session Debug option list. Client scripts are debugged in the browser (official: *"To debug client-side scripts, you can use browser-based developers tools"*) — DevTools Performance/Sources/console, plus Session Debug → **Debug UI Policies** and the **Client Transactions** *client script time* / *UI policy time* columns. |
| App. F, F2 (×3) | "All → Performance → Slow Queries" | **System Diagnostics → Stats → Slow Queries / Slow Scripts / Slow Transactions** (Stats Tools plugin). |
| App. F2 step 1 + 2 KCs | clock gives **Client / Server / Network / DB** | The clock gives **total / network / server / browser**. DB is a separate number: Transaction Log *SQL time/count* and *Slow Queries*. |
| App. A (ACL notice) | "session debug flag `glide.sys.log_security`" | No evidence the property exists (zero search hits). Replaced with the documented **Session Debug → Debug Security**, which prints granted / denied / not-evaluated per ACL. |
| App. Q glossary | "Session Debug = the **banner menu**"; "stats.do = the **banner clock** … Client/Server/Network/DB" | Both rows rewritten; a **Response Time Indicator** row added. |

## 2. Coverage added

**Appendix F — Platform Optimization & Page-Load Latency**
- **Breadcrumbs table** 6 → 9 rows: Response-time clock, Transaction Log, **Client Transactions**
  (Client Transaction Timings plugin: client-script / UI-policy / business-rule / SQL / network /
  browser ms), Session Debug, Debug log, **Stats & slow lists** (`stats.do`, Slow Queries/Scripts/
  Transactions), **Active Transactions (All Nodes)** (right-click → Kill), **Transaction
  Cancellation Log** (search `maximum execution time exceeded`), Performance Analytics.
- **Two clock notices** — clock no. 1 (Response Time Indicator, `glide.ui.response_time`,
  what it shows and when it does *not* appear) and clock no. 2 (the long-running-transaction
  **timer + Cancel** in the alert banner, `glide.ui.transaction.long_response.time` /
  `com.glide.request_manager.active`, `CANCELLED` in the Transaction Log URL).
- **New "Test and tune: client script vs server script"** — the 4-move matrix
  (baseline → narrow → tweak → re-measure) with a *different toolchain per column*, plus the
  **A/B trick** notice (deactivate the suspect script in sub-prod; if the clock does not move,
  it was never the problem).

**Appendix F2 — Diagnosing a Slow Page**
- Steps 1, 3, 4, 5, 6 rewritten: clock split corrected, session-debug path corrected, and step 4
  now answers *"where does the output land"* (bottom of the page just loaded, describing the
  **previous** transaction, full page load required; Session Debug → Debug Log; Script Debugger
  → Session Log; `glide.debugger.log.ui` = Page vs Session; roles `script_debugger` /
  `log_debugger`; limits `glide.debugger.log.transaction.count` / `glide.debugger.log_messages_limit`).
- **New: "Session debugging — what to switch on, and why"** — 8-flag table (Debug Business Rule
  (Details), Debug Security, Debug SQL, Debug UI Policies, Debug Metric Statistics, Debug Quotas,
  Debug Log, Enable/Disable All) with the question each flag answers, plus the *why enable it*
  notice (clock = how long, session debug = which line; session-scoped; overhead → sub-prod or
  low-traffic window; impersonate the affected user when role-specific; **Disable All** after).
- **New: "Which page do I check? — where the debug output lands"** — the three reading places
  side by side with their notes (this was the explicit ask).
- **New: "Worked example — the Incident form takes 12 seconds to open"** — 9 steps from the
  clock baseline → Transaction Log SQL-vs-BR split → enabling the three flags → full reload →
  reading output at the bottom of *that* form → Debug Log / Session Log → Slow Transactions /
  Slow Queries / Slow Scripts cross-check → the four real-world causes (reference field over a
  huge table, `sys_audit` query, `before query` BR, unindexed sort) → fix, *Disable All*,
  re-measure → ATF + p95 guard.
- **New: "Scenario playbooks"** — 5-row table: client infinite loop (tab freezes; nothing in
  the Transaction Log; DevTools → Sources → Pause; quotas cannot help), server infinite loop
  (alert-banner timer/Cancel → Active Transactions → Kill → Transaction Cancellation Log
  `maximum execution time exceeded` → Slow Scripts / Debug Metric Statistics), long-but-finishes,
  everything-slow instance-wide (`stats.do`, workers, 429s), slow-for-some-users. Plus the
  platform's own four causes of a slow transaction, and a **loop-guard code card** (bounded
  `while` + guard counter server-side, bounded `for` client-side).
- **Symptom → tool table** 6 → 9 rows (new: one form slow for everyone, request runs forever,
  browser tab frozen); 3 KCs corrected and **3 KCs added** (where the output appears, the
  spin-forever sequence, proving a client script is the owner).

**§16 Testing & Debugging Workflow** — 4 → 7 bullets: correct Script Debugger role
(`script_debugger`), Performance/Sources panes, "prove it with Session Debug, then Disable All",
the measure→re-measure loop pointing at Appendix F2, and bounding loops/queries *before*
load-testing.

**Appendix P + Appendix Q** — the "instance is slow for everyone" interview answer and the
glossary rows updated to the corrected tool paths; one row (Response Time Indicator) added.

## 3. Sources used

Official: Response time on forms (`c_ResponseTimeOnForms`), Session debug (`c_SessionDebug`,
Xanadu) incl. *Display debugging logs*, Script Debugger and Session Log (`script-debugger`),
Transaction quotas (`c_TransactionQuotas`), Transaction cancellation (`transaction-cancellation`),
Reviewing transaction logs (`c_TransactionLogResponseTimes`), Client transaction timings
(`r_ClientTransactionTimings`), Stats Tools (`c_StatsToolsDiagnosticsPlugin`), View and kill
active transaction (`t_ViewAndKillAnActiveTransaction`), System Logs → Transactions
(`syslog_transaction_list.do` in KB0564981). Corroborating community: the 2026 *"form taking
time to load in prod"* thread (architect's answer: Slow Transactions filtered on `incident.do`,
Slow Queries, Session Debug → Debug All, **"look at the logs at the bottom of the screen"**)
and the Session Debug output-at-the-bottom answers.

## 4. Verification

- **Structure** — after masking comments/`<style>`/`<script>`/`<pre>`/`<code>`, 20 tag types
  balance at **0 mismatches**; **0** duplicate `id`s; **0** missing `#` anchors.
- **JS syntax** — all **93** `<pre><code>` blocks run through `node --check`: **91 parse**
  (87 as module, 4 as script); the 2 non-parsing blocks are the pre-existing intentional ones
  (`if (gdt.after(start)) { ... }` placeholder and a nav-tree diagram) → **0 hard errors**.
  The new loop-guard block parses.
- **Playwright** — new checker `tools/verify_servicenow_perf_debug_coverage.mjs`:
  **36/36 PASS, exit 0** — zero page errors and zero console errors, all 5 new headings render,
  all 22 required strings present, TOC ≥40 entries all resolving, TOC click lands on
  `#appendix-diagnosing`, table/list row counts (test-and-tune 4, scenarios 5, worked example 9,
  breadcrumbs 9), F2 knowledge checks = 6, and **no horizontal overflow at 390 px**.
- **Negative control** — mutating the page (dropping the "Scenario playbooks" heading and one
  breadcrumb) makes the checker exit **1** with **3 FAIL**s; restoring the file returns it to
  md5 `332b9ad7…` and **36/36** — so the gate is not vacuous.
- **Regression** — the pre-existing `tools/verify_servicenow_es6_overflow.mjs` still reports
  **RESULT: PASS** (grid 900/900, all 5 `pre` blocks no overflow, sweep PASS at 390/768/1024/
  1280/1440 px, zero page errors).

## 5. Deployment status

- **Local:** updated and verified as above; `git status` shows the page as the only modified
  project file for this work plus the new checker and this doc.
- **Live:** **not yet uploaded.** The live site still serves the previous 408,213-byte version
  (`35b23468…`), so local ≠ live until `python3 upload_javascript.py` runs (server-side `SIZE`
  is then asserted by `verify_javascript.py`).
- **Commit / push:** pending operator go-ahead, scoped to the three files above only — the
  working tree carries unrelated modifications from other work, which must not ride along.
