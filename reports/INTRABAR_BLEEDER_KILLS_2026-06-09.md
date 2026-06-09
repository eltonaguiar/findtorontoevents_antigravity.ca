# Intrabar-Truth Bleeder Kills + Honest Pro-Pick Board — 2026-06-09

**Author:** Claude (Fable 5), session: sub-coin-flip asset-class fix
**Protocol:** docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md + docs/MUTATION_THREE_AXIS_PROTOCOL.md
**Ground truth:** `at_signal_outcomes.intrabar_*` (first-touch, SL-wins-ties, geometry-guarded,
`intrabar_ambiguous=0` only) cross-checked against the `trading_picks` resolved cohort.
All numbers below are live DB queries run this session — no subagent/pf_registry stats.

## 1. KILLS added to BLOCKED_STRATEGIES (cross-ledger verified, three-axis checked)

| Strategy | Class | intrabar n / WR / PF | trading_picks corroboration | axes |
|---|---|---|---|---|
| `commodity_momentum` | COMMODITY | 18 / 0% / 0.00 | (absent) | LONG 0/14, SHORT 0/4; NG=F 0/14, CL=F 0/4 |
| `beta_adjusted_residual_momentum` | CRYPTO | 20 / 10% / 0.08 | n=23 / 34.8% / 0.63 | all LONG; BNB 1/6, FIL 0/5, SUI 0/5 |
| `regime_mild_bull` | (all) | 43 / 20.9% / 0.17 | n=49 / 40.8% / 0.30 | all LONG; AMD 0/17, OPEN 2/11 |
| `regime_accumulation` | (all) | 29 / 20.7% / 0.50 | n=72 / 33.3% / 0.20 | LONG only; AMD 0/7, LCID 0/7; SOFI 4/4 < n=10 floor |
| `stochrsi_macd_combo` | CRYPTO | 23 / 26.1% / 0.50 | (absent) | all LONG; TAO 1/5, NOM 1/3, U 1/3 |

No axis on any of the five shows WR≥50 or PF>1.2 with n≥10 → no mutation rescue; kill is correct.

**MUTATE, not kill:** `bollinger_squeeze` CRYPTO — n=51, **WR 52.9% but PF 0.10**. The signal
direction works; the TP/SL geometry destroys it (tiny wins, huge losses). Needs R:R repair
(price-path replay per `reference-sl-optimization-needs-pricepath`), not a block.

**Inversion screen result:** the only WR≪50/PF≪1 candidate (`regime_mild_bull`, would-be ~80% WR
inverse) FAILS diversification — AMD 0/17 in a single ~1-week window (2026-05-28..06-06,
SL_HIT 27/36). One symbol, one window ≠ durable anti-edge. No inversion pick survives.

## 2. Wrong-kill contradictions (blocked winners — flagged, NOT unilaterally unblocked)

| Strategy | Block basis (old resolver) | intrabar truth (deduped per symbol-day) |
|---|---|---|
| `forex_rsi2_mean_reversion` FOREX | 2026-05-13: "WR 7.1% / PF 0.09 n=84" | **n=20, WR 70%, PF 2.44** (last-14d n=25, 68%/2.63) |
| `volume_spike_breakout` (global) | 2026-04-17: "WR 10.8% / PF 0.136 n=37" | n=97, 49.5%/1.29 (last-14d 52%/1.80) — marginal, not T2 |

Caveat: the same strategy NAME runs at very different volumes in `trading_picks` (forex_rsi2:
2,686 hourly rows, 30d PF 0.41 — wins tiny/losses huge = geometry problem) vs the daily
`at_signal_outcomes` variant (the 70%/2.44 above). Unblocking the FOREX-wide entry would re-open
the bleeding hourly variant too. **Correct path = shadow-track the daily variant only** (matches
the WS-G swarm decision + guardrails in `reports/wsg_shadow_track_decision_2026-06-09.md`).

## 3. futures_momentum — independent corroboration of the guardrail-#5 amendment

Two independent methods refute it as an edge:
- **Dedup (this session):** intrabar PF 2.59 (n=57) collapses to **PF 1.03 / WR 37.5% (n=16)**
  when deduped per (symbol, direction, day) — the hourly emitter re-emits the same SI=F/PL=F
  SHORT 5-15× per day, multiplying its winning days (06-04/06-05). Recent days are all losers.
- **Full-cohort (peer guardrail #5):** trading_picks COMMODITY n=2,029 → WR 42%.

Verdict: **NOT a shadow-track candidate.** The "n57 63%/PF2.59" was duplicate-emission-inflated.

## 4. Honest pro-pick board per asset class (intrabar-true, deduped per symbol-day)

| Class | Best honest signal | Deduped n / WR / PF | Verdict |
|---|---|---|---|
| CRYPTO | `luxalgo_confluence` | 78 / 56.4% / 1.56 | best-in-system; T2-shaped, needs n≥100 — watch |
| FOREX | `forex_rsi2_mean_reversion` (daily variant) | 20 / 70% / 2.44 | blocked; shadow-track per WS-G with guardrails |
| EQUITY | `vt_equity_two_day_rsi_reversal` | 13 / 100% / — | **AAPL-only** (HHI=1.0) — single-ticker hypothesis, not a class edge |
| COMMODITY | `futures_momentum` | 16 / 37.5% / 1.03 | REFUTED after dedup (see §3) |
| MEMECOIN | — (mercury2 ensemble 28%/0.73) | — | net loser; mercury2 dormant since 05-17 |
| ETF / BOND / FUTURES | — | n<20 | insufficient data |

**Net: 0 classes money-ready (consistent with 0/6 T2 everywhere).** The only signals worth
forward n are `luxalgo_confluence` (already emitting) and the daily `forex_rsi2` shadow-track.
Do not size anything on this table.

## 5. Data fixes this session
- **Blank asset_class backfill:** 82 `at_signal_outcomes` rows (78 EQUITY, 2 FOREX, 1 ETF,
  1 COMMODITY — the regime_* strategies were emitting unclassified). Reversal manifest:
  `reports/asset_class_backfill_manifest_2026-06-09.json`.
- `trading_picks.pnl_pct` is geometry/dup-poisoned at strategy level (WR 53.6% with PF 0.01;
  luxalgo PF 24-48 artifacts) — never block/promote on it without the intrabar cross-check.

## Reproducer
```sql
-- per class+strategy intrabar truth (deduped):
SELECT strategy, COUNT(*) n, SUM(p>0)/COUNT(*) wr,
       SUM(GREATEST(p,0))/ABS(SUM(LEAST(p,0))) pf
FROM (SELECT strategy, symbol, direction, DATE(opened_at) d, AVG(intrabar_pnl_pct) p
      FROM at_signal_outcomes
      WHERE intrabar_status IS NOT NULL AND intrabar_ambiguous=0
      GROUP BY 1,2,3,4) t GROUP BY 1;
```
