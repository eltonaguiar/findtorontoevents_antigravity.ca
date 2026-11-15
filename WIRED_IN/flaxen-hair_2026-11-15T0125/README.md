# WIRED_IN — flaxen-hair_2026-11-15T0125

**Worktree:** flaxen-hair_2026-11-15T0125 | **Date:** 2026-11-15T01:25Z | **Repo:** findtorontoevents_antigravity.ca

This folder contains the complete AI machine learning algorithm audit and fix proposals across all asset classes, including:

- Per-asset-class algorithm specifications and justifications
- Backtest results across 10 symbols and 6 strategies (42 combinations)
- Forward-test pick generator with QA gates (5 picks emitted)
- Per-column accuracy verification (PnL normalization, pick ID uniqueness)
- Mutual funds coverage gap analysis
- Forex/crypto/commodity/bonds elimination reasoning
- TradingView contest winner analysis (and why they don't transfer)
- The irony resolution: picks vs "no asset class proven profitable"
- Company turnaround case studies (Renaissance, Two Sigma, AQR, Bridgewater, Citadel)
- Key metrics from multiple perspectives (Sharpe, pro investor, mutual fund manager, bank trader)

---

## Folder Structure

| Folder | Contents |
|--------|----------|
| `01_specification/` | Per-asset-class algorithm specifications (equity, crypto, ETF, bonds/commodities/futures, mutual funds) |
| `02_justification/` | Per-asset-class pick justification docs |
| `03_backtest_results/` | Backtest results JSON and forward-test execution plan |
| `04_elimination_reasoning/` | Why other asset classes were eliminated (forex, crypto, commodity, bond, futures, mutual funds, prediction markets) |
| `05_irony_resolution/` | The irony: picks vs "no asset class proven profitable" — resolved |
| `06_peer_review/` | Peer review coordination (placeholder) |

---

## Bottom Line

**No asset class is proven profitable.** 0/23 hypotheses across 4 protocol versions survived clean out-of-sample, effective-N, capital, and execution gates. All 9 classes return `sizing_allowed: false`.

**Only ETF Tactical Asset Allocation (TAA) shows risk-adjusted value:**
- Sharpe 0.88 vs SPY 0.74, MaxDD −19% vs SPY −51%, Calmar 0.48 vs 0.21
- Validated 2007-2026 including 2008 GFC
- Smart-beta (better risk-adjusted return, NOT alpha)

**EQUITY** is the only class with positive cost margin (3.23×, mean +0.323%, n=738) but not statistically significant (t=1.52, p=0.12).

**CRYPTO** is conditional — fill bug (`kimi_riseoftheclaw`) must be fixed first, then forward-test n≥100.

**Mutual funds** — zero coverage, not a prediction class. Hold low-cost index mutual funds as core allocation instead.

**Do not deploy capital.** All 5 picks are PAPER TESTS ONLY.

---

## The 5 Forward-Test Picks (Paper Tests Only)

| # | Symbol | Strategy | Direction | Entry | TP | SL | R:R | Backtest PF | Backtest WR |
|---|--------|----------|-----------|-------|-----|-----|-----|-------------|-------------|
| 1 | SPY | connors_rsi2 | LONG | 450.00 | 463.50 | 441.00 | 1.5 | 76.92 | 83.3% |
| 2 | XLF | keltner_compression_v2 | LONG | 42.00 | 43.26 | 41.16 | 1.5 | 10.00 | 100.0% |
| 3 | GLD | ema_stack | LONG | 2650.00 | 2729.50 | 2597.00 | 1.5 | 4.51 | 80.0% |
| 4 | GLD | funding_sentiment | LONG | 2650.00 | 2729.50 | 2597.00 | 1.5 | 4.15 | 83.3% |
| 5 | SPY | funding_sentiment | LONG | 450.00 | 463.50 | 441.00 | 1.5 | 3.09 | 83.3% |

**All 5 picks have n < 10 trades — statistically insignificant. Do not allocate capital.**

### Go/No-Go Criteria for Live Capital

| Criterion | Threshold | Status |
|-----------|-----------|--------|
| n ≥ 100 forward picks | Not met (n=5) | ❌ |
| PF ≥ 1.5 forward | Not met | ❌ |
| WR ≥ 55% forward | Not met | ❌ |
| DSR ≥ 0.95 forward | Not met | ❌ |
| 3+ months clean forward | Not met | ❌ |

**Decision: NO-GO for live capital deployment.**

---

## Key Documents

| File | Description |
|------|-------------|
| `01_specification/equity_asset_class.md` | Equity spec: Connors RSI2, VIX spike reversal, only class with positive cost margin |
| `01_specification/crypto_asset_class.md` | Crypto spec: 700+ strategies, all fail clean-cohort screen, entry_price 29% clean |
| `01_specification/mutual_funds_asset_class.md` | Mutual funds: zero coverage, not a prediction class |
| `01_specification/other_asset_classes.md` | Forex, commodity, bond, futures — all blocked |
| `02_justification/FORWARD_TEST_EXECUTION_PLAN.md` | Forward-test pick generation and QA gates |
| `02_justification/HOLDING_PERIOD_TRADING_STYLE_ANALYSIS.md` | Per-class analysis by holding period vs trading style |
| `03_backtest_results/backtest_results.json` | 42 strategy-symbol combinations tested |
| `03_backtest_results/BACKTEST_AND_TRACKING_PROTOCOL.md` | Kill-fast vs hold-longer tracking protocol |
| `04_elimination_reasoning/PREDICTION_MARKETS_WHY_NO_WINNERS.md` | Why Kalshi/Polymarket copy trading fails |
| `04_elimination_reasoning/SUBQ_USAGE_GUIDE.md` | SubQ API key usage and fact-checking protocol |
| `04_elimination_reasoning/MUTUAL_FUNDS_QUICK_WINS.md` | Mutual funds coverage gap analysis |
| `05_irony_resolution/IRONY_RESOLUTION.md` | The irony: picks vs "no asset class proven profitable" — resolved |
| `05_irony_resolution/EXECUTION_ROADMAP.md` | 90-day execution roadmap |
| `05_irony_resolution/SUMMARY_RECOMMENDATIONS.md` | Summary recommendations |

---

## Quick Start

```bash
# Generate new forward-test picks
python quick_wins/shared/forward_test_pick_generator.py --generate --output both

# Run QA validation on all picks
python quick_wins/shared/forward_test_pick_generator.py --qa-check

# Expire stale open picks (>72h)
python quick_wins/shared/forward_test_pick_generator.py --expire-stale
```

**Read before trading:** All picks are PAPER TESTS ONLY. No capital deployment until n ≥ 100 forward picks with PF ≥ 1.5, WR ≥ 55%, DSR ≥ 0.95.
