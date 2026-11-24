# 28 — Programme status index (2026-11-23)

**Purpose:** an INDEX, not a new analysis. A fresh agent reads this one file and knows the state of the
programme without re-reading twenty blocks of context. Nothing here is computed for the first time; every
figure is copied from a document or artifact on `origin/main`, with its source.

TALLY: 0 INVESTABLE / 11 NOT_INVESTABLE / 3 UNKNOWN (14 rows)

That is the settled tally for the 14-row set. A test enforces it:
[`tests/test_edge_research_tally_consistency.py`](tests/test_edge_research_tally_consistency.py:139) discovers
every markdown document under `docs/` that states a tally (`SEARCH_DIR` at `:139`, `_tally_documents` at
`:146-149`) and fails any that states a figure other than the settled one outside a historical context
(`test_every_document_that_states_a_tally_states_the_settled_one`, `:168-180`). This document is inside the
globbing scope, so its tally line must stay in the canonical form.

---

## 1. The document set

| Doc | File | What it is | Status |
|---|---|---|---|
| 15 | [`15_PROGRAMME_SCOREBOARD_2026-11-22.md`](docs/edge_research/15_PROGRAMME_SCOREBOARD_2026-11-22.md) | Per-strategy scoreboard: PF register with cost basis, cost-basis audit, break-even ledger, "do not quote" list | **CURRENT** for per-strategy detail; its class-cost cells are flagged stale at [`27...md:91-92`](docs/edge_research/27_POST_COST_RECONCILIATION_2026-11-23.md:91) |
| 22 | [`22_FINAL_SYNTHESIS_2026-11-22.md`](docs/edge_research/22_FINAL_SYNTHESIS_2026-11-22.md) | 14-row verdict table, per-asset-class rollup, PF register, contradictions carried forward | **CURRENT** for the verdict table and class rollup; its Part 4 bucket headings are **SUPERSEDED** by its own tally note ([`:133-138`](docs/edge_research/22_FINAL_SYNTHESIS_2026-11-22.md:133)) |
| 23 | [`23_DEFINITIVE_ANSWER_2026-11-22.md`](docs/edge_research/23_DEFINITIVE_ANSWER_2026-11-22.md) | Closing document; the final-accounting table (`:178-193`) is the **authority** for the tally (`:195`) | **CURRENT** |
| 24 | [`24_EXECUTION_PLAN_2026-11-23.md`](docs/edge_research/24_EXECUTION_PLAN_2026-11-23.md) | PLAN rung of the 2026-11-23 window: twelve classes, eight fields each, eligibility gate defined | **SUPERSEDED** as a plan by docs 25/26; kept as the record of the gate |
| 25 | [`25_DRAFT_RANKED_LIST_2026-11-23.md`](docs/edge_research/25_DRAFT_RANKED_LIST_2026-11-23.md) | DRAFT rung: 12-class eligibility table, per-class cost and verdict cells | **SUPERSEDED** by 26; several cells are stale (pilot closes, BOND/COMMODITY/PENNY cost) — see [doc 27 §7](docs/edge_research/27_POST_COST_RECONCILIATION_2026-11-23.md:81) |
| 26 | [`26_FINAL_RANKED_LIST_2026-11-23.md`](docs/edge_research/26_FINAL_RANKED_LIST_2026-11-23.md) | FINAL rung: the answer, twelve class verdicts, the vehicle question | **CURRENT** |
| 27 | [`27_POST_COST_RECONCILIATION_2026-11-23.md`](docs/edge_research/27_POST_COST_RECONCILIATION_2026-11-23.md) | Re-runs doc 23's eligibility gate against newly measured class costs; default action NO CHANGE | **CURRENT** for cost reconciliation; it edits nothing |
| 28 | this file | Status index and programme map | **CURRENT** |

**`updates/` notes created 2026-11-23** (all under [`updates/`](updates/)):

