# audit2 + audit3 review — findings, corrections, and forward plan

**Author:** kilo (vanilla-handsaw worktree)
**Branch:** `add-strategy-variable-tracking`
**Date:** 2026-11-19 (corrected against peer review, 17:15Z)
**Handoff:** `COMS_AUDIT2_3_HANDOFF_2026-11-19.md`
**Related fix doc:** `updates/2026-11-19-audit3-tribunal-f1f2-n1-n2-n3-n4-n5-n7.md`
**Peer artifacts:** `witty-fight/COMS/HANDOFF_witty-fight_2026-11-19T1700Z_audit2_audit3_correctness.md`,
`witty-fight/COMS/AUDIT2_REVIEW_FOR_PEERS.md`,
`witty-fight/COMS/REVIEW_vanilla-handsaw_audit2_audit3_2026-11-19.md`

> **Canonical state (read this first).** The source repo
> `/home/eaguiar2015/findtorontoevents_antigravity.ca` is on branch
> `feat/audit3-p0-p1-correctness` (commits `3dfa66e`, `a92129a`), and
> `origin/main` already carries most of that work (G8 selection-alpha gate,
> `required_n_mde`/`power_analysis`, the H-BABY-EQUITY ingest condition, the
> denylist watchdog, `audit_dashboard/audit2.html|js`, and
> `data/audit2_forward.json`). See `COMS_HANDOFF_2026-11-19.md` for the canonical
> handoff. What is **still missing on `origin/main`**: the audit2 deploy wiring in
> `.github/workflows/audit-dashboard.yml` (no `audit2` references) and
> `tests/test_audit2_page_deploy.py`. Everything below is a review of the live
> surfaces plus the corrections a peer review required.

> **Status correction (important).** An earlier draft of this doc presented the
> F1/F2/N1–N5/N7 work as an unlanded branch. That is wrong. `origin/main` is
> **1,146 commits ahead** of this worktree and already contains every one of those
> gates (`PERSISTENCE_RUNS`, `_circular_blocks`, `recency_ok`,
> `materiality_floor`, `MATERIALITY_COST_FRACTION`, `stress_2x_ok`, the workflow
> `--history`/`--max-churn` flags, the freeze gate and its tests, and the N5
> selection-alpha fields). **This branch is documentation-only; do not cherry-pick
> its code diffs or you will delete 275 lines from main's tribunal.** The only new
> files are this doc, the COMS handoff, and the corrected numbers in the fix doc.

---

## 0. Ground truth (verified live, 2026-11-19)

| Surface | State |
|---|---|
| `findtorontoevents.ca/audit` | 1.4 MB unified dashboard |
| `findtorontoevents.ca/audit2` | 6.8 KB candidate/methodology library; `audit2.js` 11,404 B |
| `findtorontoevents.ca/audit3` | Quant Kill Tribunal; ledger + evidence sidecars |
| `audit3_ledger.json` | generated 2026-11-19T13:02:16Z |

### audit3 ledger (live)

| Signal | Value |
|---|---|
| `n_rows` (canonical scored) | 8,605 |
| `total_closed_picks` | 14,632 → **58.8% scored, 41.2% not scored** |
| `valid_closed_picks` | 8,175 → `scored_share_of_valid_pct` **105.26 (impossible)** |
| `n_cells_tested` / `n_cells_total` | 67 / 359 |
| `n_proven` / `n_candidate` | **0 / 0** |
| `n_weak` / `n_kill` / `n_insufficient` | 59 / 8 / 292 |
| `n_kill_classes` / `n_kill_symbols` | 3 / 10 |
| `persistence` | `runs_required 2`, `n_promoted_this_run 1`, `n_demoted_this_run 0`, `history_cells 446` |
| `verdict_churn` | `n_tracked 438`, `n_flipped 0`, `alert false` |
| `forward_gate.enforced` | true; 430 rows, all H-119 |
| `forward_gate.hypotheses.H-119` | `pf_ci_lb 0.9213 ≤ 1.0`, `IR 0.043 < 0.5`, `benchmark_coverage 0.798 < 0.90` |
| `forward_gate.pods.POD-EQUITY-BREAKOUT` | `n_forward 0` |
| `selection_alpha.available` | **false** — 0 of 7 class rows carry alpha/hold fields |
| `zero_pnl_count` | 134 (timeout/flat exits retained) |
| canonical exclusions | `invalid_row 5,802 + mirror_duplicate 92 + non_performance_exit 43 + resolver_breakeven_fallback 90 = 6,027` |

