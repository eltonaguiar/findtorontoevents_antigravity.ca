# QA Validation Protocol — PnL=0%, Blank Fields, Open/Recently Closed

This is the QA protocol referenced throughout the plan. It must be implemented in `alpha_engine/risk_qa_validator.py` and wired into `production_scanner.py`.

---

## QA Check 1: PnL = 0% Validation Against Real Market Data

**Purpose:** Detect picks where PnL is reported as 0% but real market data shows movement (indicating stale prices, missing exits, or data corruption).

**Implementation:**

```python
def validate_pnl_zero(pick, market_data):
    """
    pick: dict with entry_price, exit_price, pnl_pct, status, symbol, created_at, closed_at
    market_data: dict with symbol -> {open_price, close_price, current_price}
    """
    issues = []
    
    if pick.get("pnl_pct") == 0 or pick.get("pnl_pct") is None:
        symbol = pick.get("symbol")
        entry = pick.get("entry_price")
        exit_px = pick.get("exit_price")
        
        if symbol and symbol in market_data:
            md = market_data[symbol]
            
            # If pick is closed but pnl=0, check if price actually moved
            if pick.get("status") in ("CLOSED", "WON", "LOST", "TP_HIT", "SL_HIT"):
                if entry and md.get("close_price"):
                    real_pnl = (md["close_price"] - entry) / entry * 100
                    if abs(real_pnl) > 0.5:  # >0.5% move = suspicious zero PnL
                        issues.append({
                            "severity": "CRITICAL",
                            "check": "pnl_zero_but_price_moved",
                            "reported_pnl": 0,
                            "real_pnl_pct": round(real_pnl, 2),
                            "symbol": symbol
                        })
            
            # If pick is open >72h, check current vs entry
            if pick.get("status") in ("OPEN", "ACTIVE"):
                if entry and md.get("current_price"):
                    hours_open = (now - pick.get("created_at")).total_seconds() / 3600
                    if hours_open > 72:
                        unrealized = (md["current_price"] - entry) / entry * 100
                        issues.append({
                            "severity": "HIGH",
                            "check": "open_position_over_72h",
                            "hours_open": round(hours_open, 1),
                            "unrealized_pnl_pct": round(unrealized, 2),
                            "symbol": symbol
                        })
    
    return issues
```

**Acceptance criteria:**
- Every pick with pnl_pct=0% must be validated against real market data.
- Flag as CRITICAL if closed pick shows 0% PnL but real price moved >0.5%.
- Flag as HIGH if open position >72h without exit.
- Output to `qa_dashboard.html` with severity color coding.

---

## QA Check 2: Blank Field Flags (Open & Recently Closed Items)

**Purpose:** Detect picks with missing critical fields that make them unauditable.

**Fields to check:**

| Field | Criticality | When Missing |
|-------|------------|--------------|
| `entry_price` | CRITICAL | Always required |
| `exit_price` | CRITICAL | Required for closed picks |
| `entry_time` / `created_at` | CRITICAL | Always required |
| `exit_time` / `closed_at` | HIGH | Required for closed picks |
| `take_profit` | HIGH | Required for picks with TP exits |
| `stop_loss` | HIGH | Required for picks with SL exits |
| `status` | CRITICAL | Always required |
| `symbol` | CRITICAL | Always required |
| `asset_class` | HIGH | Required for class-level gating |
| `strategy` | HIGH | Required for attribution |
| `resolution_method` | CRITICAL | Required for all closed picks (currently MISSING on all 3,500) |
| `pnl_pct` | CRITICAL | Required for closed picks |
| `direction` | HIGH | Required (LONG/SHORT/FLAT) |

**Severity levels:**

| Severity | Definition | Action |
|----------|-----------|--------|
| CRITICAL | Pick is unauditable — cannot verify outcome | Exclude from all stats, flag for manual review |
| HIGH | Pick missing key field — partial audit possible | Include with warning, flag for fix |
| MEDIUM | Missing non-critical field | Include, log for data quality improvement |
| LOW | Cosmetic issue | Log only |

**Implementation:**

```python
def check_blank_fields(pick):
    issues = []
    for field, severity in REQUIRED_FIELDS.items():
        if field not in pick or pick[field] is None or pick[field] == "":
            issues.append({
                "field": field,
                "severity": severity,
                "pick_id": pick.get("id") or pick.get("dedup_key")
            })
    return issues
```

**Acceptance criteria:**
- All open picks checked for blank fields on every scan.
- All recently closed picks (last 24h) checked for blank fields.
- `resolution_method` backfilled on all 3,500 closed rows or flagged as CRITICAL.
- QA dashboard shows blank-field count by severity.

---

## QA Check 3: Mutual Fund Solid Pick Validation

**Purpose:** Validate mutual funds before including in core allocation (NOT active picks).

**Hard gates (ALL must pass):**

| Criterion | Threshold |
|-----------|-----------|
| Expense ratio | ≤ 0.09% (index) / ≤ 0.20% (active) |
| Load fee | None |
| 12b-1 fee | None |
| Min initial investment | ≤ $1,000 |
| AUM | ≥ $1B |
| Turnover ratio | ≤ 20% |
| Tracking error vs benchmark | ≤ 0.25% |
| Track record | ≥ 10 years |
| NAV freshness | ≤ 24h |

