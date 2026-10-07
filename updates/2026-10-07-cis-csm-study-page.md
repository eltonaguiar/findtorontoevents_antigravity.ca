# CIS-CSM study page: research, build, and deploy

## Why

`https://findtorontoevents.ca/servicenow/CIS-CSM` returned **404**. The CIS-VR briefing at
`/servicenow/CIS-VR/index.html?curriculum=<sha>#domain-1` was the model to follow, but the
CIS-CSM page had to be grounded in current official ServiceNow sources and stay practical:
tables, setup wizard, plugins/modules, cost, related credentials/micro-certifications, and a
tiered course list.

## Research sources (all official servicenow.com)

- **CIS-CSM mainline exam blueprint** — `learning.servicenow.com` KB0011529 (updated
  November 2025). Rendered with headless Chromium because the Learning site is an SPA:
  5 domains / 27%, 38%, 17%, 8%, 10%; 60 questions in 90 minutes; sample questions;
  recommended courses; Pearson VUE delivery; delta + CMP maintenance.
- **Cost of mainline certification exams** — KB0013317 (updated September 2026): all CIS
  exams **$450 USD**, CSA/CAD/CAS-PA $300; on-demand training free but exam purchased
  separately; ILT includes one free attempt.
- **CIS-CSM credential page** — `course_id=02542b1d4734f6d0b8d109b4f16d4337` (prerequisite
  chain, exam registration, recommended-course sequence).
- **CSM Implementation Workshop syllabus** — KB0012979 (prerequisites and recommended
  coursework before the exam).
- **CSM product docs** (release `Brazil`, latest family): tables installed with CSM,
  configuring case types (documents **Customer Service > Administration > Guided Setup**,
  role `csm_guided_setup_user`), additional plugins table (Zurich), activate plugins,
  quick start tests, configure overview, case API, CRM data models.
- **Course links** pulled from the CSM Fundamentals achievement page and targeted catalog
  searches, including the newest English on-demand **CSM Essentials (Australia)**,
  `course_id=55a812f0976acb102192b37de053af4e` (23h43m).
- Release naming verified: Zurich (last city name) → **Australia** (GA May 2026) →
  **Brazil** (current family in the docs as of Sept 2026).

## What was built

New self-contained page `findtorontoevents.ca/CIS-CSM/index.html` (dark theme, same
structure as the live CIS-VR guide):

1. Credential at a glance (blueprint + registration links)
2. Format, cost, and maintenance table (60/90, $450, Pearson VUE, deltas/CMP, MeasureUp)
3. Five-domain curriculum map with official weights
4. One lesson per domain, each with sub-topic blocks, a practice task, a
   "Check your understanding" self-check, and official reading links
5. Key tables (from the official "Tables installed with CSM" doc + install base item)
6. Getting started: **yes, there is a setup wizard** — Customer Service Guided Setup —
   plus a plugin/module checklist and plugin identifiers
7. Implementation sequence
8. **Course tier list** (Tier 1 foundations → Tier 2 blueprint-required → Tier 3 depth →
   Tier 4 practice/reference), with ServiceNow University links and release labels
9. Related credentials and micro-certifications (CSA, CIS-DF, and the micro-cert badges
   whose topics map onto the CIS-CSM domains)
10. Official reference links

Also added `tests/test_cis_csm_curriculum.py`, a dependency-free regression test (domain
weights total 100, each domain has enough lesson text + official links + practice +
self-check, unique ids, every internal anchor resolves, every external link is on
`servicenow.com`, and the practical markers — guided setup, $450, 60 questions, Pearson,
table names, tiers, micro-certification, deltas, MeasureUp, Now Create — are present).

## Verification

```sh
python3 tests/test_cis_csm_curriculum.py     # Ran 3 tests ... OK
```

- All 39 external links HTTP 200, except the two `www.servicenow.com` marketing pages
  (`/products/customer-service-management.html` and the Credentialing Program Guide),
  which return **403 Access Denied to automated clients** — bot protection, not dead
  links; the journey URL was copied from the official credential page.
- Deployed via FTP (ftplib, credentials from `FTP_SERVER`/`FTP_USER`/`FTP_PASS`) to
  `/findtorontoevents.ca/servicenow/CIS-CSM/index.html`.
- Live checks: `200` for `/servicenow/CIS-CSM`, `/servicenow/CIS-CSM/`, and
  `/servicenow/CIS-CSM/index.html`; downloaded bytes **identical** to the committed source.
- Headless Chromium smoke test of the live URL with `?curriculum=smoke#domain-2`:
  14 sections, 20 topic blocks, TIER 1–4 present, every `#anchor` resolves, hash
  navigation works, **0 console errors**.

## Deployment target

`/findtorontoevents.ca/servicenow/CIS-CSM/index.html` (source of truth:
`findtorontoevents.ca/CIS-CSM/index.html`). Re-run the FTP upload after any edit —
the hourly site sync does not pick this path up automatically.
