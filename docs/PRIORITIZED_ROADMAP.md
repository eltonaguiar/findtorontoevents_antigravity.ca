# Prioritized Improvement Roadmap — Alpha Engine

**Generated:** 2026-03-23 | **Author:** Claude Opus 4.6 (technical product strategy analysis)
**Based on:** 8 deep code audits, 6 AI reviewer feedback, codebase verification

---

## Executive Summary

The Alpha Engine has 120+ strategies, a 21-component scoring pipeline, and extensive infrastructure. However, **several critical assumptions baked into the scorer are empirically wrong**, three high-value gates exist as standalone modules but are not wired into production, and the ML pipeline is completely broken (1/46 features alive). The roadmap below prioritizes items that reduce false positives and drawdown, not incremental feature additions.

### Organizing Principle: Filter -> Rank -> Size

```
FILTER  (hard gates — binary pass/fail, reduces false positives)
  |  kill_switch.py, forward_validator.py, mtf_gate.py, ensemble_gate.py, ha_ensemble_filter.py
  v
RANK    (scoring — ordinal ranking of survivors, replaces additive scorer)
  |  elite_scorer.py -> calibrated P(win) model
  v
SIZE    (position sizing — how much capital per pick)
     kelly_position_sizer.py
```

Current state: Filter exists (kill switch + quality gates). Size exists (Kelly sizer). **Rank is the weak link** — still an additive score with empirically wrong weights and double-counted components.

---

## Phase 1: Quick Wins (1-3 days each, highest impact)

### P1-01: Fix R:R Scoring — Inverted Data Still in Production

```json
{
  "id": "P1-01",
  "title": "Fix R:R scoring weights — verified data contradicts current weights",
  "impact": "HIGH",
  "effort_days": 0.5,
  "status": "NOT STARTED",
  "rationale": "elite_scorer.py line 1081 comment says 'R:R 2.0-2.5 = 73.7% WR (sweet spot)' and awards 5 pts. Verified data from 8 audits shows R:R 2.0-2.5 = 26% WR — the WORST bucket. This means the scorer actively rewards the worst-performing R:R range.",
  "blockers": [],
  "next_steps": [
    "1. Open alpha_engine/elite_scorer.py lines 1068-1096",
    "2. Invert the R:R scoring: R:R 1.0-1.5 should get highest score (verified best WR)",
    "3. R:R 2.0-2.5 should get 0-1 pts (26% WR = worst bucket)",
    "4. R:R 2.5+ should get 0 pts (TP rarely reached, confirmed)",
    "5. Update comment to cite verified data, not external claims",
    "6. Run py_compile to verify syntax"
  ]
}
```

**Why this is #1:** Every single pick gets R:R scored. Fixing this immediately stops rewarding the worst-performing risk/reward profile. Zero risk, 30-minute fix, affects every pick in the system.

---

### P1-02: Wire MTF Gate into Production Pipeline

```json
{
  "id": "P1-02",
  "title": "Wire mtf_gate.py into smart_picks_engine.py as mandatory filter",
  "impact": "HIGH",
  "effort_days": 1,
  "status": "NOT STARTED — module exists but NOT wired",
  "rationale": "mtf_gate.py exists and works (used in A/B testers and score_booster.py). Research shows MTF confirmation alone can push WR from ~42% to 55-62%. Currently only used in ab_test_portfolios.py and clone_ab_tester.py — NOT in scanner.py, elite_scorer.py, or smart_picks_engine.py. The three gates (MTF, ensemble, HA) are standalone orphans.",
  "blockers": ["API rate limits for Binance kline calls during batch scoring"],
  "next_steps": [
    "1. In alpha_engine/smart_picks_engine.py, add import for mtf_gate.check_mtf_alignment (try/except pattern already exists at line 26-33)",
    "2. After the R:R >= 1.2 filter (line ~135), add MTF gate check",
    "3. If mtf result['score_adjustment'] <= -25 (BLOCKED), exclude pick from smart picks",
    "4. If mtf result['score_adjustment'] >= 0, add to smart_score as bonus",
    "5. Use batch mode (check_mtf_batch) to minimize API calls",
    "6. Add 10-min cache TTL (already built into mtf_gate.py)",
    "7. Ensure crypto-only (skip forex/equity symbols)"
  ]
}
```

