# BOND Edge Deep-Dive — 2026-05-31

**Class:** BOND
**Current state (audit_dashboard sources):**
- `hf_stats.by_asset_class.BOND`: n=11, WR=45.5%, PF=0.57, Sharpe=-3.74, MDD=2.93%, Calmar=-0.67, **NET LOSING**.
- `asset_class_health.BOND`: empty (INSUFF, n<n_floor=100).
- `edge_stability_BOND.json`: 90d WR 40% / PF 0.41 (n=10); all-time WR 45.5% / PF 0.57 (n=11).
- `money_ready_verdict.BOND`: no entry → not money-ready (verdict not generated, n too low).
- Freebuff note: 78 raw picks accumulating, **0 closed** — accumulation is real but resolver is starved.

**Verdict:** BOND is not "no edge" — it is **no data + wrong instruments + wrong holding period**. We are emitting 5 picks total against 1 source (`kimi_riseoftheclaw` betting-against-beta), against an asset class whose alpha lives on **10-100 day mean-reversion + macro regime conditioning**, not on hourly OHLC.

---

## 1. Root causes of zero edge

### R1. Wrong unit-of-observation (single biggest issue)
The 11 closed BOND picks come almost entirely from one strategy (`betting-against-beta`, kimi_riseoftheclaw, n=5) plus 4 stragglers. Of the bond-native strategies registered (`bond_yield_curve`, `bond_yield_momentum`, `bond_yield_curve_slope`, `bond_mean_reversion`, `contango_roll_yield`), **3 are mis-classified as `asset_class='CRYPTO'`** in `strategy_registry` (ids 8781, 8782, 8783) and never reach the BOND verdict path. They have 25 picks combined that get attributed to the wrong class.

### R2. Wrong holding period vs cost stack
BOND picks in `edge_stability` are evaluated against the same TP/SL ladder as equity/crypto. Treasury moves of 30-50 bps require **5-30 day holds**. Our resolver appears to be stopping out / TP'ing on intraday noise. Avg pnl per BOND pick is -0.18, gross_loss 4.54 vs gross_win 2.57 → loss-side is the same magnitude as win-side, classic too-tight-SL signature (cf. CRYPTO 2026-05-31 SL refute lesson — same pattern likely repeats here).

### R3. No structural-data feed for the angles that matter
The yield-curve, credit-spread, breakeven-inflation, and auction-tail strategies need: FRED (DGS2/DGS10/T10YIE/BAMLH0A0HYM2), Treasury auction results (auctions.treasurydirect.gov), MOVE index. **None are wired into a production picker.** `requirements-bond-data.txt` exists but the only thing emitting BOND picks is the generic momentum scout pointed at TLT/IEF.

### R4. Buried winners — strategies built and shadow-only
`strategy_summary.BOND` shows TWO registered strategies that **already cleared statistical filters but are stuck in `sizing_status='shadow'`**:

| strategy_name      | n  | WR    | PF      | DSR   | PBO   | costed_sharpe | costed_mdd | status |
|--------------------|----|-------|---------|-------|-------|---------------|------------|--------|
| futures_momentum   | 4  | 100%  | 362.6   | —     | —     | —             | —          | shadow |
| bond_yield_curve   | 13 | 23%   | 65.4    | 1.82  | 0.41  | 4.43          | 0.058      | shadow |

`bond_yield_curve` has **DSR 1.82 (> 0 = real edge after multiple-testing correction)**, costed_sharpe 4.43, costed_mdd 5.8%, PBO 0.41 (acceptable). It's been left at n=13 / shadow for 2+ days. This is the buried-winner pattern from CLAUDE.md.

### R5. The "orphan backtests" cited are CODE, not RESULTS
`tools/backtest_bond_tlt_ief_momentum.py`, `tools/backtest_bond_credit_spread_overlay.py`, `tools/backtest_bond_duration_rotation.py`, `tools/backtest_bond_yield_curve.py` all **exist as runnable backtest tools** — but **zero rows in `bt_backtest_runs` carry a BOND symbol** (TLT/IEF/HYG/LQD/etc. — confirmed by SQL today). The PF 1.29-1.62 claim in the prompt is from session memory, not from the DB. **Action: run each tool and import.** Until then, calling them "PF 1.29-1.62 orphans" is unsourced.

