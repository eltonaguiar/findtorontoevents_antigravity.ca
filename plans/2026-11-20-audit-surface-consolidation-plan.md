# Audit surface consolidation — fixes + test plan

**Date:** 2026-11-20 · **Author:** Zoo (architect) · **Status:** proposal, nothing implemented
**Scope:** `/audit`, `/audit2`, `/audit3`, their ledgers, their workflows, and the DB views feeding them.
**Governing rule:** no new strategy work until the measurement layer can be audited.

## ELI5 — the short version

Imagine three scoreboards for the same team, each keeping score differently: one says
the team scored 10, one says 9, one just repeats whatever the first one said. Nobody is
lying, but you cannot tell if you are winning. On top of that, the same player shows a
different stat on each board — a 1.9% hit rate on one, 43.2% on another.

That is the audit problem: `/audit`, `/audit2` and `/audit3` are three scoreboards fed by
the same games, and they disagree. The fix is boring and cheap: one scoreboard (one
population of trades), one set of rules for counting (one cost model, one win
definition), and every number stamped with where it came from. Then, when a number looks
good, we can check whether it is real skill or just the market going up — that check is
called *selection alpha*, and right now it is negative: our picks do worse than simply
holding the same coins and stocks.

Only once the scoreboard is trustworthy is it worth asking "which plays actually work?"
That is the discovery arm below — look at the winners we already have, find what they
share, and check whether that pattern could have happened by luck.

---

## 0. What the evidence says today

| Fact | Value | Where |
|---|---|---|
| Money-ready classes | 0 (`/audit` 0/11, `/audit3` 0/9, `/audit2` echoes) | three denominators, one product |
| PROVEN / CANDIDATE cells | 0 / 0 of ~359 | audit3 ledger |
| Selection alpha (decisive) | **−0.2763%/trade, CI [−0.506, −0.043], n=3,192** | `selection_alpha.overall` |
| Coverage | canonical 8,613/14,637 (58.84%) **vs** payload slice 3,500/16,330 (21.43%) | two ledgers, same name |
| Forward rows | 430, all H-119; POD-EQUITY-BREAKOUT 0 | `forward_gate` |
| Publishers of `audit3_ledger.json` | **two** (`audit3-ledger.yml` 6-hourly → `/audit3`; `audit-dashboard.yml` hourly → `/audit/data`) | measured lag 223 min |
| Sleeve layer | 0/10 sleeves verified against audit3 cells; CRYPTO sleeve PF 155.85 inside a class PF 0.8383 | `tools/sleeve_reconciliation.py` |
| `policy_clean_pf` vs `pf` | **bit-identical in all 11 classes** while `policy_clean_n` differs; CRYPTO's clean subset is 22,081 rows against a 3,726-row parent | `reports/CLASS_DIVERGENCE_2026-11-19.md` |
| Scored share | 8,605 / 14,632 = **58.8% scored, 41.2% not scored** (canonical exclusion list sums to 6,027) | N6 — still open |
| Price tables | equity last bar **2026-06-18**, FX **2026-02-09**, futures **2026-06-21**, ETF only 36 symbols | `bar_coverage` |
| ETF TAA claim | **NOT REPRODUCED** — 0/576 pre-registered cells met the bar; best Sharpe 0.795 vs SPY 0.735, MaxDD −41.7% | `reports/TAA_SETTLE_2026-11-19.md` |
| Tribunal gates landed | F1 block bootstrap, F2 split-half materiality, N1 persistence, N2 churn, N3 recency, N4 cost-scaled floor, N7 freeze gate — but N5 hold-normalised alpha is **code only, not published** | `updates/2026-11-19-*` |
| Runtime smoke gate | `tools/assert_tribunal_runs.py` runs the tribunal for real — **not wired into CI** | session notes 2026-11-20 |

Cross-surface contradictions that a reader sees right now: COMMODITY `WATCH` vs `KILL`;
ETF win rate 1.9% vs 43.2%; kill counts 42 vs 11 vs 8; two forward-clock renderers on one
data source; three vintages of the same page presented as one current view.

None of this says the prediction work is worthless. It says the pages cannot currently tell
you which of their numbers to believe — and that is the cheapest thing to fix.

---

## 1. Target architecture — one source, three views

