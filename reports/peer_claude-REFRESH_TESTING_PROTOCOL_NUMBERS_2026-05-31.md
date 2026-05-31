# TESTING_PROTOCOL.MD §2.5 — Live Refresh of 2026-04-04 Empirical Claims

**Date:** 2026-05-31
**Source:** live `ejaguiar1_stocks.trading_picks` (closed_at NOT NULL AND pnl_pct NOT NULL)
**Total closed sample:** n=6,619 (vs ~April baseline implied n≈few hundred to low thousands)
**Baseline ALL-closed WR (today):** 46.9%

## Side-by-Side Drift Table

| # | 2026-04-04 Claim | 2026-05-31 Verify | Drift (pp) | Verdict |
|---|---|---|---|---|
| 1 | winner_pattern_precursor LONG = 0% WR → inverse (SHORT) = 81.2% WR, PF 2.35 | strategy name returns **0 rows** today (renamed/removed); no `%winner%` or `%precursor%` strategies in DB | n/a | **DEAD** — strategy no longer exists in trading_picks |
| 2 | elite_score < 40 = 33.9% WR (toxic) | WR=45.1%, n=1,777 | **+11.2** | **DRIFTED** — toxicity gone; score<40 now near baseline (46.9%). Filter no longer separating signal |
| 3 | LONG + Trust<4 = 36.2% WR | WR=47.6%, n=2,105 | **+11.4** | **DRIFTED** — LONG/Trust<4 now performs at baseline; filter dead |
| 4 | LONG + Conf≥0.90 = 19.5% WR (toxic) | WR=42.6%, n=54 | **+23.1** | **DRIFTED MAJOR** — toxicity gone (still slightly sub-baseline but only n=54). The actual toxic cell appears to be **conf 0.70–0.75 = 39.4% WR n=436** today |
| 5 | Conf 0.75–0.79 = 86.5% WR (sweet spot) | WR=43.4%, n=1,059 | **−43.1** | **DEAD** — sweet spot evaporated; bucket now performs WORSE than baseline. New sweet spot is **conf ≥0.90 = 62.3% n=231** |
| 6 | Trust 6–7 = 77% WR (strongest single predictor) | WR=85.9%, n=99 (all are trust=7; no trust=6 rows exist) | **+8.9** | **HOLDS** (stronger than claimed). Still the strongest single predictor at n=99 |
| 7 | 62% of live picks have score 0/missing | **41.4%** of ACTIVE picks (n_active=3,600) have score 0/NULL | **−20.6** | **DRIFTED** — improved; still substantial but no longer majority |
| 8 | SHORT base 56.7% vs LONG 48.7% (SHORT edge) | SHORT 44.6% n=1,753 vs LONG 48.0% n=2,304 | SHORT **−12.1**, LONG **−0.7** | **REVERSED** — LONG now slightly beats SHORT. SHORT edge is dead. **30d recency:** SHORT 20.7% n=111 vs LONG 37.6% n=226 — SHORT actively bleeding |
| 9 | EXPIRED exits = 94.9% WR | WR=52.8%, n=231 | **−42.1** | **DEAD** — EXPIRED no longer carries the edge; barely above baseline |

## Top 3 Most-Significantly Drifted Claims (Operator Action)

### #1 — Conf 0.75–0.79 sweet spot is DEAD (−43.1 pp)
- April: 86.5% WR (sweet spot)
- Today: 43.4% WR, n=1,059 (sub-baseline)
- **New sweet spot:** confidence ≥0.90 → 62.3% WR n=231 (BUY direction inside this bucket: 72.1% n=147)
- **Action:** any code/gate citing "conf 0.75–0.79 cluster" is mis-tuned. Remove or invert. Re-tune to ≥0.90 (+BUY).

### #2 — EXPIRED exits no longer carry edge (−42.1 pp)
- April: 94.9% WR — used as a "patience pays" indicator
- Today: 52.8% WR n=231 (barely above baseline)
- **Action:** any strategy that relies on letting trades EXPIRE to lock in wins (vs hitting TP) is no longer profitable. Re-examine the TP/SL geometry — likely the resolver fix (M-067/v2.1) changed which trades count as EXPIRED.

### #3 — SHORT edge REVERSED (−12.1 pp on all-time, −22 pp on 30d)
- April: SHORT 56.7% vs LONG 48.7% (SHORT advantaged)
- Today all-time: SHORT 44.6% n=1,753 vs LONG 48.0% n=2,304
- **30d recency:** SHORT 20.7% n=111 vs LONG 37.6% n=226 — SHORT actively bleeding badly post-PR #277 EQUITY un-kill
- **Action:** any SHORT-biased gate (especially recently-tuned ones) should be reviewed. The EQUITY un-kill (#277) appears to have admitted a class of trades where the SHORT side is structurally losing.

## Holdouts / Things to Preserve

- **Trust=7 (the only existing high-trust value): 85.9% WR n=99.** Still the strongest single predictor — actually STRONGER than the April claim of 77%. Do not change the trust gate.
- **BUY (case-mess of `direction`):** BUY/SELL labels (1,164/1,115 closed) outperform LONG/SHORT (probably equity-pipeline). BUY = 45.8% WR (533/1164), SELL = 44.5%. Recency-30d: BUY 43.1% n=357, SELL 42.6% n=394 — flat. The `(direction = '')` 185-row bucket with 63.2% WR 30d is worth a separate audit (likely sports/unlabeled).

## Cross-References

- M-067 cap (251→43 picks): same root cause as the score-0/missing problem (#7). The 41.4% NULL elite_score in ACTIVE picks suggests the scorer isn't running for ~40% of inbound picks — that drove the cap path.
- PR #277 EQUITY un-kill: lines up with the SHORT collapse on 30d window (#8). Recommend per-source attribution of the 30d SHORT n=111 to confirm.
- All April claims about per-strategy WR for `winner_pattern_precursor` (#1) are unverifiable — strategy was renamed or culled; no records in `trading_picks` today.

## Recommended TESTING_PROTOCOL.MD §2.5 patches

1. **Delete** all 9 numbered claims as written (5 DEAD/DRIFTED-MAJOR, 3 DRIFTED, 1 HOLDS-STRONGER).
2. **Replace** with a "live-numbers as of 2026-05-31" block:
   - Trust=7 = 85.9% WR n=99 (strongest single predictor — preserved)
   - Conf ≥0.90 = 62.3% WR n=231 (new sweet spot; BUY-side 72.1% n=147)
   - Conf 0.70–0.75 = 39.4% WR n=436 (NEW toxic cell)
   - SHORT 30d = 20.7% WR n=111 (active bleeding post-#277 EQUITY un-kill)
   - 41.4% of ACTIVE picks still missing elite_score (scorer not firing on ~40% of inbound)
3. **Add a refresh cadence rule:** any §2.5 empirical claim must carry a `verified_at` date and the SQL filter that produced it. Auto-refresh weekly via a CI job.

## Methodology

All queries used:
```sql
SELECT ROUND(SUM(CASE WHEN pnl_pct>0 THEN 1 ELSE 0 END)*100.0/COUNT(*),1) wr, COUNT(*) n
FROM trading_picks
WHERE closed_at IS NOT NULL AND pnl_pct IS NOT NULL AND <filter>;
```
- ALL closed n=6,619 baseline 46.9% WR.
- No noise filter applied (raw `pnl_pct>0` decides win; matches the April methodology per TESTING_PROTOCOL §2.5 wording).
- Active-pick stat (#7) uses `status='ACTIVE'` instead of closed filter.

**Summary counts:** claims_checked=9, held=1, drifted=5, dead=3, max_drift_pp=43.1
