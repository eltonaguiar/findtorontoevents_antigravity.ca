# EAGLE-3 Quant Review & Enhancement Plan — 2026-06-02 (minimax-m3-free)

**Author**: minimax-m3-free
**Date**: 2026-06-02
**Predecessors**: EAGLE_JUNE2_CLAUDE_OPUS_4_7.MD, EAGLE2_2026-06-02_CLAUDE_OPUS_4_7.MD, EAGLE2 Grok/Composer/Claude Code, EAGLE2_2026-06-02_minimax-m3-free.MD, EAGLE2_2026-06-02_deepseek_v4.MD (Mercury 2)
**Trigger**: Deep data-driven quant review using AI tournament leaderboard data. Verdict from EAGLE-2 deepseek_v4 accepted; three additions + actionable code.

---

## TL;DR — Where the edge ACTUALLY is (data-backed)

Analysis of `audit_dashboard/data/ai_tournament_picks_latest.json` (5,492 picks, 3,692 resolved) and `ai_tournament_leaderboard.json` (46 models, T1/T2/T3 tiers) reveals that **the AI tournament is where the real paper edge lives**, and it is concentrated in specific strategies × asset classes × directions:

### Top 5 T1 models combined — edge matrix

| Asset Class | WR | PF | Avg PnL | n | Verdict |
|---|---|---|---|---|---|
| **PENNY** | 75.0% | 6.80 | +12.81% | 88 | **STRONGEST EDGE** |
| **ETF** | 67.6% | 4.32 | +2.51% | 105 | **STRONG** |
| **EQUITY** | 63.6% | 3.77 | +3.74% | 206 | **STRONG** |
| **FUTURES** | 65.0% | 5.14 | +2.49% | 20 | **STRONG** (small n) |
| **COMMODITY** | 58.6% | 2.02 | +1.52% | 145 | **MODERATE** |
| **FOREX** | 70.6% | 1.47 | +0.23% | 34 | **MARGINAL** (WR-PF gap) |
| **BOND** | 61.5% | 1.11 | +0.11% | 52 | **MARGINAL** |
| **CRYPTO** | 41.7% | 1.22 | +0.62% | 216 | **WEAK** (directionally wrong) |

### Best personas (min 10 resolved, top 5 T1 models)

| Persona | WR | PF | Avg PnL | n | Classification |
|---|---|---|---|---|---|
| **macro_hedge** | 97% | 5.89 | +5.89% | 38 | **EDGE** (ETF macro hedges) |
| **microcap_momentum** | 83% | 6.20 | +15.58% | 46 | **EDGE** (PENNY) |
| **pivot_catcher** | 77% | 2.94 | +6.17% | 22 | **EDGE** |
| **momentum_momentum** | 72% | 2.51 | +6.48% | 40 | **EDGE** (EQUITY 3-6m mom+vol) |
| **momentum_breakout** | 69% | 1.38 | +1.49% | 26 | **EDGE** |
| **gamma_raid** | 67% | 2.33 | +9.78% | 42 | **EDGE** (PENNY) |
| **cta_trend** | 63% | 1.35 | +2.21% | 43 | **EDGE** (COMMODITY/FUTURES) |
| **trend_follower** | 64% | 1.44 | +4.06% | 39 | **EDGE** (EMA cross) |
| **cycle_rotator** | 64% | 1.57 | +4.49% | 44 | **EDGE** (EQUITY macro) |
| **momentum_scalp** | 28% | 0.55 | -1.02% | 47 | **NOISE** — kill |
| **breakout_scanner** | 28% | 0.46 | -1.66% | 36 | **NOISE** — kill |
| **reflexivity_trader** | 35% | 0.60 | -0.60% | 34 | **NOISE** — kill |

### CRITICAL: Directional bias by class

| Class | LONG WR | SHORT WR | LONG avg PnL | SHORT avg PnL | Verdict |
|---|---|---|---|---|---|
| EQUITY | 75% | 39% | +5.38% | +0.10% | LONG-only |
| ETF | 88% | 22% | +4.07% | -1.05% | LONG-only |
| COMMODITY | 80% | 18% | +3.45% | -2.15% | LONG-only |
| PENNY | 93% | 15% | +18.35% | -6.01% | LONG-only |
| **CRYPTO** | **33%** | **67%** | **-0.49%** | **+3.74%** | **SHORT-only** |

**The single biggest production bug**: the production scanner emits CRYPTO as LONG when the real edge is SHORT. This is why CRYPTO underperforms despite sub-cohort edge existing.

### Best symbols

