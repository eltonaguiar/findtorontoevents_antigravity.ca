# FINALIZED PLAN — deepAI/inspect-wt (2026-11-14, post-24h-review)

**Basis:** full review of 24h of financial-prediction activity — ~100 remote commits (reproduced
total; the meaningful/`[skip ci]` split is window-dependent — 96/100 by the reviewer's API window),
`final_v3` (decision round: BUGS.md B1–B14, focus decision, shipped code), `final_v4` (review round:
6 bundle folders from 4 peers + finpredict-v4 synthesis), PRs #773–#777, plus my own `final_2026_11_14`
+ `final_v2` packages and local tree state (working-tree dirty counts are filter-dependent: 25
modified at review time; untracked count excludes `.venv*`/`node_modules`; zero new local peer work
outside my folders). *Counts cross-checked by review subagent — see `04_peer_crosscheck/`.*

## 0. What the 24h changed (consensus I adopt)

1. **Shipped code (quant-audit branch → main):** `audit_trail/stop_fill.py` (18 tests on main;
   `final_v3/README.md` says 20 — reconcile), gap-aware fill in `universal_pick_resolver.py`
   (`RESOLVER_GAP_AWARE_FILL`), `tools/per_class_cost_gate.py` (15 tests on main; README says 18;
   3× round-trip gate, default ON, deliberately fail-open),
   `after_cost_net_per_trade` in `dashboard_generator.py`, `tools/stop_fill_replay.py`
   (30 crypto + 25 equity + 25 ETF real replays), COT test (**failed 4/4 — honestly reported**):
   52 tests at final_v3, **66 after #773** (`tests/test_kimi_exit_fill.py`).
   → **B3 (final_v3): fill gap measured at 98.8% of class loss — SUPERSEDED by #773: the 98.8%/
   +727.3pp figures differenced against a drifted `stop_loss` field; the verified kimi fill
   correction is +67.5pp (crypto −837.8 → −770.3pp, PF 0.768 → ~0.80), per
   `final_v3/06_followups/2026-11-14_next_steps.md` and PR #773.**
2. **Focus decision (`final_v3/03_focus/DECISION.md`):** EQUITY = slot 1 (only class clearing
   3× cost: 3.23×, mean +0.323%, n=738, but **t=1.52 p=0.12** and #773 shows **EQUITY fails its
   SPY gate**); CRYPTO = slot 2 conditional (0.58× cost, fill fix must show forward evidence);
   ETF/FOREX/BOND/COMMODITY blocked by arithmetic; **MF = allocation, not prediction** (0 rows).
3. **final_v4 consensus:** "not profitable but now testable"; two candidates — **both legs then
   went false within ten minutes**: #773 ran the EQUITY SPY test and failed it (`NO_ALPHA_BETA`,
   t=1.05, median pick −0.57% vs SPY) and revised `DECISION.md` to **close slot 1 as a source of
   edge**, promoting CRYPTO to the only remaining candidate. Bug catalog caveat: **B7 has an ID
   collision** — final_v4's table says "all 166 cells single-source" while canonical
   `final_v3/00_common_themes/BUGS.md` B7 = FOREX composition/allowlist (fix G7); "0/166 cells
   pass all gates" is a separate quant-audit claim. B4 is **settled** (#773: the *label*, not the
   price; never-touched rates 52–56% truncated, 40–56% was the untruncated first pass). B8:
   170 ledgers, 4 pass vs 8.5 by chance. All bug IDs here are quoted with source package
   (`final_v3/07_peer_review/PEER_WORK_REVIEW_2026-11-14.md` §4: B1×3, B14×5 meanings —
   **namespace or single registry before any automation consumes them**).
4. **My standing contributions:** variant C walk-forward (reproduced by quant-audit
   `final_2026_11_14/quant-audit-2026-11-14/05_verification/` and finpredict-v2's
   `PEER_CLAIMS_MATRIX` row 6 — both "reproduced exactly", both label it NOT PROVED; clone-dedup
   robust, sub-T2), live repricing truth (703 open picks), 8 fixspecs + patches, and the
   adjudication record (mega_mutation: adjudicated VETOED / "high-risk secondary sleeve only" in
   `final_v3/hilarious-seer/01-common_themes/peer_adjudication_summary.md`; VWAP refuted in
   BUGS.md B1 conflict table + hilarious-seer adjudication).

## 1. The plan — four phases