---

### P1-03: Merge Forward WR + Track Record (Eliminate Double-Counting)

```json
{
  "id": "P1-03",
  "title": "Merge Forward WR (0-30pts) and Strategy Track Record (0-20pts) into single 30pt component",
  "impact": "HIGH",
  "effort_days": 1,
  "status": "NOT STARTED",
  "rationale": "Both components read from the same data source (strategy_performance.json / forward_validator stats). A strategy with WR>55% on 10+ trades gets 30 pts from Forward WR AND 20 pts from Track Record = 50 pts from the same underlying data. This is the single largest score inflation source. strategy_fwd_wr is the #1 predictor (Spearman 0.253) — it should dominate, but not be double-counted.",
  "blockers": [],
  "next_steps": [
    "1. In alpha_engine/elite_scorer.py, merge sections at lines 719-813 (Forward WR) and 1282-1326 (Track Record)",
    "2. Create unified 'strategy_evidence' component: 0-30 pts total",
    "3. Forward WR (verified by our system, 50+ trades) = primary signal, up to 25 pts",
    "4. Track record (source_system fallback) = secondary, up to 5 pts (only when forward data unavailable)",
    "5. Set breakdown keys: 'strategy_evidence' (replaces 'forward_wr' and 'strategy_track_record')",
    "6. Update SMARTPICKS.MD documentation"
  ]
}
```

---

### P1-04: Wire Ensemble Gate + HA Filter into Smart Picks

```json
{
  "id": "P1-04",
  "title": "Wire ensemble_gate.py and ha_ensemble_filter.py into production",
  "impact": "HIGH",
  "effort_days": 1.5,
  "status": "NOT STARTED — modules exist but orphaned",
  "rationale": "ensemble_gate.py (2-of-3 signal categories) and ha_ensemble_filter.py (Heikin Ashi + 3-indicator) both exist as complete, tested modules. Neither is called from scanner.py, elite_scorer.py, forward_validator.py, or smart_picks_engine.py. Only score_booster.py imports mtf_gate, not the other two. All three gates should be unified into a single 'confirmation_gate' step.",
  "blockers": ["API rate limits — all three gates make Binance API calls"],
  "next_steps": [
    "1. Create alpha_engine/confirmation_gate.py that orchestrates all 3 gates:",
    "   - mtf_gate.check_mtf_alignment(symbol, direction)",
    "   - ensemble_gate.check_ensemble(symbol, direction)",
    "   - ha_ensemble_filter.check_ha_ensemble(symbol, direction)",
    "2. Unified scoring: average the score_adjustments, require at least 2/3 gates to pass",
    "3. Wire into smart_picks_engine.py after dedup but before final ranking",
    "4. Share Binance kline cache across all 3 modules (they all fetch the same data)",
    "5. Crypto-only (all gates use Binance API, not applicable to forex/equity)",
    "6. Log gate results to data/confirmation_gate_log.json for performance tracking"
  ]
}
```

---

### P1-05: Reduce Position Performance Weight

```json
{
  "id": "P1-05",
  "title": "Reduce Position Performance from 0-10pts to 0-3pts",
  "impact": "MEDIUM",
  "effort_days": 0.5,
  "status": "NOT STARTED",
  "rationale": "Position Performance rewards picks that are currently winning. This creates momentum-chasing bias. A pick at +100% PnL gets 10pts — but it has already moved, the upside is captured. Verified by peer audit: 'Currently Winning' is backward-looking, not predictive. Smart Picks engine also has 'Currently Winning' as dimension #5 (10pts), creating another double-count.",
  "blockers": [],
  "next_steps": [
    "1. In alpha_engine/elite_scorer.py, find Position Performance section",
    "2. Reduce scale: +100% PnL: 3pts (was 10), +50%: 2pts, +20%: 2pts, +5%: 1pt, 0%: 1pt",
    "3. Remove TP progress sub-bonus (+3/+2/+1 for >80%/>50%/>25% progress)",
    "4. In smart_picks_engine.py, reduce 'Currently Winning' dimension from 10pts to 5pts max",
    "5. py_compile to verify"
  ]
}
```

