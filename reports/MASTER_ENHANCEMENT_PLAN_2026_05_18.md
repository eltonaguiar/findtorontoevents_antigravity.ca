# Master Enhancement Plan — Consolidated 2026-05-18

**Author:** Claude Opus 4.7 (Desktop 2) · Synthesis of ~20 plan/strategy `.MD` docs
produced 2026-05-17/18 by Claude, Kimi, OpenCode, FreeBuff and the strategic-fork
swarm. This doc is the **single authoritative enhancement plan** — it supersedes the
conflicting drafts listed in §4.

## 0. Authoritative posture

**Research sandbox / paper-only. Real capital stays at $0** until a signal clears
`tools/edge_stability_harness.py` (eff ≥ 0.30, same sign, ≥3/5 walk-forward windows).
7-8 straight harness kills. No asset class is money-ready — the "MONEY_READY CRYPTO
PF 2.54" verdict is an `ml_enhanced` mining artifact, retracted by `CORRECTED_GAMEPLAN`
and `EDGE_VERDICT`. Verdict-grade numbers live in `audit_dashboard/data/pf_registry.json`
(policy-clean-net), not the `/audit` tiles.

## 1. Consensus across the plans

- No edge anywhere; the existing ledger is exhausted (M-107 — do not re-hunt it).
- The harness + kill-loop is the keeper; DSR/SPA/White's pass is necessary, not sufficient.
- **Data integrity is the recurring P0 root cause** — duplicate re-emissions (83% of raw
  rows dropped downstream), COT 3-day publication lag, `ml_enhanced` placeholder stats,
  inflated dashboard tiles.
- The dashboard must tell the truth — tabs imply edge that does not exist.
- FOREX stays hard-disabled (`FOREX_HARD_DISABLE_RATIONALE.md`). FUTURES too.
- If any single bet is taken, it is **CRYPTO funding-rate / basis arbitrage**
  (structural, delta-neutral) — NOT directional, NOT a re-test of killed H-006.

## 2. Contradictions (resolved)

| Conflict | Resolution |
|----------|-----------|
| MONEY_READY CRYPTO @ 25% Kelly vs NOT_READY | **NOT_READY wins** — newer docs + Kimi's own correction header |
| 37 PRs vs 5 PRs | **5** — `CORRECTED_GAMEPLAN` self-retracts the 37-PR plan |
| Keep hunting vs accept no-edge | Sandbox is the permanent posture; ONE time-boxed 90-day probe allowed |
| New signal sources dead-end vs only path | STRAND B sidecars allowed — opt-in, harness-gated, zero production wiring |
| nb_trials 1 vs per-class | Already fixed (M-076, per-class from `ASSET_CLASS_SOURCE_SYSTEMS`) |

## 3. The master plan — priority-ordered

### Measurement / data-integrity
- **P0** Fix duplicate re-emission at the writer (83% downstream drop, 4,830 dup
  re-emissions). Fix the emitter, not downstream.
- **P0** COT 3-day publication-lag correction + CT=F concentration cap <35%
  (`quality_gates.py`, COT pipeline). M-095 killed `cot_positioning`; enforce the lag
  so it cannot recur.
