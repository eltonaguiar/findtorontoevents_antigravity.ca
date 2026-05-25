# Incidents Triage Consult — grok

**Date:** 2026-05-25
**Engine:** grok
**Prompt:** see /tmp/consult_prompt.md (also reproduced inline below)

## Reply

```
**1. Process shape: too heavy for 38 curated rows.**

The CLAIM→INVESTIGATE→PROPOSE-FIX→VERIFY loop with separate engines + full reports/triage/ artifacts is over-engineered for a one-off multi-AI audit snapshot that the seed script largely hardcodes today. It makes sense once you have continuous discovery feeding the tables (e.g., db_health.json, edge_decay, forward-validator output). For now: keep the DB + cli_track.py as source of truth, add a lightweight weekly "stale P0 sweep" by one designated agent (or swarm), and require a short `reports/triage/INCIDENT_<id>.md` only for P0s. The high-value pieces (append-only seed, post-render P0 regression diff, TRIAGE DASHBOARD summary at top of incidents.html) should land immediately; the rest can wait until volume or live ingestion justifies ceremony.

**2. First priority: inverted ML calibration + smart_picks_engine 35% weight (and the trust_score NULL that blocks HC).**

COT over-emission is flashy and embarrassing (fake DSR=1.0/WR=86.5% SUPREME EDGE poisons one narrative cell), but the calibration inversion + heavy weighting is systemic: it actively ranks every downstream pick, including those feeding the dashboard users see and potentially size on. It is the single largest "garbage signal at the top of the funnel" problem. Trust_score NULL is a close second because it makes the entire High-Conviction overlay unverifiable (Goal #1 core claim). Fix the ranker/calibration first, then the COT dedup + narrative correction. COT is reputation-risk; the ranker bug is operational daily damage.

**3. Biggest unstated risk: root data corruption making every performance number (asset_class_health, Tier claims, PF/WR, "phenomenal" verdict) potentially garbage.**

39% PnL integrity drift, 56k+ ghost rows (one cohort alone 20k identical MATIC entries), WON status rows averaging -41% PnL, 29M open bloat with validator frozen 270h, signal_outcomes at 0.09% coverage, FOREX -106k% outliers, UNKNOWN asset_class on active picks — this is not "a few bugs." This is the foundation the entire /audit story and Goal #1 claims rest on. If the input tables are this dirty, the "Tier 2 candidate" numbers and mutation/money-ready decisions are untrustworthy no matter how pretty the UI.

**4. Workflow changes to cut churn.**

- Make the seed strictly append-only / state-preserving today (ON DUPLICATE KEY only touches updated_at and immutable fields; never status/assigned/resolution/reporter).
- Add a stable fingerprint (title+key description hash or source_ref) so re-running the same audit session doesn't create new rows.
- Add the post-render job that diffs JSON for P0 OPEN→RESOLVED→OPEN flips or age>7d escalation (high signal).
- Only run the full render+commit+push when the funnel actually produced new rows or on manual dispatch; skip the "[skip ci]" churn commit on pure no-op nights.

The triage process plus these four changes turns a noisy curated backlog into a credible, low-churn incident system without over-engineering the current 38-row state.
```