---

### P1-06: Confidence Bucket Recalibration

```json
{
  "id": "P1-06",
  "title": "Recalibrate confidence thresholds — best bucket is 0.75-0.80, not 0.60-0.70",
  "impact": "MEDIUM",
  "effort_days": 0.5,
  "status": "PARTIALLY DONE (ML replacement score uses 0.70/0.80 thresholds but Forward Validator Winner Filter still blocks >0.75)",
  "rationale": "Verified: Confidence 0.75-0.80 = 79.2% WR (BEST bucket). But forward_validator.py Winner Filter blocks confidence >0.75 as 'overfit (49% WR)'. This contradicts the verified data. The Winner Filter gate is based on stale or incorrect analysis.",
  "blockers": [],
  "next_steps": [
    "1. In alpha_engine/forward_validator.py, find Winner Filter confidence gate",
    "2. Change upper bound from 0.75 to 0.90 (allow 0.75-0.80 sweet spot through)",
    "3. Keep lower bound at 0.55 (below is noise, confirmed)",
    "4. In elite_scorer.py compute_ml_replacement_score(), verify 0.80+ gets highest tier (currently correct at +8pts)",
    "5. Add logging when confidence gate filters out picks for future audit"
  ]
}
```

---

## Phase 2: Foundation Work (3-7 days, prerequisites for later phases)

### P2-01: Fix ML Feature Pipeline (Critical Prerequisite)

```json
{
  "id": "P2-01",
  "title": "Fix ML feature pipeline — only 1/46 features is alive",
  "impact": "HIGH",
  "effort_days": 5,
  "status": "NOT STARTED",
  "rationale": "ML ranker is BROKEN. AUC=1.0 is a known overfitting artifact. Champion model is INCOMPATIBLE (feature mismatch). 45/46 features are dead (80%+ at default/zero). The model auto-drops dead features during training but the underlying data pipeline never populates them. Until this is fixed, all ML-based scoring is random noise.",
  "blockers": ["Requires scanner.py to inject OHLCV-derived features at signal generation time"],
  "next_steps": [
    "1. In alpha_engine/scanner.py, at signal generation point, compute and inject:",
    "   - rsi_at_entry (currently 17% populated — need yfinance/Binance fetch)",
    "   - volume_ratio (currently 6% populated)",
    "   - atr_at_entry (currently 5% populated)",
    "   - regime_encoded (currently ~5% populated — use fast_regime_detector output)",
    "2. In alpha_engine/technical_features.py, ensure Phase 13 features compute from actual OHLCV",
    "3. Verify population rates after fix: target >80% for top 10 features",
    "4. Retrain ML model with purged CV after feature pipeline is fixed",
    "5. Monitor AUC — if still 1.0, investigate remaining leaky features",
    "6. Target: Precision@20 > 0 (currently stuck at 0)"
  ]
}
```

---

### P2-02: Implement Calibrated P(win) Scoring

```json
{
  "id": "P2-02",
  "title": "Replace additive elite_score with calibrated probability of winning",
  "impact": "HIGH",
  "effort_days": 7,
  "status": "NOT STARTED",
  "rationale": "The additive scorer sums 21 components with manually set weights. No component interaction is modeled. A pick can score 85/100 by accumulating many small bonuses from weak predictors while having poor forward WR. Calibrated P(win) directly predicts the probability of a profitable outcome. Cross-AI consensus item #10.",
  "blockers": ["P2-01 (ML feature pipeline) should be fixed first for maximum impact, but a logistic regression on the 5-7 strongest features can start immediately"],
  "next_steps": [
    "1. Start with logistic regression on top 5 verified predictors:",
    "   - strategy_fwd_wr (Spearman 0.253 — #1)",
    "   - confidence bucket (0.75-0.80 = 79.2% WR)",
    "   - elite_score Q4 vs Q1 separation (75.3% vs 50.7%)",
    "   - copy vs clone (55% vs 35% WR)",
    "   - consensus count (2-3 = 42% WR, 4+ = 34.8%)",
    "2. Train on closed_picks.json (need 200+ resolved trades)",
    "3. Calibrate with isotonic regression (sklearn.isotonic.IsotonicRegression)",
    "4. Output: P(win) between 0.0 and 1.0 per pick",
    "5. Replace elite_score with P(win) * E[return] for ranking",
    "6. Keep additive score as 'debug' field for transition period"
  ]
}
```

