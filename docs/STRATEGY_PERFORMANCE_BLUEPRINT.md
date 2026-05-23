# Strategy Performance Blueprint

**Canonical reference for locating, querying, and interpreting per-strategy and per-asset-class performance data.**

Generated: 2026-05-19 | Maintained by: agents + CI pipeline

---

## Part 1 — Strategies per Asset Class

### Asset Classes

The system tracks seven primary classes: **CRYPTO, EQUITY, FOREX, COMMODITY, FUTURES, ETF, BOND** (plus MEMECOIN and PENNY_STOCK, both fully blocked).

### Where Strategies Are Defined

| Source | Path | What it contains |
|--------|------|-----------------|
| Gate config | `audit_trail/quality_gates.py` | All gate constants, blocked pairs, score floors |
| Live stats | `alpha_engine/data/strategy_performance.json` | Per-strategy closed_picks, win_rate, profit_factor, avg_pnl |
| Dashboard system rows | `audit_dashboard/data/dashboard_data.json` → `.systems[]` | 131 source systems, each with nested `.strategies[]` rows |
| Blocked pairs | `audit_trail/quality_gates.py::BLOCKED_ASSET_STRATEGY_PAIRS` | Set of `(asset_class, strategy)` tuples that are hard-blocked |
| Permanently killed | `audit_trail/quality_gates.py::PERMANENTLY_KILLED_STRATEGIES` | Strategy names blocked across all asset classes |

### BLOCKED_ASSET_STRATEGY_PAIRS (selected entries as of 2026-05-19)

```python
# audit_trail/quality_gates.py — not exhaustive, shows pattern
BLOCKED_ASSET_STRATEGY_PAIRS = {
    ("FOREX", "MomentumEMA"),
    ("FOREX", "volume_spike_breakout"),
    ("FOREX", "myfxbook_retail_contrarian"),
    ("EQUITY", "ML Ranker"),
    ("EQUITY", "goldmine_1x_consensus"),  # and 2x/3x/4x variants
    ("CRYPTO", "goldmine_1x_consensus"),  # and 2x/3x variants
    ("CRYPTO", "MeanReversionBB"),
    ("EQUITY", "MeanReversionBB"),
    ("FUTURES", "futures_momentum"),      # H-005 escalation — WR=2%, no rescue
    ("MEMECOIN", "meme_signals"),
    ("MEMECOIN", "incubator_gainer"),
    ("CRYPTO", "super_signals"),          # n=139 WR=33% PF=0.65
    # ... 80+ additional entries
}
```

To check whether a `(class, strategy)` pair is allowed at runtime:

```python
from audit_trail.quality_gates import BLOCKED_ASSET_STRATEGY_PAIRS
assert ("CRYPTO", "MeanReversionBB") in BLOCKED_ASSET_STRATEGY_PAIRS  # True — blocked
```

### Smart-Score Floors by Asset Class

```python
# audit_trail/quality_gates.py
ASSET_CLASS_SMART_THRESHOLDS = {
    "CRYPTO":     {"min_score": 65.0, "min_fwr": 0.62, "min_trades": 10},
    "EQUITY":     {"min_score": 40.0, "min_fwr": 0.50, "min_trades": 5},
    "FOREX":      {"min_score": 40.0, "min_fwr": 0.46, "min_trades": 3},
    "COMMODITY":  {"min_score": 30.0, "min_fwr": 0.50, "min_trades": 0},
    "FUTURES":    {"min_score": 45.0, "min_fwr": 0.50, "min_trades": 0},
    "BOND":       {"min_score": 35.0, "min_fwr": 0.50, "min_trades": 0},
    "ETF":        {"min_score": 35.0, "min_fwr": 0.50, "min_trades": 0},
}
```

---

## Part 2 — Where to Find Forward WR % and Backtest Performance

### 2.1 Dashboard JSON (Canonical Source)

**File:** `audit_dashboard/data/dashboard_data.json`  
**Updated by:** CI pipeline (do NOT regenerate locally)

#### `.performance.asset_class_health` — Current live snapshot (2026-05-19)

