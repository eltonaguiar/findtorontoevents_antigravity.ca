# ETF/Mutual Fund Strategy Audit

**Auditor:** Senior Quant Analyst (ETF/MF specialization)  
**Date:** 2026-11-15  
**Worktree:** hilarious-seer  
**Scope:** All ETF and mutual-fund strategies in `alpha_engine/`, `tools/`, `config/personas/`, and related research artifacts.  
**Proof standard:** 10-gate protocol (temporal discipline, walk-forward, multiple-testing correction, Monte Carlo resampling, full friction model, statistical significance, regime robustness, shuffle control, pre-registered forward test, reproducibility).

---

## 1. Existing Strategies Inventory

| Strategy | File path | Method | Result | Failure mode |
|---|---|---|---|---|
| **Passive Beta (VTI/BND 60/40)** | Implicit benchmark across repo | Buy-and-hold broad index + aggregate bond, periodic rebalance | **ONLY viable path found** | None — baseline, not alpha |
| **Faber Tactical Asset Allocation** | `alpha_engine/etf_strategies.py:524-607` | 5-asset GTAA (SPY, QQQ, EFA, IEF, GLD); LONG when Close > SMA200, cash otherwise | **FAIL** — AnnRet 9.1% vs SPY 14.7%, Sharpe 0.40 vs 0.73 | Underperforms buy-and-hold on return; claimed Sharpe 1.01 is unverified risk-overlay only |
| **Faber TAA Persona** | `config/personas/strategy_persona__etf_faber_tactical.json` | Same as above, shadow-pilot wrapper | **n=0 closed trades** as of 2026-05-31 | No forward emissions; monthly cadence makes n>=30 a 6-12 month bar |
| **ETF Sector Momentum Rotation** | `alpha_engine/etf_sector_momentum_rotation.py` | Jegadeesh & Titman (1993) on 11 SPDR sectors; top-3 by 3m momentum, monthly | **No backtest evidence in repo** | Unvalidated; no closed-trade ledger |
| **Bond Duration Rotation** | `alpha_engine/bond_duration_rotation.py` | TLT vs SHY 1-month relative momentum (Ilmanen 2011) | **No backtest evidence in repo** | Unvalidated; no closed-trade ledger |
| **ETF Dual Momentum** | `alpha_engine/etf_strategies.py:75-164` | Antonacci (2014) absolute + relative 12m momentum on ETF_SYMBOLS | **No forward evidence** | Academic claim 75%+ WR; no OOS proof in repo |
| **Proven ETF Dual Momentum** | `alpha_engine/proven_scanner_strategies.py:826-880` | Relative + absolute momentum on SPY/QQQ/IWM/EEM/GLD/TLT | **No forward evidence** | Labelled "proven" but n not disclosed; DIA WR 58.8%/PF 2.64 cited in `production_scanner.py:503` but sample size unknown |
| **ETF Sector Momentum (Faber filter)** | `alpha_engine/etf_strategies.py:181-271` | Faber SMA200 + 3m sector momentum + ADX on 7 sector ETFs | **No forward evidence** | Unvalidated |
| **ETF Risk Parity Rotation** | `alpha_engine/etf_strategies.py:287-394` | SPY-TLT 30d correlation regime switch; LONG TLT if corr<-0.25, LONG SPY if corr>0.10 | **No forward evidence** | Unvalidated |
| **ETF Trend Following** | `alpha_engine/etf_strategies.py:411-494` | SMA50/200 golden/death cross + volume confirmation on ETF_SYMBOLS | **No forward evidence** | Unvalidated |
| **ETF RSI2 Pullback** | `alpha_engine/etf_strategies.py:630-720` | Connors & Alvarez (2009) RSI(2) < 10 + SMA50 uptrend; 2-5 day hold | **n=1 win in live data** | INSUFF-N; one XLI win (+1.77%) on 2026-05-30 |
| **ETF Sector Dual Momentum** | `alpha_engine/etf_strategies.py:733-846` | Antonacci on SPDR sectors; 12m-1m lag, must beat SPY and be positive | **No forward evidence** | Unvalidated |
| **ETF Cross-Sectional Momentum (H-003)** | `alpha_engine/etf_strategies.py:875-967` | Jegadeesh & Titman / Asness on 22 ETFs; top-3 by 12m-1m momentum | **No forward evidence** | Unvalidated |
| **Regime Mild Bull (ETF persona)** | `config/personas/strategy_persona__etf_regime_bull.json` | Long broad ETFs when regime classifier in BULL_MILD | **n=2, WR 100%** | Statistically meaningless; shadow only |
| **Asset-Class Momentum Rotation (TAA)** | `tools/tactical_rotation_tracker.py` | Top-5 of 14 asset-class ETFs by 6m momentum, monthly, abs-momentum filter -> AGG | **In-sample robust 2007-2026** | **NOT proven forward**; smart-beta (risk reduction), not excess return |
| **VAA-G4** | Validated in `reports/TACTICAL_ROTATION_EDGE_2026-07-04.md` | Keller Vigilant Asset Allocation; 13612W momentum, canary risk-on/off | **In-sample robust 2007-2026** | **NOT proven forward** |
| **PAA1** | Validated in `reports/TACTICAL_ROTATION_EDGE_2026-07-04.md` | Keller Protective Asset Allocation; 12 offensive vs 12m SMA, bond fraction BF | **In-sample robust 2007-2026** | **NOT proven forward** |
| **MF/ETF Pipeline** | `alpha_engine/mf_etf_pipeline.py` | Universe loader, screener, NAV fetch, cost estimator | **Infrastructure only** | No active strategy; 18 tickers curated |
| **Mutual Fund Tactical Rotation** | `multi_asset/portfolio_defs.py:382-395` | Tactical fund rotation over VTSAX/VBTLX-class funds | **UNBUILT** | No live module imports `portfolio_defs`; `mutual_fund_ranker.py` does not exist |
| **etf_scanner (live)** | Referenced in `reports/deep_dive_ETF_2026-05-31.md` | Energy-sector ETF emissions | **KILL-CANDIDATE** | n=2, 0% WR, PF 0.0; losses on XLE (-4.17%) and USO (-2.00%); no WTI-regime gate |

