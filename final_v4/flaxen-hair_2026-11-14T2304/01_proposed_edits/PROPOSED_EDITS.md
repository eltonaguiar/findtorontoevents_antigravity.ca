# PROPOSED EDITS — Financial Prediction Plan

**Worktree:** flaxen-hair_2026-11-14T2304 | **Date:** 2026-11-14T23:04Z

This document lists all proposed code edits, organized by file, with specific line numbers and rationale. Edits are organized by priority (P0 = must do first, P1 = next, P2 = optional).

---

## P0 — Measurement & Data Integrity Fixes (Must Do First)

These fixes address the most critical issues: PnL calculation errors, blank fields, stale data, and promotion gates that don't actually gate.

### Edit 1: alpha_engine/money_ready_verdict.py — Enable Promotion Gates

**Lines:** ~179-194 (per evidence index)

**Current:** `MONEY_READY_FDR_GATE` and `MONEY_READY_SINGLE_SOURCE_GATE` default to `"0"` (OFF)

**Proposed:** Change both defaults to `"1"` (ON)

```python
MONEY_READY_FDR_GATE = os.environ.get("MONEY_READY_FDR_GATE", "1")
MONEY_READY_SINGLE_SOURCE_GATE = os.environ.get("MONEY_READY_SINGLE_SOURCE_GATE", "1")
```

**Rationale:** Currently both critical promotion gates are disabled, meaning unvalidated strategies can be promoted to live trading.

### Edit 2: alpha_engine/per_class_cost_gate.py — Close Fail-Open Paths

**Lines:** ~29, 152-179

**Current:** Missing/stale/unknown/thin evidence passes (fail-open)

**Proposed:** Change fail-open to fail-closed. Missing/stale/unknown evidence must return `INSUFFICIENT_DATA` and block promotion.

```python
# Replace fail-open paths with:
return DecisionResult(
    decision=Decision.INSUFFICIENT_DATA,
    reason="missing/stale/unknown cost evidence — fail-closed",
    gate_state=GateState.BLOCKED
)
```

**Rationale:** Current fail-open behavior means unverified strategies can pass the cost gate.

### Edit 3: audit_trail/dashboard_generator.py — Stop Suppressing After-Cost Errors

**Lines:** ~7772-7789

**Current:** After-cost stamping errors are suppressed silently

**Proposed:** Log errors explicitly and fail the gate instead of suppressing

```python
# Replace suppression with explicit error propagation:
try:
    stamp_after_cost(pick)
except Exception as e:
    logger.error(f"After-cost stamping failed for {pick.get('id')}: {e}")
    raise AfterCostStampError(f"Cannot stamp after-cost PnL for {pick.get('id')}: {e}")
```

**Rationale:** Suppressed errors mean dashboards display incorrect PnL values without warning.

### Edit 4: alpha_engine/risk_controls.py — Add Weekly/Monthly Loss Limits

**Lines:** ~39-50 (thresholds), ~647 (run_all_risk_controls return)

**Current:** Only daily loss limits exist (-2%/-3%)

**Proposed:** Add weekly (-5%) and monthly (-10%) loss limits with explicit circuit breakers

```python
WEEKLY_BLOCK_PCT = -5.0
MONTHLY_BLOCK_PCT = -10.0
QUARTERLY_BLOCK_PCT = -15.0
```

And add to `run_all_risk_controls()` return:
```python
{
    "daily_loss_limit": daily_result,
    "weekly_loss_limit": weekly_result,
    "monthly_loss_limit": monthly_result,
}
```

**Rationale:** Without weekly/monthly limits, a strategy can lose 10% in a week and no gate triggers.

---

## P1 — QA Validation Infrastructure

### Edit 5: alpha_engine/risk_qa_validator.py — CREATE NEW FILE

**Purpose:** QA checks for PnL=0% validation, blank field flags, open/recently closed items

**Functions to implement:**

