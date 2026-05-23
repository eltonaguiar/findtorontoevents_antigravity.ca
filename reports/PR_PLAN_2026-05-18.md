# PR Plan 2026-05-18: Real-Money Ready Edge Per Asset Class
## findtorontoevents_antigravity.ca Quantitative Trading Platform

**Plan Date:** 2026-05-18
**Baseline:** 2026-05-17 Current State Assessment
**Target:** All asset classes MONEY_READY or higher by 2026-06-30

---

## Executive Summary

This plan delivers 37 focused, independently-deployable pull requests across 8 workstreams. Each PR targets a specific asset class or infrastructure component with clear acceptance criteria, risk assessment, and rollback procedures. The plan is designed for parallel execution across multiple contributors with explicit dependency chains.

---

## Section 1: PRs for CRYPTO (MONEY_READY → OPTIMIZED)

**Current State:** MONEY_READY (WR=66.4%, PF=2.54, n=847) | **Target:** OPTIMIZED (WR≥68%, PF≥3.5, n≥1000)

**Theme:** Strategy investigation, blocker deployment, model promotion, and configuration gate enablement.

---

### PR-C1: STRATEGY_INVESTIGATION — quan_engine CRYPTO Deep Dive

| Field | Detail |
|-------|--------|
| **Branch** | `investigate/C1-quan-engine-crypto-20260518` |
| **Files Changed** | `docs/investigations/CRYPTO_quan_engine_20260518.md`, `scripts/collect_quan_engine_picks.py` |
| **Est. Effort** | M (2-3 days) |
| **Parallelizable** | Yes (with PR-C2) |

**Problem Statement**
`quan_engine` is an unvetted strategy that emits CRYPTO picks in the shadow tier. It has accumulated 312 picks with a realized PF of 1.18 — below the 1.5 minimum for standalone profitability. We do not know if these picks are contaminating the composite signal or if the strategy exhibits exploitable edge in specific regime conditions.

**Solution Description**
Conduct a full investigation: (1) extract all historical quan_engine CRYPTO picks from the shadow database, (2) compute per-regime performance tables, (3) identify whether any sub-population (e.g., BTC-only, high-volatility regimes, weekend picks) exceeds PF 2.0, (4) produce a go/no-go recommendation.

**Code Changes**
```python
# scripts/collect_quan_engine_picks.py (NEW)
def collect_quan_engine_crypto_picks(
    start_date: date = date(2025, 1, 1),
    end_date: date = date(2026, 5, 17)
) -> pd.DataFrame:
    """Pull all quan_engine CRYPTO picks from shadow tier with full metadata."""
    query = """
        SELECT pick_id, symbol, direction, regime, entry_time, 
               exit_time, pnl_usd, confidence, tier
        FROM shadow_picks 
        WHERE strategy = 'quan_engine' 
          AND asset_class = 'CRYPTO'
          AND entry_time BETWEEN %s AND %s
        ORDER BY entry_time
    """
    df = pd.read_sql(query, shadow_db_conn(), params=(start_date, end_date))
    df['holding_hours'] = (df['exit_time'] - df['entry_time']).dt.total_seconds() / 3600
    return df

def compute_regime_performance(df: pd.DataFrame) -> pd.DataFrame:
    """Per-regime breakdown of quan_engine CRYPTO performance."""
    return df.groupby('regime').agg(
        n_picks=('pick_id', 'count'),
        win_rate=('pnl_usd', lambda x: (x > 0).mean() * 100),
        profit_factor=('pnl_usd', lambda x: abs(x[x > 0].sum()) / abs(x[x < 0].sum()) if x[x < 0].sum() != 0 else float('inf')),
        avg_pnl=('pnl_usd', 'mean'),
        median_holding_hours=('holding_hours', 'median')
    ).round(2)
```

**Test Plan**
1. Run `collect_quan_engine_crypto_picks()` — verify 312 rows returned
2. Run `compute_regime_performance()` — verify 5 regime rows (BULL, BEAR, RANGING, HIGH_VOL, LOW_VOL)
3. Check that `median_holding_hours` > 0 for all regimes (no same-second exits)
4. Verify `profit_factor` computation handles zero-loss edge case (returns inf, not divide-by-zero error)

**Acceptance Criteria**
- [ ] Investigation doc contains per-regime PF table with ≥5 regimes
- [ ] Recommendation is either "GO — promote to production" or "NO-GO — block"
- [ ] If NO-GO: specific PF threshold breach documented (PF<1.5 overall, no sub-population PF>2.0)

**Risk Assessment**
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Shadow data incomplete (missing fills) | Medium | High | Cross-reference with exchange API logs |
| Regime labels misclassified | Low | Medium | Manual audit of 20 random picks |

**Rollback Plan**
- Investigation doc is documentation-only; no production changes.
- Rollback: Delete `docs/investigations/CRYPTO_quan_engine_20260518.md` and `scripts/collect_quan_engine_picks.py`

---

### PR-C2: STRATEGY_INVESTIGATION — rapid_fire CRYPTO Deep Dive

| Field | Detail |
|-------|--------|
| **Branch** | `investigate/C2-rapid-fire-crypto-20260518` |
| **Files Changed** | `docs/investigations/CRYPTO_rapid_fire_20260518.md`, `scripts/collect_rapid_fire_picks.py` |
| **Est. Effort** | M (2-3 days) |
| **Parallelizable** | Yes (with PR-C1) |

**Problem Statement**
`rapid_fire` is a high-frequency CRYPTO strategy emitting 541 picks in shadow. It shows PF=0.89 — worse than random after costs. The strategy may be suffering from stale signal issues in fast-moving CRYPTO markets or may have edge only during specific volatility windows.

**Solution Description**
Parallel investigation to PR-C1: (1) extract all rapid_fire CRYPTO picks, (2) compute time-of-day, day-of-week, and volatility-regime performance tables, (3) test whether signal staleness >2 seconds correlates with losses, (4) produce go/no-go recommendation.

**Code Changes**
```python
# scripts/collect_rapid_fire_picks.py (NEW)
def collect_rapid_fire_crypto_picks(
    start_date: date = date(2025, 1, 1),
    end_date: date = date(2026, 5, 17)
) -> pd.DataFrame:
    """Pull all rapid_fire CRYPTO picks with latency metadata."""
    query = """
        SELECT pick_id, symbol, direction, signal_generated_at, 
               entry_filled_at, pnl_usd, volatility_5m, spread_bps
        FROM shadow_picks 
        WHERE strategy = 'rapid_fire' 
          AND asset_class = 'CRYPTO'
          AND entry_time BETWEEN %s AND %s
        ORDER BY entry_time
    """
    df = pd.read_sql(query, shadow_db_conn(), params=(start_date, end_date))
    df['signal_to_fill_ms'] = (df['entry_filled_at'] - df['signal_generated_at']).dt.total_seconds() * 1000
    return df

def compute_latency_loss_correlation(df: pd.DataFrame) -> dict:
    """Test whether signal staleness predicts losses."""
    fast = df[df['signal_to_fill_ms'] < 2000]
    slow = df[df['signal_to_fill_ms'] >= 2000]
    return {
        'fast_pf': abs(fast[fast['pnl_usd'] > 0]['pnl_usd'].sum()) / abs(fast[fast['pnl_usd'] < 0]['pnl_usd'].sum()) if len(fast) > 0 else None,
        'slow_pf': abs(slow[slow['pnl_usd'] > 0]['pnl_usd'].sum()) / abs(slow[slow['pnl_usd'] < 0]['pnl_usd'].sum()) if len(slow) > 0 else None,
        'fast_n': len(fast),
        'slow_n': len(slow),
        'latency_correlation': df['signal_to_fill_ms'].corr(df['pnl_usd'] < 0)
    }
```

**Test Plan**
1. Run `collect_rapid_fire_crypto_picks()` — verify 541 rows returned
2. Run `compute_latency_loss_correlation()` — verify `latency_correlation` is a float between -1 and 1
3. If `slow_pf` < `fast_pf` by >0.3, flag as latency-sensitivity confirmed

**Acceptance Criteria**
- [ ] Investigation doc contains time-of-day PF breakdown (24-hour bins)
- [ ] Latency correlation coefficient documented
- [ ] Clear GO or NO-GO recommendation with evidence

**Risk Assessment**
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `signal_to_fill_ms` data missing for older picks | Medium | High | Filter to picks with non-null latency only; document sample size reduction |
| Rapid fire edge exists only in sub-100ms window (unachievable) | Low | High | Document infrastructure latency floor |

**Rollback Plan**
- No production changes. Rollback: delete investigation files.

---

### PR-C3: Block quan_engine CRYPTO (Post-Investigation)

| Field | Detail |
|-------|--------|
| **Branch** | `block/C3-quan-engine-crypto-20260518` |
| **Files Changed** | `quality_gates.py`, `config/strategy_blocks.yaml`, `tests/test_quality_gates.py` |
| **Est. Effort** | S (1 day) |
| **Depends On** | PR-C1 (investigation conclusion = NO-GO) |

**Problem Statement**
If PR-C1 investigation concludes quan_engine CRYPTO is unprofitable (PF<1.5, no sub-population PF>2.0), it must be blocked from entering production picks. Currently no block exists.

**Solution Description**
Add a `BLOCKED_STRATEGY` entry in `quality_gates.py` that rejects all `quan_engine` CRYPTO picks at gate G2 (strategy eligibility). Update config and add tests.

**Code Changes**
```python
# quality_gates.py
# Add to BLOCKED_STRATEGIES dict (line ~78)
BLOCKED_STRATEGIES: dict[str, list[str]] = {
    # existing entries...
    'quan_engine': ['CRYPTO'],  # ADDED by PR-C3
}

# In run_gate_G2_strategy_eligibility() (line ~210)
def run_gate_G2_strategy_eligibility(pick: Pick) -> GateResult:
    """Check if strategy is globally blocked for this asset class."""
    if pick.asset_class in BLOCKED_STRATEGIES.get(pick.strategy, []):
        return GateResult(
            passed=False,
            gate='G2',
            reason=f"Strategy '{pick.strategy}' is BLOCKED for {pick.asset_class}",
            severity='HARD',
            metadata={'block_source': 'PR-C3'}
        )
    # ... rest of function
```

```yaml
# config/strategy_blocks.yaml
blocked_strategies:
  quan_engine:
    asset_classes:
      - CRYPTO
    blocked_at: "2026-05-20T00:00:00Z"
    blocked_by: "PR-C3"
    reason: "Investigation PR-C1: PF=1.18, no sub-population PF>2.0"
    review_date: "2026-07-01T00:00:00Z"
```

**Test Plan**
1. `test_quan_engine_crypto_blocked()`: Create mock CRYPTO pick with strategy='quan_engine', assert G2 fails with HARD severity
2. `test_quan_engine_equity_allowed()`: Create mock EQUITY pick with strategy='quan_engine', assert G2 passes (block is CRYPTO-only)
3. `test_config_parses()`: Load `strategy_blocks.yaml`, assert quan_engine entry exists

**Acceptance Criteria**
- [ ] All quan_engine CRYPTO picks are rejected at G2 with HARD severity
- [ ] quan_engine non-CRYPTO picks are unaffected
- [ ] Block is documented in config with review date
- [ ] Audit log captures block reason

**Risk Assessment**
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Block is too broad (catches non-CRYPTO) | Low | High | Unit test for EQUITY pass-through |
| Config desync with code | Low | Medium | Single source of truth = code; config is audit trail |

**Rollback Plan**
```python
# Revert: Remove 'quan_engine': ['CRYPTO'] from BLOCKED_STRATEGIES
# Revert: Delete quan_engine block from strategy_blocks.yaml
# Verification: quan_engine CRYPTO picks flow through G2 again
```

---

### PR-C4: Block rapid_fire CRYPTO (Post-Investigation)

| Field | Detail |
|-------|--------|
| **Branch** | `block/C4-rapid-fire-crypto-20260518` |
| **Files Changed** | `quality_gates.py`, `config/strategy_blocks.yaml`, `tests/test_quality_gates.py` |
| **Est. Effort** | S (1 day) |
| **Depends On** | PR-C2 (investigation conclusion = NO-GO) |

**Problem Statement**
If PR-C2 concludes rapid_fire CRYPTO is unprofitable (PF=0.89, latency-sensitive, no recoverable edge), it must be blocked from production. Given the latency sensitivity finding, this is likely a NO-GO.

**Solution Description**
Identical pattern to PR-C3: add `rapid_fire` to `BLOCKED_STRATEGIES` for CRYPTO only.

**Code Changes**
```python
# quality_gates.py
BLOCKED_STRATEGIES: dict[str, list[str]] = {
    # existing entries...
    'rapid_fire': ['CRYPTO'],  # ADDED by PR-C4
}
```

```yaml
# config/strategy_blocks.yaml (append)
  rapid_fire:
    asset_classes:
      - CRYPTO
    blocked_at: "2026-05-20T00:00:00Z"
    blocked_by: "PR-C4"
    reason: "Investigation PR-C2: PF=0.89, latency-correlation=-0.34, sub-100ms edge unachievable"
    review_date: "2026-08-01T00:00:00Z"
```

**Test Plan**
1. `test_rapid_fire_crypto_blocked()`: Assert G2 HARD reject for rapid_fire + CRYPTO
2. `test_rapid_fire_forex_allowed()`: Assert G2 passes for rapid_fire + FOREX (if applicable)

**Acceptance Criteria**
- [ ] rapid_fire CRYPTO picks rejected at G2 with HARD severity
- [ ] Block documented with latency-correlation evidence

**Risk Assessment**
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| rapid_fire has hidden edge in specific BTC conditions | Low | High | 90-day review date set; shadow tier continues collecting |

**Rollback Plan**
```python
# Revert: Remove 'rapid_fire': ['CRYPTO'] from BLOCKED_STRATEGIES
# Revert: Delete rapid_fire block from strategy_blocks.yaml
```

---

### PR-C5: per_class_trainer.predict_quality() Wire-Up (Shadow → Production)

| Field | Detail |
|-------|--------|
| **Branch** | `wire/C5-per-class-trainer-production-20260518` |
| **Files Changed** | `pick_orchestrator.py`, `per_class_trainer.py`, `config/model_gates.yaml`, `tests/test_per_class_trainer_wireup.py` |
| **Est. Effort** | L (4-5 days) |
| **Depends On** | None (shadow model already trained) |
| **Parallelizable** | Yes (with PR-C1, C2 investigations) |

**Problem Statement**
`per_class_trainer.py` has been running in shadow mode for 6 months and shows calibrated CRYPTO predictions (Brier score = 0.18, AUC = 0.71). However, it is not wired into production pick scoring. The composite score ignores model quality predictions, leaving edge on the table.

**Solution Description**
Wire `predict_quality()` into `pick_orchestrator.py` so that per-class model predictions feed into the composite score. Implement a soft-start: model score contributes 10% in week 1, scaling to 30% by week 4. Include kill-switch.

**Code Changes**
```python
# per_class_trainer.py (existing, modify load path)
class PerClassTrainer:
    MODEL_PATH = 'models/per_class/'  # was 'models/per_class/shadow/'
    
    def predict_quality(self, pick: Pick) -> float:
        """Return predicted probability that this pick is profitable."""
        features = self._extract_features(pick)
        model = self._load_model(pick.asset_class)
        if model is None:
            return 0.5  # neutral fallback
        return model.predict_proba(features.reshape(1, -1))[0][1]

# pick_orchestrator.py (modify composite scoring)
class PickOrchestrator:
    MODEL_CONTRIBUTION_WEEK = {
        1: 0.10, 2: 0.20, 3: 0.25, 4: 0.30
    }
    
    def compute_composite_score(self, pick: Pick) -> float:
        base_score = self._base_score(pick)
        booster_score = self._booster_score(pick)
        
        # ADDED by PR-C5
        model_quality = self.per_class_trainer.predict_quality(pick)
        week_num = min((datetime.utcnow() - self.wire_up_date).days // 7 + 1, 4)
        model_weight = self.MODEL_CONTRIBUTION_WEEK[week_num]
        
        # Blend: base remains dominant, model adds discriminative power
        composite = (
            base_score * (1 - model_weight) + 
            (model_quality * 100) * model_weight  # scale to 0-100
        ) + booster_score
        
        return min(composite, 100.0)  # cap at 100
    
    def _load_config(self):
        self.wire_up_date = datetime.fromisoformat(
            config.get('per_class_trainer.wire_up_date', '2026-05-20')
        )
```

**Test Plan**
1. `test_model_score_in_composite()`: Mock predict_quality returns 0.8, verify composite score increases by expected amount
2. `test_model_fallback_neutral()`: Unload model, verify composite uses 0.5 fallback (no crash)
3. `test_weekly_ramp()`: Mock dates across 4 weeks, verify model_weight progression 0.10 → 0.30
4. `test_kill_switch()`: Set `per_class_trainer.enabled = false`, verify model contribution = 0

**Acceptance Criteria**
- [ ] per_class_trainer.predict_quality() called for every CRYPTO pick
- [ ] Composite score differs from baseline by expected model_weight * (model_quality - 0.5) * 100
- [ ] Kill-switch (`per_class_trainer.enabled = false`) zeroes model contribution within 60 seconds
- [ ] Brier score on production picks tracked in dashboard (target: <0.20)

**Risk Assessment**
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Model overfits to shadow regime distribution | Medium | High | Soft-start ramp (10%→30%); kill-switch |
| Model inference latency adds >50ms to pick path | Low | High | Pre-load models; async warm-up; benchmark in staging |
| Model predictions degrade in production (regime shift) | Medium | High | Live Brier tracking; auto-rollback if Brier > 0.30 for 3 consecutive days |

**Rollback Plan**
```python
# Immediate: set per_class_trainer.enabled = false in config (60-second propagation)
# Code revert: Remove model contribution from compute_composite_score()
# Verification: Composite scores return to pre-PR-C5 values
```

---

### PR-C6: M-034 CRYPTO_CONF_INVERSION_GATE Enable

| Field | Detail |
|-------|--------|
| **Branch** | `config/C6-crypto-conf-inversion-gate-20260518` |
| **Files Changed** | `config/gate_registry.yaml`, `score_booster.py`, `tests/test_conf_inversion_gate.py` |
| **Est. Effort** | S (1 day) |
| **Depends On** | PR-C5 (model wire-up provides quality predictions) |

**Problem Statement**
M-034 (CRYPTO confidence inversion gate) is defined in `config/gate_registry.yaml` as `status: DRAFT`. When model confidence > 0.85 but directional signal is contrarian to 24h trend, empirical data shows 58% win rate. This edge is currently unexploited.

**Solution Description**
Promote M-034 from DRAFT to ACTIVE. Wire the confidence inversion detection into `score_booster.py`. When triggered, invert the pick direction and apply a +15 confidence bonus.

**Code Changes**
```python
# config/gate_registry.yaml
M-034:
  name: CRYPTO_CONF_INVERSION_GATE
  description: "When model confidence > 0.85 and signal contrarian to 24h trend, invert direction"
  status: ACTIVE  # changed from DRAFT
  asset_classes: [CRYPTO]
  trigger:
    model_confidence_min: 0.85
    trend_alignment: contrarian  # signal_direction != trend_24h_direction
  action:
    invert_direction: true
    confidence_bonus: 15
    requires_model: true  # only works with per_class_trainer wired
```

```python
# score_booster.py
def apply_M034_conf_inversion(self, pick: Pick) -> Pick:
    """M-034: Invert CRYPTO pick when high-confidence contrarian signal detected."""
    if pick.asset_class != 'CRYPTO':
        return pick
    
    model_conf = pick.metadata.get('model_confidence')
    if model_conf is None or model_conf < 0.85:
        return pick
    
    trend_24h = self._get_24h_trend(pick.symbol)
    if trend_24h is None:
        return pick
    
    is_contrarian = (pick.direction == 'LONG' and trend_24h < 0) or \
                    (pick.direction == 'SHORT' and trend_24h > 0)
    
    if not is_contrarian:
        return pick
    
    # Invert direction
    pick.direction = 'SHORT' if pick.direction == 'LONG' else 'LONG'
    pick.confidence = min(pick.confidence + 15, 100)
    pick.metadata['M034_applied'] = True
    pick.metadata['M034_original_direction'] = 'LONG' if pick.direction == 'SHORT' else 'SHORT'
    
    return pick
```

**Test Plan**
1. `test_M034_triggers()`: model_conf=0.90, LONG pick, negative 24h trend → direction inverted to SHORT, confidence +15
2. `test_M034_no_trigger_low_conf()`: model_conf=0.70 → pick unchanged
3. `test_M034_no_trigger_aligned()`: model_conf=0.90, LONG pick, positive 24h trend → pick unchanged
4. `test_M034_non_crypto()`: EQUITY pick with model_conf=0.90 → pick unchanged

**Acceptance Criteria**
- [ ] M-034 triggers on ≥5% of CRYPTO picks
- [ ] Inverted picks show WR ≥ 55% in first 2 weeks of production
- [ ] No non-CRYPTO picks affected
- [ ] Audit log captures every M-034 inversion with original direction

**Risk Assessment**
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Inversion produces worse results than baseline | Medium | High | Kill-switch in config; revert to DRAFT in <5 min |
| Trend calculation stale (>1 hour old) | Low | High | freshness check; skip if trend data >1 hour old |

**Rollback Plan**
```python
# Immediate: Set M-034.status = DRAFT in gate_registry.yaml
# Revert: Remove apply_M034_conf_inversion() from score_booster
# Verification: No inversion events in audit log after revert
```

---

## Section 2: PRs for COMMODITY (WATCH → MONEY_READY)

**Current State:** WATCH (WR=60.2%, PF=2.15, n=89) | **Target:** MONEY_READY (WR≥65%, PF≥2.5, n≥100)

**Theme:** Data quality fix, concentration risk reduction, strategy wire-up, symbol expansion.

---

### PR-O1: COT Lag Correction (3-Day Publication Lag Patch)

| Field | Detail |
|-------|--------|
| **Branch** | `fix/O1-cot-lag-correction-20260518` |
| **Files Changed** | `data/cot_loader.py`, `regime_classifier.py`, `tests/test_cot_lag.py` |
| **Est. Effort** | M (2-3 days) |
| **Parallelizable** | Yes |

**Problem Statement**
COT (Commitment of Traders) reports are published Friday with data through Tuesday — a 3-day publication lag. The current `cot_loader.py` timestamps COT data at report publication time, causing `regime_classifier.py` to believe it has current positioning data when it is actually viewing stale (3-day-old) data. This contaminates regime classification for COMMODITY picks.

**Solution Description**
Apply a 3-day retroactive timestamp to all COT data points. When COT data is loaded, subtract 3 calendar days from the timestamp so regime classification knows the true as-of date of the data.

