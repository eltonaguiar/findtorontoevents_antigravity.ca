# Feedback on the cross-agent plan (`d9b004db…/plan.md`)

**Reviewer:** Kilo (vanilla-handsaw) · **Date:** 2026-11-19T19:10Z
**Plan under review:** "Plan — Money-maker per asset class…$2k pick…LIVE short-term sim loop"
(copilot session `d9b004db-79cc-4f99-b5f6-5418f84ef36f`), published here as
`docs/CROSS_AGENT_PLAN_money_maker_2026-11-19.md`.
**Method:** every number below was re-derived from the live ledger (`18:32:40Z`) or the named
repo file. `[V]` = I printed it; `[?]` = could not verify (search APIs were down).

---

## 1. Verdict

**Good plan, broadly correct, and it agrees with my independent work on the two conclusions that
matter: real money → ETF tactical rotation; short-term trading → paper only.** It should be
merged with five corrections and four additions before anyone builds from it.

Highest-value parts: the base-rate priors (Brazil 97%, Taiwan −23.9bp/day), publication decay
(McLean & Pontiff), the cost/turnover argument, and the "forward tests verify execution
honesty, not alpha" framing. Those are the right priors and they are usually omitted.

## 2. Verified — these claims hold

| Claim | Check |
|---|---|
| Selection alpha is **negative**: −0.276%/trade, 95% CI [−0.506, −0.043], n=3,192 | `[V]` live ledger `selection_alpha.overall`: `alpha_pct=-0.2763`, `alpha_ci=[-0.506,-0.0427]`, `n=3192`. Correct, and it is the most important number on the pages |
| 277 distinct strategies; the `/audit` top sleeves do not exist among audit3 cells | `[V]` 277 distinct `cells[].strategy`; `Multi-Timeframe Trend Alignment`, `AuditEnsemble_LONG`, `Price Acceleration Detector`, `non_crypto_consensus` all absent. The reconciliation task (C) is real |
| 0 PROVEN / 0 CANDIDATE | `[V]` summary `n_proven=0`, `n_candidate=0` — **cell-level**; see correction 4 |
| CRYPTO KILL n=6,740, PF 0.84 | `[V]` class row matches |
| ETF TAA: top5-6m Sharpe **0.88** vs SPY **0.74**, MaxDD **−19%** vs **−51%**, 2007–2026, positive in all three thirds | `[V]` `reports/TACTICAL_ROTATION_EDGE_2026-07-04.md:43-58`. Citation is accurate; VAA-G4 (0.77 / −20%) and PAA (0.93) corroborate |
| `verified_strategies/paper_pilot/` is the right harness to reuse | `[V]` exists, incl. `faber_taa_pilot.py`. (A sparse checkout can make this look absent — it is not) |
| Forward pods all `n_forward=0` | `[V]` `audit2_forward.json` = 430 rows, all H-119 |

## 3. Five corrections before building

1. **PDT claim is unverified.** The plan states the $25k pattern-day-trader rule was repealed by
   "FINRA Notice 26-10 (effective 2026-06-04)". No link, and I could not verify it today `[?]`.
   Do not base the equity-day-trading case on it. If true, my own
   `docs/ALLOCATION_2000_AND_LIVE_SIM_PLAN_2026-11-19.md` needs the same correction — so this
   cuts both ways. Action: link and read the notice, then patch both docs. Note the Brazil/Taiwan
   base rates stand either way, so the conclusion ("still a losing game") does not change.
2. **Forward-gate mismatch.** The plan gates on "n≥100, PF CI-LB>1.0". audit3 does **not** use a
   PF CI. Its gates are: CANDIDATE = n≥30, net CI>0, q≤0.20; PROVEN_T2 = n≥100, net CI>0 at
   **2× class slippage**, DSR≥0.95, BH q≤0.10, split-half stable, concentration caps
   (`alpha_engine/audit3_tribunal.py:38-46`). Align the sim's "eligible" rule to that, or the
   sim will report promotions the ledger does not recognise.
3. **`/audit` table conflates cohorts.** CRYPTO "PF 0.26, n=3,726" mixes the policy-clean PF
   (0.258) with the honest-cohort n (3,724). Policy-clean n is ~22,455. Label the cohort per row;
   an unreconciled mixed table is the exact defect the review flagged.
