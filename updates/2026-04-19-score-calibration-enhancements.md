# Score Calibration & System Isolation Enhancements

**Date:** 2026-04-19  
**Status:** Proposal (Ready for Implementation)  
**Priority:** Critical  
**Scope:** audit_trail, alpha_engine, audit_dashboard  

---

## Executive Summary

A comprehensive audit of 3,500 recent closed picks on `/audit` revealed **systemic score calibration failure**: high-score picks (p80) return -0.742% average PnL vs low-score picks (p20) -0.431%, demonstrating **global inversion**. Root cause: single subsystem (`copy_trader_intel/copy_hl_lb_None`) dominates 143 of 395 high-score losers (-1621.3% cumulative), poisoning global score statistics.

**Key Finding:** Removing `copy_trader_intel` flips score lift from -0.312% (inverted) to +0.696% (positive), proving the distortion is 100% localized but highly concentrated.

**Proposed Enhancements:**
1. **Per-system score calibration** — prevent single pathological system from poisoning global metrics
2. **Loss driver analyzer integration** — autopsy underperforming strategies before hard-blocking
3. **Score architecture split** — separate classification quality (confidence, elite_score) from payoff quality (trust_score)
4. **Dashboard mismatch detection** — flag and monitor low-score winners (+720% total) and high-score losers (-1911.6% total)
5. **Exit-reason stratification** — understand whether losses are SL-driven vs timing/size-driven

---

## Background: The Problem

### 1. Global Score Inversion

Across all 3,500 recent closed picks:

| Score Field | p20 Avg | p80 Avg | Lift | Status |
|---|---|---|---|---|
| **Score** | -0.431% | -0.742% | -0.311% | ❌ **Inverted** |
| **Confidence** | +0.247% | -0.641% | -0.888% | ❌ **Worst** |
| **Elite_score** | -0.055% | -0.866% | -0.811% | ❌ **Inverted** |
| **Method_a_score** | -0.212% | -0.463% | -0.251% | ❌ **Inverted** |
| **Trust_score** | -0.749% | +0.279% | +1.028% | ✅ **Only Correct** |
| **ML_composite** | -0.140% | -0.744% | -0.604% | ❌ **Inverted** |

**Interpretation:**
- Score fields are measuring **classification quality** (separation of winners/losers), not **payoff quality** (tail severity)
- High-score losers dominate the dataset: 395 picks with 47.1% of all loss mass
- Low-score winners are being suppressed: 308 picks generating +720% total (+2.34% avg), 24% of all profit

### 2. The Copy_Trader_Intel Pathology

Of 395 high-score/low-PnL picks:

| System | Count | Total PnL | Avg PnL | % of Losses |
|---|---|---|---|---|
| **copy_trader_intel + copy_hl_lb_None** | 143 | -1,621.3% | -11.34% | **85%** |
| alpha_engine | 137 | -155.6% | -1.14% | 8% |
| stocks_competition | 39 | -77.4% | -1.98% | 4% |
| other | 76 | -57.3% | -0.75% | 3% |

**Validation:** Exclusion test confirms copy_trader_intel is **sole cause of global distortion**:
- With copy_trader_intel: high-score avg = -0.744% (negative)
- Without copy_trader_intel: high-score avg = +0.336% (positive)
- **Global lift flips from -0.312% to +0.696%** (+1.008pp)

### 3. Per-System Calibration Variance

When analyzed per system (n ≥ 100):

| System | n | Low-Score Avg | High-Score Avg | Lift | Status |
|---|---|---|---|---|
| kimi_riseoftheclaw | 280 | +0.215% | +1.714% | +1.498% | ✅ **Only Positive** |
| copy_trader_intel | 233 | -3.825% | -3.295% | +0.530% | ⚠️ Barely positive, deep losses |
| alpha_engine | 181 | -0.354% | -0.678% | -0.324% | ❌ Inverted |
| baby_strategies | 127 | +0.106% | -0.412% | -0.518% | ❌ Inverted |

**Implication:** kimi_riseoftheclaw has correct calibration (+1.498% lift), but it's being drowned out by copy_trader_intel's -3.825% low-score baseline. Global metrics are meaningless without per-system accounting.

### 4. Correlation Analysis

Spearman correlation of score fields with realized PnL:

| Metric | Spearman | Pearson | Status |
|---|---|---|---|
| trust_score | +0.279 | +0.311 | ✅ Best |
| elite_score | +0.410 | +0.315 | ✓ Good (misleading name) |
| method_a_score | +0.163 | +0.175 | ⚠️ Weak |
| confidence | +0.123 | +0.166 | ⚠️ Weak (inverse polarity) |
| consensus_pct | +0.032 | -0.019 | ❌ Near zero |

