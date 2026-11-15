# FINALIZED PLAN — deepAI/inspect-wt (2026-11-14, post-24h-review)

**Basis:** full review of 24h of financial-prediction activity — 100 remote commits (18 meaningful,
82 `[skip ci]` churn), `final_v3` (decision round: BUGS.md B1–B14, focus decision, shipped code),
`final_v4` (review round: 5 peer bundles + synthesis), PRs #773–#777, plus my own `final_2026_11_14`
+ `final_v2` packages and local tree state (26 modified / ~358 untracked files — all May–June
leftovers, mtime-verified; zero new local peer work outside my folders).

## 0. What the 24h changed (consensus I adopt)

1. **Shipped code (quant-audit branch → main):** `audit_trail/stop_fill.py` (20 tests),
   gap-aware fill in `universal_pick_resolver.py` (`RESOLVER_GAP_AWARE_FILL`),
   `tools/per_class_cost_gate.py` (18 tests, 3× round-trip gate, default ON),
   `after_cost_net_per_trade` in `dashboard_generator.py`, `tools/stop_fill_replay.py`
   (30 crypto + 25 equity + 25 ETF real replays), COT test (**failed 4/4 — honestly reported**).
   → **Crypto stop-fill = 98.8% of class loss is now modeled (B3 fixed).**
2. **Focus decision (`final_v3/03_focus/DECISION.md`):** EQUITY = slot 1 (only class clearing
   3× cost: 3.23×, mean +0.323%, n=738, but **t=1.52 p=0.12** and #773 shows **EQUITY fails its
   SPY gate**); CRYPTO = slot 2 conditional (0.58× cost, fill fix must show forward evidence);
   ETF/FOREX/BOND/COMMODITY blocked by arithmetic; **MF = allocation, not prediction** (0 rows).
3. **final_v4 consensus:** "not profitable but now testable"; two candidates; B1–B14 catalog
   (B4 open = 40–56% of non-crypto SL_HIT never touched the stop; B7 all 166 cells single-source;
   B8 170 ledgers 4 pass vs 8.5 chance).
4. **My standing contributions:** variant C walk-forward (reproduced twice by peers, clone-dedup
   robust, sub-T2), live repricing truth (703 open picks), 8 fixspecs + patches, and the
   adjudication record (mega_mutation disputed 2-v-1; VWAP falsified twice).

## 1. The plan — four phases

### Phase 0 — Measurement truth (1 week, blocks everything)
Close the bugs that make any PF unverifiable. Adopt peers' shipped fixes; add:
- **B1** EXPIRED→WON mislabeling + refuted-VALIDATED advertising: banner + relabel (my
  `fixspec_surface_disagreement_banner` already specifies this).
- **B4** non-crypto SL_HIT-inside-stop (deepest open bug): instrument resolver to log
  touch-vs-fill; replay harness already exists — run it on all classes, publish per-class fill error.
- **B5** `resolution_method`: record intrabar-vs-nominal explicitly (field exists as
  `exit_reason` = *which* trigger; we still need *how* it filled).
- **B7** single-source: dual-source every contributing cell or mark `SINGLE_SOURCE`.
- **B9** stale prices (404 since Apr): wire `universal_price_enricher` + staleness guard.
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
   B4 suspect; TP claimed without price ever reaching TP (flaxen-hair's 13/24 finding) → replay.
4. All gates fail-closed into the money-ready score; gate results published in `dashboard_data.json`.

### Phase 2 — Candidates (what we actually trade)
| Slot | Candidate | Evidence | Gate to pass | My P(success)* |
|---|---|---|---|---|
| 1 | **EQUITY** (variant C selector + RSI(2) H10) vs **SPY benchmark** | variant C fwd n=237 PF 1.26 (equity/ETF 232); peers' cost screen 3.23× | OOS Sharpe ≥ SPY **and** PF ≥ 1.15, both-half PF ≥ 1.05 (pre-registered, 24mo, n≥500) | **35–45%** (beta risk is real: #773 already failed one SPY gate) |
| 2 | **CRYPTO vol-targeted trend** (conditional) | ITERATION-005 + fixed fill (PF 0.768→≈1.00) | forward PF ≥ 1.15 after fill fix, n≥100, dual-source | **25–35%** (conditional on fill fix holding OOS) |
| 3 | **MF/ETF allocation sleeve** (my addition — the *only* honest "solid picks" for mutual funds) | monthly momentum rotation backtested on real NAVs → `03_risk_management/` | Sharpe ≥ 0.7 net, maxDD ≤ 15%, beats 60/40 on Calmar | **60–70%** (documented risk premium, not alpha — probability is of *beating cash+fees with acceptable risk*, not of beating SPY) |

\* probability = subjective, updated by forward data; method documented in the risk page.

**Mutual funds specifically:** structurally cannot be intraday picks (NAV once daily, next-NAV
execution, 30-day frequent-trading limits — peers are right). The deliverable is a **monthly
allocation recommendation engine** (top-2 rotation across MF/ETF share classes, absolute-momentum
filter, expense-ratio ≤0.20% screen per finpredict-v3's subset) — that IS "solid picks" for this
class, on its own honest clock. Results + risk overlays: `03_risk_management/risk_management.html`.

### Phase 3 — Risk management (separate review page)
Applied to every candidate and shown on the webpage: ¼-Kelly sizing (variant C full Kelly ≈10%/trade
→ 2.5%), 12% vol targeting, per-position cap 25%, correlation cap 0.7, portfolio DD stop 15%,
historical+parametric VaR/ES at 95/99%, stress tests (July-26 scenario, 2022-style bear, crypto
−50% flash), kill criteria (two consecutive PF<0.5 months or 3-month rolling PF<1.0), and
risk-adjusted results (Sharpe/Sortino/Calmar) before vs after overlays.

### Phase 4 — Forward certification
T2 ∧ v3 ∧ new cost gate on **forward records only**: n≥100, WR≥50% with Wilson CI excluding 50%,
PF≥1.5 (candidates: ≥1.15 interim), MDD<20% at stated sizing, ≥66% walk-forward windows positive,
multiple-testing disclosure, `is_single_source_artifact=False`. Weekly pre-registered run
(scheduler `5992b142`); no re-tuning; kill criteria as above.

## 2. Explicit non-goals
No new signal mining (my V1: 46 cells, zero survivors; B8: 170 ledgers worse than chance).
No MF live-pick class. No unblocking FUTURES/COMMODITY without a real feed (veto stands).
No `mega_mutation` enablement (disputed 2-v-1, single-source). No claim without dual-source + fill model.

## 3. Risk register (top 5)
1. Equity candidate is beta (p=0.12; SPY gate already failed once) → benchmark-relative gate kills it honestly.
2. Fill-fix regressions (B4 open) → replay harness in CI, per-class fill-error budget.
3. Data vintage drift (my Oct-23 variant-C objection) → pin payload snapshots, hash them.
4. Multiple-testing relapse (B8) → pre-registration ledger: every test recorded before run.
5. Scheduler/task decay (weekly walk-forward) → heartbeat check in `HEARTBEAT.md`.

\* P(success) definitions and full math: `03_risk_management/risk_management.html`.
