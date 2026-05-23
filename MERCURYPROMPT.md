# Mercury / IDE Agent Prompt Guide

**Last updated:** 2026-04-14 1:13 AM EDT

This document tells external AI agents (Mercury, DeepSeek, Gemini, GPT, or any IDE agent) exactly what to look at, what NOT to do, and how to produce useful output for this codebase.

---

## STOP — Read This Before Generating Any Code

**This is NOT a standard codebase.** It does NOT have `src/strategy/`, `src/models/`, or `config.yaml`. Those paths are fictional. Do NOT hallucinate file paths. Do NOT propose rebuilding infrastructure that already exists.

**Before writing any code, search the actual repo.** The structure is:

```
/workspace/
├── alpha_engine/          ← Core trading engine (658 Python files)
│   ├── scanner.py         ← Main live scanner (~4400 lines)
│   ├── elite_scorer.py    ← Score computation (~2500 lines)
│   ├── ml_ranker.py       ← ML signal ranking
│   ├── tp_sl_filler.py    ← TP/SL computation (ATR-based)
│   ├── position_sizing.py ← Kelly + risk-based sizing
│   ├── risk_controls.py   ← Circuit breakers, daily limits
│   ├── config.py          ← Symbol universes, constants
│   └── data/              ← JSON pick files (active, closed)
├── audit_trail/
│   ├── quality_gates.py   ← Quality filtering (Smart Picks, Active gates)
│   └── dashboard_generator.py ← Builds the audit dashboard payload
├── audit_dashboard/
│   ├── template.html      ← Dashboard UI (source of truth — edit THIS, not index.html)
│   ├── index.html         ← Auto-generated from template.html
│   └── data/dashboard_data.json ← Canonical pick data
├── copy_trader_intel/     ← External signal scrapers (OKX, Bybit, Hyperliquid, etc.)
├── baby_strategies/       ← New strategy experiments (not wired to live)
└── docs/                  ← Analysis reports from this audit session
```

---

## How to Get Useful Output from Mercury

### DO ask Mercury for:

1. **Statistical validation code** — bootstrap CI, permutation tests, Wilson intervals. But tell it to operate on OUR data files, not synthetic data.
2. **Specific metric computations** — "Compute Sortino ratio from `audit_dashboard/data/dashboard_data.json` → `picks.recent_closed`"
3. **Code review of specific files** — "Review `audit_trail/quality_gates.py` lines 195-500 for score threshold calibration issues"
4. **Algorithm implementations** — "Implement isotonic regression calibration that reads from `alpha_engine/data/closed_picks.json`"

### DO NOT let Mercury:

1. **Generate synthetic data** — Any `np.random.seed(42)` + fake OHLCV = useless
2. **Propose new file layouts** — `src/strategy/decision.py`, `src/models/__init__.py` etc. don't exist
3. **Build portfolio optimizers** — This system generates individual picks with TP/SL, not portfolio weights
4. **Dump generic frameworks** — We need fixes to specific files, not 500-line boilerplate scripts

### Template prompt for Mercury:

```
You are reviewing a multi-asset prediction system at github.com/eltonaguiar/findtorontoevents_antigravity.ca

DO NOT generate synthetic data or propose new file structures.
DO NOT build portfolio optimization code — this system generates individual picks with TP/SL targets.

The canonical data file is: audit_dashboard/data/dashboard_data.json → picks.recent_closed (3,500 picks)
The quality gate code is: audit_trail/quality_gates.py
The dashboard template is: audit_dashboard/template.html (edit THIS, not index.html)

TASK: [your specific ask here]

When computing performance:
- Use ALL picks (no "definitive exit" cherry-picking)
- Report PF, WR, and bootstrap 95% CI
- State which data file and which picks you used
```

---

## Prompt for Other IDE Agents (Claude, Cursor, Gemini, etc.)

