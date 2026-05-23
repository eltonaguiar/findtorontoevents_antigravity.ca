Let me fetch both sources simultaneously.Now let me get the actual picks data and key source code files. Let me use the browser to see the full audit dashboard with picks, and fetch key scoring code from the repo.Let me fetch the critical analysis files and the scoring code.Let me grab the scoring code and performance analysis report.Now I have a comprehensive picture. Here's my full analysis:

---

## 🔍 AUDIT REVIEW: Antigravity Predictive System
**findtorontoevents.ca/audit — April 7, 2026**

---

### 1. WHERE THE EDGE ACTUALLY LIVES

Based on the data across 3,500+ closed trades and the scoring architecture:

**Proven edge (data-backed):**

| Signal Source | WR | PF | Asset | Status |
|---|---|
| `st_atr_vol_breakout` | 93% | 12.92 | Crypto | Rare signals only |
| `hs_lb_None` (SHORTS only) | 92% | 8.58 | Crypto | Whale-dependent |
| `crypto_keltner_v1` (BTC only) | 78% | 8.42 | Crypto | BTC-only, p=0.0007 |
| `quality-minus-junk` | 75% | 3.39 | Equity | Degrading |
| `drawdown_recovery_rsi_eth` | 70% | 2.30 | Crypto | ETH-specific |
| `st_fear_greed_contrarian` | 70% | 1.82 | Crypto | Highest volume, F&G≤20 |

**The real predictor hierarchy** (Spearman ρ vs PnL):
- 🥇 **ml_score** — ρ=+0.33, Top 30% = 60% WR vs Bottom = 32.5% WR → **27.5pp spread**
- 🥈 **confidence** — ρ=+0.27, Top = 51.9% WR vs Bottom = 30.8%
- 🥉 **elite_score** — ρ=+0.012 overall BUT **ρ=+0.39 on non-crypto**, and **ρ=+0.54 on verified-alpha overlap** (n=32)

**Key finding: Non-crypto scores rank much better** (Spearman ~0.33-0.39) than crypto (Spearman ~0.11-0.13). The scoring system is materially stronger for forex/equity — don't dilute with the noisier crypto pool.

---

### 2. SCORE vs REALIZED PnL — THE DISCONNECTS

**Where scores mislead:**

| Issue | Detail | Action |
|---|---|
| **Confidence is almost useless** | Pearson ~0.01 pool-wide. Should NOT dominate any composite. | Already down-weighted in `computePickScore` reweight — verify deployment |
| **Overconfidence zone** | D10 (top decile) UNDERPERFORMS D9. Scores >85 with <10 trades = overconfidence cap (60). | ✅ Already implemented |
| **Confidence sweet spot** | 0.60-0.70 = 61% WR. Above 0.85 = worse. Parabolic curve confirmed. | Keep parabolic weighting |
| **ML Composite is anti-predictive** | IC = -0.19 (zeroed). Was confidence + kelly + strategy rep. | ✅ Zeroed — never re-enable |
| **Source System Tier is anti-predictive** | IC = -0.18 (zeroed). | ✅ Zeroed |
| **R:R ratio is anti-predictive** | IC = -0.13. R:R 3.0+ = 0% WR! Higher reward targets = LOWER win rate. | ✅ Zeroed. Hard gate at R:R ≥ 1.2 is correct |

**Low score / High PnL pattern:** The empirical data shows the scoring catches most winners, but **verified-alpha picks** (n=32) with Spearman ~0.54 means the curated book is where scores are MOST predictive. The global pool (crypto noise, herding, stale picks) dilutes IC to ~0.18.

---

### 3. ACTIVE PICKS ANALYSIS

From the latest snapshot (n=57 active):
- **Smart Score** Spearman vs mark-to-market PnL = **0.42** (strongest scalar on the active book)
- **Smart tier** = 64.5% WR, +0.73% mean PnL vs Active = 44% WR, -0.01%
- **Smart Picks feed is EMPTY** (`picks.smart_picks` length = 0) — pipeline check needed

The antigravity_picks_data.json shows picks like TAO, ADA, RENDER with confidence 70-82, R:R 1.33-1.67. These are reasonable setups but:
- All **LONG** direction → no directional diversification
- All **AI/GPU narrative** → narrative concentration risk
- Missing **elite_score** and **ml_score** fields → can't apply the validated ranking

---

### 4. CRITICAL LESSONS FROM CLOSED PICKS

**Catastrophic mistakes already identified:**

1. **One toxic system flips everything** — `ml_crypto_predictor` with 365 closed picks at score=60, -8% to -10% PnL each, made IC negative (-0.052). Blocked → IC flipped to +0.18.