- **P0** Default `/audit` per-class tiles to `pf_registry.json` policy-clean-net (#1221).
- **P0** Fix the non-crypto outcome resolver — EQUITY/FOREX/FUTURES/ETF/BOND close at
  `pnl_pct=0.0` placeholders, making 5 of 6 classes statistically invisible. **This is
  the highest-leverage task in the repo** (see `roadmap_no_edge_to_money_ready_2026_05_18.md`
  Phase 0).
- **P1** Regime-timeseries backfill — `closed_picks.json` has regime on 3/8421 rows.
- **P1** Wire the `at_pick_audit_trail` writer into `quality_gates.py` (opt-in) — the
  per-gate trace table shipped this session but is empty until wired.

### Gates / quality
- **P0** Quarantine the `ml_enhanced` family (M-105) — 147/149 variants unquarantined,
  family PF ≈ 0.64, dragging the CRYPTO aggregate.
- **P0** Promote post-cost expectancy from warning to hard gate (`charter_slippage.py`,
  `EXPECTANCY_GATE_ENABLED=1`) — net edge must keep ≥60% of gross after round-trip cost.
- **P1** Regime-conditional admissibility mode in `edge_stability_harness.py` — the
  current sign-stability-across-5-windows test kills regime-dependent edge.
- **P1** Harden incubator graduation: walk-forward `min_window_consistency=0.60`,
  `n_stability_windows=4`.

### Per-asset-class
- **P0** CRYPTO — the one active bet: funding-rate / basis *arbitrage* (delta-neutral).
  Day 1: confirm low-lag funding + spot/perp basis data; then a 2-yr delta-neutral
  backtest through the harness + the ≥60%-cost gate. (User go/no-go decision.)
- **P0** FOREX / FUTURES — stay hard-disabled; verify `FOREX_HARD_DISABLE=1` in all
  envs; do NOT enable the copytrader exempt path.
- **P1** COMMODITY / EQUITY / ETF / BOND — paper-only; re-test only after the
  regime-conditional harness ships AND a causal hypothesis is pre-registered.

### Edge research
- **P1** STRAND B sidecars (`options_flow`, `onchain_crypto`) — opt-in, zero production
  wiring, harness + cost gate, real data only. **Note:** both modules currently FAIL
  vetting (`reports/kilo_fork2_vetting_2026_05_18.md`) — fix before any wiring.
- **P1** Causal-hypothesis-before-data rule — write the economic mechanism, pre-register
  `H-xxx` in `hypothesis_registry.json`, then test only that. No data-dredging.

### UX / dashboard
- **P0** Honest empty state on "Money Ready": *"No admissible edge — 0/8 signal families
  passed walk-forward. Paper-only research sandbox."* Per-pick harness-verdict badges.
- **P0** Fix the orphaned `/audit` "💰 Money Ready" button (`applyMoneyReady()` calls
  undefined `window.renderActive`; no render path applies `filterMoneyReady()`).
- **P1** Surface the per-class pick funnel from `at_pick_flow_daily` (shipped this
  session). Filter "what-if" query over the SQLite traceability store.

### Infra / CI
- **P1** Confirm `incubator-pipeline.yml` flows green post-PR #1173.
- **P1** Keep the `pf_registry` reconcile gate in CI (PRs #1150-1152).
- **P2** Daily funding-rate collector cron — deepen the archive for a future re-test.

## 4. Superseded / stale documents

`MASTER_ACTION_PLAN_2026-05-18.md`, `MASTER_ACTION_PLAN_kimi_2026-05-18.md`,
`MASTER_ACTION_PLAN_KIMI_V2_2026-05-18.md` (false MONEY_READY premise),
`PR_PLAN_2026-05-18.md`, `PR_PLAN_kimi_2026-05-18.md` (37-PR drafts on the false
premise; reference nonexistent files), `PATH_TO_PROVEN_EDGE_2026-05-18.md` (its
candidate queue was run and killed), `plan_kimi_2026-05-18.md`,
`kimi_swarm_enhancement_plan_2026-05-18.md`. **Still current:** `EDGE_VERDICT`,
`EDGE_HUNT_CONCLUSION`, `STRATEGIC_FORK_SYNTHESIS`, `STRAND_B_PLAN`,
`INCUBATOR_REVIVAL_PLAN`, `ROADMAP_TO_EDGE`, `CORRECTED_GAMEPLAN`,
`FOREX_HARD_DISABLE_RATIONALE`, and this document.

## 5. Bottom line

The authoritative posture is research-sandbox / paper-only. The highest-value work is
**data-integrity fixes + an honest dashboard + the regime-conditional harness upgrade**,
with exactly one time-boxed edge bet — CRYPTO funding-rate basis arbitrage — pending a
user go/no-go. A truthful "not ready" dashboard is the near-term win; a falsely-green
one is a regression.

## 6. Post-vetting amendments (3-AI debate, 2026-05-18)

Vetted by Grok + opencode/DeepSeek + kilo — see `reports/PLAN_VET_DEBATE_2026_05_18.md`.
Core thesis endorsed by all 3. Adopted amendments:

- **A1 (P0)** — Add a **cost model**: net-of-cost expectancy + per-class slippage
  feeding every gate AND the harness. Funding-arb needs a *continuous*-funding cost
  model, not round-trip. Today gates run on gross/placeholder PnL.
- **A2 (P0)** — Add **timeboxes + go/no-go dates** to every phase, plus a terminal
  **"no edge → archive / shut down"** state. The plan must not be a one-way ratchet.
- **A3 (P0)** — **Phase 0b parallel track**: wire a paid data API (Polygon / Alpha
  Vantage) for EQUITY so Phase 0 does not block everything; verify the resolver
  *logic* works, not just that `closed_at` is filled.
- **A4 (P1)** — Kill-or-archive clause: a class with only stub emitters gets deleted,
  not "gathered".
- **A5 (P1)** — Funding-arb **demoted** from "the Phase-3 bet" to one gated probe:
  Day-1 data-availability check + pre-registered kill criterion (net expectancy
  after cost < 0.5%/cycle → abandon) before any 90-day sprint.
- **A6 (P1)** — Add external benchmark validation (coin-toss / spot-hold baseline);
  audit walk-forward window construction for genuine regime diversity.
- **A7 (P2)** — Codify a position-sizing protocol as a gate.
- **A8 (P1)** — Doc fixes: CRYPTO "33% / PF 0.17-0.41" is a *recent window* (full
  policy-clean ≈ PF 1.26, n≈2028); reconcile money-ready (n≥50/WR≥0.55) vs Phase-4
  (n≥100/WR≥0.52) thresholds; document what cost/dedup `pf_registry` applies.

## 7. Phase timeboxes + terminal state (A2, 2026-05-18)

The plan is NOT a one-way ratchet. Each phase has a go/no-go gate. Failure at any gate
triggers the **archive** path, not an infinite retry loop.

### Phase timeline

| Phase | Description | Start | Go/No-Go Deadline | Kill Criterion |
|-------|-------------|-------|-------------------|----------------|
| **Phase 0** | Data integrity: fix non-crypto resolver + dedup + COT lag | 2026-05-18 | **2026-06-01** | If resolver still produces >20% breakeven placeholders → pause all non-CRYPTO classes |
| **Phase 0b** | Parallel: wire paid data API (Polygon/Alpha Vantage) for EQUITY | 2026-05-18 | **2026-06-07** | If no paid feed wired → EQUITY stays INSUFFICIENT_DATA |
| **Phase 1** | Regime-conditional harness upgrade + post-cost gate to hard_reject | 2026-05-18 | **2026-06-15** | If harness eff <0.20 across all classes → declare no-edge, archive |
| **Phase 2** | Per-class OOS walk-forward on clean data | 2026-06-15 | **2026-07-01** | If PF<1.0 or WR<45% for any class after harness → archive that class |
| **Phase 3** | CRYPTO funding-rate probe (delta-neutral backtest through harness) | 2026-06-01 | **2026-06-30** | Net expectancy after cost <0.5%/cycle OR eff<0.30 → abandon |
| **Phase 4** | Paper trading → real money gate (n≥100, WR≥52%, PBO<0.10) | 2026-07-01 | **2026-08-15** | Zero classes meet gate → declare research sandbox, stop real-capital planning |

### Terminal state

If **Phase 4 go/no-go** is FAIL (zero classes meet money-ready gate by 2026-08-15):

1. Archive all strategy code to `archive/` branch — do NOT delete.
2. Dashboard becomes read-only research archive — remove all "MONEY_READY" UI.
3. Real-capital planning stops. Sports + Events goals (#2/#3) continue unaffected.
4. A new session can re-open the trading strand ONLY with a new causal hypothesis
   pre-registered in `hypothesis_registry.json` and a new harness threshold evidence base.

### Intermediate kill gates (per class)

A class enters **ARCHIVED** state (stops generating picks, no CI allocation) if it
fails any of:
- n≥50 clean resolved picks AND PF<0.90 over any rolling 30-day window
- Walk-forward eff<0.15 over 3+ consecutive windows
- Harness kill ≥5 consecutive attempts without a single admissible window
- Resolver failure rate >30% (breakeven placeholders as % of closed picks)

Once ARCHIVED, the class requires a new hypothesis + 30-day incubation before
re-admission. FOREX and FUTURES are already effectively ARCHIVED pending re-enable.

### Cost model gate promotion schedule (A1)

Current: `POST_COST_GATE_MODE=shadow` (tags picks, no rejection).
Target: `POST_COST_GATE_MODE=hard_reject` by **2026-06-01**.

Pre-conditions before promoting:
1. Shadow mode runs for ≥14 days on all classes.
2. Shadow rejection rate documented in `reports/post_cost_shadow_audit_YYYYMMDD.md`.
3. No class shows >40% shadow-rejection rate (would indicate cost model is mis-calibrated).
4. Operator sign-off on per-class slippage numbers in `alpha_engine/charter_slippage.py`.

Promoting: set `POST_COST_GATE_MODE=hard_reject` in `.env.production` (or GitHub Secret
`POST_COST_GATE_MODE`) and redeploy. Rollback: set to `shadow`.

### A4 — Kill-or-archive clause (stub emitters)

A strategy module that has produced zero picks for ≥60 consecutive days with no
in-flight harness test is eligible for deletion (not archiving) via:
```bash
python tools/dead_strategy_reaper.py --dry-run  # confirm scope
git rm alpha_engine/<stub_strategy>.py           # delete
```

No stub emitters are to be "gathered" — they consume CI time and create confusion
about what is production-live.