4. **"0 CANDIDATE" is cell-scoped.** The symbol bucket carries a CANDIDATE: **FOREX/AUDJPY LONG,
   n=33, net CI [0.242, 0.942]** — the only cell on either surface whose net CI is entirely above
   zero. Worth a line, and it is single-symbol so it stays a lead, not evidence.
5. **"Unstick the ETF pilot" is necessary but not sufficient.** The deeper blocker is cohort
   membership: dry-run ingest today = cohort 3,764 → admissible 430 (all H-119) → **3,334
   unmatched**, and the EQUITY/ETF breakout pod's four strategies are **absent from
   `at_signal_outcomes`** entirely. Fixing the pilot's close logic will not produce forward rows
   until the emitters record intrabar outcomes for them.

## 4. Unverified — do not build on yet `[?]`

- "Crypto funding carry compressed to ~2.7–6%/yr pre-fee (2026)". No source in the plan; the
  figure drives the "not worth building" conclusion, so it needs a citation.
- "Kalshi maker 1.75% vs taker ~7%", "Polymarket 67–70% of users lose", "maker cuts P(loss) by
  9.3pp". Directionally plausible, all uncited.
- "SR 1.0 needs ~9 years for t=3". Depends on the sampling assumption; fine as a teaching line,
  not as a gate.

## 5. Four additions from my verified work (not in the plan)

1. **Denominator mismatch.** audit3 scores a *payload slice*: 3,500 of 16,330 closed rows
   (21.43%), and the ledger says so in `coverage.denominator` ("NOT the same denominator as
   /audit"). Any `/audit` vs `/audit3` comparison is cross-population until reconciled.
2. **Data debt that outranks strategy work.** 22,947 ghost rows (top cohort: MEMECOIN
   `meta_strategy` DOGEUSDT, n=3,569 from **one** entry), 94,119 "open" vs 21 active,
   `db_health.any_red=true`, `harness_healthy=false`. `strategy_tribunal_latest.json` is absent
   from main, so the `/audit` tribunal panel renders from nothing.
3. **Reporting integrity now fixed.** 11 WEAK cells had `reasons==[]`; every WEAK now states its
   blocker, and the summary publishes `n_candidate_symbols` + `summary_scope` (landed
   `3e0ed934547`). The ingest now also reports `unmatched_top` by strategy, which is how the
   blocker in correction 5 became visible.
4. **Only 3 of 67 cells with n≥20 have a net-CI lower bound above zero** — `macd_rsi_m048` (n=24),
   `strong consensus` (n=24, PF 1,098 = artifact), `forex_rsi2_mean_reversion` (n=24). Everything
   else, including the best-looking breakout cells, has a CI straddling zero.

## 6. Where I agree, and the one nuance

- **Agree:** do not put $2k into short-term trading today; ETF TAA is the only allocation with
  robust in-repo evidence; crypto is the right *sandbox*; expected income at $2k is ~$100–200/yr
  and the value is the process.
- **Nuance:** the plan puts 100% of real money in ETF TAA. I would split **70% core index beta /
  20% ETF TAA / 10% paper sandbox**. TAA is still a backtest (forward n=0) and a smart-beta risk
  trade, not alpha — a 100% allocation to it is a bet on a backtest. The 70% core leg is the only
  component with no unproven assumption.
- **Agree with the plan's strongest line:** "forward tests verify execution honesty, not alpha."
  Add the corollary: that is exactly why every sleeve needs a **random-entry control arm** — it is
  the only way to tell execution honesty from luck.

## 7. Merge order I would use

1. Land the plan as a doc (done here) so the Windows agent can review it.
2. Resolve corrections 1–3 (PDT, gate criteria, cohort labels) — cheap, prevents wrong builds.
3. My E2 work is already live (`core-beta` sleeve, SPY 721.90, $1,400, 7 tests), so the plan's
   ETF work should extend `paper_trading/sleeves.py` rather than start a second ledger format.
4. Then the crypto intraday sim, gated on the aligned criteria from correction 2.
5. Reconcile the sleeve-name gap (their task C) — it is the largest unexplained contradiction on
   the surface and worth doing before any new signal work.

*Not investment advice. Plan published verbatim for review; this file is the review.*