| Asset Class | Status | n | WR % | PF | Sizing Allowed |
|-------------|--------|---|------|----|---------------|
| FOREX | stable | 144 | 57.6% | 1.64 | Yes |
| COMMODITY | candidate | 52 | 57.7% | 1.73 | No (n<100) |
| ETF | insufficient_data | 1 | 100% | — | No |
| EQUITY | insufficient_data | 5 | 20.0% | 0.25 | No |
| CRYPTO | stressed | 1087 | 44.3% | 0.63 | No |
| FUTURES | thin_sample | 12 | 16.7% | 0.96 | No |
| BOND | insufficient_data | 1 | 0.0% | 0.00 | No |

> **Note:** `asset_class_health` numbers reflect the **current active session window** only (picks that passed all gates in the current resolved batch). For cumulative historical numbers see `.performance.by_asset_class` (raw, pre-policy).

#### `.performance.by_asset_class` — Raw cumulative stats (pre-policy filter)

Each entry contains: `active`, `closed`, `wins`, `losses`, `pnl`, `win_rate`, `avg_win`, `avg_loss`, `profit_factor`, `expectancy`.

Example ETF raw: `WR=61.4%, PF=2.37, n_closed=83, avg_win=$3.09, avg_loss=$2.07`.

**Difference between views:**

| View | Policy blocks applied | Noise filter | Use for |
|------|----------------------|--------------|---------|
| `asset_class_health` | Yes | Yes (resolver v2.1) | Verdict-grade decisions, sizing gates |
| `by_asset_class` | No | No | Historical baseline, trend analysis |

#### `.systems[]` — Per-source-system rows (131 systems)

Each system object has:
- `name`, `win_rate`, `profit_factor`, `avg_pnl_pct`, `total_pnl_pct`, `max_drawdown`
- `asset_classes[]` — which classes the system emits to
- `strategies[]` — nested per-strategy breakdown with `win_rate`, `long_wr`, `short_wr`, `dsr_score`, `dsr_verdict`
- `is_blocked_aggregator`, `status`, `is_stale`

#### `.backtest_vs_forward[]` — Decay detection

Each row: `{strategy, system, bt_wr, fwd_wr, decay, bt_trades, fwd_trades}`. A `decay > 20pp` triggers a dashboard Decay Alert.

#### `.walkforward.by_class` — OOS walk-forward per class

Contains per-class: `folds`, `oos_wr`, `oos_wr_std`, `oos_sharpe`, `decay`, `consistency`, `worst_fold_wr`, `best_fold_wr`.

Example: ETF `oos_wr=65.8% ± 16.7%, consistency=100%, worst_fold=30%, best_fold=80%`.

---

### 2.2 Strategy Performance File

**File:** `alpha_engine/data/strategy_performance.json`  
**Schema:** keyed by strategy name, each entry contains:

```json
{
  "macd_crossover": {
    "closed_picks": 16,
    "win_rate": 0.6875,
    "avg_pnl": 0.0156,
    "profit_factor": 4.0943,
    "total_pnl": 0.2494,
    "distinct_symbols": 14,
    "top_symbol": "VIRTUALUSDT",
    "concentration_penalty": 0.0,
    "concentration_level": "NONE",
    "last_seen": "2026-05-19T07:18:04Z"
  }
}
```

Key fields: `closed_picks`, `win_rate` (0–1 float), `profit_factor`, `avg_pnl`, `total_pnl`, `concentration_level` (NONE/MODERATE/HIGH), `concentration_warning`.

**Notable strategies as of 2026-05-19:**

| Strategy | n | WR | PF | Concentration |
|----------|---|----|----|---------------|
| stochrsi_macd_combo | 43 | 14.0% | 5.24 | MODERATE (ONDOUSDT 30.7%) |
| macd_crossover | 16 | 68.8% | 4.09 | NONE |
| rsi_overbought | 5 | 60.0% | 2.25 | HIGH (n too small) |
| rsi_bounce | 52 | 17.3% | 1.16 | HIGH (API3USDT 235%) |
| quan_engine_scalp | 5293 | 30.0% | 0.38 | NONE |
| volume_spike_breakout | 198 | 9.6% | 0.44 | MODERATE |
| forex_rsi2_mean_reversion | 140 | 11.4% | 0.15 | MODERATE |

---

### 2.3 Closed Picks File

**File:** `alpha_engine/data/closed_picks.json`  
**Schema:** list of pick objects. Key fields per pick:

```json
{
  "strategy": "macd_crossover",
  "asset_class": "CRYPTO",
  "symbol": "VIRTUALUSDT",
  "direction": "LONG",
  "status": "WIN",
  "pnl_pct": 3.5,
  "confidence": 0.82,
  "entry_price": 1.234,
  "exit_price": 1.277,
  "created_at": "2026-05-10T14:32:00Z",
  "closed_at": "2026-05-11T09:15:00Z"
}
```

Status values: `WIN`, `LOSS`, `TP_HIT`, `SL_HIT`, `CLOSED_WIN`, `CLOSED_LOSS`, `EXPIRED`, `PHANTOM_EXPIRED`.

---

### 2.4 Walk-Forward Harness Output

**File:** `reports/walk_forward_eff_stability.json`  
Tests whether score fields are stable predictors across time. Summary categories:

- **admissible** — stable IC across folds (currently: none)
- **weak** — some predictive signal: `ml_score`, `confidence`, `risk_reward`
- **unstable** — IC varies across folds: `elite_score`, `ml_composite_score`, `method_a_score`, `forward_wr`
- **insufficient_data** — not enough data to evaluate

---

### 2.5 PF Registry

**File:** `reports/pf_registry_2026-05-17.md` (latest — JSON version not yet generated)  
Contains per `(asset_class, strategy, direction)` profit factor computed from resolved closed picks. Excludes sources in `PF_REGISTRY_POLICY_EXCLUDED` (e.g., `futures_connors_rsi2` due to dollar-scale artifact, `cta_commodity_momentum_term`).

---

### 2.6 Hypothesis Registry

**File:** `reports/hypothesis_registry.json`  
Contains 14 active hypotheses (H-001 to H-018, some archived). Schema per hypothesis:

```json
{
  "id": "H-001",
  "asset_class": "COMMODITY",
  "family": "COT_positioning",
  "description": "CFTC COT commercial-net SHORT signal predicts 14-day forward WR > 55%",
  "acceptance_criteria": {"min_wr": 0.55, "min_n": 100, "min_windows_admissible": 3},
  "status": "...",
  "result": {...},
  "kelly_fraction": 0.25
}
```

Status values: `REGISTERED`, `TESTING`, `ACCEPTED`, `FAILED_ARCHIVED`, `DEFERRED`.

---

### 2.7 MySQL Database

**Host:** `mysql.50webs.com` | **Database:** `ejaguiar1_stocks`

| Table | Key columns | Use |
|-------|-------------|-----|
| `trading_picks` | `strategy`, `category` (= asset_class), `status`, `pnl_pct`, `confidence`, `created_at` | Live + historical picks |
| `at_raw_picks` | `source_system`, `strategy`, `symbol`, `signal_score`, `emitted_at` | Raw signal stream before gating |

---

## Part 3 — How to Query by System / Symbol / Strategy

### From JSON (closed_picks.json)

```python
import json
from collections import defaultdict

picks = json.loads(open('alpha_engine/data/closed_picks.json').read())

# Filter by asset class
equity = [p for p in picks if p.get('asset_class') == 'EQUITY']

# Per-strategy WR (win status variants)
WIN_STATUSES  = {'WIN', 'TP_HIT', 'CLOSED_WIN'}
DONE_STATUSES = {'WIN', 'LOSS', 'TP_HIT', 'SL_HIT', 'CLOSED_WIN', 'CLOSED_LOSS'}

strategy_results = defaultdict(lambda: {'wins': 0, 'total': 0})
for p in picks:
    s = p.get('strategy', 'unknown')
    if p.get('status') in WIN_STATUSES:
        strategy_results[s]['wins'] += 1
    if p.get('status') in DONE_STATUSES:
        strategy_results[s]['total'] += 1

for strat, r in sorted(strategy_results.items(), key=lambda x: -x[1]['total']):
    if r['total'] >= 10:
        wr = r['wins'] / r['total'] * 100
        print(f"{strat}: {wr:.1f}% WR  (n={r['total']})")

# Per-symbol audit within a strategy
sym_results = defaultdict(lambda: {'wins': 0, 'total': 0, 'pnl': 0.0})
for p in [x for x in picks if x.get('strategy') == 'macd_crossover']:
    sym = p.get('symbol', '?')
    if p.get('status') in WIN_STATUSES:
        sym_results[sym]['wins'] += 1
    if p.get('status') in DONE_STATUSES:
        sym_results[sym]['total'] += 1
        sym_results[sym]['pnl'] += p.get('pnl_pct', 0)
```

