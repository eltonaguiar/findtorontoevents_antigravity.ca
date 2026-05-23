# Signature Codebase Features

**Audience:** cloud agents + future devs. This doc explains two non-obvious,
load-bearing concepts that run through the alpha engine: **Inverse Picks** and
**DNA Mutations**, plus the **"document-and-adjust, don't delete"** philosophy
that governs how strategies are retired.

All file:line references are against `main` as of 2026-05-17. Line numbers may
drift — grep the cited symbol if a reference looks stale.

---

## 1. Inverse Picks

### Concept

A strategy that *consistently loses* is not noise — it is a signal pointed the
wrong way. If a strategy wins only ~15-20% of the time on a statistically
significant sample, then **taking the opposite side of every signal it emits**
turns it into an ~80-85% winner. The repo treats a sustained structural loser
as a tradeable *anti-edge*: flip BUY↔SELL, swap TP/SL, and track the flipped
variant as its own strategy.

This is distinct from "the strategy is random" — a 45-55% WR strategy is noise
and inverting it gains nothing. Only **structural** losers (well below 40% WR,
PF < 0.9, consistent across both halves of history) carry a real inverse edge.

### Where it is implemented

| Piece | File | Notes |
|-------|------|-------|
| Structural-loser detector + inverse strategy generator | `alpha_engine/inverse_edge_system.py` | The canonical inverse engine. |
| Inverse mutation primitive (single-pick flip) | `alpha_engine/dna_mutation_engine.py:210` (`inverse_mutation`) | Flips `signal_type`, recomputes TP/SL around entry. |
| Inverse mutation over a strategy's whole history | `alpha_engine/strategy_mutator.py:166` (`mutate_inverse`) | Direction-split aware: prefers `short_only`/`long_only` subset over a blind `inverse_all`. |
| Loser→inverse pipeline (continuous) | `alpha_engine/auto_dna_mutator.py:62` (`LOSER_MUTATIONS`), `:230` (`flip_direction`) | Generates `inverse`, `inverse_tight`, `inverse_wide`. |
| Contrarian scanner for a specific source (KIMI) | `alpha_engine/kimi_inverse_scanner.py` | Reads KIMI active picks, flips them, re-risks them. |

### How an inverse variant is created and named

- **`dna_mutation_engine.inverse_mutation(pick)`** (`:210-239`): `BUY`→`SELL` /
  `SELL`→`BUY`, then swaps the TP and SL *distances* around the entry price so
  the flipped side has a sensible target/stop. Tags `mutation_type="inverse"`.
- **Naming** — inverse variants always carry a lineage suffix/prefix so their
  performance is tracked separately from the parent:
  - `dna_mutation_engine`: `{parent}_mut_inverse_g{generation}` (`:430`).
  - `auto_dna_mutator`: `inverse_{parent}` / `inverse_{parent}_tight` /
    `inverse_{parent}_wide` (`:264`, `:577`).
  - `strategy_mutator`: `{parent}_inverse` (`:217`).
  - Generic lineage markers used repo-wide: `_inverse`, `_mut_`, `inverse_*`.

### Threshold that triggers an inverse candidate

The bar differs by module — the strictest (`inverse_edge_system.py`) is the
reference standard:

| Source | Trigger to become an inverse candidate |
|--------|----------------------------------------|
| `inverse_edge_system.py:62-67` | **≥20 trades, WR < 40%, PF < 0.90, AND both halves of history < 40% WR** (split-half temporal consistency). Inverse picks then get half position size (`POSITION_SIZE_MULT=0.50`) and max 3 concurrent (`MAX_CONCURRENT_INVERSE=3`). |
| `auto_dna_mutator.py:41-43` | "Super loser": **≥10 trades, WR < 35%, total PnL < -10%** → inverse mutations generated. |
| `dna_mutation_engine.py:49-50` | **≥10 trades, WR < 40%** → mutation candidate (inverse is one of the variants produced). |
| `strategy_mutator.py:185-189` | Per-direction: if the LONG (or SHORT) subset WR < 40%, build the opposite-direction-only variant. |

