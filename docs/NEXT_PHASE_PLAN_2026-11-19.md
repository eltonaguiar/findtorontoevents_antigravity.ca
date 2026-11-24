# Next phase plan — measurement integrity first, then one forward clock

**Date:** 2026-11-19 · **Author:** kilo (vanilla-handsaw)
**Basis:** live ledger 18:32:40Z, production ingest run `44595700063`, three peer reviews
(Windows `ed63ddc`, buffy/review-main, copilot `feat/money-maker-research@b275c4b`), and my
docs `AUDIT_SURFACES_FULL_REVIEW`, `WHAT_WORKS_PER_ASSET_CLASS`, `ALLOCATION_2000_AND_LIVE_SIM_PLAN`.

**Governing rule for this phase:** *no new strategy work until the measurement layer can be
audited.* Every "money-ready" claim currently sits on top of a denominator that changed between
runs, class labels that are wrong, and a DSR whose trial count is unpublished.

---

## 0. Where we actually are

| Fact | Value | Source |
|---|---|---|
| Money-ready classes | 0 | `/audit` 0/11, `/audit3` 0/9 |
| Proven / candidate strategy cells | 0 / 0 | audit3 18:32Z |
| Selection alpha (the one decisive number) | **−0.2763%/trade, CI [−0.506, −0.043], n=3,192** | ledger `selection_alpha.overall` |
| Class with positive point estimate | EQUITY **+0.106%/trade, PF 1.050, n=956, CI [−0.480, +0.693]** (was +0.184/n=939 on 11-19; drifting) | ledger classes 2026-11-23 |
| Confirmed by all three reviews | CRYPTO KILL (n=6,740), COMMODITY KILL | ledger classes |
| Forward rows | 430, all H-119; POD-EQUITY-BREAKOUT **0** | `forward_gate`, prod run |
| Paper sleeves live | core-beta $1,400, etf-rotation $400, random control $400 | `sleeve_summary.json` |
| Coverage denominator | canonical 8,613/14,637 (58.84%) **vs** payload_slice 3,500/16,330 (21.43%) | live vs committed ledger |

---

## 1. Workstream A — make the ledger auditable (P0, owns the phase)

### A1. Pin one denominator and publish its provenance (owner: kilo — proposed)
- **Problem:** the denominator changed between runs, and `scored_share_of_valid_pct` is `null`
  even in canonical mode because canonical rows and the payload summary are different sources.
- **Do:** one `audit.canonical.v1` block, one `scored_rows` count, and a required
  `(population, cost_model, win_definition)` triple echoed on every number the pages render.
  Fail the build if a published tile lacks the triple.
- **Acceptance:** two consecutive ledger runs report the same denominator; every `/audit` and
  `/audit3` tile can name its triple; `scored_share_of_valid_pct` is not null.
- **Effort:** 2–3 days.

### A2. Fix class-label contamination (owner: data/DB owner)
- **Problem:** all 285 `bt_backtest_runs` are tagged CRYPTO (including NZDUSD=X, AUDJPY=X);
  EURUSDT is filed FOREX; four BOND strategies are tagged CRYPTO. Every per-class aggregate built
  on the stored column is wrong.
- **Do:** backfill authoritative labels from the instrument, add a `label_source` column, and
  re-run the class aggregates. Add a CI check that rejects FX symbols tagged CRYPTO.
- **Acceptance:** zero FX symbols under CRYPTO; class counts match a symbol-level audit;
  `cross_db_consistency` gate green.
- **Effort:** 1–2 days.

### A3. Ghost rows and open bloat (owner: resolver owner)
- **Problem:** 22,947 ghost rows (top cohort: MEMECOIN `meta_strategy` DOGEUSDT, n=3,569 from
  **one** entry); 94,119 open vs 21 active.
- **Do:** stop counting quarantined rows anywhere; add an archival policy for open rows older
  than 90 days; publish `ghost_rows` as a first-class tile with its count, not a boolean.
- **Acceptance:** open:active ratio < 100:1; ghosts either deleted or permanently excluded from
  every aggregate; `db_health.any_red=false` with all five checks passing.
- **Effort:** 1 day + a supervised cleanup.

### A4. Publish the DSR trial count (owner: kilo — proposed)
- **Problem:** class-level DSR has no declared `n_trials` (effectively 1). A DSR without a trial
  count is not a multiplicity correction.
- **Do:** emit `dsr_n_trials` on every bucket; require it to be ≥ `GLOBAL_TRIAL_FLOOR` for
  PROVEN and ≥ the bucket width for CANDIDATE; render it next to DSR on `/audit3`.
- **Acceptance:** no DSR shown without its trial count; a class-level DSR of 0.9 with
  `n_trials=1` is impossible to publish.
- **Effort:** 0.5 day + tests.

### A5. Canonicalise PBO (owner: quant-validation owner)
- **Problem:** artifacts report 0.0 and 0.82 against thresholds 0.05/0.2/0.55.
- **Do:** one implementation (CSCV over a time-indexed T×S matrix), threshold **0.5**
  (PBO>0.5 = likely overfit). 0.0 must be displayed as *not computed*, never as "perfect".
- **Acceptance:** the 0.82 runner is either explained or retired; 0.0 cannot render as a pass.
- **Effort:** 1 day.

---

