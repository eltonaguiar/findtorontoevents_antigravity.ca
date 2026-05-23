# 6-GATES VALIDATION — V1 FREEBUFF REPORT
## Real Picks Analysis · Date: 2026-05-21 · Author: Freebuff (Buffy)

---

## TABLE OF CONTENTS
1. Executive Summary
2. The 8 Statistical Gates (Implemented)
3. Data Overview — Resolved Picks
4. CRITICAL FINDING: Asset Class Misclassification
5. True Per-Asset-Class Picture
6. Gate-by-Gate Assessment Per Asset Class
7. Symbols That Pass Per Asset Class
8. Root Cause Analysis — Where the Bug Lives
9. Recommendations & Action Items
10. Appendix: Methodological Notes

---

## 1. Executive Summary

**The 6-gate (actually 8-gate) validation framework was run against 5,000 real resolved picks from the audit pipeline.** The framework detects statistically significant edge — 16/27 strategies with ≥20 trades pass BH-FDR, and 6/27 pass ALL 8 gates.

**However, a critical data quality bug was discovered: 90.8% of "EQUITY" picks are actually CRYPTO.** Eight native crypto pairs (ETH-USD, DOGE-USD, BTC-USD, etc.) are tagged with `asset_class: "EQUITY"` due to a missing `asset_class` field in the source emitter, which triggers a hardcoded `"EQUITY"` default in the dashboard generator.

**The actual EQUITY asset class has only 20 resolved picks across 11 symbols** — far too few for meaningful 6-gate validation. All per-asset-class conclusions drawn from the "EQUITY" slice are invalid.

---

## 2. The 8 Statistical Gates (as implemented)

| # | Gate | Definition | Current Threshold |
|---|------|-----------|-------------------|
| G1 | Sharpe Ratio | Annualized Sharpe of per-trade returns | ≥ 1.0 |
| G2 | Bootstrap P-Value | Edge is statistically significant vs zero | p < 0.05 |
| G3 | Bootstrap CI Lower | 95% confidence interval lower bound > 0 | Lower bound > 0 |
| G4 | Walk-Forward Consistency | % of out-of-sample windows with positive Sharpe | ≥ 50% |
| G5 | Monte Carlo Bootstrap | Strategy beats its own scrambled noise distribution | 5th pctile Sharpe > 0 |
| G6 | Monte Carlo Crash | Strategy survives a -10% crash day insertion | ≥ -2.0 Sharpe |
| G7 | Win Rate | Simple trade win rate | > 40% |
| G8 | Profit Factor | Gross wins / Gross losses | > 1.0 |

Source: `tools/kimi_research_2026_05_20/six_gate_validated_strategy.py` (G1–G6)  
G7–G8 from `tools/validate_resolved_picks.py`

---

## 3. Data Overview — Resolved Picks

### Source: `audit_trail/data/universal_resolved_picks.json`

| Metric | Value |
|--------|-------|
| Total resolved picks | **5,000** |
| Unique strategies | **270** |
| Strategies with ≥20 trades | **27** |
| BH-FDR significant (strategies) | **16/27 (59%)** |
| Passed 6+/8 gates | **11/27 (41%)** |
| Passed ALL 8 gates | **6/27 (22%)** |
| Negative edge (proven losers) | **5/27 (19%)** |

### Asset Class Breakdown (as currently tagged):

| Asset Class | Picks | % of Total |
|-------------|------:|-----------:|
| CRYPTO | 4,682 | **93.6%** |
| EQUITY | 218 | **4.4%** |
| FOREX | 68 | **1.4%** |
| MEMECOIN | 31 | **0.6%** |

---

## 4. ⚠️ CRITICAL FINDING: Asset Class Misclassification

### What's Wrong

**Of the 218 picks tagged as EQUITY, 198 (90.8%) are actually CRYPTO pairs.**

These are NOT crypto ETFs. They are native cryptocurrency spot pairs following the Yahoo Finance naming convention `BASE-USD` (e.g., BTC-USD = Bitcoin priced in US dollars). Real crypto ETFs would have tickers like:
- **BITO** (ProShares Bitcoin Strategy ETF)
- **IBIT** (iShares Bitcoin Trust)
- **FBTC** (Fidelity Wise Origin Bitcoin Fund)
- **GBTC** (Grayscale Bitcoin Trust)
- **EETH** (ETHA — Ethereum Strategy ETF)

### Misclassified Symbols

