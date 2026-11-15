# QA Validation Protocol — PnL=0%, Blank Fields, Open/Recently Closed

**Purpose:** QA protocol referenced throughout the profitability plan. Must be implemented in `alpha_engine/risk_qa_validator.py` and wired into `production_scanner.py`.

---

## QA Check 1: PnL = 0% Validation Against Real Market Data

**Purpose:** Detect picks where PnL is reported as 0% but real market data shows movement (indicating stale prices, missing exits, or data corruption).

### Fields Checked

| Field | Criticality | When Missing |
|-------|-------------|--------------|
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

### Severity Levels

| Severity | Definition | Action |
|----------|------------|--------|
| CRITICAL | Pick is unauditable — cannot verify outcome | Exclude from all stats, flag for manual review |
| HIGH | Pick missing key field — partial audit possible | Include with warning, flag for fix |
| MEDIUM | Missing non-critical field | Include, log for data quality improvement |
| LOW | Cosmetic issue | Log only |

---

## QA Check 2: Blank Field Detection

Every pick is checked for blank fields. The `check_blank_fields()` function returns a list of issues with severity levels.

**Severity distribution from audit of `closed_picks.json`:**
- All 3,500 closed rows missing `resolution_method` → CRITICAL
- Many picks missing `entry_price`, `exit_price`, `status`, `symbol` → CRITICAL/HIGH
- Many picks missing `take_profit`, `stop_loss` → HIGH

---

## QA Check 3: Mutual Fund Solid Pick Validation

**Purpose:** Validate mutual funds before including in core allocation (NOT active picks).

**Hard Gates (ALL must pass):**

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

**Starter universe:** VFIAX, VTSAX, FXAIX, SWTSX, VBTLX, VWELX, VGSLX, VTIAX

**Screening result:** 2 of 8 sample funds pass (FXAIX, SWTSX)

---

## QA Check 4: ETF Solid Pick Criteria

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

| Check | Threshold | Action |
|-------|-----------|--------|
| Price | > 0 and < 1000× reasonable range | FLAG if outside |
| Time | entry_time < exit_time (for closed) | FLAG if inverted |
| PnL | \|pnl_pct\| < 500% | FLAG if > 500% (corrupt) |
| Cross-source | Same symbol, different sources disagree on price > 2% | FLAG |

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

---

## Implementation Schedule

| Frequency | Check | Owner |
|-----------|-------|-------|
| Every scan | PnL=0% validation, blank fields, reasonability | `risk_qa_validator.py` |
| Every hour | Open positions >72h, unrealized PnL | `risk_dashboard_data.py` |
| Every day | Mutual fund NAV freshness, ETF validation | `mf_walkforward_backtest.py` |
| Every week | Full QA dashboard review, gate status | Manual/automated |
| Every month | Full validation report, kill/mutate decisions | Manual review |
