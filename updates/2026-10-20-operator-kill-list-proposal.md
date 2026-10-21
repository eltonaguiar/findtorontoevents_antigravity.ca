# Operator Kill-List Proposal (mutation-before-kill)

**Date:** 2026-10-20
**Status:** PROPOSED — for operator approval. **No blocklist mutation applied.** Applied only after operator signs off via the mutation-before-kill protocol.
**Source of kill list:** `/audit/data/dashboard_data.json` generated 2026-10-19 20:41 ET (last 3,500 closed rows). Operator-proposed; 54 items → 53 after removing ETF `rs-breakout-scout` (n=66, PF=1.71, kept for forward test).

---

## 1. Verification precondition (done)

- `.env.example` and `tools/deploy_updates_v05.py` restored from `stash@{1}` — confirmed modified and unstaged (` M`).
- Canonical config consulted **only**: `alpha_engine/strategy_blocklist.py` (`_RETIRED_STRATEGIES`, `_RETIRED_SYSTEM_STRATEGY_PAIRS`, `_PAPER_ONLY_STRATEGIES`, `is_blocked_strategy`, `is_blocked_pick`, `_pair_is_blocked`) and `alpha_engine/config.py::BLACKLISTED_STRATEGIES` + kill-switch registries (`fx_kill_switch`, `commodity_kill_switch`).

---

## 2. Key architectural finding — NO class-scoped kill mechanism exists

The canonical blocklist is **global strategy-name based**:

| Mechanism | Scope | Class-aware? |
|---|---|---|
| `_RETIRED_STRATEGIES` | global strategy name | no |
| `_PAPER_ONLY_STRATEGIES` | global strategy name | no |
| `BLACKLISTED_STRATEGIES` (config) | global strategy name | no |
| `_RETIRED_SYSTEM_STRATEGY_PAIRS` | (source_system, strategy) composite | no (`asset_class` ignored) |
| `is_blocked_strategy(name, asset_class)` | global name + FX-kill + commodity-inverse-kill | only for the two kill-switch classes (FOREX, COMMODITY) |

There is **no arbitrary `(asset_class, strategy)` class-scoped kill key** in the current code. The kill list is class-scoped by design (e.g. `adx-trend-scout` must die in ETF/BOND but the operator explicitly flags that `ETF rs-breakout-scout` stays). Therefore **every class-scoped kill on the list requires a NEW class-scoped key.**

---

## 3. Proposed mechanism (if approved)

Add a new canonical frozenset in `alpha_engine/strategy_blocklist.py`:

```python
_CLASS_SCOPED_BLOCKED_PAIRS: frozenset[tuple[str, str]] = frozenset({...})
```

and extend `is_blocked_pick(pick)` / `filter_blocked_picks` to check `(pick["asset_class"], pick["strategy"])` against it (casefolded, mirroring the existing `is_blocked_strategy` pattern). This preserves `adx-trend-scout`-in-equity, `rs-breakout-scout`-in-ETF, etc., because the kill keys on the pair, never on the name alone.

---

## 4. Kill-list match report (pair → config-key status)

Legend: ✅ already blocked (no mutation needed) · ➕ proposal added (new class-scoped key) · ⚠ module name (note).

### BANNED

| asset_class | strategy | Config key today | Class-scoped support now |
|---|---|---|---|
| FOREX | `forex_rsi2_mean_reversion` | ✅ `_RETIRED_STRATEGIES` (strategy_blocklist.py:237) | n/a — global name retire already blocks; name is FOREX-unique |
| (all) | `multi_asset_copytrader` | ⚠ source-level only (`production_scanner.py:1379`, `smart_picks_engine.py`, `emitter_whitelist.py`); **not** in strategy_blocklist sets | ➕ propose class-scoped pairs for each class (CRYPTO/EQUITY/FOREX/COMMODITY/FUTURES) |

### n≥30 & PF<1

| asset_class | strategy (n, PF) | Config key today | Class-scoped support now |
|---|---|---|---|
| CRYPTO | `mega_mutation_ema_momentum_m006` (68, 0.77) | none | ➕ |
| CRYPTO | `strong consensus (alpha_engine, luxalgo_filters)` (70, 0.94) | none | ➕ (as `(alpha_engine, luxalgo_filters)` composite + CRYPTO class) |
| EQUITY | `adx-trend-scout` (49, 0.93) | none | ➕ |
| EQUITY | `price-accel-scout` (35, 0.79) | none | ➕ |
| EQUITY | `quality-minus-junk` (49, 0.69) | none | ➕ |
| EQUITY | `stoch-rsi-scout` (42, 0.69) | none | ➕ |
| FOREX | `london-breakout-scout` (64, 0.74) | none | ➕ |