```mermaid
flowchart TD
  DB[(MySQL read-only)] --> RES[resolver + canonical view resolved_closed_picks_net]
  RES --> CANON[audit_canonical.json: rows + provenance triple]
  FB[forward_observations.jsonl] --> CANON
  PJ[backtest + repo JSON evidence] --> CANON
  CANON --> TRIB[audit3_tribunal: gates DSR BH cost-stress alpha]
  TRIB --> LED[audit3_ledger.json: single publisher]
  LED --> P3[/audit3 — truth surface/]
  LED --> P1[/audit — overview + deprecation map/]
  LED --> P2[/audit2 — methodology and candidate library tab/]
  LED --> DENY[audit3_denylist → feed_hygiene]
```

Rules that make it hold:

1. **One artifact, one writer.** `audit3-ledger.yml` is the only workflow allowed to produce
   `audit3_ledger.json`, and it uploads the same bytes to `/audit3/` and `/audit/data/`
   in one deploy step.
2. **One population.** Every tile on every page reads the canonical view. A page may show a
   slice, but it must label it as a slice and print the denominator.
3. **One provenance triple.** Each number carries `(population, cost_model, win_definition)`
   plus `provenance_id`. A tile without the triple fails the build.
4. **One trial counter.** The same `n_trials` feeds DSR, BH and Bonferroni in
   `audit3_tribunal.py`, `money_ready_verdict.py` and the emitter.
5. **One kill vocabulary, two labelled pipelines.** Keep the cell-gate verdicts and the
   legacy strategy-register verdicts separate, publish the union with provenance
   (`tools/kill_list_reconcile.py`), never merge them silently.

---

## 2. Fix backlog

### P0 — correctness and trust (do first, in this order)

| # | Fix | Why | Done when |
|---|---|---|---|
| P0-1 | Delete the `audit3_ledger.json` upload from `audit-dashboard.yml` | two publishers, one generation of lag, invisible to grep because the workflow globs `audit_dashboard/data/*.json` | one workflow writes the path; parity job green |
| P0-2 | Make `tools/assert_surface_parity.py` a hard CI gate (fail the build, not warn) | parity was RED at session end and nothing stopped it | a deliberately stale copy fails CI within one run |
| P0-3 | Coverage honesty: withhold any headline where `scored_rows > valid_closed_picks` (105.26%), keep `_raw`, reconcile the 430 H-119 rows | a ratio above 100% is not a rounding error | headline withheld or reconciled; denominator invariant tested |
| P0-4 | One money-ready count with one denominator, everywhere | 0/10 vs 0/9 vs echo is three answers to one question | every page shows the same `0/N` and the same N's definition |
| P0-5 | Derive `asset_class` from `symbol` in every aggregate; add a CI check that rejects FX symbols tagged CRYPTO | all 285 `bt_backtest_runs` are tagged CRYPTO, 4 BOND strategies too — every per-class number built on the column is wrong | zero FX under CRYPTO; `cross_db_consistency` green |
| P0-6 | Selection alpha becomes the per-class headline; raw PF and WR demoted to descriptors | it is the only metric that separates skill from beta, and it is negative | no page leads with WR |
| P0-7 | Rotate the leaked DB credential (human action) and scan `discord_*` columns for tokens before any distribution | a secret in git history is a secret | rotated; scan report committed with redactions |
| P0-8 | Retire the 70-minute parity tolerance; assert equal `generation_id` / `input_sha256` instead | a 6-hourly producer can never satisfy a 70-minute window, so parity RED is structural and the alert is noise | parity compares content hashes, not clocks |
| P0-9 | Fix `policy_clean_pf`: it equals `pf` in all 11 classes while `policy_clean_n` differs, and a clean subset exceeds its parent | the policy-clean net view is the readiness basis — the gate is reading a filter that does not filter | `policy_clean_n <= n` per class, and `policy_clean_pf` differs from `pf` or the equality is documented per class |
| P0-10 | Stop citing ETF tactical allocation as proven, everywhere | 0/576 cells met the pre-registered bar; the 0.88 Sharpe / −19% MaxDD figure is a window artifact that holds only in 2018-2026 | no page, plan or doc presents TAA as evidence |
| P0-11 | Apply the publish-split + sleeve-gate patch (currently has no owner) | `/audit` was 223 minutes behind `/audit3` at the end of yesterday's session, and the sleeve gate is inert until applied | one deploy step writes `/audit3/` and `/audit/data/` from one generation |