`inverse_edge_system.py:73-86` also keeps a hardcoded
`KNOWN_STRUCTURAL_LOSERS` set — pre-validated losers (e.g.
`st_multi_day_momentum` 15.7%→84.3% WR inverted) that are trusted without
re-detection.

### Where inverse variants get tracked

- `auto_dna_mutator` writes per-mutation lifecycle stats to
  `alpha_engine/data/dna_mutation_tracker.json` (`mutation_stats`,
  `killed_mutations`, `promoted_mutations`).
- `dna_mutation_engine` records inverse variants in
  `alpha_engine/data/dna_mutations.json` under `mutations` / `promoted` /
  `killed`.
- A pick carrying `source_system == "inverse_loser_mutation"` /
  `"auto_dna_mutation"` or an `inverse_*` strategy name is matched and
  evaluated by `auto_dna_mutator.update_mutation_stats` (`:376-458`).

### How to find an inverse candidate (rule of thumb)

> A strategy with **PF < 0.9 + WR < 40% + n ≥ 20**, where the sub-40% WR holds
> in *both* halves of its trade history, is an inverse candidate. Flip it, size
> it at 0.5×, cap concurrent inverse picks at 3, and track the flipped variant
> under its `_inverse` name.

Confirm the **economic story still makes sense flipped** (a momentum strategy
inverts into mean-reversion) before promoting — see Step 3 of the protocol
below.

---

## 2. DNA Mutations

### Concept

A bad strategy is rarely globally bad — it is usually *misapplied*. The same
logic that loses overall often wins on a **subset** of symbols, one direction,
one timeframe, or once its entry threshold is re-scaled to the asset class's
native volatility. So before a strategy is killed, the repo **mutates** it:
generate gated variants, forward-test them in a SANDBOX, and promote whatever
works. This is the **"mutate before kill"** rule.

### Where it is implemented

| Piece | File | Role |
|-------|------|------|
| 4-axis autopsy protocol (doc) | `docs/MUTATION_THREE_AXIS_PROTOCOL.md` | The decision procedure. |
| Autopsy / slice script | `tools/mutation_analysis.py` | Produces the system×symbol matrix + axis splits. |
| Variant generator + evaluator | `alpha_engine/dna_mutation_engine.py` | `generate_mutations`, `evaluate_mutations`, `apply_mutations_to_scanner`. |
| Continuous loser+winner mutator | `alpha_engine/auto_dna_mutator.py` | `run_auto_dna_mutator` — losers→inverse, winners→amplify. |
| Whole-history mutation + verdict | `alpha_engine/strategy_mutator.py` | `run` — PROMOTE/WATCHLIST/CONFIRMED_KILL classifier. |
| Lifecycle runner (promote/kill emitted variants) | `tools/mutation_lifecycle_runner.py` | Pairs with the scanner wire-in. |
| Production wire-in | `alpha_engine/production_scanner.py:4067-4112` | Calls `apply_mutations_to_scanner`. |

### Mutation types (`dna_mutation_engine.py:9-16`)

