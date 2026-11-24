# 03 — Content decisions

**Agent:** Kilo (deepseek-flash) · **Date:** 2026-11-19

Decisions that shaped the guide, with the reason and the trade-off.

---

## 1. Pin to the Australia release

**Decision:** Use `/docs/r/australia/...` deep links and state "Docs release: Australia" in every
guide.

**Why:** Deep links are stable within a release but move between releases. Pinning makes the
source verifiable and the staleness visible.

**Trade-off:** A reader on a newer release may see a moved page. Mitigation: every guide links
the unversioned ITOM home and the source ladder explains how to re-check.

## 2. Use "ITOM AIOps", not "ITOM Health"

**Decision:** Use **ITOM AIOps** as the family name, while noting that older material and some
product links say **ITOM Health**.

**Why:** The Australia documentation section is ITOM AIOps. Pretending the legacy name never
existed confuses readers who search for it.

## 3. Correct the PCIE shorthand

**Decision:** Teach the official phases — **Scanning, Classification, Identification,
Exploration** — and mention PCIE only as a mnemonic.

**Why:** The existing ITOM guide in the TSOM repository describes "PCIE" as the phase model.
That is a teaching shorthand, not the official phase list. Exam answers and documentation should
use the official names.

## 4. Do not copy questionable table names from the earlier guide

**Decision:** Do not use `sn_tsom_*` or speculative table names. Use only tables confirmed in
official pages or visible in the platform dictionary.

**Why:** A plausible-looking fake table is worse than "verify in the dictionary". The earlier
guide's confidence labels were not a substitute for source verification.

## 5. Separate "what the docs say" from "what your instance shows"

**Decision:** Every guide has a "verify on your instance" posture; labs record observations and
gaps.

**Why:** ITOM behaviour depends on subscription, plugin, Store app version, domain, and
configuration. Universal claims are usually wrong somewhere.

## 6. No prices, no contract advice

**Decision:** Explain licensing models and prerequisites, but do not quote prices or tell the
reader what to buy.

**Why:** Prices and packaging are contractual and change. The official docs do not publish them.

## 7. No certification exam claims

**Decision:** Point to Now Learning and the certification programme, but do not claim an exam
blueprint or reproduce questions.

**Why:** Blueprints change and exam content is confidential. The labs teach the work, not the
test.

## 8. No screenshots of customer data

**Decision:** Use diagrams, tables, and text. No customer screenshots, credentials, or instance
URLs.

**Why:** Privacy and security. A learning repo is not a data leak.

## 9. State the AI packaging shift plainly

**Decision:** Lead the AI guide with the Australia deprecation of Now Assist for ITOM and the
move to Otto/MCP, then cover governance.

**Why:** A reader who builds on a deprecating surface without knowing it will have to rebuild.
The governance model outlives the feature list.

## 10. State the CPG deprecation plainly

**Decision:** Tell new deployments to use Cloud Services Catalog; explain CPG's supported status
for existing customers and the Workflow Studio migration.

**Why:** CPG is the most common source of stale cloud advice. The official page is explicit
about the Brazil-era change.

## 11. Reuse the existing visual language

**Decision:** Reuse the layout, CSS, and JS patterns from the TSOM module-guide repository, with
a new ITOM navigation and colour accents.

**Why:** The content will merge into that site. Visual continuity reduces the merge cost and
keeps the reader oriented.

## 12. Keep research artifacts out of the published site

**Decision:** Exclude `research/`, `meta/`, `updates/`, `data/`, and `scripts/` from the Jekyll
build.

**Why:** They are evidence and maintenance artifacts, not learner-facing pages. The README and
the merge handoff link to them on GitHub.

## 13. Labs must have a design-only path

**Decision:** Every lab that needs an entitlement or MID Server includes a design-only path.

**Why:** Most readers start on a PDI without ITOM entitlements. A lab that cannot run should
still produce a correct model and an honest gap list.

## 14. Use one source of truth for the module list

**Decision:** `data/modules.json` mirrors the site's module set; the lint checks that lab paths
exist and IDs are unique.

**Why:** A site can drift from its data. The lint makes drift visible.

---


## 15. Adopt the ServiceNow three-pillar model

**Decision:** Structure the guide around the ServiceNow-specific three pillars — Visibility,
Health/AIOps, and Cloud Accelerate — plus the shared CMDB foundation, rather than a generic
industry pillar list.

**Why:** The user's earlier broad pillar list was generic industry framing. The ServiceNow
model is the accurate scope for this repository.

**Trade-off:** Some generic industry topics (automation, resilience, compliance) are still real,
so they are covered as cross-cutting guides rather than ignored.

## 16. Correct Cloud Migration Assessment

**Decision:** State that Cloud Migration Assessment is no longer deployed, enhanced, or
supported, and tell readers not to plan new work on it.

**Why:** The input described migration tooling as current. The official Australia documentation
says it is retired; repeating it as current would be wrong.

## 17. Peer review: reject unverified roles and tables

**Decision:** Review the peer build in `/home/eaguiar2015/ServiceNowLearning_ITOM`, reuse its
valuable structure (Orchestration, MID Server, CMDB, Now Assist), but **not** its unverified
facts: roles such as `sn_itom.*` and table names without an official source.

**Why:** A plausible-looking role/table is worse than "verify in the dictionary". Facts that
cannot be pinned to an official page are marked or omitted.

See `06_PEER_REVIEW.md` for the record.

---
**Agent:** Kilo (deepseek-flash) · **Updated:** 2026-11-19