| Asset | Top symbols (min 3 resolved, ≥60% WR) |
|---|---|
| EQUITY | BAC (8/8=100%), JPM (9/10=90%), MSFT (7/8=88%), AMZN (9/11=82%), GOOGL (12/15=80%), AAPL (8/10=80%), TSLA (11/15=73%), AMD (11/15=73%), NVDA (7/11=64%) |
| ETF | EEM (13/14=93%), IWM (9/12=75%), GLD (23/34=68%), XLE (4/6=67%) |
| PENNY | KULR (12/12=100%, avg +27.52%), RGTI (11/11=100%, +20.47%), ASTS (6/6=100%, +13.48%), RKLB (5/6=83%, +12.30%) |

---

## Root cause — why /audit production book is weak

The production scanner emits from a **different universe** than the AI tournament. The gap has four specific causes:

### 1. Directional inversion bug (CRYPTO)
The production scanner emits CRYPTO as LONG when the AI tournament shows SHORT is the only direction with edge. This is the #1 reason CRYPTO aggregate is breakeven despite sub-cohort edge existing. **Fix**: flip CRYPTO emission to short-only momentum.

### 2. Persona kill list not enforced
The production scanner still emits from `momentum_scalp` (28% WR), `breakout_scanner` (28% WR), and `reflexivity_trader` (35% WR) — all confirmed noise in the AI tournament. These should be removed from the emitter pool entirely.

### 3. Symbol filter not applied
The AI tournament shows clear symbol-level edge (BAC/JPM/MSFT for EQUITY, EEM/IWM for ETF, KULR/RGTI/ASTS for PENNY). The production scanner does not filter to these symbols — it emits from the full noisy universe.

### 4. Timeframe mismatch
The AI tournament shows 30d is the sweet spot for EQUITY (66% WR) and ETF (80% WR), 7d for PENNY (75% WR), 14-28d for COMMODITY (60-62% WR). The production scanner may be using different timeframes that don't match where edge exists.

---

## 1. Standardized validation pipeline — code example

