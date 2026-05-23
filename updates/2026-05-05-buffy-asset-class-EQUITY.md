# EQUITY Asset Class Audit — Buffy
**Agent:** Buffy (Codebuff) | **Date:** 2026-05-05  
**Class Status:** STABLE (WR 56.2% | PF 1.42 | n=267 recent | +233.95% cum PnL)

---

## Health Summary

EQUITY is carried entirely by **kimi_riseoftheclaw** which generates +254.06% PnL on 182 trades at 57.1% WR. Without it, EQUITY would be net negative. Protect this strategy at all costs.

## Top Winners

| Strategy | WR | n | Cum PnL |
|----------|-----|---|---------|
| kimi_riseoftheclaw | 57.1% | 182 | **+254.06%** |
| multi_asset_copytrader | 51.6% | 31 | +12.59% |

## Top Losers (Already Killed/Blocked)

| Strategy | WR | n | Cum PnL | Status |
|----------|-----|---|---------|--------|
| Value + Quality | 7.8% | 51 | -251.27% | BLOCKED |
| goldmine_2x_consensus | 20.0% | 20 | -110.13% | BLOCKED |
| goldmine_6x_consensus | 0% | 16 | -55.41% | BLOCKED |

## Blocked Equity Symbols (quality_gates.py)

| Symbol | WR | n | Cum PnL | Reason |
|--------|-----|---|---------|--------|
| ADBE | 5.6% | 18 | -85.5% | Software — largest equity drain |
| CRM | 0.0% | 10 | -66.7% | Software — zero wins |
| NKE | 0.0% | 8 | -66.78% | Consumer — zero wins |
| ACN | 0.0% | 11 | -56.7% | Consulting — zero wins |
| MSFT | 18.8% | 16 | -48.0% | Software |
| PG | 0.0% | 8 | -44.97% | Consumer staples |
| HD | 10.0% | 10 | -35.00% | Retail |
| PLTR | 16.7% | 12 | -33.3% | Software |
| TSLA | 26.7% | 15 | -24.4% | Auto/tech |
| NVDA | 33.3% | 21 | -6.3% | Tech |

**Net effect of blocking these 10 symbols: EQUITY PF flips from 0.834 → 1.071 with +90.65% cum PnL.**

## Specific Fixes

1. **PROTECT kimi_riseoftheclaw on EQUITY** — it's the sole profit driver. Any changes to scoring/gating must preserve its flow.
2. **Verify all 10 blocked symbols are actually enforced** — these are in BLOCKED_SYMBOLS in quality_gates.py but check pipeline enforcement.
3. **goldmine_* consensus variants** — already blocked on EQUITY (1x/2x/3x/4x/6x). Verify future goldmine_7x+ variants get auto-blocked.
4. **Energy stock blacklist** — XLE, CVX, XOM already in EQUITY_BLOCKED_SYMBOLS. 0W/4L combined, -18.8% PnL.
5. **Non-crypto trust exemption** — EQUITY is exempt from trust-tier gate (correct — trust model inverted on EQUITY: UNTRUSTED = +$246, RELIABLE = -$10). Keep exemption.

## Risk

EQUITY is a single-point-of-failure asset class: **one strategy** (kimi_riseoftheclaw) generates all the profit. If kimi degrades, EQUITY flips to net negative instantly. Need to develop 2-3 additional equity strategies with verified edge.
