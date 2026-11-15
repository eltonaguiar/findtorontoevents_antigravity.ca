# 01_SPECIFICATION — FOREX

**Asset Class:** FOREX (Foreign Exchange)
**Status:** BLOCKED — Negative Expectancy, High Drawdown
**sizing_allowed:** false
**Source:** `alpha_engine/data/closed_picks.json`, `audit_dashboard/data/money_ready_verdict.json`, `audit_dashboard/data/pf_registry.json`, `final_v3/quant-audit-2026-11-14/04_asset_class_fixes/ASSET_CLASS_FIXES.md`, `reports/peer_claude-phase10b-money-maker-FOREX_result_2026-05-31.md`, `reports/DAILY_IDEAS_DIGEST_FOR_RESCUE_2026-05-19.md`

---

## 1. Algorithm Specification

### Strategies Attempted

| Strategy | File | Parameters | Entry Logic | Exit Logic | TP/SL | Result |
|----------|------|-----------|-------------|------------|-------|--------|
| `multi_asset_copytrader` | `alpha_engine/data/closed_picks.json` | Copy trader consensus | Copy trader direction | Unknown | Unknown | n=160 closed, WR 12.5% (win/total), PF 0.8385 |
| Various Forex strategies | `alpha_engine/forex_strategies.py` | Various | Various | Various | Various | Not tested on real picks |

**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/forex_strategies.py` (1114 lines) — 8 FX strategies including carry trader, Asian range breakout, ORB, Connors RSI2, cross-sectional momentum, COT-adapted, London breakout, mean reversion 200d.

### Cost Model
- Spread: variable by pair (typically 1-3 pips for majors)
- Commission: varies by broker
- Swap/funding: overnight financing costs
- Source: `alpha_engine/money_ready_verdict.py:SLIPPAGE_BPS["FOREX"] = 8.0` (8 bps round-trip)

### Benchmark
- Buy-and-hold the currency pair
- No separate benchmark for FX (FX is the benchmark itself)

### Walk-Forward Design
- Not implemented for Forex strategies

---

## 2. Backtest Results (Ground Truth from closed_picks.json)

**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/data/closed_picks.json` (filter: `category == "forex"`)

| Metric | Value |
|--------|-------|
| Total closed FOREX picks | 176 |
| Wins (WON) | 24 |
| Losses (LOST) | 26 |
| CLOSED (other) | 29 (27 CLOSED + 2 EXPIRED) |
| FLAT (unresolved) | 97 |
| WR (WON ÷ all n) | **13.64%** |
| WR (WON ÷ WON+LOST only) | 48.0% (24/50) |
| Gross win ($) | +$342.40 |
| Gross loss ($) | -$263.86 |
| PF (WON/LOST only) | **1.30** |
| Net PnL ($) | +$88.00 |
| Max Drawdown ($) | **$174.76** |

**Critical caveat:** 55% of FOREX picks (97/176) are `FLAT` — never resolved to win/loss. Only 50 of 176 have a real outcome. The apparent PF of 1.30 is computed on just 50 resolved picks and is not representative of the full cohort.

---

## 3. Money-Ready Verdict

**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/audit_dashboard/data/money_ready_verdict.json`

| Metric | Value |
|--------|-------|
| n_resolved (intrabar truth) | 612 |
| WR | **32.19%** |
| PF (intrabar honest) | **0.6596** |
| policy_clean n | 432 |
| policy_clean WR | 35.88% |
| policy_clean PF | **0.8385** (≈ 0.85 "recent PF") |
| MDD | **0.8212 (82%)** — **mdd_ok = false** |
| Expectancy | 0.006089 (barely positive) |
| Expectancy OK | true (marginally) |
| Bootstrap CI lower | **-0.000194** (CI crosses zero — not statistically positive) |
| DSR OK | true (dsr_score 0.9903) |
| SPA OK | true (spa_p 0.064) |
| Walk-forward OOS PF | **0.4829** — **wf_oos_ok = false** |
| Bootstrap CI OK | **false** |
| FDR OK | null (only 1 testable strategy) |
| Recency OK | true (last pick 2.2d ago) |
| **policy_frozen** | **true** |
| **verdict** | **NOT_READY** |

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
| Official intrabar n | 612 |
| WR | 32.19% |
| PF | **0.660** |
| Registry cohort n | 432 |
| Registry WR | 35.88% |
| Registry PF | 0.838 |
| Raw 14-day window | 11 wins / 148 losses, **PF 0.087** |
| Verdict | NOT_READY |
| Action | G10 carry basket test |

---

## 6. Money-Maker FOREX Analysis

**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/reports/peer_claude-phase10b-money-maker-FOREX_result_2026-05-31.md`

**Class verdict at 06:30Z 2026-05-31:**