---

## 2. Edge angles NOT YET tried in BOND (ranked feasibility)

| # | Angle                                | Data needed                       | Build effort | Expected sharpe | Why retail misses |
|---|--------------------------------------|-----------------------------------|--------------|-----------------|-------------------|
| 1 | **Yield-curve regime conditioning** (steepener vs flattener filter on every other strat) | FRED DGS2,DGS10 (free) | 2h | n/a (gate, not strat) | Treats class as homogeneous |
| 2 | **HY-IG credit spread mean reversion** (HYG vs LQD z-score) | Yahoo/FRED BAMLH0A0HYM2 | 4h | 0.8-1.2 | Treats HY = equity-like, ignores spread regime |
| 3 | **Treasury auction tail trade** (auction yield > WI by ≥1bp → next-day TLT/IEI long) | TreasuryDirect API (free) | 6h | 1.0-1.5 | Auction calendar / WI not in price data |
| 4 | **Breakeven inflation (TIPS-Nominal) reversal** (z-score T10YIE vs SPX-vol cluster) | FRED T10YIE,VIX | 3h | 0.7-1.0 | Macro overlay, not chart-pattern |
| 5 | **Duration rotation via Fed cycle stage** (Powell speech NLP → TLT vs IEF tilt) | FOMC calendar + Bloomberg/news | 8h | 0.6-1.0 | Requires event-window discipline |
| 6 | **MBB-vs-TLT mortgage spread MR** (FNMA OAS z-score) | FRED MORTGAGE30US, MBB price | 4h | 0.5-0.8 | Mortgage spread → rates relationship hidden |
| 7 | **MOVE-implied vol regime overlay** (only emit BOND signals when MOVE < 100; suppress in vol spikes) | Yahoo ^MOVE | 1h | n/a (filter) | Equity-vol bias: retail watches VIX not MOVE |
| 8 | **Sovereign vs corporate spread carry** (EMB vs LQD risk-on/off rotation) | Yahoo EMB,LQD | 3h | 0.6-0.9 | EM bonds = "exotic" in retail mind |

Top-3 by RoI: **#1 (regime gate, smallest build, biggest cross-impact)**, **#2 (single clean number with mean-reverting half-life ~30d)**, **#7 (1-hour overlay)**.

---

## 3. Two concrete strategies to build next session

### Strategy A — `bond_credit_spread_mr_v1` (HY-IG mean reversion)

- **Citation:** Asvanunt & Richardson (2017) "The Credit Risk Premium" J.Fixed Income; Ilmanen "Expected Returns" Ch.10.
- **Universe:** HYG (long leg), LQD (short leg / pair).
- **Signal:** daily z-score of `log(HYG/LQD)` vs trailing 252-day mean. Long HYG / short LQD when z < −2.0, exit at z > −0.5. Reverse short-spread when z > +2.0.
- **Holding:** 10-30 days, time-stop at 45d.
- **Sizing:** vol-target 8% annualized.
- **Risk:** flat positions if VIX > 30 or MOVE > 140 (credit-shock filter).
- **Data:** Yahoo daily (already wired via yfinance), no new vendor.
- **Expected:** Sharpe ~0.9, WR 55-60%, PF 1.4-1.7 per academic priors.

### Strategy B — `bond_yieldcurve_regime_gate_v1` (regime conditioner, not a strategy)

- **Citation:** Estrella & Mishkin (1998) FRBNY; Adrian/Crump/Moench (2013) ACM term-premium decomposition.
- **Mechanism:** compute slope = `DGS10 - DGS2` daily; classify regime ∈ {steepening, flattening, inverted, normal} via 30d delta + level.
- **Apply as gate** on every BOND strategy: only emit long-TLT/long-duration picks in **steepening** or **inverted-and-mean-reverting** regimes; only emit short-duration/long-HYG in **flattening**.
- **Acceptance:** must improve any single bond-emitting strategy's WR by ≥5pp on 2024-2026 paper backtest without halving signal count.
- **Data:** FRED daily DGS2/DGS10 (free, free key already in repo via `requirements-bond-data.txt`).
- **Build effort:** 2h. Drop-in module + 1 SQL view.

