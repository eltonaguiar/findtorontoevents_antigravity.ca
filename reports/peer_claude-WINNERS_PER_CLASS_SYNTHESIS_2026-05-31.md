# Winners-Per-Class Deep-Dive Synthesis — 2026-05-31

**Agent:** peer_claude (Opus 4.7)
**Inputs:** 7 deep-dive reports `reports/peer_claude-deep-dive-WINNER-{CRYPTO,EQUITY,COMMODITY,ETF,FOREX,BOND,PENNY_IPO}_2026-05-31.md`
**Source data:** `ejaguiar1_stocks.trading_picks` + `ejaguiar1_backtests.bt_backtest_trades`, last 90d closed picks, policy-clean cohort
**Winner gate (all required):** n>=100 AND Wilson WR LB>0.50 AND PF bootstrap-lo>1.2 AND Sharpe bootstrap-lo>0.5 AND Bonferroni p<0.01

## Results Table

| Class | Candidates Tested | Best Candidate | n | WR | PF | Wilson-LB | PF-CI-lo | Verdict | Action |
|---|---:|---|---:|---:|---:|---:|---:|---|---|
| CRYPTO | 5 | volatility_breakout (keltner/ATR) | 85 | 0.612 | 1.47 | 0.505 | 0.77 | **NO_WINNER** | MORE_DATA_NEEDED |
| EQUITY | 5 | stocks_rsi2_pullback | 39 | 0.590 | 1.20 | 0.434 | 0.526 | **NO_WINNER** | MORE_DATA + PIPELINE_GAP (4/5 academic edges never wired) |
| COMMODITY | 5 | cta_golden_cross_200 (cluster inside momentum_12_1) | 26 | 0.923 | n/a | <0.50 | n/a | **NO_WINNER** (n<100 — investigate; momentum_12_1 n=697 PF 0.86 FAIL) | TRY_DIFFERENT_FAMILY + investigate cluster |
| ETF | 5 | (none — universe-wide n=20) | 20 | n/a | n/a | n/a | n/a | **NO_WINNER** | MORE_DATA_NEEDED (pipeline drought + 906k unresolved backtest rows) |
| FOREX | 5 | mean_reversion_bollinger | 670 | 0.414 | 0.42 | 0.414 | <1.0 | **NO_WINNER** (carry n=62 lottery; rsi2_MR n=664 net-losing) | RETIRE_CLASS from real-money + demote forex_rsi2_mean_reversion |
| BOND | 5 | (none — n=0 on all candidates) | 0 | n/a | n/a | n/a | n/a | **NO_WINNER** (uninstrumented; 243k rows OPEN, only signal_recorder zero-pnl closes) | MORE_DATA, then RETIRE_CLASS in 30d if no progress |
| PENNY_IPO | 5 | oversold_bounce_RSI2 | 15 | n/a | n/a | n/a | n/a | **NO_WINNER** (no instrumentation; universe undefined) | TRY_DIFFERENT_FAMILY + MORE_DATA (no instrumentation exists) |

## WINNERS overall

**Zero (0).** No class produced a candidate that simultaneously cleared the n>=100, Wilson-LB>0.50, PF-lo>1.2, Sharpe-lo>0.5, Bonferroni-p<0.01 gate.

Closest near-misses (do NOT size up — these are *not* winners, they are the least-disqualified candidates):
- **CRYPTO volatility_breakout** — Wilson LB barely clears 0.505 but PF-lo 0.77 and Sharpe-lo -1.26 fail; n=85<100.
- **EQUITY stocks_rsi2_pullback** — point estimates promising (WR 0.59 / PF 1.20) but every CI lower-bound straddles break-even; n=39<100.
- **COMMODITY cta_golden_cross_200** — 92.3% WR but n=26 only; suspected survivorship/label noise pending mutation analysis.

## NO_WINNER classes — Root Causes

