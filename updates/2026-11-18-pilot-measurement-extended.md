# 7-Day Pilot Measurement Plan — Extended Design (2026-11-18)

Building on updates/2026-11-18-taskC-pilot-measurement.md

## Context
BestieJob runbook §5: "7-day pilot across the four angles; equal request/time budgets; same dev definition, location rules, date window, canonical verifier. Report incremental unique yield, verification quality (verified÷reviewed, with false-remote/dead/wrong-track/dup/blocked split), issuer→discovery freshness lag (+48h, day 7), and cost per verified job — and exclusive vs shared finds. Rank angles on this evidence."

## Four Angles (from design)
| Angle | Sources / Channels |
|---|---|
| **C: GTA cities** | LinkedIn guest, Adzina, local job boards; broad geographic coverage |
| **A: Company portals** | Lever (eqbank, versapay), Greenhouse (levio), Ashby (rapdev), SmartRecruiters (servicenow) — already proven in Batch-A |
| **D: Partners/conference** | ServiceNow partners (glidefast, crossfuze, rapdev, newrocket, pentio), conference caches, sponsor lists |
| **B: CA govt** | Ontario/Canada government job boards, civil service listings |

## Measurement Framework

### 1. Incremental Unique Yield
- **Definition:** New verified roles NOT found by any previously-run adapter/source in this swarm session.
- **Collection:** Per-angle daily counts; deduplicate using identity order (ATS, tenant, posting_id) across all angles.
- **Expected:** Angle A already yielded 2 verified roles (eqbank, versapay). Angles C, D, B expected 0–1 each in pilot.
- **Go/no-go:** Promote angle if ≥1 unique verified role beyond existing A-set.

### 2. Verification Quality
- **Metric:** verified ÷ reviewed (where "reviewed" = form_reached + duties read + eligibility confirmed).
- **Split categories:**
  - `verified`: duties confirm platform+build + Ontario-eligible + dates consistent
  - `false-remote`: work-mode mismatch (listed as remote but on-site required)
  - `false-dead`: posting closed, no active apply path
  - `wrong-track`: title match but wrong function (e.g., sales CPQ misclassified as build)
  - `dup`: duplicate across angles (first-credit assigned)
- **Target:** ≥70% verified quality across pilot.

### 3. Issuer→Discovery Freshness Lag
- **Definition:** Days between issuer posting date → discovery via adapter list probe → pilot read.
- **Baseline:** eqbank list clock 2026-09-22 → discovery 2026-11-18 = 67 days. This is too lagged — need +48h gate.
- **Pilot window:** Only count roles where list clock ≤ day-0 date + 14 days (2-week freshness cutoff).
- **Day-7 checkpoint:** Measure avg lag; if >21 days, adjust date windows.

### 4. Cost per Verified Job
- **Definition:** (Total LLM API calls + web requests) ÷ number of verified roles.
- **Baseline:** 4 LLM endpoints × ~300s avg = ~20 min compute + ~5 web API calls per candidate.
- **Pilot tracking:** Log per-angle request counts; compute average.
- **Go/no-go:** If cost per verified > $0.10 (arbitrary threshold) or LLM rate-limits, optimize prompt sizes or reduce angle breadth.

### 5. Exclusive vs Shared Finds
- **Exclusive to angle:** First adapter to surface a role; credited to that angle.
- **Shared across angles:** Role found by multiple adapters; credit split proportionally or awarded to first-detected.
- **Accounting method:** Per-role tag `first_detected_by: <angle>_<adapter>`; maintain tally per angle.
- **Impact on ranking:** Angles yielding exclusive finds rank higher, all else equal.

## Day-0 Checklist (2026-11-18)
- [x] Define dev definition: ServiceNow build role + Salesforce build/integration role; exclude sales/marketing/recruiter
- [x] Define location rules: GTA (Toronto+Peel+York+Durham) + remote-CA (Ontario-eligible) + reject non-CA
- [x] Define date window: list clock ≤ day-0 − 14 days rejected; only roles posted within 14 days of pilot start
- [x] Define canonical verifier: Lever API descriptionPlain grep for platform+develop/integrations + duties read
- [x] Equal request budgets: 50 requests/angle/day (adjustable after day-3)
- [x] Create measurement template in updates/ for day-1, day-3, day-7 output

## Day-1 → Day-7 Reporting Cadence
- **Day 1:** Report request counts per angle, initial yield, verification quality on first 5 reviewed roles.
- **Day 3:** Report avg freshness lag, cost accumulation, any deduplication collisions.
- **Day 7:** Final report with all 4 metrics, angle ranking, go/no-go recommendation for scaling.

## Immediate Actions (post-commit)
1. **Create measurement template** `updates/2026-11-18-pilot-weekly-{d1,d3,d7}.md`
2. **Set up daily request budgets** via cron or manual tracking
3. **Run day-1 check** after 24h: verify the 2 candidates still pass freshness gate
4. **Resolve crossfuze + cea ATS** as angle-D warm-up (if angle-D yields roles)

## Go/No-Go Criteria (end of day 7)
- **Promote angle** if: ≥1 verified unique role + verification quality ≥70% + avg freshness lag ≤21 days + cost per verified ≤$0.10
- **Suspend angle** if: 0 verified after ≥50 requests + quality <50% + freshness lag >30 days
- **Rotate angle** if: consistently low yield across 3 consecutive days