---

## 4. Buried-winner candidates (n<30 but PF>1.5)

Pulled from `strategy_summary WHERE asset_class='BOND'` + the mis-classed CRYPTO bond strategies:

| strategy             | live class      | n  | WR    | PF    | DSR   | PBO  | Verdict                                       |
|----------------------|-----------------|----|-------|-------|-------|------|-----------------------------------------------|
| **bond_yield_curve** | BOND            | 13 | 23%   | 65.4  | 1.82  | 0.41 | **PROMOTE candidate** (DSR>0, costed_sharpe 4.4); n too low but stats survive correction. Move from shadow → micro-live with $50 size, monitor for 30d. |
| **futures_momentum** | BOND            | 4  | 100%  | 362.6 | —     | —    | Too small to act, but rank_class=1; **add to watchlist + force-resolve any stuck picks**. |
| bond_yield_momentum  | CRYPTO (wrong)  | 16 | 25%   | n/a   | —     | —    | First: **fix asset_class='BOND'** in registry; then re-aggregate. |
| bond_yield_curve_slope | CRYPTO (wrong)| 6  | 0%    | 0     | —     | —    | Same — re-tag, then assess. |
| bond_mean_reversion  | CRYPTO (wrong)  | 3  | 0%    | 0     | —     | —    | Same — re-tag. |
| contango_roll_yield  | CRYPTO (wrong)  | 10 | n/a   | n/a   | —     | —    | Same — re-tag (this is a futures roll strategy, definitionally not crypto). |

---

## 5. First operator action recommendation

**SINGLE-COMMAND fix that unlocks everything else (10 min):**

```sql
UPDATE strategy_registry
SET asset_class='BOND', notes=CONCAT(IFNULL(notes,''),' [2026-05-31 class-reclass: bond family wrongly tagged CRYPTO]')
WHERE strategy_id IN ('bond_mean_reversion','bond_yield_curve_slope','bond_yield_momentum','contango_roll_yield')
  AND asset_class='CRYPTO';
```

This alone:
1. Moves 35 picks (16+6+3+10) into the BOND verdict path on next dashboard generator run.
2. Lifts BOND n from 11 → ~46 closed (still INSUFF but halfway to n_floor=100).
3. Exposes whether those strategies are real losers or just mis-routed.

**Then, in priority order (next 24h):**
1. Run the 4 existing `tools/backtest_bond_*.py` tools and import results into `bt_backtest_runs` — confirms or refutes the "PF 1.29-1.62 orphan" claim before we spend strategy-build budget.
2. Promote `bond_yield_curve` from `sizing_status='shadow'` → `'micro_live'` at $50 notional, 30-day probation (it already has DSR 1.82 / PBO 0.41).
3. Implement `bond_credit_spread_mr_v1` (Strategy A above) — 4 hours, no new data vendor needed.
4. Implement `bond_yieldcurve_regime_gate_v1` (Strategy B) as a **gate**, applied to ALL bond strategies — 2 hours.
5. Do **not** size up the betting-against-beta picks (n=5, PF 0.37, gross_loss 2x gross_win) — refuted.

---

**Files of record:**
- `audit_dashboard/data/edge_stability/edge_stability_BOND.json`
- `audit_dashboard/data/dashboard_data.json::hf_stats.by_asset_class.BOND`
- `tools/backtest_bond_{credit_spread_overlay,duration_rotation,tlt_ief_momentum,yield_curve}.py` (unrun)
- `baby_strategies/bond_yield_curve_momentum.py` (registered, shadow)
- `strategy_summary` BOND rows ids 77 (`futures_momentum`), 128 (`bond_yield_curve`)

— claude-opus-4-7, 2026-05-31
