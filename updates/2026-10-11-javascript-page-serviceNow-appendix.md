# 2026-10-11 — JavaScript reference page: added a 16-part appendix

## What was requested

Add an appendix to `/servicenow/javascript/index.html` covering "additional
topics", built and driven by the responsibilities in a Sr ServiceNow
Application Development Engineer role (Amazon OpsTech Solutions, Job ID
10373484). Across several follow-up messages the scope grew to include:

- Application administration & configuration
- Data services
- Web service integrations (REST, SOAP) — with an explicit inbound vs outbound
  "go-to tools" section
- Advanced Glide/JS APIs
- Deploying update sets along a DEV → UAT → PROD cycle
- Platform-level optimization / page-load latency reduction, incl. a concrete
  playbook for "a page is slow — business rule, client script, or DB?" using
  the clock icon / `stats.do` / Transaction Log / Session Debug
- Technical administration & maintenance of ServiceNow IT Business Management
  (ITBM / SPM)
- Creating workflows, with a concrete ITBM "service improvement" example
- Leading release upgrades — technical **and** stakeholder management
- Coordinating system updates/patches/config changes with SDEs, including the
  documentation sites beyond the instance
- User training & communications
- Mentoring on ITBM project planning, design, and estimating
- Agile Scrum / Kanban
- Platform architecture / scale / upgrade-safe patterns, including a full answer
  to "how do you process 100,000 inbound API requests without hitting
  transaction-quota limits or spiking latency?"
- A ServiceNow interview Q&A section

## What was added

File: `findtorontoevents.ca/servicenow/javascript/index.html`

A new **Appendix** TOC group (16 entries) and 17 appendix sections (A–P, where
F2 is the slow-page playbook). Each section uses the page's existing design
system only — `h2`/`h3`, `.table-wrap`/`.table-map`, `.notice`, `.lifecycle`,
`.code-card` + `.code-toolbar` + `copyCode(this)`, `.checklist`,
`.source-list`, `.section-chip` — so it matches the rest of the page with no
new CSS.

Sections:

| id | Title |
|----|-------|
| `appendix-admin` | A. Administration & Configuration (users/roles, ACLs, tool choice, BR types, forms, update sets/scoped apps) |
| `appendix-data` | B. Data Services (import-sets lifecycle, transform maps, scripted import, CMDB/CSDM, relational reporting) |
| `appendix-integrations` | C. Web Service Integrations (outbound REST/SOAP, inbound Scripted REST, **inbound vs outbound go-to-tools table**, async/events) |
| `appendix-advanced-js` | D. Advanced Glide & JS APIs (GlideRecord surface, GlideAggregate, GlideDateTime, gs, class pattern, GlideElement) |
| `appendix-update-sets` | E. Update Sets: DEV → UAT → PROD (8-step promotion, what sets don't carry, team discipline) |
| `appendix-optimization` | F. Platform Optimization & Page-Load Latency (the 5 layers, debug tools/breadcrumbs, common wins) |
| `appendix-diagnosing` | F2. Diagnosing a Slow Page — step-by-step playbook (clock/stats.do first, then Transactions, Session Debug, Slow Queries) |
| `appendix-itbm-admin` | G. ITBM Technical Administration & Maintenance |
| `appendix-workflows` | H. Building Workflows (Flow Designer vs Workflow Editor + ITBM approval/provisioning example) |
| `appendix-upgrades` | I. Leading Release Upgrades (technical activities + stakeholder/management activities) |
| `appendix-sde-coordination` | J. Coordinating Updates with SDEs (check table incl. external docs sites, ordering, rollback) |
| `appendix-training` | K. User Training & Communications |
| `appendix-itbm-mentoring` | L. Mentoring on ITBM Planning, Design & Estimating |
| `appendix-agile` | M. Agile Scrum / Kanban on ServiceNow |
| `appendix-ops` | N. Platform Ops, Maintenance & Vendor Interface |
| `appendix-patterns` | O. Upgrade-Safe & Scale Patterns (+ the 100k-requests scale answer) |
| `appendix-interview` | P. ServiceNow Interview Q&A (Sr App Dev Engineer) |

Also updated the hero badge from `28 sections` to `28 sections + 16-part appendix`.

## Notable content — the 100k-requests answer (Appendix O)

The architectural answer interviewers look for: put a **queue in front**
(SQS/Kafka/API gateway), ingest-to-staging with an immediate `202 Accepted`,
drain with a **bounded pool of async workers**, batch where the contract allows,
keep it idempotent on an external key, raise the REST rate limit only *after*
the queue absorbs the burst, and track queue depth in Performance Analytics —
so the REST transaction quota and interactive latency are never touched.

## Verification

- **TOC integrity:** all 46 `nav.toc` links resolve to an element id; zero
  dangling targets (`missing targets: []`).
- **Structure (local, headless Chromium):** 17 `section[id^=appendix-]`
  rendered, each with a non-null `h2`, non-zero height, `display: block`;
  zero `pageerror` events.
- **Visual:** screenshot of Appendix F2 confirmed the dark theme, the sidebar
  "Contents" (with the new Appendix group), section chip, numbered steps,
  notice box and table all render correctly.
- **Live (after deploy):** `curl` shows all 17 `id="appendix-…"` present on
  https://findtorontoevents.ca/servicenow/javascript/index.html ; a headless
  check confirmed `appendixSections: 17`, `tocAppendix: 17`, the "Go-to tools",
  "100,000" and "Interview Q" content all present, and **zero JS errors**.

Deployed with `python3 upload_javascript.py`.

## Currency note

Content was written from established ServiceNow platform knowledge and the
official doc structure (breadcrumbs, table names, API names). ServiceNow ships
two releases a year, so per-release specifics (e.g. exact rate-limit property
names, plugin versions) should be re-checked against the instance's release via
docs.servicenow.com before being treated as authoritative.