2. **SCALP mode destroys capital** — 855 trades, 24.8% WR, -0.171% avg. SWING: 44.9% WR, +0.013%. Heavy penalty (-25) applied.

3. **Consensus dead zone** — 3-4 strategies agreeing = 14.6% WR (WORST). Solo or 5+ = better. Medium herding = noise, not confluence.

4. **Copy trader shorts > longs** — SHORT 91.7% WR vs LONG 0% WR. Directional bias must be exploited.

5. **Keltner is BTC-only** — expanded to DOGE/XRP/BNB/ADA = 0-2% WR, all SL hits.

6. **Stop-loss dominates losses** — 78.9% of exits are SL. Wider ATR multipliers + adaptive SL needed.

---

### 5. CODE REVIEW — KEY ISSUES IN THE REPO

**Architecture:** The `alpha_engine/` is well-structured (data → features → strategies → backtest → validation → ensemble → reporting). But:

| Issue | Location | Impact |
|---|---|
| **ml_pick_scorer.py uses simulated functions** | `simulate_hindsight_win_prob()`, `simulate_skyrocket_potential()` return random noise (`np.random.randn`) | ML enhancement is decorative, not predictive |
| **Meta-model needs real training data** | `meta_model_trainer.py` exists but `meta_model_weights.json` must be trained on actual closed outcomes | Current logistic regression is unvalidated |
| **No walk-forward validation** | No purged CV or walk-forward in the live scoring path | Risk of look-ahead bias in score calculations |
| **Field name mismatches** | `pair` vs `symbol` mismatch caused ETF picks to silently vanish | Schema validation at system boundaries missing |
| **14MB HTML payload** | Embeding JSON directly crashes mobile browsers | External fetch with 5MB cap implemented — verify |

---

### 6. SCORE TWEAKING RECOMMENDATIONS

**Priority 1 — Quick Wins:**
- **Split scoring by asset class.** Crypto Spearman ~0.11 vs non-crypto ~0.3. One formula for both is suboptimal. Use within-class z-scores or separate rank maps.
- **Fill strategy track_record.** 94% missing, yet forward WR has +97pp WR spread (Q1 vs Q4). This is the #1 predictor — invest in populating it.
- **Re-enable Empirical Bayes strategy×symbol expectancy** as a subscore. Decouple "model confidence" from "historical edge here."

**Priority 2 — Structural:**
- **Replace static weights with rolling isotonic/Platt** calibration on walk-forward weeks. Map composite → E[pnl | bucket].
- **Per-source dashboards.** JSON already has `source_system` slices. Promote monotonic quintile curves, demote inverse curves.
- **Fix `smart_picks` feed** — the UI section is empty even when smart tier logic applies elsewhere.

**Priority 3 — Risk:**
- **Widen SL by 50%** using adaptive ATR multipliers. Current 78.9% SL hit rate is killing expectancy.
- **Partial TP strategy** — TP1 at 50% target (close 50%), TP2 at 100%. Improves WR mechanically.
- **Minimum time in market before SL** — 4 candle delay prevents wick-hunting losses.

---

### 7. EDGE MAP — WHERE TO FOCUS

``
┌────────────────────────────────┐
│                    EDGE SOURCES (ranked)                 │
├────────────────────────────────┤
│ 1. Verified Alpha Picks (Spearman 0.54, n=32)          │
│    → Sort aggressively by score/smart_score here       │
│                                                         │
│ 2. Smart Tier Filter (64.5% WR vs 44% Active)         │
│    → +20pp WR from quality gates alone                 │
│                                                         │
│ 3. Non-Crypto Asset Class (Spearman 0.33-0.39)         │
│    → Scores rank better forex/equity               │
│                                                         │
│ 4. Fear & Greed Contrarian (70% WR, 262 trades)       │
│    → Most robust signal, high sample size              │
│                                                         │
│ 5. BTC-Only Strategies (Keltner 78%, Funding 59%)      │
│    → Asset-locking is essential; never expand blindly  │
│                                                         │
│ 6. Copy Trader SHORTS (92% WR)                         │
│    → Directional bias = exploitable alpha              │
└────────────────────────────────┘
```

**Bottom line:** The scoring system is real but noisy. The edge concentrates in **verified-alpha picks, smart tier filtering, and non-crypto assets.** The biggest improvements will come from (a) splitting crypto/non-crypto scoring, (b) filling the strategy track_record gap, (c) fixing the stop-loss mechanics that eat 79% of trades, and (d) replacing the simulated ML scorer with a real walk-forward trained model.