### Phase 0 — Measurement truth (1 week, blocks everything)
Close the bugs that make any PF unverifiable. Adopt peers' shipped fixes; add:
- **B1** EXPIRED→WON mislabeling (canonical BUGS.md **B10**) + refuted-VALIDATED advertising
  (canonical **B1**): banner + relabel (my `fixspec_surface_disagreement_banner` already specifies
  this) **+ G3: every verdict carries `evidence_hash` + `generated_at`; CI greps `VALIDATED`/`PROVEN`
  and fails without a registry entry** (`final_v3/01_plan/GENERAL_FIXES.md` G3).
- **B4 — diagnosis SETTLED (#773, `--truncate-at-exit`):** the *label*, not the price (11/14 EQUITY
  and 12/13 ETF never-touched rows exited at a different level). Remaining work = reclassify
  `exit_reason` (trailing/target/max-hold), quarantine the 4 rows that never traded at their
  recorded exit price, instrument the resolver for touch-vs-fill logging. **Do not extend the
  gap-aware fill to non-crypto exits** (gap-aware makes EQUITY worse: −83.62 vs −63.41pp).
- **B5** `resolution_method`: record intrabar-vs-nominal explicitly (field exists as
  `exit_reason` = *which* trigger; we still need *how* it filled) — implement as G5's field
  contract + CI assertion (≥95% of closed rows populate `resolution_method` ∧ payload
  `exit_reason`, else build fails) (`final_v3/01_plan/GENERAL_FIXES.md` G5).
- **B7 (source-package qualified)** single-source cells: dual-source every contributing cell or
  mark `SINGLE_SOURCE`. **Turn on the existing promotion gates:** `MONEY_READY_FDR_GATE` /
  `MONEY_READY_SINGLE_SOURCE_GATE` default `"0"` at `alpha_engine/money_ready_verdict.py:180/:195`
  → `"1"` for promotion (emission stays fail-open per G5).
- **B9** stale prices (404 since Apr): **extend the existing `tools/db_freshness_check.py` +
  hourly guardian** to these three feeds (BUGS.md B9 fix line), plus wire
  `alpha_engine/universal_price_enricher.py`; hard TTL fails the build.
- **B14 (`final_v3/06_followups`) — cross-symbol stop contamination:** implied-risk sanity bound
  ≤25% at write time (ADA-USD row: +45,772pp of fake correction from one row).
- **QA enforcement:** my `02_qa/QA_PLAN.md` becomes a required CI gate (below).

### Phase 1 — QA gates (continuous, see 02_qa/QA_PLAN.md)
1. **PnL=0 validator:** every row with `pnl_pct==0` (and every blank) on **OPEN and recently-closed**
   gets independently repriced: open→closed (if `closed_at`) and open→current (if open) using
   Binance/Yahoo/open.er-api by class; flag if |stored − implied| > max(0.25%, 2σ of same-class
   residuals) or if price moved >1% while stored PnL==0.
2. **Blank-field flagger:** null `entry_price/exit_price/current_price/stop_loss/take_profit/
   closed_at/direction` on open + recently-closed → `BLANK_<field>` quarantine rows, surfaced on
   `/audit` as counts, never silently 0.
3. Exit-reasonableness: hold duration vs timeframe; exit beyond stop by >3σ of class fill error →
   B4 suspect; TP claimed without price ever reaching TP → replay (**no source found for the
   "flaxen-hair 13/24" attribution — re-measure from scratch**; peer anchor: B4 replay, n=25/class,
   4 rows never traded at their recorded exit price — `final_v3/00_common_themes/BUGS.md` B4).
4. All gates fail-closed into the money-ready score; gate results published in `dashboard_data.json`.

### Phase 2 — Candidates (what we actually trade)
Peer week-1 P0s adopted verbatim (`final_v3/03_focus/DECISION.md` 90-day sequence;
hilarious-seer todo C1/C2): route `kimi_riseoftheclaw` through the intrabar resolver; kill
CRYPTO SWING emission (n=243, PF 0.457, −328.6pp).

