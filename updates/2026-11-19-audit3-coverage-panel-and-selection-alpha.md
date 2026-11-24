# audit3: coverage panel, selection-alpha headline, ETF reconciliation (2026-11-19)

Three related changes, all from the `/audit` vs `/audit3` surface review
(`docs/AUDIT_SURFACE_REVIEW_2026-11-19.md`, PR #891).

## 1. The page claimed more coverage than it had

**Broken:** `alpha_engine/audit3_tribunal.py` scores `picks.recent_closed`, an export
slice. On the live payload that is **3,500 of 16,330 closed picks (21.4%)**. Nothing on
the page said so, so every verdict read as if it covered the whole closed book. Two
cohorts the publishing dashboard excludes were analysed nowhere:

| Cohort | Rows | Consequence |
|---|---|---|
| `integrity_excluded` | 7,502 | 46% of the book removed before export (ghost rows, WON-vs-PnL sign contradictions, constant pnl) |
| `auto_expired_excluded` | 9,100 | resolved by timeout, neither win nor loss; includes 3,467 expired zero-pnl rows |
| resolver anomalies | 44 stale exits, 23 clamped losses, 3 missing `closed_at` | rows that exist but cannot be trusted at face value |

The counts deliberately do **not** partition the book: 7,502 + 9,100 > 16,330, so the
cohorts overlap. Reporting a clean subtraction would have been a second error.

**Changed:**
- `payload_coverage()` in `audit3_tribunal.py` builds a `coverage` block: scored rows,
  published closed picks, `scored_share_of_total_pct` / `_of_valid_pct`, unscored rows,
  the excluded cohorts with reasons, resolver anomalies, the scored window, row-drop
  counters from `load_rows`, and a `cohorts_overlap` flag with a one-sentence
  `statement`.
- `load_rows(..., drops={})` now counts *why* input rows were dropped
  (`not_a_record`, `no_numeric_pnl`, `not_closed`, `duplicate`) instead of discarding
  them silently.
- `/audit3/` overview gains a **"What this ledger does not score"** card: the statement,
  four coverage KPIs, a cohort/anomaly table, and the scored window. The hero gains a
  **"Share of book judged"** KPI that turns red below 50%.
- The Method tab lists the share of the book judged next to the ledger's provenance.

## 2. Selection alpha is now the headline; PF is demoted

**Broken:** the class table led with WR / PF / net-per-trade, which scores *how the
trade was expressed*. It cannot distinguish skill from beta: a +40% pick on a symbol
that returned +60% still shows as a win.

**Changed:**
- `build_report(..., alpha=...)` joins the M1b sidecar onto the class aggregates
  (`alpha_pct`, `alpha_ci`, `alpha_n`, `alpha_wr`, `hold_net_pct`) and always emits a
  `selection_alpha` block with `available: true|false`.
- New CLI flag `--alpha <path>` (`audit3_selection_alpha.py` output). An unreadable
  sidecar warns and continues — a missing sidecar must never block the ledger.
- Class table order is now: n → WR → **selection alpha vs hold** → net/trade →
  PF (raw, greyed) → gross/trade (greyed) → BH q → DSR → verdict. The page states why
  the greyed columns moved right.
- When no sidecar is present, the page says selection alpha was not computed and why
  (needs per-symbol OHLC / DB credentials), rather than leaving a blank column that
  reads as zero.
- `.github/workflows/audit3-ledger.yml`: new optional step runs the alpha module only
  when `DB_PASS_STOCKS` is set (`continue-on-error`, `|| true`), and passes `--alpha`
  to the tribunal only if the file exists. Reference values from the last successful
  run: CRYPTO LONG −0.442%/pick `[-0.892, −0.085]` n=1142, ETF LONG −0.272%
  `[-0.504, −0.037]` n=261, EQUITY +0.114%.

## 3. ETF: the two surfaces were never measuring the same thing

The review flagged `/audit` ETF **WR 1.92% / PF 0.0195 (n=52)** against audit3
**WR 43.7% / PF 1.05 (n=584)** as "unreconcilable". Reconciled, from the payload:

| | `/audit` | audit3 |
|---|---|---|
| cohort | `at_signal_outcomes.intrabar_*` signal-level outcomes | `picks.recent_closed` pick-level ledger |
| n | 52 | 584 (recomputed: 584 rows, 254 WON / 330 LOST) |
| WR / PF | 1.92% / 0.0195 | 43.66% / 1.0497 |
| cost model | intrabar fill accounting | flat 0.08% slippage → net −0.024%/trade |

`money_ready_verdicts.ETF` sets `sizing_source: intrabar_truth` and carries, inside the
same object, `intrabar_daily_divergence: {daily_wr: 0.5862, daily_pf: 1.8227,
honest_wr: 0.0192, honest_pf: 0.0195, pf_inflation_x: 93.47, flag: true}` plus
`policy_clean_n: 29, policy_clean_wr: 58.62%, policy_clean_pf: 1.8227` and
`mdd: 0.9856`.

**Verdict:** audit3's ETF number is reproducible from the closed ledger and is the
class-level figure. `/audit`'s 1.92% is a 52-row *intrabar signal-outcome* artifact
presented as the class PF — and the same tile simultaneously implies 58.62% WR on 29
"policy clean" rows. So `/audit` is the surface that is wrong **as a label**, not as
arithmetic: it publishes a 52-row intrabar cohort (1 win in 52, 98.6% MDD, 93× PF
inflation vs its own daily accounting) as the ETF asset class. A 93× daily-vs-intrabar
PF gap on the same signals points at the intrabar resolver mislabelling stops, which is
consistent with the already-documented 23 clamped losses and 3,467 expired zero-pnl
rows — but I could not confirm that at row level here (no DB credentials in this
environment), so it stays a hypothesis.

Both samples are far below audit3's n≥100 PROVEN floor, so the defensible class verdict
is unchanged: **no claim on ETF either way**.

## Verification

- `python3 -m py_compile alpha_engine/audit3_tribunal.py` — clean.
- `pytest tests/test_audit3_coverage_alpha.py tests/test_audit3_tribunal.py -q` — all
  pass, including 7 new tests (share-of-book statement, cohort-overlap flag, honest
  "no counts" path, drop counters, alpha join, alpha-absent path, JSON safety).
- Ledger regenerated from the 2026-11-19T04:04Z payload: `coverage.statement` reports
  3,500 of 16,330 (21.4%), `cohorts_overlap: true`.
- `/audit3/` inline JS syntax-checked with `node --check` on the extracted script block.

No strategy logic, gate thresholds, or verdict rules changed. No picks, signals, or
position sizing were touched; `/audit`, `/audit2` and `audit-dashboard.yml` were not
modified.