---

### P2-03: Consensus Herding Cap

```json
{
  "id": "P2-03",
  "title": "Cap consensus at 3 systems max — 4+ is herding (34.8% WR)",
  "impact": "MEDIUM",
  "effort_days": 1,
  "status": "PARTIAL — contrarian_consensus.py exists but only generates inverse signals, doesn't cap main pipeline",
  "rationale": "Verified: 2-3 systems agreeing = 42% WR (BEST). 4-7 systems agreeing = 34.8% WR (herding). The current confluence penalty in elite_scorer.py gives -3pts for 3+ agreement but doesn't hard-block. The contrarian_consensus.py generates inverse signals when 3+ agree, but the ORIGINAL picks with 4+ consensus still pass through to smart picks.",
  "blockers": [],
  "next_steps": [
    "1. In alpha_engine/smart_picks_engine.py, add filter: if consensus_count >= 4, exclude pick",
    "2. In elite_scorer.py, increase confluence penalty from -3 to -8 for 4+ agreement",
    "3. Keep contrarian_consensus.py as supplementary signal source",
    "4. Log herding-filtered picks for audit trail"
  ]
}
```

---

### P2-04: Non-Crypto Strategy Quarantine

```json
{
  "id": "P2-04",
  "title": "Quarantine non-crypto strategies — all verified as losing",
  "impact": "MEDIUM",
  "effort_days": 1,
  "status": "PARTIAL — non_crypto_policy.py exists but strategies still generate picks",
  "rationale": "Verified: CRYPTO PF 1.26, +3818% PnL (ONLY profitable class). FOREX PF 0.53, -18%. EQUITY PF 0.63, -617% (hemorrhaging). Non-crypto picks pollute the top-20 leaderboard (CT=F, BAC, COST, PFE, JNJ all in top 10 by score with N/A prices). These are untrackable and losing.",
  "blockers": [],
  "next_steps": [
    "1. In alpha_engine/smart_picks_engine.py, set forward_test_only=True for ALL non-crypto picks",
    "2. Exclude from smart_picks.json output entirely (crypto-only for live picks)",
    "3. Keep generating non-crypto signals but route to separate data/forex_picks.json, data/equity_picks.json",
    "4. Only re-enable when PF > 1.0 on 50+ closed trades per asset class",
    "5. Update PEER_STATUS.md line 120: 'DO NOT IMPLEMENT: Any non-crypto strategies (all losing)'"
  ]
}
```

---

### P2-05: Decile Separation Test Infrastructure

```json
{
  "id": "P2-05",
  "title": "Implement decile separation test for scorer validation",
  "impact": "MEDIUM",
  "effort_days": 3,
  "status": "NOT STARTED",
  "rationale": "ChatGPT called this 'THE validation' — split all closed picks into deciles by score, measure WR per decile. If WR doesn't monotonically increase from D1 to D10, the scorer is adding noise, not signal. Current Q4 vs Q1 separation (75.3% vs 50.7%) is promising but needs finer granularity.",
  "blockers": ["Requires 500+ closed picks for statistical significance at 10 deciles"],
  "next_steps": [
    "1. Create alpha_engine/decile_test.py",
    "2. Load closed_picks.json, compute elite_score for each",
    "3. Split into 10 deciles, compute WR/PF/avg_pnl per decile",
    "4. Report monotonicity score (how many adjacent deciles have correct ordering)",
    "5. Output to data/decile_separation_report.json",
    "6. Run as scheduled GitHub Action (weekly) to track scorer quality over time",
    "7. Wire into audit dashboard as a KPI"
  ]
}
```

---

