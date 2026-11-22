# TODO LEDGER — provenance programme, from 2026-11-22

Machine-read by `tools/todo_wakeup_runner.py`. **One item per wakeup.** Each item
carries its own acceptance test so an unattended run cannot claim a pass without
producing evidence.

Rules an unattended run MUST honour (from AGENTS.md / CLAUDE.md):
- Never push `push/phase2-round-2026-11-22` (foreign commits). Safe branch:
  `feat/provenance-ledger-2026-11-22` (PR #1064).
- Never `git reset --hard`, `push --force`, `clean -fd`, or delete branches.
- `export HOME=/home/eaguiar2015` before any Python that reads `~/dbpasses.txt`
  or calls yfinance.
- Document every fix in a `.md` under `updates/`.
- Report gross and net together; never invent a number; mark UNMEASURED instead.
- If a measurement is blocked, say so and move on — do not fabricate a result.

## Status legend
`[ ]` todo · `[~]` in progress (set by a run, cleared on completion) · `[x]` done ·
`[!]` blocked (needs a human or an external event)

---

## [x] T1 — Extend the resolver beyond BTC
DONE 2026-11-22 (commit `602b033bcba`). `resolve_symbol()` covers
CRYPTO/FOREX/COMMODITY/INDEX/BOND/EQUITY/FUTURE; 1h→1d interval fallback;
`bar_interval` + `asset_class` recorded; inverted-level guard added.
**Evidence:** 18 mapping assertions + real-data run across EURUSD=X, GC=F, SPY,
TLT, BTC-USD with correct signs.

## [x] T2 — Wire `pct_forward` into CI as a hard gate
DONE 2026-11-22 (commit `e870d832cc2`). `--gate` blocking at workflow step 9;
yfinance/pandas install added; def-time default-argument bug fixed.
**Evidence:** six gate regimes correct; empty ledger → exit 0; workflow parses
(12 steps); pushed to PR #1064 at `2851cc13617`.

## [!] T3 — Verify the main-path emit actually goes live
BLOCKED on PR #1064 merging. The scanner hook runs from `alpha-engine-fast.yml`
on the **default branch**, so nothing can be verified until merge.
**Acceptance:** after merge, one `alpha-engine-fast` run produces
`reports/provenance/picks_provenance.jsonl` with `n_records > 0`, and
`provenance_verify.yml` reports `chain intact`. Check with
`python3 tools/provenance_ledger.py --stats`.
**Do not** stand up a second emit path to work around the merge — that would be a
second definition of the same measurement.

## [ ] T4 — Add emit callsites beyond `production_scanner.py`
Only `production_scanner.py` emits today, so any pick that never passes through it
is invisible to the ledger — a survivorship hole in the very instrument meant to
close one.
**Acceptance:** at least one second production callsite (start with
`alpha_engine/smart_picks_engine.py` or the hyrotrader path), a documented list of
which paths emit and which do not, and a test proving a pick from the new path
lands in the ledger with a valid chain. Add the new file to
`provenance-verify.yml` push paths.

## [ ] T5 — Ledger vs dashboard reconciliation report
The ledger and `audit_dashboard/data/dashboard_data.json` are two populations of
the same thing. Any divergence is a defect in one of them.
**Acceptance:** `tools/provenance_reconcile.py` emitting
`reports/provenance/reconciliation.json` with: count in ledger, count in dashboard,
count in both, count in neither, and per-asset-class breakdown; plus a written
`updates/2026-*.md` explaining every category of divergence. Must not fail when
either side is empty — report `NO DATA` instead.

## [x] T6 — Fix `tools/deflated_sharpe.py` (4 verified defects)
Documented in `docs/STRATEGY_PROOF_REQUEST_2026-11-22.md` §2:
1. `_deflated_sharpe` returns a z-score and never applies `Φ(·)`, so `dsr` ranges
   [−23.88, +15.08] instead of [0, 1].
2. `survives = dsr > 0` is a 50% significance gate, not 95%.
3. `ANNUAL_TRADES` hardcoded to 2190 → 46.8× Sharpe inflation for every strategy
   regardless of real trade rate (hence annualised Sharpes of 43.9 and 93.2).
4. `_sharpe_se` is passed an annualised SR with a per-trade `T` (unit mismatch).
**Acceptance:** `Φ(·)` applied; the gate is at an explicit, configurable
confidence level; annualisation derived from each strategy's **observed** trade
rate; SE computed in consistent units; a selftest proving `dsr ∈ [0,1]` and that a
known-z input maps to the correct probability; the 64.4% headline withdrawn in the
regenerated artifact. Document in `updates/`.

## [ ] T7 — Scorecard: strict thresholds for the provenance rows
`tools/weekly_scorecard.py` prints the provenance/resolution rows but treats
`EMPTY`/`NO DATA` as non-alerts, so `--strict` exits 0 while nothing is measured.
**Acceptance:** `--strict` distinguishes "not yet measurable" (empty ledger, no
forward record yet — pass) from "should be measurable and is not" (ledger
non-empty but `pct_forward` null, or resolver starved — fail). Reuse the
`--gate` thresholds so there is ONE definition, not two.

## [ ] T8 — COMS broadcast + wrap for each completed block
**Acceptance:** a retained note per block on its own topic
(`notes/<slug>-copilot-<date>`), payload written from a file and
`"$(cat file)"`-expanded, byte-count verified (expect a 1-byte trailing-newline
difference). Never put backticks in a double-quoted shell string.

---

## Notes for an unattended run

- Work top-down, but skip `[!]` items — they need an external event.
- Commit each item before starting the next.
- If an acceptance test cannot be met because of missing data, mark the item `[!]`
  with the reason rather than downgrading the acceptance criterion.