**Finding:** Correlation with PnL does NOT match intended semantics. `elite_score` (meant for classification) correlates better than `trust_score` (meant for risk), but both are weak at Spearman +0.28–0.41.

### 5. Asset-Class Risk Stratification

High-score loss rate by asset class:

| Asset | n | Loss Rate | Example Systems |
|---|---|---|---|
| Commodity | 28 | 100% | Copy-trader on FX pairs |
| Crypto | 156 | 86.4% | Copy-trader high-score dominance |
| Forex | 81 | 44.2% | kimi_signal_tracking on JPY pairs |
| Equity | 130 | 29.7% | stocks_competition shallow losses |

**Implication:** Crypto and FX are asset-class risk zones due to copy_trader_intel concentrate.

---

## Proposed Enhancements

### Enhancement 1: Per-System Score Bucketization (audit_trail/score_calibration.py)

**Current State:** All picks scored on global scale; copy_trader_intel's -3.825% baseline poisons the entire distribution.

**Proposed Solution:** Score bucketization via per-system linear adjustment:
- Compute p20/p80 stats per system (n ≥ 50)
- Invert polarity if p80_avg < p20_avg (detect inverted systems like copy_trader_intel)
- Apply min/max clamping: if a system is fundamentally broken (n ≥ 50, WR < 30%, avg < -1%), flag as `_suspect_system_calibration`
- Gate active picks from suspect systems until manual review

**Implementation:**
```python
# audit_trail/score_calibration.py (new module)

def compute_per_system_calibration(closed_picks: List[dict]) -> dict:
    """
    Computes p20/p80 calibration per system.
    Returns: {system: {score_field: {p20, p80, lift, polarity_ok, suspect}}}
    """
    by_system = defaultdict(list)
    for pick in closed_picks:
        by_system[pick['system']].append(pick)
    
    calibration = {}
    for system, picks in by_system.items():
        if len(picks) < 50:
            continue  # Skip small-n systems
        
        scores_by_field = {}
        for field in ['score', 'confidence', 'elite_score', 'trust_score']:
            values = [p.get(field, 0) for p in picks if field in p]
            if not values:
                continue
            
            p20 = percentile(values, 20)
            p80 = percentile(values, 80)
            pnls = [p['pnl_pct'] for p in picks if field in p]
            
            p20_picks = [p for p, v in zip(picks, values) if v <= p20]
            p80_picks = [p for p, v in zip(picks, values) if v >= p80]
            
            p20_avg_pnl = mean([p['pnl_pct'] for p in p20_picks])
            p80_avg_pnl = mean([p['pnl_pct'] for p in p80_picks])
            
            lift = p80_avg_pnl - p20_avg_pnl
            polarity_ok = lift > 0
            
            # Suspect if high-score avg is < -1% with n >= 50
            suspect = len(p80_picks) >= 5 and p80_avg_pnl < -0.01
            
            scores_by_field[field] = {
                'p20': p20, 'p80': p80,
                'p20_avg_pnl': p20_avg_pnl,
                'p80_avg_pnl': p80_avg_pnl,
                'lift': lift,
                'polarity_ok': polarity_ok,
                'suspect': suspect,
                'n': len(picks)
            }
        
        calibration[system] = scores_by_field
    
    return calibration
```

**Benefits:**
- Isolates copy_trader_intel's toxicity (p80_avg_pnl = -3.295% → flags `suspect=True`)
- Validates kimi_riseoftheclaw's correctness (lift = +1.498%)
- Enables system-aware score reweighting (see Enhancement 3)

**Dashboard Integration:**
- Add `/audit?system_calibration=1` view showing per-system lift matrix
- Flag systems with `suspect=True` in red on dashboard
- Show exclusion impact ("Without X: global lift = +Y%")

---

### Enhancement 2: Loss Driver Analyzer Integration (tools/loss_driver_analyzer.py)

**Current State:** When a strategy underperforms, `STRATEGY_INVESTIGATION_BEFORE_KILL.md` recommends mutation analysis, but no tool exists to quickly surface loss concentration, exit-reason breakdown, or worst symbols.

**Proposed Solution:** Fast-path loss analyzer that runs before mutation tests:

```python
# tools/loss_driver_analyzer.py (new tool)

def analyze_loss_drivers(strategy: str, closed_picks: List[dict]) -> dict:
    """
    Stratify losses by: (1) exit reason, (2) symbol, (3) direction, (4) timeframe.
    Returns: {
        'total_losses': float,
        'loss_pct': float,
        'top_loss_symbols': [(symbol, loss, count), ...],
        'exit_reason_breakdown': {exit_reason: {loss, count, pct}},
        'deterministic_loser': bool  # if WR == 0% and n >= 20
    }
    """
    picks = [p for p in closed_picks if p.get('strategy') == strategy]
    if len(picks) < 10:
        return {'error': 'Insufficient data'}
    
    losing_picks = [p for p in picks if p.get('pnl_pct', 0) < 0]
    total_loss = sum(p['pnl_pct'] for p in losing_picks)
    
    # Worst symbols
    by_symbol = defaultdict(list)
    for p in losing_picks:
        by_symbol[p['symbol']].append(p['pnl_pct'])
    
    top_symbols = sorted(
        [(sym, sum(pnls), len(pnls)) for sym, pnls in by_symbol.items()],
        key=lambda x: x[1]  # Sort by total loss
    )[:10]
    
    # Exit reasons
    exit_reasons = defaultdict(lambda: {'loss': 0, 'count': 0})
    for p in losing_picks:
        reason = p.get('exit_reason', 'unknown')
        exit_reasons[reason]['loss'] += p['pnl_pct']
        exit_reasons[reason]['count'] += 1
    
    # Deterministic loser (WR = 0%)
    wr = len([p for p in picks if p['pnl_pct'] > 0]) / len(picks)
    deterministic = (wr == 0 and len(picks) >= 20)
    
    return {
        'total_losses': total_loss,
        'loss_pct': total_loss / sum(p['pnl_pct'] for p in picks),
        'top_loss_symbols': top_symbols,
        'exit_reason_breakdown': dict(exit_reasons),
        'deterministic_loser': deterministic,
        'wr': wr,
        'n': len(picks)
    }
```

**Usage in Escalation Ladder:**
1. Dashboard shows strategy with WR < 35% and avg_pnl < -0.5%
2. Run `python tools/loss_driver_analyzer.py --strategy kimi_signal_tracking`
3. If deterministic_loser (WR=0% + n≥20) → immediate surgical block (Stage 5)
4. If exit_reason_breakdown shows 80%+ SL hits → sizing/SL problem, not selection → rehabilitate
5. If top_loss_symbols has 1 symbol with 50%+ of total loss → symbol-specific block or invert direction

**Benefits:**
- Faster RCA before expensive mutation tests
- Surfaces **exit-reason** axis missing from current `MUTATION_THREE_AXIS_PROTOCOL.md`
- Enables deterministic-loser fast-path (WR=0% + n≥20 → block immediately)

---

### Enhancement 3: Score Architecture Redesign (audit_trail/score_semantics.py)

**Current State:** All scores mixed together (confidence, elite_score, trust_score) with contradictory semantics.

**Proposed Solution:** Separate classification quality from payoff quality:

```python
# audit_trail/score_semantics.py (new module)

class ScoreSemantics:
    """
    Separate score types:
    - CLASSIFICATION (confidence, elite_score): P(Win) or signal strength → good for routing
    - PAYOFF_QUALITY (trust_score, method_a): Expected payoff severity → good for sizing
    """
    
    @staticmethod
    def compute_classification_score(pick: dict) -> float:
        """
        Ensemble of confidence + elite_score (both measure classification quality).
        Average the two, but invert polarity of confidence (inverse correlation with PnL).
        """
        confidence = pick.get('confidence', 0)
        elite = pick.get('elite_score', 0)
        
        # Invert confidence: if high confidence → worse PnL, flip
        confidence_inverted = 100 - confidence if confidence else 0
        
        # Average both
        return (confidence_inverted + elite) / 2
    
    @staticmethod
    def compute_payoff_quality_score(pick: dict) -> float:
        """
        Use trust_score as primary (only correct polarity, +0.279 correlation).
        Fall back to method_a if trust_score is missing.
        This is the only score that should be trusted for sizing.
        """
        trust = pick.get('trust_score', 0)
        method_a = pick.get('method_a_score', 0)
        
        # Prefer trust_score; fallback to method_a
        return trust if trust else method_a
    
    @staticmethod
    def get_routing_score(pick: dict) -> float:
        """
        Final routing score = average of CLASSIFICATION (60%) + PAYOFF (40%).
        Classification helps with selection; payoff quality helps with sizing.
        """
        classification = ScoreSemantics.compute_classification_score(pick)
        payoff = ScoreSemantics.compute_payoff_quality_score(pick)
        
        # Weight towards classification (routing) but include payoff risk
        return 0.6 * classification + 0.4 * payoff
    
    @staticmethod
    def get_sizing_score(pick: dict) -> float:
        """
        Sizing should ONLY use payoff quality (trust_score).
        High payoff quality → larger size. Low quality → smaller size.
        """
        return ScoreSemantics.compute_payoff_quality_score(pick)
```