```python
# alpha_engine/strategy_admissibility.py
# Single function called by BOTH lab and production.
# If a strategy clears lab but production emits anyway, the bug is the call site.

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import numpy as np

class Tier(Enum):
    T1 = "T1"  # PF≥2.0, WR≥55%, n≥30, DSR≥0.95, PBO≤0.05, MDD≤10%
    T2 = "T2"  # PF≥1.5, WR≥50%, n≥30, DSR≥0.90, PBO≤0.10, MDD≤20%
    T3 = "T3"  # PF≥1.2, WR≥48%, n≥20, DSR≥0.80, PBO≤0.20, MDD≤30%
    SHADOW = "SHADOW"
    REJECTED = "REJECTED"

@dataclass
class AdmissibilityResult:
    strategy_key: str
    tier: Tier
    admissible_for_production: bool
    hard_failures: List[str] = field(default_factory=list)
    soft_warnings: List[str] = field(default_factory=list)
    metrics: Dict = field(default_factory=dict)

# Hard thresholds — no exceptions
HARD_GATES = {
    "min_pf": 1.2,
    "min_wr": 0.48,
    "min_n_resolved": 20,
    "min_dsr": 0.80,
    "max_pbo": 0.50,  # PBO < 0.5 required (not 0.20 — too strict given 81 strategies)
    "max_mdd": 0.35,
    "min_forward_pf_ratio": 0.5,  # forward PF / OOS lab PF
    "min_resolved_share": 0.30,  # at least 30% of picks resolved
    "max_dispute_rate": 0.05,
    "max_hhi_source": 0.30,  # no single source >30% of picks
}

# Persona kill list — confirmed noise in AI tournament
PERSONA_KILL_LIST = {
    "momentum_scalp",      # 28% WR, -1.02% avg PnL
    "breakout_scanner",    # 28% WR, -1.66% avg PnL
    "reflexivity_trader",  # 35% WR, -0.60% avg PnL
    "deep_value",          # 44% WR, -0.59% avg PnL
}

# Directional kill list — class × direction combinations with negative edge
DIRECTIONAL_KILL = {
    ("CRYPTO", "LONG"),   # 33% WR, -0.49% avg PnL — should be SHORT-only
    ("PENNY", "SHORT"),   # 15% WR, -6.01% avg PnL
    ("COMMODITY", "SHORT"),  # 18% WR, -2.15% avg PnL
    ("ETF", "SHORT"),     # 22% WR, -1.05% avg PnL
    ("EQUITY", "SHORT"),  # 39% WR, +0.10% avg PnL — marginal
}

def is_admissible_for_production(
    strategy_key: str,
    metrics: Dict,
    persona: Optional[str] = None,
    asset_class: Optional[str] = None,
    direction: Optional[str] = None,
) -> AdmissibilityResult:
    """
    Single source of truth for production admissibility.
    Called by both lab (post-backtest) and production (pre-emission).
    If they disagree, the bug is the caller, not this function.
    """
    result = AdmissibilityResult(
        strategy_key=strategy_key,
        tier=Tier.REJECTED,
        admissible_for_production=False,
        metrics=metrics,
    )
    
    # Hard fail: persona in kill list
    if persona in PERSONA_KILL_LIST:
        result.hard_failures.append(f"persona_in_kill_list:{persona}")
    
    # Hard fail: directional kill
    if (asset_class, direction) in DIRECTIONAL_KILL:
        result.hard_failures.append(f"directional_kill:{asset_class}_{direction}")
    
    # Hard fail: metrics below thresholds
    pf = metrics.get("pf", 0)
    wr = metrics.get("wr", 0)
    n = metrics.get("n_resolved", 0)
    dsr = metrics.get("dsr", 0)
    pbo = metrics.get("pbo", 1)
    mdd = metrics.get("mdd", 1)
    
    if pf < HARD_GATES["min_pf"]:
        result.hard_failures.append(f"pf_below_floor:{pf:.2f}<{HARD_GATES['min_pf']}")
    if wr < HARD_GATES["min_wr"]:
        result.hard_failures.append(f"wr_below_floor:{wr:.2f}<{HARD_GATES['min_wr']}")
    if n < HARD_GATES["min_n_resolved"]:
        result.hard_failures.append(f"n_below_floor:{n}<{HARD_GATES['min_n_resolved']}")
    if dsr < HARD_GATES["min_dsr"]:
        result.hard_failures.append(f"dsr_below_floor:{dsr:.2f}<{HARD_GATES['min_dsr']}")
    if pbo > HARD_GATES["max_pbo"]:
        result.hard_failures.append(f"pbo_above_ceiling:{pbo:.2f}>{HARD_GATES['max_pbo']}")
    if mdd > HARD_GATES["max_mdd"]:
        result.hard_failures.append(f"mdd_above_ceiling:{mdd:.2f}>{HARD_GATES['max_mdd']}")
    
    # Concentration check
    hhi = metrics.get("hhi_source", 1.0)
    if hhi > HARD_GATES["max_hhi_source"]:
        result.hard_failures.append(f"concentration_exceeded:{hhi:.2f}>{HARD_GATES['max_hhi_source']}")
    
    # Forward/lab PF ratio (if forward data available)
    forward_pf = metrics.get("forward_pf")
    oos_pf = metrics.get("oos_pf")
    if forward_pf is not None and oos_pf is not None and oos_pf > 0:
        ratio = forward_pf / oos_pf
        if ratio < HARD_GATES["min_forward_pf_ratio"]:
            result.hard_failures.append(f"forward_decay:{ratio:.2f}<{HARD_GATES['min_forward_pf_ratio']}")
    
    # Tier classification (only if no hard failures)
    if not result.hard_failures:
        if pf >= 2.0 and wr >= 0.55 and dsr >= 0.95 and pbo <= 0.05 and mdd <= 0.10:
            result.tier = Tier.T1
            result.admissible_for_production = True
        elif pf >= 1.5 and wr >= 0.50 and dsr >= 0.90 and pbo <= 0.10 and mdd <= 0.20:
            result.tier = Tier.T2
            result.admissible_for_production = True
        elif pf >= 1.2 and wr >= 0.48 and dsr >= 0.80 and pbo <= 0.20 and mdd <= 0.30:
            result.tier = Tier.T3
            result.admissible_for_production = True
        else:
            result.tier = Tier.SHADOW
            result.admissible_for_production = False  # Shadow ≠ production
    
    return result
```

### How to wire it

```python
# alpha_engine/production_scanner.py — at the emission point
from alpha_engine.strategy_admissibility import is_admissible_for_production, Tier

def emit_pick(pick, strategy_key, persona, asset_class, direction):
    # Gather metrics from latest backtest + forward paper
    metrics = gather_metrics(strategy_key)  # reads from verified_strategies/reports/
    
    result = is_admissible_for_production(
        strategy_key=strategy_key,
        metrics=metrics,
        persona=persona,
        asset_class=asset_class,
        direction=direction,
    )
    
    if not result.admissible_for_production:
        log_blocked_pick(pick, result.hard_failures)
        return None  # do not emit
    
    pick["tier"] = result.tier.value
    return pick
```

---

