# CRYPTO + EQUITY Priority Shadow-Pilots — 2026-05-31

**Agent:** peer_claude (Opus 4.7)
**Source synthesis:** `reports/peer_claude-WINNERS_PER_CLASS_SYNTHESIS_2026-05-31.md` (PR #304, merged 2026-05-31T21:58:15Z)
**Source deep-dive:** `reports/peer_claude-deep-dive-WINNER-CRYPTO_2026-05-31.md`, `reports/peer_claude-deep-dive-WINNER-EQUITY_2026-05-31.md`
**Status:** PROMISING-NOT-WINNER. **No real-money sizing.** Paper-only shadow track.

## Headline

The 7-class winner hunt closed **0/7 strict winners** under the pre-registered admissibility gate (n>=100, Wilson-LB>0.50, PF-lo>1.2, Sharpe-lo>0.5, Bonferroni-p<0.01). But two candidates produced **point-estimates close enough to the threshold** that the question "is this signal real with more data?" is empirically open rather than refuted:

| Class | Strategy (family) | WR | PF | n | Wilson 95% LB |
|---|---|---:|---:|---:|---:|
| CRYPTO | `volatility_breakout` (keltner / ATR / compression / expansion bucket) | 0.612 | 1.47 | 85 | **0.5057** |
| EQUITY | `stocks_rsi2_pullback` | 0.590 | 1.20 | 39 | **0.4344** |

## Strategy + filter reproduction

### CRYPTO — `volatility_breakout` family

**SQL filter** (from `peer_claude-deep-dive-WINNER-CRYPTO_2026-05-31.md`):

```sql
SELECT pick_id, signal_ts, strategy, symbol, side, pnl_pct, closed_at
FROM ejaguiar1_stocks.trading_picks
WHERE category IN ('crypto','memecoin')
  AND closed_at >= NOW() - INTERVAL 90 DAY
  AND closed_at IS NOT NULL
  AND pnl_pct IS NOT NULL
  AND (
       strategy LIKE '%volatility%' OR
       strategy LIKE '%atr%'        OR
       strategy LIKE '%keltner%'    OR
       strategy LIKE '%compression%' OR
       strategy LIKE '%expansion%'
  );
-- expected: n=85, wins=52, WR=0.612, PF=1.47
```

**Caveat (per deep-dive root cause #1):** the LIKE bucket includes a small number of high-magnitude wins (avg pnl +5.08% with std 40.8) — without intrabar OHLC replay we cannot confirm the actual `ATR > 1.5x baseline` trigger is what generated those wins (could be label artefact / outlier). This is the single biggest reason **not** to size up.

### EQUITY — `stocks_rsi2_pullback`

**SQL filter:**

```sql
SELECT pick_id, signal_ts, strategy, symbol, side, pnl_pct, closed_at
FROM ejaguiar1_stocks.trading_picks
WHERE category IN ('equity','stocks','stock')
  AND closed_at >= NOW() - INTERVAL 90 DAY
  AND closed_at IS NOT NULL
  AND pnl_pct IS NOT NULL
  AND strategy = 'stocks_rsi2_pullback';
-- expected: n=39, WR=0.590, PF=1.20
```

**Caveat (per synthesis):** 4/5 EQUITY academic edges (magic_formula, piotroski, momentum_12_1, low_vol) are never wired into production. `stocks_rsi2_pullback` is the *only* live academic-family emitter in EQUITY — its 39 closed picks are also the entire academic-family sample for the class.

## Statistical Confidence Intervals

### Wilson 95% lower bound (one-sided, z=1.96 two-sided form)

```
LB = ((p + z²/(2n)) - z*sqrt((p(1-p) + z²/(4n))/n)) / (1 + z²/n)
```

| Class | p̂ | n | Wilson 95% LB | Interpretation |
|---|---:|---:|---:|---|
| CRYPTO | 0.612 | 85 | **0.5057** | Barely clears 0.50 — "genuinely suggestive" but fragile. Adding/removing 1-2 wins flips it. |
| EQUITY | 0.590 | 39 | **0.4344** | Below 0.50 — **still consistent with random noise**. Point estimate looks good, CI says wait. |

### PF bootstrap 95% CI (B=500 resamples, from deep-dives)

- CRYPTO volatility_breakout: PF CI95 = **(0.77, 3.30)** — straddles break-even (1.0).
- EQUITY stocks_rsi2_pullback: PF CI95 = **(0.526, ~2.5)** — straddles break-even, with lower end deep in losing territory.

### Sharpe bootstrap 95% CI

- CRYPTO: Sharpe CI = (-1.26, 5.80) — straddles 0.
- EQUITY: Sharpe CI similarly straddles 0 (n=39 makes Sharpe CIs especially wide).

## Honest read

**Neither candidate clears the institutional admissibility gate.** What we can say:

- CRYPTO **volatility_breakout** is the ONLY candidate across all 35 tested where the Wilson WR LB clears 0.50. That makes it the single most-promising data point in the entire 7-class hunt. But the PF CI lower bound (0.77) still allows for a losing-strategy interpretation.
- EQUITY **stocks_rsi2_pullback** is point-estimate-promising but the Wilson LB (0.434) is still below the gate. With n=39, the data is genuinely inconclusive — could be a real ~59% WR strategy, could be a 45% WR strategy on a lucky streak.

These are **not edges**. They are **leads worth tracking** under a paper-only protocol.

## Recommended 30-Day Shadow-Pilot Protocol

**Mode:** PAPER-ONLY. Zero real-money allocation. Tracked as `SHADOW_PILOT_30d` in `pf_registry.json` per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`.

**Target sample by 2026-07-01:** n >= 100 per class (need +15 CRYPTO, +61 EQUITY).

### Per-class pilot setup

| Class | Strategy | Filter scope | Pick capture | Size | Expected n delta in 30d |
|---|---|---|---|---:|---:|
| CRYPTO | `volatility_breakout` family | keltner/ATR/compression/expansion strategies | All emissions captured to `trading_picks.shadow_track='volatility_breakout_pilot_30d'` | paper $1k notional | ~30 (current 90d run-rate 85 → ~28/30d) |
| EQUITY | `stocks_rsi2_pullback` | exact strategy match | All emissions captured to `trading_picks.shadow_track='rsi2_pullback_pilot_30d'` | paper $1k notional | ~13 (current 90d run-rate 39 → ~13/30d) |

**Caveat for EQUITY:** even running the full 30 days, expected n is only ~52. To reach n>=100 we likely need **either** (a) extend pre-90d backtest history via `bt_backtest_trades` ingest, **or** (b) extend pilot to 60-90 days.

### Daily / weekly checkpoints

- **Daily:** log every emission with full feature snapshot (ATR-at-entry, RSI2-at-entry, symbol, side, signal_ts).
- **Weekly:** recompute Wilson LB + PF CI on running cumulative sample; flag if WR collapses or PF crosses below 0.8 — early-stop trigger.
- **Day 14:** intrabar OHLC replay on captured picks (per `reference-sl-optimization-needs-pricepath`) to confirm the strategy gate is actually what's firing. This is the single most important check; if the replay reveals the wins are coming from a different mechanism than the strategy claims, abort.
- **Day 30:** full re-statistics with proper cohort.

## Post-pilot Gates Before Any Real-Money Consideration

ALL of the following must clear before *any* real-money sizing is considered. Failing one = NO_GO.

1. **Sample:** combined (current + pilot) n >= 100 per class.
2. **WR Wilson 95% LB > 0.50** with the larger sample.
3. **PF bootstrap 95% lower bound > 1.2** (B=1000 resamples, seed-stable across 3 seeds).
4. **Sharpe bootstrap 95% lower bound > 0.5** (annualized assuming ~252 trade-days).
5. **Bonferroni-corrected p-value < 0.01** (we tested 5 candidates per class → alpha = 0.05/5 = 0.01).
6. **Concentration HHI < 0.30** at the strategy level (per `feedback-concentration-strategy-not-engine`) — no single symbol/sub-source dominates the win count.
7. **Intrabar replay confirms strategy gate matches actual fills** — no label noise, no resolver mislabels (per `reference-sl-optimization-needs-pricepath` and the M-067 policy-clean cohort gate).
8. **Out-of-sample walk-forward 5/5 positive** on the 30-day pilot window split.
9. **Operator personal approval** per `CLAUDE.md` MAJOR GOAL #1 + real-money state machine (BLOCKED → REHAB → OOS_READY → SHADOW → LIVE_ELIGIBLE).
10. **30-day clean truth-layer** (zero new resolver mislabels, zero duplicate signal-ts groups, zero EXPIRED→WON inversions) on the pilot cohort window.

**Even if all 10 clear**, initial sizing cap is **0.25x baseline** under SHADOW_PROBATION for another 30 days before moving toward standard sizing.

## What this report is NOT

- NOT a buy signal.
- NOT a recommendation to size up either strategy today.
- NOT a contradiction of the 0/7 winner-hunt finding — the winner hunt remains correct that no candidate clears the institutional gate **today** on **today's data**.

What it IS: a documented decision to **track these two specifically** for 30 days, with quantified gates, instead of letting promising-but-inconclusive leads disappear into the broader NO_EDGE narrative.

## Cross-references

- `reports/peer_claude-WINNERS_PER_CLASS_SYNTHESIS_2026-05-31.md` (PR #304, merged)
- `reports/peer_claude-deep-dive-WINNER-CRYPTO_2026-05-31.md`
- `reports/peer_claude-deep-dive-WINNER-EQUITY_2026-05-31.md`
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md`
- `reference-sl-optimization-needs-pricepath` (intrabar replay non-negotiable)
- `feedback-concentration-strategy-not-engine` (HHI<0.30 strategy-level)
- `project-money-ready-2026-05-31` (plumbing-not-strategy bottleneck)
- `CLAUDE.md` MAJOR GOAL #1 + real-money state machine

---

**Return string:** `PRIORITY_SHADOWS:crypto=volatility_breakout:equity=stocks_rsi2_pullback:crypto_wilson_lb=0.5057:equity_wilson_lb=0.4344:status=PAPER_ONLY_30D`
