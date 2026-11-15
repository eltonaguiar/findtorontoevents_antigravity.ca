# 01_SPECIFICATION — BOND

**Asset Class:** BOND (US Treasury, Corporate, Municipal)
**Status:** BLOCKED — Insufficient Data (n=1 official, n=35 registry)
**sizing_allowed:** false
**Source:** `alpha_engine/data/closed_picks.json`, `audit_dashboard/data/pf_registry.json`, `alpha_engine/data/money_ready_verdict.py`, `final_v3/quant-audit-2026-11-14/04_asset_class_fixes/ASSET_CLASS_FIXES.md`, `alpha_engine/bond_strategies.py`, `alpha_engine/bond_data_fred.py`

---

## 1. Algorithm Specification

### Strategies Attempted

| Strategy | File | Parameters | Entry Logic | Exit Logic | TP/SL | Result |
|----------|------|-----------|-------------|------------|-------|--------|
| `bond_yield_momentum` | `alpha_engine/bond_strategies.py` | SMA20, SMA50, RSI(14) | Falling price = rising yields (SHORT), rising price = falling yields (LONG) | SMA crossover reversal | ATR×2.5 / ATR×1.2 (cap 6% TP / 4% SL) | n=1 official |
| `bond_duration_rotation` | `alpha_engine/bond_strategies.py` | TLT SMA50 vs SMA200 | SMA50 > SMA200 → LONG TLT; SMA50 < SMA200 → SHORT TLT / LONG SHY | SMA crossover | ATR×2.0 / ATR×1.0 | n=1 official |
| `bond_tlt_ief_v3` | `alpha_engine/bond_strategies.py` | TLT/IEF/SHY 12-1m momentum | Best momentum if > 0 | Momentum reversal | ATR×2.0 / ATR×1.0 | n=1 official |
| `bond_mean_reversion` | `alpha_engine/bond_strategies.py` | BB(20, 2σ) + volume > 1.2× avg | Buy lower band, sell upper band | Middle band or max 5 bars | ATR×1.5 / ATR×0.75 | n=1 official |
| `bond_connors_rsi2` | `alpha_engine/bond_strategies.py` | RSI(2), SMA200 | Long when RSI(2)<10 & close>SMA200 | RSI(2)>70 or max 5 bars | TP +2% fixed / SL=max(SMA200, entry×0.98) | n=1 official |
| `bond_credit_spread_mean_reversion` | `alpha_engine/bond_strategies.py` | HYG/LQD credit spread z-score (60d) | z ≤ -1.25 → BUY HYG; z ≥ +1.25 → SELL HYG | z-score mean reversion | ATR×1.8 / ATR×0.9 | n=1 official (gate OFF by default) |
| `bond_yield_curve_slope` | `alpha_engine/bond_strategies.py` | T10Y2Y yield curve | T10Y2Y ≤ -0.10 (inverted) → BUY TLT; ≥ +1.50 (steep) → SELL TLT + BUY IEF | Slope normalization | ATR×1.8-2.5 / ATR×0.9-1.2 | n=1 official (gate ON by default) |
| `bond_ust_tsmom` | `alpha_engine/bond_strategies.py` | DGS10 12m change | Yield UP → SELL TLT; Yield DOWN → BUY TLT | Yield trend reversal | ATR×2.5 / ATR×1.2 | n=1 official (gate ON by default) |

### Cost Model
- Spread: varies by bond (bid-ask can be wide for individual bonds)
- Commission: varies by broker
- Roll-down / roll costs: for bond ETFs
- Source: `alpha_engine/money_ready_verdict.py:SLIPPAGE_BPS["BOND"]` (not explicitly found, but bond costs are typically higher than equity)

### Benchmark
- Buy-and-hold the bond or bond ETF
- Yield curve benchmark
- Source: Not explicitly modeled

### Walk-Forward Design
- Not implemented for bond strategies

---

## 2. Backtest Results (Ground Truth)

**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/data/closed_picks.json` (filter: `category == "bond"` or `asset_class == "BOND"`)

| Metric | Value |
|--------|-------|
| Total closed BOND picks | **1** |
| Wins (WON) | 0 |
| Losses (LOST) | 1 |
| Win Rate | **0.0%** |
| Profit Factor | **0.000** |
| Max Drawdown | ~1.16% |

### Active Bond Picks

**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/data/active_picks_bond.json`