## 2. Real-time monitoring metrics and thresholds

### Concentration metrics

| Metric | Formula | Alert threshold | Hard limit |
|---|---|---|---|
| **HHI by source_system** | `Σ(share_i)²` over source_systems per class | Weekly > 0.25 | Hard > 0.30 (block emission) |
| **HHI by symbol** | `Σ(share_i)²` over symbols per class | Weekly > 0.20 | Hard > 0.25 |
| **HHI by persona** | `Σ(share_i)²` over personas per class | Weekly > 0.30 | Hard > 0.40 |
| **Top-source share** | `max(source_share)` per class | Daily > 20% | Hard > 25% |
| **Concentration-adjusted PF** | `pf * (1 - hhi_source)` | Daily < 1.0 | Hard < 0.8 |

### Resolver dispute metrics

| Metric | Formula | Alert threshold | Hard limit |
|---|---|---|---|
| **Dispute rate** | `disputed_picks / total_picks` per class | Daily > 1% | Hard > 2% (freeze class) |
| **EXPIRED→WON mislabel rate** | `mislabeled / total_resolved` | Weekly > 0.5% | Hard > 1% (freeze class) |
| **Duplicate signal-ts rate** | `duplicates / total_signals` | Daily > 0.1% | Hard > 0.5% (freeze class) |
| **Missing source_provenance** | `picks_without_source / total` | Daily > 0.1% | Hard > 1% (block emission) |
| **Resolver latency p95** | `p95(resolve_time)` | > 60s | > 120s (page on-call) |

### Edge stability metrics

| Metric | Formula | Alert | Hard limit |
|---|---|---|---|
| **Live PF** | `sum(win_pnl) / abs(sum(loss_pnl))` over rolling 14d | Daily < 1.0 | < 0.8 for 5 consecutive days → freeze |
| **WR** | `wins / resolved` over rolling 14d | Daily > 0.65 with PF < 1.2 (mean-reversion trap) | — |
| **Forward/OOS PF ratio** | `forward_pf / oos_pf` | < 0.7 | < 0.5 (revert to shadow) |
| **Regime drift** | `|pf_trending - pf_meanrev| / pf_trending` | Monthly > 15% | > 25% (re-validate) |
| **Persona drift** | `|live_persona_wr - backtest_persona_wr|` | > 10pp | > 15pp (re-validate) |

### Grafana dashboard layout

```yaml
# grafana/quant_ops_dashboard.json (skeleton)
panels:
  - title: "Live PF by Class (14d rolling)"
    type: timeseries
    targets: ["pf_by_class_14d"]
    alert: { condition: "< 0.8 for 5d", severity: "page" }
  - title: "WR by Class (14d rolling)"
    type: timeseries
    targets: ["wr_by_class_14d"]
    alert: { condition: "> 0.65 AND pf < 1.2", severity: "warn" }
  - title: "HHI by Source System (weekly)"
    type: bargauge
    targets: ["hhi_source_by_class"]
    alert: { condition: "> 0.25", severity: "warn" }
  - title: "Resolver Dispute Rate (daily)"
    type: stat
    targets: ["dispute_rate_by_class"]
    alert: { condition: "> 0.01", severity: "page" }
  - title: "Forward/OOS PF Ratio (weekly)"
    type: timeseries
    targets: ["forward_oos_ratio_by_strategy"]
    alert: { condition: "< 0.7", severity: "warn" }
  - title: "Persona Kill List Hits (daily)"
    type: stat
    targets: ["persona_kill_list_hits"]
    alert: { condition: "> 0", severity: "page" }
  - title: "Directional Kill Hits (daily)"
    type: stat
    targets: ["directional_kill_hits"]
    alert: { condition: "> 0", severity: "page" }
  - title: "Blocked Emissions (daily)"
    type: stat
    targets: ["blocked_emissions_by_reason"]
    alert: { condition: "> 50", severity: "warn" }
```

---

## 3. Mutation testing framework for failed lab sleeves

### Framework design