| Symbol | What It Actually Is | Tagged As | Picks |
|--------|--------------------|-----------|:----:|
| ETH-USD | Ethereum (native crypto) | EQUITY | 36 |
| BTC-USD | Bitcoin (native crypto) | EQUITY | 29 |
| DOGE-USD | Dogecoin (native crypto) | EQUITY | 29 |
| LINK-USD | Chainlink (native crypto) | EQUITY | 23 |
| SOL-USD | Solana (native crypto) | EQUITY | 22 |
| AVAX-USD | Avalanche (native crypto) | EQUITY | 22 |
| XRP-USD | XRP (native crypto) | EQUITY | 20 |
| ADA-USD | Cardano (native crypto) | EQUITY | 17 |
| **Total misclassified** | | | **198** |

### Correctly Classified (Real EQUITY)

| Symbol | Company | Source | Picks |
|--------|---------|--------|:----:|
| RIOT | Riot Platforms | stocks_competition, stocksunify2 | 2 |
| AMZN | Amazon | stocksunify2 | 2 |
| AMD | AMD | stocksunify2 | 2 |
| UNH | UnitedHealth | stocksunify2 | 2 |
| GOOGL | Alphabet | stocksunify2 | 2 |
| AVGO | Broadcom | stocksunify2 | 2 |
| CAT | Caterpillar | stocksunify2 | 2 |
| LRCX | Lam Research | stocksunify2 | 2 |
| MSTR | MicroStrategy | stocksunify2 | 1 |
| JNJ | Johnson & Johnson | stocksunify2 | 1 |
| AFRM | Affirm | stocksunify2 | 1 |
| COIN | Coinbase | stocksunify2 | 1 |
| **Total real EQUITY** | | | **20** |

### Source Systems Breakdown

| Source System | What It Emits | Tagged As | Correct? |
|--------------|--------------|-----------|:--------:|
| `signal_validation` | Crypto pairs (ETH-USD, BTC-USD…) | **EQUITY** | ❌ Wrong |
| `stocks_competition` | Crypto + few stocks | **EQUITY** | ❌ Mostly wrong |
| `stocksunify2` | Real US equities | **EQUITY** | ✅ Correct |

---

## 5. True Per-Asset-Class Picture

After reclassifying the misidentified picks, the real breakdown is:

| Asset Class | Picks | Source Systems | Data Quality |
|-------------|:----:|---------------|:------------:|
| **CRYPTO** | **4,880** | multi_asset_copytrader, claude_gainer, kimi_riseoftheclaw, ml_crypto_predictor, signal_validation, aggregated_picks, genome/evolver, alpha_engine | **✅ Rich** — 53 strategies with ≥10 trades |
| **FOREX** | **68** | signal_validation, kimi_signal_tracking | **⚠️ Sparse** — 2 strategies with ≥10 trades |
| **MEMECOIN** | **31** | meme_scanner, copy_trader | **❌ Insufficient** — no strategy has 20 trades |
| **EQUITY (real)** | **20** | stocksunify2 | **❌ Insufficient** — no strategy has 10 trades |

### Impact on Previous Analysis

**ALL per-asset-class conclusions in `reports/VALIDATION_REAL_DATA_2026-05-21.md` for EQUITY are invalid** because the data was 90.8% crypto. The "EQUITY WR=67% PF=59" numbers reported for `AuditEnsemble_LONG` etc. are actually crypto performance being attributed to the wrong asset class.

---

## 6. Gate-by-Gate Assessment Per Asset Class

### CRYPTO (4,880 picks, 53 validatable strategies)

| Gate | Pass Rate | Assessment |
|------|:---------:|-----------|
| G1: Sharpe ≥ 1.0 | ~60% | ✅ Appropriate — HFT naturally high Sharpe |
| G2: Bootstrap p < 0.05 | ~70% | ✅ Appropriate |
| G3: CI lower > 0 | ~65% | ✅ Appropriate |
| G4: Walk-forward ≥ 50% | **22%** | ⚠️ Hardest gate — only 6/27 pass. Valid for CRYPTO. |
| G5: MC Bootstrap | **100% pass** | ❌ **Too easy** — passes everything. Need tighter threshold. |
| G6: MC Crash | **100% pass** | ❌ **Too easy** — passes everything. Need tighter threshold. |
| G7: WR > 40% | ~85% | ✅ Appropriate |
| G8: PF > 1.0 | ~80% | ✅ Appropriate |

### FOREX (68 picks, 2 strategies with ≥10 trades)

