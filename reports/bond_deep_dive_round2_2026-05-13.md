# BOND Deep-Dive — Round 2

**Date:** 2026-05-13
**Author:** Claude Opus 4.7 (1M ctx)
**Prior round:** `reports/bond_root_cause_2026-05-12.md`, queued in `DAILY_IDEAS.md`
**Live state (`asset_class_health.BOND`, 2026-05-12T21:53Z):** n=11 resolved, WR 54.5%, PF 0.66, total_pnl −1.53%, `status=thin_sample`, `sizing_allowed=false`.

> Note: the /audit banner still cites `n=18 / PF 1.72 / WR 55.6%` from the older snapshot. The newer `edge_stability_BOND.json` (n=12, PF 0.66) is the trustworthy verdict-grade number. The `PF 1.72` number came from 6 legacy `ZN=F` futures_momentum trades that have rolled off the 90-day window.

---

## 1. Round-1 progress check

Round-1 (`bond_root_cause_2026-05-12.md`) produced a verified three-layer blocker diagnosis (elite_score floor 40 too high for low-vol bond signals; `FORWARD_GATE_MIN_TRADES=50` with no per-class override; bond_picks.json never merged to `active_picks.json`). **None of the three PRs (BR-1/BR-2/BR-3) shipped.** Evidence:

- `non_crypto_agent/data/bond_picks.json` 2026-05-13T02:12Z: `total_raw=10, quality=0, picks=[]`. Curation gate still rejecting everything.
- `alpha_engine/data/active_picks.json`: 0 BOND-symbol picks active.
- `edge_stability_BOND.json` n still stuck at ~12.

Textbook seeds named in MEMORY (Cochrane-Piazzesi curve momentum, Fleckenstein-Longstaff-Lustig TIPS MR, Frazzini-Pedersen IG carry) are **NOT in code** — `grep` on `alpha_engine/proven_research_strategies.py` returns 0 hits for those names. They live on paper only. The active emitter (`bond-agent.yml`) runs 5 generic strategies (`bond_yield_momentum`, `bond_duration_rotation`, `bond_mean_reversion`, `bond_connors_rsi2`, `bond_credit_spread_mean_reversion`) over 14 ETFs — none of which encode the proven-research priors.

---

## 2. Live audit gaps

Active BOND strategies per `edge_stability_BOND.json::per_strategy` (all `INSUFFICIENT_DATA`, all n≤5):

| Strategy | System | n | WR% | PF | Note |
|---|---|---|---|---|---|
| betting-against-beta | kimi_riseoftheclaw | 5 | 40 | 0.37 | **Worst drag** — TLT LONG losses dominate |
| pairs-trading | kimi_riseoftheclaw | 2 | 50 | 1.87 | HYG LONG, only multi-pick survivor |
| proven_vwap_mean_reversion | alpha_engine_fast | 1 | 100 | 999 | singleton, ignore |
| vwap-reversion-scout | kimi_riseoftheclaw | 1 | 100 | 999 | singleton |
| rs-breakout-scout | kimi_riseoftheclaw | 1 | 0 | 0 | singleton loss |
| quick_engine | crypto_ml_edge | 1 | 0 | 0 | mis-tagged crypto strat |
| ema_stack_momentum | multi_asset_scanner | 1 | 100 | 999 | singleton |

**Silent-death evidence:** all 5 bond-agent strategies produce raw signals but 0 quality (curation rejects). The 12 picks visible in edge_stability are legacy kimi_riseoftheclaw + alpha_engine_fast emissions, **not** the actual bond-agent. **Symbol concentration:** 80% TLT, balance HYG. Zero IEF/IEI/SHY/TIP/LQD/MUB picks ever resolved — a 14-ETF universe is effectively a 2-ETF universe.

`top3_strategy_pnl_share = 0.796`, `pareto_flag = STRATEGY_CONCENTRATED`. Not breadth, not edge, just two strategies on TLT.

---

## 3. Three pilot strategies (code-ready)

All three use free data (yfinance + FRED + Cboe MOVE), avoid the `outcome_resolver` live-close bug by exiting on **time + level**, not yfinance spot, and target ≥35 events/year each (→ ≥105 in 90 days combined).

### Pilot A — TIPS MR (Fleckenstein-Longstaff-Lustig 2014, "TIPS-Treasury Puzzle")
- **Entry:** when `breakeven_inflation = yield(IEF) − yield(TIP)` (FRED `DGS10`−`DFII10`) deviates >1.0σ from 60-day mean → trade *the* TIP-vs-IEF spread back to mean.
- **Direction:** breakeven > mean+1σ → LONG IEF / SHORT TIP. breakeven < mean−1σ → LONG TIP / SHORT IEF.
- **Exit:** revert to ±0.25σ, or 15 trading-day stop, or |move|>3σ stop-loss.
- **Free data:** yfinance TIP/IEF closes + FRED `T10YIE` daily series.
- **Expected events/yr:** ~40 (deviations beyond 1σ on a 60-day MA happen roughly 8×/yr per leg, two-sided, both rolled).