```
You are auditing a multi-asset trading prediction system.

CRITICAL RULES:
1. The canonical data source is: audit_dashboard/data/dashboard_data.json → picks.recent_closed
   - DO NOT use alpha_engine/data/closed_picks.json for system-wide analysis (it's 82% quan_engine_scalp)
   - DO NOT use audit_trail/data/universal_resolved_picks.json without stating you did
   - ALWAYS state which file you're reading in your first output line
2. Use ALL PICKS for WR/PF — do NOT filter to "definitive exits only" without disclosing it
   - "LOST" exits are NOT equivalent to SL_HIT (see Issue #186)
   - 22.9% of picks are TIME_EXIT — include them in honest metrics
3. Confidence (pick field "confidence") has Cohen's d = 0.011 — it does NOT predict outcomes
4. trust_score and strat_fwd_wr ARE predictive (d=0.33 and d=0.54 respectively)

KEY FILES TO REVIEW:

Performance data:
  audit_dashboard/data/dashboard_data.json     ← Canonical (3,500 picks, multi-source, labeled)
  audit_trail/data/universal_resolved_picks.json ← Alternative (4,282 picks, cleaner exits)
  alpha_engine/data/closed_picks.json          ← Alpha engine only (4,157 picks, 82% one strategy)

Quality gate code:
  audit_trail/quality_gates.py                 ← ALL filtering logic
    - passes_active_gate()    → Controls Active Picks tab visibility
    - passes_smart_gate()     → Controls Smart Picks tab visibility  
    - BLOCKED_SOURCE_SYSTEMS  → Hard-blocked systems (line ~839)
    - BLOCKED_STRATEGIES      → Per-strategy blocks (line ~879)
    - SMART_PICKS_MIN_SCORE   → Score floor per asset class (line ~197)
    - SMART_PICKS_MIN_TRUST_SCORE → Trust floor (line ~487)
    - SMART_PICKS_CRYPTO_LONG_ONLY → Crypto direction gate (line ~505)

Scoring:
  alpha_engine/elite_scorer.py                 ← Score computation (score, elite_score, method_a_score)
  alpha_engine/trust_score.py                  ← Trust score (0-10, entry-time, no lookahead)
  alpha_engine/ml_ranker.py                    ← ML signal ranking (WARNING: 39 vs 41 feature bug)

TP/SL:
  alpha_engine/tp_sl_filler.py                 ← ATR-based TP/SL with per-asset-class caps
  alpha_engine/adaptive_tp_sl.py               ← TP/SL optimizer (WARNING: calibrates on wrong dataset)

Dashboard:
  audit_dashboard/template.html                ← UI source of truth (NOT index.html)
  audit_trail/dashboard_generator.py           ← Builds payload from 30+ JSON sources

Strategy code:
  alpha_engine/scanner.py                      ← Main scanner (imports all strategies)
  alpha_engine/config.py                       ← CRYPTO_SYMBOLS, DEFAULT_UNIVERSE
  baby_strategies/                             ← New experiments (check .meta.json for wired_in_scanner)

Live site: https://findtorontoevents.ca/audit/
  - Overview tab: Asset class breakdown, system leaderboard
  - Active Picks tab: Current open positions (filtered by passes_active_gate)
  - Smart Picks tab: High-quality subset (filtered by passes_smart_gate)
  - Closed Picks tab: Historical performance
  - "High Conviction" chip: Score≥60 + Trust≥5
  - Asset class dropdown: Filter by CRYPTO/EQUITY/FOREX/COMMODITY/etc.
```

---

## Current Edge by Asset Class (as of 2026-04-14)

### Verified edges (all-picks denominator, honest metrics)

| Asset | Best Filter | N | WR | PF | PF CI Lower | Beats Random? |
|-------|-----------|---|-----|-----|------------|-------------|
| **CRYPTO** | Score≥50 + Trust≥3 | 689 | 55.2% | 1.98 | 1.53 | ✅ Yes |
| **EQUITY** | Score≥50 + Trust≥3 | 119 | 65.5% | 2.62 | 1.75 | ✅ Yes |
| **FOREX** | FwdWR≥50 | 466 | 49.8% | 1.62 | 1.05 | ✅ Yes |
| **COMMODITY** | Trust≥3 | 273 | 42.1% | 1.28 | 0.84 | ❌ Inconclusive |
| BOND | — | 8 | 50.0% | 25.9 | — | n too small |
| ETF | — | 19 | 42.1% | 0.28 | — | ❌ Dead |
| FUTURES | — | 17 | 5.9% | 0.06 | — | ❌ Dead |

### How to verify on the live dashboard