### P1 — measurement quality

| # | Fix | Notes |
|---|---|---|
| P1-1 | Measured per-strategy slippage in audit3; correct FUTURES/COMMODITY constants | flat constants are above measured for CRYPTO/ETF (kills conservative) but below measured for FUTURES/COMMODITY |
| P1-2 | `required_n` from MDE/power, not the observed cell mean | current ETF value 1,745,345 is circular |
| P1-3 | Emit or intrabar-resolve the four EQUITY breakout strategies | 15 of 23 registered pod strategies are not emitted; the forward ingest rejects every row |
| P1-4 | Per-hypothesis forward-growth watchdog | silent non-accrual is the failure mode already found |
| P1-5 | Pin `/audit2` to one ledger path and add it to the parity assertions | it renders whichever entry of its fallback chain resolves first |
| P1-6 | `dsr_n_trials` on every bucket, floored for PROVEN | a DSR without a trial count is not a multiplicity correction |
| P1-7 | Sleeve cross-mark: a sleeve unreconciled against audit3 cells renders UNVERIFIED, never a PF |
| P1-8 | Retire the dead `tier2_proven_strategies` panel; one smart-picks definition; stamp vintage per tile | a proven panel with dead cards teaches readers to ignore labels |

### P2 — consolidation and hygiene

- Page consolidation per `docs/plans/2026-11-19-audit3-v2-evidence-and-success-metric-plan.md` P5:
  `/audit3` is the truth surface, `/audit` is an overview with a deprecation map, `/audit2`
  becomes a methodology/candidate tab (or redirects) — every old section maps to a cell or is
  documented as retired.
- Weekly `audit3-evidence.yml` (separate concurrency group, separate cron minute) ingesting
  `bt_backtest_runs`, `at_large`, `at_incubator` and the 77 repo JSONs with provenance.
- Canonicalise PBO (one CSCV implementation, threshold 0.5, `0.0` renders as *not computed*).
- Workflow hygiene: prune dormant/always-failing GHA jobs (`CI Tests` on dead branches,
  `QA Market Validation`), one cron owner per artifact, keep every new pipeline file in the
  AGENTS.md path registry in the same PR.

---

## 3. Test plan

### 3.1 Deterministic unit tests (fast, no DB, run in the normal CI job)

| Area | Test | Asserts |
|---|---|---|
| Parity | `test_surface_parity_fails_on_stale_copy` | injected 1-generation-old ledger → non-zero exit |
| Provenance | `test_every_tile_has_triple` | walk rendered tiles; each has population/cost_model/win_definition/provenance_id |
| Denominator | `test_scored_rows_le_valid_closed_picks` | `coverage.scored_rows == summary.n_rows` and ≤ valid closed picks |
| Publisher | `test_single_writer_per_artifact` | parse `.github/workflows/*.yml`; each deployed artifact path has exactly one producing workflow |
| Class labels | `test_asset_class_from_symbol` | `NZDUSD=X`, `AUDJPY=X`, `BTC-USD`/`BTCUSDT` → correct class, one instrument |
| Denylist | `test_denylist_direction_aware` | KILL LONG blocks LONG, not SHORT |
| Trial counter | `test_dsr_n_trials_matches_bucket_width` | DSR never published without `n_trials`; PROVEN requires the global floor |
| required_n | `test_required_n_is_mde_based` | a cell with a tiny mean cannot claim a million-row requirement |
| Kill lists | `test_kill_union_has_provenance` | union contains both pipelines with labels, no silent merge |
| Golden ledger | `test_ledger_rebuild_is_stable` | fixed payload → same ledger modulo timestamps and git sha |

### 3.2 Integration / end-to-end

- `tests/test_audit3_ledger_e2e.py` (exists) — CLI → ledger → schema, plus the persistence sidecar.
- `tests/test_audit3_cli_smoke.py` (exists) — every flag the workflows pass still parses.
  Note: `--help` exits inside argparse, so it can never be the sole evidence that `main()` works;
  keep the crash smoke test (`build_report(...)` on a one-row payload) alongside it.
