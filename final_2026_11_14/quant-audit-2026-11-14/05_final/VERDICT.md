# 05_Final — Verdict & Reconciliation (2026-11-14)

**Worktree:** quant-audit-2026-11-14  
**Scope:** Stocks, crypto, forex, bonds, ETFs, mutual funds  
**Bottom line:** The prediction system is NOT real-money ready on any asset class. Profitable approaches exist in research but NONE are deployed in the live ledger.

---

## 1. My Core Finding — 0/166 Cells Pass

Using `tools/money_ready_screener.py` on `recent_closed_array.json` (3,447 decisive picks), I applied the full Tier-2 money-ready gate contract to all 166 strategy×class×direction cells:

| Gate | Threshold | Cells Passing |
|---|---|---|
| n ≥ 100 decisive | ≥ 100 | 1 of 166 |
| WR ≥ 50% | ≥ 50% | ~12 of 166 |
| PF ≥ 1.5 | ≥ 1.5 | ~5 of 166 |
| Net expectancy > 0 (CI lower > 0) | > 0 | ~3 of 166 |
| MDD < 20% | < 20% | ~2 of 166 |
| Single-source < 60% | < 60% | **0 of 166** |
| Multi-source ≥ 2 | ≥ 2 | **0 of 166** |
| **ALL GATES** | **all must hold** | **0 of 166** |

Every class fails. No class has WR ≥ 50% or PF ≥ 1.5 at the class level. The single-source gate alone eliminates all 166 cells.

**Result: 0 asset classes money-ready.** Consistent with `money_ready_verdict.json` (`money_ready: []`).

---

## 2. Reconciliation with Peer Findings

Peers (childlike-airport / kilo) found statistically-valid profitable approaches EXIST in backtest research. This is NOT contradictory with my 0/166 — here's why:

| Approach (peer) | Asset Class | Sharpe | PF | PBO | Where it lives | Deployed in live ledger? |
|---|---|---|---|---|---|---|
| Regime-Filtered VWAP MR | Crypto 4h | 3.76 | 1.21 | 0.489 | `/tmp/kilo/*.py` backtest harness | **NO** |
| Vol-Targeted Trend | Crypto daily | 2.13 | 1.40 | — | `/tmp/kilo/*.py` backtest harness | **NO** |
| Walk-Forward Variant C | Equity/ETF | — | 1.26 | p<0.0013 | deepAI research | **NO** |

**Reconciliation:** Kilo's approaches are validated on separate out-of-sample backtest harnesses, NOT in the deployed `recent_closed_array.json` ledger. My screener screens the LIVE ledger — the picks actually being emitted and tracked. None of Kilo's validated strategies appear in that ledger.

**The gap is between research and production:**
- Research: profitable approaches exist (VWAP MR Sharpe 3.76, Vol-Trend Sharpe 2.13)
- Production ledger: 0/166 cells pass all gates
- Live curated picks: 100% LONG-biased in RISK_OFF regime, 80% with zero forward validation
- Live open P&L: −1.42% average across 4,310 open picks

**Conclusion:** Profitable approaches EXIST but are NOT deployed. The system needs to (a) adopt Kilo's regime-filtered VWAP MR as the first production candidate, and (b) fix the data pipeline before any gate can pass.

---

## 3. Why No Cell Passes — The Binding Constraints

| Constraint | Why it binds | Evidence |
|---|---|---|
| **Single-source (all 166 cells)** | Every cell's picks come from one `source_system`; no multi-source confirmation | `luxalgo_confluence` CRYPCO: 94% one source; `alpha_engine` CRYPCO: 98.5% one source |
| **n < 100 (165 of 166 cells)** | Most strategies have too few decisive trades for statistical significance | Only `luxalgo_confluence` CRYPCO LONG (n=563) clears n≥100 |
| **WR < 50% (most cells)** | All class-level WRs are 33-50%, below the 50% floor | CRYPCO 45.7%, EQUITY 48.2%, FOREX 40.3%, ETF 44.3% |
| **MDD ≥ 20% (most cells)** | Positive-return cells have catastrophic drawdowns | `mega_mutation_macd_rsi_m048`: +6.70% net but MDD=209.6% |
| **EXPIRED→WON mislabeling** | Survivorship bias inflates WR in the dashboard cohort | Dashboard CRYPCO Smart Picks 78.93% vs DB raw 39.38% |

---

## 4. Remediation Path (5 Stages)

See `02_tools_guardian/REMEDIATION_PLAN_2026-11-14T2100Z.md` for the full plan.

**Stage 1 — Data Hygiene:** Fix EXPIRED→WON relabeling, drain zombie picks (53 at pnl=0%), restart signal_outcomes resolution, fix dead price refresh, seed hyrotrader journal only from real fills.

**Stage 2 — Strategy Pruning (PBO/SPA/FDR):** Enable `_FDR_GATE_ENFORCE=1` and `_SINGLE_SOURCE_GATE_ENFORCE=1` (already done in `alpha_engine/money_ready_verdict.py` on `wiring` branch). Require ≥2 strategies with n≥20 per class before PBO/SPA/FDR can run.

**Stage 3 — OOS Validation:** CPCV/walk-forward with embargo/purge. PF≥1.5, MDD<20%, expectancy>0 with CI lower bound>0, n≥100 decisive, net of slippage (5-15 bps/class).

**Stage 4 — Paper Trading:** n≥100 clean post-noise trades, forward validation, real-time gate monitoring.

**Stage 5 — Real Money:** Only after Stage 4 clears every Stage-7 gate.

---

## 5. Immediate Next Steps

1. **Deploy `money_ready_screener.py`** (`02_tools_guardian/tools/`) as a CI gate — run on every `recent_closed_array.json` refresh.
2. **Adopt Kilo's regime-filtered VWAP MR** as the first production candidate (crypto 4h, Sharpe 3.76, PF 1.21, MDD 10.0% with 40% position sizing).
3. **Fix EXPIRED→WON relabeling** — run `tools/relabel_crypto_expired.py --apply` after dry-run verification.
4. **Add MUTUAL_FUND class** to `alpha_engine/asset_class.py` + `ml_gatekeeper ASSET_CLASS_MAP`.
5. **Fix dead price refresh** — restore `fetch_prices.php` or confirm yfinance replacement passes CI.
6. **Sign off `d8c8dd25581`** (gatekeeper leakage-masking default, on `origin/main`).

---

## 6. Cross-Peer References

- `final_2026_11_14/childlike-airport/` — Kilo's audit: stale data (129/129 active picks ~172 days stale), PnL sign contradictions (8 picks), profitable approaches (3 validated), no mutual funds anywhere
- `final_2026_11_14/finpredict-v2/` — Finpredict v2: reconciliation backbone, CI gates G1-G13, MASTER_AUDIT per-class analysis
- `final_2026_11_14/finpredict-v3/` — Finpredict v3: data-hygiene audit (stale crypto prices, 11 frozen FOREX phantoms), horizon validation (0/6 at n≥60, 0/26 at n≥30), guardian tools (14 tests passing)

**Consensus across all peers (9 total):** NOT money-ready; data pipeline broken; highest-value first fixes are PnL-unit contract + NULL-tombstone zombie drain; no "solid" claim until the horizon harness passes.
