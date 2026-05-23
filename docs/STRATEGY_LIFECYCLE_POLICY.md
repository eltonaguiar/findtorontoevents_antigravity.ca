# Strategy Lifecycle Policy

**Version:** 1.1 (incorporates DeepSeek + Inception mercury-2 + Ollama Cloud gpt-oss:20b review consensus)
**Established:** 2026-04-17
**Status:** Active (supersedes ad-hoc kill decisions; complements `MUTATION_THREE_AXIS_PROTOCOL.md` and `STRATEGY_INVESTIGATION_BEFORE_KILL.md`)

## Changelog
- **v1.1 (2026-04-17):** Three-AI review consensus applied: (a) raised promotion criteria from 50→200 forward trades with 95% CI, (b) added walk-forward analysis (WFA) requirement, (c) added regime-conditional testing (bull/bear/choppy), (d) added transaction-cost sensitivity to edge confirmation, (e) capped backtest extensions to prevent analysis paralysis, (f) added re-injection pathway for disabled elements that recover.

---

## Principle

**A strategy or symbol-strategy pair is data, not a verdict.** Before the system disables anything, we exhaust three less-destructive options in strict order:

```
1. EXTEND BACKTESTING   →   broaden the evidence base
        ↓ (if no edge surfaces or strategy is structurally broken)
2. MUTATE OR INVERT     →   transform the signal into a winner
        ↓ (if mutation also fails)
3. DISABLE              →   add to a ban registry (last resort)
```

Disabling is reversible (entries in ban lists can be removed) but creates a gap in the supply pipeline. Always prefer (1) or (2) when feasible.

---

## Step 1 — EXTEND BACKTESTING (preferred)