- Focused suite at handoff:
  `python3 -m pytest tests/test_audit3_*.py tests/test_forward_observations*.py tests/test_resolved_closed_view.py tests/test_per_class_cost_gate.py -q`
  (expect 93+ passed once the open merge repairs land).

### 3.3 Live smoke (post-deploy, manual or scripted with `tools/wakeup_watch_20min.py`)

```bash
for u in /audit/ /audit2/ /audit3/; do curl -s -o /dev/null -w "$u %{http_code}\n" https://findtorontoevents.ca$u; done
curl -s https://findtorontoevents.ca/audit3/audit3_ledger.json | python3 -c \
 "import json,sys;d=json.load(sys.stdin);print(d['provenance']['id'],d['coverage']['scored_rows'],d['summary']['n_proven'])"
curl -s https://findtorontoevents.ca/audit/data/audit3_ledger.json | sha256sum   # must equal the /audit3 copy
```

Acceptance: three pages 200; `/audit/data/audit3_ledger.json` and `/audit3/audit3_ledger.json`
have identical sha256 and `generated_at`; provenance carries `generator_version`, `input_sha256`,
`git_sha`.

### 3.4 Fail-injection (proves the guards are load-bearing)

| Inject | Expect |
|---|---|
| Re-add the second publisher | P0-1 test red |
| Ship a tile without the triple | build fails |
| Tag `AUDJPY=X` as CRYPTO | class-label CI red |
| Freeze the forward ledger for 7 days while eligible rows exist | watchdog red |
| Publish DSR at `n_trials=1` for a class | DSR floor test red |

### 3.5 Manual review checklist (a human, each page)

- Name the provenance triple of any tile you point at.
- Every headline stat: can you tell which population it is?
- No two tiles on one page contradict each other; if they do, is the divergence labelled?
- Kill list: is each entry labelled with its pipeline?
- Vintage: is each stale number dated where it is shown?

---

## 4. Sequence

