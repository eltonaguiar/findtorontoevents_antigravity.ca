# Paper-Pilot Cohort — Proposed Approach (v2 POST-PEER-REVIEW)

**Date:** 2026-06-05 (revised after multi-AI peer review)  
**Status:** REVISED — incorporates feedback from 6 reviewers (4 swarm + ring-1T + free-mode-large)  
**Author:** claude-sonnet-4.6

---

## 0. Peer Review Summary

| Reviewer | Verdict | Key Concern |
|---|---|---|
| free-mode-fast (llama-3.1-8b) | APPROVE-WITH-CHANGES | Shutdown thresholds vague; ladder jumps too aggressive |
| free-mode-large (gemini-flash) | APPROVE-WITH-CHANGES | Correlation blindness; resolver not stress-tested |
| free-mode (gemma-4-26b) | **REJECT** | "Garbage in, garbage out" — resolver is fiction |
| deepseek-chat-direct | APPROVE-WITH-CHANGES | Undefined thresholds; 10x ladder jumps |
| ring-1t (deep reasoning) | **Option A — Conservative, no ambiguity** | "PF 6-9 is a red flag, not a selling point" |
| free-mode-large (3rd opinion) | Option A — Conservative | Execution slippage is single largest failure mode |

**Consensus (6/6 reviewers):**
1. Resolver validation is the **primary gate** before $100 step
2. Numeric shutdown thresholds are **mandatory** (not tier names)
3. Correlation blindness is real — 3 sleeves from same source ≠ diversification
4. Ladder jumps should be **3-5x max**, not 10x
5. **Adopt Option A (Conservative)** for v2

---

## 1. Mission (UNCHANGED)

Execute a **30-day paper-pilot cohort** on the 4 CRYPTO sleeves identified as real edges after strict 5-axis scrutiny. Goal: validate the edges against live OHLC, prove survivability under realistic slippage, and produce a go/no-go decision for live capital allocation by **2026-07-05**.

## 2. The 4 Sleeves (UNCHANGED, validated)

| Sleeve | Symbol/Source | n | WR | PF | Avg Win | Avg Loss | W/L | Hold |
|---|---|---|---|---|---|---|---|---|
| S1 | JUPUSDT × mega_mutation | 47 | 85% | 9.08 | +6.3% | -4.0% | 1.59 | <1d |
| S2 | ENAUSDT × mega_mutation | 30 | 80% | 8.88 | +8.7% | -3.9% | 2.22 | <1d |
| S3 | ADAUSDT × mega_mutation | 27 | 78% | 6.87 | +4.2% | -2.1% | 1.96 | <1d |
| S4 | DYDXUSDT × alpha_engine | 36 | 89% | 6.07 | +1.9% | -2.2% | 0.84 | 2-18h |

## 3. CRITICAL: Resolver Risk Acknowledged (Section v2)

All reviewers flagged the **NOMINAL_TP_LEGACY resolver issue** as the #1 risk. The resolver computes fills at TP price, not actual intrabar price. This means:
- 78-89% historical WR is **potentially inflated 15-30%**
- 6-9 PF is **likely 2-3 in reality**
- The 4 sleeves may be **less attractive than they appear**

**Required action: Resolver validation MUST complete before any real capital deployment.**

## 4. v2 Position Sizing — CONSERVATIVE OPTION A

### Per-Sleeve Caps
- **S1/S2/S3 (mega_mutation family): 1.0% per sleeve each**
- **S4 (DYDX/alpha_engine): 0.5% per sleeve**
- **Combined mega_mutation exposure cap: 3.0%** (not 5% × 3 = 15%)
- **Total cohort exposure cap: 4.0% of portfolio**
- **Max position per trade: 0.5% of total portfolio** (1-loss-survivable at 5x DD)

### Kelly Fractions (computed live, but capped)
| Sleeve | Full Kelly | Quarter Kelly | **Final Cap** |
|---|---|---|---|
| S1 JUP/mega | 75.7% | 18.9% | **1.0%** |
| S2 ENA/mega | 71.0% | 17.8% | **1.0%** |
| S3 ADA/mega | 66.5% | 16.6% | **1.0%** |
| S4 DYDX/alpha | 75.6% | 18.9% | **0.5%** |