**Soft criteria (scored, not gated):**

| Criterion | Weight |
|-----------|--------|
| Tax efficiency | 20% |
| Manager tenure (active funds) | 15% |
| Category rank (3-5 yr) | 25% |
| Max drawdown (3-5 yr) | 20% |
| Sharpe ratio (3-5 yr) | 20% |

**Implementation:**

```python
def validate_mutual_fund(fund):
    gates = {
        "expense_ratio": fund.get("er", 999) <= 0.0009,  # 0.09%
        "no_load": fund.get("load") == 0,
        "no_12b1": fund.get("b_12b1") == 0,
        "min_initial": fund.get("min_initial", 999999) <= 1000,
        "aum": fund.get("aum", 0) >= 1_000_000_000,
        "turnover": fund.get("turnover", 999) <= 0.20,
        "tracking_error": fund.get("tracking_error", 999) <= 0.0025,
        "track_record_years": fund.get("track_record_years", 0) >= 10,
        "nav_freshness_hours": fund.get("nav_freshness_hours", 999) <= 24,
    }
    passed = all(gates.values())
    failed = [k for k, v in gates.items() if not v]
    return {"passed": passed, "failed_gates": failed, "gates": gates}
```

**Starter universe (all should pass gates):** VFIAX, VTSAX, FXAIX, SWTSX, VBTLX, VWELX, VGSLX, VTIAX.

**Acceptance criteria:**
- No mutual fund emitted as an active pick. Passive allocation only.
- All hard gates enforced in code before inclusion in core allocation.
- QA dashboard shows pass/fail per fund per gate.

---

## QA Check 4: ETF Solid Pick Criteria

**Purpose:** Validate ETFs before including in core allocation.

**Hard gates (ALL must pass):**

| Criterion | Threshold |
|-----------|-----------|
| Expense ratio | ≤ 0.10% |
| AUM | ≥ $500M |
| Avg daily volume | ≥ $10M |
| Bid-ask spread | ≤ 0.05% |
| Tracking error vs benchmark | ≤ 0.20% |
| Track record | ≥ 5 years |
| Leverage / inverse | None |

---

## QA Check 5: Reasonability Checks

**Purpose:** Sanity-check picks for obvious data errors.

| Check | Threshold | Action |
|-------|-----------|--------|
| Price | > 0 and < 1000× reasonable range | FLAG if outside |
| Time | entry_time < exit_time (for closed) | FLAG if inverted |
| PnL | |pnl_pct| < 500% | FLAG if >500% (corrupt) |
| Cross-source | Same symbol, different sources disagree on price > 2% | FLAG |
| Volume | Reasonable for asset class | FLAG if zero |

---

## QA Dashboard Page (`qa_dashboard.html`)

**Sections:**

1. **PnL=0% Alerts** — Table of picks with zero PnL flagged against real market data.
2. **Blank Field Report** — Count by severity (CRITICAL/HIGH/MEDIUM/LOW), list of affected picks.
3. **Open Positions >72h** — List of stale open positions with unrealized PnL.
4. **Mutual Fund Validation** — Pass/fail per fund per gate.
5. **ETF Validation** — Pass/fail per ETF per gate.
6. **Reasonability Alerts** — Price/time/PnL anomalies.
7. **Overall QA Status** — PASS/FAIL for each gate (Gate 0-4).

**Auto-refresh:** Every 60 seconds.
**Data source:** `alpha_engine/data/risk_metrics.json` (generated by `tools/risk_dashboard_data.py`).

---

## QA Pass/Fail Gates

| Gate | Condition | Fail Action |
|------|-----------|-------------|
| Gate 0 | PnL=0% validation passes (no CRITICAL unresolved) | Block all pick emission |
| Gate 1 | Blank fields: zero CRITICAL unresolved | Block pick emission for affected symbols |
| Gate 2 | Mutual funds: all hard gates pass for core allocation | Exclude failing funds from allocation |
| Gate 3 | ETFs: all hard gates pass for core allocation | Exclude failing ETFs from allocation |
| Gate 4 | Reasonability: no unresolved CRITICAL alerts | Block affected picks |

**Rule:** Any gate failure = no capital deployment for affected assets. QA is fail-closed, not fail-open.

---

## QA Implementation Schedule

| Frequency | Check | Owner |
|-----------|-------|-------|
| Every scan | PnL=0% validation, blank fields, reasonability | risk_qa_validator.py |
| Every hour | Open positions >72h, unrealized PnL | risk_dashboard_data.py |
| Every day | Mutual fund NAV freshness, ETF validation | mf_walkforward_backtest.py |
| Every week | Full QA dashboard review, gate status | Manual/automated |
| Every month | Full validation report, kill/mutate decisions | Manual review |

---

## Integration with production_scanner.py

```python
# In production_scanner.py, before emitting any pick:
qa_result = risk_qa_validator.validate_pick(pick, market_data)
if qa_result["gate_status"] == "FAIL":
    log_qa_failure(pick, qa_result)
    continue  # Do not emit pick
if qa_result["gate_status"] == "WARN":
    log_qa_warning(pick, qa_result)
    emit_with_warning(pick)
else:
    emit_pick(pick)
```

**Never emit a pick that fails Gate 0 or Gate 1.**
