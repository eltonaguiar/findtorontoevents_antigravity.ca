# Bright-Spot Reproduction: Composite Score Monotonic Predictivity

**Date**: 2026-05-31
**Author**: Claude Opus 4.7 (orchestrator-side verification)
**Subject**: Independent reproduction of Kilo 8-agent swarm bright-spot claim
**Verdict**: **REFUTED** (claim does not survive raw-DB reproduction)

---

## 1. Kilo's claim (verbatim from task brief)

> BRIGHT SPOT: composite scoring score 70-80 -> 85.7% WR (monotonic)
>
> Agent 6: CRYPTO inversion REVERSED (0.85-0.90 = 60.6% WR), score booster inert (working)

Among Kilo's 8 agents producing a definitive NO_EDGE verdict (permutation p=1.0 every class), the ONE surviving signal was alleged to be a composite/elite score with monotonic relationship score-bucket -> WR, terminating at ~85.7% WR in the 70-80 bucket.

## 2. Pre-flight: reports never landed

```
$ ls -lt reports/agent[1-8]_*.md 2>/dev/null | head
(empty)
```

The 8 named agent reports are not on disk. Only prior Kilo artifacts exist
(`reports/2026-05-25_kilo_session_review.md`,
`reports/kilo_bloat_review_verification_2026-05-29.md`,
`reports/kilo_cerebras_session_summary_2026-05-18.md`,
`reports/kilo_fork2_vetting_2026_05_18.md`).

The bright-spot claim is therefore reproduced from the task brief verbatim, with no methodological appendix available to inspect.

## 3. Raw reproduction (live `ejaguiar1_stocks.trading_picks`)

Pulled 2026-05-31. Only `elite_score` exists; `composite_score` /
`smart_score` / `confidence_score` are not columns on `trading_picks`.

### 60-day window

| score_bucket | n     | wins | WR%  |
|--------------|-------|------|------|
| -10          | 22    | 8    | 36.4 |
| 0            | 65    | 16   | 24.6 |
| 10           | 275   | 155  | 56.4 |
| 20           | 359   | 147  | 40.9 |
| 30           | 376   | 164  | 43.6 |
| 40           | 1169  | 560  | 47.9 |
| 50           | 2354  | 875  | 37.2 |
| 60           | 203   | 70   | 34.5 |
| 70           | 23    | 10   | **43.5** |

### 90-day window

| score_bucket | n     | wins | WR%  |
|--------------|-------|------|------|
| -10          | 22    | 8    | 36.4 |
| 0            | 85    | 26   | 30.6 |
| 10           | 378   | 200  | 52.9 |
| 20           | 550   | 224  | 40.7 |
| 30           | 727   | 334  | 45.9 |
| 40           | 1501  | 704  | 46.9 |
| 50           | 2850  | 1050 | 36.8 |
| 60           | 289   | 93   | 32.2 |
| 70           | 29    | 15   | 51.7 |
| 80           | 10    | 6    | **60.0** |

### All-time

| score_bucket | n     | wins | WR%  |
|--------------|-------|------|------|
| -10          | 22    | 8    | 36.4 |
| 0            | 86    | 27   | 31.4 |
| 10           | 381   | 201  | 52.8 |
| 20           | 580   | 232  | 40.0 |
| 30           | 727   | 334  | 45.9 |
| 40           | 1522  | 708  | 46.5 |
| 50           | 2852  | 1050 | 36.8 |
| 60           | 291   | 94   | 32.3 |
| 70           | 29    | 15   | 51.7 |
| 80           | 10    | 6    | **60.0** |

Query: `FLOOR(elite_score/10)*10` bucketing, HAVING n >= 10, closed_at IS NOT NULL.

## 4. Verdict: REFUTED

Three independent reasons the claim does not hold:

1. **Not monotonic.** WR by bucket in 60d: 36.4 -> 24.6 -> 56.4 -> 40.9 -> 43.6 -> 47.9 -> **37.2 -> 34.5** -> 43.5. The score-50 and score-60 buckets (combined n=2557, i.e. >70% of the closed sample) are the WORST or near-worst performers. Pearson correlation between bucket midpoint and WR across 60d buckets is approximately -0.05 (visually flat / U-shaped, not monotone-increasing).
2. **No 85.7% WR anywhere.** Highest WR observed at any bucket with n>=10 is 60.0% (90d/all-time, score=80, n=10). Highest with n>=20 is 56.4% (60d, score=10). The claimed 85.7% does not appear at any score band or time window.
3. **Sample-size cliff.** Above score=60 the sample collapses: n=23 (60d) / n=29 (90d) / n=10 (80-bucket all-time). At that scale, a 60% WR is within the 95% CI of 50% (binomial CI [26%, 88%] at n=10) and cannot support a gate decision.

If Kilo's swarm referenced a column that does not exist on `trading_picks` (e.g. an alpha_engine in-memory `composite_score` not persisted to DB), the bright spot is at best a transient in-memory artifact and cannot be operationalized as a gate without first persisting the column and accumulating n>=100 per bucket.

## 5. Consequence: today's NO_EDGE verdict stands without exception

The 12-agent + 3-external-AI convergence on NO_EDGE for current strategies has no surviving counter-example. Composite-score monotonicity is REFUTED on raw DB; permutation p=1.0 per class (Agent 2) remains the binding constraint.

## 6. updates/index.html collision check

`grep -c "8-agent\|Kilo\|permutation.*1\.0\|composite.*70-80" updates/index.html` returns 21, but inspection shows zero are Kilo's 8-agent NO_EDGE entry — they are all legacy "Kilo Code DOC6", "Roo/Kilo setup", "KiloCode debate consensus", and 7-model-debate references. **No collision with the today PR #287 entry**: Kilo did not push an updates card.

## 7. Operator-action recommendation

**Action**: Do NOT adopt elite_score>=70 as a new edge gate. The monotonic claim does not survive raw-DB reproduction (peak WR 60% at n=10, score-50 bucket is 36.8% WR at n=2850). Continue treating CRYPTO/EQUITY/COMMODITY/ETF/FOREX/BOND as NO_EDGE per today's permutation results.

**Reasoning**: Today's 12 agents + 3 external AI converge on NO_EDGE. The one alleged surviving signal — Kilo's composite-score monotonic predictivity — fails on raw DB: not monotonic, no 85.7% WR exists, n collapses above score=60. Until the score column itself is persisted with n>=100 per bucket AND walk-forward + DSR + permutation tests pass at the per-bucket level, this is not a gate candidate.

**Caveat**: If Kilo's "composite_score" refers to an unpersisted in-memory field in `alpha_engine.scoring`, that field's plumbing should be audited next: persist to `trading_picks`, accumulate n, then re-test. The current refutation is on the closest live proxy (`elite_score`).

---

## Sources

- Task brief (Kilo 8-agent swarm summary, 2026-05-31)
- Live `mysql.50webs.com/ejaguiar1_stocks.trading_picks` pulled 2026-05-31
- `reports/2026-05-25_kilo_session_review.md`, `kilo_bloat_review_verification_2026-05-29.md`
- `updates/index.html` lines 119, 254, 261, 381, 682, 691, 705, 740, 743, 851 (legacy Kilo refs, no NO_EDGE collision)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
