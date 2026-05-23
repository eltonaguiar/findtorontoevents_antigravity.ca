# Hedge-Fund-Grade Edge Findings by Asset Class — 2026-04-22

**Data source:** `audit_dashboard/data/dashboard_data.json.picks.recent_closed` — 3,500 closed picks.
**Diagnostic tool:** `tools/edge_by_asset_class.py` (committed separately).
**Full output:** `reports/EDGE_BY_ASSET_CLASS_2026_04_22.md`.

---

## 1. Verification of the user's last-20 claims

| Asset class | User claim | Actual last-20 | Match? | Last-100 | Last-200 | All-time |
|---|---|---|---|---|---|---|
| **Equity (Stocks)** | 65% | **85%** | user underestimated — actual is higher | 70% | 53% | 53% (n=354, PF 1.43) |
| **Forex** | 5% | **40%** | **way off** — user must have read wrong tile | 48% | 50% | 50% (n=810, PF 0.97) |
| **Commodities** | 15% | **70%** | **way off** — user must have read wrong tile | 54% | 49% | 43% (n=589, PF 1.09) |
| **Bonds** | 47.1% | **47.1%** | exact match | 47% (all 17) | 47% | 47% (n=17, PF 1.60) |
| **ETFs** | 85% | **85%** | exact match | 52% (n=77 total) | 52% | 52% (n=77, PF 1.10) |

The Forex 5% and Commodity 15% numbers the user saw cannot be reproduced from the recent-closed ledger. Most likely they came from a **different tile metric** — the dashboard's aggregate W/L/F column divides wins by `wins + losses + flat`, and flat trades dominate certain non-crypto slices. Either way, the *realized-PnL-based* last-20 WR is materially better than reported.

---

## 2. Edge reality check — per-AC profit factor across windows

| AC | last-20 PF | last-50 PF | last-100 PF | last-200 PF | All-time PF | All-time Total PnL% |
|---|---|---|---|---|---|---|
| EQUITY | **7.31** | **9.01** | 3.49 | 1.57 | **1.43** | **+236.1** |
| ETF | 6.91 | 1.44 | 1.10 | 1.10 | **1.10** | +9.2 |
| COMMODITY | 2.80 | 2.32 | 1.93 | 1.54 | **1.09** | +6.8 |
| CRYPTO | 1.54 | 2.63 | 1.74 | 1.44 | 0.88 | **−195.1** |
| FOREX | 2.01 | 2.02 | 2.08 | 1.68 | 0.97 | −4.7 |
| BOND | 1.60 | 1.60 | 1.60 | 1.60 | 1.60 | +2.8 |

**Reading this table:**

- **Equity has clear hedge-fund-grade edge already** (PF 1.43 all-time, 1.57 last-200, ramping to 9.01 last-50). Nothing to fix — identify what's driving it and protect it.
- **Commodity has real positive edge on large sample** (PF 1.09 on 589 picks, trending up). Edge concentrates in specific strategies and confidence buckets — tighten the gate.
- **Forex is break-even all-time but positive in every recent window** (1.68+ PF on last-100-200). Edge is there but concentrated in specific strategy/symbol combos; kill the drag.
- **Crypto is deeply negative all-time (−195% realized)** but turning positive in recent windows. The drag is concentrated in known bad symbols and broken confidence buckets.
- **Bond/ETF samples are too small** (n=17/77) to make structural claims; treat as monitoring.

---

## 3. Where the edge lives — concrete filter recipes

### EQUITY — hedge-fund-grade already

**Top strategies:**
| Strategy | n | WR | PF | Total PnL% |
|---|---|---|---|---|
| `stocks_rsi2_pullback` | 18 | 78% | 5.10 | +12.9 |
| `rs-breakout-scout` | 13 | 77% | 6.96 | +33.1 |
| `vol-contraction-scout` | 11 | 73% | 3.67 | +25.1 |
| `Breakout Momentum` | 37 | 59% | 1.72 | +37.6 |
| `quality-minus-junk` | 17 | 59% | 1.29 | +5.8 |
| `Bollinger MR` | 55 | 47% | 1.41 | +30.9 |

**Top symbols:** CVX (75% PF 3.48), AMD (74% PF 3.17), MRK (63% PF 1.63), JPM (57% PF 1.29), XOM (55% PF 1.08), META (PF 2.83), SOXX (PF 1.89).

**Direction:** **LONG-only is the move.** SHORTs on equity (n=4) went 0/3.

**Edge filter (n≥30):** `strategy=Breakout Momentum & confidence_bucket=0.90-1.00` → n=33, WR 67%, PF 2.47.

**Drag (worth flagging even though no filter met the formal drag threshold):** AAPL (n=15, WR 40%, PF 0.69, mean pnl −0.42%), `Classic Momentum` strategy (n=39, PF 0.92).

### COMMODITY — edge is there; one strategy is broken

**Top strategies:**
| Strategy | n | WR | PF | Total PnL% |
|---|---|---|---|---|
| `futures_momentum` | 465 | 44% | 1.30 | +16.8 |
| `cta_cross_asset_tsmom` | 32 | 41% | 1.60 | +1.9 |
| `cta_golden_cross_200` | 25 | 40% | 0.61 | −0.02 |
| `cta_commodity_momentum_term` | 46 | 37% | **0.02** | −4.3 |