| Class | Root Cause | Recommended Next Step |
|---|---|---|
| CRYPTO | Classical academic candidates don't separate winners from the losing universe distribution (universe PF 1.14); heavy-tailed pnl makes bootstrap CIs span break-even | Extend n via pre-90d backtest history; intrabar replay before any TP/SL re-tune; **do NOT live-size** |
| EQUITY | **Pipeline gap** — 4/5 academic edges (magic_formula, piotroski, momentum_12_1, low_vol) never wired into production. Only rsi2_pullback emits picks (n=39) | Implement + wire the 4 missing academic strategies per Wire-Up Rule; re-test in 30d |
| COMMODITY | **Strategy mono-culture** — 83% of closed trades are `futures_momentum` (bleeding at PF 0.79); seasonal/COT/mean-reversion families never emit picks | Build out missing CTA families; investigate cta_golden_cross_200 cluster; suspend futures_momentum size-up |
| ETF | **Pipeline drought** — only 20 closed-with-pnl rows in 90d; 906k backtest rows unresolved; no Faber/dual-momentum/risk-parity wired | Fix bt_backtest_trades ETF resolver; wire one academic ETF strategy (Faber 10mo MA is the simplest) |
| FOREX | **Dominant strategy broken** — forex_rsi2_mean_reversion (n=664, 40% of class flow) at PF 0.42 drags class verdict; carry/momentum cohorts too thin (lottery distributions) | **P0 demote forex_rsi2_mean_reversion** via mutation-before-kill; extend carry/momentum sleeves with 3yr history |
| BOND | **Class uninstrumented at resolver layer** — 243k bt rows OPEN with pnl_pct=NULL; only 5 forward closed picks lifetime (single strategy on ZN=F) | Wire bond resolver to close LQD/HYG/TLT/IEF/ZN=F backtest rows; backfill 30d then re-test |
| PENNY_IPO | **Not an instrumented asset class** — no IPO calendar, no smallcap universe, no float/fundamentals source; only 15 candidate rows total | Build IPO calendar scanner + smallcap universe definition before any strategy work |

## Honest Conclusion

**0/7 classes produced a winner under the pre-registered admissibility gate.**

This corroborates today's bulletproof NO_EDGE finding on the current production strategy library, *but does NOT prove the absence of edge in the asset classes themselves*. The dominant pattern across 4/7 classes (EQUITY, COMMODITY, ETF, BOND, PENNY_IPO) is **pipeline gaps, not strategy refutation**:

- **17 of 35 candidates (49%) returned n=0 or n<20** because the strategy was never implemented or never emits picks in production.
- **Only ~6 of 35 candidates** had n>=100 to be statistically testable. Of those, none cleared the winner gate.

### Recommended path forward (priority order)

1. **PLUMBING FIRST, NOT NEW STRATEGIES** — wire the 4 EQUITY academic edges, fix ETF + BOND resolvers, demote broken FOREX rsi2_MR. This is consistent with today's earlier finding (`project-money-ready-2026-05-31`) that the money-ready bottleneck is plumbing, not strategy.
2. **No SHADOW_PILOT_30d on any candidate today.** Every "best" candidate fails at least 2 of 5 winner-gate criteria. Operator should NOT size up.
3. **Literature-grounded fresh start is premature** — we have not yet refuted the academic library because we have not yet tested it. The 4-of-5-EQUITY-strategies-never-wired gap proves the deficiency is on our side, not the literature's.
4. **Re-run this hunt in 30d** after the wiring + resolver work lands and n>=100 cohorts exist per candidate.

### Risk register

- **Survivorship in COMMODITY golden-cross cluster** (n=26, WR 92%) — almost certainly label noise; do NOT promote without `tools/mutation_analysis.py`.
- **Heavy-tailed bootstrap CIs in CRYPTO/FOREX** — even point-estimate PF>1.2 is statistically indistinguishable from break-even without intrabar replay (per `reference-sl-optimization-needs-pricepath`).
- **Concentration risk**: FOREX 40% in one broken strategy, COMMODITY 83% in one bleeding strategy, BOND 100% on one symbol — class-level numbers are dominated by single-strategy/single-symbol behavior.

## Cross-references
- `money_ready_verdict.json` 2026-05-24
- `CLAUDE.md` MAJOR GOAL #1 (Tier 2 minimum gates)
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate-before-kill)
- `reference-sl-optimization-needs-pricepath` (intrabar replay required)
- `project-money-ready-2026-05-31` (plumbing not strategy is the bottleneck)
- 7 input deep-dives: `reports/peer_claude-deep-dive-WINNER-*_2026-05-31.md`

---

**Return string:** `SYNTHESIS:classes_tested=7:winners=0:no_winner=7:next_step=PLUMBING_NOT_NEW_STRATEGIES`