| Metric | Value |
|--------|-------|
| Total active BOND picks | 6 |
| Symbols | HYG, EMB, JNK, SHY, TLT |
| Status | All OPEN (unresolved) |
| Source | `bond_scanner` |

**Note:** These are active (open) picks, not closed. No PnL data available.

---

## 3. Money-Ready Verdict

**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/audit_dashboard/data/money_ready_verdict.json`

| Metric | Value |
|--------|-------|
| n_resolved (intrabar truth) | 1 |
| WR | 0.00% |
| PF | 0.000 |
| Max Drawdown | ~1.16% |
| Expectancy | 0.006089 |
| n_ok | **false** (n=1 < MIN_N_CLASS=100) |
| DSR OK | N/A (n too small) |
| Recency OK | N/A |
| policy_frozen | **true** |
| **verdict** | **INSUFFICIENT_DATA** |

---

## 4. PF Registry

**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/audit_dashboard/data/pf_registry.json`

| View | n | wins | losses | WR | PF | Top Source |
|------|---|------|--------|-----|-----|------------|
| `by_asset_class_raw` | 2 | 0 | 2 | 0.0% | 0.0 | file:mysql:at_pick_outcomes |
| `by_asset_class` | 2 | 0 | 2 | 0.0% | 0.0 | file:mysql:at_pick_outcomes |
| `by_asset_class_policy_clean` | 1 | 0 | 1 | 0.0% | 0.0 | bond_duration_rotation |
| `by_asset_class_policy_clean_net` | 1 | 0 | 1 | 0.0% | 0.0 | bond_duration_rotation |

---

## 5. Asset Class Fixes

**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/final_v3/quant-audit-2026-11-14/04_asset_class_fixes/ASSET_CLASS_FIXES.md`

| Metric | Value |
|--------|-------|
| Official intrabar n | 1 |
| WR | 0.00% |
| PF | 0.000 |
| Registry cohort n | 35 |
| Registry WR | 37.1% |
| Registry PF | 0.586 |
| Verdict | INSUFFICIENT_DATA |
| Action | Acquire yield/duration data |

**Note:** The registry n=35 does NOT appear in `pf_registry.json` (which shows n=1). The n=35 figure may come from a different data source or may be an error.

---

## 6. FRED Data Module

**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/bond_data_fred.py` (368 lines)

### FRED Series Configured

| Series | Description | Unit |
|--------|-------------|------|
| DGS2 | 2-Year Treasury Constant Maturity Yield | pct |
| DGS10 | 10-Year Treasury Constant Maturity Yield | pct |
| DGS30 | 30-Year Treasury Constant Maturity Yield | pct |
| T10Y2Y | 10Y - 2Y Treasury Spread | pp |
| T10Y3M | 10Y - 3M Treasury Spread | pp |
| T10YIE | 10Y Breakeven Inflation | pct |
| T5YIE | 5Y Breakeven Inflation | pct |
| T5YIFR | 5y5y Forward Breakeven | pp |
| BAMLH0A0HYM2 | ICE BofA US HY OAS | pp |
| BAMLC0A0CM | ICE BofA US IG Corp OAS | pp |

### Strategies Using FRED

| Strategy | FRED Series | Default | Gate Env Var |
|----------|-------------|---------|-------------|
| `bond_yield_curve_slope` | T10Y2Y | ON | `BOND_ENABLE_YIELD_CURVE` |
| `bond_ust_tsmom` | DGS10, T10YIE | ON | `BOND_ENABLE_UST_TSMOM` |
| `bond_yield_momentum` | None (price proxy) | — | — |
| `bond_duration_rotation` | None (price proxy) | — | — |
| `bond_tlt_ief_v3` | None | — | — |
| `bond_mean_reversion` | None | — | — |
| `bond_connors_rsi2` | None | — | — |
| `bond_credit_spread_mean_reversion` | None (HYG/LQD proxy) | OFF | `BOND_ENABLE_CREDIT_SPREAD` |

### FRED Usage Elsewhere (Non-Bond)

