# 2026-11-18 — divide-and-conquer dispatch + web verification (kilo)

**Owner:** kilo · seat `inbox/gx10-c9b9/bestiejobharvest-v2/kilo`
**Trigger:** `dbpasses.txt` authorization — dispatched 4 subtasks to local LLMs + real web verification of the 2 candidate-dev roles.
**Status:** 2 candidates verified. 10 tenants resolved to partial state. 4 LLM subtask outputs collected (quality varies; honest notes).

## A. Local LLM divide-and-conquer dispatch

Dispatched to 3 endpoints in parallel:
- **Task A → devstral:24b @ 192.168.2.32:11434/v1** — 11 tenant resolution + candidate verification checklist (273s)
- **Task B → devstral:24b @ 192.168.2.32:11434/v1** — SmartRecruiters detail pass + Workday gap_channels_scan routing (37s)
- **Task C → hermes3:8b @ 192.168.2.32:11434/v1** — 7-day pilot measurement plan (106s)
- **Task D → devstral:24b @ 192.168.2.32:11434/v1** — dedupe analysis + batch-A synthesis (97s)
- (Task D first attempt via deepseek-r1 put output in reasoning_content, not content → re-run via devstral.)

Outputs in `updates/2026-11-18-task{A,B,C,D}-*.md`.

**Quality notes (honest):**
- Task A: usable framework, but all tenant ATS marked UNKNOWN (LLM had no web).
- Task B: concise step-by-step design, usable.
- Task C: generic/repetitive (hermes3); covers the 4 metrics but shallow.
- Task D: reasonable dedupe rules + synthesis; usable.

These outputs are **scaffolding**, not verified facts. Real verification below.

## B. Candidate verification (real web, done by kilo)

Both candidates confirmed via read-only GET to Lever posting API + full duties read.

### Candidate 1 — EQ Bank (lever:eqbank) — Senior ServiceNow Engineer
- **Hosted URL:** https://jobs.lever.co/eqbank/1af36346-6dd1-475a-bee9-1d5e805452e8
- **Dept:** Infrastructure & Operations · **Work mode:** hybrid (Toronto) · **Commitment:** Full Time
- **Duties confirm platform+build:** "designing, developing, and supporting ServiceNow applications, workflows, catalog items, integrations, and the platform in general" / "leading the design, development, and delivery of major ServiceNow features and modules".
- **Geo:** Toronto (GTA) — Ontario-eligible ✓
- **List clock (lever createdAt):** 2026-09-22 — consistent with prior probe
- **Disposition:** `form_reached` — verified build role, duties confirmed.

### Candidate 2 — Versapay (lever:versapay) — Salesforce Developer
- **Hosted URL:** https://jobs.lever.co/versapay/7906bc29-f17e-44d2-a41b-334e6ce0608c
- **Dept:** Customer Operations · team Salesforce · **Work mode:** remote · **Commitment:** Regular Full-Time
- **Duties confirm platform+build:** "Salesforce Developer who will work closely with our existing platform team… ensure the platform remains scalable, secure, and reliable as we evolve… high-ownership position within a mature, integration-aware environment." Section titled "The Role — Salesforce Developer (Integrations & Platform)".
- **Geo:** Canada (Remote) — remote-CA bucket, Ontario-eligible ✓
- **US twin:** separate (must not dedupe to a US pay range)
- **Disposition:** `form_reached` — verified build role, duties confirmed.

**Verdict:** both candidate-dev leads are confirmed live, in-scope, duties-verified. No PII/credentials captured; stored as private leads in `updates/2026-11-18-batchA-leads.jsonl` (unverified duties → now `form_reached`).

## C. Tenant resolution (11 `resolve_employer`)

Probed official careers URLs for all 10 with a known site (cea has no URL yet). Findings:

| Tenant | Careers URL | Result | In scope? |
|---|---|---|---|
| alimentiv | https://alimentiv.com/ (careers /careers/) | Clinical trial mgmt (GI CRO); no lever/gh/ashby/smartrecruiters/workday/bamboohr on page | Likely out of scope — no platform-build track |
| ensiti | https://www.ensiti.com/ | IT/AI recruitment agency (staffing) | Out of scope — recruiter, not employer |
| lanefour | https://lanefour.com/opportunities/ | Salesforce admin + consultant roles (no dev track) | Out of scope per runbook (admin/consultant, not developer) |
| tractionrec | https://tractionrec.bamboohr.com/careers | BambooHR (not kit-supported) | Needs manual adapter |
| ateko | https://ateko.com/en/careers/ | ADP + FX Innovation (non-kit adapters) | Out of scope — non-kit ATS |
| pentio | https://www.pentio.com/ | Japanese company (ペンティオ株式会社); IDaaS/OneLogin/PKI | **Out of scope geo** — not Toronto |
| glidefast | https://glidefast.com/careers | ServiceNow consultant/architect roles (SecOps/IRM, ITAM, ITOM, CSM, HRSD, Portal, Solutions Consultant) — all consultant/architect, not dev | Out of scope — consultant/architect track, not developer |
| rapdev | https://www.rapdev.io/ | Ashby board links live; also Datadog & ServiceNow integration partner | In scope — Ashby tenant live, needs board API probe |
| newrocket | https://www.newrocket.com/careers | Greenhouse (`gh_jid`) — ServiceNow + Anthropic partner | In scope — Greenhouse tenant live |
| crossfuze | https://www.crossfuze.com/company/careers | ServiceNow Elite partner; no ATS link found on page | Resolve — careers page found, ATS unknown |

**cea:** no URL yet — still unresolved.

## D. Recommended next actions (priority order)

1. **Stage the 2 verified candidates** into the private sidecar as `form_reached` (duties verified).
2. **Verify rapdev Ashby** via correct Ashby API endpoint (`api.ashbyhq.com/...` boards probe returned non-JSON; use `jobs.ashbyhq.com/rapdev` + parse, or `ashbyhq.com/api/v1/...`).
3. **Verify newrocket Greenhouse** (`gh_jid` token; probe greenhouse API).
4. **Drop out-of-scope tenants** (pentio-JP, ensiti-recruiter, alimentiv-CRO, lanefour-consultant, ateko-adp, glidefast-consultant) from the developer-track candidate set.
5. **Resolve crossfuze + cea** ATS via deeper careers-page probe.
6. **Workday tenants** (big-5/consulting) via `gap_channels_scan.py` — still unrouted.
7. **7-day pilot** — use task C design, but make it specific to the 4 angles.
8. **Add rights field + classifier EXCLUDE (sales/marketing/recruiter)** before staging.

## E. No side effects beyond reads

All web probes were read-only GETs. No apply, no credentials used (service-now admin pass in dbpasses.txt was NOT touched — out of scope for job hunting; it belongs to the ServiceNow lab, not the job board). No secrets captured or exposed.