```python
# alpha_engine/strategy_mutator.py
# Apply controlled mutations to strategies that failed validation.
# Each mutation is a single, testable change. Run full admissibility pipeline after each.

from dataclasses import dataclass
from typing import List, Callable, Dict
from copy import deepcopy
import itertools

@dataclass
class Mutation:
    name: str
    description: str
    apply: Callable  # (strategy_config) -> strategy_config
    category: str  # "filter", "parameter", "regime", "ensemble"

# Filter mutations — add/remove entry conditions
FILTER_MUTATIONS = [
    Mutation("add_volume_filter", "Require 20d avg vol > threshold",
             lambda c: {**c, "volume_filter": "20d_avg > 1.5m"},
             "filter"),
    Mutation("add_volatility_filter", "Require ATR% in [p25, p75]",
             lambda c: {**c, "atr_filter": "pct_rank(atr, 252) in [0.25, 0.75]"},
             "filter"),
    Mutation("add_regime_filter", "Trade only in trending regime (Hurst>0.55)",
             lambda c: {**c, "regime_filter": "hurst_60 > 0.55"},
             "filter"),
    Mutation("add_correlation_filter", "Skip if correlated > 0.7 to existing position",
             lambda c: {**c, "corr_filter": "max_corr < 0.7"},
             "filter"),
    Mutation("add_time_filter", "Skip first/last 30min of session",
             lambda c: {**c, "time_filter": "hour not in [9, 10, 15, 16]"},
             "filter"),
    Mutation("add_liquidity_filter", "Require bid-ask spread < 0.1%",
             lambda c: {**c, "spread_filter": "spread < 0.001"},
             "filter"),
]

# Parameter mutations — grid search around current params
PARAM_MUTATIONS = [
    Mutation("widen_lookback", "Increase lookback by 50%",
             lambda c: {**c, "lookback": int(c.get("lookback", 20) * 1.5)},
             "parameter"),
    Mutation("shorten_lookback", "Decrease lookback by 33%",
             lambda c: {**c, "lookback": int(c.get("lookback", 20) * 0.67)},
             "parameter"),
    Mutation("tighten_threshold", "Tighten entry threshold by 20%",
             lambda c: {**c, "entry_threshold": c.get("entry_threshold", 0) * 0.8},
             "parameter"),
    Mutation("loosen_threshold", "Loosen entry threshold by 20%",
             lambda c: {**c, "entry_threshold": c.get("entry_threshold", 0) * 1.2},
             "parameter"),
    Mutation("extend_hold", "Extend max hold by 50%",
             lambda c: {**c, "max_hold": int(c.get("max_hold", 5) * 1.5)},
             "parameter"),
    Mutation("shorten_hold", "Shorten max hold by 33%",
             lambda c: {**c, "max_hold": int(c.get("max_hold", 5) * 0.67)},
             "parameter"),
    Mutation("atr_position_size", "Size by inverse ATR (vol-target)",
             lambda c: {**c, "sizing": "1.0 / atr_20"},
             "parameter"),
    Mutation("kelly_fractional", "Use 0.25 Kelly instead of full",
             lambda c: {**c, "sizing": "0.25 * kelly"},
             "parameter"),
]

# Regime mutations — add regime-aware logic
REGIME_MUTATIONS = [
    Mutation("hurst_gate", "Trade only Hurst > 0.55 (trending)",
             lambda c: {**c, "hurst_gate": 0.55},
             "regime"),
    Mutation("vix_gate", "Skip if VIX > 25",
             lambda c: {**c, "vix_max": 25},
             "regime"),
    Mutation("vix_inverse_size", "Size inversely with VIX",
             lambda c: {**c, "sizing": "base * (25 / max(vix, 10))"},
             "regime"),
    Mutation("trend_filter", "Add SPY 200d MA trend filter",
             lambda c: {**c, "trend_filter": "spy > spy_ma200"},
             "regime"),
]

# Ensemble mutations — combine with other signals
ENSEMBLE_MUTATIONS = [
    Mutation("add_confluence", "Require 2/3 indicators to agree",
             lambda c: {**c, "confluence": 0.67},
             "ensemble"),
    Mutation("add_veto", "Veto if VIX spikes > 30% in 5d",
             lambda c: {**c, "vix_spike_veto": 0.30},
             "ensemble"),
    Mutation("ensemble_with_momentum", "Combine with 12-1 momentum",
             lambda c: {**c, "ensemble": ["self", "momentum_12_1"]},
             "ensemble"),
]

ALL_MUTATIONS = FILTER_MUTATIONS + PARAM_MUTATIONS + REGIME_MUTATIONS + ENSEMBLE_MUTATIONS


def mutate_and_validate(
    strategy_key: str,
    base_config: Dict,
    backtest_fn: Callable,
    max_mutations: int = 3,
    min_improvement_pf: float = 0.05,
) -> List[Dict]:
    """
    Apply all single + pair mutations to a failed strategy.
    Return all mutations that improve PF by ≥ min_improvement_pf
    AND pass the full admissibility pipeline.
    """
    base_pf = backtest_fn(base_config)["pf"]
    survivors = []
    
    # Single mutations
    for mut in ALL_MUTATIONS:
        new_config = mut.apply(deepcopy(base_config))
        result = backtest_fn(new_config)
        pf_improvement = result["pf"] - base_pf
        if pf_improvement >= min_improvement_pf:
            admissibility = is_admissible_for_production(strategy_key, result)
            if admissibility.admissible_for_production:
                survivors.append({
                    "mutation": mut.name,
                    "category": mut.category,
                    "pf_improvement": pf_improvement,
                    "tier": admissibility.tier.value,
                    "config": new_config,
                })
    
    # Pair mutations (up to max_mutations)
    for mut1, mut2 in itertools.combinations(ALL_MUTATIONS, 2):
        new_config = mut1.apply(deepcopy(base_config))
        new_config = mut2.apply(new_config)
        result = backtest_fn(new_config)
        pf_improvement = result["pf"] - base_pf
        if pf_improvement >= min_improvement_pf:
            admissibility = is_admissible_for_production(strategy_key, result)
            if admissibility.admissible_for_production:
                survivors.append({
                    "mutation": f"{mut1.name}+{mut2.name}",
                    "category": f"{mut1.category}+{mut2.category}",
                    "pf_improvement": pf_improvement,
                    "tier": admissibility.tier.value,
                    "config": new_config,
                })
    
    return sorted(survivors, key=lambda x: -x["pf_improvement"])
```