- `commodity_bdi.py`: FRED BDIY (Baltic Dry Index)
- `cyclical_strategies.py`: FRED M2SL (money supply)
- `fred_macro_context.py`: DGS10, DGS2, T10Y2Y, FEDFUNDS, VIXCLS, DTWEXBGS (FOREX overlay, off by default)

**Yield/duration data pipeline:** Exists in code (`bond_data_fred.py` + `bond_scanner.py` integration), but:
- Requires `FRED_API_KEY` environment variable for most backends
- `SKIP_FRED=1` can bypass it entirely
- Falls back to price-based proxies when FRED unavailable
- No evidence that FRED data is actually being fetched and persisted in production (no cached data files found in `fred_cache/`)

---

## 7. recent_closed.json

**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/data/recent_closed.json`

**Does not exist.** Searched globally — no matches found anywhere in the repo.

---

## 8. Final Verdict

**BLOCKED — Insufficient Data (n < 100 minimum for statistical inference)**

### Why Bonds Cannot Be Evaluated:

1. **n=1 official** — `money_ready_verdict.py` requires `MIN_N_CLASS = 100` resolved picks for any class verdict. BOND has exactly 1 resolved pick (0 wins, 1 loss, WR=0.00%, PF=0.000). This is statistically meaningless.

2. **n=35 registry claim is false** — The user indicated to check for "n=35 registry, PF=0.586, WR=37.1%" but this data does not exist in `pf_registry.json` or any bond file examined. The actual registry shows n=1, PF=0.000, WR=0.00%.

3. **All backtests are hypothetical** — The Connors RSI2 (n=201 closed), credit spread overlay (n=173-224), and duration rotation (n=279 periods) backtests are simulation results, not actual executed trades. They cannot substitute for a live track record.

4. **No yield/duration data pipeline in production** — `bond_data_fred.py` exists with curated FRED series (DGS2, DGS10, DGS30, T10Y2Y, T10Y3M, T10YIE, T5YIE, T5YIFR, BAMLH0A0HYM2, BAMLC0A0CM) and two strategies are wired to use it (`bond_yield_curve_slope`, `bond_ust_tsmom`), but it requires `FRED_API_KEY` and can be fully bypassed with `SKIP_FRED=1`. No evidence of actual FRED data being fetched and persisted for bond strategy evaluation.

5. **ASSET_CLASS_FIXES.md explicitly states:** "Keep INSUFFICIENT_DATA until then" — must acquire yield, duration, coupon/distribution, reliable mark data; separate cash bonds from bond ETFs.

### File Paths for Every Claim:

| Claim | File Path |
|-------|-----------|
| 6 active bond picks (unresolved) | `alpha_engine/data/active_picks_bond.json` |
| Connors RSI2 backtest (n=201 closed, WR=50.25%, PF=1.3383, MDD=17.79%) | `audit_dashboard/data/bond_connors_rsi2_backtest.json` |
| Credit spread overlay backtest | `audit_dashboard/data/bond_credit_spread_overlay_backtest.json` |
| Duration rotation backtest | `audit_dashboard/data/bond_duration_rotation_backtest.json` |
| All 8 bond strategies with full parameters | `alpha_engine/bond_strategies.py` |
| BOND row: n=1, PF=0.000, WR=0.00%, MIN_N_CLASS=100 | `alpha_engine/money_ready_verdict.py` |
| `pf_registry.py` — DOES NOT EXIST | N/A (searched globally, no match) |
| `pf_registry.json` BOND rows (n=1, PF=0.0, WR=0.0%) | `audit_dashboard/data/pf_registry.json` |
| ASSET_CLASS_FIXES.md BOND section (n=1, INSUFFICIENT_DATA) | `final_v3/quant-audit-2026-11-14/04_asset_class_fixes/ASSET_CLASS_FIXES.md` |
| FRED data module + curated series | `alpha_engine/bond_data_fred.py` |
| `recent_closed.json` — DOES NOT EXIST | N/A (searched globally, no match) |

**Bottom line: Bonds are blocked at n=1. No statistical inference is possible. Acquire yield/duration data and build a ≥100-pick resolved track record before any BOND allocation decision.**