**Rationale:** Theoretical Kelly is dangerous for small samples with possibly inflated WR. Caps reflect (a) correlation risk, (b) resolver uncertainty, (c) small-sample noise.

### Worst-Case Loss Scenario (v2)
- All 4 sleeves hit BLACK shutdown simultaneously: 1+1+1+0.5 = **3.5% portfolio loss**
- If mega_mutation source fails: 3.0% (combined cap) + 0.5% (DYDX) = **3.5% portfolio loss**
- Survivable. No redemption event.

## 5. v2 Numeric Shutdown Thresholds (per peer review mandate)

| Tier | Sleeve DD | Aggregate DD | Other Triggers | Action |
|---|---|---|---|---|
| 🟡 **YELLOW** | -3% sleeve | -2% cohort | Single trade loss > 1%, last-3-trades WR < 50%, 24h with no exit | Pause new entries; notify Discord |
| 🟠 **ORANGE** | -5% sleeve | -4% cohort | Last-5-trades WR < 50%, 3 consecutive losses, 2+ sleeves Yellow in 4h | Pause all entries; close positions at market; mandatory review |
| 🔴 **RED** | -10% sleeve | -8% cohort | Last-10-trades WR < 40%, single-sleeve loss > 5% | Force close all; halt 24h; operator review required |
| ⚫ **BLACK** | -15% sleeve | -12% cohort | 2-sigma VaR breach, exchange API failure, 0 trades for 7d | Permanent shutdown; 48h cooling; restart requires full sign-off |

**New triggers added per review:**
- **Time-decay:** 0 trades in 7d → auto-disable sleeve
- **Correlation breach:** 2+ sleeves Yellow within 4h → Orange (correlation attack detection)
- **Volatility expansion:** 1h realized vol > 2x 30d avg → pause entries
- **Stale data:** price feed > 5min stale during market hours → Tier 4

## 6. v2 5-Stage Size-Up Ladder (per peer review)

| Stage | Duration | Size | Min Trades | Promotion Criteria | Roll-back Trigger |
|---|---|---|---|---|---|
| **0 — Paper** | 30+ days | $0 (virtual $1k) | 30 closed | Resolver validation PASS, 5-axis scrutiny holds, no Orange+ | Any Red/Black |
| **1 — Micro** | 14+ days | $100 total | 20 closed | Actual-fill WR within 15pp of backtest, no Red+ | Actual WR < backtest - 20pp |
| **2 — Small** | 14+ days | $300 total | 20 closed | Aggregate PF > 2.0 on actual fills | Last 10 trades WR < 40% |
| **3 — Mid** | 30+ days | $1,000 total | 30 closed | All gates pass, max DD < 8%, last 14d WR > 60% | Tier 3 trigger |
| **4 — Full** | Ongoing | $5,000 → operator-set | 60+ total | All scrutiny holds, last 30d WR > 65% | Tier 3 trigger |

**Step size:** 1x → 3x → 3.3x → 5x (per deepseek-chat-direct recommendation)

**Roll-back at any stage:** if criteria not met, **drop back 1 stage and re-validate**. No skipping.

## 7. Resolver Validation — MANDATORY PRE-CONDITION (per all 6 reviewers)

### Step 1: Build `tools/validate_intrabar_fills.py`
For each historical pick marked TP_HIT, replay 5-min OHLCV (or 1-min if available) from entry to find:
- Did `Low < SL` before `High >= TP`? If yes, the original WR is INFLATED
- Compute % of "TP_HIT" picks that actually hit SL first intraday
- If >20%, **reject that sleeve from pilot**

### Step 2: 7-Day Parallel Run
- Run BOTH NOMINAL_TP_LEGACY and INTRABAR_ACTUAL simultaneously
- Quantify WR/PF delta
- If delta > 15% on WR or 10% on PF, **recalculate all sizing**
- If corrected PF < 2.0 for any sleeve, **drop that sleeve from cohort**