## Phase 3: Advanced (1-2 weeks, architectural changes)

### P3-01: Full Filter -> Rank -> Size Separation

```json
{
  "id": "P3-01",
  "title": "Refactor pipeline into clean Filter -> Rank -> Size architecture",
  "impact": "HIGH",
  "effort_days": 10,
  "status": "PARTIAL — Filter and Size exist, Rank still coupled to additive scorer",
  "rationale": "Currently, filtering and ranking are entangled in elite_scorer.py (21 components, some act as filters, some as ranking signals). The kill_switch is a proper filter. The Kelly sizer is a proper sizer. But ranking is an additive score that mixes binary gates (regime misalignment cap) with continuous signals (forward WR). Clean separation makes each layer independently testable and improvable.",
  "blockers": ["P2-02 (calibrated P(win)) provides the Rank model", "P1-02/P1-04 (gates wiring) provides the Filter layer"],
  "next_steps": [
    "1. FILTER layer (alpha_engine/quality_filter.py — NEW):",
    "   - kill_switch check (emergency/critical/warning)",
    "   - forward_gate (50+ trades, WR > random)",
    "   - confirmation_gate (MTF + ensemble + HA, from P1-04)",
    "   - R:R >= 1.2 gate",
    "   - consensus <= 3 gate",
    "   - banned system/symbol gate",
    "   - VPIN toxicity gate",
    "   Returns: pass/fail + reason",
    "2. RANK layer (alpha_engine/pick_ranker.py — NEW):",
    "   - P(win) from calibrated model (P2-02)",
    "   - E[return] = P(win) * TP_dist - (1 - P(win)) * SL_dist",
    "   - Marginal portfolio contribution (correlation-adjusted)",
    "   Returns: ranked list with expected value",
    "3. SIZE layer (existing kelly_position_sizer.py):",
    "   - Half-Kelly fraction",
    "   - Vol scaling",
    "   - Correlation penalty",
    "   Returns: position size per pick",
    "4. Orchestrator: production_scanner.py calls Filter -> Rank -> Size in sequence",
    "5. Keep elite_scorer.py as legacy fallback during transition"
  ]
}
```

---

### P3-02: Portfolio-Level Optimization

```json
{
  "id": "P3-02",
  "title": "Implement portfolio-level optimization with correlation caps",
  "impact": "MEDIUM",
  "effort_days": 7,
  "status": "PARTIAL — Kelly sizer has BTC-correlation penalty, no portfolio optimization",
  "rationale": "Currently picks are selected independently (top 11 by score). No consideration of portfolio-level diversification beyond MAX_PICKS_PER_SYMBOL=2 and BTC-correlation penalty. Adding 4 BTC-correlated alts creates concentrated risk even if each pick individually scores well.",
  "blockers": ["P3-01 (Filter->Rank->Size) should be in place first"],
  "next_steps": [
    "1. Create alpha_engine/portfolio_optimizer.py",
    "2. Compute correlation matrix for candidate picks (rolling 30d returns)",
    "3. Constrain: max 15% exposure per symbol, max 40% per sector (DeFi/L1/meme/infra)",
    "4. Objective: maximize E[return] subject to VaR constraint",
    "5. Use simple mean-variance optimization (scipy.optimize.minimize)",
    "6. Replace top-11-by-score with optimizer output in smart_picks_engine.py",
    "7. Track portfolio Sharpe and max drawdown in equity_tracker.py"
  ]
}
```

---

### P3-03: Regime-Specialist Models

```json
{
  "id": "P3-03",
  "title": "Train separate ML models per regime state (BULL/BEAR/CHOP)",
  "impact": "MEDIUM",
  "effort_days": 10,
  "status": "NOT STARTED — regime classification exists, specialist models don't",
  "rationale": "Different features predict winners in different regimes. In BULL markets, momentum features dominate. In BEAR markets, mean-reversion and funding rate features matter more. A single model averages across regimes, diluting regime-specific signal.",
  "blockers": ["P2-01 (ML feature pipeline) must be fixed first", "Need 200+ closed picks per regime state"],
  "next_steps": [
    "1. In alpha_engine/ml_ranker.py, add regime_state to training metadata",
    "2. Split training data by regime (from fast_regime_detector.py or hmm_regime.py)",
    "3. Train 3 separate models: bull_model, bear_model, chop_model",
    "4. At inference time, select model based on current regime",
    "5. Fallback to general model if regime-specific model has <50 training samples",
    "6. Track per-regime accuracy in data/regime_ml_performance.json"
  ]
}
```