Live measured costs: CRYPTO **0.0993**, FOREX **0.0291**, EQUITY/ETF 0.05,
COMMODITY/FUTURES 0.15 (≈5× FOREX, not the 0.0996/0.02 quoted in an earlier draft).

---

## 1. What the gates do (confirmed on main, not this branch)

Each item below is present on `origin/main` and, where visible in the live ledger,
operating as described. This section records *why* each gate exists so a future
agent does not weaken one by accident.

- **F1 block bootstrap** — `_circular_blocks` + `bootstrap_mean_ci(..., block=True)`
  for the G2 net CI and 2× cost stress. Overlapping picks are autocorrelated; an
  i.i.d. resample makes the CI too tight and inflates promotion. Default stays
  i.i.d. so callers cannot silently change a verdict.
- **F2 split-half materiality** — `split_half_ok(..., min_mean=floor)`. "Positive"
  is not "material"; a +0.001% half must not count as stable.
- **N1 repeated-looks (persistence)** — a `CANDIDATE`/`PROVEN_T2` must persist
  across 2 consecutive runs; `first_pass_at` records the streak start. Live:
  `n_promoted_this_run 1` while the granted count is 0 — the gate is doing exactly
  its job.
- **N2 churn monitor** — `raw_verdict` stamped before the persistence hold;
  fail-closed (`exit 3`) above 30% churn so a churning ledger is never published.
  Live: 0 flips / 438 tracked.
- **N3 recency gate** — trailing `max(5, 25%·n)` closes must have non-negative net
  mean; `PROVEN_T2` caps at `CANDIDATE` on a stale regime. Symmetric to the
  window-bias that can spuriously kill longs.
- **N4 cost-scaled materiality** — `max(0.05, 0.5·mean cost)`; a crypto cell
  cannot promote on an edge smaller than half the cost it overcame.
- **N5 hold-time-normalised selection alpha** — fields exist in the code, but the
  live ledger does not publish them (`available=false`). **Treat as code-only.**
- **N7 freeze gate** — `reports/strategy_freeze.json` (P0 = E11/E13/E14) +
  `tools/strategy_freeze_gate.py`, enforced first in
  `forward-test-new-strategies.yml`. Do not generate new strategies while a P0
  item is open.

**Test count (corrected):** the three files changed here give **49 passed**
(`tests/test_audit3_tribunal.py` 34 + `tests/test_audit3_selection_alpha.py` 11 +
`tests/test_strategy_freeze_gate.py` 4). The earlier "86" added unrelated suites
without naming them; do not repeat that.

---

## 2. Open defects, ranked (with owners)

### audit3

1. **Coverage denominator contradiction (P0, owner: main).** 8,605 scored vs 8,175
   "valid" → 105.26%; 430 rows unaccounted. The witty-fight worktree has a fix
   (`scored_share_of_valid_pct = None` above 100, keep `_raw`, add
   `valid_denominator_inconsistent`, `denominator_reconciliation` with the 430-row
   bucket). **Land that first, then build N6 on the reconciled denominator.**
2. **Auto-expired wording is false (P0/P1, owner: main).** "Dropped before scoring
   and never counted" is wrong in canonical mode — timeouts that pass integrity
   are retained (`zero_pnl_count 134`). Use mode-aware wording (witty-fight has it).
3. **Candidate KPI contradicts its own table (P1, owner: main).**
   `summary.n_candidate = 0` while `symbols` has FOREX AUDJPY LONG n=31, WR 0.8065,
   PF 8.6353, q=0.034, verdict CANDIDATE. Add `n_candidate_symbols` /
   `n_candidate_segments`; page labels "Candidate cells" vs "Candidate symbols".
4. **Forward benchmark coverage 79.8% (P1, owner: main).** Root cause is a
   right-edge query window, not missing data: 63 of 87 null legs sit at each
   symbol's latest exit. Fix is a lookahead pad in `forward_observations_ingest`
   (witty-fight has it, with 2 regression tests). **Residual:** backfill the 87
   null legs and schedule the ingest — no workflow runs it, which is why
   `POD-EQUITY-BREAKOUT` still shows 0 forward rows.
5. **Provenance leaks a build path (P2, owner: main).** `source: /tmp/audit3/…`;
   embed commit SHA + input SHA-256 + generator version.
6. **N5 not published (P2, owner: main).** Emit the alpha/hold fields in the
   ledger before citing them.

### audit2

7. **Deploy target is dead (P0, owner: main).** CI uploads the page to `/audit/`
   (404); the live page is `/audit2/` (200). Refs:
   `.github/workflows/audit-dashboard.yml:1286-1304,1418-1435,1479-1496`;
   `tools/deploy_audit_files.py:147-149`.