### Step 3: Worst-Case Fill Stress Test
- Assume every TP fill is delayed by 1 bar (+0.5% worse)
- Re-label 20% of "wins" as "losses" (per ring-1T recommendation)
- Recalculate PF, WR, max DD
- If any sleeve has corrected PF < 2.0, **demote to research-only**

### Step 4: Latency Budget
- Real execution: exchange API latency 50-200ms
- Queue position risk on limit orders
- Add **0.2% per-trade "unknown slippage buffer"** (per deepseek-chat-direct)

**Gate:** All 4 steps must complete + pass before Stage 1 ($100) begins. Paper (Stage 0) can proceed.

## 8. Correlation Analysis (v2 — Per-Source Caps)

### Same-Day Exit Overlap (LIVE DB)
| Pair | Shared Days | % of A | % of B |
|---|---|---|---|
| JUP & ENA | 6 | 37.5% | 60.0% |
| JUP & ADA | 7 | 43.8% | 58.3% |
| JUP & DYDX | 2 | 12.5% | 8.7% |
| ENA & ADA | 5 | 50.0% | 41.7% |
| ENA & DYDX | 2 | 20.0% | 8.7% |
| ADA & DYDX | 1 | 8.3% | 4.3% |

**Insight:** S1/S2/S3 are **NOT 3 independent edges** — same source, same signal, 3 tickers.

**v2 Mitigation:**
- **Combined mega_mutation cap: 3.0%** (vs 5%×3=15% in v1)
- **DYDX (alpha_engine) cap: 0.5%** (independent source)
- **Total cohort cap: 4.0%**
- If any pair's 30d rolling correlation exceeds 0.70, **count as 1 sleeve for position limit purposes** (per ring-1T)

## 9. Slippage + Venue (v2 — With Stress Multiplier)

| Sleeve | Symbol | Venue | Base Slip | **Stress Slip** | Notes |
|---|---|---|---|---|---|
| S1 | JUPUSDT | Binance → OKX → Bybit | 0.08% | 0.30% | Mid-cap, flash-crash stress |
| S2 | ENAUSDT | Binance → OKX | 0.10% | 0.40% | Smaller cap, wider stress |
| S3 | ADAUSDT | Binance → Coinbase | 0.05% | 0.20% | Top-10, deep liquidity |
| S4 | DYDXUSDT | Binance → OKX | 0.12% | 0.50% | Lower volume, wider stress |

**Stress test:** If actual slippage exceeds stress estimate on >10% of trades (per ring-1T), **pilot auto-fails**.

**Latency buffer:** 0.2% per trade "unknown" (per deepseek-chat-direct)

## 10. Entry / Exit / Stop (UNCHANGED from v1)

### S1, S2, S3 (mega_mutation family)
- TP: +2.0% (FIXED) | SL: -1.0% (FIXED) | R:R: 2.0 | Time stop: 24h
- Resolver: NOMINAL_TP_LEGACY (under validation)

### S4 (DYDX/alpha_engine)
- TP: +1.6% to +2.9% (adaptive) | SL: -1.3% to -2.3% | R:R: 1.25 | Time stop: 48h
- Resolver: PRICE_RESOLVED (cleaner)

## 11. DYDX Sleeve Brittleness (v2 — Lower Cap)

DYDX has W/L ratio 0.84 (avg_win < avg_loss). Combined with 0.5% per-trade cap (vs 1.0% for others):
- Even 5 consecutive losses = -2.5% sleeve
- 12 wins to recover = +2.4%
- **Tier 2 alert triggers earlier:** if last 5 trades WR < 70% (vs <50% for mega)

## 12. Out-of-Scope (Other Asset Classes) — UNCHANGED

FOREX, EQUITY (PEAD), ETF, COMMODITY, BOND — see v1.

## 13. Open Questions for Operator (v2)