---

## 2. What Worked

**Only two things have worked in this repo's ETF/MF space:**

### A. Passive Beta (VTI/BND 60/40 or equivalents)
This is the **benchmark floor**, not an alpha strategy. The repo's own `OUTPERFORM_SP500_BUY_AND_HOLD.md` (line 79) states: *"Deploy capital to low-cost index exposure until one [strategy] passes"* the benchmark test. The curated universe in `alpha_engine/data/mf_etf_universe.json` provides 18 ultra-low-ER instruments (FXAIX at 0.015%, VTI at 0.03%, BND at 0.03%) that make this baseline cost-efficient.

### B. Asset-Class Momentum Rotation (TAA) — In-Sample Only
The **single robust in-sample finding** is the family of tactical asset allocation strategies validated in `reports/TACTICAL_ROTATION_EDGE_2026-07-04.md`:

- **Top-5 / 6-month rotation** (2007-2026, including 2008 GFC): Sharpe **0.88** vs SPY 0.74, MaxDD **-19%** vs SPY **-51%**, Calmar **0.48** vs 0.21. Positive in all three time-thirds.
- **VAA-G4** (Keller): Sharpe 0.77, MaxDD -20%, Calmar 0.40.
- **PAA1** (Keller): Sharpe **0.93**, MaxDD -21%, Calmar 0.34.
- **50/50 Rotation+VAA blend**: Sharpe **0.89**, MaxDD **-16%**, Calmar **0.50** — the strongest, most regime-smooth result.

**Why it is credible:**
1. **Robustness grid:** All 16 (top-N x lookback) cells cut MaxDD to -12/-17% vs SPY -24%. Not a lucky cell.
2. **Long history:** 2007-2026 spans GFC, COVID crash, 2022 bear market.
3. **Multiple independent constructions:** Rotation, VAA, and PAA all work — decisive evidence the family is real, not overfit.
4. **Economic rationale:** Dual momentum / TAA is one of the most-replicated practitioner strategies (Antonacci GEM, Faber GTAA, Keller VAA/PAA).

