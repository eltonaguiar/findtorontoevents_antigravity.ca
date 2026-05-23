# M-055 — Kill-Threshold Re-Calibration: Audit + Wire-In Target Map — 2026-05-15

> **Status note (2026-05-15):** the statistical kill-gate itself — `audit_trail/kill_gate.py` (min-n floor + binomial p-value + Wilson 95% CI, 18 tests) — was shipped by a peer agent via **PR #1068 (MERGED)**. This document is therefore NOT a build proposal; it is the **kill-mechanism audit + wire-in target map** for the remaining M-055 follow-up: routing the three legacy kill mechanisms through `kill_gate.py` after re-auditing each `*_BLACKLIST`. Sections 1-5 below remain the authoritative inventory of what must be re-routed.

## Why this is the P0

Every finding in the 2026-05-15 cotton/kill-calibration session converged on one root cause: **the system kills strategies and symbols on statistically-insufficient evidence, and calibrates its kill thresholds on in-sample data that includes the strategies about to be killed.** This is a self-reinforcing downward ratchet — the tradeable universe shrinks every cycle, which is why the project has been "stuck in paper trading for months."

Proof points already on record:
- Cotton CT=F was killed (Phase 2-D, 2026-04-29) on a cited "n=12 WR 8.3%". The actual resolver-v2 outcomes for those exact 12 picks were **WR 66.7% / PF 3.50** (`reports/deep_dive_cotton_2026-05-15.md`, PR #1061).
- KC=F (coffee) cites the **identical** "n=12 WR 8.3%" at `quality_gates.py:1263` — 8.3% = 1/12, i.e. "1 win, 11 unresolved-counted-as-loss". Systematic panel-time resolver bug.
- A `/swarm-second-opinion` (DeepSeek + Kilo, both HIGH confidence) independently identified kill-threshold mis-calibration — not kill-without-replacement — as the deeper root cause.

## Audit — current kill mechanisms

Five kill mechanisms found. Thresholds and data sources as of 2026-05-15:

### 1. `alpha_engine/commodity_kill_switch.py`

| Line | Constant | Value |
|---|---|---|
| :37 | `_PF_KILL_THRESHOLD` | 0.9 |
| :38 | `_DECAY_KILL_THRESHOLD` | 0.15 (15pp) |
| :39 | `_MIN_TRADES_FOR_PF_KILL` | 20 |
| :40 | `_MIN_TRADES_FOR_DECAY_KILL` | 15 |
| :41 | `_MIN_TRADES_FOR_ZERO_WR_KILL` | 15 |

Data source: `closed_picks.json` / `universal_resolved_picks.json` (lines 73-91). Walk-forward verdict: **NOT consulted.** Kills on n=15 — below a defensible floor.

### 2. `alpha_engine/fx_kill_switch.py`

Lines :32-36 — **thresholds identical to commodity** (PF<0.9, decay>15pp, min n 15-20). Walk-forward verdict: NOT consulted. No significance test.

### 3. `alpha_engine/strategy_killer.py` — **most dangerous**

`KILL_CRITERIA` at :57-65:

| Criterion | Threshold | Min trades |
|---|---|---|
| `wr_zero` | 0% WR | **3** ⚠️ |
| `wr_low` | < 25% WR | 5 |
| `pf_low` | PF < 0.5 | **5** ⚠️ |
| `pnl_dollar_floor` | −$500 | none |
| `max_consec_losses` | 5 | none |
| `avg_rr_floor` | 0.5 | 5 |

Kills on **n=3** (`wr_zero`). At n=3 a single trade outcome flips the verdict. This is the cotton failure mode in code form. Data source: aggregated from 5 sources (closed_picks, universal_resolved, track_record, strategy_performance, dashboard_payload). Walk-forward verdict: NOT consulted.

### 4. `audit_trail/quality_gates.py` — hard-coded lists

- `PERMANENTLY_KILLED_STRATEGIES` (:1052-1185) — 134 entries, growing.
- `COMMODITY_BLACKLIST` (:1266-1290) — 24 symbols.
- `BLOCKED_ASSET_STRATEGY_PAIRS` (:1819+) — 40+ tuples.
- `BLOCKED_ASSET_STRATEGY_SYMBOL_TRIPLES` (:2061) — surgical blocks.

Min-n required before a name is added: **NONE** — these are hand-maintained blacklists. No calibration logic in code.

### 5. `alpha_engine/walk_forward_validator.py` — orphaned

`MIN_TRADES = 20`, `NUM_WINDOWS = 5` (:43-44). Emits ROBUST / MODERATE / FRAGILE verdicts from window-consistency. **Zero callers in any kill mechanism.** The one tool that could make kills statistically honest is not wired in.

## Key findings

1. **Statistically invalid floors.** `strategy_killer.py` kills on n=3 / n=5. No sample this small can distinguish a dead strategy from a high-variance live one.
2. **No significance testing.** Every gate is a deterministic threshold (`PF < 0.9`, `WR < 25%`). None asks "is the observed WR significantly below break-even, or is this noise?"
3. **Walk-forward validator orphaned.** ROBUST/FRAGILE verdicts exist but feed nothing.
4. **Data-source mismatch.** Commodity/FX switches read `closed_picks.json` (mixes pre/post resolver-v2 records); `quality_gates` reads aggregated `dashboard_payload`. No mechanism reads a single unified resolver-v2 ledger.
5. **Blacklists uncalibrated.** 134 permanently-killed strategies + 24 blacklisted commodity symbols, none gated by a min-n or significance check at add-time.

## Proposed recalibration

| Mechanism | Current cutoff | Proposed cutoff | Min-n | Statistical test to add |
|---|---|---|---|---|
| Commodity PF kill | PF<0.9 @ n≥20 | PF<0.8 @ n≥50 | 50 | Binomial p-test on WR vs break-even |
| Commodity WR=0% kill | WR=0% @ n≥15 | WR=0% @ n≥30 | 30 | Binomial: reject only if WR sig. < break-even @ 95% |
| Commodity decay kill | decay>15pp @ n≥15 | decay>20pp @ n≥50 | 50 | Rank-sum on window decay |
| FX kill (all rules) | = commodity | separate per-class gate | 50 | Bayesian WR posterior |
| `strategy_killer` WR=0% | n≥3 ⚠️ | n≥50 | 50 | Binomial + walk-forward FRAGILE corroboration |
| `strategy_killer` PF<0.5 | n≥5 ⚠️ | n≥50 | 50 | Likelihood-ratio test |
| Permanent-kill / blacklist add | hand-maintained | require min-n gate at add-time | n/a | Recompute from resolver-v2 ledger before adding |

Design principles for the recalibrated kill gate:
- **(a) Min-n floor.** No kill on fewer than 30 (WR=0% case) or 50 (PF/decay) clean resolved trades.
- **(b) Significance test.** A kill fires only when a binomial / Bayesian test rejects "WR ≥ break-even" at 95%. A low point-estimate WR on small n is not sufficient.
- **(c) Walk-forward corroboration.** Wire `walk_forward_validator` — a FRAGILE verdict is a required corroborating signal for a kill; a ROBUST/MODERATE verdict blocks the kill pending more data.
- **(d) Single data source.** All kill mechanisms read the resolver-v2 ledger only — never `closed_picks.json` snapshots that may contain unresolved picks counted as losses.

## Remaining wire-in plan (post PR #1068)

`audit_trail/kill_gate.py` already exists (PR #1068). The shared helper this spike originally proposed is shipped — under the name `kill_gate`, not `kill_eligibility`. Remaining M-055 follow-up:

1. **Route the three legacy mechanisms through `kill_gate.py`.** `commodity_kill_switch.check_strategy_for_kill`, `fx_kill_switch`, and `strategy_killer` must call the gate and delete their local threshold constants (`commodity_kill_switch.py:37-41`, `fx_kill_switch.py:32-36`, `strategy_killer.py:57-65`). Wire it as an **override that can only make a kill more conservative** — that makes default-on safe (the gate never kills something the old logic kept).
2. **Re-audit each `*_BLACKLIST` before enforcement flips on.** `PERMANENTLY_KILLED_STRATEGIES` (134), `COMMODITY_BLACKLIST` (24), `BLOCKED_ASSET_STRATEGY_PAIRS` (40+) — recompute each entry against the resolver-v2 ledger through `kill_gate`. Produce `reports/kill_recompute_*.md` listing which kills survive.
3. **Un-blacklist the kills that fail the gate.** Cotton CT=F is the proven first case; GC=F / SI=F pending a full-ledger recompute (their cited n=91/n=181 may live outside `recent_closed`).
4. **Only then** proceed to M-056 (incubator) and M-058 (auto-spawn).

> Coordination note: a peer agent is actively performing the `quality_gates.py` wire-in. This doc is the shared target map for that work — it is a reference, not a competing implementation.

## Provenance

- Audit performed by `caveman:cavecrew-investigator` subagent, 2026-05-15.
- Root-cause framing: `/swarm-second-opinion` run `swarm_runs/second-opinion-20260515T080442Z` (DeepSeek + Kilo).
- Companion findings: `reports/deep_dive_cotton_2026-05-15.md`, `daily_ideas.md` 2026-05-15 entries, PR #1061 / #1064 / #1065.