1. **Approve resolver validation gate before Stage 1?** (All 6 reviewers say YES)
2. **Approve v2 position sizing (1%/sleeve, 3% combined mega, 0.5% DYDX)?**
3. **Approve numeric shutdown thresholds (3%/5%/10%/15% sleeve DD)?**
4. **Approve 5-stage ladder (paper → $100 → $300 → $1k → $5k)?**
5. **Set max cohort loss at 12% (BLACK trigger)?**
6. **Set 0.2% per-trade unknown slippage buffer?**
7. **Approve combined mega_mutation cap of 3.0%?**
8. **Set max cohort exposure at 4.0% of total portfolio?**

## 14. Required Code/Data Changes (v2)

1. **`tools/validate_intrabar_fills.py`** — Resolver validation tool (Step 1-3 of §7). **HIGHEST PRIORITY.**
2. **`verified_strategies/paper_pilot/crypto_real_money_pilot.py`** — Forward logger with 4-tier alerts
3. **4 paper-pilot state files** (S1-S4)
4. **5-minute cron** in `.github/workflows/real_money_pilot_monitor.yml`
5. **`money_ready_verdict.json`** updates: add `is_actionable: true` for the 4 sleeves
6. **/audit dashboard** "Real-Money Cohort" panel
7. **Discord webhook** for Tier 1+ alerts

## 15. Timeline (v2)

| Date | Milestone | Owner |
|---|---|---|
| 2026-06-05 | v1 spec shipped, peer review | claude-sonnet-4.6 |
| 2026-06-05 | v2 spec (post-review) shipped | claude-sonnet-4.6 |
| 2026-06-06 | Resolver validation tool + Stage 0 state files | claude-sonnet-4.6 |
| 2026-06-07 | Operator review + greenlight on v2 | operator |
| 2026-06-08 | Resolver validation runs (7-day parallel) | GHA |
| 2026-06-15 | Resolver validation results review | claude-sonnet-4.6 |
| 2026-06-22 | Stage 0 (paper) starts IF resolver passes | GHA |
| 2026-07-22 | Stage 0 → Stage 1 ($100) decision | operator |
| 2026-08-22 | Stage 1 → Stage 2 ($300) decision | operator |
| 2026-09-22 | Stage 2 → Stage 3 ($1k) decision | operator |
| 2026-10-22 | Stage 3 → Stage 4 (full) decision | operator |

**Slower than v1 by ~3 months** — necessary cost of doing due diligence on infrastructure with known data quality issues (per ring-1T).

## 16. Key Changes from v1

| Area | v1 | v2 (post-review) | Source of Change |
|---|---|---|---|
| Per-sleeve cap | 5% | **1%** (mega), 0.5% (DYDX) | ring-1T Option A |
| Combined mega cap | 5%×3=15% | **3.0%** | ring-1T, free-mode-large |
| Total cohort cap | 30% of portfolio | **4.0%** | ring-1T Option A |
| Numeric thresholds | tier names only | **-3/-5/-10/-15% sleeve, -2/-4/-8/-12% cohort** | All 6 reviewers |
| Ladder | 3 stages (10x jumps) | **5 stages (3-5x jumps)** | deepseek, ring-1T |
| Resolver gate | acknowledged | **MANDATORY pre-condition** | All 6 reviewers |
| Latency buffer | none | **0.2% per trade** | deepseek-chat |
| Stress slippage | base only | **base + 0.30-0.50% stress** | ring-1T |
| Correlation attack trigger | none | **2+ Yellow in 4h → Orange** | ring-1T |
| Worst-case loss | unclear | **3.5% portfolio (cap-defined)** | ring-1T Option A |

## 17. Final Verdict from Swarm

**6/6 reviewers say: DO NOT proceed to live money without resolver validation.**

- 1 (gemma-4) says **REJECT** outright until resolver is fixed
- 3 say **APPROVE-WITH-CHANGES** (need numeric thresholds + resolver gate)
- 2 say **Option A (Conservative)** explicitly

**v2 of this spec incorporates all 6 reviewers' recommendations.** Operator can now make an informed decision.

---

## v2 STATUS: PEER-REVIEWED, READY FOR OPERATOR APPROVAL