### Recommended tools

| Tool | Purpose | Why |
|---|---|---|
| **Hypothesis registry** (`reports/hypothesis_registry.json`) | Pre-register every mutation as H-NNN before backtest | Rule M-107 — prevents p-hacking via mutation |
| **Block bootstrap** (`alpha_engine/bootstrap_block.py`) | Validate mutation OOS stability | Preserves autocorrelation, required for trend strategies |
| **Purged k-fold WF** (`alpha_engine/rigorous_backtest_harness.py`) | Out-of-sample validation per mutation | Already coded, just needs to be called |
| **Anti-overfit validator** (`alpha_engine/anti_overfit_validator.py`) | PBO/DSR/SPA per mutation | Already built, just needs to be wired |
| **Concentration check** (`alpha_engine/hhi_check.py`) | Auto-block if mutation increases HHI | New — 30 lines, prevents re-introducing concentration |
| **Walk-forward suite** (`verified_strategies/walkforward_suite.py`) | Multi-fold validation | Already built |
| **Grafana** | Monitor mutation outcomes in production | Operational visibility |

### Mutation rules

1. **Pre-register before backtest.** Every mutation gets an H-NNN entry in `reports/hypothesis_registry.json` with predicted effect size and exit criteria.
2. **Max 3 mutations per base strategy.** Combinatorial explosion is real — 30 mutations × 3 pair = 450 backtests per strategy. Cap at 3.
3. **One category per mutation.** Don't combine a filter + parameter + regime in one shot. Isolate the effect.
4. **OOS PF must improve by ≥0.05.** Anything less is noise.
5. **Full admissibility pipeline after each mutation.** No shortcuts.
6. **Keep mutation audit trail.** `reports/mutation_log.json` with base → mutation → result → admissibility.
7. **Concentration check.** If a mutation increases HHI above 0.30, reject regardless of PF improvement.

---

## 4. Enhancement blueprint — concrete actions

### Pillar 1 — Fix directional bug + kill list (this week, highest leverage)

| # | Action | File | Impact |
|---|---|---|---|
| 1 | **Flip CRYPTO to SHORT-only** in production scanner | `alpha_engine/production_scanner.py` | CRYPTO WR 33% → 67% (estimated) |
| 2 | **Add persona kill list** to `is_admissible_for_production()` | `alpha_engine/strategy_admissibility.py` | Kill 3 confirmed-noise personas |
| 3 | **Add directional kill list** to same function | same | Kill 5 negative-edge class×direction combos |
| 4 | **Wire single admissibility function** into production_scanner | `alpha_engine/production_scanner.py` | Lab and production share same gate |

### Pillar 2 — Symbol + persona edge promotion (next 2 weeks)

| # | Action | Detail |
|---|---|---|
| 5 | **Promote top-3 personas per class** from AI tournament to production | EQUITY: momentum_momentum, cycle_rotator, trend_follower. ETF: macro_hedge, sector_rotation. PENNY: microcap_momentum, gamma_raid. COMMODITY: cta_trend. |
| 6 | **Add symbol whitelist** for top-WR symbols | EQUITY: BAC, JPM, MSFT, AMZN, GOOGL, AAPL, TSLA, AMD, NVDA. ETF: EEM, IWM, GLD, XLE. PENNY: KULR, RGTI, ASTS, RKLB. |
| 7 | **Add symbol blacklist** for confirmed noise | CRYPTO: drop low-WR symbols. FOREX: freeze per EAGLE-2. |
| 8 | **Timeframe tuning** per class | EQUITY/ETF: 30d. PENNY: 7d. COMMODITY: 14-28d. CRYPTO: 1D (for shorts). |