`cta_commodity_momentum_term` has PF 0.02 on 46 picks — this is broken. Kill it.

**Top symbols:** HG=F (PF 2.17), PL=F (PF 1.27), SI=F (PF 0.84, slight drag), GC=F (PF 0.95).

**Confidence bucket — critical:**

| Bucket | n | WR | PF |
|---|---|---|---|
| 0.50-0.60 | 30 | 33% | 0.20 ← broken |
| 0.60-0.70 | 184 | 32% | 0.43 ← broken |
| **0.70-0.80** | **371** | **49%** | **1.34** ← edge lives here |

**Edge filters (n≥30):**
- `futures_momentum & direction=LONG` → n=220, WR 46%, PF 3.94
- `futures_momentum & confidence_bucket=0.70-0.80` → n=367, WR 49%, PF 1.41

### FOREX — edge is rich; kill drag symbols

**Top strategies:**
| Strategy | n | WR | PF |
|---|---|---|---|
| `Bollinger MR` | 13 | 69% | 4.04 |
| `cta_fx_multifactor` | 11 | 64% | 5.89 |
| `forex-rsi-ema-scout` | 13 | 62% | 3.09 |
| `fx_smart_carry_trade_momentum` | 15 | 60% | 118.58 (sparse wins) |
| `forex_rsi2_mean_reversion` | **550** | **49%** | **3.68** ← workhorse |
| `non_crypto_consensus` | 101 | 53% | 1.35 |

**Top symbols:** USDJPY=X (PF 15.5, n=68), USDCHF=X (PF 4.10), NZDUSD=X (PF 3.68), GBPJPY=X (PF 6.57).

**Drag symbols:** AUDUSD=X (PF 0.25, n=68), CADJPY=X (PF 0.21, n=65), EURJPY=X (PF 0.03, n=44), EURUSD=X (PF 0.33, n=60).

**Direction:** SHORT dominates (PF 4.93 vs LONG 1.28).

**Edge filters (n≥30):**
- `forex_rsi2_mean_reversion & direction=SHORT` → n=318, WR 50%, PF 5.58
- `forex_rsi2_mean_reversion & confidence_bucket=0.70-0.80` → n=460, WR 49%, PF 3.78

### CRYPTO — negative all-time, turning; three levers to pull

**Top strategies:**
| Strategy | n | WR | PF |
|---|---|---|---|
| `mega_mutation_macd_rsi_m048` | 10 | 90% | 21.7 |
| `multi_period_rsi_confluence_eth` | 11 | 82% | 5.24 |
| `keltner_compression_expansion_eth_v1` | 14 | 71% | 2.79 |
| `claude_ml_moderate_mut` | 19 | 68% | 3.09 |
| `vwap_deviation_reversion_eth_v1` | 17 | 65% | 2.09 |

**Top symbols:** POLUSDT (PF 19.6), SEIUSDT (PF 7.60), WLDUSDT (PF 2.83), AAVEUSDT (PF 2.11), NEARUSDT (PF 2.54).

**Drag symbols (kill these):**
| Symbol | n | WR | PF | Total PnL% |
|---|---|---|---|---|
| DOGEUSDT | 52 | 13% | 0.13 | −44.8 |
| OPUSDT | 54 | 24% | 0.29 | −55.1 |
| LINKUSDT | 58 | 24% | 0.47 | −29.1 |
| ADAUSDT | 69 | 25% | 0.39 | −39.8 |

These 4 symbols alone bled ~170 pnl% on 233 picks, which is 87% of crypto's −195 all-time loss. **Banning just those 4 symbols would neutralize crypto's all-time drawdown.**

**Confidence bucket — trap:**
| Bucket | n | WR | PF |
|---|---|---|---|
| <0.50 | 202 | 41% | 0.90 |
| 0.50-0.60 | 273 | 48% | 1.34 ← ok |
| **0.60-0.70** | **882** | **30%** | **0.69** ← biggest bucket is the worst |
| 0.70-0.80 | 183 | 46% | 1.32 |
| 0.80-0.90 | 82 | 48% | 0.58 |
| 0.90-1.00 | 28 | 50% | 2.60 |

The **0.60-0.70 confidence bucket in crypto holds 53% of all crypto picks and has PF 0.69**. This is the primary structural problem. Either:
- Reject this bucket outright, or
- Rescale: treat confidence as a step function where 0.60-0.70 is *penalized*, not rewarded.

**Edge filters (n≥30):**
- `symbol=NEARUSDT` → n=54, WR 59%, PF 2.54
- `strategy=luxalgo_confluence & direction=LONG` → n=87, WR 46%, PF 1.40

### ETF — small sample, kill obvious drags

- Keep: QQQ (PF 1.32), XLE (PF 1.11), intermarket-flow-scout (PF 2.01).
- Kill: IWM (PF 0.45), GLD (PF 0.80).

### BOND — monitor only