**When applicable:** strategy has codified entry/exit logic that runs on historical OHLCV data (i.e. it's actually backtest-able). Excludes strategies that depend on real-time order flow, social sentiment ingestion, or 3rd-party copy-trader outputs.

### Required test matrix before any kill decision

| Dimension | Required coverage |
|---|---|
| **Symbol universe** | All eligible symbols in the asset class (e.g. for crypto: top-100 by 30d volume; for equity: S&P-500; for forex: 28 majors+crosses) |
| **Timeframes** | Minimum 3: 15m, 1h, 4h (crypto) / 1h, 4h, 1d (non-crypto) |
| **OOS splits** | **Walk-forward analysis (WFA)** preferred over single train/val/test split. Minimum 3 rolling windows with retraining, each ≥ 180 days for non-crypto / ≥ 90 days for crypto. |
| **Regime split** | Tag each backtest period as TRENDING_BULL / TRENDING_BEAR / CHOPPY (per dashboard `regime_validation`). Edge must hold in ≥ 2 of 3 regimes. |
| **Monte Carlo** | 1,000 random trade-order shuffles for execution-noise robustness, **plus** bootstrap of 200 hyper-parameter resamples for parameter robustness → check Sharpe-stability and 5%-percentile PF |
| **Transaction-cost sensitivity** | Sweep round-trip cost from 0% → 0.5% in 0.1% steps. Edge must survive at realistic cost (0.10% crypto, 0.05% forex, 0.20% equity) AND not flip to negative-EV at 2× realistic cost. |
| **Edge confirmation (post-cost)** | Sharpe ≥ 1.0, PF ≥ 1.5, max-drawdown ≤ 25%, n_trades ≥ 100 across the matrix, **WR 95% confidence interval lower bound ≥ 50%** |
| **Extension cap** | At most ONE additional 180-day window if initial matrix is inconclusive. Past that, proceed to Step 2 — no analysis paralysis. |

### Tools

- `tools/cross_asset_backtester.py` — runs the matrix
- `tools/mutation_analysis.py` — pre-mutation analysis (export closed CSV first per CLAUDE.md)
- `tools/backtest_hc_filter.py` / `backtest_hc_gates.py` — gate-aware backtests

### Deliverable

Write `updates/{date}-{strategy}-extended-backtest.md` with:
- The matrix used (symbols × timeframes × splits)
- Per-cell WR/PF/Sharpe/MaxDD
- Monte Carlo confidence bands
- Verdict: edge confirmed → **promote to live with sized probation**, OR no edge → **proceed to Step 2**

---

## Step 2 — MUTATE OR INVERT (intermediate option)

**When applicable:** Step 1 found no broad edge but the closed-pick history shows asymmetry (one direction wins, one symbol-subset wins, one regime wins).

### The three mutation axes (per `MUTATION_THREE_AXIS_PROTOCOL.md`)

1. **Symbol axis** — restrict to top-quartile symbols by historical WR
2. **Direction axis** — keep only the winning side (LONG-only or SHORT-only)
3. **Confidence/RR axis** — apply min thresholds where edge appears

### Inverse strategy variant

If WR is consistently below 35% with statistically significant n (≥ 50), test the **mathematical inverse**:
- Flip every historical trade's direction
- Apply realistic costs (0.10% round-trip crypto, 0.05% forex, 0.20% equity)
- If inverse WR > 60% with PF > 1.5 → deploy `{strategy}_inverse` as SANDBOX

### Hybrid mutation

Combine axes: e.g. M_HYBRID = `LONG-only on TRX+TAO + invert on 9 chronic-loss symbols + block MATIC`. This is what saved `quan_engine_scalp`: parent at 21% WR PF 0.25 → hybrid at 71% WR PF 2.89.

### Deliverable

Write `updates/{date}-{strategy}-mutation-investigation.md` with:
- Phase 1 investigation table (per-symbol, per-direction, per-conf-bucket WR)
- Phase 2 inverse comparison
- Phase 3 top mutations
- Phase 5 recommendation: KILL / MUTATE / INVERT / REASSIGN / PROBATION

### Sandbox deployment

- **Sandbox phase:** 0.25× sizing for the first 200 forward trades (raised from 50 per 3-AI review — 50 trades has only ~10% statistical power)
- **Promotion floor (post-cost):** WR ≥ 60% (lower bound of 95% Wilson CI ≥ 55%) AND PF ≥ 2.0 AND Sharpe ≥ 1.0 AND maxDD ≤ 20%
- **Auto-demotion triggers:**
  - WR < 45% over 50 consecutive trades → back to investigation
  - Drift > 5% from sandbox baseline WR after 100 trades → back to investigation
  - Single-trade loss > 5% of account → freeze + escalate

### Re-injection pathway (recovered strategies)

Disabled strategies (Step 3) can be **un-disabled** if:
1. Underlying data-quality bug is fixed (for source-level disables)
2. Re-run of Step 1 backtest matrix with current data confirms edge
3. Last-disable date is older than 30 days
4. New investigation MD documents what changed

Maintain `updates/{date}-{strategy}-reinjection.md` for any un-disable. Reset to SANDBOX (not PROVEN) regardless of prior tier.

---

## Step 3 — DISABLE (last resort)

**When applicable:** Steps 1 and 2 both failed AND the strategy is bleeding active picks.

### Conceptual model: 3 logical tiers, 9 composite-key lists

The 9 registries in `audit_trail/quality_gates.py` aren't 9 distinct disable concepts — they're **three conceptual tiers** with composite-key precision:

| Conceptual tier | Implementation registries |
|---|---|
| **A. Symbol-specific** (most surgical) | `BLOCKED_STRATEGY_SYMBOL_PAIRS`, `BLOCKED_SYMBOLS` |
| **B. Direction/asset-conditional** (medium) | `BLOCKED_DIRECTION_TRIPLES`, `BLOCKED_ASSET_STRATEGY_PAIRS`, `BLOCKED_ASSET_SOURCE_PAIRS` |
| **C. Global** (most aggressive) | `BLOCKED_STRATEGIES`, `BLOCKED_SOURCE_SYSTEMS`, `PERMANENTLY_KILLED_STRATEGIES`, `BLOCKED_ACTIVE_TRUST_TIERS` |

Always prefer the most surgical tier (A → B → C). Composite keys exist precisely so we don't kill a winning sub-slice when blocking a losing one.

### Disable registry index (most surgical → most aggressive)

| Registry | Format | When to use |
|---|---|---|
| `BLOCKED_STRATEGY_SYMBOL_PAIRS` | `(strategy, symbol)` | Strategy works elsewhere but bleeds on a specific symbol (e.g. `quan_engine_scalp` on MATICUSDT 0/239 WR) |
| `BLOCKED_DIRECTION_TRIPLES` | `(asset_class, strategy, direction)` | Strategy has asymmetric edge — kill the losing side only (e.g. `(CRYPTO, quan_engine_swing, LONG)`) |
| `BLOCKED_ASSET_STRATEGY_PAIRS` | `(asset_class, strategy)` | Strategy works on one asset class but not another (e.g. `(FOREX, MomentumEMA)`) |
| `BLOCKED_ASSET_SOURCE_PAIRS` | `(asset_class, source_system)` | Source's data quality is bad for one asset class only |
| `BLOCKED_STRATEGIES` | `(strategy, asset_class_or_None)` | Strategy is structurally broken across the named class (or all if None) |
| `BLOCKED_SOURCE_SYSTEMS` | source name | Entire source is broken (e.g. data layer corruption like `kimi_signal_tracking`) |
| `BLOCKED_SYMBOLS` | symbol | Symbol itself is structurally bad (delisted, micro-cap manipulation, etc.) |
| `PERMANENTLY_KILLED_STRATEGIES` | strategy name | Last-resort global kill — use sparingly |
| `BLOCKED_ACTIVE_TRUST_TIERS` | tier name | Block by trust tier (BANNED, AVOID, UNTRUSTED) |

### Mandatory before adding to any registry

1. **Investigation MD** at `updates/{date}-{strategy}-investigation.md` documenting:
   - n closed, WR, PF, total PnL
   - Per-symbol, per-direction breakdown (whichever applies)
   - Whether Step 1 (extend backtesting) was attempted
   - Whether Step 2 (mutate/invert) was attempted, and why those failed
   - Active picks that will be orphaned (count + symbols)

2. **Inline comment** in the registry entry citing the investigation MD

3. **Reversibility plan**: under what conditions would we remove this entry? (e.g., "remove if upstream ingest fixes the BUY → LONG vocab")

---

## Special case: data-layer corruption

If the issue is malformed input (wrong field values, scale errors, missing fields) rather than poor edge, the proper fix is **upstream**, not in the disable registry. Document the bug, attempt to find the broken integration, and only fall back to source-level disable if the upstream fix is impractical.

Example: `kimi_signal_tracking` has `confidence=9.9999` (10× scale bug) and `direction=BUY` (pre-vocab-migration). The right fix is to find and fix the Kimi ingest. Adding to `BLOCKED_SOURCE_SYSTEMS` is option B if the upstream code can't be located or owned.

---

## Audit trail

Every disable, mutation deployment, or backtest reform must:
- Live in a dated MD under `updates/`
- Cite source data files and commit SHAs used in the analysis
- Be reversible by removing the registry entry + restoring any blocked active picks
- Be subject to the 14-day re-evaluation cycle (do conditions warrant un-disabling?)

---

## Why this order

| Order | Why |
|---|---|
| Backtest first | Most strategies are killed because of regime mismatch or low n; broadening the test surface often reveals true edge |
| Mutate second | A failing strategy often contains a winning sub-strategy (asymmetric edge); discarding the whole loses the signal |
| Disable last | Disabling is reversible but causes supply-pipeline gaps; it should be the last option once edge has been definitively proven absent |

Killed strategies don't generate forward data, so once disabled they cannot prove their own redemption. This is the asymmetric cost that justifies the cascade.

---

## Approval gates per cascade step

| Step | Required approvals |
|---|---|
| 1. Extend backtest | None — anyone can launch the matrix; results speak for themselves |
| 2. Mutate / Invert (SANDBOX) | Auto-approve if MD shipped + py_compile OK + 0.25× sizing |
| 2. Mutate / Invert (PROMOTE to full sizing) | Requires 50-trade forward sample + WR/PF thresholds met |
| 3. Disable (any registry) | Investigation MD + 14-day re-eval timer + active-picks orphan list |

---

## Cross-references

- `CLAUDE.md` — peer coordination + "Mutate Before Kill" rule
- `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` — investigation template
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md` — mutation procedure
- `docs/PROVEN_TIER_VALIDATION_PROTOCOL.md` — promotion criteria
- `audit_trail/quality_gates.py` — all 9 disable registries
- `tools/mutation_analysis.py` — analysis runner
- `tools/cross_asset_backtester.py` — backtest matrix runner

---

## Review feedback — Cursor agent (2026-04-19)

1. **Factory alignment:** v1.1 forward-test thresholds are **asset-class-specific** — add a footnote here when lifecycle promotion numbers (e.g. 200 trades) conflict with factory §, and cite which doc wins.
2. **Forex / single-strategy bleed:** Recent dashboards show **one combo** can dominate an asset-class PnL — lifecycle “investigate before kill” should explicitly require **system+strategy+symbol** slice queries, not asset-class aggregates only.
3. **Correlation:** Before promoting a rehabilitated strategy, run [correlation_prune_strategies.py](../baby_strategies/correlation_prune_strategies.py) against incumbent return series — rehabilitation can clone an existing factor by accident.
4. **Extension cap:** The “one additional 180-day window” rule is good — log **reason for extension** in the investigation MD to prevent endless retries.
5. **Discovery handoff:** See [STRATEGY_DISCOVERY_PROTOCOL.md](STRATEGY_DISCOVERY_PROTOCOL.md) for green-field hypotheses; lifecycle doc remains the right place for **existing** strategy rehab.

## Review feedback — Kimi Code CLI (2026-04-19)

1. **Add deterministic-loss exception to Step 3 (Disable).** Any strategy-symbol pair with n ≥ 20 and WR = 0% bypasses Steps 1–2 and goes straight to `BLOCKED_STRATEGY_SYMBOL_PAIRS`. Evidence: `quan_engine_scalp` × MATICUSDT (0/913), `copy_hl_lb_None` (0/25). These are not rehab candidates — they are structurally broken.
2. **Integrate `loss_driver_analyzer.py` into Step 1 (Extend Backtesting).** Before broadening the test matrix, run `scripts/loss_driver_analyzer.py --strategy <name>` to identify whether losses are concentrated in one symbol, one direction, or one exit reason. This narrows the matrix scope and prevents wasted compute.
3. **Correlation guard before Step 2 promotion.** The policy already cites `correlation_prune_strategies.py` in Cursor's feedback. Reinforce this: **no mutation or inverse strategy may enter SANDBOX without passing `scripts/strategy_correlation_guard.py --threshold 0.30` against all validated strategies.** Rehabilitation can accidentally clone existing factors.
4. **Auto-demote at S7: add "live data hash firebreak" check.** The factory v1.1 amendments introduced a live-vs-backtest data hash check. The lifecycle policy should reference this: if live data schema/venue changes (e.g., BTCUSDT → BTC-PERP), auto-freeze until S1-S3 are re-run on the new data.
5. **Extension cap: log reason for extension.** The policy already has the one-additional-180-day-window rule. Add a requirement that the investigation MD must state **why** the initial matrix was inconclusive (regime gap? symbol gap? timeframe gap?) to prevent endless retry loops.