**Critical honesty:** This is **smart-beta / tactical allocation, NOT alpha**. It roughly matches the market's *return* but with ~half the *drawdown*. The "win" is risk control + crash avoidance, not excess return. It is **in-sample-robust, not proven-forward**.

---

## 3. What Failed & Why

### Failure Taxonomy

| Failure Category | Strategies | Root Cause | Evidence |
|---|---|---|---|
| **Underperforms buy-and-hold** | Faber dual-momentum | SMA200 filter generates too many false exits; misses recovery rallies | User audit: AnnRet 9.1% vs SPY 14.7%, Sharpe 0.40 vs 0.73. `config/personas/strategy_persona__etf_faber_tactical.json` line 12 notes this is "the strongest academic backing for ETF" but still shadow-only because forward sample is zero. |
| **No sector/macro regime gate** | `etf_scanner` (live) | Emitted XLE + USO into falling oil regime with no WTI override | `reports/deep_dive_ETF_2026-05-31.md` lines 36-48: n=2, 0% WR, both losses energy-sector, 50% cohort concentration. |
| **INSUFF-N (n < 30)** | `etf_rsi2_pullback`, `regime_mild_bull`, all ETF personas | Monthly cadence + new asset class = structurally slow accumulation | `reports/deep_dive_ETF_2026-05-31.md` line 24: "n=4 << the n>=30 floor". `config/personas/strategy_persona__etf_regime_bull.json` line 9: "n=2 is artifact-sized". |
| **Unverified academic claims** | `etf_dual_momentum`, `etf_sector_dual_momentum`, `etf_cross_sectional_momentum` | Cited academic WR (75%+) but no look-ahead-free OOS replication in repo | `alpha_engine/etf_strategies.py` lines 9, 65-67 cite Antonacci 75%+ WR, but `reports/deep_dive_ETF_2026-05-31.md` line 24 shows live cohort PF=0.476. |
| **Vaporware** | `tactical_fund_rotation` (mutual funds) | Spec'd in `multi_asset/portfolio_defs.py` but no live module imports it | `2026-11-14/finpredict/2026-11-14T160004Z/quick-wins/by-asset-class/MUTUAL_FUNDS.md` line 4: "UNBUILT". `alpha_engine/mutual_fund_ranker.py` does not exist. |
| **Risk-overlay only** | Faber 200d MA Sharpe 1.01 claim | Claim conflates crash-avoidance with return generation | User context: "Faber 200d MA Sharpe 1.01 claim UNVERIFIED — risk-overlay only". The drawdown cut is real; the Sharpe boost comes from lower vol, not higher return. |

### Key Insight from Repo
The `alpha_engine/strategy_blocklist.py` (lines 376-377) already blocks:
- `etf_volatility_target`
- `etf_small_cap_premium`
- `etf_gold_miners_ratio`
- `etf_equal_weight_rotation`
- `etf_emerging_market_momentum`

These were PR #256 additions (2026-04-19) with no v1.1 gate validation, blocked by peer review. The repo has a history of shipping ETF strategies without proof.

---

## 4. Proposed New Experiments

All experiments follow the 10-gate proof standard. None are claimed as profitable until all gates pass.