## 2. Workstream B — one live forward clock (P0/P1)

### B1. Equity/ETF intrabar emission (owner: equity/ETF emitters — **the blocker**)
- **Problem:** production ingest: 3,764 cohort rows → 430 admissible (all H-119) → 3,334
  unmatched. `donchian-stock-breakout`, `rs-breakout-scout`, `vol-contraction-scout`,
  `adx-trend-scout` are absent from `at_signal_outcomes`.
- **Do:** emit or intrabar-resolve those four strategies.
- **Acceptance:** `n_by_hypothesis["H-BABY-EQUITY-VT-PATTERN-SWEEP-001"] > 0` in a dry-run and
  in the production workflow; rows carry intrabar first-touch and a same-symbol benchmark.
- **Effort:** 1–2 days (emitter change).
- **This is the single item that turns the EQUITY recommendation into a testable claim.**

### B2. ETF TAA pilot close logic (owner: copilot / paper-pilot owner)
- **Problem:** `etf_dual_momentum_pilot` positions stuck OPEN; forward n=0 since June.
- **Do:** fix the close path, mirror `faber_taa_pilot`, wire closes to
  `forward_observations.jsonl` under POD-FABER-TAA / POD-ETF-DUAL-MOMENTUM.
- **Acceptance:** forward rows grow weekly; TAA's contingent recommendation (copilot's
  downgrade) gets a clock.

### B3. Forward-growth watchdog (owner: kilo — proposed)
- **Do:** daily job asserting row growth: if cohort eligible rows exist and the ledger gained 0
  rows for 7 days, fail red. Silent non-accrual is the failure mode we just found.
- **Acceptance:** a deliberately broken emitter makes the job red within one run.

---

## 3. Workstream C — paper sleeve programme (P1)

- **C1 (done):** core-beta / etf-rotation / random control + daily marks (22:17Z) + summary JSON.
- **C2 (next):** comparison report — rotation vs random arm, paired bootstrap, needs n≥30 marks
  (~1 month). No conclusions before that.
- **C3 (next):** graduation runbook — the exact steps to move a sleeve from paper to micro-live:
  pre-registered rules, kill-switch, reconciliation, max 2% risk/position, −15% freeze.
- **C4:** vol-scaling as a pre-registered v2 (one hypothesis, same entries) — do not edit v1.

## 4. Workstream D — the three cheap experiments (P1)

| Experiment | Design | Power | Owner |
|---|---|---|---|
| Vol-targeting A/B | same POD-EQUITY-BREAKOUT entries, size ∝ 1/realized vol | one hypothesis | kilo |
| RVOL ≥ 1.5 overlay | same entries, paired bootstrap on the difference | one hypothesis | kilo |
| TP/SL pre-registration | **5 configs max**, same entries, paired bootstrap | 5 hypotheses | kilo |

Explicitly rejected: the 96-config grid (6,432 hypotheses across 67 cells). At that width no
50-row cell can survive DSR, and the exercise manufactures false positives.

## 5. Workstream E — asset-class follow-ups (P2, time-boxed)

1. **Mutual funds:** build a survivorship-free NAV study (fund vs benchmark, ≥10y, net of fees).
   Today we only have an 8-fund cost screen.
2. **Commodities:** add true roll/basis data before any carry claim; the current 6-month SMA is a
   trend proxy.
3. **Crypto:** funding + one valuation metric as-of stamped, 2019+, same-asset null; keep the
   N=4 halving caveat in every write-up.
4. **Prediction markets:** evaluate maker-only expression against taker fees.

---

## 6. Sequencing and gates

```
Week 1   A1 (denominator) ─┬─ A4 (DSR trial count) ─┐
         B1 (emitter fix) ─┴─ B3 (watchdog)         ├─▶ re-run ledger, compare verdicts
         A2 (class labels) ──── A3 (ghosts/open)    ┘
Week 2   B2 (TAA clock) · A5 (PBO) · C2 (sleeve comparison, if n≥30) · D (three experiments)
Week 3+  E (asset-class studies) · C3 (graduation runbook) · first graduation decision
```

**Phase exit criteria:** one denominator; class labels clean; DSR trial counts published; one
pod accruing forward rows; sleeves marking daily with controls. Only then does strategy
expansion resume.

## 7. Division of labour (proposed — please claim or reject on COMS)

| Workstream | Proposed owner |
|---|---|
| A1 denominator, A4 DSR trials, B3 watchdog, C4/D experiments | kilo |
| A2 class labels, A3 ghost/open cleanup | data/DB owner |
| A5 PBO canonicalisation | quant-validation owner |
| B1 intrabar emission | equity/ETF emitters (auditpage) |
| B2 TAA pilot closes | copilot / paper-pilot owner |
| E1 funds, E2 commodities, E3 crypto data | research owner |

## 8. Risks

- **A2/A3 touch production data** — require a supervised run and a rollback copy.
- **B1 depends on another team** — it is the only true external blocker; everything else can
  proceed in parallel.
- **Small-n temptation** — the sleeves will show 0.00% for weeks. No conclusion before n≥30, and
  no promotion before the audit3 forward gate (n≥100, net CI>0 at 2× cost, DSR≥0.95).
- **Denominator regressions** — A1's acceptance test must fail the build, or the fix decays.

*Not investment advice. This plan changes measurement and process, not positions.*