1. Go to `https://findtorontoevents.ca/audit/`
2. Click **Closed Picks** tab
3. Use the asset class dropdown to select CRYPTO/EQUITY/FOREX
4. The **Smart Picks** tab applies the quality gate from `passes_smart_gate()` in `quality_gates.py`
5. The **"High Conviction"** chip applies Score≥60 + Trust≥5 (stricter than Smart Picks)
6. For the validated edge: manually check picks with Trust≥3 and Score≥50

### How to verify in code

```python
import json

with open('audit_dashboard/data/dashboard_data.json') as f:
    dd = json.load(f)
closed = dd['picks']['recent_closed']

# Apply the validated compound filter
crypto_filtered = [p for p in closed 
    if (p.get('asset_class') or '').upper() == 'CRYPTO'
    and float(p.get('score') or 0) >= 50
    and float(p.get('trust_score') or 0) >= 3]

# Compute PF
pnls = [float(p.get('pnl_pct') or 0) for p in crypto_filtered]
gw = sum(x for x in pnls if x > 0)
gl = abs(sum(x for x in pnls if x <= 0))
pf = gw / gl if gl > 0 else 99
wr = sum(1 for x in pnls if x > 0) / len(pnls) * 100
print(f"Crypto Score≥50+Trust≥3: n={len(pnls)}, WR={wr:.1f}%, PF={pf:.2f}")
```

---

## Edge Determination Upgrades — Beyond PF+WR (added 2026-04-14 late)

PF and Wilson WR CI are the minimum bar. For "hedge-fund grade edge" claims, the following are also required. Each closes a specific failure mode that PF-alone analysis misses.

### 1. Risk-adjusted metrics (not just PF)

| Metric | Formula | Threshold for "good" | Why it matters |
|---|---|---|---|
| **Sharpe** | annualized mean excess return ÷ annualized volatility | ≥ 1.0 acceptable, ≥ 2.0 elite | A strategy with PF 1.5 and 50% max drawdown is worse than PF 1.3 with 10% DD. PF cannot tell you this. |
| **Sortino** | like Sharpe but only counts downside volatility | ≥ 1.5 | Penalizes left-tail risk specifically — matters for capital preservation. |
| **Max Drawdown** | largest peak-to-trough equity drop on the pick-by-pick equity curve | ≤ 20% ideally, ≤ 15% elite | The single most important survival metric. A strategy with DD > 30% cannot be traded with realistic size. |
| **Calmar** | annualized return ÷ max DD | ≥ 3.0 | Pairs return with drawdown — high Calmar = recovers quickly from losses. |

**Required output shape for any PF claim:**
```
n=X, WR=X% [Wilson CI], PF=X [bootstrap CI], Sharpe=X, Sortino=X, MaxDD=X%, Calmar=X
```

Not just `PF=X`.

### 2. Multiple-testing correction

If you test 100 strategies at p < 0.05 significance, **~5 will pass by chance alone**. With 189 baby_strats in this repo, you need either:

- **Bonferroni**: multiply raw p-values by number of tests (conservative — use for headline claims)
- **Benjamini-Hochberg FDR**: control the false discovery rate at e.g. 5% (more powerful — use for screening)

```python
# Example: Bonferroni-adjusted significance for N tests
from scipy import stats
import statsmodels.stats.multitest as mt
p_values = [compute_p_value(strat) for strat in strategies]
reject, p_corrected, _, _ = mt.multipletests(p_values, method='fdr_bh', alpha=0.05)
winners = [s for s, r in zip(strategies, reject) if r]
```

**Rule:** a single strategy claim at p < 0.05 is NOT evidence of edge when you scanned 100+ strategies to find it. Either pre-register the hypothesis OR apply FDR correction.

### 3. Fee / slippage haircut scenario (mandatory)

Paper PF ≠ realistic net PF. The fee scenarios you should always compute:

| Asset | Round-trip cost assumption | Why |
|---|---|---|
| Crypto | **10-20 bps** | Binance maker+taker + funding on perps + spread |
| Equity | **5-10 bps** | Commission + half-spread on liquid large-caps, wider for mid/small |
| Forex | **1-3 bps** | Retail spread + commission; tighter on majors, wider on crosses |
| Commodity futures | **5-15 bps** | Commission + half-spread, varies by contract |
| ETF | **5-10 bps** | Same as equity + creation/redemption spread |