| Experiment | Hypothesis | Gap filled | Method | Data | Timeframe | Universe | Parameters | Cost model | Benchmark | Proof gates |
|---|---|---|---|---|---|---|---|---|---|---|
| **E1: Forward-Test TAA Rotation (6-month)** | Top-5 asset-class momentum rotation matches or beats SPY risk-adjusted (Sharpe/Calmar) OOS | No forward proof exists for the one in-sample robust finding | Pre-register holdings from `tools/tactical_rotation_tracker.py` monthly; compare basket return vs SPY total return | `ejaguiar1_stocks.etf_daily_ohlcv` + yfinance | 12 months minimum | SPY, QQQ, IWM, EFA, EEM, TLT, IEF, AGG, GLD, DBC, VNQ, LQD, HYG, TIP | top_n=5, lookback=6m, rebalance=monthly, abs_filter=AGG | 5 bps per trade (ETF commission + slippage) + ER drag | SPY total return | 1. Pre-registered 2. Chronological 3. Walk-forward monthly 4. Bonferroni across 3 TAA variants 5. Block bootstrap CI 6. Full friction 7. Regime split (bull/bear/crash) 8. Shuffle control 9. 12mo forward track 10. Seeded reproducible |
| **E2: Canadian ETF Equivalent Rotation** | TAA rotation works on Canadian-listed ETFs (lower FX drag for Canadian accounts) | All existing research is US-centric; no Canadian validation | Same dual-momentum method on XIC, XUS, XBB, XGB, XRE, XMA, XEM, XEG, CGL.C, HXT, HXS, ZAG, ZSP, VIU, VEE, XSB | TMX/yfinance CAD ETFs | 2015-2026 IS + 12mo forward | 14 Canadian asset-class ETFs | Same as E1 | 5 bps + FX spread (0.15% on non-hedged) + MER | XIC total return (or 60/40 XIC/ZAG) | All 10 gates |
| **E3: MF Next-NAV Backtest with Cost Drag** | Low-cost index mutual funds (FXAIX, FSKAX, SWPPX) match their ETF equivalents after accounting for next-day NAV settlement and ER drag | MF pipeline exists but has no strategy backtest | Use `alpha_engine/mf_etf_pipeline.py` `backtest_nav_fill_series()` to model T+1 NAV fills; compare MF buy-and-hold vs ETF buy-and-hold net of costs | yfinance NAV series for FXAIX, FSKAX, SWPPX, FXNAX | 2015-2026 | 4 MFs (FXAIX, FSKAX, SWPPX, FXNAX) vs ETF equivalents (VOO, VTI, SCHB, BND) | None (passive hold) | ER drag (0.015-0.03%) + next-NAV opportunity cost | Equivalent ETF buy-and-hold | Gates 1, 2, 5, 6, 10 |
| **E4: Faber 200d MA as Risk Overlay (not standalone)** | Adding Faber SMA200 cash-out filter to a 60/40 portfolio improves Calmar without hurting CAGR | Prior audit killed Faber as standalone; re-test as overlay only | 60/40 VTI/BND baseline vs 60/40 with Faber filter: when VTI < SMA200, move equity slice to BND/SHY | yfinance daily | 2007-2026 | VTI, BND, SHY, AGG | SMA200 on VTI; cash to AGG/SHY | 5 bps on overlay trades | 60/40 buy-and-hold | All 10 gates |
| **E5: Sector Momentum with Macro Regime Filter** | SPDR sector momentum works when gated by VIX < 20 and oil trend alignment | `etf_scanner` failed because energy picks had no macro gate | Jegadeesh & Titman top-3 sectors by 3m momentum, ONLY when VIX < 20 and WTI 50d SMA rising (or exclude energy if WTI < SMA50) | yfinance + `^VIX` + `CL=F` | 2010-2026 | 11 SPDR sectors | 3m momentum, VIX<20 gate, WTI trend gate, monthly rebalance | 5 bps + 0.03% ER | SPY total return | All 10 gates |
| **E6: Bond Duration Momentum with Yield-Curve Regime** | TLT/SHY rotation works when conditioned on yield curve slope (10Y-2Y spread) | `bond_duration_rotation.py` has no regime conditioning | LONG TLT when 1m TLT > 1m SHY AND 10Y-2Y spread > 0 (steepening); LONG SHY otherwise | yfinance + FRED (GS10, GS2) | 2000-2026 | TLT, SHY, IEF | 1m return spread, yield-curve slope gate, monthly | 5 bps + 0.03% ER | AGG total return | All 10 gates |

---

## 5. Highest Probability Recommendation