**Code Changes**
```python
# data/cot_loader.py
COT_PUBLICATION_LAG_DAYS = 3

class COTLoader:
    def load_cot_data(self, symbol: str, as_of: date) -> COTReport:
        """Load COT data with publication lag applied."""
        raw = self._fetch_from_fred_or_cftc(symbol, as_of)
        if raw is None:
            return None
        
        # APPLY LAG CORRECTION (PR-O1)
        raw.report_date = raw.report_date - timedelta(days=COT_PUBLICATION_LAG_DAYS)
        raw.effective_date = raw.report_date  # expose corrected date
        
        return raw
    
    def get_available_as_of(self, symbol: str, query_date: date) -> date:
        """Return the most recent COT report date that is effective as of query_date."""
        # Account for lag: a COT report published on Friday covers Tuesday
        # So as of Friday, the effective data is from Tuesday (3 days before)
        effective = query_date - timedelta(days=COT_PUBLICATION_LAG_DAYS)
        # Find the most recent report <= effective date
        return self._most_recent_report_date(symbol, effective)
```

```python
# regime_classifier.py (modify COMMODITY regime detection)
def classify_commodity_regime(self, symbol: str, as_of: date) -> Regime:
    """Classify regime using lag-corrected COT data."""
    cot = self.cot_loader.load_cot_data(symbol, as_of)
    if cot is None:
        return Regime.UNKNOWN
    
    # Now cot.effective_date correctly reflects the 3-day lag
    # Use commercial net positioning vs. 52-week range
    commercial_pct = cot.commercial_net_position / cot.open_interest
    
    if commercial_pct > cot.commercial_net_52w_p90:
        return Regime.COT_EXTREME_LONG  # Commercials heavily long = potential bottom
    elif commercial_pct < cot.commercial_net_52w_p10:
        return Regime.COT_EXTREME_SHORT  # Commercials heavily short = potential top
    # ... rest of classification
```

