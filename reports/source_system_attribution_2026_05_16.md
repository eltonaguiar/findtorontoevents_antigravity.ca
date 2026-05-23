# D5 — Source-System Attribution Audit (2026-05-16)

**Goal:** identify the (asset_class, source_system) cells dragging aggregate PF
below institutional grade, and quantify the lift from a clean-cut demotion.

**Data:** `audit_trail/data/universal_resolved_picks.json` (5,000 resolved picks
across all asset classes; pnl_pct realized).

**Method:** aggregate per `(asset_class, source_system)` with `n>=10`; normalize
`asset_class` to upper-case to merge the duplicate `CRYPTO` / `crypto` cohorts
(see Finding #1). Compute WR, PF, total PnL%, share of class volume. Then run a
leave-one-out drag simulation against the CRYPTO aggregate.

---

## Headline finding

> **Removing all CRYPTO source_systems with PF<1 (n>=20) lifts aggregate
> CRYPTO PF from 1.43 → 2.07** (Tier 1 / Renaissance band) at a cost of 37.4%
> of CRYPTO trade volume. **+446% in realized PnL is freed up** (the net loss
> those drag-systems contributed).

This validates the AGENTS.md Goal #1 intuition: most of the CRYPTO underperformance
is **a small number of high-volume, low-PF source_systems dragging the elite
strategies down**, not a system-wide lack of edge.

---

## Finding #1 — `asset_class` casing bug (data quality)

`asset_class` is inconsistently cased in `universal_resolved_picks.json`:

| Value | Count |
|---|---:|
| `crypto` | 3,133 |
| `CRYPTO` | 1,565 |
| `equity` | 160 |
| `MEME` | 71 |
| `forex` | 68 |
| `UNKNOWN` | 3 |

The dashboard's `performance.asset_class_health` keys on upper-case (`CRYPTO`,
`EQUITY`, `FOREX`, etc.). Any consumer that does case-sensitive lookups against
this file will see only ~1/3 of crypto picks, ~0% of equity/forex (since they
arrive lower-case here but upper-case in the dashboard).

**Action:** normalize `asset_class` at write time in `audit_trail/asset_classification.py`
(or wherever picks are written), or normalize on read everywhere. Verify
`dashboard_generator.py` is not double-counting after fix.

---

## Finding #2 — CRYPTO drag table (normalized, n>=10)

| source_system | n | share | WR% | PF | total_pnl% |
|---|---:|---:|---:|---:|---:|
| **ml_crypto_pred** | 844 | 18.0% | 34.8 | **0.81** | **−211.4** |
| quan_engine | 624 | 13.3% | 33.0 | 1.28 | +139.0 |
| **alpha_engine** | 426 | 9.1% | 34.9 | **0.81** | **−83.1** |
| dna_winner_picks | 405 | 8.6% | 33.8 | 1.05 | +16.4 |
| aggregated_picks | 373 | 7.9% | 76.9 | **6.60** | +820.9 |
| kimi_signal_tracking | 364 | 7.7% | 80.8 | **7.62** | +774.7 |
| luxalgo_filters | 357 | 7.6% | 40.1 | 1.31 | +89.0 |
| copy_trader_highscore | 217 | 4.6% | 40.8 | 1.07 | +15.0 |
| copy_trader_intel | 128 | 2.7% | 44.5 | 1.36 | +44.6 |
| **dna_rapid_fire_mutations** | 117 | 2.5% | 31.6 | **0.74** | **−29.9** |
| **claude_gainer_st** | 112 | 2.4% | 28.6 | **0.71** | **−42.3** |
| signal_engine_mutations | 110 | 2.3% | 34.5 | 1.00 | −0.2 |
| ml_crypto_pred_v12 | 99 | 2.1% | 43.9 | 1.34 | +33.3 |
| signal_validation | 87 | 1.9% | 56.3 | 1.93 | +63.2 |
| regime_terminal | 67 | 1.4% | 34.3 | 1.05 | +3.0 |
| rapid_fire | 47 | 1.0% | 51.1 | 1.67 | +31.2 |
| stocks_competition | 42 | 0.9% | 64.3 | 3.15 | +64.5 |
| **mutation_lab** | 39 | 0.8% | 10.3 | **0.19** | **−44.6** |
| revival_all | 35 | 0.7% | 100.0 | inf | +90.5 |
| **battleground** | 30 | 0.6% | 0.0 | **0.00** | **−31.4** |
| **trusted_genome** | 25 | 0.5% | 36.0 | **0.87** | −3.3 |
| chatgpt_combined | 12 | 0.3% | 58.3 | 2.52 | +14.3 |

**Bold rows are PF<1 and n>=20 — the drag cohort.**

---

## Finding #3 — Per-source leave-one-out PF impact (CRYPTO)

Starting aggregate PF = **1.431** (n=4,560 merged CRYPTO).

| Remove this source | n | source PF | New aggregate PF |
|---|---:|---:|---:|
| ml_crypto_pred | 844 | 0.81 | **1.662** ← biggest single lift |
| alpha_engine | 426 | 0.81 | 1.507 |
| dna_winner_picks | 405 | 1.05 | 1.466 |
| claude_gainer_st | 112 | 0.71 | 1.458 |
| copy_trader_highscore | 217 | 1.07 | 1.453 |
| dna_rapid_fire_mutations | 117 | 0.74 | 1.452 |
| mutation_lab | 39 | 0.19 | 1.448 |
| battleground | 30 | 0.00 | 1.443 |
| signal_engine_mutations | 110 | 1.00 | 1.442 |
| regime_terminal | 67 | 1.05 | 1.438 |
| trusted_genome | 25 | 0.87 | 1.435 |