**Integration:**
- Update `forward_validator.py` to use `get_routing_score()` for active pick selection
- Update position sizing in `regime_position_sizer.py` to use `get_sizing_score()`
- Mark `confidence` as "diagnostic only" in dashboard (show but don't route on)

**Benefits:**
- Reconciles contradictory semantics (confidence inverted → confidence_inverted correct)
- Isolates payoff quality to trust_score (only field with consistent polarity)
- Enables separate A/B tests: "routing via classification_score vs routing via payoff_score"

---

### Enhancement 4: Mismatch Detection & Alerting (audit_trail/mismatch_detector.py)

**Current State:** Low-score winners (+720%) and high-score losers (-1911.6%) exist but are not flagged or monitored.

**Proposed Solution:** Automated cohort tracking:

```python
# audit_trail/mismatch_detector.py (new module)

def detect_mismatches(closed_picks: List[dict], window_trades: int = 500) -> dict:
    """
    Identify recent picks that contradict score signals.
    Returns mismatch cohorts for dashboard alerts.
    """
    recent = sorted(closed_picks, key=lambda p: p.get('close_time', 0))[-window_trades:]
    
    winners = [p for p in recent if p.get('pnl_pct', 0) > 0]
    losers = [p for p in recent if p.get('pnl_pct', 0) < 0]
    
    # Scoring threshold: p80
    score_threshold = percentile([p.get('score', 0) for p in recent], 80)
    
    # Low-score winners: score < p20, pnl > 0
    low_score_threshold = percentile([p.get('score', 0) for p in recent], 20)
    low_score_winners = [p for p in winners if p.get('score', 0) < low_score_threshold]
    
    # High-score losers: score > p80, pnl < 0
    high_score_losers = [p for p in losers if p.get('score', 0) > score_threshold]
    
    return {
        'low_score_winners': {
            'count': len(low_score_winners),
            'total_pnl': sum(p['pnl_pct'] for p in low_score_winners),
            'avg_pnl': mean([p['pnl_pct'] for p in low_score_winners]) if low_score_winners else 0,
            'top_systems': top_n_by_pnl(low_score_winners, 5),
            'signal': '⚠️ UNDERVALUED EDGE — routing might be TOO CONSERVATIVE'
        },
        'high_score_losers': {
            'count': len(high_score_losers),
            'total_pnl': sum(p['pnl_pct'] for p in high_score_losers),
            'avg_pnl': mean([p['pnl_pct'] for p in high_score_losers]) if high_score_losers else 0,
            'top_systems': top_n_by_pnl(high_score_losers, 5),
            'signal': '🚨 TOXIC COMBO — high score + consistent losses = miscalibrated signal'
        }
    }
```

**Dashboard Integration:**
- Add "Mismatch Cohorts" card on `/audit` homepage
- Show low-score winners as green alert: "Found +$Y edge in N picks scored below median"
- Show high-score losers as red alert: "N high-scoring picks lost avg $Z — root cause analysis in progress"
- Link to per-system breakdown (Enhancement 1)

**Benefits:**
- Surfaces routing inefficiencies automatically
- Enables system-level investigation (e.g., "which systems drive high-score losses?")
- Validates per-system calibration improvements in real-time

---

### Enhancement 5: Exit-Reason Stratification (audit_trail/exit_reason_analysis.py)

**Current State:** Losses are aggregated without understanding **why** they lost (SL hit, timeout, adverse reversal, etc.).

**Proposed Solution:** Stratify losses by exit reason:

```python
# audit_trail/exit_reason_analysis.py (new module)

def stratify_by_exit_reason(picks: List[dict]) -> dict:
    """
    Categorize losses by: SL-hit (R:R ≈ 1:1), TP-hit, timeout, reversal (R:R >> 1:1).
    Returns: {exit_reason: {wr, avg_pnl, pf, count, interpretation}}
    """
    by_reason = defaultdict(list)
    
    for p in picks:
        reason = p.get('exit_reason', 'unknown')
        by_reason[reason].append(p)
    
    results = {}
    for reason, reason_picks in by_reason.items():
        wins = [p for p in reason_picks if p['pnl_pct'] > 0]
        losses = [p for p in reason_picks if p['pnl_pct'] < 0]
        
        wr = len(wins) / len(reason_picks)
        avg_pnl = mean([p['pnl_pct'] for p in reason_picks])
        pf = sum(p['pnl_pct'] for p in wins) / abs(sum(p['pnl_pct'] for p in losses)) if losses else float('inf')
        
        # Interpretation
        if wr < 0.30 and pf < 1.5:
            interpretation = "⚠️ LOW WR + LOW PF = strategy not viable; consider retire"
        elif reason == "SL_HIT" and pf < 0.8:
            interpretation = "SL-driven losses dominate; issue is sizing/SL config, not selection"
        elif reason == "TIMEOUT" and pf > 2.0:
            interpretation = "✅ Timeouts are profitable; extend hold window"
        else:
            interpretation = "Neutral outcome"
        
        results[reason] = {
            'wr': wr,
            'avg_pnl': avg_pnl,
            'pf': pf,
            'count': len(reason_picks),
            'interpretation': interpretation
        }
    
    return results
```

**Usage in Strategy Investigation:**
- If strategy has WR < 30% and avg_pnl < -0.5%:
  - Run exit_reason_analysis
  - If SL_HIT dominates with R:R ≈ 1:1 → not a selection problem, it's a sizing problem → rehab via SL config
  - If TIMEOUT dominates with high PF → extend hold window → quick win
  - If REVERSAL dominates → strategy logic is flawed → consider retire

**Benefits:**
- Distinguishes **selection problems** (bad entry logic) from **sizing problems** (SL/TP config)
- Enables targeted rehabilitation (e.g., "SL config fix" vs "entry logic rewrite")
- Speeds up escalation-ladder decisions

---

## Implementation Roadmap

| Phase | Deliverables | Timeline | Dependencies |
|---|---|---|---|
| **Phase 1: Diagnostics** | score_calibration.py (per-system stats), loss_driver_analyzer.py | Week 1 | None |
| **Phase 2: Architecture** | score_semantics.py (score split), mismatch_detector.py | Week 2 | Phase 1 |
| **Phase 3: Integration** | Dashboard cards for mismatches, per-system calibration view | Week 3 | Phases 1–2 |
| **Phase 4: Validation** | Run on production data, A/B test new routing vs old | Week 4 | Phase 3 |
| **Phase 5: Deployment** | Cut to production, update docs, retire copy_trader_intel variants | Week 5 | Phase 4 |

---

## Success Metrics

| Metric | Current | Target | Validation |
|---|---|---|---|
| Global score lift | -0.312% (inverted) | +0.696% (positive) | Remove copy_trader_intel, verify |
| High-score WR | 45.5% | > 50% | Per-system calibration + architecture split |
| Low-score edge preservation | +720% total | +900%+ total | Improve routing to low-score winners |
| High-score loss reduction | -1911.6% total | < -1000% total | System isolation + exit-reason rehab |
| Deterministic-loser false-positive rate | N/A | < 5% | Validate hard-block criteria on validation set |
| Dashboard mismatch detection latency | N/A | < 5 min | Real-time alert on `/audit` |

---

## Related Documents

- `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` — enhanced with exit-reason axis + loss_driver_analyzer integration
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md` — add fast-path for deterministic losers (WR=0%)
- `audit_trail/pick_schema.py` — add optional fields: `exit_reason`, `strategy_mutation_parent`, `suspect_calibration_flag`

---

## Appendix: Calibration Audit Summary (2026-04-19)

**Dataset:** 3,500 recent closed picks from production `/audit` dashboard  
**Timestamp:** 2026-04-19 19:12:31 UTC  
**Key Findings:**

1. **Global score inversion:** High-score picks (p80) return -0.742% vs low-score -0.431%; lift = -0.311%
2. **copy_trader_intel toxicity:** 143 picks, -1621.3% total, -11.34% avg; accounts for 85% of all high-score losses
3. **Per-system variance:** kimi_riseoftheclaw +1.498% lift (correct), copy_trader_intel +0.530% (deep baseline), alpha_engine -0.324% (inverted)
4. **Correlation hierarchy:** elite_score +0.410 Spearman, trust_score +0.279 (best payoff proxy), confidence +0.123 (inverse polarity)
5. **Asset-class risk:** Commodity 100% high-score loss rate, Crypto 86.4%, Forex 44.2%, Equity 29.7%
6. **Mismatch cohorts:** 308 low-score winners (+720%), 395 high-score losers (-1911.6%)
7. **Remediation ROI:** Removing copy_trader_intel flips score lift from -0.312% to +0.696% (+1.008pp)

---

## Sign-Off

- **Analysis by:** GitHub Copilot + Claude Haiku 4.5
- **Review status:** Ready for peer review
- **PR Target:** main branch (after 1 approval from code-review agent)
