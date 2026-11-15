# 01_SPECIFICATION — FUTURES

**Asset Class:** FUTURES
**Status:** BLOCKED — All Picks Force-Closed Toxic, Stale 246 Days
**sizing_allowed:** false
**Source:** `alpha_engine/data/closed_picks.json`, `audit_dashboard/data/money_ready_verdict.json`, `audit_dashboard/data/pf_registry.json`, `final_v3/quant-audit-2026-11-14/04_asset_class_fixes/ASSET_CLASS_FIXES.md`

---

## 1. Algorithm Specification

### Strategies Attempted

| Strategy | File | Parameters | Entry Logic | Exit Logic | TP/SL | Result |
|----------|------|-----------|-------------|------------|-------|--------|
| `futures_momentum` | `alpha_engine/futures_strategies.py` | Momentum-based | Trend following | Trend reversal | Unknown | Blocked (WR=2%, n=202, both directions broken) |
| `multi_asset_copytrader` | `alpha_engine/data/closed_picks.json` | Copy trader consensus | Copy trader direction | Unknown | Unknown | 31 picks, all force-closed toxic, WR=0% |

### Cost Model
- Commission: varies by contract (typically $1-5 per contract per side)
- Slippage: varies by contract liquidity
- Round-trip cost: varies significantly by contract
- Source: Not explicitly modeled in backtests

### Benchmark
- Buy-and-hold the futures contract (not directly possible due to contract expiration/roll)
- Source: Not modeled

### Walk-Forward Design
- Not implemented for futures strategies

---

## 2. Backtest Results (Ground Truth from closed_picks.json)

**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/data/closed_picks.json` (filter: `category == "futures"` or `asset_class == "FUTURES"`)

| Metric | Value |
|--------|-------|
| Total closed FUTURES picks | **31** |
| Wins (WON) | 0 |
| Losses (LOST) | 0 |
| CLOSED (all 31) | **31** |
| Win Rate | **0.0%** |
| Profit Factor | undefined (0 wins / 0 losses = 0/0) |
| Gross win / Gross loss | $0 / $0 |
| Net PnL ($) | **$0.00** |
| Max Drawdown ($) | **$0.00** |

**Every single FUTURES pick is status=`CLOSED` with zero PnL — all force-closed toxic / never opened.** There is no realized FUTURES PnL whatsoever in `closed_picks.json`.

---

## 3. Money-Ready Verdict

**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/audit_dashboard/data/money_ready_verdict.json`

| Metric | Value |
|--------|-------|
| n_resolved (intrabar truth) | 52 |
| WR | 42.31% |
| PF (intrabar) | 1.0936 |
| policy_clean n | 13 |
| policy_clean WR | 30.77% |
| policy_clean PF | 1.0093 |
| MDD | 0.1378 — mdd_ok = true |
| Expectancy | 0.006615 — expectancy_ok = true |
| **n_ok** | **false** (n=13 < MIN_N_CLASS=100) |
| **DSR OK** | **false** (dsr_score 0.0075) |
| **Recency OK** | **false** (last pick **246.4 days ago** — 2026-03-13, stale) |
| **policy_frozen** | **true** |
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
| Official intrabar n | 52 |
| WR | 42.31% |
| PF | 1.094 |
| Registry cohort n | 13 |
| Registry WR | 30.77% |
| Registry PF | 1.009 |
| Verdict | INSUFFICIENT_DATA |
| Action | Real feed + contract identity |

---

## 6. Futures Copy-Trader Blocked

**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/audit_trail/quality_gates.py`

**Line 2715:** `("FUTURES", "multi_asset_copytrader"),  # 2026-11-15 — WR=2.5% n=157 critical drain (verified against closed_picks.json)`

Also blocked:
- `alpha_engine/strategy_blocklist.py:229` — `"futures_momentum"`
- `alpha_engine/smart_picks_engine.py:290-291` — `"futures_momentum"` (killed 2026-05-06, 0% WR on 56 closed, PF 0.00)
- `alpha_engine/emitter_discipline.py:48` — `"futures_momentum"` (94 emits/7d, LONG PF=0.00)
- `alpha_engine/config.py:291` — `"futures_momentum"` (M-110 blocked)
- `alpha_engine/hedge_fund_quality_gate.py:186` — `FUTURES_BANNED_STRATEGIES = frozenset({"futures_momentum"})`
- `tools/fixes_v3/strategy_killer.py:82` — `"futures_momentum"` block config
- `tools/research/strategy_block_expiry_audit.py:46` — `"futures_momentum": "2026-05-17"`

**Yes — the FUTURES copy-trader (`multi_asset_copytrader`) IS blocked in quality_gates.py at line 2715.** Also `futures_momentum` blocked at line 2714.

---

## 7. Final Verdict: BLOCKED

| Criterion | Threshold | Actual | Pass/Fail |
|-----------|-----------|--------|-----------|
| Net expectancy | > 0 | $0.00 (all $0 PnL) | **FAIL** |
| Win Rate | > 50% | 0.0% | **FAIL** |
| Profit Factor | > 1.15 | undefined (0/0) | **FAIL** |
| DSR | ≥ 0.95 | 0.0075 | **FAIL** |
| PBO | ≤ 0.10 | N/A (no trades) | **FAIL** |
| Forward closes | ≥ 100 over 3 months | 0 | **FAIL** |
| Max Drawdown | < 20% | 0.0% (all $0 PnL) | PASS (trivially) |
| Recency | < 30 days since last pick | 246.4 days (2026-03-13) | **FAIL** |
| Sample size | n ≥ 100 | n=13 (policy clean) | **FAIL** |

**FOREX/FUTURES copy-trader: BLOCKED.** All 31 FUTURES picks in `closed_picks.json` are `status=CLOSED` with `pnl_pct=0` — all force-closed toxic, zero realized PnL. Stale 246 days since last pick. DSR=0.0075. No credible path to profitability.

**File paths for every claim:**
- Closed picks JSON: `alpha_engine/data/closed_picks.json` — 31 FUTURES picks, all CLOSED, all pnl_pct=0
- Money ready verdict: `audit_dashboard/data/money_ready_verdict.json` — FUTURES block lines 954-1098
- PF registry: `audit_dashboard/data/pf_registry.json` — FUTURES policy_clean_net: n=13, WR 30.77%, PF 1.009
- Asset class fixes: `final_v3/quant-audit-2026-11-14/04_asset_class_fixes/ASSET_CLASS_FIXES.md` — FUTURES section lines 107-119
- FUTURES copy-trader blocked: `audit_trail/quality_gates.py:2715`
- Additional futures_momentum blocks: `alpha_engine/strategy_blocklist.py:229`, `alpha_engine/smart_picks_engine.py:290-291`, `alpha_engine/emitter_discipline.py:48`, `alpha_engine/config.py:291`, `alpha_engine/hedge_fund_quality_gate.py:186`, `tools/fixes_v3/strategy_killer.py:82`

**FUTURES is BLOCKED.** Stale (246 days since last pick), insufficient n (13 policy-clean), failing DSR (0.0075), all closed_picks picks are zero-PnL force-closes. Neither class has a credible path to profitability.