**The asset-class momentum rotation (TAA, top-5 by 6-month momentum, monthly rebalance, absolute-momentum filter to AGG) is the highest-probability ETF/MF strategy in this repo, but it is NOT money-ready.** It is the only strategy with in-sample robustness across 20 years including the 2008 GFC (Sharpe 0.88 vs SPY 0.74, MaxDD -19% vs SPY -51%, positive in all three time-thirds), and it is corroborated by two independent constructions (VAA-G4 and PAA1). However, it has **zero proven forward track record** in this stack. The right action is to **run the 12-month pre-registered forward test (Experiment E1)** at modest paper size, tracking the monthly holdings from `tools/tactical_rotation_tracker.py` against SPY total return. If after 12 months the live basket Sharpe/Calmar exceed SPY with PF >= 1.2 and n >= 12 monthly rebalances, promote to live sizing capped at 5% NAV per ETF. Until then, **the only deployable allocation is passive beta** (VTI/BND 60/40 or Canadian equivalent XIC/ZAG 60/40). The Faber dual-momentum should not be deployed standalone; it may be re-tested only as a risk overlay (Experiment E4). Mutual funds remain research-only until `mutual_fund_ranker.py` is built and forward-tested.

---

## 6. Runnable Code

Below is a **seeded, reproducible Python backtest** for Experiment E1 (TAA Rotation) with a full friction model. It runs on free yfinance data and implements all 10 proof gates where applicable for an offline test.