---

## Phase 4: Research (ongoing, experimental)

### P4-01: ML Retrain with MFE/MAE Labels

```json
{
  "id": "P4-01",
  "title": "Retrain ML using MFE/MAE as training labels instead of binary win/loss",
  "impact": "MEDIUM",
  "effort_days": 5,
  "status": "NOT STARTED — MFE/MAE data being collected by forward_validator.py",
  "rationale": "Binary win/loss throws away information about HOW a trade won or lost. A trade that hit 90% of TP before reversing to SL is fundamentally different from one that went straight to SL. MFE/MAE labels capture trade quality, not just outcome. Cross-AI consensus item #5.",
  "blockers": ["P2-01 (feature pipeline) should be fixed first", "Need 500+ closed picks with MFE/MAE data"],
  "next_steps": [
    "1. Extract MFE/MAE data from closed_picks.json",
    "2. Create continuous labels: edge_quality = MFE / (MFE + MAE) — ranges 0 to 1",
    "3. Train regression model (not classifier) on edge_quality",
    "4. Use max 5 features (Kimi recommendation): strategy_fwd_wr, confidence, R:R, regime, atr",
    "5. Validate with walk-forward cross-validation (not purged CV which overfits)",
    "6. Deploy as supplementary signal alongside P(win)"
  ]
}
```

---

### P4-02: Adversarial Devil's Advocate Agent

```json
{
  "id": "P4-02",
  "title": "Build adversarial agent that argues against each pick",
  "impact": "LOW",
  "effort_days": 7,
  "status": "NOT STARTED",
  "rationale": "Gemini recommendation. For each candidate pick, generate counter-arguments: resistance levels above entry, bearish divergences, high funding rate, overextended RSI. Quantify bearish evidence as 'adversarial_score'. Picks that survive adversarial scrutiny are stronger. Low priority because the confirmation gates (MTF/ensemble/HA) already serve a similar function.",
  "blockers": ["P1-04 (gate wiring) provides most of the value already"],
  "next_steps": [
    "1. Create alpha_engine/adversarial_agent.py",
    "2. For each pick, check: nearest resistance, RSI divergence, funding rate extreme, OI drop",
    "3. Generate adversarial_score (0-100, higher = more bearish evidence)",
    "4. Picks with adversarial_score > 70 get flagged for manual review",
    "5. Track correlation between adversarial_score and trade outcome"
  ]
}
```

---

### P4-03: Leave-One-Symbol-Out Cross-Validation

```json
{
  "id": "P4-03",
  "title": "Implement LOSO cross-validation for scorer robustness testing",
  "impact": "LOW",
  "effort_days": 3,
  "status": "NOT STARTED",
  "rationale": "ChatGPT recommendation. If removing FETUSDT (153% of total PnL) collapses the system's profitability, the system is not robust — it's a one-symbol wonder. LOSO reveals which symbols are carrying the portfolio and which are dragging it down.",
  "blockers": ["Need 500+ closed picks across 20+ symbols"],
  "next_steps": [
    "1. Create alpha_engine/loso_test.py",
    "2. For each unique symbol in closed_picks.json:",
    "   - Remove all picks for that symbol",
    "   - Recompute portfolio WR, PF, Sharpe, max drawdown",
    "   - If Sharpe drops >50%, flag symbol as 'portfolio dependency'",
    "3. Output data/loso_report.json with per-symbol impact",
    "4. Run weekly as GitHub Action"
  ]
}
```

---

### P4-04: WebSocket Real-Time Data

