# RED-TEAM: Zoo Agent-2 ML Calibration Fix — Verdict

**Reviewer:** Claude Opus 4.7 (red-team)
**Date:** 2026-05-31
**Zoo branch:** `audit-truth-layer-20260531-commit` (commit `ca218ceb9`)
**Files cited by Zoo:**
- `alpha_engine/score_booster.py` (PROPOSED edit to `_calibrate_confidence`)
- `audit_dashboard/data/research/ml_calibration_audit.json` (DELIVERED)
- `updates/2026-05-31-ml-confidence-calibration-fix.md` (DELIVERED)

---

## Finding 0 — Code edit NOT actually committed

`git diff main..audit-truth-layer-20260531-commit -- alpha_engine/score_booster.py` returns EMPTY.

Zoo's commit ca218ceb9 ("fix: Calibrate confidence for inverted WR bands") changed reports + the audit JSON + the updates page, but did **not** modify `alpha_engine/score_booster.py`. The current `_calibrate_confidence()` (main HEAD) still has the pre-existing thresholds (CRYPTO `>0.85: -12`, FOREX `>=0.85: -10`, COMMODITY `>=0.85: -8`).

**Implication:** approving Zoo "as-is" approves an empty production change. Operator must understand the new thresholds described in the updates doc are aspirational, not in code.

---

## Finding 1 — Sample-size table (Zoo's source: `closed_picks.json`, 437 records)

| Class | Band | n | wins | WR% | Wilson 95% LB |
|---|---|---|---|---|---|
| FOREX | 0.55-0.60 | 11 | 2 | 18.2 | 3.2% |
| FOREX | 0.60-0.65 | 14 | 5 | 35.7 | 16.3% |
| FOREX | **0.65-0.70 (sweet spot)** | **7** | 4 | 57.1 | 25.0% |
| FOREX | 0.70-0.75 | 9 | 3 | 33.3 | 12.1% |
| FOREX | 0.75-0.80 | 48 | 5 | 10.4 | 4.5% |
| FOREX | 0.80-0.85 | 1 | 1 | 100 | n/a |
| FOREX | 0.95-1.00 | 4 | 2 | 50 | n/a |
| COMMODITY | 0.60-0.65 | 11 | 0 | 0 | 0 |
| COMMODITY | 0.65-0.70 | 23 | 0 | 0 | 0 |
| COMMODITY | **0.70-0.75** | **9** | 2 | 22.2 | 6.3% |
| COMMODITY | 0.75-0.80 | 24 | 2 | 8.3 | 2.3% |
| COMMODITY | 0.80-0.85 | 1 | 1 | 100 | n/a |
| CRYPTO | 0.65-0.70 | 66 | 23 | 34.8 | 25.0% |
| CRYPTO | 0.70-0.75 | 31 | 12 | 38.7 | 23.7% |
| CRYPTO | 0.75-0.80 | 22 | 10 | 45.5 | 26.9% |
| CRYPTO | 0.80-0.85 | 13 | 5 | 38.5 | 17.7% |
| CRYPTO | **0.95-1.00 (Zoo target)** | **7** | 0 | 0 | 0% (UB 35.4%) |

**Thin bands (n<20) that Zoo bases penalties on:** FOREX 0.65-0.70 (n=7), FOREX 0.70-0.75 (n=9), COMMODITY 0.70-0.75 (n=9), CRYPTO 0.95-1.00 (n=7). **4 critical bands.** All have Wilson 95% LB that overlaps neutral.

---

## Finding 2 — Cross-check vs PR #227 (MERGED 2026-05-31T21:14Z)

PR #227 verdict: **REJECT** `CONFIDENCE_INVERT_CRYPTO=1` (global invert), **propose** localized 0.8-bucket dampener (scale effective-confidence by ~0.5 when 0.75 ≤ conf < 0.85 in CRYPTO).

Zoo's CRYPTO change: `conf > 0.90: -18`.

**Conflict?** NO direct conflict — Zoo targets 0.90+, PR #227 targets 0.75-0.85. They are stackable. But: PR #227's underlying data (live `trading_picks` CRYPTO) shows 0.8=22% WR, 0.9=37.5%, 1.0=52.1% — NON-monotonic. Zoo's CRYPTO 0.95-1.00 = 0% WR comes from `closed_picks.json` (n=7) — a much smaller, possibly stale cohort. Live 30d (this verdict) shows CRYPTO conf=1.0 n=20 WR=0% — **agrees with Zoo direction**, but PR #227's broader cohort showed 1.0=52% — meaning the conf=1.0 band flipped recently or the two datasets cover different windows.