### BOND (all 12)

`adx-trend-scout`, `betting-against-beta`, `cta_golden_cross_200`, `ema_stack_momentum`, `mtf-align-scout`, `pairs-trading`, `quick_engine`, `rs-breakout-scout`, `rsi-divergence-scout`, `volume-anomaly-scout`, `vwap-reclaim-scout`, `vwap-reversion-scout` → **all ➕** (no config key; class-scoped). Note `rs-breakout-scout` is killed in BOND but kept in ETF — proof class-scoping is mandatory.

### FUTURES (all 2)

`commodity_term_cot`, `futures_cross_asset_momentum` → **both ➕**. Note `futures_cross_asset_momentum` is a real emitter (`futures_strategies.py:274/335/485`).

### ETF (all 30 except `rs-breakout-scout`)

`adx-trend-scout`, `aroon-trend-scout`, `betting-against-beta`, `bollinger-squeeze`, `call-surge-scout`, `cmf-accumulation-scout`, `donchian-stock-breakout`, `ema-ribbon`, `golden-cross-stocks`, `goldmine_1x_consensus`, `intermarket-flow-scout`, `macd-hidden-div-scout`, `momentum-factor`, `mtf-align-scout`, `options-flow-scout`, `pairs-trading`, `post-earnings-rev-scout`, `price-accel-scout`, `quality-minus-junk`, `quality-momentum-scout`, `quick_engine`, `regime_mild_bull`, `sector-rotation`, `stoch-rsi-scout`, `strong consensus (alpha_engine, kimi)`, `vix-mean-rev-scout`, `vol-contraction-scout`, `volume-anomaly-scout`, `vwap-reclaim-scout`, `vwap-reversion-scout` → **all ➕**. Exception **kept**: `ETF rs-breakout-scout`.

### FREEZE (paper-only)

| asset_class | strategy | Config key today | Action |
|---|---|---|---|
| CRYPTO | `luxalgo_confluence` | ❌ REMOVED from `_PAPER_ONLY_STRATEGIES` on 2026-04-29 (Near-Miss panel) | ➕ **re-add** to `_PAPER_ONLY_STRATEGIES` → hard-blocks live emission until forward-validated |

---

## 5. Overlap / redundancy notes

- ETF `intermarket-flow-scout` is **already** in `_PAPER_ONLY_STRATEGIES` (strategy_blocklist.py:363) → already blocked globally; the ETF kill is redundant but harmless (kept in the list for an audit trail).
- Several names (`adx-trend-scout`, `betting-against-beta`, `mtf-align-scout`, `pairs-trading`, `quick_engine`, `rs-breakout-scout`, `rsi-divergence-scout`, `volume-anomaly-scout`, `vwap-reclaim-scout`, `vwap-reversion-scout`) appear in **both** BOND and ETF lists → class-scoping required; **never** a global name kill.

---

## 6. Contingency check (per operator instruction)

- None of the kill-list strategy names exist as **verbatim keys** in the canonical blocklist sets (`_RETIRED_STRATEGIES` / `_PAPER_ONLY_STRATEGIES` / `BLACKLISTED_STRATEGIES`) except `forex_rsi2_mean_reversion`. Therefore there are no "name doesn't match config" ambiguities to resolve — every kill-list pair is an emitter-side name that requires a **new class-scoped pair key**.
- If the operator wants an exact-name sanity check on any specific emitter, that name must be looked up in the emitting scanner's dispatch table (e.g. `multi_asset_copytrader_scraper.py`), not the blocklist config — noted here for the PR description.

---

## 7. Validation (post-approval only)

1. Replay 2026-10-12→19: `forex_rsi2_mean_reversion` emitted = 0.
2. 24h post-deploy: issued picks for every (asset_class, strategy) on the list = 0.
3. `ETF rs-breakout-scout` **still issues** (regression guard).
4. `luxalgo_confluence` emits 0 live; paper-only mode still permitted.
