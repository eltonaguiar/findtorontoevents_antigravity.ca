# Deep Analysis of Trading System: KILOCODE_OPENRMIMO_MAY262026.MD Validation

## Executive Summary
This analysis validates the claims in `KILOCODE_OPENRMIMO_MAY262026.MD` against current system data.
**Key Finding:** Significant discrepancy exists between the report's claimed metrics and the primary `alpha_engine/data/closed_picks.json` data source.
The report appears to reference aggregated or historical data from other sources (e.g., `battleground`, `mercury2`), while the main engine's current closed picks show minimal EQUITY activity with poor performance.

## 1. Asset Class Edge Report (`tools/asset_class_edge_report.py`)

### 1.1. Primary Data Source (`alpha_engine/data/closed_picks.json`)
**Command:** `python tools/asset_class_edge_report.py`
**Output:**
```
Source: `closed_picks.json` — 3 resolved picks.
Thresholds: best-edge n>=20, consistent n>=30, low-sample n<20.

## 1. Overall performance per asset class

| Asset class | n | WR | PF | total pnl% |
|---|---|---|---|---|
| EQUITY | 3 | 0.0% | 0.00 | -449.9% |

## EQUITY — strategy breakdown
```
**Analysis:**
- Only 3 resolved picks found in the primary data source.
- All picks are EQUITY (`stocks_rsi2_pullback`).
- Performance is catastrophic: 0% WR, 0.00 PF, -449.9% total PnL.
- **Report Claim vs. Reality:** The report claims EQUITY PF 1.55 (T2 candidate). The current primary data shows PF 0.00.

### 1.2. Alternative Data Source (`battleground/data/closed_picks.json`)
**Command:** `python tools/asset_class_edge_report.py --picks /home/eaguiar2015/findtorontoevents_antigravity.ca/battleground/data/closed_picks.json`
**Output:**
```
Source: `closed_picks.json` — 123 resolved picks.
## 1. Overall performance per asset class
| Asset class | n | WR | PF | total pnl% |
|---|---|---|---|---|
| UNKNOWN | 123 | 56.9% | 1.77 | 2810.3% |

## UNKNOWN — strategy breakdown
- **Best edge:** `crypto_liquidity_wick_reversal_v1` — PF 1.50, WR 58.1%, n=43
- **Most consistent:** `crypto_liquidity_wick_reversal_v1` — WR 58.1%, PF 1.50, n=43
- **High-edge / low-sample (investigate — broke or regime-specific):**
  - `drawdown_recovery_rsi_sol` — PF 8.57, WR 66.7%, n=6
  - `drawdown_recovery_rsi_eth` — PF 5.98, WR 64.3%, n=14
```
**Analysis:**
- This source shows CRYPTO-like activity (symbols like ETHUSDT, SOLUSDT).
- PF 1.77 aligns more closely with report claims (CRYPTO PF 1.30, EQUITY PF 1.55) than the primary source.
- The "UNKNOWN" asset class is likely CRYPTO based on symbol patterns.

## 2. Prediction Quality Tracker (`alpha_engine/prediction_quality_tracker.py`)
**File Path:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/prediction_quality_tracker.py`
**History Path:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/data/prediction_quality_history.json`

### 2.1. Recent Metrics Snippet
The history file contains hourly metrics. Recent entry (lines 1-46):
```json
{
  "timestamp": "2026-04-19T17:58:44Z",
  "directional_accuracy": 0.326,
  "cumulative_pnl_7d": -545.9853,
  "sharpe_daily": -5.3024,
  "profit_factor_7d": 0.2948,
  "win_rate_7d": 0.5714,
  "total_active": 116,
  "total_closed": 5264
}
```
**Analysis:**
- Recent metrics show negative PnL and Sharpe, indicating poor recent performance.
- The history tracks 14 quality dimensions but does not explicitly compute DSR.

## 3. Top 3 'High-Edge/Low-Sample' Strategies
**Criteria:** PF >= 1.5, WR >= 55%, n < 20 (per `asset_class_edge_report.py` logic).

The report `KILOCODE_OPENRMIMO_MAY262026.MD` mentions "CRYPTO shows promise but needs larger sample sizes" and lists generic categories, but **does not explicitly name specific high-edge/low-sample strategies**.

Analysis of `battleground/data/closed_picks.json` identified the following strategies meeting the criteria:

1.  **`drawdown_recovery_rsi_sol`**
    - PF: 8.57
    - WR: 66.7%
    - n: 6
    - Path: `battleground/data/closed_picks.json`

2.  **`drawdown_recovery_rsi_eth`**
    - PF: 5.98
    - WR: 64.3%
    - n: 14
    - Path: `battleground/data/closed_picks.json`

**Note:** `drawdown_recovery_rsi_xrp` (PF 3.34, WR 75%) was excluded by the script's `n >= 5` floor filter (n=4).

## 4. DSR Calculations (`statistical_validation_framework.py`)
**File Path:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/statistical_validation_framework.py`

**Findings:**
- The provided snippet (lines 1-200) does not contain explicit DSR (Deflated Sharpe Ratio) computation functions.
- DSR implementation is found in a separate module: `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/deflated_sharpe.py`.
- The `deflated_sharpe.py` module implements the Bailey & Lopez de Prado (2014) DSR methodology for filtering false-positive strategies.
- The `prediction_quality_tracker.py` computes Sharpe and Sortino ratios but does not call DSR.

## 5. Accidentally-Banned Strategies Check
**Tool:** `tools/asset_class_edge_report.py` (logic check for blocked strategies with good performance).

**Analysis:**
- The script checks `strategy_blocklist.py` for blocked strategies.
- **Primary Source (`alpha_engine/data/closed_picks.json`):** No strategies flagged as "accidentally-banned" (only 3 picks, none blocked).
- **Battleground Source (`battleground/data/closed_picks.json`):** No strategies flagged as "accidentally-banned".
- **Strategy Blocklist Review:** `drawdown_recovery_rsi_*` strategies are not found in `_RETIRED_STRATEGIES` or `_PAPER_ONLY_STRATEGIES` in `strategy_blocklist.py` (lines 100-199).

**Conclusion:** No "accidentally-banned" strategies identified in the analyzed data sources.

## 6. Verification of Report Claims
| Report Claim | Current System Data (Primary) | Current System Data (Battleground) | Verdict |
|---|---|---|---|---|
| EQUITY PF 1.55 | PF 0.00 (n=3) | N/A (Battleground shows UNKNOWN/CRYPTO) | **Discrepancy** |
| CRYPTO PF 1.30 | N/A (No CRYPTO in primary) | PF 1.77 (UNKNOWN/CRYPTO) | **Partial Alignment** |
| COMMODITY DSR=1.0 | Not found in closed_picks.json | Not found in closed_picks.json | **Data Missing** |
| High-edge/low-sample strategies | None (n<5 or PF<1.5) | 2 strategies found (`drawdown_recovery_rsi_sol`, `drawdown_recovery_rsi_eth`) | **Found in alternate source** |

## 7. Recommendations
1.  **Data Source Alignment:** Investigate why `alpha_engine/data/closed_picks.json` contains minimal data compared to `battleground` and `mercury2`. The report likely aggregates from multiple sources.
2.  **Strategy Promotion:** Investigate `drawdown_recovery_rsi_sol` and `drawdown_recovery_rsi_eth` (high-edge, low-sample) for potential promotion or further validation.
3.  **DSR Integration:** Ensure DSR calculations from `deflated_sharpe.py` are integrated into the main validation pipeline if not already present.