8. **Deploy test is a false green (P0, owner: main).**
   `tests/test_audit2_page_deploy.py:29-44` asserts filenames appear in the
   workflow, not that the URL resolves.
9. **False data-source claim (P0/P1, owner: main).** `audit2.html:112` says every
   live number comes from `audit3_ledger.json`; the forward clock reads
   `audit2_forward.json` and 7 of 9 sections are static arrays.
10. **Pods are not joined to the ledger (P1, owner: main).** Six pods hardcoded in
    `audit2.js:6-25`; `H-2026-11-19-01..05` exist only there. Render from a
    web-served confirmatory sidecar and show zero-row pods from
    `ledger.forward_gate.pods` so `POD-EQUITY-BREAKOUT` is visible.
11. **Sidecar drift (P1, owner: main).** Repo 08:41 vs live 13:02 vs tdotevent
    09:04 (`n_rows` 8,735 vs 8,605). Generate it in CI.
12. **P2 cleanups.** First ledger path always 404s (`audit2.js:138`); cost figures
    are prose (`audit2.html:88`); `POD-LUXALGO-SHORT` mislabelled "Retired" though
    the manifest says `post_hoc`; no nav links.

---

## 3. Merge order (do this, not a branch merge)

1. **Coverage honesty** (defect 1 + 2) — unblocks honest N6.
2. **audit2 deploy + real-URL test** (defects 7 + 8) — the page currently 404s at
   its CI target.
3. **Forward benchmark window** (defect 4) + backfill the 87 null legs + schedule
   the ingest.
4. **Candidate counters** (defect 3).
5. **audit2 pods from the ledger** (defect 10) + CI sidecar (defect 11).
6. **Docs/cost literals** (defect 12).
7. **N6** on the reconciled denominator; **E11/E13/E14** stubs under the N7 freeze.

Do **not** merge `audit2-page-*` worktrees — they carry no unique code; they are
purpose labels.

---

## 4. Decisions grounded in data

- **E8 vs E3 → E3 (equity breakout).** `POD-EQUITY-BREAKOUT` is already
  pre-registered and does not depend on the broken FX feed. E8 adds a new surface
  before the measurement holes close.
- **FX backfill → bounded by the freeze criterion.** Backfill until `fx_prices`
  covers ≥90% of the ledger span, then stop. Do not fund beyond the criterion.
- **E12 clock → 90 days.** H-119 accumulated 430 rows over ~9 months (~1.6/day),
  so n=100 takes ~60 days; a 30-day clock would fail pods for lack of time, not
  lack of edge.
- **Expect no promotion from coverage alone.** H-119 also fails `pf_ci_lb` and
  `IR`; coverage is one of three independent failures.

---

## 5. What would make me push back

- Any change that weakens a gate's default without a fail-closed test.
- Any change that demotes a `KILL`/`WEAK` verdict (doctrine).
- Publishing a coverage percentage from the contradictory denominator.
- Cherry-picking this branch's **code** diffs onto main — they are older than
  main's and would delete working gates.
- Registering a second premium pod before E11/E13/E14 close.

---

## 6. File map

**New on this branch (docs only):**
- `docs/AUDIT2_3_REVIEW_KILO_VANILLAHANDSAW_2026-11-19.md` (this file)
- `COMS_AUDIT2_3_HANDOFF_2026-11-19.md`
- `COMS_FINAL_SUMMARY_VANILLAHANDSAW_2026-11-19.md`
- corrected: `updates/2026-11-19-audit3-tribunal-f1f2-n1-n2-n3-n4-n5-n7.md`

**Already on `origin/main` (do not re-land):**
- `alpha_engine/audit3_tribunal.py`, `alpha_engine/audit3_selection_alpha.py`,
  both workflows, `tools/strategy_freeze_gate.py`, `reports/strategy_freeze.json`,
  `tests/test_audit3_*`, `docs/AUDIT3_REVIEW_2026-11-19.md`,
  `docs/FUND_MANAGER_QUICK_VIABLE_PLAN_2026-11-19.md`.

**Not mine (leave alone):** all `[skip ci]` auto-update commits and data files
(`pead_earnings_cache.json`, `recent_exits.json`, `pcg5_log.json`,
`ab_router_log.jsonl`, `broadcast_drain.jsonl`, `failover_cache/*`, `etf_vix_gate_log.jsonl`,
`reports/forex_carry_backtest_20261119.json`).
