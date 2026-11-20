# Consolidating /audit + /audit2 + /audit3 into one source of truth

**Date:** 2026-11-20
**Author seat:** `freebuff-deepseek-v4-flash` (COMS `inbox/gx10-c9b9/findtorontoevents_antigravity-ca/`)
**Base:** `origin/main` @ the commit this PR branched from
**Status:** plan. No behaviour change in this PR.

---

## 1. What the three surfaces are today (measured, not described)

| Surface | Size | Role | Data it actually reads |
|---|---|---|---|
| `/audit/` | 1.44 MB | pick-level dashboard ("Unified Audit Dashboard v99.0") | `dashboard_data.json` (25.8 MB) + ~14 sidecars; **never reads `audit3_ledger.json`** (`grep -c` = 0 in `index.html` and `template.html`) |
| `/audit2/` | 6.7 KB | candidate + methodology library | `audit3_ledger.json` via a **4-path fallback** list, plus `audit2_forward.json`, `audit2_pods.json` |
| `/audit3/` | 45.7 KB | quant kill tribunal | `audit3_ledger.json`, `audit3_evidence.json` |

The `/audit` page is a pick table with its own promotion verdict; `/audit3` is a statistical
tribunal with its own verdict vocabulary. **They are two independent opinions about the same
asset classes, and nothing reconciles them.**

## 2. The contradictions that matter (same day, same repo)

`/audit` reads `money_ready_verdict.json`; `/audit3` reads `audit3_ledger.json`.

| Class | `/audit` verdict | `/audit3` verdict |
|---|---|---|
| CRYPTO | NOT_READY (n=22,148, PF 0.26) | **KILL** |
| COMMODITY | **WATCH** (n=26, PF 0.29) | **KILL** |
| ETF | INSUFFICIENT_DATA (n=29, PF 1.82, WR 58.6%) | **WEAK** |
| EQUITY | NOT_READY (n=115, PF 0.60) | WEAK |
| FOREX | NOT_READY (n=456, PF 0.26) | WEAK |
| BOND | INSUFFICIENT_DATA (n=2) | WEAK |
| FUTURES | INSUFFICIENT_DATA (n=17, PF 1.27) | INSUFFICIENT_N |

Two of these are outright contradictions, not vocabulary differences:

1. **COMMODITY is `WATCH` on /audit while /audit3 kills it** — and /audit's own numbers for it are
   a losing PF (0.29) and a 30.8% win rate. A `WATCH` with a losing PF is a bug in the promotion
   gate or in which field it reads.
2. **ETF is `INSUFFICIENT_DATA` on /audit but `WEAK` on /audit3** — the only class whose raw
   numbers look positive (PF 1.82, WR 58.6%) is dismissed as thin on one surface and judged on the
   other. Nobody can tell whether that is honest cautiousness or two different denominators.

Both surfaces are individually defensible. Together they make the system un-auditable: a reader
cannot answer "is ETF worth money?" without knowing which page is authoritative, and there is no
page that says.

## 3. Duplicate machinery behind the duplication

Same artifact, multiple producers or publishers:

| Artifact | Produced by | Published by |
|---|---|---|
| `audit3_ledger.json` | `alpha_engine/audit3_tribunal.py` | `audit3-ledger.yml`, `audit3-health.yml`, `audit3-denylist-watchdog.yml`, `forward-observations-ingest.yml` |
| `money_ready_verdict.json` | `alpha_engine/money_ready_verdict.py`, `verified_promotion_gate.py` | `audit-dashboard.yml`, `money-ready-snapshot.yml` |
| `pf_registry.json` | `bootstrap_verified_edges.py`, `strategy_kill_list.json` | `audit-dashboard.yml`, `money-ready-registry-gate.yml` |
| `audit2_forward.json` | `tools/audit2_forward_summary.py` | `audit3-ledger.yml` **and** `audit-dashboard.yml` |
| `dashboard_data.json` | many | **19 workflows reference it** |