### Pilot B — Treasury-curve carry momentum (Cochrane-Piazzesi 2005)
- **Entry:** rank monthly the four belly/long Treasury ETFs (IEI, IEF, TLH, TLT) by 3-month total return. LONG top quartile, SHORT bottom quartile. Rebalance monthly first trading day.
- **Filter (regime gate):** only fire if `MOVE index < 20-day MA` (low vol regime — Cochrane-Piazzesi premium pays only outside crisis); otherwise SKIP that month and log.
- **Exit:** next monthly rebalance OR `MOVE > +1σ` triggers immediate flatten.
- **Free data:** yfinance ETF closes + Cboe MOVE via `^MOVE` (or `MOVE` on Investing.com fallback).
- **Expected events/yr:** ~24 (2 picks/month × 12).

### Pilot C — HYG-LQD credit-spread mean reversion (Frazzini-Pedersen IG-vs-HY carry inverse)
- **Entry:** compute `cs = log(LQD/HYG)`; if 1d Δcs > +2σ of 60-day rolling stdev → LONG HYG / SHORT LQD (spread widened, mean-revert). Inverse for −2σ.
- **Filter:** require SPY 20-day return > −5% (skip crisis regime — credit spreads trend in panics, don't revert).
- **Exit:** Δcs < ±0.5σ, OR 10-day hold, OR adverse 2× initial stdev.
- **Free data:** yfinance HYG/LQD + SPY daily.
- **Expected events/yr:** ~50 (2σ excursions on 1-day Δ of 60-day series occur ~weekly).

**Combined ramp math:** 40+24+50 = 114 events/yr → ~28 picks per 90-day window per pilot if independent, but with overlap and skip-filter rejections expect 70–95 closed picks in 90 days. Combined with the existing ~12/quarter from legacy strategies, **n=100 in 90 days is on the edge of achievable** — recommend running all three in shadow plus relaxing curation (BR-1 from Round-1) to let the existing emitter contribute another 15–25 picks.

All three strategies are **code-ready as Python signal functions** following the `(data: dict[str,DataFrame], context: dict) -> list[pick]` signature in `proven_research_strategies.py`. Adding them = ~150 LoC + register in `BOND_STRATEGIES` dict.

---

## 4. Tonight's paper-trade pick

**None.** Reasons:

1. Bond emitter produced 10 raw signals at 2026-05-13T02:12Z but 0 passed curation. No vetted signal exists.
2. Bond markets trade 24/5 but the relevant ETFs (TLT/IEF/TIP/HYG/LQD) only have liquid execution during NYSE hours (09:30–16:00 ET). Tonight is post-close; bid-ask spreads on after-hours TLT routinely exceed the typical strategy edge.
3. The three pilots above need ≥1 backtest run before any shadow paper trade — entering blind contradicts `feedback_confidence_is_not_edge`.

**Tomorrow's action:** at 09:35 ET, compute Pilot A (TIPS MR) signal — if breakeven_inflation deviation >1σ, place a shadow paper pick on `TRUSTOURSCORE` or `TESTER` account (per `tv-paper-trade` skill), 0.5% position, no real-money sizing.

---

## 5. Acceptance gate (shadow → live sizing)

A pilot promotes from shadow to live (`sizing_allowed=true` in `edge_stability_BOND.json`) when **all five** are met:

1. **n ≥ 30 closed shadow picks for that pilot** (per-strategy, not aggregate).
2. **PF ≥ 1.5 and WR ≥ 50%** sustained over the most recent 30 picks (rolling window).
3. **MDD ≤ 8%** intraday peak-to-trough on the shadow paper account (lower than charter's 20% because bond vol is structurally lower — must still beat 60/40 buy-and-hold MDD).
4. **CLV check passed:** mean fill price ≤ signal price + 2bp slippage (bond ETFs have wider spreads than equities; verify execution realism).
5. **Resolver audit:** sample 5 closed picks, verify exits were time/level-based per spec, NOT yfinance-spot stamped at run time (cross-check via `outcome_resolver.py` log) — guards against the `feedback_noncrypto_resolver_live_close_bug` inflation that already polluted prior BOND verdicts.

**Stop-loss (auto-revert to shadow):** any pilot whose live-money 30-pick rolling PF drops below 1.0 OR WR below 45% gets demoted back to shadow within 1 trading day. No grace period.

---

## Summary

- **Round-1 verdict re-confirmed:** the three-layer fix (BR-1/2/3) never shipped; bond_picks.json still emits raw=10, quality=0, picks=[] daily.
- **Live n actually regressed:** /audit banner shows `n=18` but `edge_stability_BOND.json` shows `n=12, PF 0.66` — the `1.72 PF` was rolled-off legacy futures; current state is sub-floor on both PF and n.
- **Three pilot strategies specced:** TIPS MR (Fleckenstein), curve carry momentum (Cochrane-Piazzesi) with MOVE regime gate, HYG-LQD credit-spread MR (Frazzini-Pedersen inverse) — combined ~114 events/yr, free-data, time/level exits to dodge resolver bug.
- **No paper trade tonight:** post-close, no curated signal, and pilots need ≥1 backtest before shadow placement — tomorrow 09:35 ET re-run.