### From strategy_performance.json

```python
import json

perf = json.loads(open('alpha_engine/data/strategy_performance.json').read())

# Top strategies by PF (min 10 closed picks)
top = [
    (name, v['profit_factor'], v['win_rate'], v['closed_picks'])
    for name, v in perf.items()
    if isinstance(v, dict) and v.get('closed_picks', 0) >= 10
]
top.sort(key=lambda x: -x[1])
for name, pf, wr, n in top[:10]:
    print(f"{name}: PF={pf:.2f}  WR={wr*100:.1f}%  n={n}")
```

### From dashboard_data.json

```python
import json

d = json.load(open('audit_dashboard/data/dashboard_data.json'))

# Asset class health summary
for cls, stats in d['performance']['asset_class_health'].items():
    print(f"{cls}: {stats['status']}  WR={stats['wr_pct']}%  PF={stats['pf']}  n={stats['n']}")

# Systems sorted by PF (min 20 resolved picks)
systems = [s for s in d['systems'] if s.get('resolved_picks', 0) >= 20]
systems.sort(key=lambda x: -(x.get('profit_factor') or 0))
for s in systems[:10]:
    print(f"{s['name']}: WR={s['win_rate']}%  PF={s['profit_factor']}  "
          f"n={s['resolved_picks']}  classes={s['asset_classes']}")

# Find all strategies for a specific asset class
crypto_strategies = set()
for s in d['systems']:
    if 'CRYPTO' in (s.get('asset_classes') or []):
        for strat in s.get('strategies', []):
            crypto_strategies.add(strat['name'])
print(f"CRYPTO strategies: {len(crypto_strategies)}")
```

### From MySQL

```sql
-- Per-strategy WR and avg PnL by asset class
SELECT
    strategy,
    category                                                        AS asset_class,
    COUNT(*)                                                        AS n,
    SUM(CASE WHEN status IN ('WIN','TP_HIT') THEN 1 ELSE 0 END)
        / COUNT(*)                                                  AS wr,
    AVG(pnl_pct)                                                    AS avg_pnl,
    SUM(CASE WHEN pnl_pct > 0 THEN pnl_pct ELSE 0 END)
        / NULLIF(ABS(SUM(CASE WHEN pnl_pct < 0 THEN pnl_pct ELSE 0 END)), 0)
                                                                    AS profit_factor
FROM trading_picks
WHERE status NOT IN ('OPEN','ACTIVE')
GROUP BY strategy, category
HAVING COUNT(*) >= 10
ORDER BY wr DESC;

-- Per-symbol breakdown for one strategy
SELECT symbol, COUNT(*) AS n,
       AVG(pnl_pct) AS avg_pnl,
       SUM(CASE WHEN status IN ('WIN','TP_HIT') THEN 1 ELSE 0 END) / COUNT(*) AS wr
FROM trading_picks
WHERE strategy = 'macd_crossover'
  AND status NOT IN ('OPEN','ACTIVE')
GROUP BY symbol
ORDER BY n DESC;

-- Recent 30-day realized WR per class
SELECT category AS asset_class,
       COUNT(*) AS n,
       SUM(CASE WHEN status IN ('WIN','TP_HIT') THEN 1 ELSE 0 END) / COUNT(*) AS wr_30d
FROM trading_picks
WHERE status NOT IN ('OPEN','ACTIVE')
  AND closed_at >= NOW() - INTERVAL 30 DAY
GROUP BY category;
```

---

## Part 4 — The Audit Dashboard

| Item | Detail |
|------|--------|
| **URL** | `findtorontoevents.ca/audit` |
| **Template** | `audit_dashboard/template.html` — **edit this**, not `index.html` |
| **Generated index** | `audit_dashboard/index.html` — auto-generated by CI, never edit directly |
| **Data file** | `audit_dashboard/data/dashboard_data.json` — updated by CI on every push |
| **Generator** | `audit_trail/dashboard_generator.py` — **do NOT run locally** (overwrites live HTML) |
| **Panels** | Asset class health, per-system leaderboard, Decay Alerts (rolling 7d WR drop >20pp), Hypothesis Registry, Walk-Forward, MONEY_READY verdict |