Scale of the surface: **356 JSON files, 88 MB, 58 of them over 100 KB**, published by a
`data/*.json` glob rather than an explicit manifest. The single-publisher bug fixed today
(PR #994) was one instance of this class; there are at least four more.

Two different "implausible PF" ceilings are live at once: `money_ready_verdict.py`
`_PF_IMPLAUSIBLE = 5.0`, and `audit3_tribunal.py` sleeve gate `PF_CEILING = 25.0`. A PF of 12 is
"implausible" to one surface and "rankable" to the other.

## 4. Data-quality reality behind the verdicts

From `audit3_ledger.json` (canonical denominator):

- **8,769** canonical kept rows
- excluded: **`invalid_row` 7,394** ← 45% of all rows
- `mirror_duplicate` 95, `non_performance_exit` 43, `resolver_breakeven_fallback` 71
- `selection_alpha` available, covered 3,162
- **362** scored cells; hypothesis registry **108** entries
  (22 PRE_REGISTERED, 19 FORWARD_OBSERVATION, 15 REFUTED, 7 PAPER_PILOT, ~2 SUPPORTED/TESTED_PASS)

`money_ready_verdict.json` summary: **`money_ready: []`** (0 of 11 classes), `watch: [COMMODITY]`.
`reports/forward_observations.jsonl` is 430 rows, **all** `H-119`, with `fees = 0.0` and
`funding = 0.0` on 100% of rows — every expectancy computed from it is missing cost drag.

**Honest conclusion: nothing here is money-worthy today.** The useful work is making the system
say that consistently, and making the one credible candidate (ETF, PF 1.82 on n=29) resolvable by
adding n rather than by argument.

## 5. Fix plan

### P0 — trust (small, surgical, no schema change)

1. **Declare precedence in one line of code, not prose.** `/audit`'s class verdict is
   authoritative for promotion; `/audit3`'s verdict is authoritative for statistical validity. Where
   they disagree the page must render **both** with a `DIVERGENT` badge and the reason — never let
   one silently override the other.
2. **Reconcile COMMODITY.** `WATCH` + PF 0.29 is a defect. Either the gate is reading
   `policy_clean_pf` while `WATCH` was computed from a different field, or the threshold is wrong.
   Add a unit test: `verdict == WATCH` requires `pf >= 1.0 AND n >= MIN_N_CLASS`.
3. **Pin `/audit2`.** `audit2.js:138` lists 4 `LEDGER_PATHS` and silently falls through on 404.
   Pin to `../audit3/audit3_ledger.json` and delete the other three; a fallback chain turns a
   missing deploy into a stale-but-plausible page.
4. **One PF ceiling.** Pick one constant (`PF_IMPLAUSIBLE`) in `alpha_engine/config.py` and import
   it in both `money_ready_verdict.py` (5.0) and `audit3_tribunal.py` (25.0). Document the choice
   with the sleeve evidence (155.85, 111.81, 56.73, 49.37, 33.09 all flagged implausible today).
5. **Budget `invalid_row`.** 45% invalid is the biggest single quality problem. Add a ledger-step
   assertion: fail the build when `invalid_row / total > 0.10`, and print the top three invalid
   reasons. Silent exclusion is how "n=22,148 CRYPTO" coexists with "PF 0.26".

### P1 — one source

6. **One canonical per-class verdict document**, `audit_dashboard/data/class_verdict.json`
   (`schema: audit.verdict.v1`), produced by **one** module (`alpha_engine/class_verdict.py`) that
   merges: tribunal cells (validity), money-ready gates (promotion), hypothesis registry
   (provenance), coverage/denominator (population), selection alpha (skill vs beta).
   Fields per class: `verdict`, `promotion`, `validity`, `n`, `pf`, `wr`, `expectancy_net_ci`,
   `coverage_share`, `alpha_covered`, `hypotheses_supported/refuted`, `divergence{from,reason}`.
7. **All three surfaces read that file** for class-level claims. `/audit` keeps its pick tables
   (pick-level detail belongs there); it stops computing a second class verdict.
8. **Deprecate duplicate producers** — exactly one writer per artifact. Retire the second producer
   of `money_ready_verdict.json` and the duplicate publisher of `audit2_forward.json`.
9. **Publish by manifest, not glob.** Replace `data/*.json` with an explicit list so adding a file
   to the repo cannot silently add it to the live site (this is the #994 bug class).

### P2 — evidence

10. **Cost drag is mandatory**: reject `forward_observations` rows with `fees == 0` and
    `funding == 0`; regenerate the 430 H-119 rows.
11. **Resolve ETF honestly**: it needs n ≥ 100 (currently 29). Either accrue forward observations
    until it clears, or keep INSUFFICIENT_DATA and stop showing it near the promotion boundary.
12. **DB as the durable store, JSON as the view**: `ejaguiar1_stocks` / `ejaguiar1_backtests` hold
    the pick and backtest history; the JSON sidecars should be regenerable from them, not primary.
    Add a check that a sidecar's `generated_at` is newer than its source table's max row.

## 6. Test plan

| # | Test | File / command | Fails when |
|---|---|---|---|
| T1 | Verdict schema contract | `tests/test_class_verdict_schema.py` (new) | missing key, unknown enum, `KILL` without `validity=FAIL`, `MONEY_READY` with `pf<1.5` |
| T2 | Single-source allowlist | extend `tools/assert_surface_parity.py` | any surface fetches a ledger path outside the allowlist (catches `/audit2`'s 4-path chain) |
| T3 | Cross-surface verdict equality | same tool, new assertion | `/audit` and `/audit3` disagree without a `divergence` block |
| T4 | Runtime gate on every PR | `.github/workflows/tribunal-runtime-gate.yml` (**shipped**) | the tribunal crashes on real picks |
| T5 | Coverage budget | ledger step in `audit3-ledger.yml` | `invalid_row / total > 0.10` |
| T6 | Cost drag present | `tests/test_forward_cost_drag.py` (new) | any forward row has fees+funder both zero |
| T7 | Publisher uniqueness | `tests/test_single_publisher.py` (new) | two workflows publish the same artifact name |
| T8 | Page weight budget | `tools/assert_page_budget.py` (new) | `/audit` HTML > 2 MB, ledger > 1 MB, `dashboard_data.json` > 30 MB |
| T9 | Negative controls | in T4 + T7 | gate passes a deliberately crashed tree, or a duplicate publisher is not detected |

Negatives are not optional: T4 and T7 already have proven negative cases (injected
`TypeError`, stale republish), which is the only reason to believe they are real gates.

**Acceptance:** T1–T9 green in CI, `/audit` and `/audit3` rendering identical class verdicts with
explicit divergence badges, 0 artifacts with two publishers, `invalid_row` under 10%.

## 7. Sequencing and risk

1. P0 items 2–4 are single-file diffs with tests — land first, no schema change.
2. Item 6/7 (one verdict document) is the real change; land it behind a `CLASS_VERDICT_V1=1` flag
   so the old path stays comparable for one cycle, then delete the old path.
3. Items 8/9 touch deployment; do them with the parity tool green before and after.

**Risk:** collapsing two verdicts can *hide* a real disagreement. That is why P0-1 requires both
verdicts to render side by side during the transition and why T3 asserts on divergence rather than
on sameness.

**Limitation of this plan:** it is derived from committed artifacts and live pages on one day. The
two contradictions (COMMODITY, ETF) could both be explained by a field mismatch rather than a
policy difference; that is exactly what P0-2 exists to determine before anything is rewritten.
