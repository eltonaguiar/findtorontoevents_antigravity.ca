# 2026-11-19 — ITOM coverage expansion

**Agent:** Kilo (deepseek-flash) · **Repository:** ServiceNowLearning_ITOM

## What changed

Expanded the guide to fully cover the ServiceNow three-pillar ITOM model and the cross-cutting
foundation, verified against the Australia docs:

- Added a **CMDB foundation** guide (tables, CSDM/service instance, identification/reconciliation,
  Service Graph Connectors, impact).
- Added a **Automation and remediation** guide (SOW alert automation, alert/CI remediation,
  CCG and tag remediation, LEAP, Ansible, guardrails).
- Added a **Resilience, security, and compliance** guide (backup-resource visibility, change and
  configuration control, certificate/firewall/cryptographic audits, audit evidence).
- Added a **coverage map** page mapping every pillar and subtopic to its guide.
- Expanded **Discovery** with containers and Kubernetes (pattern, Visibility Agent, Explorer).
- Expanded **AI in ITOM** with Now Assist/Otto alert analysis, past-incident summaries, alert
  group descriptions, and Probable RCA, including the deprecation caveat.
- Expanded **Cloud Accelerate** with cost/capacity controls, Cloud Action Library, and the Cloud
  Migration Assessment retirement correction.
- Added a **peer review record** (`research/06_PEER_REVIEW.md`).
- Updated navigation, index, family map, README, study plan, roles/tables, common mistakes,
  glossary, module data, source catalog, and research artifacts.

## Why

The user asked to double-check coverage of the ITOM pillars and their subtopics, and to review
peer work. This expansion closes the identified gaps with verified official sources.

## Sources

Official ServiceNow Australia documentation only; every new page ends with its sources. See
`research/02_SOURCE_MATRIX.md` and `data/sources.json`.

## Verification

Run `python3 scripts/sn_lint.py` and inspect the deployed site (`research/04_VERIFICATION.md`).
