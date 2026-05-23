# Strategy investigation before hard kill

**Last updated:** 2026-04-08  

We **tread lightly** on adding systems to `BLOCKED_SOURCE_SYSTEMS` or ripping generators out of the pipeline. Losers in one context often become useful after **DNA mutation**, **inverse direction**, **parameter grid**, **regime gating**, or **cross-asset / cross-symbol** transfer. Hard kills destroy signal we may not have finished extracting.

## Principles

1. **Investigate first** — Poor rolling WR or dashboard “REDUCE”-style warnings mean **escalate to rehabilitation**, not immediate graveyard.
2. **Preserve lineage** — Track parent strategy → mutation → backtest result (see `alpha_engine/data/strategy_mutations.json` patterns).
3. **Cross-asset humility** — The same logic may lose on crypto and win on forex/equity (or vice versa). Before blocking, check **asset-class splits** in closed history.
4. **Three-axis autopsy** — Many losers are **misapplied** winners: check **symbol**, **direction**, and **timeframe** slices on closed data before kill. Run **`python tools/mutation_analysis.py`** on an exported closed CSV; full playbook: **`docs/MUTATION_THREE_AXIS_PROTOCOL.md`**.
5. **Scoring is not the edge** — It ranks and executes; **strategy selection and rehabilitation** create recoverable edge. Do not expect a higher `score` alone to fix a broken generator.

## Escalation ladder (recommended)

| Stage | Action | Repo touchpoints |
|-------|--------|------------------|
| 0 — Observe | Flag in dashboard / logs; no block | `audit_trail/dashboard_generator.py` summaries |
| 1 — Reduce risk | Lower max active picks, size, or promotion — **optional**; pause **new** variants only if needed | Portfolio caps, forward validator |
| 2 — Rehabilitation | Run inverse / mutation / regime / grid per **TESTING_PROTOCOL §7** | `TESTING_PROTOCOL.MD` Stages 2–5 |
| 3 — DNA / auto mutator | Generate `inverse_*`, `_mut_*` candidates | `alpha_engine/dna_mutation_engine.py`, `alpha_engine/auto_dna_mutator.py`, `alpha_engine/strategy_mutator.py` |
| 4 — Backtest / WF | Evidence: WR, PF, min trades on **held-out** data | `incubator/backtest_team/`, walk-forward reports |
| 5 — Hard block | Add to `BLOCKED_SOURCE_SYSTEMS` **only** after rehab fails or legal/TOS mandate | `audit_trail/quality_gates.py` (sync `BLOCKED_SYSTEMS` in `audit_dashboard/template.html`) |

## Automated three-axis autopsy workflow

This workflow operationalises the three-axis autopsy (symbol / direction / timeframe) so demotion decisions rest on reproducible evidence. It exports the `closed_picks` ledger, loops `tools/mutation_analysis.py` over every strategy present, consolidates results into `audit_exports/mutation_report.csv`, and optionally appends deterministic losers to `alpha_engine/strategy_blocklist.py` behind an explicit safeguard flag.

### Step 1 — Export ledger

Export `alpha_engine/data/closed_picks.json` to `audit_exports/closed_picks.csv`. A one-shot Python block (json → csv) is sufficient; no dedicated tool required. Required fields:

```bash
# Export alpha_engine/data/closed_picks.json → audit_exports/closed_picks.csv
# Fields: strategy, symbol, direction, entry_ts, exit_ts, entry_price, exit_price, pnl_pct, timeframe
```

### Step 2 — Run per-strategy autopsy

- Driver script `tools/run_all_mutations.sh` iterates the unique `strategy` values in the exported CSV.
- For each strategy it invokes:

  ```bash
  python tools/mutation_analysis.py \
      --input audit_exports/closed_picks.csv \
      --strategy <name> \
      --output audit_exports/mutation_<name>.csv \
      --min-trades 10
  ```

- Per-strategy reports are consolidated into a single `audit_exports/mutation_report.csv` for review.

Three-axis grouping applied per strategy:

| Axis | Grouping | Flag condition |
|---|---|---|
| Symbol | group by `symbol` | WR < 30% OR avg pnl < -0.5% |
| Direction | split long vs short | strategy wins only on one side |
| Timeframe | group by `timeframe` | profitable on only one timeframe — suggest grid or regime-gate on others |

### Step 3 — Optional auto-blocklist append (safeguarded)

