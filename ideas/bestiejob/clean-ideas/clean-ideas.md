# BESTIEJOB — Clean ideas (deduplicated)

**Scope:** ServiceNow/Salesforce developer + related ITSM/CMDB/ITAM roles, **Toronto/GTA and Canada-remote**.  
**Policy:** source-first, compliant collection (APIs/feeds/open data/JSON-LD; respect ToS/robots/rate limits; no auth/CAPTCHA/IP evasion). No private contact data. Cite certainty; mark `<uncertain>` where unverified.

## 1) Fix & stabilize the pipeline (P0)
| ID | Idea | Why | Status |
|---|---|---|---|
| C-01 | **Block gated/paywall domains at ingest + merge + build** (`job_source_truth` blocklist/config/env); purge existing gated canonicals to a role ledger with xref links | Truth-check failing on `main` (35 gated rows observed); prevents reintroduction | observed need / unlanded local bundle |
| C-02 | **Harden shared-writer publish**: bounded multi-attempt fetch→rebase→push for gap-channels and similar workflows | Commit-and-push failure after successful work (contention) | observed need |
| C-03 | **Resolve `board invariants` ratchet failures** via data/logic fixes or justified re-baseline with audit trail | Gate blocks on baseline debt/regressions | observed need |
| C-04 | **Actionable CI diagnostics** (grouped causes, affected rows/URLs, artifacts) for truth/invariant gates | Faster remediation, less guesswork | proposed |

## 2) Data quality & compliance gates (P0/P1)
| ID | Idea | Why | Status |
|---|---|---|---|
| C-05 | **Absolute source dates only**; no guessed dating; hot windows for freshness | Board integrity/freshness | observed practice / reinforce |
| C-06 | **Liveness policy**: dead=404/410/451; tolerate bot-walls/transient errors per policy; reverify before publish | Drop closed roles without false positives | observed practice |
| C-07 | **Dedupe stack**: normalized canonical URL + `title|company|city` fingerprint + ATS requisition/content key; resolve redirectors safely | Collapse mirrors/reposts/geo dupes | observed practice / extend |
| C-08 | **Geo/remote eligibility**: Toronto/GTA/ON/Canada or explicit Canada-remote; exclude US-only/ambiguous remote; tag GTA submarkets | Match target market precisely | proposed/partial |
| C-09 | **Minimum-data & licensing hygiene**: store canonical URL, employer, title, location, dates, hash/evidence; link out; avoid uncertain full-text republication | Compliance/maintainability | proposed (strategy-aligned) |

## 3) Relevance & matching (P0/P1 yield)
| ID | Idea | Why | Status |
|---|---|---|---|
| C-10 | **Two-tier matching** (A: strong platform/cert in title/company/fields; B: body match requires platform/cert + role-intent; context-aware exclusions) | Capture CSA/CAD/CIS/module mentions beyond titles, reduce false positives | proposed |
| C-11 | **Expanded token/query library**: SN/SF + CSA/CAD/CIS-* + ITSM/ITOM/ITAM/CMDB/HRSD/CSM/GRC/SecOps + Apex/SOQL/LWC/Flow/CPQ/cloud modules + platform admin/dev terms | Coverage of real role variants | proposed |
| C-12 | **Per-profile batching** (SN dev/admin, SF dev/admin, ITSM/CMDB/ITAM platform) with geo splits (Toronto, Mississauga, Markham, Etobicoke/GTA, Ontario, Canada-remote) | Prevent crowd-out, improve precision | proposed |

## 4) Sourcing strategy (P1/P2, source-first)
| ID | Idea | Why | Status |
|---|---|---|---|
| C-13 | **Company universe as core asset**: SN/SF partners (Partner Finders, tiers), consultancies, customers/repeat hirers, verified event employers | Higher signal than blind board search | proposed (`<uncertain>` specific rosters) |
| C-14 | **Primary ingestion = direct ATS APIs & career sites** (Greenhouse/Lever/Ashby/Workable/SmartRecruiters/Workday/Phenom/Oracle + JSON-LD/sitemaps where permitted); aggregators for discovery/validation only | Cleaner, fresher, defensible | proposed/partial in repo |
| C-15 | **Batch 1 (highest yield): company portals/ATS**, few tenants at a time, probe/health-check before trust | Scales proven mechanisms | proposed |
| C-16 | **Batch 3: Toronto/GTA + Canada-remote geo feeds** (aggregator geo queries, verified municipal/civic boards) | Target-market coverage | partial; municipal endpoints `<uncertain>` |
| C-17 | **Batch 2: Canadian gov/public sector** (Job Bank certain) + verified boards with date adapters | Unique, compliant postings | partial; others `<uncertain>` |
| C-18 | **Batch 4: partners/customers/conference ecosystem** converted to direct sources | Opportunistic high-value leads | opportunistic; `<uncertain>` lists |
| C-19 | **Canada Job Bank open data** as supplementary enrichment/discovery (structured fields) | Coverage/validation | proposed (source certain as concept) |

## 5) Classification, lifecycle, ranking (P2)
| ID | Idea | Why | Status |
|---|---|---|---|
| C-20 | **Two-stage classification**: deterministic rules → AI for ambiguity with confidence + evidence; review queue for low confidence | Accurate SN/SF/Other bucketing | proposed |
| C-21 | **Lifecycle tracking**: `first/posted/updated/last/removed`, active/closed states from source signals | Trustworthy freshness | proposed/partial |
| C-22 | **Transparent ranking**: category/geo-remote fit, direct-source preference, freshness, completeness | User value | proposed |
| C-23 | **Daily diffs & datasets** (JSON/CSV/UI) with filters | Consumability | proposed/partial |

## 6) Operations & ownership
| ID | Idea | Why | Status |
|---|---|---|---|
| C-24 | **Assign owners to red gates** and land validated fixes on `BESTIEJOB` `main` with CI proof | Unblocks pipeline health | observed gap |
| C-25 | **Owner decision on first build angle** (recommended: C-15 + C-10/C-11) | Unparks v2/v3 execution | observed gap |
| C-26 | **COMS read/history capability** or Git-based durable handoff convention for “missed while away” | Coordination reliability | observed gap |

## Deduplication notes (what was merged)
- Multiple mentions of gated-domain blocking/purge/ingest enforcement → **C-01** (+ QA aspects).
- Push contention/retry hardening across symptoms → **C-02**.
- Absolute dates/liveness/dedupe/geo checks repeated in QA and batches → **C-05–C-08**.
- Cert/body/title-expansion, query matrices, profile batching → **C-10–C-12**.
- ATS-direct/company-universe/aggregator-as-discovery/source-first compliance → **C-13–C-15, C-09**.
- Four sourcing angles consolidated into **C-15–C-18** with certainty markers.
- User strategy (lifecycle, classification, ranking, datasets, Job Bank) → **C-19–C-23**.