```json
{
  "id": "P4-04",
  "title": "Migrate from 30-min GH Actions cron to WebSocket streaming",
  "impact": "MEDIUM",
  "effort_days": 14,
  "status": "NOT STARTED",
  "rationale": "Currently running on GitHub Actions every 30 minutes. This means a pick generated at T=0 may not be validated until T=30min, during which the market may have already moved past TP or SL. WebSocket would enable sub-minute signal validation. However, this requires infrastructure changes (VPS, persistent process) that are incompatible with the current GH Actions model.",
  "blockers": ["Requires VPS or cloud hosting (not GH Actions)", "Non-trivial ops burden"],
  "next_steps": [
    "1. Start with hybrid: GH Actions for signal generation, lightweight polling for price checks",
    "2. Deploy Binance WebSocket price feed for top 20 symbols only",
    "3. Run on a $5/mo DigitalOcean droplet",
    "4. Push price updates to forward_validator.py via webhook or shared JSON",
    "5. Full migration to streaming architecture in Phase 5"
  ]
}
```

---

## Implementation Priority Matrix

| Priority | ID | Title | Impact | Effort | Dependencies |
|----------|-----|-------|--------|--------|-------------|
| **1** | P1-01 | Fix R:R scoring weights | HIGH | 0.5d | None |
| **2** | P1-03 | Merge Forward WR + Track Record | HIGH | 1d | None |
| **3** | P1-05 | Reduce Position Performance weight | MEDIUM | 0.5d | None |
| **4** | P1-06 | Confidence bucket recalibration | MEDIUM | 0.5d | None |
| **5** | P1-02 | Wire MTF gate into production | HIGH | 1d | None |
| **6** | P1-04 | Wire Ensemble + HA gates | HIGH | 1.5d | P1-02 |
| **7** | P2-03 | Consensus herding cap | MEDIUM | 1d | None |
| **8** | P2-04 | Non-crypto quarantine | MEDIUM | 1d | None |
| **9** | P2-05 | Decile separation test | MEDIUM | 3d | None |
| **10** | P2-01 | Fix ML feature pipeline | HIGH | 5d | None |
| **11** | P2-02 | Calibrated P(win) scoring | HIGH | 7d | P2-01 |
| **12** | P3-01 | Filter->Rank->Size refactor | HIGH | 10d | P2-02, P1-02, P1-04 |
| **13** | P3-02 | Portfolio optimizer | MEDIUM | 7d | P3-01 |
| **14** | P3-03 | Regime-specialist ML | MEDIUM | 10d | P2-01 |
| **15** | P4-01 | MFE/MAE ML labels | MEDIUM | 5d | P2-01 |
| **16** | P4-03 | LOSO cross-validation | LOW | 3d | None |
| **17** | P4-02 | Adversarial agent | LOW | 7d | P1-04 |
| **18** | P4-04 | WebSocket streaming | MEDIUM | 14d | VPS hosting |

---

## Critical Codebase Findings (Verified Against Claims)

### Bugs Still Active in Production

| Finding | File | Line | Severity |
|---------|------|------|----------|
| R:R 2.0-2.5 awarded 5pts as "sweet spot" — verified 26% WR (WORST bucket) | `elite_scorer.py` | 1081-1083 | **P0** |
| Forward WR (30pts) + Track Record (20pts) double-count from same data | `elite_scorer.py` | 719-813, 1282-1326 | **P1** |
| Winner Filter blocks confidence >0.75 — verified 79.2% WR (BEST bucket) | `forward_validator.py` | Winner Filter section | **P1** |
| MTF/Ensemble/HA gates exist but NOT wired into any production file | `mtf_gate.py`, `ensemble_gate.py`, `ha_ensemble_filter.py` | N/A | **P1** |
| Non-crypto picks in top-20 with N/A prices (untrackable, all losing) | `smart_picks_engine.py` | Top-20 output | **P2** |
| ML ranker BROKEN: 1/46 features alive, AUC=1.0 artifact | `ml_ranker.py` | Feature pipeline | **P2** |

### Components Correctly Disabled (Verified)

