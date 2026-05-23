# Statistical Edge & Prediction Quality — Improvement Analysis
**Generated:** 2026-05-16 | **Sources:** live `ejaguiar1_backtests`, `quality_gates.py`, `alpha_engine/config.py`, `DAILY_IDEAS_PROMPTS.MD`

---

## 1. What the Live DB Actually Says (ejaguiar1_backtests)

### bt_backtest_runs — 94 strategies, all CRYPTO, last imported 2026-03-06

| Symbol | Trades | Avg PF | Avg WR | Note |
|---|---|---|---|---|
| BTCUSDT | 248 | 3.32 | 57.4% | Anchor — best diversified |
| XRPUSDT | 66 | 2.74 | 42.9% | Good PF, low WR — wins are large |
| ETHUSDT | 126 | 2.52 | 50.1% | Solid; second anchor |
| SOLUSDT | 63 | 1.95 | 45.0% | Borderline T2 |
| BNBUSDT | 20 | 0.01 | 5.0% | **Catastrophic — entirely `opposite_day`** |
| AVAXUSDT | 20 | 0.01 | 10.0% | **Catastrophic — entirely `opposite_day`** |
| DOGEUSDT | 21 | 0.41 | 28.6% | Sub-floor |

**Critical finding:** BNBUSDT and AVAXUSDT look terrible in the DB **because 100% of their bt_backtest_runs rows are `opposite_day`** — a strategy with PF 0.009–0.011 across all 10 CRYPTO symbols. The symbols themselves may have edge; the strategy is the problem.

### `opposite_day` — KILL CANDIDATE

- 158 trades across 8 symbols, avg WR 9.7%, avg PF 0.114
- Only LINKUSDT shows PF 1.74 — but n=3 (statistical noise)
- **Recommendation: add `("opposite_day", "CRYPTO")` to `BLOCKED_STRATEGIES` immediately**
- This would rehabilitate BNBUSDT and AVAXUSDT stats in the DB

### Top Strategy Archetypes (incubator, n≥15 trades)

| Archetype | Symbols | Trades | PF | WR | Sharpe |
|---|---|---|---|---|---|
| `rsi_mean_reversion` | 5 | 101 | **2.57** | **65.4%** | 5.33 |
| `ichimoku_cloud` | 5 | 1008 | 1.78 | 37.8% | -8.4 |
| `vwap_reversion` | 2 | 23 | 1.59 | 52.3% | 2.91 |
| `ema_crossover` | 4 | 219 | 0.48 | 27.2% | -10.5 |

**`ema_crossover` is broken** — kill it in the incubator or restrict to trend-following regimes only (not mean-reversion crypto).

### No Portable Edge Detected
Zero strategies show `min_pf > 1.2` across ≥2 symbols simultaneously. The best strategies are single-symbol optimized (e.g., `drawdown_recovery_rsi` on BTCUSDT only, PF 11.6). This is the single biggest risk: **single-symbol overfit masquerading as a proven strategy**.

---

## 2. Improvement Areas Per Asset Class

### CRYPTO (most data, most actionable)

**Current state:** PF 1.25, WR 44.6% system-wide (post-resolver-v2, per CLAUDE.md). Elite strategies (PF 2.34–3.97) dragged down by `quan_engine` (18% volume, PF 0.70) and `unknown` (7%, PF 0.35).

**Actions ranked by impact:**

1. **Kill `opposite_day`** on CRYPTO immediately — 158 losing trades polluting BNBUSDT/AVAXUSDT stats.
2. **Expand top strategies cross-symbol.** `drawdown_recovery_rsi` is PF 11.6 on BTC but untested on ETH/SOL/XRP. Run incubator sweep. `keltner_compression_expansion` has PF 5.9–6.4 on ETH/XRP — test on BTC/SOL.
3. **Port incubator `rsi_mean_reversion` params to production.** Best incubator archetype: PF 2.57, WR 65.4%. The `at_large_backtest_results` has specific params: RSI(3), rsi_entry<8, rsi_exit>75, ATR-based SL/TP (1.89×/2.65×), max_hold 3 days. These are concrete, backtested params — wire to production scanner.
4. **Cut `ema_crossover`** from incubator sweep list — consistently PF 0.48, WR 27.2% across 4 CRYPTO symbols, 219 trades. Use RSI-based entries instead.
5. **Regime gate for LONG crypto.** The `quality_gates.py:965` already blocks `crypto_short_blocked_in_bull_regime` — add a matching long-in-bear-regime gate. Bull = BTC above 200d SMA; bear = below.
6. **quan_engine volume reduction.** Already flagged in CLAUDE.md. The 18% volume at PF 0.70 is the #1 systemic drag. Gate: if `source_system == "quan_engine"` AND asset_class == "CRYPTO", require score ≥ 70 (vs. default 50).

