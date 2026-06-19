# Audit dashboard payload-contract validation — 2026-06-13 (loop iteration 15)

Read-only validation of the `/audit` frontend↔backend contract for the measurement fields (FWD WR / Track / verified-alpha / HC), via the dashboard-contract-reviewer + my verification of the key lines. **5 confirmed issues; the FOREX HC-threshold mismatch is the most measurement-critical (false HC badges on a not-money-ready class).** No code changed here — fixes are owner judgment calls (live-product thresholds + the dashboard generator that must not be run locally).

## Issue 1 (MAJOR, measurement-critical) — HC win-rate thresholds disagree between the JS gate and the Python gate, on all 3 classes

Verified values:

| Class | `hc_filter.js` (live dashboard HC button) | `tools/dashboard_hc_rules.py` (Python money-ready gate) | Divergence |
|---|---|---|---|
| CRYPTO | 60 (`:35`) | 40 (`:28`) | JS 20pp STRICTER |
| EQUITY | 55 (`:36`) | 50 (`:29`) | JS 5pp stricter |
| **FOREX** | **45** (`:37`); relaxed 40 (`:49`) | **55** (`:30`), 60 fallback (`:261`) | **JS 10–15pp LOOSER** |

**Impact:** the dashboard's HIGH CONVICTION button shows HC badges for FOREX picks at ≥45% FWD WR, while the Python gate rejects them below 55–60%. Given this session proved FOREX (`non_crypto_consensus`) is **not money-ready** (net PF 0.76; gross edge dies sub-1bp), surfacing HC badges on sub-55% FOREX picks is exactly the "embarrassing loser" display the operator wants eliminated.
**Recommendation (owner decision — thresholds were deliberately tuned, per the JS comments):** pick ONE source of truth and reconcile both files. Recommend aligning to the Python gate (FOREX→55) since it's the money-ready authority; at minimum, make the two files import the same constants so they can't drift.

## Issue 2 (MAJOR) — `is_verified_alpha` / `hc_tier` declared in the generator schema but never written

`dashboard_generator.py:292` lists them in the enrichment allowlist, but the generator never calls `stamp_pick_quality.stamp_picks()` (which writes them at `stamp_pick_quality.py:455-456`). Result: 0/all picks carry these fields. The page itself doesn't break (it reads the top-level `verified_alpha` cohort), but any API/tool consumer reading `pick["is_verified_alpha"]` gets silent `null`.
**Recommendation:** either wire the generator to call `stamp_picks()`, or remove the fields from the schema allowlist and document they're DB-layer only.

## Issue 3 (MAJOR) — `sym_track_total/wins/losses` absent from all `recent_closed` picks

The generator writes these only in the active-picks enrichment loop (`dashboard_generator.py:15933-15935`); 0/1746 closed picks have them, yet the frontend reads them for the closed-view Track tooltip (`template.html:8171,8189,8190`). Closed Track detail silently falls back to strategy-wide.
**Recommendation:** apply the same enrichment to `recent_closed`, or confirm the omission is intentional (leakage avoidance) and document it.

## Issue 4 (MINOR) — `at_issue_strat_fwd_wr` units mismatch ([0,1] vs [0,100])

Snapshot stores it as a ratio while `strat_fwd_wr` is percent; rescued by `template.html` `_normFwdWrPct()` (×100 when ≤1.5) but latent. **Recommendation:** normalize to percent at snapshot time (`dashboard_generator.py:315`).

## Issue 5 (MINOR) — INCIDENT_OVERALL#136 confirmed: track keys are direction-blind

`_track_stats_key(strategy, symbol)` → `f"{strategy}::{symbol}"` (`dashboard_generator.py:5447-5449`); `buildVerifiedEdgeIndex` uses `s+'||'+sym` (`template.html:2879`). Neither includes direction, so a strategy traded both LONG and SHORT on the same symbol blends outcomes. This session's data shows direction matters enormously (FOREX `non_crypto_consensus` LONG PF 3.13 vs SHORT 1.54), so direction-blind track stats can mis-rate a pick. **Recommendation:** add direction to the key — `f"{strategy}::{symbol}::{direction}"` — in both the generator and `buildVerifiedEdgeIndex`.

## Notes
- All findings carry file:line evidence; the threshold values in Issue 1 and the #136 keys in Issue 5 were independently re-verified.
- Generator-side fixes (Issues 2–5) require running/regenerating the dashboard, which per CLAUDE.md must not be done locally — they're flagged for the generator owner.
- Issue 1 (hc_filter.js) is live-product config that was deliberately tuned — reconciliation is an operator/owner call, not a unilateral edit.