`inverse`, `tighter_stops`, `wider_stops`, `regime_gate`, `timeframe_shift`,
`confidence_threshold`, `crossover` (blend a strong donor's TP/SL into the
weak strategy's inverse). `auto_dna_mutator` adds the *winner* side:
`tight`, `wide`, `fast`, `slow`, `aggressive` amplifications
(`auto_dna_mutator.py:68-74`).

### The mutation lifecycle

```
  detect underperformer
        │
        ▼
  4-axis autopsy  (docs/MUTATION_THREE_AXIS_PROTOCOL.md)
    Axis 1 Symbol      — which symbols does it win on?  → symbol allowlist
    Axis 2 Direction   — LONG vs SHORT WR split?        → long_only / short_only / inverse
    Axis 3 Timeframe   — SCALP vs SWING vs POSITION?    → TF gate
    Axis 4 Threshold-  — entry trigger mis-scaled vs    → re-express trigger in
           normalization  the class's native vol?         ATR / realized-vol units
        │  (run: python tools/mutation_analysis.py --json)
        ▼
  gated mutation generated  (named with lineage: _mut_, _inverse, _tight, ...)
        │
        ▼
  SANDBOX  — variant enters the pipeline at SANDBOX trust tier with a
             minimum-forward-trades requirement; original keeps running
             unchanged (the variant is ADDED alongside, not a replacement —
             dna_mutation_engine.apply_mutations_to_scanner :657-746)
        │
        ▼
  evaluate  (dna_mutation_engine.evaluate_mutations / auto_dna_mutator.update_mutation_stats)
        ├── PROMOTE  — variant WR ≥ 50% on ≥10 trades   → status "promoted"
        │             (auto_dna_mutator: WR ≥ 55% AND PnL ≥ +5% on ≥5 trades)
        └── KILL     — variant WR < 35% on ≥10 trades   → status "killed"
                       (auto_dna_mutator: WR < 35% OR PnL < -5%)
```

#### Key thresholds

| Stage | Module | Threshold |
|-------|--------|-----------|
| Mutation candidate | `dna_mutation_engine.py:49-50` | n ≥ 10, WR < 40% |
| Donor (crossover DNA) | `dna_mutation_engine.py:52-53` | n ≥ 10, WR ≥ 55% |
| Promote variant | `dna_mutation_engine.py:54-55` | n ≥ 10, WR ≥ 50% |
| Kill variant | `dna_mutation_engine.py:56-57` | n ≥ 10, WR < 35% |
| Promote (auto_dna) | `auto_dna_mutator.py:58-59` | n ≥ 5, WR ≥ 55%, PnL ≥ +5% |
| Kill (auto_dna) | `auto_dna_mutator.py:56-57` | n ≥ 5, WR < 35% OR PnL < -5% |
| Mutation-quality / curve-fit guard | `MUTATION_THREE_AXIS_PROTOCOL.md` Step 5 | winning subset must be **≥ ~10% of total closed trades** for that system. |
| `strategy_mutator` verdict | `strategy_mutator.py:46-48,366-374` | PROMOTE if WR gain ≥ 10pp **and** WR ≥ 45%; WATCHLIST if WR improved but < 45%; else CONFIRMED_KILL. |

#### Production safety gates (`production_scanner.py:4067-4112`)

The mutation engine is wired into `production_scanner` but **default OFF**:

- `MUTATION_ENGINE_ENABLED=1` — actually extend `active` with mutated variants.
- `MUTATION_ENGINE_SHADOW=1` — compute mutations + log telemetry, do NOT
  extend `active` (7-day shadow-telemetry mode before any pick displacement).
- `MUTATION_SCORE_HAIRCUT` (default `0.85`) — multiplicative haircut on a
  mutated pick's `ml_composite`, so a mutation cannot mechanically crowd out
  a known-good pick at the `MAX_ACTIVE_PICKS` sort-and-truncate gate.

Mutated variants are **added alongside** the original pick, never replace it
(`apply_mutations_to_scanner` docstring, `dna_mutation_engine.py:657-672`).
Already-mutated strategies are skipped from re-mutation
(`dna_mutation_engine.py:173-174`; `auto_dna_mutator._is_mutation_strategy`).

### How to find a mutation candidate

> A strategy with **WR < 40% on n ≥ 10** is a mutation candidate. Run
> `python tools/mutation_analysis.py --json` to get its 4-axis split. If any
> axis (symbol / direction / timeframe / vol-normalized threshold) shows a
> large, stable WR split where the winning subset is ≥ ~10% of total closed
> trades, generate that gated variant, ship it at SANDBOX tier, and wait for
> the forward sample before promote/kill.

---

## 3. "Document-and-Adjust, Don't Delete" Philosophy

Strategies are **not deleted** from the codebase. A losing strategy is first
investigated, then mutated/inverted, and only *demoted or quarantined* — with
the reasoning documented inline — if every rehab path fails. Deletion would
destroy the trade history that the inverse and mutation engines depend on.

### Demotion / quarantine mechanisms

| Mechanism | Location | Effect |
|-----------|----------|--------|
| `BLOCKED_SOURCE_SYSTEMS` | `audit_trail/quality_gates.py:1707` | Hard-block: a source's picks are completely hidden from all views. Mirrored as `BLOCKED_SYSTEMS` in `audit_dashboard/template.html`. Enforced at `quality_gates.py:7267` and `dashboard_generator.py:14307`. |
| `REQUIRES_WALKAHEAD_AUDIT` | `audit_trail/quality_gates.py:1784` | Soft quarantine: suspicious-headline systems excluded from Smart Picks / High Conviction until a clean walk-forward audit. |
| Trust tiers (`SANDBOX` etc.) | `alpha_engine/feed_hygiene.py`, `crypto_sandbox_policy.py`, `smart_picks_engine.py` | New / mutated strategies run at `SANDBOX` trust until they accumulate a forward sample; they cannot reach live-grade accounts. |
| Strategy blocklist (feed level) | `alpha_engine/strategy_blocklist.py` | `RETIRED` (negative-EV, hard-block forever) vs `PAPER-ONLY` (unvalidated, blocked from live but allowed in paper). Also hosts the FX + COMMODITY dynamic kill switches. |
| Per-class kill switches | `alpha_engine/fx_kill_switch.py`, `commodity_kill_switch.py` | Dynamic PF/WR/decay kills, each with a `*_DISABLED=1` rollback env flag. |

### The discipline

1. **Investigation gate first.** Per `CLAUDE.md` and the header comment at
   `quality_gates.py:1704-1706`, you may NOT add a `BLOCKED_SOURCE_SYSTEMS`
   entry without working through `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`
   and `docs/MUTATION_THREE_AXIS_PROTOCOL.md`.
2. **Document the autopsy inline.** Every `BLOCKED_SOURCE_SYSTEMS` entry
   carries a comment with n, WR, PF, the 4-axis autopsy result, and a
   `reports/` reference (see the `copy_trader_highscore` and `goldmine_stocks`
   blocks at `quality_gates.py:1740-1770` for the template).
3. **Blocks are reversible and audited.** Entries get *un*blocked when fresh
   data shows recovery — e.g. `kimi_signal_tracking` unblocked 2026-05-16
   after WR recovered 18.2%→76.6% (`quality_gates.py:1716-1718`),
   `signal_validation` unbanned 2026-04-13 (`:1725-1734`). Re-block triggers
   are written into the comment.
4. **Mutate before kill.** A loser is moved to the inverse / mutation pipeline
   *instead of* being blocked when an axis split exists — see the commented-out
   `claude_gainer` / `aggregated_picks` entries at `quality_gates.py:1771-1773`
   ("MUTATION CANDIDATES — NOT blocked, moved to inverse pipeline").

---

## Quick Reference

| Want to... | Go to |
|------------|-------|
| Detect structural losers / build inverse strategies | `alpha_engine/inverse_edge_system.py` |
| Generate/evaluate DNA mutations | `alpha_engine/dna_mutation_engine.py` |
| Run the continuous loser+winner mutator | `python alpha_engine/auto_dna_mutator.py` |
| Run the 4-axis autopsy on a strategy | `python tools/mutation_analysis.py --json` |
| Understand the kill decision procedure | `docs/MUTATION_THREE_AXIS_PROTOCOL.md`, `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` |
| See what is blocked and why | `audit_trail/quality_gates.py:1707` (`BLOCKED_SOURCE_SYSTEMS`) |
| Mutation lifecycle state | `alpha_engine/data/dna_mutation_tracker.json`, `dna_mutations.json` |