| Note | One-line purpose |
|---|---|
| [`2026-11-23-cost-artifact-provenance-reconciliation.md`](updates/2026-11-23-cost-artifact-provenance-reconciliation.md) | Re-derives the new-class cost artifact's fields arithmetically from its own per-name records; records which commit it was read from |
| [`2026-11-23-cost-estimator-description-correction.md`](updates/2026-11-23-cost-estimator-description-correction.md) | Self-correction: the headline cost figures are 1-min bar-range **upper bounds**, not Corwin-Schultz |
| [`2026-11-23-doc22-count-clarification.md`](updates/2026-11-23-doc22-count-clarification.md) | Explains doc 22's three counts (9 / 13 / 14) as distinct quantities, not a typo |
| [`2026-11-23-fx-cron-log-visibility-fix.md`](updates/2026-11-23-fx-cron-log-visibility-fix.md) | Makes a failed FX strategy chain print in the Actions log; does not restore the missing tool |
| [`2026-11-23-fx-cron-preflight.md`](updates/2026-11-23-fx-cron-preflight.md) | Read-only diagnosis of the FX weekday-overlap workflow; documents the absent `tools/fx_meanrev_research.py` |
| [`2026-11-23-nbbo-measurability-probe.md`](updates/2026-11-23-nbbo-measurability-probe.md) | Feasibility probe for live NBBO on BOND, COMMODITY_FUTURES, PENNY_STOCK; adds no cost constant |
| [`2026-11-23-paper-pilot-reachability.md`](updates/2026-11-23-paper-pilot-reachability.md) | Can the crypto paper pilot reach n≥20 per slot before day-30 and n≥100 before day-60? Read-only |
| [`2026-11-23-pilot-rate-extrapolation-provenance.md`](updates/2026-11-23-pilot-rate-extrapolation-provenance.md) | Self-correction of close-rate figures quoted from the pilot log; dates are my arithmetic, not recorded values |
| [`2026-11-23-stale-cost-status-corrections.md`](updates/2026-11-23-stale-cost-status-corrections.md) | Corrects "cost UNMEASURED" statements made stale by the new class measurements; changes no verdict |

---

## 2. The twelve asset classes

Taxonomy is the 12-class superset at [`22_FINAL_SYNTHESIS_2026-11-22.md:71`](docs/edge_research/22_FINAL_SYNTHESIS_2026-11-22.md:71). Costs are round-trip (RT) bp,
all **upper bounds** (see §6), all `COMMISSION_UNKNOWN`.

