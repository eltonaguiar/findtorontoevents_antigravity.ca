# Kimi Audit Findings — 2026-04-05

**Reviewer:** Kimi Code agent
**Dashboard:** https://findtorontoevents.ca/audit/ (v102-ish, reported as v99.0)
**Status:** Corrections applied (see §13 of source). Legit P0/P1 bugs below.

## 🔄 Verification status (2026-04-04 17:55 UTC)

| Kimi finding | Status | Evidence |
|---|---|---|
| §2.2 Equities summary vs drill-down (45.8% vs 83.3% WR) | ✅ **CLOSED** | Playwright E2E verified 17:42Z — 53A/61C vs 53A/60C (off-by-1) |
| §2.3 Forex drift (164/177 vs 118/108) | ✅ **CLOSED** | Playwright E2E verified 17:42Z — 3A/236C both match |
| §2.5 Futures empty drill-down | ✅ **CLOSED** | Playwright E2E verified 17:42Z — 0A/5C both match |
| §2.6 ETFs PF=0 (catClosed empty) | ✅ **CLOSED** | Playwright E2E verified 17:42Z — 0A/4C both match |
| §1.4 Drawdown 19,702% uncapped | ✅ **CLOSED** | Mercury DD cap shipped in f0c30c1671 by claude-noncrypto-drilldown |
| §1.1 Total PnL −17,657% (summation bug) | 🟡 **IN PROGRESS** | antigrav-dash-integrity working on dashboard_generator.py aggregation |
| §4 VA source→realized 9.5pp drop | ℹ️ **INFO / RESOLVED** | VA not broken — 27 active picks confirmed; JS parity fix e84bf9adfc |
| §0.2 Missing exit prices on closed picks | 🟡 **UNCLAIMED** | still in bus:tasks:pending, data pipeline |

**Additional fixes shipped in f0c30c1671** (claude-noncrypto-drilldown, 2026-04-04):
- Conflict resolver wired in
- Active pick deduplication
- Score safety-net

**Coordination:** copilot-quant-audit session COMPLETE (CHATWITHIT.MD); antigrav-dash-integrity owns remaining aggregation P0s.

---

## P0 — BLOCKERS (fix immediately)

### 1. Total PnL = −17,657.56% — summation bug (not compounding)
- Tooltip itself admits: "sum of each trade's individual return, NOT compounded"
- 93% of the figure comes from TRXUSDT alone
- Removing TRX → −1,240.5% (still wrong, but "reasonable")
- **Fix:** `total_pnl = (final_capital − initial_capital) / initial_capital × 100`, not `sum(trade_pnl_pct)`
- Files: `cleanup_dashboard.py`, `update_audit_dashboard.py`, `audit_dashboard/data/dashboard_data.json`

### 2. Rolling 30d Drawdown = 19,702.89% — uncapped
- Drawdown cannot exceed 100% without leverage/liquidation
- **Fix:** `DD = (peak − trough) / peak × 100`, cap at 100%
- Section: Mercury Validation

### 3. Commodities summary vs drill-down mismatch
- Summary card: **+18.95%** realized PnL
- Drill-down modal: **−9.80%** realized PnL (opposite sign!)
- Same root cause as §5 below (different data sources)

### 4. Missing exit prices on closed picks
- Some closed trades show `—` for exit price but still have a PnL number
- Question: how is PnL computed without exit? Data pipeline gap.

---

## P1 — HIGH (fix this week)

### 5. Client-side `catClosed` filter bug (aka magnifying-glass bug)
- Drill-down modals compute stats from `catClosed` = client filter of `D.picks.recent_closed`
- If category picks fall outside the capped payload, `catClosed.length = 0`
- Consequences: ETF PF=0, Futures drill-down shows "no trades" despite 5 closed in summary
- **This is the SAME bug causing 3 symptoms** — fix once
- **Fix:** Either uncap the payload for drill-downs, or send per-category slices server-side

### 6. Equities summary vs drill-down drift
- Summary: 45.8% WR, 130/153/1, +62.60%
- Drill-down: 83.3% WR, 35/7, +135.06%
- Root cause: same as §5 (drill-down filtering capped payload)

### 7. Forex summary vs drill-down drift
- Summary: 164/177/36
- Drill-down: 118/108/32
- Same root cause as §5

---

## P2 — MEDIUM (fix this month)

### 8. 10+ strategies showing 0% rolling 7d WR
- Examples: `ml_enhanced_STRKUSDT_15m`, `ml_enhanced_TRXUSDT_4h`, `drawdown_recovery_rsi_sol`, `crypto_keltner_compression_expansion`
- Either broken, dormant, or tracking bug

### 9. Stale strategies (no picks in 9+ days)
- `top_gainer_predictor`: 224h idle
- `revival_all`, `revival_dormant_strategies`: 159h idle

### 10. Zero-PnL active picks (QQQ, IWM, EEM, USDCHF=X, AUDUSD=X, SI=F, HG=F)
- Opened 54m–1.4h ago, should show movement
- Likely entry=current price stale, or price feed missing

### 11. Missing Score values on active picks (QQQ, IWM, EEM show `—`)

### 12. Tooltips missing for Smart Snapshot, Trust Tiers (BANNED/UNTRUSTED/WATCH)

---

## Overlap with other agents

- **copilot-quant-audit** already found: VA=0, zero-PnL sourceless picks, GC=F invalid prices, WUSDT sign inversion
- **Recommendation:** coordinate to avoid duplicate work. Who owns which fix?

---

## Kimi's self-corrections (important context)

1. **PF=4.99 is valid math** — Kimi initially flagged as impossible, then corrected. `PF = sum(win_pnl)/|sum(loss_pnl)|`, NOT wins/losses ratio.
2. **Per-trade Sharpe (-0.1203) ≠ annualized** — don't compare directly to benchmarks. Use annualized (-7.05) for comparisons.
3. **ETF PF=0** isn't a math bug — it's the `catClosed` filter bug (§5).

---

## Claim this work (via Redis bus)

```bash
PY="C:/Users/zerou/AppData/Local/Programs/Python/Python314/python.exe"
BUS="C:/Users/zerou/redis-bus/agent_bus.py"
$PY $BUS broadcast <your-id> "CLAIMING: P0 #1 total_pnl compounding fix"
```

Recommended ownership:
| Item | Candidate owner | Why |
|---|---|---|
| P0 #1 total_pnl fix | backend/data agent | Touches cleanup_dashboard.py |
| P0 #2 drawdown cap | backend/data agent | Same file |
| P0 #3 + P1 #5/#6/#7 | dashboard-ui agent | All driven by `catClosed` filter bug |
| P0 #4 exit prices | data-pipeline agent | Source DB audit |
| P2 #8/#9 strategies | quant agent | Strategy lifecycle |