- Hard-block candidate criteria: `WR < 0.35 AND avg_pnl_pct < -0.5 AND total_trades >= 10`.
- Writes the union of existing + candidate pairs back to `alpha_engine/strategy_blocklist.py`, deduplicated.
- **Safeguard:** this step requires the explicit `--auto-block` flag. Default behaviour is a dry-run that prints candidates only — never mutate the blocklist silently.

### Step 4 — Top-10 quick sanity-check

Sort `audit_exports/mutation_report.csv` by `avg_pnl_pct` ascending and take the head — a one-liner pattern (`sort -t, -k<col> -g | head -10`, or equivalent pandas) surfaces the deepest bleeders for manual triage before any block is applied.

### Integration with escalation ladder

Entries auto-flagged by this workflow must still traverse Stages 2–4 of the escalation ladder (rehabilitation → DNA mutation → backtest/WF) before any Stage-5 hard block, UNLESS the loss pattern is deterministic (WR = 0% on n ≥ 20) — in which case the composite-pair block in `alpha_engine/strategy_blocklist.py::_RETIRED_SYSTEM_STRATEGY_PAIRS` (for example `kimi_signal_tracking/default` on forex, added 2026-04-19) is appropriate without further rehab.

## When hard block is still appropriate

- Sustained negative edge **after** documented rehab attempts (or explicit user sign-off).
- Data-quality disasters (phantom symbols, redenomination bugs) — see symbol blocklists separately from **strategy** blocks.
- Compliance / vendor TOS.

## Plan alignment (scoring vs strategy)

- **Noise reduction** (e.g. one `claude_gainer_st` row per symbol) improves **interpretability** without claiming new alpha.
- **Entry-time score freeze** validates whether **any** feature predicts outcomes — use it to decide *whether* to invest in rehab vs kill.
- **Micro-cap / narrative discovery** (SIDU-class) is **human + batch tooling**, not a dashboard sort order change.

## Related docs

- `docs/MUTATION_THREE_AXIS_PROTOCOL.md` — symbol / direction / timeframe autopsy, mutation quality score, allowlist workflow.
- `TESTING_PROTOCOL.MD` — rehabilitation-first philosophy, §7 stages, inverse precedents.
- `docs/TRADINGVIEW_MCP_GUIDE.md` — execution automation only.
- `.claude/skills/tv-paper-trade/SKILL.md` — paper TP/SL discipline.

---

## Review feedback — Cursor agent (2026-04-19)

1. **Dashboard-first RCA:** When a strategy “looks bad,” pull **top_symbols + system** slices from `dashboard_data.json` before mutating — the extensive 2026-04-19 summary shows **misleading asset-class totals** when one combo dominates.
2. **Evidence base:** Prefer **`closed_picks.json`** for kill/mute decisions; `strategy_performance.json` remains secondary per Strategy Factory v1.1.
3. **Orthogonality after rehab:** A successful mutation may still be redundant — add a correlation check ([correlation_prune_strategies.py](../baby_strategies/correlation_prune_strategies.py)) before re-promoting.
4. **Blocklist symmetry:** When removing a block, record **why** (which gate failed vs recovered) in the investigation MD so the same mistake isn’t re-merged via Copilot.
5. **Cross-link:** [STRATEGY_DISCOVERY_PROTOCOL.md](STRATEGY_DISCOVERY_PROTOCOL.md) for new-template discovery; this doc stays the **rehab vs kill** guide for existing routes.

## Review feedback — Kimi Code CLI (2026-04-19)

1. **Add `loss_driver_analyzer.py` to the autopsy workflow.** Step 2 (Run per-strategy autopsy) should begin with `scripts/loss_driver_analyzer.py --strategy <name>` before `tools/mutation_analysis.py`. The analyzer surfaces loss concentration, exit-reason breakdown, and worst symbols in seconds — this informs which mutation axes are worth testing.
2. **Deterministic-loss fast-path.** The hard-block criteria currently say `WR < 0.35 AND avg_pnl_pct < -0.5 AND total_trades >= 10`. Add a separate fast-path: `WR = 0% AND total_trades >= 20` → immediate surgical block, no rehab. See `LOSS_DRIVER_ANALYSIS_2026_04_19.md` §The MATIC Pattern.
3. **Exit-reason analysis is missing from the autopsy.** The three-axis protocol covers symbol/direction/timeframe but not **exit reason**. If 80% of losses are SL hits with R:R ≈ 1:1, the strategy has no positive expectancy regardless of symbol or direction — it's a sizing/SL problem, not a selection problem.
4. **Correlate with `strategy_performance.json` before investigation.** If a strategy has `total_pnl_pct < -50` and `losses > 100`, run the analyzer before exporting closed picks. The JSON already contains per-symbol PnL and exit reasons — no need to re-derive from CSV.
5. **Link to correlation guard.** Before any Stage-4 backtest/WF promotion of a rehabilitated strategy, mandate `scripts/strategy_correlation_guard.py` pass. The investigation template should include a "Correlation Check" section.