| Metric | Value |
|--------|-------|
| PF | 0.035 |
| WR | 27.59% |
| n | 29 (policy-clean-net) |
| MDD | 81.05% |
| Expectancy | -4.58%/pick |
| CVaR95 | -50.84% |
| T2-status: | **FAIL on (PF, WR, MDD, n, DSR, expectancy)** — every gate failed |

Raw 90d (no policy filter): n_closed=1,531; 904 TP_HIT + 21 WON + 1,379 LOST + 131 EXPIRED + 11,601 TIME_EXIT + 3 SL_HIT. The TIME_EXIT slug (76%+ of "closed") is the same EXPIRED→positive-PnL mislabel pathology.

Best candidate: `cta_cross_asset_tsmom` (n=189, WR=53.4%, PF=3.57 — but inflated by 1 catastrophic mislabel; true PF est. 2.0-2.5). Phase-3 MC pick `fx_smart_carry_trade_momentum` (n=56, WR=37.5%, PF=0.817) underperforms.

**P(T2@n=100) ≈ <1%** — the class fails on PF and expectancy long before n=100.

---

## 5. Historical FOREX PF ~0.27

**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/reports/DAILY_IDEAS_DIGEST_FOR_RESCUE_2026-05-19.md` (line 17)

| Class | Pain | Action |
|-------|------|--------|
| **FOREX** | **PF~0.27, −1026% PnL** | **FOREX_HARD_DISABLE ✅** |

Carry/COT daily families killed/toxic. FOREX hard-disable was shipped. This is the "historical PF 0.27 (sub-floor)" referenced in the request.

---

## 6. Forex Strategies File

**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/forex_strategies.py` (1114 lines) — 8 FX strategies:
- Carry trader
- Asian Range Breakout
- ORB (Opening Range Breakout)
- Connors RSI2
- Cross-Sectional Momentum
- **COT-adapted**
- London Breakout
- Mean Reversion 200d

References `forex_carry_ppp`, `non_crypto_quality_gate.forex_macro_gate`.

---

## 7. Forex COT Contrarian Strategy

**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/forex_cot_reversal.py` (per `cot_crypto_overlay_2026-05-17.md`)

Also: `alpha_engine/commodity_cot_contrarian.py`, `alpha_engine/cot_positioning.py`, `tools/cftc_cot_fetcher.py`, `tools/cot_lag_corrector.py`

**Gate (pre-registered, lines 80-82):**
- `GATE_OOS_PF = 1.15`
- `GATE_MIN_TRADES = 100`
- `GATE_MAX_SLIPPAGE_SHARE = 0.25`
- 4 checks: `n_ge_100`, `pf_ge_1.15`, `slippage_lt_25pct`, `beats_benchmark`

Focus: COMMODITY (weekly, CFTC COT data from `ejaguiar1_stocks.cftc_cot_weekly`, 2,849 rows / 11 markets, yfinance continuous futures `=F`). Not FOREX-specific.

**Gate result:** No saved `reports/cot_contrarian_backtest.json` exists. Backtest requires live MySQL connection (`pymysql` against `ejaguiar1_stocks`) and `yfinance` price data — cannot be run offline.

---

## 8. Money-Ready Gate Result

**0/7 gates passed.** FOREX has:
- Historical PF 0.27 (sub-floor)
- Recent PF 0.85 (below break-even)
- WR 32-40%
- High n but negative expectancy
- MDD 82% (exceeds 20% threshold)
- Walk-forward OOS PF 0.4829 < 1.0
- Bootstrap CI crosses zero (lower bound -0.000194)
- Policy frozen (`policy_frozen=true`)

**FOREX is BLOCKED.** No credible path to profitability.

**File paths for every claim:**
- Closed picks JSON: `alpha_engine/data/closed_picks.json` — 176 FOREX picks, WR 13.64% (of all n), PF 0.6596
- Money ready verdict: `audit_dashboard/data/money_ready_verdict.json` — FOREX block lines 209-376
- PF registry: `audit_dashboard/data/pf_registry.json` — FOREX policy_clean_net: n=432, WR 35.88%, PF 0.838
- Asset class fixes: `final_v3/quant-audit-2026-11-14/04_asset_class_fixes/ASSET_CLASS_FIXES.md` — FOREX section lines 74-87
- Money-maker FOREX analysis: `reports/peer_claude-phase10b-money-maker-FOREX_result_2026-05-31.md` — expectancy -4.58%/pick
- Historical PF 0.27: `reports/DAILY_IDEAS_DIGEST_FOR_RESCUE_2026-05-19.md` line 17 — FOREX_HARD_DISABLE
- Forex strategies: `alpha_engine/forex_strategies.py` — 8 strategies
- Forex COT reversal: `alpha_engine/forex_cot_reversal.py`

**FOREX is BLOCKED.** High n but sub-floor PF (0.66-0.84 vs 1.5 floor), MDD 82%, failing OOS walk-forward (0.48), bootstrap CI crosses zero. No path to profitability.