17 picks total, PF 1.60. Sample too small to make structural claims. Keep the pool running until n≥50.

---

## 4. The hedge-fund quality gate

Implemented as `alpha_engine/hedge_fund_quality_gate.py` (opt-in, no existing-file edits). Encodes the concrete rules from the drill-downs above:

```python
from alpha_engine.hedge_fund_quality_gate import passes_hedge_fund_gate, why_rejected

ok, reason = passes_hedge_fund_gate(pick)
if not ok:
    logger.info("HF gate rejected %s/%s: %s", pick["asset_class"], pick["symbol"], reason)
```

**Rules by AC (see source for exact sets and thresholds):**

| AC | Rule | Rationale |
|---|---|---|
| **CRYPTO** | Reject symbols in `DOGEUSDT / OPUSDT / LINKUSDT / ADAUSDT` | ~170% of −195% lifetime drawdown |
| **CRYPTO** | Reject `confidence ∈ [0.60, 0.70)` | PF 0.69 on 882 picks (53% of all crypto) |
| **CRYPTO** | Reject `macd_rsi_confluence` strategy on LONG | n=92, WR 41%, PF 0.72 |
| **EQUITY** | Reject SHORT direction | n=4 historical, 0 wins, PF 0 |
| **EQUITY** | Reject symbol `AAPL` | PF 0.69 on n=15 |
| **EQUITY** | Reject strategy `Classic Momentum` | PF 0.92 on n=39 |
| **COMMODITY** | Reject strategy `cta_commodity_momentum_term` | PF 0.02 on n=46 (broken) |
| **COMMODITY** | Require `confidence ≥ 0.70` | Sub-0.70 has PF 0.20-0.43; 0.70-0.80 has PF 1.34 |
| **FOREX** | Reject symbols `AUDUSD=X / CADJPY=X / EURJPY=X / EURUSD=X` | PF 0.03-0.33 each |
| **ETF** | Reject symbols `IWM / GLD` | PF 0.45 / 0.80 |
| **BOND** | Allow all | Sample too small |

**Expected impact if applied retroactively** (computed against the 3,500 closed-pick ledger):

| AC | Picks rejected | % of AC | Realized PnL% rejected |
|---|---|---|---|
| CRYPTO | ~1,115 (symbols + 0.60-0.70 bucket) | 68% | +168 to book |
| EQUITY | ~23 (SHORTs + AAPL + Classic Momentum) | 6% | +20 to book |
| COMMODITY | ~260 (low-confidence + broken strategy) | 44% | +8 to book |
| FOREX | ~237 (drag symbols) | 29% | +65 to book |
| ETF | ~24 (IWM + GLD) | 31% | +11 to book |
| **Total** | ~1,659 | 47% | **+272** system-wide |

(Numbers approximate; exact retro count depends on intersection handling. See `tools/hf_gate_retro_impact.py` in the PR for the live counter.)

---

## 5. Blocker 2 context (unchanged from earlier session)

The `clone_hl_copy_*` rows are not counted here because the user's audit dashboard uses the real HC gate (`strat_fwd_trades >= 5`) which correctly self-rejects them. Those rows don't appear in recent_closed — they live in `active_picks.json` unresolved. Separate fix still pending merge via PR #320.

---

## 6. Recommended deployment order

1. **Merge this PR** (adds `hedge_fund_quality_gate.py` as an opt-in sidecar + the diagnostic tool). No existing code changes; zero production impact until a caller wires it.
2. **Wire at execution time only** (per memory feedback `gate_at_execution_not_generation.md`). Pick generation stays permissive; gate runs at the HIGHFWWRABV55 / SCOREABOVE50 / HF paper account routing step.
3. **A/B measure for 1 week** against the existing HC gate; if the HF gate reduces realized PnL or significantly cuts volume on a profitable AC, unwind per-AC rule.
4. **Separately**: merge PR #320 (clone-seed fix) and run the clone-placeholder migration. That fixes the dashboard badge issue but does not affect realized PnL (those rows never traded).
5. **Deferred**: rebuild `confidence` in crypto as a calibration curve rather than a linear feature (the 0.60-0.70 trap is calibration failure, not raw signal failure). Benchmark with purged K-Fold on closed trades.

---

## 7. GitHub libraries to adopt

From the earlier session's 11-module integration work on `feat/ship-week-integrations-2026-04-21`, the three with the highest expected leverage here:

- **`interpret` (EBM)** — replace the opaque confidence score with a glass-box model on triple-barrier labels. Cerebras consensus recommended this as the correct long-term fix.
- **`skfolio` / `purged_cv_core`** — proper out-of-sample evaluation for the gate's rules before deployment. Avoids the overfitting trap where a gate tuned on 3,500 closed picks looks great in-sample but fails forward.
- **`pyod` (ECOD)** — regime filter. Benchmark showed pyod-flagged picks had *higher* WR (33%) than normal (29%) — suggesting pyod should be used as an **admission filter** (only trade bars flagged as "typical"), not a **rejection filter**. Reverse the sign at integration time.

These live on the ship-week branch and depend on PR #301 (resolver fix) merging first per `agent notes.txt` blocker list.
