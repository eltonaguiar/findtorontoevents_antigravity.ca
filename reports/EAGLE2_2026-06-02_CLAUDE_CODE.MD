# EAGLE2 Enhancement Plan: Fixing the Research-to-Production Pipeline
## Date: 2026-06-02 | Model: Claude Code (gx10-c9b9)

---

## The Real Problem (Not What We Thought)

**The portfolio is NOT empty.** `pf_portfolios.json` shows 81 portfolios, 66 with open positions. `deepseek_v4__aggressive` has 11 open names. The URL issue was likely a cache/stale asset problem.

**The real problem is a research-to-production translation failure.** We have edges in the lab (VWAPReversion DSR=21.4, BollingerMR OOS PF=1.673, OBV Divergence WR=75.7%) but the production pipeline can't deploy them because:

1. **8 sequential quality gates create a catch-22** — new strategies need 50 closed trades to be "forward validated," but the gates block picks from unvalidated strategies
2. **Walk-forward validation is the only failing pipeline step** — the only one that matters for promotion
3. **ML confidence is anti-predictive** but still used as a hard gate (conf >= 0.55)
4. **40+ banned strategies** silently kill most candidates
5. **elite_score has r=-0.001 correlation with PnL** — it's noise

---

## Root Cause by Asset Class

| Class | Diagnosis | Edge Location |
|-------|-----------|---------------|
| **CRYPTO** | Live book loses, but edge exists in sub-cohorts. Problem is selection/gating/concentration. | Tournament models (deepseek_v4), lab sleeves (VWAP, Bollinger) |
| **EQUITY** | Honest failure. Bad deployed strategies, weak emitter quality. | Only `stocks_rsi2_pullback` (n=70, WR=62.9%) |
| **ETF** | Best candidate edge, but sample too small. Main "wait for n" class. | ETF dual momentum (walk-forward PASS, OOS PF=1.21) |
| **FOREX** | Data/resolver problem + weak edge. High WR with terrible PF = red flag. | Dead. Hard-gated. |
| **COMMODITY** | Too little clean sample. Stability problem, not strategy death. | Needs investigation |
| **BOND** | Data gap. No meaningful live sample yet. | Backtests PF 1.29-1.62 but orphaned |

---

## What We're Doing Wrong

1. **Different standards for research vs production** — lab sleeves look decent, but the main scanner emits from a much noisier universe
2. **Too much breadth, not enough promotion discipline** — 100+ strategies, 8 gates, 0 promoted to A-tier
3. **Confusing "interesting cell" with "capital-ready strategy"** — tournament edge ≠ funnel edge ≠ money-ready edge
4. **Concentration masquerading as edge** — one source/system dominating looks amazing but is fragile
5. **Resolver/label issues polluting trust** — disputed cohorts, mislabeled `claude_gainer_st` inflating CRYPTO stats

---

## The 10-Step Enhancement Plan

### Phase 1: Fix the Pipeline (This Week)

#### 1. Fix Walk-Forward Validation (P0 — The Only Failing Step)
The pipeline has `walkforward_validation` as the only degraded step. Fix it:
- Wire `verified_strategies/walkforward_suite.py` into the pipeline health check
- Run walk-forward on all 68 verified strategies
- Use the verdicts to promote/demote strategies

#### 2. Lower the Forward Gate Catch-22 (P0)
`FORWARD_GATE_MIN_TRADES = 50` creates a chicken-and-egg problem. Fix:
- Lower to 20 for CRYPTO (faster cycle time)
- Lower to 10 for EQUITY/ETF/BOND
- Add a "shadow mode" that accumulates trades without blocking picks

#### 3. Fix or Disable ML Confidence Gate (P0)
ML confidence is anti-predictive (conf >= 0.90 → 14.4% WR). Options:
- **Option A**: Invert the gate — block HIGH confidence, promote LOW confidence
- **Option B**: Remove confidence from quality gates for CRYPTO (already zeroed in scoring)
- **Option C**: Recalibrate with proper IS/OOS split

#### 4. Unblock Proven Lab Strategies (P1)
VWAPReversion and BollingerMR pass walk-forward but aren't in production. Wire them:
- `CRYPTO_VERIFIED_VWAP_ENABLED=1` (already gated)
- `CRYPTO_VERIFIED_BOLLINGER_MR_ENABLED=1` (already gated)
- Add to `smart_picks_engine.py` non-crypto allowlists for ETF variant

### Phase 2: Improve Evidence Standards (Next Week)