| Component | Status | Verification |
|-----------|--------|-------------|
| Session Bonus | DISABLED (set to 0) | `elite_scorer.py` line 1029-1030 |
| Monte Carlo | DISABLED (set to 0) | `elite_scorer.py` line 1105 |
| Meta Label | DISABLED (set to 0) | `elite_scorer.py` line 1213-1214 |
| Hindsight Winner | DISABLED (set to 0) | `elite_scorer.py` line 1221-1223 |
| Skyrocket Potential | DISABLED (set to 0) | `elite_scorer.py` line 1230-1231 |

### Docstring vs Reality Discrepancies

| Claim in Docstring | Reality |
|-------------------|---------|
| elite_scorer.py header lists "Session Bonus (0-5 pts)" | Disabled, always 0 |
| elite_scorer.py header lists "Meta-label (-5 to +3 pts)" | Disabled, always 0 |
| elite_scorer.py header lists "Hindsight winner bonus (0-3 pts)" | Disabled, always 0 |
| elite_scorer.py header lists "Skyrocket potential bonus (0-5 pts)" | Disabled, always 0 |
| SMARTPICKS.MD says "R:R 2.0-2.5 = 73.7% WR" | Verified: 26% WR |
| SMARTPICKS.MD says "Winner Filter: Confidence 0.55-0.75 range" | Best bucket is 0.75-0.80 (79.2% WR) |
| SMARTPICKS.MD says "Forward Gate: Min 4 closed trades" | Code has `FORWARD_GATE_MIN_TRADES = 50` (correctly updated) |

---

## Key Metrics to Track

After implementing Phase 1-2, monitor these KPIs weekly:

1. **Smart Picks WR** — target: >55% (currently ~60% on active batches, but only 1 resolved batch)
2. **Decile Separation** — target: monotonically increasing WR from D1 to D10
3. **Score-to-WR Spearman Correlation** — target: >0.30 (currently 0.423 for elite_score, but 0 for ML)
4. **Profit Factor** — target: >1.5 (currently 1.26 for crypto)
5. **Max Drawdown** — target: <15% (tracked by equity_tracker.py)
6. **False Positive Rate** — picks scored >70 that lose — target: <30%
7. **Gate Pass Rate** — % of raw signals that survive all filters — track to ensure not over-filtering

---

## Appendix: File Reference

| Module | Path | Purpose |
|--------|------|---------|
| Elite Scorer | `alpha_engine/elite_scorer.py` | 21-component additive scoring (main target for reform) |
| Forward Validator | `alpha_engine/forward_validator.py` | MFE/MAE tracking, 50-trade gate, price validation |
| Smart Picks Engine | `alpha_engine/smart_picks_engine.py` | Final pick selection (top 11 from scored pool) |
| Score Booster | `alpha_engine/score_booster.py` | Post-processing family boosts, age decay |
| MTF Gate | `alpha_engine/mtf_gate.py` | Multi-timeframe confirmation (NOT WIRED) |
| Ensemble Gate | `alpha_engine/ensemble_gate.py` | 2-of-3 signal category confirmation (NOT WIRED) |
| HA Ensemble Filter | `alpha_engine/ha_ensemble_filter.py` | Heikin Ashi + 3-indicator (NOT WIRED) |
| Regime Flip Detector | `alpha_engine/regime_flip_detector.py` | BTC regime classification |
| Kill Switch | `alpha_engine/kill_switch.py` | Emergency halt on drawdown/WR collapse |
| Kelly Sizer | `alpha_engine/kelly_position_sizer.py` | Half-Kelly with vol scaling |
| ML Ranker | `alpha_engine/ml_ranker.py` | BROKEN — 1/46 features alive |
| Scanner | `alpha_engine/scanner.py` | Main orchestrator (3800+ lines) |
| Production Scanner | `alpha_engine/production_scanner.py` | Production wrapper with quality gates |
| Config | `alpha_engine/config.py` | MAX_PICKS_PER_SYMBOL=2, asset class defaults |
| Confirmation Gate | `alpha_engine/confirmation_gate.py` | TO BE CREATED (P1-04) |
| Quality Filter | `alpha_engine/quality_filter.py` | TO BE CREATED (P3-01) |
| Pick Ranker | `alpha_engine/pick_ranker.py` | TO BE CREATED (P3-01) |