---

## cta_replicator — COMMODITY class block (2026-05-17)

**Investigation date:** 2026-05-17  
**Evidence source:** `reports/commodity_nonctf_strategy_autopsy_2026_05_17.md` + live `closed_picks.json` verification  
**Autopsy type:** Three-axis (symbol / direction / class split)

### Findings from closed_picks.json (verified)

The autopsy document refers to `cta_replicator` as an umbrella name. In `closed_picks.json` the COMMODITY losers resolve to two concrete strategy names:

| Strategy (closed_picks name) | Symbol | n | WR | avg_pnl |
|------------------------------|--------|---|----|---------|
| cta_cross_asset_tsmom | CL=F (Oil) | 47 | 19.1% | -0.015% |
| cta_cross_asset_tsmom | NG=F (Gas) | 24 | 0.0% | -0.030% |
| cta_commodity_momentum_term | ZC=F (Corn) | 8 | 0.0% | -0.038% |
| cta_commodity_momentum_term | ZS=F (Soy) | 3 | 0.0% | -0.029% |

**Direction breakdown (cta_cross_asset_tsmom COMMODITY):**
- LONG: WR=0.0%, n=24 — complete wipeout
- SHORT: WR=19.1%, n=47 — sub-floor (< 45% charter)

**Direction breakdown (cta_commodity_momentum_term COMMODITY):**
- SHORT only: WR=0.0%, n=11 — complete wipeout

### CT=F (Cotton) — unaffected

The WR=84-87% edge on CT=F comes from `cot_positioning` and `cftc_cot_commercial_signal`, NOT from `cta_replicator`/`cta_cross_asset_tsmom`/`cta_commodity_momentum_term`. Those strategies have 0 CT=F picks. The CT=F edge is fully preserved.

### PF calculation

| Subset | n | WR | PF |
|--------|---|----|----|
| Non-CT=F losers (cta_replicator family) | 83 | ~12% | 0.22 |
| CT=F (cot_positioning + cftc_cot_commercial_signal) | 230 | 85.7% | 7.84 |

### Prior gates already in place

1. `BLOCKED_SOURCE_SYMBOL_PAIRS` (lines 5645–5649): blocks `cta_replicator` × `CL=F`, `NG=F`, `ZC=F`
2. `BLOCKED_DIRECTION_TRIPLES` (lines 2708–2709, 2726–2727): blocks `cta_cross_asset_tsmom` LONG+SHORT for COMMODITY; `cta_commodity_momentum_term` LONG+SHORT for COMMODITY

### Verdict: BLOCK cta_replicator LONG and SHORT for COMMODITY

Both directions are sub-floor (WR < 45%) with no salvageable direction. Adding `("COMMODITY", "cta_replicator", "LONG")` and `("COMMODITY", "cta_replicator", "SHORT")` to `BLOCKED_DIRECTION_TRIPLES` provides defense-in-depth: any new `cta_replicator` COMMODITY picks (regardless of symbol) are rejected.

This is a **per-class direction block, not a full kill** — `cta_replicator` remains active for FOREX and other classes where it may have edge.

### Gate added

```python
# cta_replicator COMMODITY autopsy 2026-05-17: WR=0-19% PF=0.22 n=83
# (Oil CL=F n=47 WR=19%, Gas NG=F n=24 WR=0%, Corn ZC=F n=8 WR=0%)
# Both directions sub-floor; CT=F Cotton edge (WR=84-87%) is from
# cot_positioning / cftc_cot_commercial_signal — unaffected.
("COMMODITY", "cta_replicator", "LONG"),
("COMMODITY", "cta_replicator", "SHORT"),
```

Re-evaluate: if `cta_replicator` emits ZS=F/ZW=F/KC=F picks that clear the
BLOCKED_SOURCE_SYMBOL_PAIRS and accumulate n≥30 with WR≥50%, remove the block
for the profitable direction only.
