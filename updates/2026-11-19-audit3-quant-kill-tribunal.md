# audit3 — quantitative kill tribunal (`findtorontoevents.ca/audit3`)

**Date:** 2026-11-19
**Status:** built, tested, ledger generated from the live 04:04Z snapshot.
**Scope:** new, isolated surface. No changes to `/audit`, `/audit2`, `audit-dashboard.yml`,
or any file the audit2 swarm is touching.

## What was broken

`/audit` accumulated dozens of overlapping surfaces — six filter rows, smart picks,
money-ready tiers, tier-2 proven, kill switch, copytrader, prediction markets — and
none of them answered one question consistently: *which cells have a realized edge
that survives the number of tests we ran?*

The page also mixed gross and net statistics, published WR on tiny samples, and
reported "NOT money-ready" for every class without showing the arithmetic that
produced the verdict. Two different filter stacks on the same page could show
CRYPTO at 35.8% WR and 38.4% WR with different PF values, both unlabelled.

## What audit3 is

One static page, one JSON sidecar, one stdlib-only Python module:

| File | Role |
|---|---|
| `alpha_engine/audit3_tribunal.py` | all statistics + verdicts (no network, no DB, 4s on 3.5k rows) |
| `audit_dashboard/data/audit3_ledger.json` | generated evidence ledger |
| `audit_dashboard/audit3.html` | renderer only; performs no statistics |
| `tests/test_audit3_tribunal.py` | 13 deterministic unit tests |
| `.github/workflows/audit3-ledger.yml` | independent 6-hourly refresh + FTP deploy |

### Gates (declared before looking at results)

- **G0 sample floor** — n ≥ 20 for any verdict, n ≥ 100 for PROVEN.
- **G1 edge direction** — one-sided exact binomial test of WR > 50%.
- **G2 net expectancy** — 2,000-resample seeded bootstrap 95% CI must exclude 0,
  after per-class round-trip slippage (CRYPTO 15bp, EQUITY 10bp, …).
- **G3 multiplicity** — Benjamini–Hochberg q ≤ 0.10 across every tested cell.
- **G4 overfit** — Deflated Sharpe ≥ 0.95 with `n_trials` = tested cells.
- **G5 stability** — chronological split-half: both halves net mean > 0.
- **G6 concentration** — symbol ≤ 60% of a cell; source ≤ 90% of an aggregate.
- **G7 cost realism** — win is defined as *net* pnl > 0, never gross.

Verdicts: `PROVEN_T2`, `CANDIDATE`, `WEAK`, `KILL`, `INSUFFICIENT_N`.
`KILL` requires the net-expectancy CI entirely below zero, or PF < 0.80 at n ≥ 50.

The page also carries the **hypothesis tracker** (joins `reports/hypothesis_registry.json`,
M-107 pre-registration rule) and the **kill tribunal** (every kill ships with a mutation
instruction: invert, filter, drop dominant symbol, require a second source, or retire).

## Live result (2026-11-19T04:04Z snapshot, 3,500 closed picks)

- 45 strategy cells tested (171 total cells incl. n < 20).
- **0 PROVEN_T2, 0 CANDIDATE, 33 WEAK, 12 KILL.**
- Class verdicts: CRYPTO **KILL** (n=1,851, WR 39.8%, PF 0.72, net −0.51%/trade),
  FOREX **KILL** (PF 0.69), COMMODITY **KILL** (PF 0.12), EQUITY WEAK,
  ETF WEAK, BOND WEAK, FUTURES INSUFFICIENT_N.
- Copytrader family **KILL** (n=81, WR 35.8%, PF 0.30). Prediction-market family
  has n=1 in this ledger — not testable; it needs its own resolved-pick feed.
- This is consistent with the `/audit` class table the user pasted (CRYPTO 35.8%,
  FOREX 32%, ETF 2.1%) — audit3 just shows the arithmetic and applies multiplicity.

## GitHub Actions design (non-interference)

- Own concurrency group `audit3-ledger`; never queues behind the 35-min audit build.
- Cron `23 */6 * * *`, off the `:10` hourly audit-dashboard slot.
- **No `push:` trigger** → cannot create the commit/deploy loop that forced removal
  of the audit-dashboard push trigger (2026-05-19).
- Reads the live snapshot over HTTP (one 26MB GET) instead of re-running scanners,
  so it adds ~5s of compute and no DB load. The same snapshot is already what the
  dashboard serves; no second source of truth is introduced.
- Stdlib only: no pip install, no MySQL connection, no yfinance.
- Commit is data-only with `[skip ci]`; deploy is two FTP files under `/audit3/`.

## Verification

- `python3 -m pytest tests/test_audit3_tribunal.py -q` — 13 passed.
- Ledger built from the live URL (`HTTP 200`, 26,296,986 bytes, generated_at
  2026-11-19T04:04:16Z); strict JSON (`allow_nan=False`) validated.
- Page JavaScript syntax-checked with `node --check`.
- No existing file modified except this doc and the new files listed above.

## Known limits (stated on the page)

- Measures the realized closed-pick ledger; cannot detect look-ahead leakage,
  mislabeled resolutions, or a feed that stopped emitting.
- Random-entry timing null is not run in this job (needs per-symbol price series);
  the companion is `alpha_engine/benchmark_closed_ledger.py`.
- Family bucketing is name-based; per-trader copytrader reverse engineering needs
  its own ledger.