| Gate | Assessment |
|------|-----------|
| G1: Sharpe ≥ 1.0 | ⚠️ Too strict — forex edges are smaller, more consistent. Suggestion: ≥ 0.5 |
| G2: Bootstrap p < 0.05 | ✅ Appropriate (statistically sound) |
| G4: Walk-forward | ❌ Can't run — needs ≥42 trades for minimum 4 windows |
| G5/G6: MC | ✅ Can run but 2 strategies insufficient |
| G7: WR > 40% | ✅ Appropriate |
| G8: PF > 1.0 | ⚠️ Suggestion: ≥ 0.8 for forex (tighter spreads, lower fees) |

### EQUITY (20 picks, 0 validatable strategies)

**Insufficient data for ANY gate validation.** Need 100+ resolved equity picks minimum before any 6-gate analysis is meaningful.

### MEMECOIN (31 picks, 0 validatable strategies)

Same as EQUITY — insufficient data.

---

## 7. Symbols That Pass Per Asset Class (True Classification)

### CRYPTO — ✅ Strong Pass (>60% WR, ≥10 trades, positive avg PnL)

| Symbol | Trades | Win Rate | Avg PnL | Passes Basic Gates |
|--------|:-----:|:--------:|:-------:|:------------------:|
| ENJ-USD | 68 | **100.0%** | +3.50% | ✅ Yes |
| TRX-USD | 66 | **100.0%** | +3.21% | ✅ Yes |
| ALGO-USD | 37 | **100.0%** | +3.49% | ✅ Yes |
| THETA-USD | 33 | **100.0%** | +3.50% | ✅ Yes |
| INJ-USD | 30 | **100.0%** | +3.50% | ✅ Yes |
| ONDO-USD | 21 | **100.0%** | +3.31% | ✅ Yes |
| **BTCUSDT** | **306** | **77.5%** | +2.15% | ✅ Yes |
| APTUSDT | 159 | 72.3% | +1.51% | ✅ Yes |
| CHZ-USD | 40 | 67.5% | +1.51% | ✅ Yes |
| WLDUSDT | 86 | 67.4% | +1.40% | ✅ Yes |
| SEIUSDT | 100 | 65.0% | +1.16% | ✅ Yes |
| GALAUSDT | 5 | 60.0% | +1.20% | ⚠️ Borderline |

### CRYPTO — ❌ Fail (≤40% WR)

| Symbol | Trades | Win Rate | Avg PnL |
|--------|:-----:|:--------:|:-------:|
| LINKUSDT | 80 | **38.8%** | +0.15% |
| SUIUSDT | 104 | **37.5%** | +0.05% |
| HYPEUSDT | 96 | **37.5%** | +0.24% |
| DOGEUSDT | 82 | 37.8% | +0.28% |
| DOTUSDT | 86 | 33.7% | +0.03% |

### FOREX — ⚠️ Low Confidence (too few trades)

| Symbol | Trades | Win Rate | Avg PnL |
|--------|:-----:|:--------:|:-------:|
| AUD-USD | 11 | 63.6% | +1.20% |
| EUR-USD | 15 | 46.7% | +0.14% |
| GBP-USD | 14 | 42.9% | +0.29% |
| USD-JPY | 17 | **0.0%** | 0.00% |
| USD-CHF | 11 | **0.0%** | 0.00% |

### EQUITY (Real) — ❌ Insufficient Data

Only 20 picks total across 11 symbols. No strategy has ≥5 trades. Need more real equity picks from `stocksunify2` or other sources.

### MEMECOIN — ❌ Insufficient Data

31 picks (DOGEUSDT, BONKUSDT). DOGEUSDT borderline (20 trades, 40% WR, +0.65%).

---

## 8. Root Cause Analysis — Where the Bug Lives

### The Chain of Misclassification

```
signal_tracker.py (source emitter)
  └─ writes signals_database.json
      └─ NO asset_class field set — field is missing/empty
          └─ universal_pick_resolver.py reads into at_raw_picks
              └─ dashboard_generator.py line 8282:
                  if not p.get("asset_class"):
                      p["asset_class"] = "EQUITY"    ← HARDCODED DEFAULT
```

**Root Cause:** The `signal_tracker.py` emitter writes crypto symbols (ETH-USD, BTC-USD, etc.) into `signals_database.json` without setting `asset_class`. When the dashboard generator encounters picks with missing `asset_class`, it defaults them to `"EQUITY"`.

**Secondary Contributor:** `quality_gates.py` line 5598 has an explicit override that gives `signal_validation` picks tagged as EQUITY a +10 score bonus, cementing the incorrect classification into the scoring system.