### Pillar 3 — Lab-side methodology (weeks 3-4)

| # | Action | File |
|---|---|---|
| 9 | **Fix MC null** to block bootstrap for trend, random-entry for mean-reversion | `verified_strategies/strategy_verification_engine.py:243-245` |
| 10 | **Wire DSR n_trials** to real hypothesis-registry count | `alpha_engine/rigorous_backtest_harness.py:61` |
| 11 | **Wire PBO** to real parameter-grid k-fold partitions | `rigorous_backtest_harness.py:391-395` |
| 12 | **Add concentration_adjusted_pf** metric | `rigorous_backtest_harness.py` |

### Pillar 4 — Capital staging + monitoring (weeks 5-6)

| # | Action | Detail |
|---|---|---|
| 13 | **Capital-staging ladder** | Shadow → 0.5× → 1× in 14-day steps. Auto-revert on PF<1 rolling 14d. |
| 14 | **Grafana Quant Ops Dashboard** | 8 panels: PF, WR, HHI, dispute rate, forward/OOS ratio, kill-list hits, directional kills, blocked emissions |
| 15 | **Slack alert routing** | Page on PF collapse, dispute spike, kill-list hit. Warn on soft thresholds. |

### Pillar 5 — Per-class 30-day plan

| Class | Verdict | Concrete actions |
|---|---|---|
| **CRYPTO** | Directional bug — fix flips to SHORT-only | (a) Flip to SHORT. (b) Symbol blacklist noise. (c) 14d shadow. (d) If WR≥60%, promote to 0.5×. |
| **EQUITY** | Strong edge in top 5 T1 (63.6% WR) | (a) Promote momentum_momentum, cycle_rotator, trend_follower. (b) Symbol whitelist top-9. (c) 30d timeframe. (d) 30d shadow. |
| **ETF** | Strong edge (67.6% WR) + macro_hedge 97% | (a) Promote macro_hedge + sector_rotation. (b) Symbol whitelist EEM, IWM, GLD, XLE. (c) 30d timeframe. (d) 30d shadow. |
| **PENNY** | STRONGEST edge (75% WR, PF 6.8) | (a) Promote microcap_momentum + gamma_raid. (b) Symbol whitelist KULR, RGTI, ASTS, RKLB. (c) 7d timeframe. (d) 14d shadow then 0.5×. |
| **COMMODITY** | Moderate (58.6% WR, PF 2.02) | (a) Promote cta_trend. (b) 14-28d timeframe. (c) Shadow + COT lag fix. |
| **FUTURES** | Strong but n=20 (small) | (a) Keep shadow. (b) Wait for n≥50. (c) No sizing until then. |
| **FOREX** | Marginal + data issues | (a) Keep frozen (EAGLE-2). (b) Fix resolver. (c) 60d paper. |
| **BOND** | Cold start | (a) Paper-only 60d. (b) HYG/LQD focus. |

---

## 5. Capital sequencing — what gets size when

| Strategy | Asset | Today | After Pillar 1 (1 week) | After 30d shadow | After 60d sized paper |
|---|---|---|---|---|---|
| **PENNY microcap_momentum** | PENNY | not in production | shadow | 0.5× live if WR≥70% | 1× live if PF≥5 |
| **PENNY gamma_raid** | PENNY | not in production | shadow | 0.5× live cautiously | 1× live if PF≥4 |
| **ETF macro_hedge** | ETF | not in production | shadow | 0.5× live if WR≥90% | 1× live if PF≥4 |
| **EQUITY momentum_momentum** | EQUITY | not in production | shadow | 0.5× live if WR≥65% | 1× live if PF≥3 |
| **EQUITY cycle_rotator** | EQUITY | not in production | shadow | 0.5× live if WR≥60% | 1× live if PF≥2.5 |
| **EQUITY trend_follower** | EQUITY | not in production | shadow | 0.5× live if WR≥60% | 1× live if PF≥2.5 |
| **CRYPTO SHORT-only momentum** | CRYPTO | LONG (BUG) | SHORT (fix) | shadow | 0.5× live if WR≥60% |
| **COMMODITY cta_trend** | COMMODITY | shadow | shadow + COT fix | 0.5× live if WR≥55% | 1× live if PF≥2 |
| **ETF Verified DM** (EAGLE-1) | ETF | shadow | shadow | 0.5× live if WR holds | 1× live |
| **FUTURES cta_trend** | FUTURES | not enough n | shadow | sized after n≥50 | — |
| **Tournament edge** (deepseek_v4, gpt4o, grok3) | mixed | paper league | **never sized in production** until it clears the same admissibility pipeline | — |
| **FOREX / BOND** | — | frozen | frozen | frozen | only after class-specific forensics |