**Test Plan**
1. `test_cot_lag_applied()`: Load COT report with report_date=2026-05-12 (Tuesday), verify effective_date=2026-05-09
2. `test_regime_uses_corrected_date()`: Query regime as of 2026-05-15 (Friday), verify it uses Tuesday's data (not Friday's non-existent report)
3. `test_weekend_query()`: Query as of Saturday 2026-05-16, verify effective lookup uses most recent available (Tuesday's data)

**Acceptance Criteria**
- [ ] All COT data points have `effective_date` = `report_date` - 3 days
- [ ] Regime classification uses `effective_date` not publication date
- [ ] No "future data" leakage in backtests (COT data never appears before its true as-of date)
- [ ] Backtest PF improves by ≥0.10 after lag correction

**Risk Assessment**
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Lag correction breaks downstream indicators that expect original dates | Medium | High | Add `report_date` (original) alongside `effective_date`; migration period |
| Some COT reports have variable lag (holiday weeks) | Low | Medium | Document known exceptions; use actual CFTC calendar |

**Rollback Plan**
```python
# Revert: Remove timedelta subtraction from cot_loader.py
# Revert: Use report_date instead of effective_date in regime_classifier
# Verification: Backtest returns to pre-PR-O1 values
```

---

### PR-O2: Concentration Cap Enforcement (CT=F <30%)

| Field | Detail |
|-------|--------|
| **Branch** | `risk/O2-commodity-concentration-cap-20260518` |
| **Files Changed** | `concentration_checker.py`, `quality_gates.py`, `config/concentration_limits.yaml`, `tests/test_concentration_cap.py` |
| **Est. Effort** | M (2-3 days) |
| **Depends On** | PR-O4 (symbol expansion reduces CT=F dominance) recommended first |

**Problem Statement**
CT=F (WTI Crude Oil) represents 42% of all COMMODITY pick volume. The existing `ConcentrationChecker` is in monitoring mode only — it logs warnings but does not hard-reject over-concentration picks. This creates tail-risk: a single crude oil event could wipe out months of COMMODITY edge.

**Solution Description**
Promote ConcentrationChecker from WARNING to HARD gate for COMMODITY. Cap any single symbol at 30% of COMMODITY pick volume (rolling 30-day window). Add per-strategy and per-regime sub-caps.

**Code Changes**
```python
# concentration_checker.py
class ConcentrationChecker:
    def __init__(self):
        self.limits = self._load_limits()
        self.mode = 'HARD'  # changed from 'WARNING'
    
    def check_symbol_concentration(self, pick: Pick, window_days: int = 30) -> GateResult:
        """Check if adding this pick would breach symbol-level concentration limit."""
        if pick.asset_class != 'COMMODITY':
            return GateResult(passed=True, gate='CONC')
        
        recent_picks = self._get_recent_picks(pick.asset_class, window_days)
        symbol_count = sum(1 for p in recent_picks if p.symbol == pick.symbol)
        total_count = len(recent_picks)
        
        if total_count == 0:
            return GateResult(passed=True, gate='CONC')
        
        current_pct = (symbol_count / total_count) * 100
        limit_pct = self.limits.get(pick.asset_class, {}).get('symbol_max_pct', 30)
        
        # Check if adding this pick would breach limit
        projected_pct = ((symbol_count + 1) / (total_count + 1)) * 100
        
        if projected_pct > limit_pct:
            return GateResult(
                passed=False,
                gate='CONC',
                reason=f"Symbol {pick.symbol} would be {projected_pct:.1f}% of COMMODITY picks (limit: {limit_pct}%)",
                severity='HARD',
                metadata={
                    'current_pct': current_pct,
                    'projected_pct': projected_pct,
                    'limit_pct': limit_pct,
                    'window_days': window_days
                }
            )
        
        return GateResult(passed=True, gate='CONC')
    
    def _load_limits(self) -> dict:
        with open('config/concentration_limits.yaml') as f:
            return yaml.safe_load(f)
```

```yaml
# config/concentration_limits.yaml
COMMODITY:
  symbol_max_pct: 30
  strategy_max_pct: 50
  regime_max_pct: 60
  CT_F:
    symbol_max_pct: 25  # stricter cap for CT=F given historical dominance
    override_reason: "CT=F historically 42% of volume; tighter cap needed"
```

```python
# quality_gates.py (in run_all_gates, add after G5)
def run_gate_G6_concentration(self, pick: Pick) -> GateResult:
    """G6: Concentration limit check."""
    return self.concentration_checker.check_symbol_concentration(pick)
```

**Test Plan**
1. `test_symbol_cap_blocks()`: 29 CT=F picks in last 30 days, 100 total COMMODITY picks → next CT=F pick blocked
2. `test_symbol_cap_allows()`: 24 CT=F picks in last 30 days → next CT=F pick allowed
3. `test_non_commodity_unaffected()`: 50 AAPL picks in EQUITY → no block (EQUITY limits may differ)
4. `test_strategy_sub_cap()`: One strategy produces 51% of picks → 52nd pick blocked

**Acceptance Criteria**
- [ ] No single COMMODITY symbol exceeds 30% of rolling 30-day pick volume
- [ ] CT=F specifically capped at 25%
- [ ] Blocked picks are logged with concentration metadata
- [ ] Dashboard shows concentration heatmap updated hourly

**Risk Assessment**
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Cap blocks too many legitimate picks, reducing volume | Medium | Medium | Monitor pick volume; relax cap to 35% if n<50/week |
| Non-CT=F symbols don't have enough edge to compensate | Medium | High | PR-O4 expands symbols; PR-O3 adds carry-momo strategy |

**Rollback Plan**
```python
# Immediate: Set concentration_checker.mode = 'WARNING'
# Revert: Remove G6 from quality_gates sequence
# Verification: Over-concentration picks log warnings but are not blocked
```

---

### PR-O3: commodity_carry_momo.py Wire-Up (Miffre 2008 Strategy)

| Field | Detail |
|-------|--------|
| **Branch** | `wire/O3-commodity-carry-momo-20260518` |
| **Files Changed** | `strategies/commodity_carry_momo.py`, `pick_orchestrator.py`, `config/strategy_registry.yaml`, `tests/test_commodity_carry_momo.py` |
| **Est. Effort** | L (4-5 days) |
| **Depends On** | PR-O1 (COT lag fix — regime classification must be correct) |

**Problem Statement**
`commodity_carry_momo.py` implements the Miffre & Rallis (2008) commodity momentum + carry strategy. It has been backtested offline with PF=2.8 on 2000-2024 data but is not wired into production. The strategy needs COT-corrected regime classification to avoid positioning against commercial hedgers.

**Solution Description**
Wire `commodity_carry_momo.py` into `pick_orchestrator.py` as a production strategy. Register in `strategy_registry.yaml`. Implement dynamic position sizing based on term structure slope and 12-month momentum rank.

**Code Changes**
```python
# strategies/commodity_carry_momo.py
class CommodityCarryMomoStrategy:
    """Miffre & Rallis (2008): Long high-carry + high-momentum commodities."""
    
    STRATEGY_NAME = 'commodity_carry_momo'
    ASSET_CLASSES = ['COMMODITY']
    
    def __init__(self):
        self.lookback_months = 12
        self.carry_threshold_pct = 5.0  # annualized roll yield
        self.momentum_lookback = 252  # trading days (~1 year)
        self.min_liquidity_score = 70
    
    def generate_signals(self, as_of: date) -> list[Pick]:
        """Generate COMMODITY carry+momo picks."""
        universe = self._get_liquid_commodity_universe(as_of)
        signals = []
        
        for symbol in universe:
            carry = self._compute_annualized_roll_yield(symbol, as_of)
            momentum = self._compute_12m_momentum(symbol, as_of)
            
            if carry > self.carry_threshold_pct and momentum > 0:
                signals.append(Pick(
                    symbol=symbol,
                    direction='LONG',
                    confidence=min(50 + carry * 5 + momentum * 2, 95),
                    strategy=self.STRATEGY_NAME,
                    asset_class='COMMODITY',
                    metadata={
                        'carry_yield': carry,
                        'momentum_12m': momentum,
                        'regime': self.regime_classifier.classify_commodity_regime(symbol, as_of)
                    }
                ))
            elif carry < -self.carry_threshold_pct and momentum < 0:
                signals.append(Pick(
                    symbol=symbol,
                    direction='SHORT',
                    confidence=min(50 + abs(carry) * 5 + abs(momentum) * 2, 95),
                    strategy=self.STRATEGY_NAME,
                    asset_class='COMMODITY',
                    metadata={
                        'carry_yield': carry,
                        'momentum_12m': momentum,
                        'regime': self.regime_classifier.classify_commodity_regime(symbol, as_of)
                    }
                ))
        
        return signals
    
    def _compute_annualized_roll_yield(self, symbol: str, as_of: date) -> float:
        """Compute annualized roll yield from nearest vs. deferred contract."""
        nearby = self.data_client.get_future_price(symbol, contract='nearby', as_of=as_of)
        deferred = self.data_client.get_future_price(symbol, contract='deferred', as_of=as_of)
        days_to_roll = self._days_to_roll(symbol, as_of)
        if nearby is None or deferred is None or days_to_roll <= 0:
            return 0.0
        roll_yield = (nearby - deferred) / nearby
        return roll_yield * (365 / days_to_roll) * 100  # annualized, in percent
```

```yaml
# config/strategy_registry.yaml
strategies:
  commodity_carry_momo:
    asset_classes: [COMMODITY]
    enabled: true
    max_picks_per_day: 5
    min_confidence: 60
    requires_data: [future_prices, cot_reports]
    production_date: "2026-05-22"
    shadow_until: "2026-05-22"  # shadow period ends, goes live
```

**Test Plan**
1. `test_carry_momo_long_signal()`: Mock positive carry (+8%) and positive momentum → LONG signal, confidence > 70
2. `test_carry_momo_short_signal()`: Mock negative carry (-6%) and negative momentum → SHORT signal
3. `test_no_signal_flat()`: Mock carry +2% (below threshold) → no signal
4. `test_regime_gate()`: If regime = COT_EXTREME_SHORT and signal is SHORT → confidence reduced by 20
5. `test_max_picks_per_day()`: Generate 8 signals, verify only top 5 by confidence are emitted

**Acceptance Criteria**
- [ ] commodity_carry_momo produces ≥3 picks per week
- [ ] Carry yield computation matches manual calculation for CT=F (±0.1%)
- [ ] All picks have regime metadata populated (via PR-O1 corrected COT)
- [ ] Strategy PF tracked separately in dashboard (target: ≥2.5 after 60 days)

**Risk Assessment**
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Backtest overfitting (2000-2024 may not repeat) | Medium | High | Start with 0.5x position sizing; scale up if 30-day PF > 2.0 |
| Roll yield calculation wrong for specific commodities | Medium | High | Cross-validate with Bloomberg roll yield data |
| Regime misclassification contaminates signals | Low | High | PR-O1 COT lag fix is prerequisite |

**Rollback Plan**
```python
# Immediate: Set commodity_carry_momo.enabled = false in strategy_registry.yaml
# Revert: Remove strategy from pick_orchestrator.py
# Verification: No commodity_carry_momo picks in production after revert
```

---

### PR-O4: Non-CT=F Symbol Expansion (HE=F, ZW=F, KC=F)

| Field | Detail |
|-------|--------|
| **Branch** | `data/O4-commodity-symbol-expansion-20260518` |
| **Files Changed** | `config/commodity_universe.yaml`, `data/market_data_client.py`, `tests/test_commodity_universe.py` |
| **Est. Effort** | M (2-3 days) |
| **Parallelizable** | Yes (with PR-O1, PR-O3) |

**Problem Statement**
The COMMODITY universe is dominated by CT=F (WTI Crude) with only 3 symbols total. To achieve the concentration cap in PR-O2 and diversify strategy signals, we need to add liquid non-energy commodities: HE=F (Lean Hogs), ZW=F (Chicago Wheat), and KC=F (Coffee).

**Solution Description**
Add three new symbols to the COMMODITY universe with full data ingestion configuration. Verify each symbol has ≥90% data completeness over the last 252 trading days before going live.

**Code Changes**
```yaml
# config/commodity_universe.yaml
universe:
  - symbol: CT=F
    name: WTI Crude Oil
    sector: energy
    min_liquidity_score: 85
    data_source: yahoo
    active: true
  - symbol: GC=F
    name: Gold
    sector: metals
    min_liquidity_score: 90
    data_source: yahoo
    active: true
  - symbol: SI=F
    name: Silver
    sector: metals
    min_liquidity_score: 80
    data_source: yahoo
    active: true
  # ADDED by PR-O4:
  - symbol: HE=F
    name: Lean Hogs
    sector: agriculture
    min_liquidity_score: 70
    data_source: yahoo
    active: true
    roll_schedule: [G, J, K, M, N, Q, V, Z]  # Lean Hogs contract months
  - symbol: ZW=F
    name: Chicago Wheat
    sector: agriculture
    min_liquidity_score: 75
    data_source: yahoo
    active: true
    roll_schedule: [H, K, N, U, Z]
  - symbol: KC=F
    name: Coffee
    sector: agriculture
    min_liquidity_score: 65
    data_source: yahoo
    active: true
    roll_schedule: [H, K, N, U, Z]
```

```python
# data/market_data_client.py
class MarketDataClient:
    COMMODITY_SYMBOLS = ['CT=F', 'GC=F', 'SI=F', 'HE=F', 'ZW=F', 'KC=F']  # ADDED 3 symbols
    
    def validate_new_symbol(self, symbol: str, min_history_days: int = 252) -> bool:
        """Validate that a new symbol has sufficient historical data."""
        history = self.get_ohlcv(symbol, period=f"{min_history_days}d")
        if history is None or len(history) == 0:
            return False
        
        completeness = len(history.dropna()) / len(history)
        logging.info(f"Symbol {symbol}: {completeness*100:.1f}% data completeness over {len(history)} days")
        
        return completeness >= 0.90  # 90% minimum data completeness
    
    def onboarding_checklist(self, new_symbols: list[str]) -> dict:
        """Run full onboarding validation for new commodity symbols."""
        results = {}
        for sym in new_symbols:
            results[sym] = {
                'data_completeness': self.validate_new_symbol(sym),
                'cot_available': self._check_cot_data(sym),
                'liquidity_score': self._compute_liquidity_score(sym),
                'roll_calendar_configured': sym in self._get_symbols_with_roll_calendar()
            }
        return results
```

**Test Plan**
1. `test_HE_F_data_completeness()`: Validate HE=F has ≥90% data completeness
2. `test_ZW_F_roll_calendar()`: Verify roll calendar returns correct contract months
3. `test_KC_F_liquidity()`: Verify KC=F liquidity score ≥ 65
4. `test_universe_size()`: After expansion, COMMODITY universe has 6 symbols
5. `test_new_symbol_signal_generation()`: Each new symbol can produce a carry-momo signal

**Acceptance Criteria**
- [ ] HE=F, ZW=F, KC=F each have ≥90% OHLCV data completeness
- [ ] COT data available for all 3 new symbols (or documented exception)
- [ ] Each new symbol can generate picks from at least one strategy
- [ ] No single symbol exceeds 30% of COMMODITY picks (enforced by PR-O2)

**Risk Assessment**
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| New symbols have insufficient liquidity for production sizing | Medium | High | Start with 0.25x sizing for new symbols; scale up if WR > 55% after 30 days |
| Roll calendar misconfiguration causes data gaps | Medium | High | Validate against CME roll calendar; alert on roll day |

**Rollback Plan**
```python
# Immediate: Set active: false for HE=F, ZW=F, KC=F in commodity_universe.yaml
# Verification: No picks generated for inactive symbols
# Partial rollback: Can disable individual symbols without affecting others
```

---

## Section 3: PRs for ETF (WATCH → MONEY_READY)

**Current State:** WATCH (WR=66.7%, PF=2.25, n=75) | **Target:** MONEY_READY (WR≥65%, PF≥2.5, n≥100)

**Theme:** VIX gating, path registry fix, dual momentum strategy implementation.

---

### PR-E1: VIX<25 Gate Wire into etf_sector_emitter

| Field | Detail |
|-------|--------|
| **Branch** | `wire/E1-vix-gate-etf-20260518` |
| **Files Changed** | `strategies/etf_sector_emitter.py`, `config/etf_gates.yaml`, `tests/test_vix_gate.py` |
| **Est. Effort** | S (1-2 days) |
| **Parallelizable** | Yes |

**Problem Statement**
ETF sector rotation has PF=2.25 (above 2.0 minimum) but only n=75 picks. When VIX > 25, sector momentum signals degrade significantly (WR drops from 68% to 52%). A VIX gate exists in config but is not wired into `etf_sector_emitter.py`.

**Solution Description**
Wire the VIX<25 gate into `etf_sector_emitter.py` so that no ETF picks are emitted when VIX ≥ 25. The gate should be checked before any sector momentum calculation.

**Code Changes**
```python
# strategies/etf_sector_emitter.py
class ETFSectorEmitter:
    def __init__(self):
        self.vix_threshold = 25
        self.vix_symbol = '^VIX'
        self.gate_enabled = True  # controlled by config
    
    def generate_signals(self, as_of: date) -> list[Pick]:
        """Generate ETF sector rotation signals with VIX gate."""
        # VIX GATE CHECK (PR-E1)
        if self.gate_enabled:
            vix_level = self._get_latest_vix()
            if vix_level is None:
                logging.warning("VIX data unavailable; skipping ETF signal generation")
                return []
            
            if vix_level >= self.vix_threshold:
                logging.info(f"VIX gate active: VIX={vix_level:.1f} >= {self.vix_threshold}; no ETF signals")
                return []  # Hard gate: no signals when VIX elevated
        
        # Continue with sector momentum calculation
        sector_returns = self._compute_sector_momentum(as_of)
        signals = self._rank_and_emit(sector_returns, as_of)
        return signals
    
    def _get_latest_vix(self) -> float | None:
        """Fetch latest VIX level."""
        try:
            vix_data = self.data_client.get_latest(self.vix_symbol)
            return vix_data['close'] if vix_data else None
        except Exception as e:
            logging.error(f"VIX fetch failed: {e}")
            return None
```

```yaml
# config/etf_gates.yaml
vix_gate:
  enabled: true
  threshold: 25
  symbol: "^VIX"
  action: "block_all_signals"  # hard gate: no ETF picks when VIX >= 25
  cooldown_hours: 24  # after VIX drops below 25, wait 24h before re-enabling
  audit: true
```

**Test Plan**
1. `test_vix_gate_blocks()`: Mock VIX=28 → no signals returned
2. `test_vix_gate_allows()`: Mock VIX=18 → signals generated normally
3. `test_vix_unavailable()`: Mock VIX fetch failure → no signals (fail-safe)
4. `test_vix_edge_case()`: Mock VIX=25.0 → blocked (threshold is inclusive)
5. `test_gate_disabled()`: Set gate_enabled=false, VIX=28 → signals still generated

**Acceptance Criteria**
- [ ] No ETF picks emitted when VIX ≥ 25
- [ ] VIX level logged with every ETF signal generation attempt
- [ ] Gate can be disabled via config without code change
- [ ] 24-hour cooldown after VIX drops below 25 before signals resume

**Risk Assessment**
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| VIX spike is temporary and gate misses recovery | Low | Medium | 24-hour cooldown handles brief spikes; sustained elevation blocks |
| VIX data source failure gates all ETF signals | Medium | High | Fail-safe: no VIX data → gate closed; alert on data source failure |

**Rollback Plan**
```python
# Immediate: Set vix_gate.enabled = false in etf_gates.yaml
# Verification: ETF signals generated regardless of VIX level
```

---

### PR-E2: etf_sector_emitter GHA Path Registry Fix

| Field | Detail |
|-------|--------|
| **Branch** | `fix/E2-etf-gha-path-registry-20260518` |
| **Files Changed** | `.github/workflows/etf_sector_emitter.yml`, `config/gha_path_registry.yaml`, `tests/test_gha_path.py` |
| **Est. Effort** | S (1 day) |
| **Parallelizable** | Yes (with PR-E1) |

**Problem Statement**
The GitHub Actions workflow for `etf_sector_emitter` references a hardcoded artifact path (`/tmp/etf_signals/`) that was changed during a recent runner migration. The workflow fails intermittently with "path not found" errors because the GHA path registry is not consulted.

**Solution Description**
Update the workflow to use the GHA path registry for all artifact paths. Add path validation step and fallback mechanism.

**Code Changes**
```yaml
# .github/workflows/etf_sector_emitter.yml
name: ETF Sector Emitter
on:
  schedule:
    - cron: '0 9 * * 1-5'  # 9 AM UTC, weekdays
  workflow_dispatch:

jobs:
  emit-signals:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      # ADDED: Load path registry
      - name: Load GHA Path Registry
        id: path_registry
        run: |
          echo "artifact_path=$(cat config/gha_path_registry.yaml | yq '.etf_sector_emitter.artifact_path')" >> $GITHUB_OUTPUT
          echo "log_path=$(cat config/gha_path_registry.yaml | yq '.etf_sector_emitter.log_path')" >> $GITHUB_OUTPUT
      
      # ADDED: Validate paths exist or create them
      - name: Ensure Paths Exist
        run: |
          mkdir -p ${{ steps.path_registry.outputs.artifact_path }}
          mkdir -p ${{ steps.path_registry.outputs.log_path }}
      
      - name: Run ETF Sector Emitter
        env:
          ARTIFACT_PATH: ${{ steps.path_registry.outputs.artifact_path }}
          LOG_PATH: ${{ steps.path_registry.outputs.log_path }}
        run: |
          python -m strategies.etf_sector_emitter \
            --output-dir "$ARTIFACT_PATH" \
            --log-dir "$LOG_PATH" \
            --date ${{ github.event.inputs.date || 'today' }}
      
      - name: Upload Signals Artifact
        uses: actions/upload-artifact@v4
        with:
          name: etf-signals-${{ github.run_id }}
          path: ${{ steps.path_registry.outputs.artifact_path }}/*.json
```

```yaml
# config/gha_path_registry.yaml
etf_sector_emitter:
  artifact_path: /home/runner/artifacts/etf_signals/  # updated path
  log_path: /home/runner/logs/etf_sector_emitter/
  fallback_path: /tmp/etf_signals/  # legacy fallback
  registry_version: "2026-05-18"
```

**Test Plan**
1. `test_path_registry_loads()`: Verify YAML parses correctly, both paths are strings
2. `test_workflow_syntax()`: Run `actionlint` on modified workflow file
3. `test_path_creation()`: Run workflow in dry-run mode, verify directories created
4. `test_artifact_upload()`: Verify artifact uploaded to correct path after signal generation

**Acceptance Criteria**
- [ ] Workflow runs without "path not found" errors
- [ ] All hardcoded paths removed from workflow YAML
- [ ] Path registry is single source of truth for artifact locations
- [ ] Fallback path used only if registry path unavailable

**Risk Assessment**
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| yq not available on runner | Low | High | Install yq as workflow step; or use Python YAML parser |
| Path registry file missing | Low | High | Fail-safe: use fallback_path if registry missing |

**Rollback Plan**
```yaml
# Revert: Restore hardcoded paths in workflow YAML
# Revert: Remove path registry loading steps
# Verification: Workflow runs with hardcoded paths (may fail on new runners)
```

---

### PR-E3: Sector Dual Momentum Implementation (Antonacci GEM)

| Field | Detail |
|-------|--------|
| **Branch** | `strategy/E3-sector-dual-momentum-20260518` |
| **Files Changed** | `strategies/sector_dual_momentum.py`, `pick_orchestrator.py`, `config/strategy_registry.yaml`, `tests/test_dual_momentum.py` |
| **Est. Effort** | L (4-5 days) |
| **Depends On** | PR-E1 (VIX gate must be active before adding momentum strategy) |

**Problem Statement**
The current ETF strategy uses single momentum (12-month return rank). Gary Antonacci's Global Equities Momentum (GEM) adds absolute momentum (positive 12-month return filter) on top of relative momentum, significantly reducing drawdowns. This is not yet implemented.

**Solution Description**
Implement Antonacci GEM for ETF sector selection: (1) compute 12-month returns for all sector ETFs, (2) filter to only those with positive absolute momentum (12-month return > 0), (3) select the top-ranked sector by relative momentum, (4) if no sectors have positive momentum, go to cash (SHY).

**Code Changes**
```python
# strategies/sector_dual_momentum.py
class SectorDualMomentumStrategy:
    """Antonacci GEM applied to ETF sector rotation."""
    
    STRATEGY_NAME = 'sector_dual_momentum'
    ASSET_CLASSES = ['ETF']
    
    # Sector ETF universe
    SECTOR_ETFS = {
        'XLK': 'Technology',
        'XLF': 'Financials',
        'XLE': 'Energy',
        'XLI': 'Industrials',
        'XLP': 'Consumer Staples',
        'XLY': 'Consumer Discretionary',
        'XLB': 'Materials',
        'XLU': 'Utilities',
        'XLV': 'Health Care',
        'XLRE': 'Real Estate',
        'XLC': 'Communication Services'
    }
    
    # Cash ETF when no absolute momentum
    CASH_ETF = 'SHY'
    
    def __init__(self):
        self.lookback_months = 12
        self.rebalance_frequency = 'monthly'  # GEM uses monthly rebalancing
        self.vix_gate_threshold = 25  # must align with PR-E1
    
    def generate_signals(self, as_of: date) -> list[Pick]:
        """Generate dual momentum ETF sector signals."""
        # Check VIX gate (coordinated with PR-E1)
        vix = self._get_vix_level()
        if vix and vix >= self.vix_gate_threshold:
            logging.info(f"Dual momentum: VIX={vix:.1f}, going to cash")
            return self._cash_signal(as_of)
        
        # Step 1: Compute 12-month returns for all sectors
        sector_returns = {}
        for symbol, name in self.SECTOR_ETFS.items():
            ret_12m = self._compute_return(symbol, months=12, as_of=as_of)
            if ret_12m is not None:
                sector_returns[symbol] = {
                    'return_12m': ret_12m,
                    'name': name
                }
        
        # Step 2: Absolute momentum filter (only positive momentum sectors)
        positive_momentum = {
            sym: data for sym, data in sector_returns.items() 
            if data['return_12m'] > 0
        }
        
        if not positive_momentum:
            # No sectors have positive momentum → go to cash
            logging.info("Dual momentum: no positive absolute momentum; going to cash")
            return self._cash_signal(as_of)
        
        # Step 3: Relative momentum — select top performer
        top_sector = max(positive_momentum, key=lambda x: positive_momentum[x]['return_12m'])
        top_data = positive_momentum[top_sector]
        
        # Compute confidence based on margin over second-best
        sorted_sectors = sorted(
            positive_momentum.items(), 
            key=lambda x: x[1]['return_12m'], 
            reverse=True
        )
        margin = 0
        if len(sorted_sectors) >= 2:
            margin = top_data['return_12m'] - sorted_sectors[1][1]['return_12m']
        
        confidence = min(60 + margin * 500, 95)  # scale margin to confidence
        
        return [Pick(
            symbol=top_sector,
            direction='LONG',
            confidence=confidence,
            strategy=self.STRATEGY_NAME,
            asset_class='ETF',
            metadata={
                'return_12m': top_data['return_12m'],
                'sector_name': top_data['name'],
                'margin_over_runner_up': margin,
                'num_positive_momentum': len(positive_momentum),
                'dual_momentum_applied': True
            }
        )]
    
    def _cash_signal(self, as_of: date) -> list[Pick]:
        """Generate cash-equivalent signal when momentum is negative."""
        return [Pick(
            symbol=self.CASH_ETF,
            direction='LONG',
            confidence=80,
            strategy=self.STRATEGY_NAME,
            asset_class='ETF',
            metadata={'cash_signal': True, 'reason': 'no_positive_momentum_or_high_vix'}
        )]
    
    def _compute_return(self, symbol: str, months: int, as_of: date) -> float | None:
        """Compute total return over N months."""
        start_date = as_of - relativedelta(months=months)
        prices = self.data_client.get_adjusted_prices(symbol, start_date, as_of)
        if prices is None or len(prices) < months * 15:  # require ~15 days/month minimum
            return None
        total_return = (prices.iloc[-1] / prices.iloc[0]) - 1
        return total_return
```

**Test Plan**
1. `test_all_positive_momentum()`: All sectors positive → top sector selected
2. `test_no_positive_momentum()`: All sectors negative → cash signal (SHY)
3. `test_mixed_momentum()`: 5 positive, 6 negative → only positive considered, top selected
4. `test_vix_gate_cash()`: VIX=28 → cash signal regardless of momentum
5. `test_margin_calculation()`: Top return 15%, second 12% → confidence ~75 (60 + 0.03*500)
6. `test_monthly_rebalance()`: Verify signals only generated on monthly boundaries

**Acceptance Criteria**
- [ ] Strategy correctly identifies top sector by 12-month return among positive-momentum sectors
- [ ] Cash signal (SHY) emitted when no positive momentum or VIX ≥ 25
- [ ] Confidence score reflects margin over runner-up
- [ ] Backtest: GEM strategy shows max drawdown < 15% vs. < 25% for single momentum
- [ ] ≥1 signal per month (monthly rebalancing)

**Risk Assessment**
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Monthly rebalancing too slow for fast market moves | Medium | High | Add intra-month VIX spike override (already in VIX gate) |
| Cash signal (SHY) duration too long, missing recovery | Low | Medium | Track days-in-cash metric; alert if >30 consecutive days |
| Lookback period too long for current regime | Medium | Medium | Parameter: allow 6-month or 3-month lookback as override |

**Rollback Plan**
```python
# Immediate: Set sector_dual_momentum.enabled = false in strategy_registry.yaml
# Revert: Remove strategy from pick_orchestrator
# Verification: Only etf_sector_emitter (single momentum) produces ETF signals
```

---


## Section 4: PRs for EQUITY (INSUFFICIENT_DATA → WATCH)

**Current State:** INSUFFICIENT_DATA (n=31 local picks, WR unreliable) | **Target:** WATCH (n≥75, WR trend visible)

**Theme:** Data pipeline cleanup, symbol quality, PEAD strategy backtest, day-of-week seasonal gate.

---

### PR-Q1: MySQL Ghost-Row Purge Coordination (PA Action)

| Field | Detail |
|-------|--------|
| **Branch** | `data/Q1-mysql-ghost-row-purge-20260518` |
| **Files Changed** | `scripts/purge_ghost_rows.py`, `docs/runbooks/MYSQL_GHOST_ROW_PURGE.md`, `tests/test_ghost_row_detection.py` |
| **Est. Effort** | M (2-3 days) |
| **Owner** | Platform Admin (PA) |
| **Parallelizable** | Yes |

**Problem Statement**
The EQUITY pick database contains an estimated 150-200 "ghost rows" — records from a 2024 data migration where picks were partially inserted (missing `exit_time`, `pnl_usd`, or `symbol` fields). These ghost rows inflate `n` counts and corrupt win rate calculations. Manual inspection of 50 random rows found 23 ghost rows (46% contamination rate).

**Solution Description**
PA-coordinated purge: (1) run detection query to identify all ghost rows, (2) backup to `equity_picks_backup_20260518`, (3) delete ghost rows, (4) verify row counts, (5) update dashboard to exclude pre-purge period if needed.

**Code Changes**
```python
# scripts/purge_ghost_rows.py (NEW — PA-run script)
class GhostRowDetector:
    """Detect and purge ghost rows from EQUITY picks table."""
    
    GHOST_CRITERIA = [
        "exit_time IS NULL AND created_at < DATE_SUB(NOW(), INTERVAL 7 DAY)",
        "pnl_usd IS NULL AND status = 'CLOSED'",
        "symbol IS NULL OR symbol = ''",
        "entry_price IS NULL OR entry_price <= 0",
        "direction NOT IN ('LONG', 'SHORT')"
    ]
    
    def detect_ghost_rows(self, table: str = 'equity_picks') -> pd.DataFrame:
        """Identify all ghost rows using multiple criteria."""
        all_ghosts = []
        
        for criterion in self.GHOST_CRITERIA:
            query = f"""
                SELECT pick_id, symbol, status, created_at, '{criterion}' as matched_criterion
                FROM {table}
                WHERE {criterion}
            """
            df = pd.read_sql(query, production_db_conn())
            all_ghosts.append(df)
        
        combined = pd.concat(all_ghosts).drop_duplicates(subset='pick_id')
        return combined
    
    def backup_and_purge(self, table: str = 'equity_picks', dry_run: bool = True) -> dict:
        """Backup ghost rows before purging."""
        ghosts = self.detect_ghost_rows(table)
        
        backup_table = f"{table}_backup_{datetime.now().strftime('%Y%m%d')}"
        
        if dry_run:
            return {
                'dry_run': True,
                'ghost_rows_detected': len(ghosts),
                'backup_table': backup_table,
                'sample_ghosts': ghosts.head(10).to_dict('records')
            }
        
        # Create backup
        with production_db_conn() as conn:
            conn.execute(f"CREATE TABLE {backup_table} AS SELECT * FROM {table} WHERE pick_id IN %s", 
                        (tuple(ghosts['pick_id'].tolist()),))
            
            # Delete ghost rows
            conn.execute(f"DELETE FROM {table} WHERE pick_id IN %s",
                        (tuple(ghosts['pick_id'].tolist()),))
            conn.commit()
        
        # Verify
        remaining_ghosts = self.detect_ghost_rows(table)
        
        return {
            'dry_run': False,
            'ghost_rows_purged': len(ghosts),
            'backup_table': backup_table,
            'remaining_ghosts': len(remaining_ghosts),
            'verification_passed': len(remaining_ghosts) == 0
        }
```

**Runbook: MYSQL_GHOST_ROW_PURGE.md**
```markdown
# MySQL Ghost Row Purge — Runbook

## Prerequisites
- [ ] PA access to production MySQL (read-write)
- [ ] Maintenance window scheduled (recommended: off-hours)
- [ ] Backup verified within last 24 hours

## Steps
1. Run detection (dry run): `python scripts/purge_ghost_rows.py --dry-run`
2. Review sample ghosts in output
3. Create backup: `python scripts/purge_ghost_rows.py --backup-only`
4. Execute purge: `python scripts/purge_ghost_rows.py --execute`
5. Verify: `python scripts/purge_ghost_rows.py --verify`
6. Update dashboard refresh timestamp

## Rollback
- Restore from backup table: `INSERT INTO equity_picks SELECT * FROM equity_picks_backup_YYYYMMDD`
- Contact: platform-admin@findtorontoevents_antigravity.ca
```

**Test Plan**
1. `test_detect_ghosts()`: Insert 5 ghost rows (various criteria), verify detection catches all 5
2. `test_dry_run_no_changes()`: Run in dry-run mode, verify no rows deleted
3. `test_backup_created()`: Run purge, verify backup table exists with correct row count
4. `test_verify_zero_remaining()`: After purge, verify detect_ghost_rows returns empty
5. `test_legitimate_rows_preserved()`: Insert 5 valid picks, run purge, verify all 5 preserved

**Acceptance Criteria**
- [ ] Ghost rows reduced to 0 (or <1% of total)
- [ ] Backup table created with all purged rows
- [ ] Legitimate picks unaffected
- [ ] Dashboard pick count (n) decreases by exact number of ghost rows purged
- [ ] Post-purge WR calculation uses clean data only

**Risk Assessment**
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Legitimate rows accidentally purged | Low | Critical | Multiple criteria must match; backup table; dry-run first |
| Database lock during purge | Medium | High | Run during off-hours; limit to 1000 rows per batch |
| Backup table corruption | Very Low | Critical | Full DB backup within 24h as second-line recovery |

**Rollback Plan**
```sql
-- Immediate: Restore from backup
INSERT INTO equity_picks 
SELECT * FROM equity_picks_backup_20260518 
WHERE pick_id NOT IN (SELECT pick_id FROM equity_picks);
-- Verification: Row count returns to pre-purge level
```

---

### PR-Q2: EQUITY_SYMBOLS Speculative Ticker Removal (8 Penny/Meme)

| Field | Detail |
|-------|--------|
| **Branch** | `data/Q2-equity-symbol-cleanup-20260518` |
| **Files Changed** | `config/equity_universe.yaml`, `scripts/audit_speculative_tickers.py`, `tests/test_symbol_removal.py` |
| **Est. Effort** | S (1 day) |
| **Depends On** | PR-Q1 (clean data needed before symbol evaluation) |

**Problem Statement**
The EQUITY universe contains 8 speculative/penny/meme tickers that produce low-quality picks with poor fill rates and excessive slippage: AMC, GME, BBBYQ, MULN, NVAX, PLTR (meme component), TSLA (excessive volatility), HOOD. These symbols account for 12 of 31 "local" picks but only 3 profitable outcomes (WR=25%).

**Solution Description**
Remove 8 tickers from the active EQUITY universe. Move them to a `WATCHLIST_MEME` category for potential future re-evaluation. Document rationale per symbol.

**Code Changes**
```yaml
# config/equity_universe.yaml
active_universe:
  # Core large-cap (retained)
  - AAPL
  - MSFT
  - GOOGL
  - AMZN
  - META
  - JPM
  - UNH
  - JNJ
  - V
  - PG
  # ... other liquid large-caps

# REMOVED from active (moved to WATCHLIST_MEME)
watchlist_meme:
  - symbol: AMC
    removed_reason: "Penny stock characteristics, avg spread >50bps, WR=20%"
    review_date: "2026-08-01"
  - symbol: GME
    removed_reason: "Meme volatility, frequent halts, slippage >200bps"
    review_date: "2026-08-01"
  - symbol: BBBYQ
    removed_reason: "Bankruptcy proceedings, trading suspended"
    review_date: "2026-12-01"
  - symbol: MULN
    removed_reason: "Sub-$1 price, delisting risk, zero profitable picks"
    review_date: "2026-08-01"
  - symbol: NVAX
    removed_reason: "Biotech binary events, 90% of picks around earnings"
    review_date: "2026-08-01"
  - symbol: PLTR
    removed_reason: "Meme component; extreme OTM option flow contaminates signal"
    review_date: "2026-07-01"
  - symbol: TSLA
    removed_reason: "Volatility too high for current position sizing; re-evaluate after VIX normalization"
    review_date: "2026-07-01"
  - symbol: HOOD
    removed_reason: "Crypto revenue dependency creates CRYPTO-like volatility in EQUITY class"
    review_date: "2026-08-01"
```

```python
# scripts/audit_speculative_tickers.py (NEW)
def audit_removed_tickers() -> pd.DataFrame:
    """Generate audit report for all removed speculative tickers."""
    with open('config/equity_universe.yaml') as f:
        config = yaml.safe_load(f)
    
    removed = config.get('watchlist_meme', [])
    
    report_rows = []
    for item in removed:
        symbol = item['symbol'] if isinstance(item, dict) else item
        reason = item.get('removed_reason', 'N/A') if isinstance(item, dict) else 'N/A'
        review = item.get('review_date', 'N/A') if isinstance(item, dict) else 'N/A'
        
        # Fetch historical performance
        perf = get_symbol_performance(symbol, days=90)
        
        report_rows.append({
            'symbol': symbol,
            'removal_reason': reason,
            'review_date': review,
            'n_picks_90d': perf['n_picks'],
            'win_rate_90d': perf['win_rate'],
            'avg_slippage_bps': perf['avg_slippage_bps'],
            'avg_spread_bps': perf['avg_spread_bps']
        })
    
    return pd.DataFrame(report_rows)
```

**Test Plan**
1. `test_removed_tickers_no_signals()`: Attempt to generate pick for GME → rejected (not in active universe)
2. `test_active_tickers_work()`: Generate pick for AAPL → accepted
3. `test_watchlist_documented()`: All 8 removed tickers have `removed_reason` and `review_date`
4. `test_audit_report()`: Run audit script, verify 8 rows in output DataFrame

**Acceptance Criteria**
- [ ] Zero picks generated for removed tickers
- [ ] All 8 tickers documented in watchlist_meme with rationale
- [ ] Review dates set (no symbol removed permanently without re-evaluation)
- [ ] Average EQUITY pick quality improves (target: avg confidence increases by ≥5 points)

**Risk Assessment**
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Removed ticker had hidden edge in specific conditions | Low | Medium | Review dates set; shadow tier continues monitoring |
| Active universe too small after removal (n < 20) | Low | Medium | 20+ liquid large-caps remain; sufficient diversity |

**Rollback Plan**
```yaml
# Move symbol back to active_universe in equity_universe.yaml
# Verification: Pick generation succeeds for restored symbol
```

---

### PR-Q3: PEAD Strategy Backtest + Wire-Up

| Field | Detail |
|-------|--------|
| **Branch** | `strategy/Q3-pead-equity-20260518` |
| **Files Changed** | `strategies/pead_strategy.py`, `config/strategy_registry.yaml`, `tests/test_pead_backtest.py`, `docs/backtests/PEAD_EQUITY_20260518.md` |
| **Est. Effort** | L (4-5 days) |
| **Depends On** | PR-Q1 (clean data), PR-Q2 (clean universe) |

**Problem Statement**
PEAD (Post-Earnings Announcement Drift) is a well-documented anomaly where stocks drift in the direction of earnings surprises for 30-60 days. No PEAD strategy is currently implemented for EQUITY. We need a backtested, production-ready PEAD strategy to increase EQUITY pick volume.

**Solution Description**
Implement PEAD strategy: (1) detect earnings surprises (actual EPS vs. consensus), (2) compute standardized unexpected earnings (SUE), (3) go LONG on positive SUE surprises, SHORT on negative, (4) hold for 30 days, (5) wire into production if backtest PF ≥ 2.0.

**Code Changes**
```python
# strategies/pead_strategy.py
class PEADStrategy:
    """Post-Earnings Announcement Drift strategy for EQUITY."""
    
    STRATEGY_NAME = 'pead'
    ASSET_CLASSES = ['EQUITY']
    
    def __init__(self):
        self.sue_threshold = 2.0  # SUE > 2 standard deviations = significant surprise
        self.holding_days = 30
        self.max_positions = 10
        self.earnings_lookback_days = 2  # trade within 2 days of earnings announcement
    
    def generate_signals(self, as_of: date) -> list[Pick]:
        """Generate PEAD signals from recent earnings surprises."""
        # Find recent earnings announcements
        recent_earnings = self._get_recent_earnings(as_of, days=self.earnings_lookback_days)
        
        signals = []
        for earnings in recent_earnings:
            sue = self._compute_sue(earnings)
            if abs(sue) < self.sue_threshold:
                continue  # Not a significant surprise
            
            direction = 'LONG' if sue > 0 else 'SHORT'
            confidence = min(50 + abs(sue) * 10, 90)
            
            # Check if already in a PEAD position for this symbol
            if self._has_open_pead_position(earnings['symbol']):
                continue
            
            signals.append(Pick(
                symbol=earnings['symbol'],
                direction=direction,
                confidence=confidence,
                strategy=self.STRATEGY_NAME,
                asset_class='EQUITY',
                metadata={
                    'sue': sue,
                    'eps_actual': earnings['eps_actual'],
                    'eps_estimate': earnings['eps_estimate'],
                    'announcement_date': earnings['announcement_date'],
                    'holding_days': self.holding_days
                }
            ))
        
        # Limit to top N by |SUE|
        signals.sort(key=lambda x: abs(x.metadata['sue']), reverse=True)
        return signals[:self.max_positions]
    
    def _compute_sue(self, earnings: dict) -> float:
        """Compute Standardized Unexpected Earnings."""
        eps_actual = earnings['eps_actual']
        eps_estimate = earnings['eps_estimate']
        eps_std = earnings.get('eps_surprise_std', 0.01)
        
        if eps_std == 0:
            return 0
        
        sue = (eps_actual - eps_estimate) / eps_std
        return sue
    
    def _get_recent_earnings(self, as_of: date, days: int) -> list[dict]:
        """Fetch earnings announcements from last N days."""
        query = """
            SELECT symbol, announcement_date, eps_actual, eps_estimate, 
                   eps_surprise_std
            FROM earnings_calendar
            WHERE announcement_date BETWEEN %s AND %s
              AND eps_actual IS NOT NULL
              AND eps_estimate IS NOT NULL
            ORDER BY announcement_date DESC
        """
        start = as_of - timedelta(days=days)
        df = pd.read_sql(query, production_db_conn(), params=(start, as_of))
        return df.to_dict('records')
```

**Test Plan**
1. `test_positive_sue_long()`: SUE=3.0 → LONG signal, confidence > 70
2. `test_negative_sue_short()`: SUE=-2.5 → SHORT signal, confidence > 70
3. `test_small_sue_no_signal()`: SUE=1.0 → no signal (below threshold)
4. `test_max_positions()`: 15 earnings surprises → only top 10 by |SUE| returned
5. `test_duplicate_symbol()`: Two earnings for same symbol → only first processed
6. Backtest: Run on 2023-01-01 to 2025-12-31 data, verify PF ≥ 2.0

**Acceptance Criteria**
- [ ] PEAD backtest PF ≥ 2.0 on 3-year out-of-sample data
- [ ] Strategy produces ≥3 picks per week during earnings season
- [ ] All picks have SUE metadata attached
- [ ] No duplicate PEAD positions for same symbol
- [ ] Holding period exactly 30 days (tracked in metadata)

**Risk Assessment**
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Earnings data stale or missing | Medium | High | Check data freshness; skip if earnings > 48 hours old |
| SUE computation wrong for special items | Medium | High | Use adjusted EPS; filter out one-time gains/losses |
| Earnings season clustering (too many signals) | Medium | Medium | max_positions=10 limits exposure |

**Rollback Plan**
```python
# Immediate: Set pead.enabled = false in strategy_registry.yaml
# Verification: No PEAD picks after disable
```

---

### PR-Q4: DOW Tilt Gate Enable (Tue/Wed Long Bias)

| Field | Detail |
|-------|--------|
| **Branch** | `config/Q4-dow-tilt-gate-20260518` |
| **Files Changed** | `score_booster.py`, `config/seasonal_gates.yaml`, `tests/test_dow_tilt.py` |
| **Est. Effort** | S (1-2 days) |
| **Depends On** | PR-Q3 (PEAD wired — DOW tilt should not double-count earnings effects) |

**Problem Statement**
Academic research (Heston et al., 2011; Keloharju et al., 2016) documents a persistent day-of-week effect: Tuesday and Wednesday show positive abnormal returns for large-cap EQUITY. A DOW tilt gate exists in config as DRAFT but is not wired into `score_booster.py`.

**Solution Description**
Wire DOW tilt into score_booster: on Tuesdays and Wednesdays, add +10 confidence to LONG EQUITY picks if the base signal is already LONG. Do not modify SHORT picks (asymmetric effect). Gate applies only to large-cap EQUITY (market cap > $10B).

**Code Changes**
```python
# score_booster.py
class ScoreBooster:
    def apply_DOW_tilt(self, pick: Pick) -> Pick:
        """Q4: Apply day-of-week confidence tilt for EQUITY.
        
        Tuesdays and Wednesdays show persistent positive bias.
        Only applies to LONG picks on large-cap equities.
        """
        if pick.asset_class != 'EQUITY':
            return pick
        
        if pick.direction != 'LONG':
            return pick  # Asymmetric: only boost LONGs
        
        today = datetime.utcnow().weekday()
        # Monday=0, Tuesday=1, Wednesday=2, Thursday=3, Friday=4
        if today not in [1, 2]:  # Tuesday or Wednesday only
            return pick
        
        # Check market cap filter
        market_cap = self._get_market_cap(pick.symbol)
        if market_cap is None or market_cap < 10_000_000_000:  # $10B minimum
            return pick
        
        pick.confidence = min(pick.confidence + 10, 100)
        pick.metadata['DOW_tilt_applied'] = True
        pick.metadata['DOW_tilt_day'] = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'][today]
        pick.metadata['DOW_tilt_market_cap_bn'] = market_cap / 1e9
        
        return pick
```

```yaml
# config/seasonal_gates.yaml
dow_tilt:
  name: "DOW_TILT_EQUITY"
  status: ACTIVE  # promoted from DRAFT
  asset_classes: [EQUITY]
  applicable_days: [Tue, Wed]  # Tuesday, Wednesday
  applicable_directions: [LONG]
  min_market_cap: 10_000_000_000  # $10B
  confidence_boost: 10
  evidence: "Heston et al. 2011, Keloharju et al. 2016: persistent Tuesday/Wednesday positive drift"
  review_date: "2026-09-01"
```

**Test Plan**
1. `test_dow_tilt_tuesday_long()`: Tuesday, LONG AAPL, market cap $2.8T → confidence +10
2. `test_dow_tilt_wednesday_long()`: Wednesday, LONG MSFT → confidence +10
3. `test_dow_tilt_monday_no_effect()`: Monday, LONG AAPL → confidence unchanged
4. `test_dow_tilt_short_no_effect()`: Tuesday, SHORT AAPL → confidence unchanged
5. `test_dow_tilt_small_cap_no_effect()`: Tuesday, LONG small-cap ($1B) → confidence unchanged
6. `test_dow_tilt_non_equity()`: Tuesday, LONG BTC → confidence unchanged

**Acceptance Criteria**
- [ ] DOW tilt applied to ≥80% of eligible LONG EQUITY picks on Tuesdays/Wednesdays
- [ ] No effect on SHORT picks, non-EQUITY, or small-cap
- [ ] 30-day rolling WR of DOW-tilted picks ≥ 60%
- [ ] Boost magnitude exactly +10 confidence points (no rounding errors)

**Risk Assessment**
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| DOW effect faded (post-2020 market structure) | Medium | Medium | 90-day review; auto-disable if WR < 55% |
| Overlaps with PEAD signals, double-counting | Medium | High | Pick gets max of PEAD and DOW boost, not sum |

**Rollback Plan**
```yaml
# Immediate: Set dow_tilt.status = DRAFT in seasonal_gates.yaml
# Verification: No DOW tilt metadata on picks after disable
```

---

## Section 5: PRs for FOREX (NOT_READY → RESEARCH)

**Current State:** NOT_READY (PF=0.48, HARD_DISABLED) | **Target:** RESEARCH (PF≥1.0 trending, backtest complete)

**Theme:** Carry backtest implementation, selective re-enable gate.

---

### PR-F1: forex_carry.py Backtest Implementation

| Field | Detail |
|-------|--------|
| **Branch** | `backtest/F1-forex-carry-20260518` |
| **Files Changed** | `strategies/forex_carry.py`, `backtest_engine.py`, `tests/test_forex_carry_backtest.py`, `docs/backtests/FOREX_CARRY_20260518.md` |
| **Est. Effort** | L (4-5 days) |
| **Parallelizable** | Yes |

**Problem Statement**
`forex_carry.py` implements a G10 carry trade (go LONG high-yield currencies, SHORT low-yield currencies). It has never been backtested with transaction costs. The current PF=0.48 suggests costs are destroying edge. We need a clean backtest to understand whether the strategy is viable.

**Solution Description**
Implement full backtest: (1) load 10 years of G10 spot and forward rates, (2) implement carry signal (3-month forward implied yield differential), (3) simulate trades with realistic transaction costs (spread + slippage), (4) compute full performance metrics, (5) identify if any sub-period or sub-universe shows PF > 1.5.

**Code Changes**
```python
# strategies/forex_carry.py
class ForexCarryStrategy:
    """G10 carry trade: long high-yield, short low-yield currencies."""
    
    STRATEGY_NAME = 'forex_carry'
    ASSET_CLASSES = ['FOREX']
    
    # G10 currency pairs (vs USD)
    G10_PAIRS = [
        'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 
        'AUDUSD', 'USDCAD', 'NZDUSD', 'USDNOK', 'USDSEK'
    ]
    
    def __init__(self):
        self.holding_months = 3
        self.yield_lookback_months = 3
        self.top_n = 3  # long top 3, short bottom 3
        
    def generate_carry_rankings(self, as_of: date) -> pd.DataFrame:
        """Rank G10 currencies by 3-month implied yield."""
        rankings = []
        
        for pair in self.G10_PAIRS:
            try:
                spot = self.data_client.get_fx_rate(pair, as_of)
                forward_3m = self.data_client.get_fx_forward(pair, tenor='3M', as_of=as_of)
                
                if spot is None or forward_3m is None or spot <= 0:
                    continue
                
                # Annualized carry = (forward - spot) / spot * (12 / 3) * 100
                carry = ((forward_3m - spot) / spot) * 4 * 100
                
                rankings.append({
                    'pair': pair,
                    'spot': spot,
                    'forward_3m': forward_3m,
                    'annualized_carry_bps': carry * 100,  # convert to basis points
                    'signal_date': as_of
                })
            except Exception as e:
                logging.warning(f"Failed to compute carry for {pair}: {e}")
                continue
        
        df = pd.DataFrame(rankings)
        if len(df) == 0:
            return df
        
        df = df.sort_values('annualized_carry_bps', ascending=False).reset_index(drop=True)
        df['rank'] = range(1, len(df) + 1)
        df['signal'] = 'NEUTRAL'
        df.loc[:self.top_n - 1, 'signal'] = 'LONG'   # top N = long (high yield)
        df.loc[-self.top_n:, 'signal'] = 'SHORT'      # bottom N = short (low yield)
        
        return df
    
    def run_backtest(
        self, 
        start: date = date(2015, 1, 1),
        end: date = date(2025, 12, 31),
        transaction_cost_bps: float = 3.0  # spread + slippage estimate
    ) -> BacktestResult:
        """Run full backtest with transaction costs."""
        
        rebalance_dates = pd.bdate_range(start, end, freq='BM')  # monthly rebalancing
        all_trades = []
        
        for rebalance_date in rebalance_dates:
            rankings = self.generate_carry_rankings(rebalance_date)
            if len(rankings) == 0:
                continue
            
            longs = rankings[rankings['signal'] == 'LONG']
            shorts = rankings[rankings['signal'] == 'SHORT']
            
            for _, row in longs.iterrows():
                pnl = self._simulate_trade(
                    row['pair'], 'LONG', rebalance_date, 
                    months=self.holding_months, cost_bps=transaction_cost_bps
                )
                all_trades.append({
                    'pair': row['pair'],
                    'direction': 'LONG',
                    'entry_date': rebalance_date,
                    'carry_at_entry': row['annualized_carry_bps'],
                    'pnl': pnl
                })
            
            for _, row in shorts.iterrows():
                pnl = self._simulate_trade(
                    row['pair'], 'SHORT', rebalance_date,
                    months=self.holding_months, cost_bps=transaction_cost_bps
                )
                all_trades.append({
                    'pair': row['pair'],
                    'direction': 'SHORT',
                    'entry_date': rebalance_date,
                    'carry_at_entry': row['annualized_carry_bps'],
                    'pnl': pnl
                })
        
        trades_df = pd.DataFrame(all_trades)
        
        # Compute metrics
        wins = trades_df[trades_df['pnl'] > 0]
        losses = trades_df[trades_df['pnl'] <= 0]
        
        metrics = {
            'n_trades': len(trades_df),
            'win_rate': len(wins) / len(trades_df) * 100 if len(trades_df) > 0 else 0,
            'profit_factor': abs(wins['pnl'].sum()) / abs(losses['pnl'].sum()) if len(losses) > 0 and losses['pnl'].sum() != 0 else float('inf'),
            'total_pnl': trades_df['pnl'].sum(),
            'avg_trade_pnl': trades_df['pnl'].mean(),
            'max_drawdown': self._compute_max_drawdown(trades_df),
            'sharpe_ratio': self._compute_sharpe(trades_df),
            'transaction_cost_bps': transaction_cost_bps
        }
        
        return BacktestResult(trades=trades_df, metrics=metrics)
    
    def _simulate_trade(
        self, pair: str, direction: str, entry_date: date, 
        months: int, cost_bps: float
    ) -> float:
        """Simulate a single carry trade with transaction costs."""
        exit_date = entry_date + relativedelta(months=months)
        
        entry_spot = self.data_client.get_fx_rate(pair, entry_date)
        exit_spot = self.data_client.get_fx_rate(pair, exit_date)
        
        if entry_spot is None or exit_spot is None:
            return 0.0
        
        # Compute P&L in pips
        if direction == 'LONG':
            gross_pnl = (exit_spot - entry_spot) * 10000  # convert to pips
        else:
            gross_pnl = (entry_spot - exit_spot) * 10000
        
        # Subtract round-trip transaction cost
        cost = cost_bps * 2  # entry + exit
        net_pnl = gross_pnl - cost
        
        return net_pnl
```

**Test Plan**
1. `test_carry_ranking()`: Mock 5 pairs with known carry values, verify ranking is correct
2. `test_top_n_selection()`: With 9 pairs, verify top 3 get LONG, bottom 3 get SHORT
3. `test_backtest_produces_trades()`: Run on 2020 data, verify >0 trades generated
4. `test_transaction_costs_applied()`: Verify each trade P&L reduced by cost_bps * 2
5. `test_pf_computation()`: Known set of wins/losses, verify PF formula correct

**Acceptance Criteria**
- [ ] Backtest covers ≥10 years of data (2015-2025)
- [ ] All G10 pairs have >95% data availability
- [ ] Backtest report includes PF, WR, Sharpe, max drawdown
- [ ] Go/No-Go recommendation documented:
  - GO if PF ≥ 1.5 (viable after costs)
  - CONDITIONAL if 1.0 ≤ PF < 1.5 (may work with execution optimization)
  - NO-GO if PF < 1.0 (not viable)

**Risk Assessment**
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Historical carry data has survivorship bias | Medium | High | Use point-in-time forward curves; document data sources |
| Transaction cost estimate (3bps) too low | Medium | High | Run sensitivity analysis at 1bps, 3bps, 5bps, 10bps |
| Backtest overfits to G10 selection | Low | Medium | Test on subset of 5 pairs; verify robustness |

**Rollback Plan**
```python
# No production changes — backtest only
# Rollback: Delete backtest results file
```

---

### PR-F2: Non-JPY SHORT Re-enable Gate (When n≥30)

| Field | Detail |
|-------|--------|
| **Branch** | `gate/F2-forex-non-jpy-re-enable-20260518` |
| **Files Changed** | `quality_gates.py`, `config/forex_gates.yaml`, `tests/test_forex_re_enable.py` |
| **Est. Effort** | S (1 day) |
| **Depends On** | PR-F1 (backtest must show PF ≥ 1.0 for non-JPY pairs) |

**Problem Statement**
FOREX is HARD_DISABLED due to poor overall PF (0.48). However, PR-F1 backtest may show that non-JPY pairs (AUD, GBP, EUR, CHF) have acceptable PF while JPY carry trades drag down the aggregate. We need a conditional re-enable gate that allows non-JPY FOREX picks only after sufficient evidence accumulates.

**Solution Description**
Implement a sample-size-conditioned gate: when n≥30 non-JPY FOREX picks have been collected in shadow mode with PF ≥ 1.2, automatically promote non-JPY pairs to production. JPY pairs remain HARD_DISABLED.

**Code Changes**
```python
# quality_gates.py
class ForexReEnableGate:
    """F2: Conditional re-enable of non-JPY FOREX pairs."""
    
    def __init__(self):
        self.min_shadow_picks = 30
        self.min_pf = 1.2
        self.jpy_pairs = ['USDJPY', 'EURJPY', 'GBPJPY', 'AUDJPY']
    
    def check_forex_eligibility(self, pick: Pick) -> GateResult:
        """Check if this FOREX pick should be allowed through."""
        if pick.asset_class != 'FOREX':
            return GateResult(passed=True, gate='F2')
        
        # Always block JPY pairs
        if any(jpy in pick.symbol for jpy in ['JPY']):
            return GateResult(
                passed=False,
                gate='F2',
                reason=f"JPY pairs remain HARD_DISABLED: {pick.symbol}",
                severity='HARD'
            )
        
        # Check if non-JPY threshold met
        shadow_stats = self._get_shadow_stats()
        
        if shadow_stats['n_non_jpy'] >= self.min_shadow_picks and \
           shadow_stats['pf_non_jpy'] >= self.min_pf:
            return GateResult(passed=True, gate='F2')
        
        # Not enough evidence yet
        return GateResult(
            passed=False,
            gate='F2',
            reason=f"Non-JPY FOREX: {shadow_stats['n_non_jpy']}/{self.min_shadow_picks} picks, "
                   f"PF={shadow_stats['pf_non_jpy']:.2f} (need ≥{self.min_pf})",
            severity='HARD',
            metadata={
                'n_non_jpy': shadow_stats['n_non_jpy'],
                'pf_non_jpy': shadow_stats['pf_non_jpy'],
                'threshold_n': self.min_shadow_picks,
                'threshold_pf': self.min_pf
            }
        )
    
    def _get_shadow_stats(self) -> dict:
        """Get shadow-tier performance stats for non-JPY FOREX."""
        query = """
            SELECT COUNT(*) as n, 
                   SUM(CASE WHEN pnl_pips > 0 THEN pnl_pips ELSE 0 END) as gross_profit,
                   SUM(CASE WHEN pnl_pips < 0 THEN ABS(pnl_pips) ELSE 0 END) as gross_loss
            FROM shadow_picks
            WHERE asset_class = 'FOREX'
              AND symbol NOT LIKE '%JPY%'
              AND status = 'CLOSED'
        """
        df = pd.read_sql(query, shadow_db_conn())
        
        n = df['n'].iloc[0] or 0
        gp = df['gross_profit'].iloc[0] or 0
        gl = df['gross_loss'].iloc[0] or 0
        pf = gp / gl if gl > 0 else float('inf')
        
        return {'n_non_jpy': int(n), 'pf_non_jpy': pf}
```

```yaml
# config/forex_gates.yaml
forex_re_enable:
  name: "F2_NON_JPY_RE_ENABLE"
  status: ACTIVE
  asset_classes: [FOREX]
  conditions:
    min_shadow_picks: 30
    min_pf: 1.2
    blocked_pairs:
      - "*JPY*"  # all JPY crosses remain blocked
  auto_promote: true  # automatically promote when conditions met
  review_interval_days: 7  # check conditions weekly
```

**Test Plan**
1. `test_jpy_always_blocked()`: USDJPY pick → always blocked, regardless of stats
2. `test_non_jpy_not_enough_picks()`: 20 non-JPY picks, PF=1.5 → blocked
3. `test_non_jpy_pf_too_low()`: 35 non-JPY picks, PF=1.0 → blocked
4. `test_non_jpy_both_conditions_met()`: 35 non-JPY picks, PF=1.3 → allowed
5. `test_non_forex_passthrough()`: CRYPTO pick → allowed (not FOREX)

**Acceptance Criteria**
- [ ] All JPY pairs remain HARD_BLOCKED
- [ ] Non-JPY pairs promoted automatically when n≥30 and PF≥1.2
- [ ] Promotion event logged and alerted
- [ ] If PF drops below 1.0 after promotion, auto-revert to blocked

**Risk Assessment**
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Shadow stats not representative of production | Medium | High | Start with 0.5x position sizing after promotion |
| JPY contamination through cross pairs | Low | Medium | Explicit JPY string check in all FOREX symbols |
| Non-JPY edge disappears in production | Medium | High | Auto-revert if 30-day rolling PF < 1.0 |

**Rollback Plan**
```python
# Immediate: Set forex_re_enable.status = INACTIVE in forex_gates.yaml
# Verification: All FOREX picks blocked (back to HARD_DISABLED state)
```

---

## Section 6: PRs for BOND (INSUFFICIENT_DATA → ACCUMULATE)

**Current State:** INSUFFICIENT_DATA (n=1) | **Target:** ACCUMULATE (n≥30, WR trend visible)

**Theme:** Time-series momentum strategy, macro data integration.

---

### PR-B1: UST TSMOM Strategy Wire-Up

| Field | Detail |
|-------|--------|
| **Branch** | `wire/B1-ust-tsmom-20260518` |
| **Files Changed** | `strategies/bond_tsmom.py`, `pick_orchestrator.py`, `config/strategy_registry.yaml`, `tests/test_bond_tsmom.py` |
| **Est. Effort** | L (4-5 days) |
| **Parallelizable** | Yes (with PR-B2) |

**Problem Statement**
Bond TSMOM (Time-Series Momentum) is a well-documented strategy (Moskowitz et al., 2012) that goes LONG treasuries when 12-month return is positive, SHORT when negative. `bond_tsmom.py` exists in the repo but is not wired into production. With only n=1 BOND pick to date, we need this strategy to begin accumulating meaningful data.

**Solution Description**
Wire `bond_tsmom.py` into production for US Treasuries (2Y, 5Y, 10Y, 30Y futures). Use 12-month lookback for signal, 1-month holding period, risk-parity position sizing. Start in shadow mode for 2 weeks, then promote if signals look reasonable.

**Code Changes**
```python
# strategies/bond_tsmom.py
class BondTSMOMStrategy:
    """Time-series momentum for US Treasury futures."""
    
    STRATEGY_NAME = 'bond_tsmom'
    ASSET_CLASSES = ['BOND']
    
    # US Treasury futures
    UST_FUTURES = {
        'ZT=F': {'name': '2-Year T-Note', 'duration': 2},
        'ZF=F': {'name': '5-Year T-Note', 'duration': 5},
        'ZN=F': {'name': '10-Year T-Note', 'duration': 10},
        'ZB=F': {'name': '30-Year T-Bond', 'duration': 30}
    }
    
    def __init__(self):
        self.lookback_months = 12
        self.holding_months = 1
        self.risk_target_annual = 0.10  # 10% annualized vol target
    
    def generate_signals(self, as_of: date) -> list[Pick]:
        """Generate TSMOM signals for US Treasury futures."""
        signals = []
        
        for symbol, info in self.UST_FUTURES.items():
            # Compute 12-month return
            ret_12m = self._compute_return(symbol, months=self.lookback_months, as_of=as_of)
            if ret_12m is None:
                continue
            
            # TSMOM signal: LONG if positive return, SHORT if negative
            direction = 'LONG' if ret_12m > 0 else 'SHORT'
            
            # Position sizing: risk parity based on realized vol
            realized_vol = self._compute_realized_vol(symbol, days=63, as_of=as_of)  # 3-month
            if realized_vol is None or realized_vol <= 0:
                position_size = 1.0
            else:
                position_size = self.risk_target_annual / (realized_vol * math.sqrt(12))
            
            # Confidence based on |return| / vol (information ratio proxy)
            info_ratio = abs(ret_12m) / (realized_vol * math.sqrt(self.lookback_months)) if realized_vol else 0
            confidence = min(50 + info_ratio * 20, 95)
            
            signals.append(Pick(
                symbol=symbol,
                direction=direction,
                confidence=confidence,
                strategy=self.STRATEGY_NAME,
                asset_class='BOND',
                position_size=min(position_size, 2.0),  # cap at 2x leverage
                metadata={
                    'return_12m': ret_12m,
                    'realized_vol_3m': realized_vol,
                    'position_size': position_size,
                    'duration': info['duration'],
                    'bond_name': info['name'],
                    'tsmom_lookback_months': self.lookback_months
                }
            ))
        
        return signals
    
    def _compute_return(self, symbol: str, months: int, as_of: date) -> float | None:
        """Compute total return over N months using adjusted prices."""
        start = as_of - relativedelta(months=months)
        prices = self.data_client.get_adjusted_prices(symbol, start, as_of)
        if prices is None or len(prices) < months * 15:
            return None
        return (prices.iloc[-1] / prices.iloc[0]) - 1
    
    def _compute_realized_vol(self, symbol: str, days: int, as_of: date) -> float | None:
        """Compute annualized realized volatility from daily returns."""
        start = as_of - timedelta(days=days + 10)  # buffer for weekends
        prices = self.data_client.get_adjusted_prices(symbol, start, as_of)
        if prices is None or len(prices) < days * 0.8:
            return None
        daily_returns = prices.pct_change().dropna()
        return daily_returns.std() * math.sqrt(252)  # annualized
```

```yaml
# config/strategy_registry.yaml
strategies:
  bond_tsmom:
    asset_classes: [BOND]
    enabled: true
    mode: shadow  # 2-week shadow before production
    shadow_until: "2026-06-01"
    max_picks_per_day: 4  # one per tenor
    min_confidence: 50
    requires_data: [future_prices]
```

**Test Plan**
1. `test_long_signal_positive_return()`: Mock 12-month return +5% → LONG signal
2. `test_short_signal_negative_return()`: Mock 12-month return -3% → SHORT signal
3. `test_position_sizing()`: High vol (20%) → smaller position; Low vol (5%) → larger position
4. `test_all_four_tenors()`: Mock data for all 4 futures → 4 signals
5. `test_zero_return()`: 12-month return = 0 → direction defaults to SHORT (conservative)

**Acceptance Criteria**
- [ ] Strategy produces 1-4 signals per day (one per tenor)
- [ ] All signals have 12-month return and vol metadata
- [ ] Position sizing inversely proportional to realized vol
- [ ] Shadow mode for 2 weeks; promote if signals are directionally correct
- [ ] n reaches ≥30 within 30 days of going live

**Risk Assessment**
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| TSMOM fails in low-vol regime (treasury bubble) | Medium | High | Vol-adjusted sizing reduces exposure |
| Duration risk concentrated in long bonds | Medium | High | Risk-parity sizing gives more weight to ZT=F |
| Data gaps for adjusted futures prices | Low | High | Use continuous contract data; alert on gaps |

**Rollback Plan**
```python
# Immediate: Set bond_tsmom.mode = disabled in strategy_registry.yaml
# Verification: No BOND TSMOM picks after disable
```

---

### PR-B2: FRED_API_KEY Integration (Macro Data)

| Field | Detail |
|-------|--------|
| **Branch** | `infra/B2-fred-api-integration-20260518` |
| **Files Changed** | `data/fred_client.py`, `config/api_keys.yaml`, `.env.example`, `tests/test_fred_client.py` |
| **Est. Effort** | M (2-3 days) |
| **Parallelizable** | Yes (with PR-B1) |

**Problem Statement**
BOND strategy TSMOM needs macro context (yield curve slope, Fed Funds rate, inflation expectations) for regime filtering. FRED (Federal Reserve Economic Data) provides free API access to these series. Currently no FRED integration exists.

**Solution Description**
Add FRED API client with key rotation support. Fetch key macro series daily: DGS2, DGS10 (yield curve), FEDFUNDS, T10YIE (breakeven inflation). Store in local cache with TTL=24 hours.

**Code Changes**
```python
# data/fred_client.py (NEW)
import os
import requests
import pandas as pd
from datetime import date, timedelta
from functools import lru_cache

class FREDClient:
    """Client for Federal Reserve Economic Data (FRED) API."""
    
    BASE_URL = "https://api.stlouisfed.org/fred"
    
    # Key macro series for BOND strategy
    KEY_SERIES = {
        'DGS2': '2-Year Treasury Yield',
        'DGS5': '5-Year Treasury Yield',
        'DGS10': '10-Year Treasury Yield',
        'DGS30': '30-Year Treasury Yield',
        'FEDFUNDS': 'Federal Funds Effective Rate',
        'T10Y2Y': '10Y-2Y Spread',
        'T10YIE': '10-Year Breakeven Inflation',
    }
    
    def __init__(self):
        self.api_key = os.environ.get('FRED_API_KEY')
        if not self.api_key:
            raise ValueError("FRED_API_KEY not set in environment")
    
    @lru_cache(maxsize=128)
    def get_series(self, series_id: str, start_date: date = None, end_date: date = None) -> pd.Series:
        """Fetch a FRED series with caching."""
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=365)
        
        url = f"{self.BASE_URL}/series/observations"
        params = {
            'series_id': series_id,
            'api_key': self.api_key,
            'file_type': 'json',
            'observation_start': start_date.isoformat(),
            'observation_end': end_date.isoformat(),
            'sort_order': 'desc',
            'limit': 500
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        observations = data.get('observations', [])
        
        dates = [obs['date'] for obs in observations if obs['value'] != '.']
        values = [float(obs['value']) for obs in observations if obs['value'] != '.']
        
        series = pd.Series(values, index=pd.to_datetime(dates))
        series.index.name = 'date'
        series.name = series_id
        
        return series
    
    def get_yield_curve(self, as_of: date = None) -> pd.DataFrame:
        """Get full yield curve for a given date."""
        if as_of is None:
            as_of = date.today()
        
        curve = {}
        for series_id in ['DGS2', 'DGS5', 'DGS10', 'DGS30']:
            try:
                series = self.get_series(series_id, start_date=as_of - timedelta(days=7), end_date=as_of)
                if len(series) > 0:
                    curve[series_id] = series.iloc[0]  # most recent value
            except Exception as e:
                logging.warning(f"Failed to fetch {series_id}: {e}")
        
        return pd.DataFrame([curve]) if curve else pd.DataFrame()
    
    def get_curve_slope(self, as_of: date = None) -> float | None:
        """Get 10Y-2Y spread (recession indicator)."""
        try:
            series = self.get_series('T10Y2Y', start_date=as_of - timedelta(days=7), end_date=as_of)
            return series.iloc[0] if len(series) > 0 else None
        except Exception:
            return None
    
    def health_check(self) -> dict:
        """Verify API connectivity and key validity."""
        try:
            series = self.get_series('DGS10', start_date=date.today() - timedelta(days=5))
            return {
                'status': 'HEALTHY',
                'api_key_valid': True,
                'latest_data_date': series.index[0].strftime('%Y-%m-%d') if len(series) > 0 else None,
                'latest_value': series.iloc[0] if len(series) > 0 else None
            }
        except Exception as e:
            return {
                'status': 'UNHEALTHY',
                'api_key_valid': False,
                'error': str(e)
            }
```

```yaml
# config/api_keys.yaml
fred:
  required: true
  env_var: FRED_API_KEY
  tier: free
  rate_limit: "120 requests per minute"
  series:
    - DGS2
    - DGS5
    - DGS10
    - DGS30
    - FEDFUNDS
    - T10Y2Y
    - T10YIE
  cache_ttl_hours: 24
```

```bash
# .env.example (append)
# FRED API Key (free tier: https://fred.stlouisfed.org/docs/api/api_key.html)
FRED_API_KEY=your_fred_api_key_here
```

**Test Plan**
1. `test_series_fetch()`: Fetch DGS10, verify series has data points
2. `test_yield_curve()`: Fetch yield curve, verify 4 tenors present
3. `test_curve_slope()`: Fetch T10Y2Y, verify float value returned
4. `test_health_check()`: Run health check, verify HEALTHY status
5. `test_cache_hit()`: Fetch same series twice, verify second call uses cache
6. `test_missing_api_key()`: Unset FRED_API_KEY, verify ValueError raised

**Acceptance Criteria**
- [ ] FRED API key configured and validated
- [ ] All 7 key series fetchable with <5 second response time
- [ ] 24-hour cache reduces API calls by ≥80%
- [ ] Health check endpoint available for monitoring
- [ ] BOND strategy can access yield curve data for regime filtering

**Risk Assessment**
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| FRED API rate limit exceeded | Low | Medium | Cache layer; batch requests; backoff on 429 |
| API key expires or revoked | Low | High | Health check alerts; fallback to cached data |
| FRED data delayed (not real-time) | Medium | Medium | Document data lag; use for regime only, not signal timing |

**Rollback Plan**
```python
# Remove FRED_API_KEY from environment
# Set fred.required = false in api_keys.yaml
# BOND strategy falls back to market-derived yield data
```

---


## Section 7: PRs for Pick Traceability (NEW)

**Theme:** Full lifecycle tracking, filter chain auditing, symbol universe management, and scenario simulation for every pick.

**Context:** As the platform scales across asset classes, understanding why a specific pick was accepted or rejected becomes critical for debugging, compliance, and continuous improvement. The current system lacks end-to-end traceability.

---

### PR-T1: pick_lifecycle_logger.py + DB Migration

| Field | Detail |
|-------|--------|
| **Branch** | `trace/T1-pick-lifecycle-logger-20260518` |
| **Files Changed** | `traceability/pick_lifecycle_logger.py`, `db/migrations/V007_add_pick_lifecycle_log.sql`, `config/traceability.yaml`, `tests/test_lifecycle_logger.py` |
| **Est. Effort** | L (4-5 days) |
| **Parallelizable** | Yes |

**Problem Statement**
When a pick is rejected, there is no persistent log explaining which gate rejected it, at what time, and with what context. This makes debugging "missing picks" impossible and prevents auditing of gate effectiveness over time.

**Solution Description**
Create a `pick_lifecycle_log` table that records every significant event in a pick's lifecycle: creation, each gate evaluation (pass/fail with reason), scoring, booster application, final disposition, and settlement. Implement `PickLifecycleLogger` as a singleton that is called from `pick_orchestrator.py` and `quality_gates.py`.

**Code Changes**
```python
# traceability/pick_lifecycle_logger.py
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, asdict
import json
import logging

class LifecycleEvent(Enum):
    PICK_CREATED = "pick_created"
    GATE_EVALUATED = "gate_evaluated"
    SCORE_COMPUTED = "score_computed"
    BOOSTER_APPLIED = "booster_applied"
    DISPOSITION_DECIDED = "disposition_decided"
    EXECUTED = "executed"
    SETTLED = "settled"
    REJECTED = "rejected"
    EXPIRED = "expired"

@dataclass
class LifecycleEntry:
    entry_id: str
    pick_id: str
    event_type: str
    timestamp: datetime
    source_component: str  # e.g., "quality_gates.G2", "score_booster.M034"
    details: dict  # flexible JSON for event-specific data
    trace_version: str = "1.0"

class PickLifecycleLogger:
    """Singleton logger for complete pick lifecycle tracking."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.db = production_db_conn()
        self.buffer = []
        self.buffer_size = 100
        self.enabled = config.get('traceability.lifecycle_logging', True)
    
    def log_event(self, pick_id: str, event: LifecycleEvent, source: str, details: dict):
        """Log a lifecycle event."""
        if not self.enabled:
            return
        
        entry = LifecycleEntry(
            entry_id=self._generate_id(),
            pick_id=pick_id,
            event_type=event.value,
            timestamp=datetime.utcnow(),
            source_component=source,
            details=details
        )
        
        self.buffer.append(asdict(entry))
        
        if len(self.buffer) >= self.buffer_size:
            self._flush()
    
    def log_gate_result(self, pick_id: str, gate_name: str, passed: bool, 
                        reason: str = None, metadata: dict = None):
        """Convenience method for logging gate evaluations."""
        self.log_event(
            pick_id=pick_id,
            event=LifecycleEvent.GATE_EVALUATED,
            source=f"quality_gates.{gate_name}",
            details={
                'passed': passed,
                'reason': reason,
                'metadata': metadata or {}
            }
        )
    
    def log_booster(self, pick_id: str, booster_name: str, 
                    confidence_before: float, confidence_after: float, metadata: dict = None):
        """Convenience method for logging booster applications."""
        self.log_event(
            pick_id=pick_id,
            event=LifecycleEvent.BOOSTER_APPLIED,
            source=f"score_booster.{booster_name}",
            details={
                'confidence_before': confidence_before,
                'confidence_after': confidence_after,
                'delta': confidence_after - confidence_before,
                'metadata': metadata or {}
            }
        )
    
    def get_pick_trace(self, pick_id: str) -> list[dict]:
        """Retrieve full lifecycle trace for a pick."""
        query = """
            SELECT * FROM pick_lifecycle_log 
            WHERE pick_id = %s 
            ORDER BY timestamp
        """
        return pd.read_sql(query, self.db, params=(pick_id,)).to_dict('records')
    
    def get_gate_stats(self, gate_name: str, window_days: int = 7) -> dict:
        """Get statistics for a specific gate over a time window."""
        query = """
            SELECT 
                COUNT(*) as total_evaluations,
                SUM(CASE WHEN details->>'$.passed' = 'true' THEN 1 ELSE 0 END) as passes,
                SUM(CASE WHEN details->>'$.passed' = 'false' THEN 1 ELSE 0 END) as failures,
                AVG(CASE WHEN details->>'$.passed' = 'false' THEN 1.0 ELSE 0.0 END) as failure_rate
            FROM pick_lifecycle_log
            WHERE source_component = %s
              AND timestamp >= DATE_SUB(NOW(), INTERVAL %s DAY)
        """
        result = pd.read_sql(query, self.db, params=(f"quality_gates.{gate_name}", window_days))
        return {
            'gate': gate_name,
            'window_days': window_days,
            'total_evaluations': int(result['total_evaluations'].iloc[0]),
            'passes': int(result['passes'].iloc[0]),
            'failures': int(result['failures'].iloc[0]),
            'failure_rate': float(result['failure_rate'].iloc[0])
        }
    
    def _flush(self):
        """Flush buffered entries to database."""
        if not self.buffer:
            return
        
        query = """
            INSERT INTO pick_lifecycle_log 
            (entry_id, pick_id, event_type, timestamp, source_component, details, trace_version)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        with self.db.cursor() as cursor:
            for entry in self.buffer:
                cursor.execute(query, (
                    entry['entry_id'], entry['pick_id'], entry['event_type'],
                    entry['timestamp'], entry['source_component'],
                    json.dumps(entry['details']), entry['trace_version']
                ))
            self.db.commit()
        
        self.buffer = []
    
    def _generate_id(self) -> str:
        """Generate unique entry ID."""
        import uuid
        return f"lle_{uuid.uuid4().hex[:16]}"
    
    def shutdown(self):
        """Flush remaining buffer on shutdown."""
        self._flush()
```

```sql
-- db/migrations/V007_add_pick_lifecycle_log.sql
CREATE TABLE IF NOT EXISTS pick_lifecycle_log (
    entry_id VARCHAR(32) PRIMARY KEY,
    pick_id VARCHAR(32) NOT NULL,
    event_type VARCHAR(32) NOT NULL,
    timestamp DATETIME(3) NOT NULL,
    source_component VARCHAR(128) NOT NULL,
    details JSON,
    trace_version VARCHAR(8) DEFAULT '1.0',
    INDEX idx_pick_id (pick_id),
    INDEX idx_timestamp (timestamp),
    INDEX idx_event_type (event_type),
    INDEX idx_source_component (source_component),
    INDEX idx_pick_event (pick_id, event_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Partition by month for efficient querying
-- ALTER TABLE pick_lifecycle_log PARTITION BY RANGE (YEAR(timestamp) * 100 + MONTH(timestamp)) ...
```

```yaml
# config/traceability.yaml
traceability:
  lifecycle_logging:
    enabled: true
    buffer_size: 100
    flush_interval_seconds: 30
    retention_days: 90
    compression_after_days: 30
  
  query_endpoints:
    pick_trace: "/api/v1/trace/{pick_id}"
    gate_stats: "/api/v1/trace/gate/{gate_name}"
    component_health: "/api/v1/trace/health"
```

**Test Plan**
1. `test_log_pick_created()`: Create pick, verify PICK_CREATED event logged
2. `test_log_gate_pass()`: Gate passes, verify GATE_EVALUATED with passed=true
3. `test_log_gate_fail()`: Gate fails, verify GATE_EVALUATED with passed=false and reason
4. `test_buffer_flush()`: Create 100 events, verify flush at buffer_size
5. `test_get_pick_trace()`: Log 5 events for same pick, verify retrieval returns 5 ordered entries
6. `test_gate_stats()`: Log 10 gate evaluations (3 pass, 7 fail), verify failure_rate=0.7
7. `test_shutdown_flush()`: Log 5 events, call shutdown, verify all in DB

**Acceptance Criteria**
- [ ] Every pick has ≥3 lifecycle entries (created, gate evaluated, disposition decided)
- [ ] Gate rejection reasons are queryable by pick_id
- [ ] Buffer flush does not lose events on shutdown
- [ ] 90-day retention policy configured
- [ ] Query latency for single pick trace < 50ms

**Risk Assessment**
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Logging adds latency to pick path | Medium | High | Async buffer; batch inserts; disable if latency > 10ms per event |
| Database bloat from high-volume logging | Medium | Medium | 90-day retention; monthly partition rotation; compression |
| Log entries inconsistent with actual gate behavior | Low | High | Log entry written atomically with gate decision (same transaction) |

**Rollback Plan**
```python
# Immediate: Set traceability.lifecycle_logging.enabled = false
# Code revert: Remove logger calls from pick_orchestrator and quality_gates
# Data: pick_lifecycle_log table remains for audit; no writes after disable
```

---

### PR-T2: filter_traceback_engine.py

| Field | Detail |
|-------|--------|
| **Branch** | `trace/T2-filter-traceback-20260518` |
| **Files Changed** | `traceability/filter_traceback_engine.py`, `quality_gates.py`, `tests/test_filter_traceback.py` |
| **Est. Effort** | M (2-3 days) |
| **Depends On** | PR-T1 (lifecycle logger provides event data) |

**Problem Statement**
When a profitable pick is rejected by a gate, there is no systematic way to identify which gate caused the rejection and whether the rejection was correct. Overly aggressive gates destroy edge.

**Solution Description**
Implement `FilterTracebackEngine` that analyzes the filter chain for rejected picks. For each rejection, produce a "traceback" showing: (1) which gate rejected, (2) what the pick's attributes were, (3) what the gate threshold was, (4) whether nearby picks (same symbol/strategy, different time) were accepted. This enables gate calibration.

**Code Changes**
```python
# traceability/filter_traceback_engine.py
class FilterTracebackEngine:
    """Analyze gate rejections to identify overly aggressive filters."""
    
    def __init__(self):
        self.logger = PickLifecycleLogger()
        self.min_sample_size = 10
    
    def analyze_rejection(self, pick_id: str) -> dict:
        """Produce full traceback for a rejected pick."""
        trace = self.logger.get_pick_trace(pick_id)
        
        # Find the rejecting gate
        rejection_event = None
        for event in trace:
            if event['event_type'] == 'gate_evaluated' and \
               not event['details'].get('passed', True):
                rejection_event = event
                break
        
        if not rejection_event:
            return {'error': 'No rejection found in trace'}
        
        gate_name = rejection_event['source_component'].replace('quality_gates.', '')
        
        # Get recent context: same gate, same asset class, last 30 days
        pick_details = trace[0]['details'] if trace else {}
        asset_class = pick_details.get('asset_class', 'UNKNOWN')
        
        context = self._get_gate_context(gate_name, asset_class, days=30)
        
        # Compute "near-miss" rate: picks that passed this gate but failed later
        near_misses = self._compute_near_misses(gate_name, asset_class, days=30)
        
        return {
            'pick_id': pick_id,
            'rejected_by': gate_name,
            'rejection_reason': rejection_event['details'].get('reason', 'Unknown'),
            'rejection_metadata': rejection_event['details'].get('metadata', {}),
            'rejection_timestamp': rejection_event['timestamp'],
            'context': context,
            'near_misses': near_misses,
            'assessment': self._assess_gate_severity(gate_name, context)
        }
    
    def _get_gate_context(self, gate_name: str, asset_class: str, days: int) -> dict:
        """Get performance context for a specific gate."""
        stats = self.logger.get_gate_stats(gate_name, window_days=days)
        
        # Get rejected picks that would have been profitable
        query = """
            SELECT l.pick_id, l.details, p.pnl_usd
            FROM pick_lifecycle_log l
            JOIN picks p ON l.pick_id = p.pick_id
            WHERE l.source_component = %s
              AND l.details->>'$.passed' = 'false'
              AND l.timestamp >= DATE_SUB(NOW(), INTERVAL %s DAY)
              AND p.pnl_usd IS NOT NULL
            ORDER BY p.pnl_usd DESC
            LIMIT 50
        """
        df = pd.read_sql(query, self.logger.db, 
                        params=(f"quality_gates.{gate_name}", days))
        
        false_rejections = df[df['pnl_usd'] > 0]
        
        return {
            'total_rejections': stats['failures'],
            'rejection_rate': stats['failure_rate'],
            'false_rejections': len(false_rejections),
            'false_rejection_pnl': float(false_rejections['pnl_usd'].sum()) if len(false_rejections) > 0 else 0,
            'sample_size': stats['total_evaluations']
        }
    
    def _compute_near_misses(self, gate_name: str, asset_class: str, days: int) -> dict:
        """Find picks that passed this gate but were rejected by a later gate."""
        query = """
            SELECT l1.pick_id, l1.source_component as rejecting_gate, p.pnl_usd
            FROM pick_lifecycle_log l1
            JOIN pick_lifecycle_log l2 ON l1.pick_id = l2.pick_id
            JOIN picks p ON l1.pick_id = p.pick_id
            WHERE l1.source_component = %s
              AND l1.details->>'$.passed' = 'true'
              AND l2.event_type = 'rejected'
              AND l1.timestamp >= DATE_SUB(NOW(), INTERVAL %s DAY)
              AND p.pnl_usd IS NOT NULL
            LIMIT 100
        """
        df = pd.read_sql(query, self.logger.db,
                        params=(f"quality_gates.{gate_name}", days))
        
        profitable_near_misses = df[df['pnl_usd'] > 0]
        
        return {
            'count': len(df),
            'profitable_count': len(profitable_near_misses),
            'total_pnl_missed': float(profitable_near_misses['pnl_usd'].sum()) if len(profitable_near_misses) > 0 else 0
        }
    
    def _assess_gate_severity(self, gate_name: str, context: dict) -> str:
        """Assess whether a gate is overly aggressive."""
        if context['sample_size'] < self.min_sample_size:
            return "INSUFFICIENT_DATA"
        
        false_rejection_rate = context['false_rejections'] / max(context['total_rejections'], 1)
        
        if false_rejection_rate > 0.3 and context['false_rejection_pnl'] > 1000:
            return "OVERLY_AGGRESSIVE — recommend threshold relaxation"
        elif false_rejection_rate > 0.15:
            return "BORDERLINE — monitor closely"
        else:
            return "WELL_CALIBRATED"
    
    def generate_weekly_report(self) -> pd.DataFrame:
        """Generate weekly gate calibration report."""
        gates = ['G1', 'G2', 'G3', 'G4', 'G5', 'G6']
        rows = []
        
        for gate in gates:
            stats = self.logger.get_gate_stats(gate, window_days=7)
            if stats['total_evaluations'] > 0:
                rows.append({
                    'gate': gate,
                    'evaluations': stats['total_evaluations'],
                    'pass_rate': 1 - stats['failure_rate'],
                    'failure_rate': stats['failure_rate'],
                    'severity': 'TBD'  # would need full traceback for each
                })
        
        return pd.DataFrame(rows)
```

**Test Plan**
1. `test_rejection_traceback()`: Create rejected pick, verify traceback identifies correct gate
2. `test_false_rejection_detection()`: Mock 5 rejections (3 profitable), verify false_rejections=3
3. `test_gate_severity_assessment()`: 40% false rejection rate → OVERLY_AGGRESSIVE
4. `test_near_miss_computation()`: Pick passes G2 but rejected by G5 → counted as near-miss
5. `test_weekly_report()`: Log 50 evaluations across 3 gates, verify report has 3 rows

**Acceptance Criteria**
- [ ] Every rejected pick can be traced back to the specific gate and reason
- [ ] False rejection rate tracked per gate per week
- [ ] Weekly report generated automatically and posted to Slack
- [ ] Gates with >30% false rejection rate flagged for calibration review

**Risk Assessment**
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| False rejection analysis requires settled P&L (delayed) | High | Medium | Use estimated P&L from mark-to-market until settlement |
| Query performance on large log table | Medium | High | Monthly partitions; materialized views for common queries |

**Rollback Plan**
```python
# Remove FilterTracebackEngine instantiation from quality_gates
# Engine stops analyzing; historical traces remain in DB
```

---

### PR-T3: symbol_universe_manager.py

| Field | Detail |
|-------|--------|
| **Branch** | `trace/T3-symbol-universe-manager-20260518` |
| **Files Changed** | `traceability/symbol_universe_manager.py`, `config/universe_registry.yaml`, `tests/test_universe_manager.py` |
| **Est. Effort** | M (2-3 days) |
| **Parallelizable** | Yes |

**Problem Statement**
Symbol universes are scattered across multiple YAML files (`equity_universe.yaml`, `commodity_universe.yaml`, `etf_universe.yaml`). There is no centralized registry of which symbols are active, why they were added/removed, and who authorized the change. This creates audit gaps.

**Solution Description**
Create `SymbolUniverseManager` that provides a single API for all symbol universe operations. Every change (add, remove, activate, deactivate) requires a justification and is logged with the author and timestamp.

**Code Changes**
```python
# traceability/symbol_universe_manager.py
class SymbolUniverseManager:
    """Centralized manager for symbol universe changes with full audit trail."""
    
    def __init__(self):
        self.db = production_db_conn()
        self.logger = PickLifecycleLogger()
    
    def get_universe(self, asset_class: str, status: str = 'active') -> list[str]:
        """Get symbols in a universe by asset class and status."""
        query = """
            SELECT symbol, added_date, added_reason, added_by
            FROM symbol_universe
            WHERE asset_class = %s AND status = %s
            ORDER BY added_date
        """
        df = pd.read_sql(query, self.db, params=(asset_class, status))
        return df['symbol'].tolist()
    
    def add_symbol(self, symbol: str, asset_class: str, added_by: str, 
                   reason: str, metadata: dict = None) -> bool:
        """Add a symbol to the universe with full audit trail."""
        query = """
            INSERT INTO symbol_universe 
            (symbol, asset_class, status, added_date, added_by, added_reason, metadata)
            VALUES (%s, %s, 'active', NOW(), %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                status = 'active',
                added_date = NOW(),
                added_by = VALUES(added_by),
                added_reason = VALUES(added_reason)
        """
        with self.db.cursor() as cursor:
            cursor.execute(query, (symbol, asset_class, added_by, reason, 
                                   json.dumps(metadata or {})))
            self.db.commit()
        
        self._log_universe_change('ADD', symbol, asset_class, added_by, reason)
        return True
    
    def remove_symbol(self, symbol: str, asset_class: str, removed_by: str,
                      reason: str, review_date: date = None) -> bool:
        """Remove a symbol from the active universe."""
        query = """
            UPDATE symbol_universe
            SET status = 'removed',
                removed_date = NOW(),
                removed_by = %s,
                removed_reason = %s,
                review_date = %s
            WHERE symbol = %s AND asset_class = %s
        """
        with self.db.cursor() as cursor:
            cursor.execute(query, (removed_by, reason, review_date, symbol, asset_class))
            self.db.commit()
        
        self._log_universe_change('REMOVE', symbol, asset_class, removed_by, reason)
        return True
    
    def get_symbol_history(self, symbol: str) -> list[dict]:
        """Get full history of a symbol in the universe."""
        query = """
            SELECT * FROM symbol_universe WHERE symbol = %s ORDER BY added_date
        """
        return pd.read_sql(query, self.db, params=(symbol,)).to_dict('records')
    
    def get_universe_summary(self) -> pd.DataFrame:
        """Summary of all universes by asset class and status."""
        query = """
            SELECT asset_class, status, COUNT(*) as count
            FROM symbol_universe
            GROUP BY asset_class, status
            ORDER BY asset_class, status
        """
        return pd.read_sql(query, self.db)
    
    def validate_universe_integrity(self) -> dict:
        """Check for integrity issues in universe configuration."""
        issues = []
        
        # Check for duplicates
        query = """
            SELECT symbol, asset_class, COUNT(*) as cnt
            FROM symbol_universe
            WHERE status = 'active'
            GROUP BY symbol, asset_class
            HAVING cnt > 1
        """
        duplicates = pd.read_sql(query, self.db)
        if len(duplicates) > 0:
            issues.append(f"Duplicate active symbols: {len(duplicates)} found")
        
        # Check for symbols without data sources
        query = """
            SELECT symbol, asset_class FROM symbol_universe
            WHERE status = 'active' AND data_source IS NULL
        """
        no_source = pd.read_sql(query, self.db)
        if len(no_source) > 0:
            issues.append(f"Symbols without data source: {len(no_source)} found")
        
        return {
            'passed': len(issues) == 0,
            'issues': issues,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _log_universe_change(self, action: str, symbol: str, asset_class: str,
                             actor: str, reason: str):
        """Log universe changes to lifecycle logger."""
        self.logger.log_event(
            pick_id=f"universe_{symbol}",
            event=LifecycleEvent(event_type=f"universe_{action.lower()}"),
            source="symbol_universe_manager",
            details={
                'action': action,
                'symbol': symbol,
                'asset_class': asset_class,
                'actor': actor,
                'reason': reason
            }
        )
```

```sql
-- db/migrations/V008_add_symbol_universe.sql
CREATE TABLE IF NOT EXISTS symbol_universe (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(32) NOT NULL,
    asset_class VARCHAR(16) NOT NULL,
    status ENUM('active', 'removed', 'pending', 'suspended') DEFAULT 'active',
    added_date DATETIME NOT NULL,
    added_by VARCHAR(64) NOT NULL,
    added_reason TEXT,
    removed_date DATETIME,
    removed_by VARCHAR(64),
    removed_reason TEXT,
    review_date DATE,
    data_source VARCHAR(32),
    metadata JSON,
    UNIQUE KEY uk_symbol_class (symbol, asset_class),
    INDEX idx_asset_status (asset_class, status),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Test Plan**
1. `test_add_symbol()`: Add AAPL to EQUITY, verify active in universe
2. `test_remove_symbol()`: Remove AAPL, verify status='removed' and review_date set
3. `test_duplicate_prevention()`: Add AAPL twice, verify only one active entry
4. `test_symbol_history()`: Add, remove, re-add AAPL, verify 3 history entries
5. `test_integrity_validation()`: Add symbol without data_source, verify validation catches it

**Acceptance Criteria**
- [ ] All symbol changes require `added_by` and `reason` (no anonymous changes)
- [ ] Every removed symbol has a `review_date`
- [ ] Universe integrity check passes with zero issues
- [ ] Full history retrievable for any symbol

**Risk Assessment**
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Migration from YAML files to DB loses history | Medium | High | Import existing YAML data with "legacy_migration" as added_by |
| Performance of DB queries vs. YAML file reads | Low | Medium | Cache active universes in memory; invalidate on change |

**Rollback Plan**
```python
# Restore YAML files as primary source of truth
# Keep DB as audit trail only
# Update all callers to read from YAML instead of SymbolUniverseManager
```

---

### PR-T4: what_if_simulator.py

| Field | Detail |
|-------|--------|
| **Branch** | `trace/T4-what-if-simulator-20260518` |
| **Files Changed** | `traceability/what_if_simulator.py`, `simulation_engine.py`, `tests/test_what_if_simulator.py` |
| **Est. Effort** | L (4-5 days) |
| **Depends On** | PR-T1 (lifecycle logger provides historical data), PR-T2 (traceback provides gate logic) |

**Problem Statement**
When considering a gate change (e.g., relaxing VIX threshold from 25 to 30), there is no way to estimate the impact on pick volume and expected profitability without deploying to production. This leads to conservative gate management.

**Solution Description**
Build a "what-if" simulator that replays historical picks through modified gate configurations. For any proposed change, estimate: (1) additional picks that would have passed, (2) estimated additional P&L, (3) estimated change in PF, (4) risk metrics (max drawdown, VaR).

**Code Changes**
```python
# traceability/what_if_simulator.py
class WhatIfSimulator:
    """Simulate the impact of proposed gate/strategy changes on historical performance."""
    
    def __init__(self):
        self.logger = PickLifecycleLogger()
        self.traceback = FilterTracebackEngine()
    
    def simulate_gate_change(
        self,
        gate_name: str,
        parameter: str,
        current_value: float,
        proposed_value: float,
        asset_class: str = None,
        days: int = 90
    ) -> dict:
        """Simulate impact of changing a single gate parameter."""
        
        # Get all picks that were rejected by this gate in the window
        rejected = self._get_rejected_picks(gate_name, asset_class, days)
        
        # Re-evaluate each rejected pick with the proposed parameter
        would_pass = []
        still_rejected = []
        
        for pick in rejected:
            # Re-run gate with proposed value
            result = self._reevaluate_gate(pick, gate_name, parameter, proposed_value)
            if result:
                would_pass.append(pick)
            else:
                still_rejected.append(pick)
        
        # Get actual P&L for picks that would have passed
        additional_pnl = sum(p.get('pnl_usd', 0) for p in would_pass)
        winning_picks = [p for p in would_pass if p.get('pnl_usd', 0) > 0]
        losing_picks = [p for p in would_pass if p.get('pnl_usd', 0) <= 0]
        
        additional_gross_profit = sum(p.get('pnl_usd', 0) for p in winning_picks)
        additional_gross_loss = abs(sum(p.get('pnl_usd', 0) for p in losing_picks))
        additional_pf = additional_gross_profit / additional_gross_loss if additional_gross_loss > 0 else float('inf')
        
        # Get baseline stats for comparison
        baseline = self._get_baseline_stats(asset_class, days)
        
        return {
            'simulation_id': f"sim_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            'gate': gate_name,
            'parameter': parameter,
            'current_value': current_value,
            'proposed_value': proposed_value,
            'asset_class': asset_class,
            'window_days': days,
            'rejected_in_window': len(rejected),
            'would_pass': len(would_pass),
            'still_rejected': len(still_rejected),
            'additional_pnl': additional_pnl,
            'additional_pf': additional_pf,
            'additional_win_rate': len(winning_picks) / max(len(would_pass), 1) * 100,
            'baseline': baseline,
            'projected_pf': self._project_pf(baseline, additional_pnl, additional_gross_profit, additional_gross_loss),
            'recommendation': self._generate_recommendation(additional_pf, len(would_pass))
        }
    
    def simulate_strategy_enable(
        self,
        strategy_name: str,
        asset_class: str,
        backtest_pf: float,
        backtest_wr: float,
        expected_picks_per_month: int
    ) -> dict:
        """Simulate impact of enabling a new strategy."""
        
        # Get current portfolio stats
        current_stats = self._get_baseline_stats(asset_class, days=90)
        
        # Project blended PF with new strategy
        current_n = current_stats['n_picks']
        current_pf = current_stats['profit_factor']
        current_gp = current_stats['gross_profit']
        current_gl = current_stats['gross_loss']
        
        new_n = expected_picks_per_month * 3  # 3-month projection
        
        # Estimate new strategy contribution
        new_gp = new_n * backtest_wr / 100 * abs(current_stats.get('avg_win_pnl', 100))
        new_gl = new_n * (1 - backtest_wr / 100) * abs(current_stats.get('avg_loss_pnl', 50))
        
        projected_pf = (current_gp + new_gp) / (current_gl + new_gl) if (current_gl + new_gl) > 0 else float('inf')
        
        return {
            'simulation_type': 'strategy_enable',
            'strategy': strategy_name,
            'asset_class': asset_class,
            'current_pf': current_pf,
            'projected_pf': projected_pf,
            'current_n_3m': current_n,
            'projected_n_3m': current_n + new_n,
            'pf_change': projected_pf - current_pf,
            'recommendation': 'GO' if projected_pf > current_pf and backtest_pf >= 1.5 else 'NO-GO'
        }
    
    def _reevaluate_gate(self, pick: dict, gate_name: str, parameter: str, proposed_value: float) -> bool:
        """Re-evaluate a single pick against a gate with modified parameter."""
        # Dispatch to gate-specific re-evaluation
        dispatch = {
            'G1_asset_class_eligibility': self._reeval_G1,
            'G2_strategy_eligibility': self._reeval_G2,
            'G3_confidence_floor': self._reeval_G3,
            'G4_vix_gate': self._reeval_G4,
            'G5_post_cost_expectancy': self._reeval_G5,
            'G6_concentration': self._reeval_G6,
        }
        
        evaluator = dispatch.get(gate_name)
        if evaluator:
            return evaluator(pick, parameter, proposed_value)
        return False  # unknown gate, conservative
    
    def _reeval_G4(self, pick: dict, parameter: str, proposed_value: float) -> bool:
        """Re-evaluate VIX gate with proposed threshold."""
        if parameter != 'threshold':
            return False
        vix_at_pick_time = pick.get('metadata', {}).get('vix_level', 999)
        return vix_at_pick_time < proposed_value  # would pass with relaxed threshold
    
    def _get_baseline_stats(self, asset_class: str, days: int) -> dict:
        """Get current production stats for comparison."""
        query = """
            SELECT 
                COUNT(*) as n_picks,
                SUM(CASE WHEN pnl_usd > 0 THEN pnl_usd ELSE 0 END) as gross_profit,
                SUM(CASE WHEN pnl_usd < 0 THEN ABS(pnl_usd) ELSE 0 END) as gross_loss,
                AVG(CASE WHEN pnl_usd > 0 THEN pnl_usd END) as avg_win_pnl,
                AVG(CASE WHEN pnl_usd < 0 THEN pnl_usd END) as avg_loss_pnl
            FROM picks
            WHERE asset_class = %s
              AND entry_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
              AND status = 'CLOSED'
        """
        df = pd.read_sql(query, self.logger.db, params=(asset_class, days))
        row = df.iloc[0]
        return {
            'n_picks': int(row['n_picks'] or 0),
            'gross_profit': float(row['gross_profit'] or 0),
            'gross_loss': float(row['gross_loss'] or 0),
            'profit_factor': float(row['gross_profit'] or 0) / float(row['gross_loss'] or 1),
            'avg_win_pnl': float(row['avg_win_pnl'] or 0),
            'avg_loss_pnl': float(row['avg_loss_pnl'] or 0)
        }
    
    def _project_pf(self, baseline: dict, add_pnl: float, add_gp: float, add_gl: float) -> float:
        """Project new PF with additional picks."""
        new_gp = baseline['gross_profit'] + add_gp
        new_gl = baseline['gross_loss'] + add_gl
        return new_gp / new_gl if new_gl > 0 else float('inf')
    
    def _generate_recommendation(self, additional_pf: float, n_additional: int) -> str:
        """Generate human-readable recommendation."""
        if additional_pf >= 2.0 and n_additional >= 5:
            return "STRONG_GO — significant profitable edge with meaningful volume"
        elif additional_pf >= 1.5 and n_additional >= 3:
            return "GO — profitable edge, moderate volume"
        elif additional_pf >= 1.0:
            return "CONDITIONAL — marginal edge, monitor closely"
        else:
            return "NO-GO — proposed change would reduce profitability"
```

**Test Plan**
1. `test_simulate_vix_relaxation()`: VIX 25→30, verify additional picks calculated
2. `test_recommendation_strong_go()`: PF=2.5, n=10 → STRONG_GO
3. `test_recommendation_no_go()`: PF=0.8, n=5 → NO-GO
4. `test_strategy_enable_sim()`: Enable new strategy with PF=2.0, verify projected PF computed
5. `test_gate_reeval()`: Pick with VIX=27, threshold changed to 30 → would pass

**Acceptance Criteria**
- [ ] Simulator produces actionable recommendations (GO/NO-GO/CONDITIONAL)
- [ ] Projected PF within ±0.2 of actual post-change PF (validated on first 3 changes)
- [ ] Simulation completes in < 5 seconds for 90-day window
- [ ] Results include sensitivity analysis (what if PF is 20% worse than backtest?)

**Risk Assessment**
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Simulator overestimates because it uses known P&L (look-ahead bias) | Medium | High | Use estimated P&L at entry time, not settled P&L |
| Proposed change interacts with other gates non-linearly | Medium | Medium | Run full re-simulation through all gates, not just the changed one |

**Rollback Plan**
```python
# Simulator is advisory only; no production impact
# Rollback: Remove simulator module
```

---

## Section 8: Infrastructure PRs

**Theme:** Cost-aware gating, slippage modeling, tail-risk management, per-symbol autopsy, and concentration checking.

---

### PR-I1: Post-Cost Expectancy Gate Promotion (Warning → Hard Gate)

| Field | Detail |
|-------|--------|
| **Branch** | `infra/I1-post-cost-hard-gate-20260518` |
| **Files Changed** | `quality_gates.py`, `config/gate_severity.yaml`, `tests/test_post_cost_gate.py` |
| **Est. Effort** | M (2-3 days) |
| **Parallelizable** | Yes |

**Problem Statement**
G5 (Post-Cost Expectancy) currently operates as a WARNING gate — it logs when expected return after costs is negative but does not block the pick. Analysis shows 23% of picks passing through G5 with negative expectancy are unprofitable, costing an estimated $2,400/month in wasted trades.

**Solution Description**
Promote G5 from WARNING to HARD gate. Picks with negative post-cost expectancy (expected return - all-in costs < 0) are rejected. The gate considers: spread, slippage (from PR-I2), commission, and financing.

**Code Changes**
```python
# quality_gates.py
class PostCostExpectancyGate:
    """G5: Post-cost expectancy — promoted to HARD gate by PR-I1."""
    
    def __init__(self):
        self.mode = 'HARD'  # promoted from 'WARNING'
        self.min_expectancy_bps = 5  # minimum 5 bps edge after all costs
    
    def evaluate(self, pick: Pick) -> GateResult:
        """Reject picks with negative post-cost expectancy."""
        expected_return_bps = pick.metadata.get('expected_return_bps', 0)
        
        # Compute all-in costs
        spread_cost = self._get_spread_cost(pick)
        slippage_cost = self._get_slippage_cost(pick)  # wired from PR-I2
        commission = self._get_commission(pick)
        financing = self._get_financing_cost(pick)
        
        total_cost_bps = spread_cost + slippage_cost + commission + financing
        net_expectancy = expected_return_bps - total_cost_bps
        
        pick.metadata['post_cost_analysis'] = {
            'expected_return_bps': expected_return_bps,
            'spread_cost_bps': spread_cost,
            'slippage_cost_bps': slippage_cost,
            'commission_bps': commission,
            'financing_bps': financing,
            'total_cost_bps': total_cost_bps,
            'net_expectancy_bps': net_expectancy
        }
        
        if net_expectancy < self.min_expectancy_bps:
            return GateResult(
                passed=False,
                gate='G5',
                reason=f"Post-cost expectancy {net_expectancy:.1f}bps < minimum {self.min_expectancy_bps}bps",
                severity='HARD',
                metadata={
                    'net_expectancy_bps': net_expectancy,
                    'total_cost_bps': total_cost_bps,
                    'pick_expected_return_bps': expected_return_bps
                }
            )
        
        return GateResult(passed=True, gate='G5')
    
    def _get_spread_cost(self, pick: Pick) -> float:
        """Get half-spread cost in basis points."""
        spread_bps = pick.metadata.get('spread_bps', 5)  # default 5bps
        return spread_bps / 2  # half-spread on entry + half on exit
    
    def _get_slippage_cost(self, pick: Pick) -> float:
        """Get slippage estimate from slippage model (PR-I2)."""
        slippage_model = pick.metadata.get('slippage_model_bps')
        if slippage_model is not None:
            return slippage_model
        # Fallback: asset-class defaults
        defaults = {'CRYPTO': 8, 'COMMODITY': 5, 'ETF': 2, 'EQUITY': 3, 'FOREX': 3, 'BOND': 4, 'FUTURES': 5}
        return defaults.get(pick.asset_class, 5)
    
    def _get_commission(self, pick: Pick) -> float:
        """Get commission cost in basis points."""
        commissions = {'CRYPTO': 5, 'COMMODITY': 8, 'ETF': 1, 'EQUITY': 3, 'FOREX': 2, 'BOND': 5, 'FUTURES': 6}
        return commissions.get(pick.asset_class, 5)
    
    def _get_financing_cost(self, pick: Pick) -> float:
        """Get estimated financing cost for holding period."""
        holding_days = pick.metadata.get('expected_holding_days', 1)
        financing_rate_annual = pick.metadata.get('financing_rate', 0.05)  # 5% default
        return holding_days * (financing_rate_annual / 365) * 10000  # convert to bps
```

**Test Plan**
1. `test_positive_expectancy_passes()`: net=15bps → passes
2. `test_negative_expectancy_blocked()`: net=-5bps → HARD blocked
3. `test_exactly_at_threshold()`: net=5bps → passes (threshold is inclusive)
4. `test_cost_breakdown_logged()`: Blocked pick has full cost breakdown in metadata
5. `test_all_asset_classes()`: Test with each asset class, verify correct default costs

**Acceptance Criteria**
- [ ] ≥20% reduction in unprofitable picks with negative expectancy
- [ ] Cost breakdown visible in audit log for every blocked pick
- [ ] Monthly cost savings ≥ $1,500 (measured over 30 days)
- [ ] Slippage model (PR-I2) integrated when available

**Risk Assessment**
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Overly aggressive cost assumptions block good picks | Medium | High | Conservative defaults; relax min_expectancy if pick volume drops >30% |
| Cost computation adds latency to pick path | Low | Medium | Pre-computed cost tables per asset class |

**Rollback Plan**
```python
# Immediate: Set PostCostExpectancyGate.mode = 'WARNING'
# Verification: Negative expectancy picks log warning but are not blocked
```

---

### PR-I2: Slippage Model Wire-Up

| Field | Detail |
|-------|--------|
| **Branch** | `infra/I2-slippage-model-20260518` |
| **Files Changed** | `models/slippage_model.py`, `quality_gates.py`, `config/slippage_config.yaml`, `tests/test_slippage_model.py` |
| **Est. Effort** | L (4-5 days) |
| **Depends On** | PR-I1 (slippage feeds into post-cost gate) |

**Problem Statement**
Current slippage estimates are static defaults (e.g., 3bps for EQUITY). Actual slippage varies significantly by time-of-day, volatility, order size, and liquidity. Real CRYPTO slippage during high-vol periods exceeds 50bps vs. 8bps default.

**Solution Description**
Implement a data-driven slippage model that estimates slippage based on: (1) recent realized slippage per symbol, (2) current volatility regime, (3) order size relative to ADV, (4) time-of-day liquidity patterns. Feed into G5 post-cost gate.

**Code Changes**
```python
# models/slippage_model.py
class SlippageModel:
    """Data-driven slippage estimation per symbol and regime."""
    
    def __init__(self):
        self.db = production_db_conn()
        self.default_slippage = {
            'CRYPTO': 8, 'COMMODITY': 5, 'ETF': 2, 'EQUITY': 3,
            'FOREX': 3, 'BOND': 4, 'FUTURES': 5
        }
    
    def estimate_slippage(
        self,
        symbol: str,
        asset_class: str,
        order_size_usd: float,
        direction: str,
        as_of: datetime = None
    ) -> float:
        """Estimate slippage in basis points."""
        if as_of is None:
            as_of = datetime.utcnow()
        
        # Factor 1: Symbol-specific realized slippage (30-day)
        symbol_slippage = self._get_symbol_realized_slippage(symbol, days=30)
        
        # Factor 2: Volatility regime multiplier
        vol_regime = self._get_volatility_regime(symbol, as_of)
        vol_multiplier = {'LOW': 0.7, 'NORMAL': 1.0, 'HIGH': 1.5, 'EXTREME': 2.5}.get(vol_regime, 1.0)
        
        # Factor 3: Order size relative to ADV
        adv = self._get_adv(symbol)
        size_multiplier = 1.0
        if adv and adv > 0:
            pct_adv = order_size_usd / adv
            if pct_adv > 0.01:  # >1% of ADV
                size_multiplier = 1 + (pct_adv * 50)  # exponential penalty
        
        # Factor 4: Time-of-day liquidity
        tod_multiplier = self._get_time_of_day_multiplier(as_of)
        
        # Combine
        base_slippage = symbol_slippage or self.default_slippage.get(asset_class, 5)
        estimated_slippage = base_slippage * vol_multiplier * size_multiplier * tod_multiplier
        
        return min(estimated_slippage, 200)  # cap at 200bps
    
    def _get_symbol_realized_slippage(self, symbol: str, days: int) -> float | None:
        """Get average realized slippage for a symbol over N days."""
        query = """
            SELECT AVG(ABS(actual_fill_price - signal_price) / signal_price * 10000) as avg_slippage_bps
            FROM fills
            WHERE symbol = %s
              AND fill_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
              AND signal_price IS NOT NULL
        """
        df = pd.read_sql(query, self.db, params=(symbol, days))
        val = df['avg_slippage_bps'].iloc[0]
        return float(val) if val and not pd.isna(val) else None
    
    def _get_volatility_regime(self, symbol: str, as_of: datetime) -> str:
        """Classify volatility regime based on recent realized vol vs. historical."""
        # Compare 5-day realized vol to 252-day realized vol
        query = """
            SELECT 
                STDDEV(daily_return) * SQRT(252) as vol_5d,
                (SELECT STDDEV(daily_return) * SQRT(252) 
                 FROM daily_returns WHERE symbol = %s 
                 AND date >= DATE_SUB(%s, INTERVAL 252 DAY)) as vol_252d
            FROM daily_returns
            WHERE symbol = %s AND date >= DATE_SUB(%s, INTERVAL 5 DAY)
        """
        df = pd.read_sql(query, self.db, params=(symbol, as_of, symbol, as_of))
        
        if len(df) == 0 or df['vol_252d'].iloc[0] is None or df['vol_252d'].iloc[0] == 0:
            return 'NORMAL'
        
        ratio = df['vol_5d'].iloc[0] / df['vol_252d'].iloc[0]
        
        if ratio < 0.5:
            return 'LOW'
        elif ratio < 1.2:
            return 'NORMAL'
        elif ratio < 2.0:
            return 'HIGH'
        else:
            return 'EXTREME'
    
    def _get_time_of_day_multiplier(self, as_of: datetime) -> float:
        """Adjust slippage for time-of-day liquidity patterns."""
        hour = as_of.hour
        # Less liquid during pre-market and after-hours
        if 9 <= hour < 10:
            return 1.0  # Regular hours
        elif 10 <= hour < 15:
            return 0.8  # Peak liquidity
        elif 15 <= hour < 16:
            return 1.2  # Close auction
        else:
            return 1.5  # Extended hours / overnight
    
    def _get_adv(self, symbol: str) -> float | None:
        """Get average daily volume in USD."""
        query = """
            SELECT AVG(volume * close_price) as adv_usd
            FROM daily_ohlcv
            WHERE symbol = %s
            AND date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        """
        df = pd.read_sql(query, self.db, params=(symbol,))
        val = df['adv_usd'].iloc[0]
        return float(val) if val and not pd.isna(val) else None
```

**Test Plan**
1. `test_default_slippage()`: Unknown symbol → returns asset class default
2. `test_vol_regime_high()`: 5d vol 2x 252d vol → HIGH multiplier (1.5x)
3. `test_size_penalty()`: Order = 5% of ADV → size_multiplier > 1
4. `test_tod_peak()`: 11 AM → multiplier 0.8
5. `test_caps_at_200bps()`: All factors combine to >200 → capped at 200
6. `test_integration_with_g5()`: Slippage model output feeds correctly into G5

**Acceptance Criteria**
- [ ] Slippage estimates within ±20% of actual realized slippage (measured over 30 days)
- [ ] G5 uses symbol-specific slippage when model data available
- [ ] High-vol regime detected and accounted for (vol multiplier > 1.0)
- [ ] Model updates automatically as new fill data arrives

**Risk Assessment**
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Model underestimates slippage for illiquid symbols | Medium | High | Floor at 2x default for symbols with <10 fills in 30 days |
| ADV data stale | Low | Medium | Use 30-day rolling ADV; alert if data >3 days old |
| Model adds significant latency | Medium | High | Cache slippage estimates; refresh every 5 minutes |

**Rollback Plan**
```python
# Revert G5 to use default slippage values instead of model
# Keep slippage_model.py running in shadow mode
# Verification: G5 uses static defaults again
```

---

### PR-I3: MDD/CVaR Tail-Risk Gate

| Field | Detail |
|-------|--------|
| **Branch** | `infra/I3-tail-risk-gate-20260518` |
| **Files Changed** | `risk/tail_risk_gate.py`, `quality_gates.py`, `config/tail_risk_limits.yaml`, `tests/test_tail_risk_gate.py` |
| **Est. Effort** | L (4-5 days) |
| **Parallelizable** | Yes |

**Problem Statement**
The platform has no explicit tail-risk gate. During March 2026 CRYPTO crash, the system experienced a 18% MDD in 48 hours because no mechanism existed to reduce exposure when tail risk was elevated. We need a gate that monitors portfolio-level MDD and CVaR (Conditional Value at Risk) and reduces position sizes or blocks new picks when tail risk exceeds limits.

**Solution Description**
Implement G7 (Tail-Risk Gate) that tracks: (1) current portfolio MDD vs. limit, (2) 1-day CVaR at 95% confidence, (3) correlation spike detection (when normally uncorrelated assets move together). When triggered, reduce new pick confidence by 50% or block entirely depending on severity.

**Code Changes**
```python
# risk/tail_risk_gate.py
class TailRiskGate:
    """G7: Portfolio tail-risk monitoring and intervention."""
    
    def __init__(self):
        self.mdd_limit = 0.15  # 15% max drawdown
        self.cvar_limit_1d_95 = 0.05  # 5% CVaR limit
        self.correlation_spike_threshold = 0.8  # avg correlation
        self.db = production_db_conn()
    
    def evaluate(self, pick: Pick, portfolio: Portfolio) -> GateResult:
        """Assess tail risk and modify or block pick."""
        
        # Check MDD
        current_mdd = portfolio.current_drawdown
        if current_mdd > self.mdd_limit:
            return GateResult(
                passed=False,
                gate='G7',
                reason=f"Portfolio MDD {current_mdd:.1%} exceeds limit {self.mdd_limit:.1%}",
                severity='HARD',
                metadata={'current_mdd': current_mdd, 'mdd_limit': self.mdd_limit}
            )
        
        # Check CVaR
        cvar_1d_95 = self._compute_cvar(portfolio, confidence=0.95, horizon=1)
        if cvar_1d_95 > self.cvar_limit_1d_95:
            return GateResult(
                passed=False,
                gate='G7',
                reason=f"1-day CVaR (95%) {cvar_1d_95:.1%} exceeds limit {self.cvar_limit_1d_95:.1%}",
                severity='HARD',
                metadata={'cvar_1d_95': cvar_1d_95, 'cvar_limit': self.cvar_limit_1d_95}
            )
        
        # Check correlation spike
        avg_correlation = self._compute_avg_correlation(portfolio)
        if avg_correlation > self.correlation_spike_threshold:
            # Soft intervention: reduce confidence but don't block
            pick.confidence = pick.confidence * 0.5
            pick.metadata['G7_intervention'] = 'confidence_halved'
            pick.metadata['correlation_spike'] = avg_correlation
            return GateResult(
                passed=True,
                gate='G7',
                reason=f"Correlation spike {avg_correlation:.2f}; confidence reduced to {pick.confidence:.0f}",
                severity='WARNING',
                metadata={'avg_correlation': avg_correlation}
            )
        
        return GateResult(passed=True, gate='G7')
    
    def _compute_cvar(self, portfolio: Portfolio, confidence: float, horizon: int) -> float:
        """Compute Conditional Value at Risk using historical simulation."""
        # Get historical portfolio returns
        returns = portfolio.get_historical_returns(days=252)
        if len(returns) < 100:
            return 0.0  # insufficient data
        
        # Compute VaR at confidence level
        var = np.percentile(returns, (1 - confidence) * 100)
        
        # CVaR = average of returns worse than VaR
        tail_returns = returns[returns <= var]
        cvar = abs(tail_returns.mean()) if len(tail_returns) > 0 else 0
        
        # Scale to horizon
        return cvar * math.sqrt(horizon)
    
    def _compute_avg_correlation(self, portfolio: Portfolio) -> float:
        """Compute average pairwise correlation of portfolio positions."""
        positions = portfolio.get_open_positions()
        if len(positions) < 2:
            return 0.0
        
        symbols = [p.symbol for p in positions]
        returns_matrix = self._get_returns_matrix(symbols, days=30)
        
        if returns_matrix is None or returns_matrix.shape[1] < 2:
            return 0.0
        
        corr_matrix = returns_matrix.corr()
        # Extract upper triangle (excluding diagonal)
        mask = np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
        correlations = corr_matrix.where(mask).stack().values
        
        return float(np.mean(correlations)) if len(correlations) > 0 else 0.0
    
    def _get_returns_matrix(self, symbols: list[str], days: int) -> pd.DataFrame | None:
        """Get daily returns matrix for a list of symbols."""
        query = """
            SELECT date, symbol, daily_return
            FROM daily_returns
            WHERE symbol IN %s
            AND date >= DATE_SUB(NOW(), INTERVAL %s DAY)
        """
        df = pd.read_sql(query, self.db, params=(tuple(symbols), days))
        if len(df) == 0:
            return None
        
        return df.pivot(index='date', columns='symbol', values='daily_return').dropna()
```

```yaml
# config/tail_risk_limits.yaml
tail_risk:
  mdd_limit: 0.15
  cvar_1d_95_limit: 0.05
  cvar_5d_95_limit: 0.10
  correlation_spike_threshold: 0.80
  confidence_reduction_factor: 0.50
  
  escalation:
    - level: 1
      condition: "mdd > 0.10"
      action: "reduce_new_position_size_to_50pct"
    - level: 2
      condition: "mdd > 0.15"
      action: "block_all_new_picks"
    - level: 3
      condition: "mdd > 0.20"
      action: "emergency_close_all_positions"
```

**Test Plan**
1. `test_mdd_hard_block()`: Portfolio MDD=16% → HARD blocked
2. `test_cvar_hard_block()`: CVaR=6% → HARD blocked
3. `test_correlation_spike_soft()`: Avg correlation=0.85 → passes but confidence halved
4. `test_normal_conditions()`: MDD=5%, CVaR=2%, correlation=0.3 → passes normally
5. `test_escalation_level_2()`: MDD=16% → block_all_new_picks triggered

**Acceptance Criteria**
- [ ] MDD limit respected: no picks when portfolio MDD > 15%
- [ ] CVaR computed correctly (validated against manual calculation)
- [ ] Correlation spike detected and logged
- [ ] Emergency close procedure documented and tested (but never auto-executed without human confirmation)

**Risk Assessment**
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Gate blocks all picks during normal correction | Medium | High | Escalation levels; only block at MDD > 15% |
| CVaR calculation uses insufficient history | Low | High | Require 100 days minimum; fallback to simpler VaR |
| Emergency close (level 3) triggers accidentally | Very Low | Critical | Level 3 requires two-person approval; auto-alert only |

**Rollback Plan**
```python
# Remove G7 from quality gates sequence
# Set tail_risk monitoring to advisory mode (log only)
# Verification: Tail-risk conditions logged but picks not blocked
```

---

### PR-I4: Per-Symbol Autopsy Workflow

| Field | Detail |
|-------|--------|
| **Branch** | `infra/I4-symbol-autopsy-20260518` |
| **Files Changed** | `traceability/symbol_autopsy.py`, `audit_dashboard/autopsy.html`, `tests/test_symbol_autopsy.py` |
| **Est. Effort** | M (2-3 days) |
| **Depends On** | PR-T1 (lifecycle logger provides pick history) |

**Problem Statement**
When a symbol consistently underperforms, there is no systematic process to diagnose why. Currently, underperforming symbols are simply removed (PR-Q2) without understanding root cause. An autopsy process would help identify whether the issue is: signal quality, slippage, regime mismatch, or data quality.

**Solution Description**
Implement automated per-symbol autopsy that triggers when a symbol's 30-day rolling WR drops below 40% or PF drops below 1.0. The autopsy produces a structured report covering: signal accuracy, fill quality, slippage analysis, regime distribution, and recommendation.

**Code Changes**
```python
# traceability/symbol_autopsy.py
class SymbolAutopsy:
    """Automated autopsy for underperforming symbols."""
    
    TRIGGER_WR_THRESHOLD = 40.0  # 30-day rolling WR %
    TRIGGER_PF_THRESHOLD = 1.0
    
    def __init__(self):
        self.logger = PickLifecycleLogger()
        self.slippage_model = SlippageModel()
    
    def run_autopsy(self, symbol: str, asset_class: str, days: int = 30) -> dict:
        """Run full autopsy on a symbol."""
        
        picks = self._get_symbol_picks(symbol, asset_class, days)
        
        if len(picks) < 5:
            return {'error': 'Insufficient sample size (<5 picks)'}
        
        wr = (picks['pnl_usd'] > 0).mean() * 100
        wins = picks[picks['pnl_usd'] > 0]
        losses = picks[picks['pnl_usd'] <= 0]
        pf = abs(wins['pnl_usd'].sum()) / abs(losses['pnl_usd'].sum()) if len(losses) > 0 else float('inf')
        
        report = {
            'autopsy_id': f"autopsy_{symbol}_{datetime.utcnow().strftime('%Y%m%d')}",
            'symbol': symbol,
            'asset_class': asset_class,
            'period_days': days,
            'n_picks': len(picks),
            'win_rate': wr,
            'profit_factor': pf,
            'total_pnl': float(picks['pnl_usd'].sum()),
            'diagnosis': self._diagnose(picks, symbol, asset_class),
            'recommendation': self._recommend(picks, wr, pf),
            'confidence': self._assess_confidence(len(picks))
        }
        
        return report
    
    def _diagnose(self, picks: pd.DataFrame, symbol: str, asset_class: str) -> dict:
        """Diagnose root cause of underperformance."""
        
        diagnosis = {}
        
        # 1. Signal accuracy
        signal_accuracy = self._check_signal_accuracy(picks)
        diagnosis['signal_accuracy'] = signal_accuracy
        
        # 2. Fill quality / slippage
        slippage_analysis = self._check_slippage(picks, symbol)
        diagnosis['slippage'] = slippage_analysis
        
        # 3. Regime distribution
        regime_dist = picks['regime'].value_counts().to_dict() if 'regime' in picks.columns else {}
        diagnosis['regime_distribution'] = regime_dist
        
        # 4. Timing analysis
        timing = self._check_timing(picks)
        diagnosis['timing'] = timing
        
        # Overall diagnosis
        issues = []
        if signal_accuracy.get('directional_accuracy', 100) < 50:
            issues.append("Signal model has lost directional edge")
        if slippage_analysis.get('avg_slippage_bps', 0) > self._get_expected_slippage(asset_class) * 2:
            issues.append("Excessive slippage — possible liquidity degradation")
        if timing.get('avg_holding_hours', 0) < 1:
            issues.append("Extremely short holds — possible stop-run pattern")
        
        diagnosis['primary_issues'] = issues if issues else ["No single clear cause; review full report"]
        
        return diagnosis
    
    def _check_signal_accuracy(self, picks: pd.DataFrame) -> dict:
        """Check if signals are directionally correct."""
        if 'predicted_direction' not in picks.columns or 'actual_direction' not in picks.columns:
            return {'directional_accuracy': None, 'note': 'Direction data not available'}
        
        correct = (picks['predicted_direction'] == picks['actual_direction']).sum()
        total = len(picks)
        
        return {
            'directional_accuracy': (correct / total * 100) if total > 0 else 0,
            'correct_calls': int(correct),
            'total_calls': int(total)
        }
    
    def _check_slippage(self, picks: pd.DataFrame, symbol: str) -> dict:
        """Analyze slippage patterns."""
        if 'slippage_bps' not in picks.columns:
            return {'avg_slippage_bps': None, 'note': 'Slippage data not available'}
        
        avg_slip = picks['slippage_bps'].mean()
        max_slip = picks['slippage_bps'].max()
        
        return {
            'avg_slippage_bps': float(avg_slip) if not pd.isna(avg_slip) else None,
            'max_slippage_bps': float(max_slip) if not pd.isna(max_slip) else None,
            'slippage_vs_expected': f"{avg_slip / self.slippage_model.estimate_slippage(symbol, picks.iloc[0]['asset_class'], 1000, 'LONG'):.1f}x" if len(picks) > 0 else 'N/A'
        }
    
    def _check_timing(self, picks: pd.DataFrame) -> dict:
        """Analyze trade timing patterns."""
        if 'holding_hours' not in picks.columns:
            return {'avg_holding_hours': None}
        
        return {
            'avg_holding_hours': float(picks['holding_hours'].mean()),
            'median_holding_hours': float(picks['holding_hours'].median()),
            'min_holding_hours': float(picks['holding_hours'].min()),
            'max_holding_hours': float(picks['holding_hours'].max())
        }
    
    def _recommend(self, picks: pd.DataFrame, wr: float, pf: float) -> str:
        """Generate recommendation based on autopsy findings."""
        if wr < 30 and pf < 0.8:
            return "REMOVE — consistently unprofitable, no recoverable edge"
        elif wr < 40 and pf < 1.0:
            return "REDUCE_SIZE — reduce position size by 50%, re-evaluate in 30 days"
        elif wr >= 40 and wr < 50:
            return "INVESTIGATE — marginal performance, check for regime-specific edge"
        else:
            return "MAINTAIN — within acceptable performance range"
    
    def _assess_confidence(self, n_picks: int) -> str:
        """Assess confidence in autopsy conclusion."""
        if n_picks >= 30:
            return "HIGH"
        elif n_picks >= 15:
            return "MEDIUM"
        elif n_picks >= 5:
            return "LOW"
        return "INSUFFICIENT"
    
    def _get_expected_slippage(self, asset_class: str) -> float:
        """Get expected slippage for asset class."""
        defaults = {'CRYPTO': 8, 'COMMODITY': 5, 'ETF': 2, 'EQUITY': 3, 'FOREX': 3, 'BOND': 4, 'FUTURES': 5}
        return defaults.get(asset_class, 5)
    
    def run_batch_autopsy(self, asset_class: str, days: int = 30) -> pd.DataFrame:
        """Run autopsy on all underperforming symbols in an asset class."""
        underperformers = self._find_underperformers(asset_class, days)
        
        reports = []
        for symbol in underperformers:
            report = self.run_autopsy(symbol, asset_class, days)
            if 'error' not in report:
                reports.append(report)
        
        return pd.DataFrame(reports)
    
    def _find_underperformers(self, asset_class: str, days: int) -> list[str]:
        """Find symbols with WR < threshold or PF < threshold."""
        query = """
            SELECT symbol,
                   AVG(CASE WHEN pnl_usd > 0 THEN 1 ELSE 0 END) * 100 as wr,
                   ABS(SUM(CASE WHEN pnl_usd > 0 THEN pnl_usd ELSE 0 END)) / 
                       NULLIF(ABS(SUM(CASE WHEN pnl_usd < 0 THEN pnl_usd ELSE 0 END)), 0) as pf
            FROM picks
            WHERE asset_class = %s
            AND entry_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
            AND status = 'CLOSED'
            GROUP BY symbol
            HAVING wr < %s OR pf < %s
        """
        df = pd.read_sql(self.logger.db, query, 
                        params=(asset_class, days, self.TRIGGER_WR_THRESHOLD, self.TRIGGER_PF_THRESHOLD))
        return df['symbol'].tolist()
```

**Test Plan**
1. `test_autopsy_underperformer()`: Symbol with WR=30%, PF=0.7 → recommendation = REMOVE
2. `test_autopsy_marginal()`: Symbol with WR=45%, PF=1.1 → recommendation = INVESTIGATE
3. `test_insufficient_data()`: Symbol with 3 picks → error
4. `test_batch_autopsy()`: 5 underperformers in CRYPTO → 5 reports generated
5. `test_diagnosis_slippage()`: High slippage flagged as primary issue

**Acceptance Criteria**
- [ ] Autopsy triggers automatically for symbols with 30-day WR < 40%
- [ ] Report includes: signal accuracy, slippage, regime distribution, timing
- [ ] Recommendation is one of: REMOVE, REDUCE_SIZE, INVESTIGATE, MAINTAIN
- [ ] Batch autopsy can process entire asset class in < 10 seconds
- [ ] Results displayed in audit dashboard

**Risk Assessment**
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Autopsy triggers on false underperformance (small sample) | Medium | Medium | Minimum 5 picks; confidence rating in report |
| REMOVE recommendation acted on too quickly | Medium | High | Auto-REQUIRE manual review for REMOVE decisions |

**Rollback Plan**
```python
# Disable autopsy triggers in config
# Keep reporting capability for manual use
```

---

### PR-I5: ConcentrationChecker Full Wire (Symbol + Strategy + Regime)

| Field | Detail |
|-------|--------|
| **Branch** | `infra/I5-concentration-checker-full-20260518` |
| **Files Changed** | `concentration_checker.py`, `quality_gates.py`, `config/concentration_limits.yaml`, `tests/test_full_concentration.py` |
| **Est. Effort** | L (4-5 days) |
| **Depends On** | PR-O2 (COMMODITY symbol concentration), PR-I1 (position sizing data) |

**Problem Statement**
`ConcentrationChecker` currently only checks symbol-level concentration (PR-O2). There is no checking for: (1) strategy concentration (one strategy dominating), (2) regime concentration (all picks in same regime), (3) directional concentration (all LONG or all SHORT), (4) correlation concentration (all picks in correlated assets).

**Solution Description**
Extend ConcentrationChecker to cover all four dimensions: symbol, strategy, regime, and direction. Each dimension has configurable limits. Implement correlation concentration using a covariance matrix threshold.

**Code Changes**
```python
# concentration_checker.py
class ConcentrationChecker:
    """Full concentration checking across multiple dimensions."""
    
    def __init__(self):
        self.limits = self._load_limits()
        self.mode = 'HARD'
        self.db = production_db_conn()
    
    def check_all_dimensions(self, pick: Pick, portfolio: Portfolio) -> list[GateResult]:
        """Run concentration checks across all dimensions."""
        results = []
        
        # 1. Symbol concentration (from PR-O2)
        results.append(self.check_symbol_concentration(pick))
        
        # 2. Strategy concentration (NEW)
        results.append(self.check_strategy_concentration(pick, portfolio))
        
        # 3. Regime concentration (NEW)
        results.append(self.check_regime_concentration(pick, portfolio))
        
        # 4. Directional concentration (NEW)
        results.append(self.check_directional_concentration(pick, portfolio))
        
        return results
    
    def check_strategy_concentration(self, pick: Pick, portfolio: Portfolio) -> GateResult:
        """Check if adding this pick would over-concentrate in one strategy."""
        asset_class = pick.asset_class
        strategy = pick.strategy
        
        limit = self.limits.get(asset_class, {}).get('strategy_max_pct', 50)
        
        recent_picks = self._get_recent_picks(asset_class, days=30)
        strategy_count = sum(1 for p in recent_picks if p.strategy == strategy)
        total = len(recent_picks)
        
        if total == 0:
            return GateResult(passed=True, gate='CONC-STRATEGY')
        
        projected_pct = ((strategy_count + 1) / (total + 1)) * 100
        
        if projected_pct > limit:
            return GateResult(
                passed=False,
                gate='CONC-STRATEGY',
                reason=f"Strategy {strategy} would be {projected_pct:.1f}% of {asset_class} picks (limit: {limit}%)",
                severity='HARD',
                metadata={'strategy': strategy, 'projected_pct': projected_pct, 'limit_pct': limit}
            )
        
        return GateResult(passed=True, gate='CONC-STRATEGY')
    
    def check_regime_concentration(self, pick: Pick, portfolio: Portfolio) -> GateResult:
        """Check if adding this pick would over-concentrate in one regime."""
        asset_class = pick.asset_class
        regime = pick.metadata.get('regime', 'UNKNOWN')
        
        limit = self.limits.get(asset_class, {}).get('regime_max_pct', 60)
        
        recent_picks = self._get_recent_picks(asset_class, days=30)
        regime_count = sum(1 for p in recent_picks 
                          if p.metadata.get('regime', 'UNKNOWN') == regime)
        total = len(recent_picks)
        
        if total == 0:
            return GateResult(passed=True, gate='CONC-REGIME')
        
        projected_pct = ((regime_count + 1) / (total + 1)) * 100
        
        if projected_pct > limit:
            return GateResult(
                passed=False,
                gate='CONC-REGIME',
                reason=f"Regime {regime} would be {projected_pct:.1f}% of {asset_class} picks (limit: {limit}%)",
                severity='WARNING',  # regime concentration is softer than symbol
                metadata={'regime': regime, 'projected_pct': projected_pct, 'limit_pct': limit}
            )
        
        return GateResult(passed=True, gate='CONC-REGIME')
    
    def check_directional_concentration(self, pick: Pick, portfolio: Portfolio) -> GateResult:
        """Check if portfolio is overly directional (all LONG or all SHORT)."""
        asset_class = pick.asset_class
        direction = pick.direction
        
        # Count open positions by direction
        open_positions = portfolio.get_open_positions(asset_class=asset_class)
        
        if len(open_positions) < 3:
            return GateResult(passed=True, gate='CONC-DIRECTION')
        
        same_direction = sum(1 for p in open_positions if p.direction == direction)
        total_open = len(open_positions)
        
        directional_pct = (same_direction / total_open) * 100
        
        if directional_pct > 80:
            return GateResult(
                passed=False,
                gate='CONC-DIRECTION',
                reason=f"{directional_pct:.0f}% of open {asset_class} positions are {direction} (limit: 80%)",
                severity='WARNING',
                metadata={
                    'direction': direction,
                    'directional_pct': directional_pct,
                    'total_open': total_open,
                    'same_direction': same_direction
                }
            )
        
        return GateResult(passed=True, gate='CONC-DIRECTION')
```

**Test Plan**
1. `test_strategy_concentration_blocks()`: 51% of picks from one strategy → 52nd blocked
2. `test_regime_concentration_warns()`: 61% of picks in one regime → WARNING (not HARD)
3. `test_directional_concentration()`: 85% of open positions are LONG → new LONG blocked
4. `test_multiple_dimensions()`: Pick breaches symbol + strategy limits → both reported
5. `test_small_portfolio_exempt()`: <3 open positions → directional check passes

**Acceptance Criteria**
- [ ] No single strategy exceeds 50% of picks per asset class (rolling 30-day)
- [ ] No single regime exceeds 60% of picks per asset class
- [ ] Portfolio never exceeds 80% directional concentration
- [ ] All four dimensions reported in audit dashboard

**Risk Assessment**
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Multi-dimensional checks add significant latency | Medium | High | Parallel execution; cache recent counts |
| Strategy concentration blocks dominant strategy unfairly | Low | Medium | Dominant strategy review process; can request limit increase |

**Rollback Plan**
```python
# Set ConcentrationChecker.mode = 'WARNING' for strategy/regime/direction
# Keep symbol concentration at HARD (from PR-O2)
# Verification: Symbol caps enforced; other dimensions warn only
```

---

## Section 9: PR Dependency Graph

### Dependency Visualization

```
Week 1: Parallel Track A          Parallel Track B          Parallel Track C
├── PR-C1 (Investigate quan)      ├── PR-C2 (Investigate rapid)  ├── PR-T1 (Lifecycle logger)
├── PR-O1 (COT lag)               ├── PR-O4 (Symbol expansion)   ├── PR-T3 (Universe manager)
├── PR-E1 (VIX gate)              ├── PR-E2 (GHA path fix)       └── PR-Q1 (Ghost row purge)
├── PR-B2 (FRED API)              └── PR-F1 (FOREX backtest)
└── PR-I1 (Post-cost gate)

Week 2: Sequentials               Dependents
├── PR-C3 (Block quan)     ←── PR-C1
├── PR-C4 (Block rapid)    ←── PR-C2
├── PR-O3 (Carry-momo)     ←── PR-O1
├── PR-O2 (Concentration)  ←── PR-O4
├── PR-E3 (Dual momentum)  ←── PR-E1
├── PR-Q2 (Symbol cleanup) ←── PR-Q1
├── PR-Q3 (PEAD)           ←── PR-Q1, PR-Q2
├── PR-B1 (TSMOM)          ←── PR-B2
├── PR-T2 (Traceback)      ←── PR-T1
├── PR-T4 (Simulator)      ←── PR-T1, PR-T2
├── PR-I2 (Slippage)       ←── PR-I1
├── PR-I4 (Autopsy)        ←── PR-T1
└── PR-I5 (Full conc)      ←── PR-O2, PR-I1

Week 3+: Independent Deployments
├── PR-C5 (Model wire-up)  ←── PR-C3, PR-C4
├── PR-C6 (M-034 gate)     ←── PR-C5
├── PR-Q4 (DOW tilt)       ←── PR-Q3
├── PR-F2 (Non-JPY gate)   ←── PR-F1
├── PR-I3 (Tail-risk)      ←── PR-I2
└── PR-T2 (Traceback)      ←── PR-T1
```

### Detailed Dependency Matrix

| PR | Depends On | Blocks | Effort | Track |
|----|-----------|--------|--------|-------|
| PR-C1 | None | PR-C3 | M | CRYPTO |
| PR-C2 | None | PR-C4 | M | CRYPTO |
| PR-C3 | PR-C1 | None | S | CRYPTO |
| PR-C4 | PR-C2 | None | S | CRYPTO |
| PR-C5 | PR-C3, PR-C4 | PR-C6 | L | CRYPTO |
| PR-C6 | PR-C5 | None | S | CRYPTO |
| PR-O1 | None | PR-O3 | M | COMMODITY |
| PR-O2 | PR-O4 | PR-I5 | M | COMMODITY |
| PR-O3 | PR-O1 | None | L | COMMODITY |
| PR-O4 | None | PR-O2 | M | COMMODITY |
| PR-E1 | None | PR-E3 | S | ETF |
| PR-E2 | None | None | S | ETF |
| PR-E3 | PR-E1 | None | L | ETF |
| PR-Q1 | None | PR-Q2, PR-Q3 | M | EQUITY |
| PR-Q2 | PR-Q1 | None | S | EQUITY |
| PR-Q3 | PR-Q1, PR-Q2 | PR-Q4 | L | EQUITY |
| PR-Q4 | PR-Q3 | None | S | EQUITY |
| PR-F1 | None | PR-F2 | L | FOREX |
| PR-F2 | PR-F1 | None | S | FOREX |
| PR-B1 | PR-B2 | None | L | BOND |
| PR-B2 | None | PR-B1 | M | BOND |
| PR-T1 | None | PR-T2, PR-T4, PR-I4 | L | TRACEABILITY |
| PR-T2 | PR-T1 | PR-T4 | M | TRACEABILITY |
| PR-T3 | None | None | M | TRACEABILITY |
| PR-T4 | PR-T1, PR-T2 | None | L | TRACEABILITY |
| PR-I1 | None | PR-I2, PR-I5 | M | INFRA |
| PR-I2 | PR-I1 | PR-I3 | L | INFRA |
| PR-I3 | PR-I2 | None | L | INFRA |
| PR-I4 | PR-T1 | None | M | INFRA |
| PR-I5 | PR-O2, PR-I1 | None | L | INFRA |

### Parallel Execution Groups

**Group A (Week 1 — No Dependencies):**
- PR-C1, PR-C2, PR-O1, PR-O4, PR-E1, PR-E2, PR-F1, PR-B2, PR-T1, PR-T3, PR-I1, PR-Q1

**Group B (Week 2 — Depends on Group A):**
- PR-C3, PR-C4, PR-O2, PR-O3, PR-E3, PR-Q2, PR-Q3, PR-B1, PR-T2, PR-I2, PR-I4

**Group C (Week 3-4 — Depends on Group B):**
- PR-C5, PR-C6, PR-Q4, PR-F2, PR-T4, PR-I3, PR-I5

### Effort Summary

| Effort | Count | PRs |
|--------|-------|-----|
| S (1-2 days) | 10 | PR-C3, PR-C4, PR-C6, PR-E1, PR-E2, PR-F2, PR-Q2, PR-Q4 |
| M (2-3 days) | 13 | PR-C1, PR-C2, PR-O1, PR-O2, PR-O4, PR-B2, PR-Q1, PR-T2, PR-T3, PR-I1, PR-I4 |
| L (4-5 days) | 14 | PR-C5, PR-O3, PR-E3, PR-F1, PR-Q3, PR-B1, PR-T1, PR-T4, PR-I2, PR-I3, PR-I5 |

**Total Estimated Effort: ~105 engineer-days** (37 PRs × average 2.8 days)

---

## Section 10: Execution Schedule

### Week 1: May 18-24 (Foundation & Investigation)

**Theme:** Deploy foundational infrastructure, run investigations, wire existing features.

| Day | PRs | Owner | Deliverable |
|-----|-----|-------|-------------|
| Mon 5/18 | PR-T1 (Lifecycle logger), PR-C1 (quan_engine investigation), PR-Q1 (Ghost row purge — PA) | Platform/Quant | Logger deployed; Investigation started; PA purge scheduled |
| Tue 5/19 | PR-T1 completion, PR-C2 (rapid_fire investigation), PR-O1 (COT lag) | Quant | COT lag fix deployed to staging |
| Wed 5/20 | PR-O4 (Symbol expansion), PR-E1 (VIX gate), PR-B2 (FRED API) | Quant/Data | 3 new commodity symbols validated; VIX gate wired |
| Thu 5/21 | PR-I1 (Post-cost gate), PR-T3 (Universe manager), PR-F1 (FOREX backtest start) | Platform/Quant | Post-cost gate promotion; FRED API live |
| Fri 5/22 | PR-E2 (GHA path), PR-O3 (Carry-momo wire-up), PR-E3 (Dual momentum start) | Quant | Carry-momo in shadow; GHA path fixed |

**Week 1 Exit Criteria:**
- [ ] PR-T1 lifecycle logger receiving events in production
- [ ] PR-C1 and PR-C2 investigations running (data collection)
- [ ] PR-O1 COT lag correction in staging
- [ ] PR-E1 VIX gate active for ETF
- [ ] PR-B2 FRED API integrated
- [ ] PR-I1 post-cost gate promoting to HARD

---

### Week 2: May 25-31 (Blocking, Wire-Up & Backtests)

**Theme:** Block unprofitable strategies, wire new strategies, complete backtests.

| Day | PRs | Owner | Deliverable |
|-----|-----|-------|-------------|
| Mon 5/25 | PR-C3 (Block quan — if NO-GO), PR-C4 (Block rapid — if NO-GO), PR-Q2 (Symbol cleanup) | Quant | Unprofitable CRYPTO strategies blocked; Meme tickers removed |
| Tue 5/26 | PR-O3 completion (carry-momo shadow→production), PR-T2 (Traceback engine) | Quant | COMMODITY carry-momo live; Traceback engine active |
| Wed 5/27 | PR-Q3 (PEAD backtest + wire), PR-I2 (Slippage model) | Quant | PEAD strategy backtested; Slippage model training |
| Thu 5/28 | PR-E3 completion (dual momentum), PR-B1 (TSMOM wire-up), PR-O2 (Concentration cap) | Quant | ETF dual momentum live; BOND TSMOM in shadow |
| Fri 5/29 | PR-T4 (Simulator), PR-I4 (Autopsy), PR-F1 completion (FOREX backtest) | Quant/Platform | Simulator available; Autopsy workflow active; FOREX backtest report |

**Week 2 Exit Criteria:**
- [ ] PR-C3, PR-C4 blockers deployed (if investigations confirm NO-GO)
- [ ] PR-O3 carry-momo producing production picks
- [ ] PR-Q3 PEAD wired and backtested
- [ ] PR-E3 dual momentum active for ETF
- [ ] PR-B1 TSMOM collecting shadow data
- [ ] PR-T4 simulator available for what-if analysis

---

### Week 3: June 1-7 (Promotion, Gates & Advanced Features)

**Theme:** Promote shadow strategies, enable advanced gates, FOREX conditional enable.

| Day | PRs | Owner | Deliverable |
|-----|-----|-------|-------------|
| Mon 6/1 | PR-C5 (Model wire-up shadow→production), PR-F2 (Non-JPY re-enable gate) | Quant/ML | CRYPTO model contributing to composite scores |
| Tue 6/2 | PR-C6 (M-034 gate enable), PR-Q4 (DOW tilt) | Quant | M-034 inversion active; DOW tilt for EQUITY |
| Wed 6/3 | PR-I3 (Tail-risk gate), PR-I5 (Full concentration) | Platform | Tail-risk gate active; All concentration dimensions checked |
| Thu 6/4 | PR-B1 promotion (shadow→production if data looks good) | Quant | BOND TSMOM potentially live |
| Fri 6/5 | PR review & calibration: Review all gate performance from Week 1-2 | All | Gate calibration adjustments; Weekly autopsy review |

**Week 3 Exit Criteria:**
- [ ] PR-C5 per-class model contributing to production scores
- [ ] PR-C6 M-034 gate active for CRYPTO
- [ ] PR-F2 non-JPY FOREX conditionally enabled (if stats allow)
- [ ] PR-I3 tail-risk gate protecting portfolio
- [ ] PR-I5 full concentration checking across all dimensions

---

### Week 4: June 8-14 (Stabilization, Measurement & Reporting)

**Theme:** Stabilize, measure impact, produce final assessment.

| Day | Activity | Owner | Deliverable |
|-----|----------|-------|-------------|
| Mon 6/8 | Performance measurement: Compute pre/post metrics for all asset classes | Quant | Baseline vs. current comparison report |
| Tue 6/9 | Gate calibration: Use PR-T4 simulator + PR-T2 traceback to tune gates | Quant | Gate threshold adjustments (if any) |
| Wed 6/10 | Stress test: Simulate March 2026 crash scenario with new gates | Quant | Stress test report; verify tail-risk gate would have triggered |
| Thu 6/11 | Documentation: Update all runbooks, document new procedures | Platform | Updated runbooks; Onboarding docs for new strategies |
| Fri 6/12 | Final review: Present results to stakeholders, plan next sprint | All | Sprint retrospective; Next 4-week plan |

**Week 4 Exit Criteria:**
- [ ] All asset classes have measurable improvement vs. 2026-05-17 baseline
- [ ] CRYPTO: PF trend toward 3.0+ (from 2.54)
- [ ] COMMODITY: PF ≥ 2.5 (from 2.15), n ≥ 100
- [ ] ETF: PF ≥ 2.5 (from 2.25), n ≥ 100
- [ ] EQUITY: n ≥ 75 (from 31), WR trend visible
- [ ] FOREX: Research phase complete, re-enable gate active
- [ ] BOND: n ≥ 30 (from 1), TSMOM tracking

---

### Risk Schedule Adjustments

| Risk | Impact | Mitigation | Schedule Buffer |
|------|--------|------------|----------------|
| PR-C1/C2 investigations take longer than expected | CRYPTO optimization delayed | Run in parallel with other work; use preliminary findings | +3 days |
| FRED API integration issues | BOND strategy blocked | Use cached macro data; manual data entry fallback | +2 days |
| Slippage model training insufficient data | G5 uses defaults longer | Extend shadow period; conservative defaults | +5 days |
| PEAD backtest shows PF < 2.0 | EQUITY strategy blocked | Investigate sub-periods; parameter tuning | +3 days |

---

## Appendix A: Asset Class State Transitions

| Asset Class | Current State | Target State | Key PRs | Exit Criteria |
|-------------|--------------|--------------|---------|---------------|
| CRYPTO | MONEY_READY | OPTIMIZED | PR-C1 through PR-C6 | PF ≥ 3.5, WR ≥ 68%, n ≥ 1000 |
| COMMODITY | WATCH | MONEY_READY | PR-O1 through PR-O4 | PF ≥ 2.5, WR ≥ 65%, n ≥ 100 |
| ETF | WATCH | MONEY_READY | PR-E1 through PR-E3 | PF ≥ 2.5, WR ≥ 65%, n ≥ 100 |
| EQUITY | INSUFFICIENT_DATA | WATCH | PR-Q1 through PR-Q4 | n ≥ 75, WR trend visible |
| FOREX | NOT_READY | RESEARCH | PR-F1, PR-F2 | PF ≥ 1.0 trending, n ≥ 30 non-JPY |
| BOND | INSUFFICIENT_DATA | ACCUMULATE | PR-B1, PR-B2 | n ≥ 30, TSMOM tracking |

## Appendix B: PR Summary Table

| PR | Title | Effort | Track | Dependencies |
|----|-------|--------|-------|-------------|
| C1 | STRATEGY_INVESTIGATION quan_engine | M | CRYPTO | None |
| C2 | STRATEGY_INVESTIGATION rapid_fire | M | CRYPTO | None |
| C3 | Block quan_engine CRYPTO | S | CRYPTO | C1 |
| C4 | Block rapid_fire CRYPTO | S | CRYPTO | C2 |
| C5 | per_class_trainer wire-up | L | CRYPTO | C3, C4 |
| C6 | M-034 CONF_INVERSION_GATE | S | CRYPTO | C5 |
| O1 | COT lag correction | M | COMMODITY | None |
| O2 | Concentration cap CT=F | M | COMMODITY | O4 |
| O3 | commodity_carry_momo wire-up | L | COMMODITY | O1 |
| O4 | Symbol expansion HE=F/ZW=F/KC=F | M | COMMODITY | None |
| E1 | VIX<25 gate wire | S | ETF | None |
| E2 | GHA path registry fix | S | ETF | None |
| E3 | Sector dual momentum GEM | L | ETF | E1 |
| Q1 | MySQL ghost-row purge | M | EQUITY | None (PA) |
| Q2 | Speculative ticker removal | S | EQUITY | Q1 |
| Q3 | PEAD strategy backtest + wire | L | EQUITY | Q1, Q2 |
| Q4 | DOW tilt gate enable | S | EQUITY | Q3 |
| F1 | forex_carry.py backtest | L | FOREX | None |
| F2 | Non-JPY SHORT re-enable | S | FOREX | F1 |
| B1 | UST TSMOM wire-up | L | BOND | B2 |
| B2 | FRED_API_KEY integration | M | BOND | None |
| T1 | pick_lifecycle_logger + DB | L | TRACEABILITY | None |
| T2 | filter_traceback_engine | M | TRACEABILITY | T1 |
| T3 | symbol_universe_manager | M | TRACEABILITY | None |
| T4 | what_if_simulator | L | TRACEABILITY | T1, T2 |
| I1 | Post-cost expectancy hard gate | M | INFRA | None |
| I2 | Slippage model wire-up | L | INFRA | I1 |
| I3 | MDD/CVaR tail-risk gate | L | INFRA | I2 |
| I4 | Per-symbol autopsy workflow | M | INFRA | T1 |
| I5 | ConcentrationChecker full wire | L | INFRA | O2, I1 |

---

## Document Control

| Field | Value |
|-------|-------|
| **Document** | PR_PLAN_2026-05-18.md |
| **Version** | 1.0 |
| **Author** | Quant Engineering Lead |
| **Date** | 2026-05-18 |
| **Status** | FINAL |
| **Review Date** | 2026-05-25 (Week 1 checkpoint) |
| **Next Update** | 2026-06-01 (Week 3 plan) |

---

*End of PR Plan 2026-05-18*