| Class | Verdict | Deciding number | Cost RT | Cost provenance |
|---|---|---|---|---|
| CRYPTO | no investable entry | crypto intraday mean-rev PF 0.815 at 0 bp; funding carry: 2.89% of episodes reach the 16.398-day break-even [SRC: `23...md:67`, `:189`] | 20.0–52.0 | **MEASURED** (taker fee + walked depth); perp spread assumed = spot [SRC: `23...md:48-49`] |
| EQUITY | no entry: breakout NOT_INVESTABLE | random-entry null 69.8/71.4 pct; alpha CI-LB −0.285% [SRC: `23...md:182`] | 12.0749 | **MEASURED UPPER BOUND** from 1-min bars, 13 names; not NBBO [SRC: `23...md:53-54`, `25...md:18`] |
| ETF | no entry: no ETF strategy with a CI | N1 R2 null 35.4; R3 null 53.4 [SRC: `23...md:192-193`] | 6.7122 | **MEASURED UPPER BOUND**, 14 names [SRC: `23...md:55`, `25...md:19`] |
| BOND | no entry: bond momentum NOT_INVESTABLE | break-even 0 bp/side; B1 PF 1.312 beside Sharpe −0.550 [SRC: `23...md:188`] | 1.2125 | **MEASURED UPPER BOUND** from bond-ETF 1-min bars, 10 names; artifact is NOT on main; Treasury-direct UNMEASURED [SRC: `27...md:32`] |
| COMMODITY | 2 UNKNOWN (`BLOCKED_MISSING_DATA`) | zero second-month series; roll-corrupted front month [SRC: `23...md:187`, `:190`] | 6.3182 | **MEASURED UPPER BOUND**, front-month spread only; roll cost UNMEASURED [SRC: `27...md:36`, `:100`] |
| FOREX | no entry: carry and momentum NOT_INVESTABLE; mean-rev UNKNOWN | mean-rev break-even 4.3038 vs measured 7.533 [SRC: `23...md:51`, `:181`] | 7.533 | **MEASURED UPPER BOUND** at the Sunday 22:00Z reopen; thin book [SRC: `23...md:51-52`] |
| FUTURES | no row in the 14-row set | n/a | UNMEASURED | no cost model [SRC: `22...md:81`] |
| MEME | no row | DOGE 6.7938 quotable, 1 of 3 names [SRC: `23...md:56-58`] | UNMEASURED (as a class) | partial only; an average would manufacture a number [SRC: `23...md:88-89`] |
| PENNY_STOCK | no row | n/a | UNMEASURED in doc 25 [SRC: `25...md:26`]; 21.2974 in doc 27 [SRC: `27...md:41`] | **CONTESTED**: doc 27's figure comes from an artifact not on main; doc 25 still says UNMEASURED |
| INDEX | no row (ETF alias) | n/a | 8.0325 | **MEASURED UPPER BOUND** as an alias of the ETF sample, 4 names [SRC: `23...md:56`, `25...md:20`] |
| SPORTS | no row | n/a | UNMEASURED | out of scope [SRC: `22...md:85`] |
| MUTUAL_FUND | no row | n/a | UNMEASURED | 0.08 configured, never populated [SRC: `22...md:86`] |

**Classes with no measured cost:** FUTURES, MEME, SPORTS and MUTUAL_FUND uncontestably; PENNY_STOCK is
contested between doc 25 (UNMEASURED) and doc 27 (measured, artifact not on main); INDEX is measured only
through the ETF alias. That is **4 uncontested + 2 contested**, not 7. (See §8, discrepancy 3.)

---

## 3. The three UNKNOWN rows and what would unblock them

| Doc 23 line | Row | Verdict | Exact unblock requirement |
|---|---|---|---|
| [`181`](docs/edge_research/23_DEFINITIVE_ANSWER_2026-11-22.md:181) | FX mean-reversion (5d/5d) | UNKNOWN (`ALREADY_SCHEDULED`) | A representative **weekday** FX spread run in the London/NY overlap; the workflow exists and is pending [SRC: `23...md:99-101`] |
| [`187`](docs/edge_research/23_DEFINITIVE_ANSWER_2026-11-22.md:187) | Commodity momentum V1/V2/V3 | UNKNOWN (`BLOCKED_MISSING_DATA`) | Roll-adjusted, back-adjusted continuous futures built from **individual contract months** with an explicit, pre-declared roll rule, plus commission and slippage charged per contract [SRC: `23...md:119-121`] |
| [`190`](docs/edge_research/23_DEFINITIVE_ANSWER_2026-11-22.md:190) | Commodity term-structure carry | UNKNOWN (`BLOCKED_MISSING_DATA`) | A genuine futures curve: **at least two simultaneous contract months** per commodity per date, over a multi-year history [SRC: `23...md:125-126`] |

Both commodity rows are permanently blocked on data that is not on disk, not on effort. The FX row is open on
a fact cost measurement can supply, but its clustered CI includes zero even at 1 bp [SRC: `23...md:181`].

---

## 4. The two evidence-producing paths, honestly

### 4.1 FOREX weekday spread sample