```python
def validate_pnl_zero(picks: list[dict]) -> list[dict]:
    """Flag picks with PnL=0 but non-trivial price movement."""
    flags = []
    for p in picks:
        pnl = p.get("pnl_pct")
        entry = p.get("entry_price")
        exit_p = p.get("exit_price") or p.get("current_price")
        status = p.get("status", "").upper()
        if pnl is not None and abs(float(pnl)) < 0.0001:
            if entry and exit_p and abs(float(entry) - float(exit_p)) > 0.01:
                if status in ("WON", "LOST", "TP_HIT", "SL_HIT", "CLOSED", "ACTIVE"):
                    flags.append({
                        "id": p.get("id"),
                        "symbol": p.get("symbol"),
                        "issue": "PnL=0% with price movement — resolver/data bug",
                        "severity": "CRITICAL",
                        "correct_pnl": round((float(exit_p) / float(entry) - 1.0) * (1 if p.get("direction") == "LONG" else -1), 6),
                    })
    return flags

def validate_blank_fields(picks: list[dict]) -> list[dict]:
    """Flag picks with missing required fields, especially open/recently closed items."""
    required_open = ["symbol", "entry_price", "stop_loss", "take_profit", "strategy", "asset_class", "direction", "entry_time", "status"]
    required_closed = required_open + ["exit_price", "exit_date", "closed_at", "pnl_pct"]
    flags = []
    for p in picks:
        status = p.get("status", "").upper()
        if status in ("OPEN", "ACTIVE", "PENDING"):
            missing = [f for f in required_open if p.get(f) is None or p.get(f) == ""]
        elif status in ("CLOSED", "WON", "LOST", "TP_HIT", "SL_HIT"):
            missing = [f for f in required_closed if p.get(f) is None or p.get(f) == ""]
        else:
            missing = [f for f in required_open if p.get(f) is None or p.get(f) == ""]
        if missing:
            severity = "CRITICAL" if len(missing) >= 3 else ("HIGH" if len(missing) >= 2 else "MEDIUM")
            flags.append({
                "id": p.get("id"),
                "symbol": p.get("symbol"),
                "status": status,
                "issue": f"Blank fields: {', '.join(missing)}",
                "severity": severity,
            })
    return flags

def validate_open_items(picks: list[dict], max_open_hours: int = 72) -> list[dict]:
    """Flag open picks that have been open too long (stale positions)."""
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    flags = []
    for p in picks:
        if p.get("status", "").upper() in ("OPEN", "ACTIVE", "PENDING"):
            created = p.get("entry_time") or p.get("timestamp") or p.get("created_at")
            if created:
                age = now - datetime.fromisoformat(str(created).replace("Z", "+00:00"))
                if age > timedelta(hours=max_open_hours):
                    severity = "CRITICAL" if age > timedelta(hours=168) else "HIGH" if age > timedelta(hours=72) else "MEDIUM"
                    flags.append({
                        "id": p.get("id"),
                        "symbol": p.get("symbol"),
                        "issue": f"Open for {age.total_seconds()/3600:.1f} hours (>{max_open_hours}h limit)",
                        "severity": severity,
                        "age_hours": round(age.total_seconds() / 3600, 1),
                    })
    return flags

def validate_recently_closed(picks: list[dict], max_hours: int = 24) -> list[dict]:
    """Flag recently closed picks missing exit data."""
    flags = []
    for p in picks:
        if p.get("status", "").upper() in ("CLOSED", "WON", "LOST", "TP_HIT", "SL_HIT"):
            missing = [f for f in ["exit_price", "exit_date", "closed_at", "pnl_pct"] if p.get(f) is None or p.get(f) == ""]
            if missing:
                flags.append({
                    "id": p.get("id"),
                    "symbol": p.get("symbol"),
                    "issue": f"Recently closed but missing: {', '.join(missing)}",
                    "severity": "HIGH",
                })
    return flags

def run_all_qa_checks(picks: list[dict]) -> dict:
    """Run all QA checks and return aggregated results."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_picks": len(picks),
        "pnl_zero_flags": validate_pnl_zero(picks),
        "blank_field_flags": validate_blank_fields(picks),
        "open_item_flags": validate_open_items(picks),
        "recently_closed_flags": validate_recently_closed(picks),
        "total_flags": 0,  # computed
        "critical_flags": 0,  # computed
        "passes_qa": True,  # computed
    }
```

### Edit 6: production_scanner.py — Wire QA Checks Into Pick Generation

**Location:** Before pick emission in production_scanner.py

**Proposed:** Add QA validation gate before any pick is emitted:

```python
from alpha_engine.risk_qa_validator import run_all_qa_checks

# Before emitting picks:
qa_result = run_all_qa_checks(candidate_picks)
if not qa_result["passes_qa"]:
    logger.error(f"QA failed: {qa_result['total_flags']} flags, {qa_result['critical_flags']} critical")
    # Block emission or quarantine picks with critical flags
    candidate_picks = [p for p in candidate_picks if p.get("id") not in 
                       {f["id"] for f in qa_result["critical_flags"] if "id" in f}]
```

**Rationale:** Prevents picks with blank fields, PnL=0% bugs, or stale open positions from reaching the dashboard.

---

## P2 — Mutual Fund + ETF Infrastructure

