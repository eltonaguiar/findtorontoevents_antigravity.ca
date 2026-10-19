# 2026-10-11 — JavaScript appendix: L6 interview deep-dive + knowledge checks (all sections)

## Context

Feedback from Grok: a phone-screen prep brief for an Amazon **Sr ServiceNow
Application Development Engineer (OpsTech Solutions)** interview. Requests:

1. Research further and **double-check** the technical claims in the brief,
   then document.
2. Add the brief's content (L6 bar, live-coding scenarios, governance talking
   points, STAR/behavioral prep, questions to ask).
3. Add **knowledge checks for each section** so readers verify they're actually
   learning the key points.

## Research / verification performed

ServiceNow's live docs are JS-rendered and sign-in-walled (docs.servicenow.com
"moved/deleted" errors; developer.servicenow.com SPA needs auth; Google/DDG
blocked the automated fetch), so detail pages couldn't be scraped. The brief's
technical claims were verified against established ServiceNow behavior:

| Claim | Verdict |
|-------|---------|
| Client-callable Script Include uses `Object.extendsObject(AbstractAjaxProcessor, {…})` | **Correct** (modern form; also needs "Client callable" = true) |
| Client calls `ga.addParam('sysparm_name', …)` + `ga.getXMLAnswer(cb)` | **Correct**; `getXMLAnswer` returns a **string**, `getAnswer()` returns XML (legacy) |
| `setWorkflow(false)` skips business rules | **Correct but nuanced** — it suppresses BRs **and** workflow/flow triggers; it does **NOT** bypass ACLs. This nuance was added explicitly. |
| `autoSysFields(false)` stops `sys_updated_on/by/mod_count` updates | **Correct** |
| `updateMultiple()` for bulk update | **Correct** — updates matched rows to the **same** values; not for per-row-varying data |
| `GlideAggregate` for counts instead of looping | **Correct** |
| `getRowCount()` has a 10,000 default cap | **Correct** |
| `GlideRecordSecure` enforces ACLs; `GlideRecord` does not | **Correct** |
| Business-rule types: before/after/async/display/query | **Correct** (five types) |
| Timing split Client/Server/Network/DB via `stats.do` | **Correct** |

## What was added

File: `findtorontoevents.ca/servicenow/javascript/index.html`

### 1. New Appendix R — "L6 Interview Deep-Dive"
- The L6 mindset (patterns/standards, ownership language, ACL-aware + upgrade-safe).
- **Five live-coding scenarios** with full code + talking points:
  1. Query open high-priority incidents for a group (`GlideRecordSecure`,
     `addQuery IN`, `setLimit`, returns array).
  2. Bulk update without firing BRs/notifications (`setWorkflow(false)` +
     `autoSysFields(false)`, chunked) — **with the ACL caveat called out**.
  3. GlideAjax `onChange` → client-callable Script Include using
     `Object.extendsObject(AbstractAjaxProcessor, {…})` + `getXMLAnswer`.
  4. GlideAggregate P1/P2 last-30-days by category.
  5. Refactor client GlideRecord work to GlideAjax + server (pattern table).
- Server-vs-client decision table, governance talking points, a STAR/story
  table (mapped to Leadership Principles, weighted to Deliver Results), the
  questions to ask the interviewer, and a recitable decision checklist.

### 2. Knowledge checks — every appendix section
Added a reusable, JS-free `.kcheck` component (native `<details>`, styled to
match the page) and a block of section-specific Q&A at the **end of each
appendix section A–P and R** (18 blocks, 62 questions total). Answers reveal on
click; the summary badge flips from **Q** to **A** when open.

Sections covered: A Administration, B Data Services, C Integrations,
D Advanced APIs, E Update Sets, F Optimization, F2 Diagnosing a Slow Page,
G ITBM, H Workflows, I Upgrades, J SDE Coordination, K Training,
L Mentoring, M Agile, N Ops, O Patterns/Scale, P Interview Q&A, R L6 Prep.

### 3. Fixes
- Corrected a malformed tag in the Workflows knowledge-check answer
  (`task</em></strong>` → `task</strong>`).
- Hero badge updated to "28 sections + 19-part appendix".

## Verification

- **TOC integrity:** 48 `nav.toc` links, zero missing targets.
- **Structure:** 19 `section[id^=appendix-]`; 18 `.kcheck` blocks; 62
  `<details>` questions; 0 `pageerror` events (local + live).
- **Visual:** rendered screenshots confirm the knowledge-check box (headed,
  Q-badges, expandable answers) and Appendix R (code cards + checks) look clean
  on the dark theme; sidebar TOC intact.
- **Live after deploy:** `curl` shows 18 `class="kcheck"` and the
  `appendix-l6-prep` section present.

Deployed with `python3 upload_javascript.py`.

## Currency note

The ServiceNow APIs and type names above are stable and widely documented;
per-release specifics (exact semaphore/transaction-quota property names, menu
labels) should still be confirmed against the instance's release. The
live-coding answers focus on the *pattern and trade-off* (the L6 signal) rather
than brittle per-release detail.