### EQUITY (T2 candidate, PF 1.41, WR 52.7%, n=421)

**Actions:**
1. **Blocked symbol expansion review.** 14 equity symbols blocked (ADBE, CRM, ACN, MSFT, PLTR, TSLA, XLE, CVX, XOM, NVDA, NKE, PG, HD + JTOUSDT/XLMUSDT/ICPUSDT/RENDERUSDT for crypto). These blocks are correct — but add a scheduled 90-day review gate (see §4 unblock criteria).
2. **`Earnings Drift` inversion.** Already noted in `BLOCKED_STRATEGIES`: inverse confirmed PF 2.07. This inversion is not yet wired to production — it should be. Implement `inverse_earnings_drift` as a LONG-only EQUITY strategy.
3. **Quality momentum filter.** From DAILY_IDEAS_PROMPTS.MD #8: stocks with top 30% ROE AND top 30% 12-month momentum outperform. If `alpha_fundamentals` table has ROE data, this can be built as a score multiplier in `calculate_smart_score`.
4. **Sector concentration guard.** ADBE/CRM/ACN/MSFT/PLTR/TSLA are all tech/software — the block fixed the symptom but not the root cause. Add a sector-concentration penalty: if >40% of active EQUITY picks are in the same GICS sector, cap new picks from that sector.

### COMMODITY (T2 PF-qualified, PF 1.78, WR 46.9%, n=750 — lift WR)