1. **Stop the bleeding** — P0-1, P0-2 (a day's work, immediately removes the lag and the silent staleness).
2. **Make the denominator honest** — P0-3, P0-4, P0-5 with their tests.
3. **Change the headline** — P0-6, P1-6, P1-7 (alpha, trial counts, sleeve honesty).
4. **Consolidate the pages** — P2, after the numbers agree, so we are not merging three ledgers into one confusing page.
5. **Feed the forward clock** — P1-3, P1-4, then re-evaluate whether any class deserves a pod.

## 5. Discovery arm — reverse engineering what actually works

Falsification is already well covered (gates, DSR, forward clock). What is missing is a
*discovery* arm held to the same standard, for reverse engineering skyrocketing moves in
stocks, crypto, forex, bonds, ETFs, commodities, futures and mutual funds:

| # | Item | Why it is required |
|---|---|---|
| D1 | **Survivorship-free universe** — point-in-time symbol lists, delisted names included | Winners-only data manufactures any edge you want |
| D2 | **Pre-commit the event definition** — "skyrocket = +X% within N days", written before looking | Otherwise the threshold is chosen after seeing which one is significant |
| D3 | **Label-leakage audit** — every feature must be knowable at entry time | The classic failure: a feature computed after the fact predicts perfectly |
| D4 | **Base rate first** — what share of all names/picks skyrocketed anyway? | Lift is meaningless without the denominator |
| D5 | **Matched controls** — same asset class, regime, hold window | A class-wide effect looks like a feature otherwise |
| D6 | **Multiplicity across features** — BH over everything tried; pre-register the surviving family | Trying 200 features guarantees 10 hits at p<0.05 |
| D7 | **Forward test the survivors** through the audit3 forward gate | A backtest is a hypothesis, not evidence |
| D8 | **Cost check** — daily/weekly events need fill + slippage at 2× measured | Many "edges" vanish at realistic costs |

Tooling: `tools/skyrocket_reverse_eng.py` — computes the event base rate (Wilson CI),
per-feature decile lift, a permutation p-value for rank association, and matched-control
feature differences with bootstrap CIs. It is a discovery instrument: it proposes
candidates and deliberately refuses to declare an edge.

## 6. Level-up layer — from "trusted numbers" to "verifiable audit"

Fixing the numbers gets you a trustworthy scoreboard. These eight get you an audit that can be
*checked by a stranger*, which is what a research ledger is for.

```mermaid
flowchart LR
  subgraph today [Today]
    A1[audit3-ledger every 6h] --> L1[audit3_ledger.json]
    A2[audit-dashboard hourly] --> L1
    L1 --> S1[/audit3/]
    L1 --> S2[/audit/]
    S3[/audit2/ fallback chain]
  end
  subgraph next [Next level]
    CONTRACT[metric contract registry] --> TRIB[tribunal]
    DISC[discovery registry] --> TRIB
    BARS[price data SLA] --> TRIB
    EXCL[exclusion ledger + bias bound] --> TRIB
    TRIB --> GEN[one generation id]
    GEN --> V1[/audit3 truth/]
    GEN --> V2[/audit overview/]
    GEN --> V3[/audit2 method/]
    GEN --> REPLAY[replay verifier]
    GEN --> POWER[MDE per class]
  end
```

| # | Enhancement | Why it is a level up | Test |
|---|---|---|---|
| L1 | **Replayable ledgers** — `audit3 replay <ledger>` regenerates from the pinned inputs (`input_sha256`, `generator_version`, `git_sha`) and diffs | Today a published number is trusted; with replay it is *checkable* by anyone, offline | replay of a pinned ledger is identical modulo timestamps; a tampered ledger fails |
| L2 | **Exclusion ledger + bias bound** (N6 done properly, not skipped) | 41.2% of the book is unscored. If what is excluded differs from what is kept, every headline is biased — and no one has tested that | per-cohort exclusion counts with reasons; scored-vs-unscored comparison on class, direction, hold, entry month; build fails on an unexplained divergence |
| L3 | **Price-data SLA** — stale class renders `UNMEASURABLE (stale since DATE)`, never `unmeasured`, and backfill is a tracked P0 | FOREX has been unmeasurable since **2026-02-09** because of missing bars, not missing edge. The current wording hides that | a class whose last bar is older than N days cannot emit an alpha number; backfill verified by row count and last bar |
| L4 | **Sabotage suite** — inject known-bad cells: pure noise, a look-ahead feature, single-symbol concentration, a survivors-only universe | Existing tests prove gates *fire on fixtures*. This proves the judge has **power** against frauds it will actually meet | each sabotage fixture is demoted below PROVEN; if any passes, the suite is red |
| L5 | **MDE per class** — publish the minimum detectable effect at the real n and dispersion | With no MDE, "we found no edge" is uninformative: it cannot distinguish no edge from no power. This is the lesson from the per-class review, where two classes were *inconclusive*, not negative | every "no edge" claim prints its MDE; a class whose MDE exceeds a plausible edge is labelled underpowered |
| L6 | **Discovery trials feed `n_trials`** — append-only discovery registry of every feature, event and threshold tried; DSR at the forward gate counts them | Otherwise discovery silently inflates the gate's significance: 200 features searched, then a forward test that pretends it was the only trial | a discovery run increments the registry; the forward gate's DSR uses the total; a test asserts the count flows through |
| L7 | **Verdict calibration** — for cells judged PROVEN k runs ago, compare claimed expectancy to realized forward expectancy; publish a calibration curve | Churn rate (N2) is a symptom. Calibration is the disease metric: does PROVEN mean what it claims? | calibration bins with realized-vs-claimed expectancy and a Brier-style score tracked per ledger |
| L8 | **Metric contract registry, enforced** — every published metric name maps to `(population, cost_model, win_definition)` in one machine-readable file | Rule 3 is currently a convention; this makes it a build failure. A page rendering a name it does not own cannot ship | a page that renders an unowned metric fails; adding a metric without a contract entry fails |

Two smaller carries: **normalize-on-read for verdict strings** (the `hypothesis_status.py` pattern —
seven canonical states, `UNKNOWN` never guessed, CLI exits 1 on drift) applied to verdicts across
ledgers, and **`assert_tribunal_runs.py` in CI on every PR**, so a branch that compiles but crashes
at runtime can never again be approved on the strength of `--help`.

## 7. Explicit non-goals

- No new strategy hunting until steps 1–3 are green.
- No promotion to real money; the audit3 forward gate decides that (n≥100 forward rows,
  net CI > 0 at 2× measured slippage, DSR ≥ 0.95), and nothing is close.
- No deletion of strategy evidence to make the numbers look better.
