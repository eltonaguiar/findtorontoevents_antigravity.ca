# 7-Day Pilot Execution Tracker — 2026-11-18 (day 0)

**Owner:** kilo · seat `inbox/gx10-c9b9/bestiejobharvest-v2/kilo`
**Pilot window:** 2026-11-18 → 2026-11-24 (day 0 → day 7)
**Equal request budget per angle:** 50 requests/angle/day (cron-adjusted after day 3)
**Same dev definition:** ServiceNow/Salesforce platform build role; EXCLUDE sales/marketing/recruiter
**Same location rules:** GTA + remote-CA (Ontario-eligible); reject non-CA
**Same date window:** list clock ≤ day-0 + 14 days
**Same canonical verifier:** Lever API `descriptionPlain` grep for platform+develop/integrations + duties read

## Per-angle day-0 baseline

| Angle | Sources | Requests day-0 | Verified | Notes |
|-------|---------|---------------|----------|-------|
| C: GTA cities | LinkedIn guest, Adzuna, local boards | 0 | 0 | aggregator rights question unresolved — private discovery only |
| A: Company portals | Lever (eqbank, versapay), Greenhouse (levio), Ashby (solink, rapdev), SmartRecruiters (servicenow) | 5 list probes | 2 | eqbank + versapay verified; staged in inbox/kilo--2026-11-18--v1.md |
| D: Partners/conference | glidefast, rapdev, newrocket, crossfuze, pentio, cea, alimentiv, ensiti, lanefour, tractionrec, ateko | 11 probes | 0 | all resolved: 8 out_of_scope, 2 verified_no_eligible_roles, 1 needs_manual_adapter |
| B: CA govt | Ontario/Canada govt job boards | 0 | 0 | not yet started |

## Day-1 → Day-7 checkpoint log

- **Day 0 (2026-11-18):** baseline recorded; 2 verified candidates staged; 11 tenants resolved.

## Metrics (to fill daily)

- incremental unique yield: _
- verification quality (verified÷reviewed): _
- issuer→discovery freshness lag (+48h, day 7): _
- cost per verified job: _
- exclusive vs shared finds: _

## Go/no-go (end of day 7)

- Promote angle if: ≥1 verified unique role + quality ≥70% + freshness lag ≤21 days + cost/verified ≤$0.10
- Suspend angle if: 0 verified after ≥50 requests + quality <50% + freshness lag >30 days
- Rotate angle if: consistently low yield across 3 consecutive days

## Next daily actions (cron-driven)

1. Re-probe verified Adapter list (lever/gh/ashby/SR) — 5 requests
2. Re-probe tractionrec BambooHR manually — 1 request
3. Re-probe govt boards (angle B) — 5 requests
4. Log metrics; commit; COMS on material change only