- **Workflow:** [`.github/workflows/fx-cost-overlap.yml`](.github/workflows/fx-cost-overlap.yml) with six weekday crons at `:38-43`:
  `48 13`, `56 13`, `52 14`, `57 14`, `54 15`, `58 15` (UTC, Mon–Fri), plus `workflow_dispatch` at `:44`.
- **The only class where cost is binding and the gap is small:** measured cost **7.533 bp** [SRC: `23...md:51`]
  vs mean-reversion break-even **4.3038 bp** [SRC: `23...md:181`] = a **3.2292 bp** shortfall (≈3.23 bp), in
  contrast to FX carry's 468.5 bp break-even [SRC: `docs/edge_research/15_PROGRAMME_SCOREBOARD_2026-11-22.md:98`].
- **Known issue:** the strategy chain fails because `tools/fx_meanrev_research.py` is absent from main
  (verified: the file does not exist in a clean `origin/main` worktree; `tools/fx_cost_sampler.py:379` imports
  it). As of PR **#1077** (MERGED 2026-11-23T03:24:10Z) the failure is **visible** in the job log
  ([`tools/fx_cost_sampler.py:717-729`](tools/fx_cost_sampler.py:717)) but it still fails.
- **The cost measurement itself is unaffected** by that chain failure [SRC: `fx_cost_sampler.py:729`].

### 4.2 CRYPTO paper pilot

- **CANNOT graduate as designed.** The threshold is **per slot**: `MIN_N_BEFORE_JUDGMENT = 20`
  ([`verified_strategies/paper_pilot/crypto_intraday_sim.py:54`](verified_strategies/paper_pilot/crypto_intraday_sim.py:54)),
  counted per slot at `:301` (`trades = [t for t in closed if t.get("slot") == slot]`) and `:324`
  (`"n_closed": len(trades)`). With three slots, the pod needs **60 closes**, not 20.
- **Observed:** 5 CLOSE rows in the committed log (3 + 0 + 2 across slots), i.e. **1.8–2.5 closes/day**
  depending on the window chosen [SRC: `updates/2026-11-23-paper-pilot-reachability.md:69-70`]; structural
  TIME-exit ceiling **≈2.9/day** for the pod [SRC: `...reachability.md:98-99`].
- **n≥20 per slot before the day-30 gate (2026-12-19): MARGINAL.** **n≥100 per slot before day-60
  (2027-01-18): NO** for every slot in practice — vwap_reversion is frozen, and the other two are MARGINAL only
  at the theoretical ceiling, which the empirical rate is already near [SRC: `...reachability.md:139-144`].
- **`vwap_reversion` is HALTED** at trailing drawdown **11.5229%** vs the **10.0%** limit
  (`TRAILING_DD_HALT_PCT`, `:51`; checked at `:318`), so its n can never reach 20 without an operator decision
  [SRC: `...reachability.md:154-156`; state file `guardrails.vwap_reversion.status = "HALTED"`].

---

## 5. Open operator decisions (deliberately not done)

1. **Restore `tools/fx_meanrev_research.py`** — NOT done. It is another agent's tool from a refused branch, and
   restoring it would be adopting someone else's work into main without review [SRC: `updates/2026-11-23-fx-cron-preflight.md:164`].
2. **Change pilot `max_hold_bars`, add slots, extend a gate, or clear the halt** — NOT done. Each would change
   the pre-registered design after seeing the data; the halt is a guardrail requiring manual review
   (`crypto_intraday_sim.py:19`), not a bug to patch around.
3. **Purchase NBBO or SIP data** — NOT done. A standing bound forbids new data purchases; the cost figures are
   bar-range upper bounds because no NBBO feed is available [SRC: `23...md:61-62`].
4. **Re-open any DEAD class** — NOT done. Re-opening requires the pre-declared unblock condition in §3, not
   effort [SRC: `23...md:91-93`].

---

## 6. The cost constants and their exact nature