**Combined removal of all PF<1 (n>=20) sources: PF 1.43 → 2.07.**

`ml_crypto_pred` alone accounts for the largest single-source lift (PF +0.23).
It is also the highest-volume source (18% of CRYPTO).

---

## Finding #4 — Non-CRYPTO cohorts are too thin to attribute

| Asset class | Source | n | WR | PF | Notes |
|---|---|---:|---:|---:|---|
| EQUITY | signal_validation | 131 | 55.7 | 1.88 | Single dominant source |
| EQUITY | stocksunify2 | 18 | 0.0 | 0.00 | All flat (PnL=0) — likely unresolved, not actually losing |
| EQUITY | stocks_competition | 11 | 81.8 | 7.88 | Tiny sample |
| FOREX | signal_validation | 68 | 60.6 | 2.16 | **Only one source**, and it's PF>2 — but this disagrees with the AGENTS.md memory snapshot of FOREX PF 0.27 (n=1169). Reconcile via DB pull. |
| MEME | dna_rapid_fire_mutations | 15 | 46.7 | 1.68 | Tiny |
| MEME | aggregated_picks | 14 | 92.9 | 34.21 | Tiny |

**Note:** FOREX, COMMODITY, BOND, ETF data in this resolver file is far thinner
than the AGENTS.md numbers (which come from the dashboard's DB-backed
`asset_class_health`). The drag analysis in this report is **CRYPTO-only**
until a DB pull from `ejaguiar1_stocks` / `ejaguiar1_backtests` produces a
matching dataset for the other classes — that's the natural next prompt.

---

## Recommended next actions (in order)

1. **Fix the `asset_class` casing bug first.** Otherwise downstream gates and
   the dashboard see split cohorts. One-line normalize at the resolver write site.
2. **Run mutation-before-kill on the CRYPTO PF<1 cohort** per
   `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` + `docs/MUTATION_THREE_AXIS_PROTOCOL.md`.
   Priority order by impact:
   - `ml_crypto_pred` (n=844, drag −211% PnL) — biggest fish; export closed
     CSV → `tools/mutation_analysis.py`. Look for time-of-day / regime axis
     that flips it positive before demoting outright.
   - `alpha_engine` (n=426, drag −83%) — surprising; this is a core source.
     Drill into which sub-strategies inside `alpha_engine` are losing.
     Compare against `aggregated_picks` (PF 6.60, n=373) which also flows
     through the same scoring path.
   - `claude_gainer_st`, `dna_rapid_fire_mutations`, `mutation_lab`,
     `battleground` — smaller volume, but `mutation_lab` (PF 0.19) and
     `battleground` (PF 0.00, WR 0.0%) are dead weight.
3. **Investigate why `alpha_engine` raw is PF 0.81 while `aggregated_picks`
   (which ostensibly uses `alpha_engine` signals) is PF 6.60.** This delta is
   the largest signal-quality gradient in the table. The aggregation layer is
   doing the real work — quantify what it's filtering out, and apply that
   filter upstream in `alpha_engine` itself.
4. **Pull the non-CRYPTO sources from the DB** (`ejaguiar1_stocks` +
   `ejaguiar1_backtests`) for the same per-source attribution. The resolver
   file is too thin for FOREX/COMMODITY/BOND/ETF to draw conclusions.
5. **Run Prompt D1 (leakage audit) on `ml_crypto_pred` and `alpha_engine`
   first** — given they share the same losing-PF profile (WR ~35%, PF 0.81),
   a shared feature/leakage issue is plausible.

---

## Acceptance criteria for this report

- [x] Identifies the ONE highest-impact single change (kill or fix
      `ml_crypto_pred` → PF 1.43 → 1.66 alone).
- [x] Identifies the combined ceiling (PF 2.07 if all PF<1 sources removed).
- [x] Calls out the data-quality bug (casing) that would invalidate any
      downstream cohort-level metric.
- [x] Hands the next agent a prioritized investigation queue, not a kill list.

## Reproducer

```python
import json
from collections import defaultdict
picks = json.load(open('audit_trail/data/universal_resolved_picks.json'))
agg = defaultdict(lambda: {'n':0,'gw':0.0,'gl':0.0,'wins':0,'losses':0,'pnl':0.0})
for p in picks:
    ac = (p.get('asset_class') or 'UNK').upper()
    ss = p.get('source_system') or 'unknown'
    pnl = p.get('pnl_pct')
    if pnl is None: continue
    a = agg[(ac, ss)]; a['n'] += 1; a['pnl'] += pnl
    if pnl > 0: a['wins'] += 1; a['gw'] += pnl
    elif pnl < 0: a['losses'] += 1; a['gl'] += abs(pnl)
# print rows, then drag-sim for CRYPTO
```

Run from repo root. Data file is regenerated by
`audit_trail/universal_pick_resolver.py`; report numbers are valid for the
snapshot in this commit.