**Evidence that the misclassification was known but not fixed:**
- `tools/weekly_filter_picks.py` line 32: `"signal_validation": {"classes": ["CRYPTO", "FOREX"]}` — correctly identifies signal_validation as emitting CRYPTO and FOREX only
- `tmp_scrub_fake_forex.py` lines 31-32: references `signal_validation` as a known sandbox testing source
- The system has a fix available (`_CAT_TO_ASSET_CLASS` map in `multi_asset/scanner.py`) but it's not applied to the `signal_validation` source

### Bug Taxonomy

| ID | Bug | Location | Impact |
|----|-----|----------|--------|
| B1 | Missing asset_class in source emitter | `signal_tracker.py` | 198/218 EQUITY picks misclassified |
| B2 | Hardcoded EQUITY fallback masks missing data | `dashboard_generator.py:8282` | Prevents detection of the gap |
| B3 | Score bonus cements incorrect classification | `quality_gates.py:5598` | Inflates EQUITY metrics with crypto data |
| B4 | `stocks_competition` also misclassifies DOGE-USD | `STOCKS/competition/` emitter | 9 additional misclassifications |

---

## 9. Recommendations & Action Items

### P0 — Fix the Misclassification (Immediate)

1. **Fix `signal_tracker.py`** to set `asset_class: "CRYPTO"` for these symbols
2. **Patch `dashboard_generator.py:8282`** — change the fallback to `"UNKNOWN"` instead of `"EQUITY"` to make missing classifications visible
3. **Backfill** the misclassified 198 picks in `at_raw_picks` or `universal_resolved_picks.json`
4. **Add a validation gate** — if a symbol contains `-USD` and is not a real stock symbol (AAPL, MSFT, etc.), reject the EQUITY classification

### P1 — Gate Threshold Tuning

1. **Tighten MC Bootstrap (G5)**: Raise threshold from `5th pctile > 0` to `5th pctile > 0.5` or use the new bootstrap-vs-crash-scenario approach
2. **Tighten MC Crash (G6)**: Currently passes 100% — needs a harder crash scenario or higher Sharpe requirement
3. **Lower Sharpe for FOREX (G1)**: Use ≥ 0.5 instead of ≥ 1.0 for forex strategies
4. **Lower PF for FOREX (G8)**: Use ≥ 0.8 instead of ≥ 1.0

### P2 — Data Pipeline Improvements

1. **Route more real EQUITY picks** through the resolver — `stocksunify2` only produces ~20 closed picks. Need to scale a properly-classified equity source.
2. **Fix FOREX data scarcity** — only 68 resolved FOREX picks is insufficient for 6-gate validation
3. **Add asset_class validation** to the `collect_all_picks()` step — verify that symbols match their declared asset class before ingestion

### P3 — Validation Improvements

1. **Re-run the 6-gate validation** after fixing the misclassification to get true per-class results
2. **Build daily PnL series** for realistic Sharpe values (currently using per-trade annualization which inflates Sharpe)
3. **Add symbol-level asset_class verification** — a BI tool or CI check that flags mismatches

---

## 10. Appendix: Methodological Notes

### How the 6-Gate Framework Works

The validation framework (`tools/validate_resolved_picks.py`) reads resolved picks from `audit_trail/data/universal_resolved_picks.json`, groups them by strategy + asset class, and runs each group through the 8 gates.

**Per-trade Sharpe inflation:** Sharpe is computed as `mean(pnl_pct) / std(pnl_pct) * sqrt(annual_trades)`. For CRYPTO strategies doing hundreds of trades per year, this produces Sharpe values of 10+ — which means the "annualized Sharpe" is really "per-trade Sharpe projected to 1 year assuming same performance." This is not a daily-returns Sharpe and should not be compared to common benchmarks (e.g., "Sharpe > 2 is exceptional").

### Data Sources

| File | Records | Purpose |
|------|---------|---------|
| `audit_trail/data/universal_resolved_picks.json` | 5,000 | Primary input for validation |
| `audit_trail/data/at_raw_picks` (MySQL) | ~146k | Full source ledger |
| `signals_database.json` | Live | signal_validation emitter output |
| `STOCKS/competition/forward_picks.json` | Live | stocks_competition emitter output |

### Tools Used

- `tools/validate_resolved_picks.py` — Main 6-gate validation runner
- `tools/kimi_research_2026_05_20/six_gate_validated_strategy.py` — Gate 1-6 implementation (Gates 4/5 have been patched with improvements)
- `tools/kimi_research_2026_05_20/statistical_validation_framework.py` — Statistical testing framework

---

*Generated by Freebuff (Buffy) on 2026-05-21. Contact: Codebuff CLI tool.*