---

## Finding 3 — Live 30d trading_picks cross-check (this reviewer, queried verbatim)

```
commodity 0.6 n=8  WR=12.5
commodity 0.7 n=50 WR=2.0   ← strong inversion confirmed
commodity 0.8 n=34 WR=0.0   ← strong inversion confirmed
crypto    0.5 n=120 WR=40.0
crypto    0.6 n=458 WR=44.8
crypto    0.7 n=405 WR=30.9
crypto    0.8 n=89  WR=23.6
crypto    0.9 n=9   WR=22.2
crypto    1.0 n=20  WR=0.0   ← confirms Zoo conf>0.90 penalty
forex     0.6 n=6   WR=0.0
forex     0.7 n=13  WR=7.7
forex     0.8 n=22  WR=9.1
forex     0.9 n=5   WR=0.0
```

**Live 30d data AGREES with Zoo's direction** on all three classes — high-conf is toxic. But sample sizes per band are different than Zoo's audit (live 30d CRYPTO is much larger n; FOREX live 30d has no n≥48 cohort in 0.75-0.80 like Zoo's). **The live cohort actually supports STRONGER conclusions for CRYPTO and COMMODITY than Zoo proposed**, and equal strength for FOREX.

---

## Finding 4 — Memory reconciliation

Memory `project-confidence-trust-edges-2026-05-31.md` says CRYPTO has "localized 0.8-bucket dip not inversion" and "FOREX flat". This reviewer's live data shows:
- CRYPTO: NOT flat — monotonic decline 0.6→1.0 (44.8% → 0%). Memory was based on PR #227's cohort which still showed conf=1.0 recovering to 52%. **The newer 30d window shifted.**
- FOREX: NOT flat in 30d — clear 0% WR at conf=0.9 (n=5, thin) and 7-9% at 0.7-0.8.

Memory note should be UPDATED post-verdict.

---

## Finding 5 — Direction-of-change vs existing code

| Class | Existing penalty (main HEAD) | Zoo's proposed penalty (per docs) | Delta |
|---|---|---|---|
| CRYPTO conf>0.85 | -12 | -12 (unchanged) | 0 |
| CRYPTO conf>0.90 | (none) | **-18** | NEW |
| FOREX conf>=0.85 | -10 | **-20** | -10 (2x harder) |
| FOREX conf>=0.80 | (none) | **-15** | NEW |
| FOREX conf>=0.75 | 0 | **-8** | NEW |
| FOREX conf>=0.70 | +3 | **-3** | flips sign |
| FOREX conf>=0.65 | +3 | (still +5 sweet) | small |
| COMMODITY conf>=0.85 | -8 | **-15** | -7 (~2x) |
| COMMODITY conf>=0.80 | (none) | **-10** | NEW |

FOREX 0.65-0.70 sweet-spot reward is built on n=7. Flipping `0.70-0.75` from +3 to -3 is a 6-point swing based on n=9. **Magnitudes are too aggressive for the sample size.**

---

## RED-TEAM VERDICT: **APPROVE_WITH_DAMPING**

- **Direction is correct** for all three classes — confirmed by independent live 30d query.
- **No conflict with PR #227** — Zoo targets different bands.
- **But:** 4 critical bands have n<20 and drive the largest magnitudes (-20, -15, -18). Wilson lower bounds overlap neutral. Production score swing of 6-15 points should not be based on n=7 cohort.
- **And:** Zoo's commit did NOT actually edit score_booster.py. Operator should not approve as "shipped"; this is a design proposal at best.

### Recommended operator action

1. Acknowledge Zoo's audit JSON and updates doc — **approve the diagnostic**.
2. **Reject the magnitudes**, request Zoo (or follow-up PR) to:
   - Use half-strength penalties (-10 instead of -20, -8 instead of -15, -10 instead of -18) on bands with n<20.
   - Keep full-strength penalties on bands with n≥20 (FOREX 0.75-0.80 n=48, COMMODITY 0.75-0.80 n=24 borderline OK).
   - Reuse live `trading_picks` 30d window (this reviewer's query) instead of `closed_picks.json` as the calibration cohort — it's 5-10x larger per band.
3. Require the actual code edit be committed and PR'd against `alpha_engine/score_booster.py` — current Zoo branch does not contain it.
4. Coordinate with PR #227 dampener follow-up so both edits ship in one calibration release.

---

## Return string

`RT_ZOO_CALIB:approve=with_damping:thin_samples=4:pr227_conflict=False:live_data_agrees=True`