```python
def net_pf(picks, fee_bps):
    fee_pct = fee_bps / 100.0  # bps → percent
    haircut = [float(p.get('pnl_pct', 0)) - fee_pct for p in picks]
    gw = sum(x for x in haircut if x > 0)
    gl = sum(-x for x in haircut if x < 0)
    return gw / gl if gl > 0 else float('inf')

# Required output alongside gross PF
print(f"Gross PF: {gross_pf:.2f} | Net @10bps: {net_pf(picks, 10):.2f} | Net @20bps: {net_pf(picks, 20):.2f}")
```

A strategy that looks like gross PF 1.5 often becomes net PF 1.1 at 10bps, or net PF 0.85 at 20bps. Do not claim "edge" without disclosing the fee scenario.

### 4. Stationarity / regime-dependence check

Split the sample into halves (or thirds). Report PF for each window. If PF in the newest window is materially worse than the oldest, the "edge" may be a stale regime fit.

```python
def half_split_pf(picks_sorted_by_time):
    half = len(picks_sorted_by_time) // 2
    first, second = picks_sorted_by_time[:half], picks_sorted_by_time[half:]
    return pf_of(first), pf_of(second)
```

**Rule:** if `second_half_pf < 0.7 * first_half_pf`, flag the strategy as "decaying — do not promote based on full-sample stats alone".

This is how we caught the 19 decaying baby_strats in the April 14 audit. Mature-forward strategies with big bt→fwd drops were all positive on their backtest window and all negative recent — they'd pass a naive full-sample PF check.

### 5. Permutation null distribution (the gold standard)

PF CI from bootstrap tells you "how uncertain is our estimate of this strategy's PF". A permutation test tells you "is this PF distinguishable from random entry timing at all". Under the null (random timing), PF should cluster around 1.0 — observed PF significantly above that distribution is real edge.

```python
import random
def permutation_p_value(pnls, n_perms=1000, seed=42):
    observed_pf = pf_of(pnls)
    rng = random.Random(seed)
    null_pfs = []
    for _ in range(n_perms):
        shuffled = [rng.choice(pnls) for _ in pnls]  # resample with replacement
        null_pfs.append(pf_of(shuffled))
    # fraction of null PFs >= observed
    return sum(1 for x in null_pfs if x >= observed_pf) / n_perms
```

**Rule:** a permutation p < 0.05 is required to claim edge beyond random-entry baseline. Combine with FDR correction above for multi-strategy screens.

### 6. Cluster-aware sample size

If a strategy fires 50 picks on the same symbol within 1 hour, the effective n is NOT 50 — it's closer to 1-5 because the outcomes are highly correlated (same underlying move). Treating them as independent picks inflates the sample size and deflates the CI width.

**Simple cluster-penalty heuristic:** de-dupe picks to at most 1 per (symbol, hour) bucket before computing WR/PF. For strategies that fire bursts on confluence events (e.g., news spikes, session opens), this can cut effective n by 70-90%.

**Rule for high-volume strategies:** report both raw-n and de-clustered-n stats. If the de-clustered PF is > 20% lower than raw PF, the strategy is over-counting correlated picks and any statistical claim needs the de-clustered version.

### 7. Entry-time snapshot rule (generalized lookahead prevention)

The existing MERCURYPROMPT.md warns about `trust_score` lookahead specifically. Generalize this to all features read on closed picks:

> **Rule:** any feature used for filtering or edge attribution on a closed pick must be captured at entry time and NOT refreshed at dashboard-generation or read time.

Features currently safe (computed at entry + persisted):
- `entry_price`, `take_profit`, `stop_loss`, `direction`, `symbol`, `strategy`
- `score`, `elite_score`, `confidence` (per scanner output)
- `regime_at_entry` (though currently 0% populated — known bug)

Features currently UNSAFE (refreshed at dashboard gen time):
- `trust_score.track_record` (3 of 10 points, via `enrich_picks_with_trust_score`) — see `audit_trail/dashboard_generator.py:10886`
- `strat_fwd_wr`, `forward_wr` — back-filled from current strategy_performance.json
- `forward_trades`, `strat_fwd_trades`