Every constant below is a **1-minute bar-range UPPER BOUND** on the round-trip quoted spread (bid and ask both
lie inside `[low, high]`). It is **not** Corwin-Schultz and **not** the NBBO. The per-bar range is computed at
[`tools/equity_cost_measure.py:224`](tools/equity_cost_measure.py:224), its per-name median at `:240`
(`"median": ranges[n // 2]`), and the cross-name median at `:602` (`"median": statistics.median(vals)`).
Corwin-Schultz is a **separate, less reliable field** in the same artifact (`def corwin_schultz` at `:147`,
per-name median `:172`, aggregate `:606`), unusable for BOND and meaningless for COMMODITY. See
[`updates/2026-11-23-cost-estimator-description-correction.md`](updates/2026-11-23-cost-estimator-description-correction.md).

| Class | Constant (bp RT) | Source |
|---|---|---|
| EQUITY | 12.0749 | [SRC: `23...md:53`] |
| ETF | 6.7122 | [SRC: `23...md:55`] |
| INDEX (proxy) | 8.0325 | [SRC: `23...md:56`] |
| BOND | 1.2125 | [SRC: `27...md:32`] |
| COMMODITY_FUTURES | 6.3182 (front month) | [SRC: `27...md:36`] |
| PENNY_STOCK | 21.2974 (contested, see §2) | [SRC: `27...md:41`] |
| FOREX | 7.533 | [SRC: `23...md:51`] |
| CRYPTO | 20.0–52.0 | [SRC: `23...md:48-49`] |

Roll cost of commodity futures is `UNMEASURED` [SRC: `27...md:100`]. No class has a CI on net return, so a
measured cost never by itself produces a verdict [SRC: `22...md:89`].

---

## 7. What a fresh agent should do first

1. Read this index, then doc 23's final-accounting table (`:178-195`) if a row-level reason is needed.
2. Treat every class cost as an upper bound, never as a measured spread.
3. Do not re-derive the verdicts: they are settled, and the test in the header enforces the tally.
4. Before proposing new work, read §5: the four obvious next moves were deliberately declined, each for a
   stated reason.

---

## 8. Figures in the request that did not match `origin/main`

Reported, not silently corrected. Main's value is used above.

1. **"7 of 12 classes still cost-UNMEASURED: EQUITY, ETF, FUTURES, MEME, INDEX, SPORTS, MUTUAL_FUND"** →
   EQUITY (12.0749), ETF (6.7122) and INDEX (8.0325) *have* measured upper bounds on main
   [SRC: `23...md:53-56`, `25...md:18-20`]. Main supports **4 uncontested** unmeasured classes
   (FUTURES, MEME, SPORTS, MUTUAL_FUND) plus PENNY_STOCK contested. Doc 22's own ":89" line says "5 of 12"
   while listing six, and doc 27 flags it stale [SRC: `27...md:90`].
2. **Pilot "n≥100 before day-60 is NO for every slot"** → main says **NO for vwap_reversion, MARGINAL for the
   others** at the theoretical ceiling [SRC: `...reachability.md:139`]. In practice it is NO, because the
   empirical rate is already near the ceiling [SRC: `...reachability.md:100`], but the exact word for the two
   live slots on main is MARGINAL.
3. **"ledger 430"** → the audit3 ledger's `forward_gate.n_rows` is **449** [SRC: `audit_dashboard/data/audit3_ledger.json`],
   while H-119's own `n_forward` is **430**. Both are right at different scopes; doc 23:132 quotes the 430.
4. **Pilot closed count** → doc 25:24 still says "pilot 0 closed" [SRC: `25...md:24`]; the committed state and
   log show **5** closed trades (§4.2). Doc 25 is stale, not wrong at the time it was written.

---

**Provenance.** Read from `origin/main` at sha **`6b2e65fadd144be375cd14d58f6dca3bdbbf8268`** (pre-merge tip)
through a clean `/tmp` worktree, never from the shared working tree. All line numbers are that ref's.