### Edit 7: alpha_engine/asset_class.py — Register MUTUAL_FUND Asset Class

**Add:**
```python
MUTUAL_FUND_SYMBOLS = frozenset({
    "VFIAX", "VTSAX", "VBTLX", "VTIAX", "VGSLX", "FXAIX", "FBALX", 
    "VWINX", "VFSTX", "PRBLX", "PIMIX", "VWELX", "VFORX", "VSMGX", 
    "VASGX", "VLCSX", "VEIRX", "VEXPX", "VIMAX", "VMAX", "VEXAX"
})

CAT_MAP["mutual_fund"] = "MUTUAL_FUND"
LOWER_TO_UPPER["mutual_fund"] = "MUTUAL_FUND"

def is_mutual_fund(pick: dict) -> bool:
    return pick.get("asset_class") == "MUTUAL_FUND" or pick.get("category") == "mutual_fund"

MUTUAL_FUND_STRATEGY_HINTS = ("mutual_fund", "fund_", "index_fund", "vanguard", "fidelity")
```

### Edit 8: ml_gatekeeper/gatekeeper.py — Add MUTUAL_FUND Class ID

**Line 73:** Change:
```python
ASSET_CLASS_MAP = {"CRYPTO": 0, "FOREX": 1, "EQUITY": 2, "COMMODITY": 3, "ETF": 4, "BOND": 5, "FUTURES": 6}
```
To:
```python
ASSET_CLASS_MAP = {"CRYPTO": 0, "FOREX": 1, "EQUITY": 2, "COMMODITY": 3, "ETF": 4, "BOND": 5, "FUTURES": 6, "MUTUAL_FUND": 7}
```

### Edit 9: audit_trail/dashboard_generator.py — Add Mutual Fund Dashboard Bucket

**Lines:** ~6763, ~6128, ~14201

Add `"mutual_fund"` to `_PER_ASSET_CLASSES`, `_CANONICAL`, `_AC_TF_GRID_ASSET_CLASSES`

### Edit 10: alpha_engine/risk_thresholds.json — CREATE NEW FILE

**Purpose:** Centralized risk threshold configuration

```json
{
  "position_sizing": {
    "default_risk_pct": 0.01,
    "max_risk_per_trade": 0.02,
    "max_single_position": 0.05,
    "max_crypto_allocation": 0.20,
    "kelly_fraction": 0.25,
    "min_trades_for_kelly": 30
  },
  "stop_loss": {
    "method": "atr_based",
    "sl_atr_mult": 1.0,
    "tp_atr_mult": 1.5,
    "min_rr_ratio": 1.5,
    "max_stop_distance_pct": 0.10,
    "trailing_stop_atr": 1.5,
    "regime_multipliers": {"BULLISH": 0.9, "NEUTRAL": 1.0, "BEARISH": 1.2, "CRISIS": 1.5}
  },
  "drawdown_controls": {
    "daily_block_pct": -2.0,
    "daily_warning_pct": -1.0,
    "weekly_block_pct": -5.0,
    "monthly_block_pct": -10.0,
    "quarterly_block_pct": -15.0,
    "max_portfolio_dd": -20.0,
    "consecutive_loss_breaker": 5
  },
  "correlation_limits": {
    "max_positions_per_group": 3,
    "max_pair_correlation": 0.70,
    "max_directional_exposure": 0.20,
    "max_portfolio_market_correlation": 0.80
  },
  "risk_adjusted_thresholds": {
    "min_sharpe": 0.5,
    "min_sortino": 1.0,
    "min_calmar": 0.5,
    "min_psr": 0.80,
    "max_var_95": 0.02,
    "max_ulcer_index": 0.05
  },
  "expectancy": {
    "min_win_rate": 0.40,
    "min_rr_ratio": 1.5,
    "min_expectancy_pct": 0.005,
    "min_profit_factor": 1.3
  },
  "mutual_fund": {
    "max_expense_ratio": 0.002,
    "min_aum": 1000000000,
    "max_turnover": 0.20,
    "max_tracking_error": 0.0025,
    "min_track_record_years": 10,
    "min_investment": 1000,
    "max_nav_staleness_hours": 24
  },
  "etf": {
    "max_expense_ratio": 0.001,
    "min_aum": 500000000,
    "min_adv_usd": 10000000,
    "max_bid_ask_spread": 0.0005,
    "max_tracking_error": 0.002,
    "min_track_record_years": 5
  }
}
```

---

## P3 — Mutual Fund & ETF Solid Pick Infrastructure