**Actions:**
1. **WR is the bottleneck** (46.9% vs. T2 floor of 50%). Focus on better entry timing: add a macro trend confirmation gate — only take LONG positions when 20d SMA of commodity price is above 60d SMA (per DAILY_IDEAS_PROMPTS.MD #8 copper/wheat strategy).
2. **COT dedup guard is active** (72h window) — verify it's actually reducing n inflation for CT=F (cotton was 94.3% of COMMODITY picks before dedup).
3. **Volatility-scaled sizing** — target 1% portfolio vol per trade (DAILY_IDEAS_PROMPTS.MD), not fixed size. This lifts WR by forcing smaller positions in high-vol regimes where mean-reversion strategies fail.

### BOND (T2 PF+WR qualified, PF 1.72, WR 55.6%, n=18 — sample size bottleneck)

**Action:** One thing only — get n from 18 to ≥100 before any optimization. The PF/WR look good but 18 trades is below the charter floor. Add more bond instruments (TLT, IEF, SHY, BND) and allow 2yr/10yr spread strategies (DAILY_IDEAS_PROMPTS.MD #8). Do not optimize parameters until n ≥ 50.

### FOREX (Genuinely sub-floor, PF 0.27, WR 46.4%, n=1169)

**Status:** Active investigation required per MUTATION_THREE_AXIS_PROTOCOL. `forex_rsi2_mean_reversion` is already re-blocked (2026-05-13). 

**Actions:**
1. **Carry trade + EMA trend filter** (from DAILY_IDEAS_PROMPTS.MD #8): enter LONG EUR/USD, GBP/USD, AUD/USD only when price EMA(20) > EMA(50) AND interest rate differential is positive. This combines trend with carry — neither alone works in FOREX.
2. **Stop-loss discipline.** DAILY_IDEAS_PROMPTS.MD recommends 1.5% SL / 3.0% TP for carry trades. Current FOREX strategies likely have poor R:R. Check `avg_trade_pnl` distribution in `at_signal_outcomes` for FOREX picks.
3. **Do NOT add new FOREX strategies until n ≥ 50 clean trades post-resolver-v2 on any single strategy.**

### ETF (Borderline, PF 1.24, WR 55.2%, n=87)

**Action:** Get n → 100 first. Add pairs-trading (XLK vs. VGT cointegration per DAILY_IDEAS_PROMPTS.MD). ETF_BLACKLIST already removes the worst symbols. The remaining portfolio needs 13 more clean resolved trades.

---

## 3. Symbol Unblock Criteria (Medical-Grade Standard)

A blocked symbol may be proposed for unblock when **ALL** of the following hold:

### Gate A — Minimum Sample (non-negotiable)
- `n_resolved_post_block ≥ 30` clean trades (post-resolver-v2 `_is_valid_resolved_pick`)
- At least **2 distinct strategies** contributed to this n (single-strategy concentration = not proven)
- Time window ≥ 21 calendar days (not a short-term spike)

### Gate B — Statistical Edge
- **Win rate ≥ 52%** (Wilson 95% lower bound ≥ 45%)
- **Profit factor ≥ 1.20** (bootstrap 2.5th-percentile CI lower bound > 1.0)
- Max drawdown ≤ 25% of peak equity in the window
- Avg trade PnL > 0.05% (minimum pip-equivalent to cover slippage)

### Gate C — Trend (Recent Momentum)
- **7-day trailing WR ≥ 50%** (last 14 days is even better)
- Linear regression slope of cumulative PnL over last 30 days: **positive** (β > 0)
- No more than 3 consecutive losses in the last 10 resolved trades

### Gate D — Regime Compatibility
- Symbol is NOT in a confirmed structural adverse regime (e.g., delisted, redenominated, regulatory blocked)
- For CRYPTO: if BTC is in bear regime (< 200d SMA), only allow symbols with short-bias or regime-neutral strategies
- For EQUITY: sector cannot be in >40% active-pick concentration at unblock time

### Gate E — Process (mandatory paperwork)
- Must produce `updates/YYYY-MM-DD-symbol-rehab-<SYMBOL>.md` with:
  - Block reason + original metrics
  - Post-block metrics (n, WR, PF, MDD, slope)
  - Which strategies drove the recovery
  - 30-day forward-test plan with re-block trigger
- **Re-block trigger** (must be stated in the doc): e.g., "Re-block if WR drops below 40% on n ≥ 20 forward trades"

### Immediate Candidates for Unblock Review
Based on the live DB data and the `opposite_day` contamination finding:

| Symbol | Block Reason | Current DB PF | Why Review |
|---|---|---|---|
| BNBUSDT | No block in BLOCKED_SYMBOLS — but opposite_day pollutes its stats | 0.011 | 100% of bad trades = opposite_day; real PF unknown |
| AVAXUSDT | No block in BLOCKED_SYMBOLS — same issue | 0.010 | Same as BNB |
| LINKUSDT | Not blocked — but in bt_backtest_runs with PF 1.74 on opposite_day | 1.74 | n=3, needs real data |
| NVDA | Blocked 2026-04-15: n=21, WR 33.3%, PF 0.77 | n/a live | It's 2026-05-16 — 30 days passed; review if n≥30 new |

---

## 4. Safety Gate Improvements

### New Gates to Add (priority order)

**G1 — `opposite_day` kill (P0)**
```python
# audit_trail/quality_gates.py  BLOCKED_STRATEGIES
("opposite_day", "CRYPTO"),  # PF 0.009-0.114, WR 3.6-29.4% across 14 symbols, 158 trades
```

**G2 — Single-symbol concentration guard (P1)**
Any strategy with n ≥ 20 but only 1 symbol should be flagged `REQUIRES_WALKAHEAD_AUDIT` automatically. Add to the existing set-construction logic.

**G3 — Source volume cap per asset class (P1)**
```python
# alpha_engine/config.py
SOURCE_VOLUME_CAP = {
    "quan_engine": {"CRYPTO": 0.12},   # was ~18%; cap at 12%
}
# If source exceeds cap for asset class: score penalty -15
```

**G4 — Portable-edge minimum for graduation (P2)**
Before a strategy graduates from incubator to production, it must show `min_pf > 1.2` on ≥2 symbols (not just 1). Add this check to the incubator graduation gate.

**G5 — EMA crossover block in CRYPTO incubator (P2)**
```python
("ema_crossover", "CRYPTO"),  # PF 0.48, WR 27.2%, 219 incubator trades — structural loser
```

**G6 — 90-day scheduled unblock review (P3)**
Add a `PENDING_UNBLOCK_REVIEW` dict in `quality_gates.py` mapping symbol → review_date. The dashboard generator can surface these as "due for review" without auto-unblocking.
```python
PENDING_UNBLOCK_REVIEW = {
    "NVDA": "2026-05-15",   # blocked 2026-04-15, 30d passed
    "JTOUSDT": "2026-05-15",
    "XLMUSDT": "2026-05-15",
}
```

---

## 5. DNA Mutation Opportunities (from DAILY_IDEAS_PROMPTS.MD)

The following blocked/failing strategy→direction pairs have the highest inversion potential based on the existing block data:

| Original Strategy | Block Reason | Inversion Candidate | Why It May Work |
|---|---|---|---|
| `Earnings Drift` (EQUITY) | 15.8% WR, PF 0.30 | `inverse_earnings_drift` | Block note says "inverse confirmed PF 2.07" — not yet implemented |
| `claude_gainer` | 14.3% WR | `inverse_claude_gainer` | Already mentioned in code comment "validated 85.7% WR" — is this wired? |
| `ig_contrarian_sentiment` | 30.3% WR, PF 0.01 | `ig_trend_sentiment` | Pure contrarian fails → pure trend-follow |
| `opposite_day` on LINK | PF 1.74 on n=3 | Test `opposite_day_LINK` with n≥30 | Small sample suggests genuine LINK-specific contrarian edge |
| `drawdown_recovery_rsi` | BTC-only, PF 11.6 | Cross-symbol: ETH/SOL/XRP | Best incubator strategy, zero cross-symbol validation |

---

## 6. Institutional-Grade Improvements (Medium-Term)

These require more engineering effort but match the techniques in DAILY_IDEAS_PROMPTS.MD:

| Technique | Asset Classes | Current Gap | Estimated PF Lift |
|---|---|---|---|
| Walk-forward OOS validation (12m train / 3m test) | ALL | Only in-sample backtests in incubator | Eliminates overfit-masking; prevents PF inflation |
| Regime-aware strategy switching | CRYPTO, EQUITY | Partial (bull/bear gate for shorts) | +0.2–0.5 PF by turning off mean-reversion in trending markets |
| Volatility-scaled position sizing | ALL | Fixed-size assumption | Reduces MDD 20–40% without changing WR |
| Feature importance pruning (SHAP) | ML strategies | ml_bg_system_* are killed but no root cause analysis | Identifies which features caused collapse; enables rehab |
| Carry + trend filter for FOREX | FOREX | No carry gate exists | FOREX is at PF 0.27 — carry filter alone could lift to >1.0 |
| Sector concentration cap | EQUITY | No sector-level gate | Prevents ADBE/CRM/ACN-style cluster failures |
| Cointegration pairs for ETF | ETF | No pairs logic | XLK/VGT spread: historically <2σ reversion within 5 days |

---

## 7. Immediate Action Items (this week)

| Priority | Action | File | Impact |
|---|---|---|---|
| P0 | Add `("opposite_day", "CRYPTO")` to `BLOCKED_STRATEGIES` | `audit_trail/quality_gates.py` | Cleans BNBUSDT/AVAXUSDT stats, removes 158 losing trades from system |
| P0 | Add `("ema_crossover", "CRYPTO")` to `BLOCKED_STRATEGIES` | `audit_trail/quality_gates.py` | Removes 219 incubator losing trades |
| P1 | Add `PENDING_UNBLOCK_REVIEW` dict with NVDA/JTOUSDT/XLMUSDT/ICPUSDT | `audit_trail/quality_gates.py` | Creates structured review pipeline |
| P1 | Run incubator sweep: `drawdown_recovery_rsi` params on ETH/SOL/XRP | `tools/` or swarm_v2 | Tests portability of best CRYPTO strategy |
| P1 | Wire `inverse_earnings_drift` to EQUITY production path | `alpha_engine/` | "Inverse confirmed PF 2.07" — free edge not yet captured |
| P2 | Add source volume cap for `quan_engine` CRYPTO ≤ 12% | `alpha_engine/config.py` | Reduces #1 systemic drag |
| P2 | Add portable-edge gate to incubator graduation | `alpha_engine/` | Prevents single-symbol overfit from reaching production |
| P3 | Create `tools/symbol_rehab.py` — automated unblock checker | `tools/` | Implements §3 criteria programmatically |