If you use any UNSAFE feature in a filter, expect backtest PF to be **20-40% higher** than live-forward PF. Calibrate accordingly.

### 8. Required output template for any edge claim

Any agent reporting "strategy X has edge on asset class Y" should produce this block:

```
Strategy: <name>
Asset class: <CRYPTO|EQUITY|FOREX|COMMODITY|BOND|ETF|FUTURES>
Data source: <file path>
Filter applied: <exact predicate>
Date range: <start> to <end>

Sample:  n=<raw>, de-clustered n=<effective>
WR:      <wr%> [Wilson 95% CI: lo%, hi%]
PF (gross):  <pf> [bootstrap 95% CI: lo, hi]
PF (net, 10bps):  <pf>
PF (net, 20bps):  <pf>
Sharpe:  <value> (annualized)
Sortino: <value>
Max DD:  <pct>
Calmar:  <value>
Half-split PF: first=<pf1>, second=<pf2>, decay=<delta>
Permutation p-value (n=1000): <p>
Multi-test adjusted p (FDR): <p_adj>

Edge verdict: [REAL / BORDERLINE / NOT REPRODUCIBLE / FAIL]
Reasoning: <one line>
```

If any field is missing or cannot be computed (e.g., n too small for bootstrap), explicitly say so instead of omitting.

---

## Known Bugs (as of 2026-04-14)

| Bug | Location | Severity | Status |
|-----|----------|----------|--------|
| Train-serve feature misalignment (39 vs 41) | `alpha_engine/ml_ranker.py` L359-422, L2462-2473 | 🔴 Critical | Open |
| `ml_score` is 0% populated on closed picks | `alpha_engine/scanner.py` | 🔴 Critical | Open |
| `adaptive_tp_sl.py` calibrates on wrong dataset | `alpha_engine/adaptive_tp_sl.py` | 🟡 Medium | Open (Issue #186) |
| LOST exits are binary outcome labels, not exit reasons | `audit_trail/dashboard_generator.py:5139` | 🟡 Medium | Issue #186 filed |
| `regime_at_entry` is 0% populated | `alpha_engine/scanner.py` | 🟡 Medium | Open |
| `is_daily_blocked()` returns False always | `alpha_engine/risk_controls.py` | 🟡 Medium | Open |
| Confidence doesn't predict outcomes (d=0.011) | `alpha_engine/model_calibration.py` | 🟡 Medium | Documented |
| 232 unique exit_reason labels (needs normalization) | Various | 🟡 Medium | Open |

---

## Analysis Reports from This Session

All in `/workspace/docs/`:

| File | Topic |
|------|-------|
| `SESSION_SUMMARY_AND_GAMEPLAN_2026-04-13.md` | Master gameplan with 4-phase roadmap |
| `ROOT_CAUSE_NEGATIVE_EXPECTANCY_2026-04-14.md` | 4 root causes + TIME_EXIT contamination |
| `DATA_SOURCE_RECONCILIATION_2026-04-14.md` | Why 3 data sources contradict |
| `PER_ASSET_CLASS_AUDIT_2026-04-14.md` | Per-asset diagnostic with corrections |
| `NON_CRYPTO_IMPROVEMENTS_2026-04-14.md` | Strategy blocks + forex changes |
| `TP_POSTPROCESSOR_AND_EARNINGS_AUDIT_2026-04-14.md` | TP tiered exits (rejected) + Earnings Drift inverse |
| `DNA_MUTATION_WINNERS_2026-04-14.md` | Winner mutations for low-volume strategies |
| `strategy_audits/stocks_competition_2026-04-14.md` | Kill-ritual investigation |

---

## What Mercury's Frameworks ARE Good For (Future Phase)

After the bugs above are fixed (especially ml_score population and feature alignment), Mercury's statistical frameworks become useful:

- **Bootstrap CI and permutation tests** → for promotion gate validation
- **SHAP importance ranking** → for incubator feature selection
- **Walk-forward with turnover controls** → for strategy validation
- **Cross-asset correlation features** → for diversification

But NOT until the foundation is solid. Building ML optimization on top of broken features is waste.

---

*For questions about this guide, check the Redis bus broadcasts or ping in the repo issues.*
