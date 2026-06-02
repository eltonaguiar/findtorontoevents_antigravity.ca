# EAGLE2 Enhancement Plan: Research-to-Production Translation
## 2026-06-02 — Claude Code

---

## Diagnosis (from multi-agent quant review)

The main /audit production book is weak because **research edge ≠ deployed edge**. Live policy-clean performance is bad in the classes that matter most, while the places that do show edge are mostly paper/tournament-only, overly concentrated, insufficiently sampled, or contaminated by resolver/label issues.

**This is NOT a "wait longer" problem.** It's a research-to-production translation problem.

### By Asset Class

| Class | Diagnosis | Action |
|-------|-----------|--------|
| CRYPTO | Live book bad, but edge exists in sub-cohorts. Selection/gating/concentration mismatch. | Depromote aggregate. Promote VWAPReversion + BollingerMR. |
| EQUITY | Honest failure. Bad deployed strategies / failed holdout / weak emitter quality. | Stop trading. Rebuild from scratch. |
| ETF | Best candidate edge, but sample too small. Main "wait for forward n" class. | Keep collecting. Don't size yet. |
| FOREX | Data/resolver problem + weak edge. High WR with terrible PF = red flag. | Fix resolver. Don't trade until PF > 1.0. |
| COMMODITY | Too little clean sample. Stability/sample problem. | Keep collecting. |
| FUTURES | Concentration/artifact risk. Stats too dependent on narrow sources. | Don't trust yet. |
| BOND | Mostly data gap / no meaningful live sample. | Wire FRED API. |

---

## Enhancement Plan

### Phase 1: Stop the Bleeding (This Week)

**1.1 Depromote weak live classes**
- CRYPTO aggregate: desize until VWAPReversion/BollingerMR are promoted individually
- EQUITY: stop all sizing. PF=0.76 means we lose 24 cents per dollar traded.
- FOREX: stop all sizing. PF=0.27 is catastrophic.

**1.2 Fix portfolio pipeline**
- The portfolio IS generating data (81 portfolios, 66 with positions)
- `deepseek_v4__aggressive` has 11 open names
- The URL was correct — need to verify the page loads properly
- Debug: check if `pf_portfolio_deepseek_v4__aggressive.json` exists and is being served

**1.3 Enable VWAPReversion in production**
- `CRYPTO_VERIFIED_VWAP_ENABLED=1`
- Gate: WALKFORWARD_REPORT.json "vwap_reversion" → PASS ✓
- DSR=21.4, PBO=0.18 — best statistical validation of any strategy

### Phase 2: Admissibility Pipeline (This Month)

Every strategy must pass this pipeline before it can affect capital:

```
┌─────────────────────────────────────────────────────────────────┐
│                    ADMISSIBILITY PIPELINE                        │
├─────────────────────────────────────────────────────────────────┤
│ 1. Pre-register hypothesis (M-107)                              │
│    - Lock parameters BEFORE seeing data                         │
│    - Document expected edge source                              │
│                                                                 │
│ 2. Real data only                                               │
│    - No synthetic data                                          │
│    - Explicit source/fallback provenance                        │
│    - FRED API key for carry rates                               │
│                                                                 │
│ 3. Purged + embargoed walk-forward                              │
│    - 70/30 IS/OOS chronological split                           │
│    - 5% purge gap between train/test                            │
│    - Rolling windows (train=504d, test=126d)                    │
│                                                                 │
│ 4. Costs/slippage by asset class                                │
│    - Crypto: 10bps commission + 5bps slippage                   │
│    - Equity: 5bps + 3bps                                        │
│    - Forex: 3bps + 2bps                                         │
│                                                                 │
│ 5. DSR + PBO + SPA correction                                   │
│    - DSR > 1.0 required                                         │
│    - PBO < 0.5 required                                         │
│    - SPA p-value < 0.10                                         │
│                                                                 │
│ 6. Block bootstrap (not i.i.d. shuffle)                         │
│    - Preserve autocorrelation structure                         │
│    - 1000 iterations minimum                                    │
│                                                                 │
│ 7. Regime robustness                                            │
│    - Must work in trending AND ranging markets                  │
│    - Test on bull/bear/sideways separately                      │
│                                                                 │
│ 8. Forward paper evidence                                       │
│    - Minimum 30 resolved picks                                  │
│    - Forward PF within 20% of OOS PF                            │
│                                                                 │
│ 9. Gradual capital scaling                                      │
│    - Shadow → tiny (1%) → small (5%) → full                    │
│    - Only scale after live proof                                │
└─────────────────────────────────────────────────────────────────┘
```