### Edit 11: alpha_engine/mutual_fund_ranker.py — CREATE NEW FILE

Implement mutual fund ranker implementing the solid-pick criteria:

```python
MUTUAL_FUND_CRITERIA = {
    "max_expense_ratio": 0.002,      # 0.20%
    "max_load_fee": 0.0,             # No load
    "max_12b1_fee": 0.0,             # No 12b-1
    "max_min_investment": 1000,      # $1,000
    "min_aum": 1_000_000_000,        # $1B
    "max_turnover": 0.20,            # 20%
    "max_tracking_error": 0.0025,    # 0.25%
    "min_track_record_years": 10,    # 10 years
}

def rank_mutual_funds(funds: list[dict]) -> list[dict]:
    """Rank mutual funds by solid-pick criteria. Returns only funds passing all gates."""
    qualified = []
    for f in funds:
        if not _passes_all_criteria(f):
            continue
        score = _compute_score(f)
        qualified.append({**f, "rank_score": score, "qualified": True})
    return sorted(qualified, key=lambda x: x["rank_score"], reverse=True)

def _passes_all_criteria(f: dict) -> bool:
    return (
        f.get("expense_ratio", 999) <= MUTUAL_FUND_CRITERIA["max_expense_ratio"] and
        f.get("load_fee", 999) <= MUTUAL_FUND_CRITERIA["max_load_fee"] and
        f.get("b12b_fee", 999) <= MUTUAL_FUND_CRITERIA["max_12b1_fee"] and
        f.get("min_investment", 999999) <= MUTUAL_FUND_CRITERIA["max_min_investment"] and
        f.get("aum", 0) >= MUTUAL_FUND_CRITERIA["min_aum"] and
        f.get("turnover", 999) <= MUTUAL_FUND_CRITERIA["max_turnover"] and
        f.get("tracking_error", 999) <= MUTUAL_FUND_CRITERIA["max_tracking_error"] and
        f.get("track_record_years", 0) >= MUTUAL_FUND_CRITERIA["min_track_record_years"]
    )
```

### Edit 12: tools/mf_traits_walkforward_runner.py — CREATE NEW FILE

Mutual fund walkforward runner with monthly NAV rebalancing, next-NAV execution semantics.

### Edit 13: tools/mf_walkforward_backtest.py — CREATE NEW FILE

MF walkforward backtest with fees, commissions, whole-share rules, next-NAV execution.

### Edit 14: tools/mf_trait_features.py — CREATE NEW FILE

MF trait feature computation (expense ratio, AUM, turnover, tracking error, category ranking).

### Edit 15: audit_dashboard/data/mf_cache_manifest.json — CREATE NEW FILE

SHA-256 provenance manifest mirroring `research/profitability/data/manifest.json`.

---

## Summary of All Proposed Edits

| Priority | # | File | Action | Lines |
|----------|---|------|--------|-------|
| P0 | 1 | alpha_engine/money_ready_verdict.py | Enable promotion gates | ~179-194 |
| P0 | 2 | alpha_engine/per_class_cost_gate.py | Close fail-open paths | ~29, 152-179 |
| P0 | 3 | audit_trail/dashboard_generator.py | Stop suppressing after-cost errors | ~7772-7789 |
| P0 | 4 | alpha_engine/risk_controls.py | Add weekly/monthly loss limits | ~39-50, ~647 |
| P1 | 5 | alpha_engine/risk_qa_validator.py | CREATE — QA validation functions | New file |
| P1 | 6 | production_scanner.py | Wire QA checks into pick generation | — |
| P2 | 7 | alpha_engine/asset_class.py | Register MUTUAL_FUND asset class | — |
| P2 | 8 | ml_gatekeeper/gatekeeper.py | Add MUTUAL_FUND class ID 7 | Line 73 |
| P2 | 9 | audit_trail/dashboard_generator.py | Add mutual fund dashboard bucket | ~6763, ~6128, ~14201 |
| P2 | 10 | alpha_engine/risk_thresholds.json | CREATE — Centralized risk thresholds | New file |
| P2 | 11 | alpha_engine/mutual_fund_ranker.py | CREATE — MF ranker | New file |
| P2 | 12 | tools/mf_traits_walkforward_runner.py | CREATE — MF walkforward runner | New file |
| P2 | 13 | tools/mf_walkforward_backtest.py | CREATE — MF walkforward backtest | New file |
| P2 | 14 | tools/mf_trait_features.py | CREATE — MF trait features | New file |
| P2 | 15 | audit_dashboard/data/mf_cache_manifest.json | CREATE — SHA-256 provenance manifest | New file |

---