| Slot | Candidate | Evidence | Gate to pass | My P(success)* |
|---|---|---|---|---|
| 1 | **EQUITY — CLOSED as a source of edge (measurement baseline only)** per DECISION.md REVISION + #773 (`NO_ALPHA_BETA`: t=1.05, median pick −0.57% vs SPY, 54% underperform). Reopening requires a *new pre-registered* test with a documented trial ID (B8 discipline), not a re-run with different thresholds | variant-C equity/ETF concentration (n=232 of 237) is now a *baseline measurement*, not a candidate | benchmark-relative gate (record only) | **n/a (0% as candidate)** |
| 2 | **CRYPTO vol-targeted trend** (the ONLY remaining candidate, conditional) | ITERATION-005 + fixed fill (PF 0.768 → **~0.80 per #773 — not ≈1.00**); kimi routed through intrabar resolver; CRYPTO SWING emission killed | forward **PF ≥ 1.3, WR ≥ 55%**, n≥100, dual-source (peers' pre-registered gate, `DECISION.md` slot-2 step 3), **and** a risk-matched benchmark (TSMOM Sharpe 2.13 vs B&H ≈2.2 must be beaten — `final_v3/07_peer_review` §3) | **20–30%** (revised down: fill fix buys ~+67.5pp, not breakeven; benchmark objection open) |
| 3 | **MF/ETF allocation sleeve** (my addition — the *only* honest "solid picks" for mutual funds) | monthly momentum rotation backtested on real NAVs → `03_risk_management/` | Sharpe ≥ 0.7 net, maxDD ≤ 15%, beats 60/40 on Calmar | **60–70%** (documented risk premium, not alpha — probability is of *beating cash+fees with acceptable risk*, not of beating SPY) |

\* probability = subjective, updated by forward data; method documented in the risk page.

**Mutual funds specifically:** structurally cannot be intraday picks (NAV once daily, next-NAV
execution, 30-day frequent-trading limits — peers are right). The deliverable is a **monthly
allocation recommendation engine** (top-2 rotation across MF/ETF share classes, absolute-momentum
filter, expense-ratio ≤0.20% screen per `final_v3/03_focus/MUTUAL_FUNDS_SUBSET.md` —
`final_v3/finpredict/FOCUS_DECISION.md` separately proposes the `BENCHMARK_SLEEVE` control arm
(vs SPY); adopt it as the sleeve's control — that IS "solid picks" for this
class, on its own honest clock. Results + risk overlays: `03_risk_management/risk_management.html`.

### Phase 3 — Risk management (separate review page)
Applied to every candidate and shown on the webpage: ¼-Kelly sizing (variant C full Kelly ≈10%/trade
→ 2.5%), 12% vol targeting, per-position cap 25%, correlation cap 0.7, portfolio DD stop 15%,
historical+parametric VaR/ES at 95/99%, stress tests (July-26 scenario, 2022-style bear, crypto
−50% flash), kill criteria (two consecutive PF<0.5 months or 3-month rolling PF<1.0), and
risk-adjusted results (Sharpe/Sortino/Calmar) before vs after overlays.

### Phase 4 — Forward certification
T2 ∧ v3 ∧ new cost gate on **forward records only**: n≥100, WR≥50% with Wilson CI excluding 50%,
PF≥1.5 (slot-2 crypto interim gate: PF≥1.3/WR≥55% per peers), MDD<20% at stated sizing,
≥66% walk-forward windows positive, multiple-testing disclosure, `is_single_source_artifact=False`.
**All certification runs must be CI-green** (pandas `freq="ME"` incident: no tests-pass claim from
2026-11-14 was CI-verified before #775). Weekly pre-registered run
(scheduler `5992b142`); no re-tuning; kill criteria as above.

## 2. Explicit non-goals
No new signal mining (my V1: 46 cells, zero survivors; B8: 170 ledgers worse than chance).
No MF live-pick class. No unblocking FUTURES/COMMODITY without a real feed (veto stands).
No `mega_mutation` enablement (adjudicated VETOED / secondary-sleeve-only; single-source). No claim without dual-source + fill model.
No ITERATION-005 deployment on "tested vs zero" evidence — it must beat a risk-matched
buy-and-hold (Sharpe 2.13 vs ≈2.2 currently fails).

## 3. Risk register (top 5)
1. Equity closed as beta (#773 `NO_ALPHA_BETA`: t=1.05, median −0.57% vs SPY) → slot 1 is a measurement baseline; reopening needs a new pre-registered trial ID.
2. Fill-fix regressions (#773 settled B4; kimi booking fixed pre-/post- split) → replay harness in CI (`--truncate-at-exit`), per-class fill-error budget.
3. Data vintage drift (my Oct-23 variant-C objection) → pin payload snapshots, hash them.
4. Multiple-testing relapse (B8) → pre-registration ledger: every test recorded before run.
5. Scheduler/task decay (weekly walk-forward) → heartbeat check in `HEARTBEAT.md`.

\* P(success) definitions and full math: `03_risk_management/risk_management.html`.