#### 5. Pre-Register All Hypotheses (P1)
Before any backtest, lock:
- Strategy parameters
- Symbol universe
- Entry/exit rules
- Success criteria (min WR, min PF, min Sharpe)

Use `reports/hypothesis_registry.json` (already exists). No more curve-fitting.

#### 6. Run Mutation Analysis on Failed Strategies (P1)
For every strategy with WR > 55% but negative Sharpe (ConnorsRSI2 pattern):
- Test the INVERSE (fade the signal)
- Test parameter variants (grid search)
- Test symbol-specific variants (edge is symbol-specific)

#### 7. Wire Orphaned Strategies (P1)
ETF and BOND strategies have backtests showing edge but aren't wired to production:
- `etf_sector_rotation` — backtest shows edge, no production wire
- `etf_rotation_vix_regime` — backtest shows edge, no production wire
- BOND strategies — PF 1.29-1.62, accumulating picks since 2026-05-31

### Phase 3: Fix Infrastructure (This Month)

#### 8. Unify Backtesting Engine (P2)
5 modules with inconsistent implementations. Merge into 1 canonical engine:
- Purged walk-forward on raw OHLCV data (not pre-computed PnL)
- Wire existing cost models (`transaction_costs.py`, `slippage_model.py`)
- Correct DSR (Lopez de Prado eq. 7)
- Correct PBO (parameter permutations, not sign flips)
- Trade-frequency-aware Sharpe annualization

#### 9. Add Dead Assets to Universe (P2)
Survivorship bias inflates all backtests:
- Add LUNA, FTT, UST, and other dead tokens to crypto universe
- Add delisted tickers to equities
- Use CoinGecko historical snapshots for crypto

#### 10. Separate Tournament Edge from Production Edge (P2)
The tournament (39 models, deepseek_v4 leading) is a different universe from production. Keep them separate until tournament strategies survive the same admissibility pipeline:
- Pre-register hypothesis
- Walk-forward validation
- DSR + PBO
- Forward paper evidence
- Promotion only if forward PF/WR ≈ OOS lab PF/WR

---

## Where the Edge Actually Is

### Confirmed (Multiple Validations)
| Strategy | Asset | Evidence | Production Status |
|----------|-------|----------|-------------------|
| VWAPReversion | CRYPTO | DSR=21.4, PBO=0.18, 516 OOS trades | **Enable: CRYPTO_VERIFIED_VWAP_ENABLED=1** |
| BollingerMR | CRYPTO | Walk-forward PASS, OOS PF=1.673 | **Enable: CRYPTO_VERIFIED_BOLLINGER_MR_ENABLED=1** |
| OBV Divergence | CRYPTO | 115 trades, WR=75.7%, PF=8.15 | Already in production scanner |
| stocks_rsi2_pullback | EQUITY | n=70, WR=62.9% | Already active |

### Promising (Needs More Evidence)
| Strategy | Asset | Evidence | What's Missing |
|----------|-------|----------|----------------|
| ETF Dual Momentum | ETF | Walk-forward PASS, OOS PF=1.21 | Forward sample (n too small) |
| CryptoDonchianBreakout | CRYPTO | Walk-forward PASS all 3, DSR=7.24 | PBO=0.68 (needs 4h test) |
| Bond backtests | BOND | PF 1.29-1.62 | Production wire-up |
| deepseek_v4 | CRYPTO | Tournament leader | Same admissibility pipeline |

### Dead (Confirmed)
| Strategy | Asset | Evidence |
|----------|-------|----------|
| ConnorsRSI2 | CRYPTO | Sharpe -2.6, bleeds 89-97% |
| FOREX (all) | FOREX | Hard-gated, net PnL=-1026% |
| COMMODITY DSR=1.0 | COMMODITY | Falsified (6.33x over-emission) |
| ML confidence | ALL | Anti-predictive |

---

## The Hard Truth

**We have 4 confirmed edges.** That's it. Everything else is either dead, unproven, or losing money.

The path forward:
1. Enable VWAPReversion + BollingerMR in production NOW
2. Fix the walk-forward pipeline (the only failing step)
3. Lower the forward gate catch-22
4. Stop treating aggregate green stats as proof — size only from policy-clean money-ready layer
5. Depromote weak live classes (CRYPTO aggregate, EQUITY, FOREX) until fixed

---

*Generated: 2026-06-02T07:00Z*
*Reviewer: Claude Code (gx10-c9b9)*
*Based on: 3 parallel agent audits + live dashboard data + verification reports*