### Phase 3: Strategy DNA Mutation (Q3 2026)

**3.1 Mutation framework**
For every strategy that fails but has plausible signal:
1. Generate parameter variants (±20% on each parameter)
2. Test each variant through the admissibility pipeline
3. Select winners by OOS Sharpe, not IS Sharpe
4. Lock winning parameters before forward test

**3.2 Inversion testing**
For every strategy with WR > 60%:
1. Test the INVERSE (fade the signals)
2. If inverse has PF > 1.0, the original is noise
3. Example: ConnorsRSI2 (WR 60%, PF 0.95) → inverse would have WR 40%, PF ~1.05

**3.3 Regime-conditional strategies**
Instead of one strategy for all regimes:
1. Detect regime (ADX for trend, ATR for volatility)
2. Route to regime-appropriate strategy
3. Trending: momentum/trend-following
4. Ranging: mean-reversion
5. High-vol: breakout
6. Low-vol: carry

### Phase 4: Data Infrastructure (Q3 2026)

**4.1 Fix FRED API**
- Wire API key for historical rate differentials
- Fix timeout issues from gx10
- Cache locally with 7-day TTL

**4.2 Intraday data for equities**
- Use 4h candles for 6x more data points
- Test all equity strategies on 4h before declaring dead

**4.3 Resolver/label fixes**
- Audit disputed cohorts
- Fix TIME_EXIT artifacts in FOREX
- Clean duplicate picks

**4.4 Concentration detection**
- Flag strategies where >50% of edge comes from one source
- Require cross-symbol validation

### Phase 5: Tournament → Production Bridge (Q3 2026)

**5.1 Keep tournament separate**
- Tournament edge ≠ production edge
- Don't promote tournament winners directly to production
- Run them through the admissibility pipeline first

**5.2 Best tournament candidates**
- deepseek_v4: most credible edge
- gpt4o: decent evidence
- grok3: promising

**5.3 Production candidates from lab**
- ETF dual momentum: best future candidate
- Crypto VWAP/Bollinger: better than live production mix
- DonchianBreakout: walk-forward PASS but needs more forward sample

---

## Priority Order

| Priority | Action | Timeline | Impact |
|----------|--------|----------|--------|
| P0 | Enable VWAPReversion | Today | Stop losing money on crypto |
| P0 | Depromote EQUITY/FOREX | Today | Stop hemorrhaging capital |
| P1 | Fix portfolio pipeline | This week | Visibility into what's working |
| P1 | Wire FRED API | This week | Fix carry trade data |
| P2 | Run all strategies on 4h | This month | 6x more statistical power |
| P2 | Build admissibility pipeline | This month | Prevent curve-fit promotion |
| P3 | DNA mutation framework | Q3 | Find hidden edges in failed strategies |
| P3 | Regime detection | Q3 | Route strategies to correct regime |

---

## What NOT to Do

1. **Don't add more strategies** until the admissibility pipeline is built
2. **Don't trust aggregate green stats** — size only from policy-clean money-ready layer
3. **Don't confuse tournament edge with production edge** — they're different universes
4. **Don't allow concentration to masquerade as edge** — one source dominating = fragile
5. **Don't promote based on backtest WR alone** — WR × PF (Kelly) is the right metric

---

## The Bottom Line

We have **1 validated production-ready strategy** (VWAPReversion). Everything else is either dead, unproven, or losing money. The path forward is:

1. Enable VWAPReversion (stop the bleeding)
2. Depromote losing classes (EQUITY, FOREX)
3. Build the admissibility pipeline (prevent future failures)
4. Mutate failed strategies (find hidden edges)
5. Wait for forward sample on ETF/COMMODITY

We don't need more strategies. We need fewer, better-validated strategies with proper forward proof.

---

*Generated: 2026-06-02T07:00Z*
*Agent: Claude Code (gx10-c9b9)*
