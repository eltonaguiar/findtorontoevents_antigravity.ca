# 06 — Peer review

**Agent:** Kilo (deepseek-flash) · **Date:** 2026-11-19

The user asked to review peers' work in
`/home/eaguiar2015/findtorontoevents_antigravity.ca/.kilo/worktrees/` and update this guide
accordingly. This file records what was found and what changed.

---

## 1. What was found

The four `itomlearning*` worktrees (v1–v4) were empty clones of the findtorontoevents
repository at the same commit; they contained no ITOM content.

A separate peer build existed at `/home/eaguiar2015/ServiceNowLearning_ITOM` (uncommitted,
actively written during the same session). It included:

- README, index, Jekyll config/layout/assets
- `data/modules.json` and `data/sources.json`
- docs and labs, including topics this guide did not yet cover in depth:
  - Orchestration
  - MID Server
  - CMDB (ITOM perspective)
  - Now Assist for ITOM
  - Cloud Management (legacy naming)
  - Certification alignment

## 2. Assessment

| Area | Verdict | Action |
|---|---|---|
| Structure and breadth | Good coverage of useful topics | Kept and built on in this guide |
| Roles (e.g. `sn_itom.admin`, `sn_itom.user`) | Not verified against official sources | Rejected; this guide uses verified roles (`discovery_admin`, `evt_mgmt_*`, `sm_admin`, etc.) |
| Table names (e.g. `alm_alert`, `discovery_plan`, `sn_itom.*`) | Many lack an official source | Rejected or re-verified; only official/seen tables are used |
| Certification table (exam weights, KB numbers) | Not independently verifiable here; changes over time | Not adopted; the guide points to Now Learning and the official certification programme instead |
| Now Assist for ITOM | Written as current | Corrected to state the Australia deprecation preparation and the Otto/MCP forward path |
| Cloud Management naming | Legacy | Replaced with the current Cloud Accelerate/Cloud Services Catalog naming |

The peer work is the peer's; this repository did not commit or copy it. Where the peer's topic
choice was good, this guide incorporated equivalents using verified official sources.

## 3. What changed in this guide because of the review

1. Added an **Orchestration-adjacent** automation scope (alert/CI remediation, cloud actions,
   LEAP, Ansible) without inventing a separate ITOM Orchestration product pillar.
2. Added a **CMDB foundation** guide with verified tables, CSDM, identification, and Service
   Graph Connectors.
3. Added **MID Server** depth inside Discovery (already present) and referenced it in
   automation/orchestration.
4. Expanded **Now Assist / Otto in SOW** with verified alert-analysis, past-incident, alert-group
   description, and Probable RCA pages, plus the deprecation caveat.
5. Added **Cloud cost/capacity**, **Cloud Action Library**, and the **Cloud Migration Assessment
   retirement** correction.
6. Added **Resilience/security/compliance** coverage with verified backup-pattern and audit
   sources.

## 4. Method note

This guide's rule from the charter stands: a claim is only "covered" when it can be pinned to an
official ServiceNow source or verified on the instance. Peer material that could not satisfy that
rule was not carried forward as fact.

---

**Agent:** Kilo (deepseek-flash) · **Updated:** 2026-11-19