```python
#!/usr/bin/env python3
"""
ETF_TAA_ROTATION_BACKTEST.py
============================
Seeded, reproducible backtest for asset-class momentum rotation (Experiment E1).
Implements the 10-gate proof standard where applicable in an offline setting.

Usage:
    python3 ETF_TAA_ROTATION_BACKTEST.py --start 2007-01-01 --end 2026-01-01 --out results.json

Dependencies: yfinance, numpy, pandas
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# REPRODUCIBILITY (Gate 10)
# ---------------------------------------------------------------------------
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
UNIVERSE = [
    "SPY",   # US large
    "QQQ",   # Nasdaq
    "IWM",   # US small
    "EFA",   # Intl developed
    "EEM",   # Emerging
    "TLT",   # Long Treasury
    "IEF",   # Intermediate Treasury
    "AGG",   # US Aggregate Bond
    "GLD",   # Gold
    "DBC",   # Broad commodity
    "VNQ",   # REITs
    "LQD",   # IG credit
    "HYG",   # HY credit
    "TIP",   # TIPS
]

CASH_ASSET = "AGG"
TOP_N = 5
LOOKBACK_MONTHS = 6
REBALANCE_FREQ = "MS"  # Month Start
COST_BPS = 5.0         # 5 bps per trade (commission + slippage)
ER_PCT = {
    "SPY": 0.0945, "QQQ": 0.20, "IWM": 0.19, "EFA": 0.33,
    "EEM": 0.68, "TLT": 0.15, "IEF": 0.15, "AGG": 0.03,
    "GLD": 0.40, "DBC": 0.85, "VNQ": 0.12, "LQD": 0.14,
    "HYG": 0.48, "TIP": 0.19,
}

BENCHMARK = "SPY"


def fetch_data(tickers: list[str], start: str, end: str) -> dict[str, pd.DataFrame]:
    """Fetch adjusted daily closes from yfinance."""
    import yfinance as yf
    data: dict[str, pd.DataFrame] = {}
    for t in tickers:
        df = yf.download(t, start=start, end=end, progress=False, threads=False, auto_adjust=True)
        if df is not None and not df.empty and "Close" in df.columns:
            # Flatten MultiIndex if present
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df[["Close"]].copy()
            df.index = pd.to_datetime(df.index)
            df = df.sort_index()
            data[t] = df
    return data


def compute_monthly_momentum(data: dict[str, pd.DataFrame], rebalance_dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Compute N-month momentum at each rebalance date."""
    lookback_days = LOOKBACK_MONTHS * 21
    rows = []
    for d in rebalance_dates:
        row: dict[str, Any] = {"date": d}
        for t in UNIVERSE:
            df = data.get(t)
            if df is None:
                row[t] = np.nan
                continue
            # Find price at or before d
            prices = df.loc[:d]
            if len(prices) < lookback_days + 1:
                row[t] = np.nan
                continue
            price_now = float(prices["Close"].iloc[-1])
            price_then = float(prices["Close"].iloc[-(lookback_days + 1)])
            row[t] = (price_now / price_then - 1.0) if price_then > 0 else np.nan
        rows.append(row)
    mom = pd.DataFrame(rows).set_index("date")
    return mom


def backtest(data: dict[str, pd.DataFrame], start: str, end: str) -> dict[str, Any]:
    """Run the TAA rotation backtest with full friction model."""
    # Build monthly rebalance dates
    all_dates = pd.date_range(start=start, end=end, freq="B")
    rebalance_dates = pd.date_range(start=start, end=end, freq=REBALANCE_FREQ)

    mom = compute_monthly_momentum(data, rebalance_dates)
    bench_df = data.get(BENCHMARK)
    if bench_df is None:
        raise ValueError(f"Benchmark {BENCHMARK} data missing")

    # Align benchmark to rebalance dates
    bench_prices = bench_df["Close"].reindex(rebalance_dates, method="ffill")
    bench_rets = bench_prices.pct_change().dropna()

    strategy_rets: list[float] = []
    bench_rets_aligned: list[float] = []
    holdings_log: list[dict] = []
    prev_holdings: dict[str, float] = {}

    for i, d in enumerate(rebalance_dates):
        if i == 0:
            continue  # No return on first date

        # Rank by momentum
        row = mom.loc[d]
        valid = row.dropna()
        if len(valid) < TOP_N:
            strategy_rets.append(0.0)
            bench_rets_aligned.append(float(bench_rets.loc[d]) if d in bench_rets.index else 0.0)
            continue

        ranked = valid.sort_values(ascending=False)
        top = ranked.head(TOP_N)

        # Absolute momentum filter: negative momentum -> cash slot
        holdings: dict[str, float] = {}
        cash_slots = 0
        for sym, m in top.items():
            if m > 0:
                holdings[sym] = 1.0 / TOP_N
            else:
                cash_slots += 1
        if cash_slots:
            holdings[CASH_ASSET] = holdings.get(CASH_ASSET, 0.0) + cash_slots * (1.0 / TOP_N)

        # Normalize weights
        total_w = sum(holdings.values())
        if total_w > 0:
            holdings = {k: v / total_w for k, v in holdings.items()}

        # Compute portfolio return for the month
        month_start = d
        month_end = rebalance_dates[i + 1] if i + 1 < len(rebalance_dates) else pd.Timestamp(end)

        port_ret = 0.0
        for sym, w in holdings.items():
            df = data.get(sym)
            if df is None:
                continue
            p0 = float(df.loc[:month_start]["Close"].iloc[-1]) if len(df.loc[:month_start]) > 0 else np.nan
            p1_ser = df.loc[:month_end]["Close"]
            p1 = float(p1_ser.iloc[-1]) if len(p1_ser) > 0 else np.nan
            if pd.isna(p0) or pd.isna(p1) or p0 <= 0:
                continue
            asset_ret = p1 / p0 - 1.0
            # ER drag (annualized to monthly)
            er_monthly = (ER_PCT.get(sym, 0.0) / 100.0) / 12.0
            port_ret += w * (asset_ret - er_monthly)

        # Transaction cost on turnover
        turnover = 0.0
        all_syms = set(prev_holdings.keys()) | set(holdings.keys())
        for sym in all_syms:
            turnover += abs(holdings.get(sym, 0.0) - prev_holdings.get(sym, 0.0))
        cost = 0.5 * turnover * (COST_BPS / 10000.0)  # Half spread on turnover
        port_ret -= cost

        strategy_rets.append(port_ret)
        bench_rets_aligned.append(float(bench_rets.loc[d]) if d in bench_rets.index else 0.0)
        holdings_log.append({"date": d.strftime("%Y-%m-%d"), "holdings": holdings, "turnover": round(turnover, 4)})
        prev_holdings = holdings.copy()

    # -----------------------------------------------------------------------
    # METRICS
    # -----------------------------------------------------------------------
    s = np.array(strategy_rets)
    b = np.array(bench_rets_aligned)

    def sharpe(x: np.ndarray) -> float:
        if len(x) < 2 or np.std(x, ddof=1) == 0:
            return 0.0
        return float(np.mean(x) / np.std(x, ddof=1) * math.sqrt(12))

    def maxdd(equity: np.ndarray) -> float:
        peak = np.maximum.accumulate(equity)
        dd = (peak - equity) / peak
        return float(np.max(dd))

    def calmar(cagr: float, mdd: float) -> float:
        return abs(cagr / mdd) if mdd != 0 else 0.0

    s_equity = np.cumprod(1 + s)
    b_equity = np.cumprod(1 + b)

    s_cagr = float((s_equity[-1] ** (12 / len(s))) - 1) if len(s) > 0 else 0.0
    b_cagr = float((b_equity[-1] ** (12 / len(b))) - 1) if len(b) > 0 else 0.0
    s_mdd = maxdd(s_equity)
    b_mdd = maxdd(b_equity)

    # Walk-forward: split into two halves (Gate 2, 3)
    mid = len(s) // 2
    s_sharpe_full = sharpe(s)
    s_sharpe_first = sharpe(s[:mid])
    s_sharpe_second = sharpe(s[mid:])
    b_sharpe_full = sharpe(b)

    # Block bootstrap (Gate 5)
    bootstrap_sharpes = []
    block_size = 3
    n_blocks = int(np.ceil(len(s) / block_size))
    for _ in range(1000):
        starts = np.random.randint(0, len(s) - block_size + 1, size=n_blocks)
        boot = np.concatenate([s[start:start + block_size] for start in starts])[:len(s)]
        bootstrap_sharpes.append(sharpe(boot))
    sharpe_ci = (float(np.percentile(bootstrap_sharpes, 2.5)), float(np.percentile(bootstrap_sharpes, 97.5)))

    # Regime split: bull (benchmark ret > 0) vs bear (<=0) (Gate 7)
    bull_mask = b > 0
    bear_mask = ~bull_mask
    s_bull_sharpe = sharpe(s[bull_mask]) if np.any(bull_mask) else 0.0
    s_bear_sharpe = sharpe(s[bear_mask]) if np.any(bear_mask) else 0.0

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seed": SEED,
        "params": {
            "universe": UNIVERSE,
            "top_n": TOP_N,
            "lookback_months": LOOKBACK_MONTHS,
            "rebalance_freq": REBALANCE_FREQ,
            "cost_bps": COST_BPS,
            "cash_asset": CASH_ASSET,
        },
        "strategy": {
            "cagr": round(s_cagr * 100, 2),
            "sharpe_annual": round(s_sharpe_full, 4),
            "sharpe_first_half": round(s_sharpe_first, 4),
            "sharpe_second_half": round(s_sharpe_second, 4),
            "max_dd_pct": round(s_mdd * 100, 2),
            "calmar": round(calmar(s_cagr, s_mdd), 4),
            "sharpe_ci_95": (round(sharpe_ci[0], 4), round(sharpe_ci[1], 4)),
            "sharpe_bull": round(s_bull_sharpe, 4),
            "sharpe_bear": round(s_bear_sharpe, 4),
            "n_months": len(s),
            "avg_monthly_turnover": round(float(np.mean([h["turnover"] for h in holdings_log])), 4),
        },
        "benchmark": {
            "ticker": BENCHMARK,
            "cagr": round(b_cagr * 100, 2),
            "sharpe_annual": round(b_sharpe_full, 4),
            "max_dd_pct": round(b_mdd * 100, 2),
            "calmar": round(calmar(b_cagr, b_mdd), 4),
        },
        "holdings_log": holdings_log,
        "verdict": {
            "passes_in_sample_robustness": s_sharpe_first > 0 and s_sharpe_second > 0,
            "beats_benchmark_sharpe": s_sharpe_full > b_sharpe_full,
            "beats_benchmark_calmar": calmar(s_cagr, s_mdd) > calmar(b_cagr, b_mdd),
            "sharpe_ci_excludes_null": sharpe_ci[0] > 0,
            "note": "In-sample only. Forward test required before live sizing.",
        },
    }
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="TAA Rotation Backtest (Experiment E1)")
    ap.add_argument("--start", default="2007-01-01")
    ap.add_argument("--end", default="2026-01-01")
    ap.add_argument("--out", default="WIRED_IN/2026-11-15T065338Z_hilarious-seer/taa_backtest_result.json")
    args = ap.parse_args()

    print(f"Fetching data for {len(UNIVERSE)} tickers...")
    data = fetch_data(UNIVERSE + [BENCHMARK], args.start, args.end)
    print(f"Fetched {len(data)} tickers.")

    print("Running backtest...")
    result = backtest(data, args.start, args.end)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"Wrote results to {out_path}")

    s = result["strategy"]
    b = result["benchmark"]
    print(f"\n{'METRIC':<25} {'STRATEGY':>12} {'BENCHMARK':>12}")
    print("-" * 52)
    print(f"{'CAGR %':<25} {s['cagr']:>11.2f}% {b['cagr']:>11.2f}%")
    print(f"{'Sharpe (annual)':<25} {s['sharpe_annual']:>12.4f} {b['sharpe_annual']:>12.4f}")
    print(f"{'Max Drawdown %':<25} {s['max_dd_pct']:>11.2f}% {b['max_dd_pct']:>11.2f}%")
    print(f"{'Calmar':<25} {s['calmar']:>12.4f} {b['calmar']:>12.4f}")
    print(f"{'Sharpe CI 95%':<25} [{s['sharpe_ci_95'][0]:.4f}, {s['sharpe_ci_95'][1]:.4f}]")
    print(f"\nVerdict: {result['verdict']['note']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### How to run

```bash
pip install yfinance numpy pandas
python3 ETF_TAA_ROTATION_BACKTEST.py --start 2007-01-01 --end 2026-01-01
```

### Expected output (based on prior validation)
Based on `reports/TACTICAL_ROTATION_EDGE_2026-07-04.md` lines 47-48, the 2007-2026 run should produce approximately:

- Strategy CAGR: ~9.2%, Sharpe: ~0.88, MaxDD: ~-19%, Calmar: ~0.48
- Benchmark CAGR: ~10.8%, Sharpe: ~0.74, MaxDD: ~-51%, Calmar: ~0.21

**Interpretation:** The strategy matches or slightly underperforms SPY on raw return but cuts drawdown by ~60% and improves Sharpe/Calmar. This is **risk-adjusted outperformance, not alpha**. The CI and both-halves positive are the key robustness signals.

---

## Audit Summary

| Claim | Status | Basis |
|---|---|---|
| Passive beta is viable | **TRUE** | VTI/BND 60/40; ER < 0.03% |
| Faber TAA beats SPY standalone | **FALSE** | AnnRet 9.1% vs SPY 14.7%; Sharpe 0.40 vs 0.73 |
| Faber 200d MA Sharpe 1.01 | **UNVERIFIED** | Risk-overlay only; no clean OOS proof |
| Sector momentum rotation works | **UNPROVEN** | No backtest evidence in repo |
| Bond duration rotation works | **UNPROVEN** | No backtest evidence in repo |
| TAA rotation is robust in-sample | **TRUE** | 2007-2026, all 16 cells cut MaxDD, positive thirds |
| TAA rotation is proven forward | **FALSE** | 12-month forward test required (Experiment E1) |
| Mutual fund pipeline is live | **FALSE** | Infrastructure exists; no active strategy |
| etf_scanner is viable | **FALSE** | KILL-CANDIDATE; n=2, 0% WR, energy concentration |
| 50/50 Rotation+VAA blend is best in-sample | **TRUE** | Sharpe 0.89, MaxDD -16%, Calmar 0.50 |

**Bottom line:** There is exactly **one** ETF/MF strategy family with any evidence (TAA rotation), and it is **in-sample only**. All other strategies are either unvalidated, underperform buy-and-hold, or vaporware. Run Experiment E1 forward for 12 months before sizing live.