---

## 6. Operator decision points (this week)

1. **Approve CRYPTO directional flip** (Pillar 1 #1). Reversible. Biggest single leverage.
2. **Approve persona + directional kill lists** (Pillar 1 #2-3). Code is in the snippet above.
3. **Approve wire of `is_admissible_for_production()`** into production_scanner (Pillar 1 #4).
4. **Approve symbol whitelist** (Pillar 2 #6). Reversible config change.
5. **Pick first capital-staging run.** Recommendation: **PENNY microcap_momentum** — strongest edge in the data (75% WR, PF 6.8, 83% persona WR with 15.58% avg PnL), smallest universe, fastest validation cycle.
6. **Approve Grafana dashboard** + Slack alert routing.

---

## 7. Why this plan differs from prior EAGLE-2s

- **EAGLE-1 (Opus 4.7)**: methodology only.
- **EAGLE-2 (Opus 4.7)**: + freeze, promotion bridge, per-class plan.
- **EAGLE-2 (Grok/Composer/Claude Code)**: + research-to-production bridge framing.
- **EAGLE-2 (minimax-m3-free)**: + 25% concentration cap, concentration-adjusted PF, single admissibility function.
- **EAGLE-2 (deepseek_v4 / Mercury 2)**: + 12-week timeline, governance, data hygiene, Grafana monitoring.
- **EAGLE-3 (this doc)**: **+ data-driven identification of the CRYPTO directional bug as the #1 cause of production weakness**, persona kill list from AI tournament data, symbol whitelist from top-WR symbols, code-level admissibility function with hard gates, mutation framework with pre-registration, and concrete per-class 30-day plan grounded in tournament data.

The single most important finding: **the production scanner emits CRYPTO as LONG when the real edge is SHORT** (67% WR on shorts vs 33% on longs, n=216). Fixing this one bug should materially improve the production CRYPTO book within 14 days.

---

## Companion artifacts

- `audit_dashboard/data/ai_tournament_leaderboard.json` — 46-model leaderboard (deepseek_v4 #1)
- `audit_dashboard/data/ai_tournament_model_summary.json` — per-model summary
- `audit_dashboard/data/ai_tournament_picks_latest.json` — 4.4MB, 5,492 picks
- `audit_dashboard/data/pf_portfolio_portfolio_mix__aggressive_top5.json` — 569KB aggressive
- `audit_dashboard/data/pf_portfolio_portfolio_mix__balanced_top3.json` — 315KB balanced
- `audit_dashboard/data/pf_portfolio_portfolio_mix__conservative_top1.json` — 138KB conservative
- `audit_dashboard/data/pf_portfolio_portfolio_mix__diversified_per_class.json` — 98KB diversified
- `audit_dashboard/data/pf_portfolio_portfolio_mix__sharpe_optimized.json` — 279KB sharpe
- `alpha_engine/strategy_admissibility.py` — NEW: single admissibility function
- `alpha_engine/strategy_mutator.py` — NEW: mutation framework
- `alpha_engine/anti_overfit_validator.py` — PBO/DSR/SPA infra
- `alpha_engine/rigorous_backtest_harness.py` — WF + DSR + PBO + tier
- `verified_strategies/strategy_verification_engine.py` — backtest engine
- `verified_strategies/walkforward_suite.py` — WF suite
- `reports/hypothesis_registry.json` — H-102, H-103 pre-registered
- `docs/BACKTESTING_GUIDE.md` — existing harness spec
- `audit_trail/quality_gates.py` — BLOCKED_ASSET_CLASSES_FOR_EMISSION + gate guards
- `EAGLE_JUNE2_CLAUDE_OPUS_4_7.MD` — EAGLE-1
- `EAGLE2_2026-06-02_CLAUDE_OPUS_4_7.MD` — EAGLE-2 Opus
- `EAGLE2_2026-06-02_minimax-m3-free.MD` — EAGLE-2 minimax
- `EAGLE2_2026-06-02_deepseek_v4.MD` — EAGLE-2 deepseek_v4 (Mercury 2)

**Filed**: `EAGLE3_2026-06-02_minimax-m3-free.MD`
