# EAGLE-6 Admissibility Gate — 2026-06-02 (minimax-m3-free)

## TL;DR

Adds a third layer to the EAGLE pick pipeline: **global per-strategy statistical hard gates**. Runs after EAGLE-4 (persona kill) and EAGLE-5 (symbol/persona boost). Implemented in `alpha_engine/eagle_gates.py` as `apply_eagle6_admissibility()`, wired into `production_scanner.py` at section 6f2.7.

## What it does (v1, today)

Three hard gates; **any** failure kills the pick:

| Gate | Threshold | Source | Fail-closed? |
|---|---|---|---|
| DSR noise | Strategy not in `dsr_noise` set | `tools/deflated_sharpe_results.json` (27 noise strategies out of 52) | Yes — kills pick if strategy is in noise set |
| Insufficient-n | Strategy has ≥ 30 resolved trades | DSR JSON `trades` field per strategy | Yes — kills if < 30 |
| HHI concentration | This strategy's source-HHI ≤ 0.20 of total active picks | Computed live from current `active` list | Yes — kills if > 0.20 |

**v2 (planned, not shipped today):**
- PBO < 0.5 (Probability of Backtest Overfitting) — needs `tools/cpcv_pbo_results.json` (not yet generated)
- Walk-forward OOS PF ≥ 0.8 × IS PF — needs per-strategy walk-forward payload (not yet per-strat)
- Bootstrap CI for PF must not cross 1.0 — needs per-strategy PnL list (not in DSR JSON)

All three v2 gates are blocked on data pipeline work, not on code. Added as v2-stubs in the module docstring with explicit blockers.

## Why this layer

EAGLE-4 is **local** (per-pick persona/direction). EAGLE-5 is **local** (per-pick symbol boost). EAGLE-6 is **global** (per-strategy statistical credibility). A pick from a strategy that lost money 70% of the time (DSR noise) shouldn't be saved by a per-pick whitelist boost — that's the whole point of having a 3-layer pipeline.

## Data sources

- `tools/deflated_sharpe_results.json` (24 KB, generated 2026-04-06) — DSR scores, haircut, per-strategy trade counts
  - 52 strategies analysed, 25 surviving, 27 flagged as noise (48.1% survival rate)
  - sr_haircut = 2.5034 (Harvey-Liu multiple-testing threshold for 164 total strategies)
  - First 5 DSR-noise strategies: `Consecutive Beats, Earnings Drift, ML Ranker, MomentumEMA, Value + Quality`
- `_compute_source_hhi()` runs at scan time, no external file needed

## Smoke test (live)

```bash
cd /home/eaguiar2015/findtorontoevents_antigravity.ca
python3 -c "
import sys; sys.path.insert(0, 'alpha_engine')
from eagle_gates import apply_eagle6_admissibility, _load_dsr_noise
print(f'DSR noise: {len(_load_dsr_noise())} strategies')
"
```

Result: **27 DSR noise strategies loaded**, all gates functional, fail-open on missing data file (won't break production if `deflated_sharpe_results.json` is moved/renamed).

## Wiring

- Code: `alpha_engine/eagle_gates.py` (added `is_admissible_for_production()`, `apply_eagle6_admissibility()`, `_load_dsr_noise()`, `_compute_source_hhi()`)
- Scanner: `alpha_engine/production_scanner.py` section 6f2.7 — try/except import from `eagle_gates`; fail-open on any error
- Position in pipeline: 6f2.5 EAGLE-4 → 6f2.6 EAGLE-5 → **6f2.7 EAGLE-6** → 6f3 portfolio cap → … → emit

## Bug-class this prevents

The classic data-snooping trap. With 80+ emitters emitting daily, by chance some strategies will show positive PF on small samples. DSR (Deflated Sharpe Ratio) corrects for the multiple-comparisons problem: even a 2.5 SR is not "real" if you tested 164 strategies. EAGLE-6 enforces that the strategies we ship picks from are DSR-survived. Without this layer, a strategy that won 6 of 6 trades (statistically meaningless) could still get EAGLE-5 symbol boosts and emit at full sizing.

## Tagging

Every pick gets `_eagle6_verdict` (`ADMISSIBLE`/`INADMISSIBLE`/`UNSCORED`) and `_eagle6_gates` (dict of per-gate pass + numerics) so downstream consumers (dashboard, paper-pilot, portfolio export) can reason about the gate result without re-running it.

## Risks

- **Fail-open by design.** If `deflated_sharpe_results.json` is missing or corrupt, the gate returns picks unchanged with `_eagle6_verdict = "UNSCORED"`. This is intentional (we don't want a missing file to nuke production) but it means a misconfigured deployment could run with EAGLE-6 effectively disabled. Mitigation: pre-flight check at scan start that logs "EAGLE-6 ACTIVE (N noise strategies loaded)".
- **HHI gate over-zealous on small populations.** A strategy with 1 pick out of 1 has HHI = 1.0 and gets killed. For per-strategy concentration, a small-N universe will trigger spurious HHI kills. v2 should use a moving-window HHI or per-strategy slot count rather than per-pick share.

## Next actions

1. Run scanner 3-5 times and confirm EAGLE-6 counters (`killed_dsr`, `killed_n`, `killed_hhi`) appear in the log without breaking emissions.
2. Generate `tools/cpcv_pbo_results.json` to unblock PBO v2 gate.
3. Wire per-strategy walk-forward payload to unblock WF OOS v2 gate.
4. Add the HHI windowed-version fix to the v2 backlog.

## Cross-references

- Commit: see `git log -1 --format=%H -- alpha_engine/eagle_gates.py` (this commit)
- Sibling docs: `EAGLE4_2026-06-02_minimax-m3-free.MD`, `EAGLE3_2026-06-02_minimax-m3-free.MD`
- User-facing guide: `/updates/eagle4-eagle5-gates-2026-06-02.html` (add EAGLE-6 section in next revision)
- Swarm synthesis: `reports/EAGLE_SWARM_SYNTHESIS_2026-06-02.md` §5 (Bonferroni note: α_adj ≈ 0.000625 for 80+ emitters)
