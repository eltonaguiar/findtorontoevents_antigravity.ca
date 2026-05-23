# Cursor Changes Blueprint

**Created:** 2026-03-01  
**Scope:** Strategy graveyard, negative-EV exclusion, new strategies, forward-performance stats

---

## 1. Context

- System ROI was ~0.9% with 34% win rate; many strategies have **negative expected value (EV)**.
- Kelly Criterion audit identified ~100 of 151 strategies as negative-Kelly (graveyard candidates).
- Goal: keep graveyarded strategies in the codebase for research and duplicate-avoidance, but **exclude them from all live picks**; add new high-EV strategies and track forward performance by strategy and bucket.

---

## 2. Current State (As of 2026-03-01)

| Component | Status |
|-----------|--------|
| **Graveyard list** | `stabilization/disabled_strategies.json` → `graveyard` array (72 names) + `graveyard_metadata` |
| **Kelly audit** | `tmp/identify_graveyard.py` → `tmp/kelly_audit_results.json`; `tmp/build_graveyard.py` writes graveyard into disabled file |
| **Picks exclusion** | `alpha_engine/strategy_guard.py` uses `disabled` list; `generate_baby_strats_dashboard.py` excludes disabled when building dashboard |
| **Docs** | `baby_strategies/STRATEGY_GRAVEYARD.md` and `baby_strategies/BABY_STRATEGY_GEN_PROMPT.md` describe graveyard semantics |
| **Research** | `tmp/DEEP_STRATEGY_RESEARCH_2026.md` (527 lines, 30+ sources); updates at https://findtorontoevents.ca/updates/ |

---

## 3. Changes Blueprint

### 3.1 Graveyard & Exclusion (Done / Verify)

- [ ] **Verify** `get_disabled_strategies()` in `strategy_guard.py` uses the full `disabled` list (which includes graveyard).
- [ ] **Optional:** Add `is_graveyarded(name)` helper that checks `graveyard` array; use in tooling or dashboards to label "graveyard" vs "phase1 cull".
- [ ] **No new code required** for exclusion — graveyard names are already in `disabled`; guard and dashboard already respect it.

### 3.2 Documentation (Done / Minor Edits)

- [ ] **Confirm** `baby_strategies/STRATEGY_GRAVEYARD.md` is the single source of truth for "what the graveyard flag means" and that it’s linked from `BABY_STRATEGY_GEN_PROMPT.md` and any other baby .md files as needed.
- [ ] **Optional:** Add a short "Strategy lifecycle" section in `BABY_BUNDLE_GUIDE.md` or `BABY_BUNDLE_REGISTRY.md`: active → disabled → graveyard, with link to `STRATEGY_GRAVEYARD.md`.

### 3.3 New Strategies (To Implement)

| Strategy | Source / Location | Action |
|----------|-------------------|--------|
| **Funding rate arbitrage** | `alpha_engine/funding_rate_scanner.py`, `funding_arb_backtest.py` | Wire scanner’s BUY signals into central live-picks pipeline; register as strategy bucket "Funding Arb"; ensure forward trades are recorded. |
| **Grid trading** | No full implementation yet | New module: grid bounds from range/BB; record each fill as forward trade; bucket "Grid – range income". |
| **Risk-managed momentum (28d/5d)** | `alpha_engine/quant_strategies.py` (TSMOM, blended mom+MR) | Add 28d lookback / 5d hold + vol-scaled TSMOM; feed signals into same live-picks + forward-stats pipeline; bucket "Directional – risk-managed momentum". |

### 3.4 Forward-Performance Stats (To Implement)

- [ ] **Aggregator script** (e.g. `tools/forward_buckets_aggregator.py` or under `battleground/`):
  - Input: closed forward trades from existing logs (e.g. `baby_strats_dashboard` forward_trades, bundle_trades, alpha closed picks).
  - Compute per **strategy**: win rate, avg win, avg loss, EV per trade, Kelly%, max DD, trade count.
  - Compute per **bucket**: same metrics aggregated by strategy type (e.g. funding_arb, grid, momentum, mean_reversion_bundle).
  - Output: e.g. `battleground/data/forward_buckets_dashboard.json` and/or a small markdown report.
- [ ] **Run periodically** (cron or post-close hook) so the dashboard reflects latest forward results and graveyard theory can be validated.

### 3.5 Extra Research Rounds (Optional)

- [ ] **10 rounds** of focused checks (e.g. funding arb across exchanges/regimes, grid in chop vs trend, 28d/5d OOS decay) and append summary to `tmp/DEEP_STRATEGY_RESEARCH_2026.md` or a sibling file.

---

## 4. File Touch List

| File | Change |
|------|--------|
| `alpha_engine/strategy_guard.py` | Optional: add `is_graveyarded()`; ensure path to `disabled_strategies.json` is robust. |
| `baby_strategies/STRATEGY_GRAVEYARD.md` | No change unless expanding "lifecycle" or adding links. |
| `baby_strategies/BABY_STRATEGY_GEN_PROMPT.md` | No change; already references graveyard. |
| `BABY_BUNDLE_GUIDE.md` or `BABY_BUNDLE_REGISTRY.md` | Optional: add "Strategy lifecycle" + link to STRATEGY_GRAVEYARD.md. |
| New: grid module | Implement grid logic + forward-trade logging. |
| `alpha_engine/quant_strategies.py` | Add 28d/5d risk-managed TSMOM; optional: register in scanner. |
| `alpha_engine/funding_rate_scanner.py` | Wire output into central live-picks tracker. |
| New: forward aggregator | Implement `forward_buckets_aggregator` (or equivalent) and output JSON/MD. |

---

## 5. Success Criteria

- Graveyarded strategies never generate live picks; code and research remain available.
- New strategies (funding arb, grid, risk-managed momentum) are in the pipeline and assigned to buckets.
- Forward-performance stats exist per strategy and per bucket, updated on a defined schedule.
- One canonical doc (`STRATEGY_GRAVEYARD.md`) explains the graveyard flag; other .md files point to it where relevant.