### Key Dashboard Fields (per-system row)

| Field | Meaning |
|-------|---------|
| `win_rate` | Forward WR % on resolved picks |
| `profit_factor` | Gross profit / gross loss |
| `avg_pnl_pct` | Average PnL per resolved pick |
| `max_drawdown` | Max peak-to-trough drawdown |
| `dsr_score` | Deflated Sharpe Ratio (1.0 = edge very likely real) |
| `dsr_verdict` | `EDGE_LIKELY_REAL` / `OVERFIT_LIKELY` |
| `is_stale` | True if no signal in last N days |
| `is_blocked_aggregator` | True if system is in BLOCKED_SOURCE_SYSTEMS |

### OBI Shadow Log

`audit_dashboard/data/obi_shadow_log.json` — tracks strategies in the "shadow" probation queue. Strategies enter shadow when WR drops below threshold; they graduate to production only after n≥10 wins with WR≥50% and PF≥1.5.

---

## Part 5 — Performance Tiers

From `reports/hedge_fund_performance_review_*.md` (PERFORMANCE_CHARTER):

| Tier | Label | PF | WR | MDD | Action |
|------|-------|----|----|-----|--------|
| T1 | Renaissance | >2.0 | >55% | <10% | Full sizing |
| T2 | Institutional | >1.5 | >50% | <20% | Standard sizing |
| T3 | Developing | >1.2 | >45% | — | Reduced sizing, monitoring |
| Below T3 | Under review | <1.2 | <45% | — | Mutate-before-kill protocol |

### Minimum n Requirements

| Threshold | n | Meaning |
|-----------|---|---------|
| `min_display_n` | 10 | Show on dashboard |
| `min_candidate_n` | 50 | Eligible for candidate status |
| `min_stable_n` | 100 | Eligible for stable status + full sizing |

### Asset Class Status as of 2026-05-19

| Class | Tier estimate | Status | Sizing | Notes |
|-------|--------------|--------|--------|-------|
| FOREX | T2 candidate | stable | Yes (144 n) | PF=1.64, WR=57.6% |
| COMMODITY | T2 candidate | candidate | No (n=52<100) | PF=1.73, WR=57.7% — lift n |
| ETF | T1 raw | insufficient_data | No | Raw: PF=2.37, WR=61.4%, n=83 — session window too small |
| EQUITY | Below T3 | insufficient_data | No | Current session window n=5 only |
| CRYPTO | Below T3 | stressed | No | PF=0.63, WR=44.3% — quan_engine_scalp drag |
| FUTURES | Below T3 | thin_sample | No | WR=16.7%, futures_momentum re-blocked |
| BOND | Insufficient | insufficient_data | No | n=1 current window |

> **Resolver note:** The `asset_class_health` numbers reflect picks resolved through `alpha_engine/outcome_resolver.py` with `PNL_WIN_THRESHOLD_BY_CLASS` (CRYPTO 0.1bp, others 5bp). Pre-resolver data lives in `by_asset_class` (raw) and should not be used for tier verdicts.

---

## Quick-Reference File Map

```
alpha_engine/data/
  strategy_performance.json     ← per-strategy live stats (WR, PF, n, concentration)
  closed_picks.json             ← resolved trades (WIN/LOSS/TP_HIT/SL_HIT + pnl_pct)
  active_picks.json             ← currently open picks

audit_dashboard/data/
  dashboard_data.json           ← CANONICAL source (131 systems, per-class health, BvF)
  obi_shadow_log.json           ← shadow probation tracker

audit_trail/
  quality_gates.py              ← BLOCKED_ASSET_STRATEGY_PAIRS, score floors, kill lists
  dashboard_generator.py        ← DO NOT run locally

reports/
  hypothesis_registry.json      ← H-001..H-018 formal hypothesis tests
  walk_forward_eff_stability.json ← score-field IC stability across time folds
  pf_registry_2026-05-17.md    ← per (class, strategy, direction) PF from closed picks
  deep_dive_<class>_*.md        ← per-class autopsy reports (spawn when PF<1)

MySQL ejaguiar1_stocks @ mysql.50webs.com
  trading_picks                 ← full pick ledger with confidence, strategy, pnl_pct
  at_raw_picks                  ← raw signal stream pre-gating
```
