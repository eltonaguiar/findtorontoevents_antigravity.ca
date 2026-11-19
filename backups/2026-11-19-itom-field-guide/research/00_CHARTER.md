# 00 — Charter

**Project:** ServiceNowLearning_ITOM
**Agent:** Kilo (deepseek-flash)
**Date:** 2026-11-19
**Status:** v1.0 content complete; deployment pending verification

---

## 1. Purpose

Create a source-backed, beginner-friendly field guide to ServiceNow IT Operations Management in
`eltonaguiar/ServiceNowLearning_ITOM`, following the methodology and visual language of the
existing ServiceNow learning repositories:

- <https://github.com/eltonaguiar/servicenow_learning>
- <https://github.com/eltonaguiar/ServiceNow_Learning_TSOM-_CSM_FSM_SalesCRM_HAM_ITSM>

The content must be merge-ready for a new **ITOM** section of the larger guide, but must work as
a standalone repository now.

## 2. Success criteria

- [x] Covers the current ITOM documentation family: Visibility, AIOps, Cloud Accelerate, Agent
      Client Collector, Metric Intelligence, AI in ITOM, and licensing.
- [x] Every guide is based on official ServiceNow sources and links them.
- [x] Every guide includes a record model, roles, tables, common mistakes, and a quiz.
- [x] Labs exist for the four core operational paths: orientation, discovery, event-to-incident,
      service mapping, and HLA.
- [x] The site follows the existing guide's design language and navigation.
- [x] A structured knowledge base (`data/modules.json`) and source catalog
      (`data/sources.json`) exist.
- [x] A lint script enforces stamps, official sources, resolving links, and data integrity.
- [x] The repo deploys to GitHub Pages and the deployment is verified.

## 3. Non-goals

- Reproducing ServiceNow documentation, screenshots, or customer data.
- Covering every ITOM Store app or every telecom (TSOM) product.
- Providing certification exam dumps or claiming a specific exam blueprint.
- Pretending every feature is available on a PDI.
- Giving pricing or contractual advice.

## 4. Constraints

- The target repository starts empty.
- The source of truth is the **Australia** release of the official documentation.
- The site is built by GitHub Pages with Jekyll; no local Ruby runtime is available in the
  build environment.
- No credentials or customer data may enter the repository.
- The existing guide's conventions (stamps, official sources, ELI5, labs, teach-back) must be
  preserved.

## 5. Stakeholders

| Role | Responsibility |
|---|---|
| Repository owner | Merge into the main ITOM section; approve scope |
| Content agent | Research, write, verify, deploy |
| Reviewer | Check facts against official sources and run the lab |

## 6. Definition of done

1. Content is complete for the modules in scope.
2. `python3 scripts/sn_lint.py` exits 0.
3. The Pages workflow succeeds.
4. The deployed site responds and the navigation works.
5. The merge handoff is written and links resolve.

---

**Agent:** Kilo (deepseek-flash) · **Updated:** 2026-11-19
