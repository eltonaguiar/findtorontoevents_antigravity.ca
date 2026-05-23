# Hedge-Fund Libraries — Leverage Audit & Wiring Plan

**Date:** 2026-04-22
**Question:** Have we actually leveraged the 20+ hedge-fund library integrations peer agents built over the last 48h? Are any of them improving picks quality?
**Short answer:** **No.** 20 of 21 modules are orphans — zero production callers. The scoring path (`calculate_smart_score`) is still entirely hand-tuned and has never imported any hedge lib.

## 1. Measured orphan rate

| Module | Callers in prod pick code |
|---|---|
| `alpha_engine/mlfinlab_integration.py` | **0** (orphan) |
| `alpha_engine/bt_integration.py` | **0** |
| `alpha_engine/flaml_integration.py` | **0** |
| `alpha_engine/pyod_integration.py` | **0** |
| `alpha_engine/skfolio_integration.py` | **0** |
| `alpha_engine/skforecast_integration.py` | **0** |
| `alpha_engine/interpret_integration.py` | **0** |
| `alpha_engine/imbalanced_learn_integration.py` | **0** |
| `alpha_engine/feature_engine_integration.py` | **0** |
| `alpha_engine/purged_cv_core.py` | **0** |
| `alpha_engine/fingpt_sentiment.py` | **0** |
| `alpha_engine/dynamic_universe.py` | **0** |
| `alpha_engine/market_making.py` | **0** |
| `alpha_engine/hifi_backtest.py` | **0** |
| `alpha_engine/multi_exchange_executor.py` | **0** |
| `alpha_engine/finrl_agent.py` | **0** |
| `alpha_engine/vectorized_backtest.py` | **0** |
| `alpha_engine/catalyst_filter.py` | **0** (branch-only) |
| `alpha_engine/drift_aware_scoring.py` | **0** (branch-only) |
| `alpha_engine/meta_labeler.py` | 1 (forward_validator — measurement, not scoring) |
| `alpha_engine/macro_data_pipeline.py` | 1 (standalone refresh script) |
| `tools/triple_barrier_labeler.py` (PR #301) | 0 (pending merge) |
| `tools/risk_metrics.py` (PR #301) | 0 (pending merge) |
| `tools/risk_parity_allocator.py` (PR #301) | 0 |
| `tools/meta_labeler.py` (PR #301) | 0 |

**`audit_trail/quality_gates.calculate_smart_score()` — the actual ranker that produces `smart_picks_count`** — imports none of them. It uses 7 hand-tuned components (base 30, R:R 15, track record 15, trust 12, confidence 10, technical 10, consensus 8).

## 2. The four highest-leverage wire-ups

These would measurably improve picks quality, ordered by impact per hour of work:

### 🔴 #1 — Wire `catalyst_filter.py` as an equity pick pre-filter

**Where:** `audit_trail/dashboard_generator.py` near line 13397 (`if not passes_smart_gate(pick): continue`).

**Change:** Add before `passes_smart_gate` for EQUITY/ETF asset classes:

```python
from alpha_engine.catalyst_filter import hours_to_earnings
if pick.get("asset_class") in ("EQUITY", "ETF", "STOCKS"):
    hrs = hours_to_earnings(pick["symbol"])
    if hrs is not None and 0 < hrs < 72:
        pick["_catalyst_block"] = f"earnings_in_{hrs:.1f}h"
        continue  # skip smart-picks surface, keep in active book
```

**Why:** We've been blind-sided by earnings on equity picks. OpenBB earnings calendar closes that hole. `catalyst_filter` smoke-tested against 5 symbols (commit `274f6318a9` on `feat/ship-week-integrations-2026-04-21`) — works with FMP → yfinance fallback. Currently orphan because its branch hasn't merged.

**Effort:** 10 min to write, 1-hour shadow period to compare smart-pick lists.

### 🟠 #2 — Wire `drift_aware_scoring.apply_drift_conservatism` as a scoring multiplier

**Where:** `calculate_smart_score` in `quality_gates.py:4337`. After computing `score`, multiply by a drift factor.

**Change:**
```python
# Near end of calculate_smart_score, before return:
from alpha_engine.drift_aware_scoring import apply_drift_conservatism, detect_simple_drift
source = str(pick.get("source_system", "")).lower()
recent_drift = _get_cached_source_drift_severity(source)  # new helper, reads drift_demo output
adjusted = apply_drift_conservatism({"confidence": score / 100}, recent_drift)
score = adjusted["confidence"] * 100
```

**Why:** `drift_demo` already found `copy_trader_highscore` and `copy_trader_intel` flipped `urgent_retrain` last 7d. If wired, those sources' smart-score would auto-halve (×0.5) until drift resolves. Currently they're scoring full weight.

**Effort:** 1-2 hours (needs a cached drift lookup; `drift_demo.py` writes the data once nightly).

### 🟡 #3 — Replace crude trust-tier component with `risk_metrics.psr`

**Where:** `calculate_smart_score` trust-tier block (currently +12 pts if trust>=6).

**Change:** Use Probabilistic Sharpe Ratio of the source system's last 100 closed trades instead of the binary trust flag.

**Why:** Trust tier is a step function (6→12pts, 7→12pts — no gradient). PSR is continuous and directly measures "how likely this is skill not luck." `tools/risk_metrics.py` (PR #301) computes PSR for a return series. Swap via an adapter that loads the source's recent PnL history once per run.

**Effort:** 2-3 hours including caching + PR #301 merge dependency.

### 🟢 #4 — `triple_barrier_labeler` pre-merge gate on forward_wr numbers

**Where:** `alpha_engine/forward_validator.py` (where `strat_fwd_wr` gets computed).

**Change:** Reclassify closed picks through `tools/triple_barrier_labeler.py`'s WIN/LOSS/TIMEOUT rather than the current +1bp threshold. Fixes the FLAT_CLOSE_BUG at source.

**Why:** PR #301 analysis found 20% of non-crypto picks are miscounted as neither WIN nor LOSS. Fixing at source cleans `strat_fwd_wr` which feeds `calculate_smart_score` via R:R and track-record components.

**Effort:** 3-4 hours. Gated on PR #301 merge and `outcome_resolver.py` co-fix.

## 3. What I am NOT recommending

- **Wholesale mlfinlab/skfolio/feature_engine adoption.** These are heavy research libs. Value comes from specific concepts (purged CV, HRP allocator, fractional differencing), not from importing the whole surface.
- **`market_making`, `multi_exchange_executor`** — wrong domain. We use TV paper, not live exchange routing.
- **`finrl_agent`** — RL for HC-threshold tuning only, not for trade picks directly. Deferred until #1-#4 land.
- **`hifi_backtest`** — TV paper has zero slippage so a fill model would "improve" realism by downgrading measured edge; useful only for pre-promotion validation, not live scoring.

## 4. Measured baseline (before any of this lands)

- `alpha_engine/data/active_picks.json`: 90 picks → 52 pass active gate (post PR #325, was 14)
- `audit_dashboard/data/dashboard_data.json` `smart_picks: 0` (empty — pipeline issue separate from active gate)
- Zero hedge-lib imports in any scoring path

## 5. If you want to proceed

Order of merge to get picks-quality lift:

1. **PR #320** (clone-placeholder fix) — removes 35 noisy placeholder picks
2. **PR #301** (hedge-fund gap-filler tools) — lands risk_metrics + triple_barrier + meta_labeler + risk_parity
3. **Merge my `catalyst_filter.py` and `drift_aware_scoring.py` branches to main** — unblocks #1 and #2 above
4. **Write the 4 wire-ups** above, each as its own focused PR with shadow-period measurement before enforce

Total effort to actually leverage what's been built: ~8-12 hours of careful integration work. Estimated impact: +5-10 pp smart-picks WR via catalyst filtering + drift sizing. PSR replacement is higher-ceiling but needs a few weeks of data to tune.

## 6. Why this happened

Peer agents prioritized breadth ("11 modules + 57 tests!") over wiring depth. The default completion bar was "module importable + tests pass" — which triggers "mission accomplished" claims — without the follow-through step that would actually touch the live scoring pipeline. This audit is the first time anyone has measured callers.

Recommendation in one line: **no new integration modules until the existing 20 orphans are either wired or deleted**.
