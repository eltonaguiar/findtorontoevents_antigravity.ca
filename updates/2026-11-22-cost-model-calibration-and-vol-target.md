# Fix + research, 2026-11-22: carry cost model calibration, vol-target measurement, 50-item programme

## What was broken

`tools/funding_carry_maker_path.py` (new this session) priced every fill as fee + spread,
including maker fills, and charged no spread at all on taker entry. The result was a "retail
taker" path that printed **31.32 bp** round trip against the measured **42.64 bp** — a 26%
understatement of the baseline the whole comparison is anchored to.

That is the exact failure mode the programme exists to catch: a cost model that quietly
disagrees with the number it claims to decompose. A maker path compared against an understated
taker baseline looks less impressive than reality, but the same bug in the other direction
would have manufactured an edge.

## What changed

1. `path_cost()` now prices **per fill**: a taker fill pays fee + spread crossed; a maker fill
   pays fee + adverse selection (and no spread). Fills are classified by comparing the fee to
   the taker fee.
2. A **calibration gate** was added: the taker path must reproduce the measured 42.64 bp within
   0.05 bp, or the tool raises `SystemExit` and refuses to publish. An uncalibrated cost model
   is not allowed to write a report.
3. The recalibrated comparison, which is materially different from the buggy output:

   | path | round trip | beats 3.5% T-bill from |
   |---|---|---|
   | retail taker, both sides (measured) | 42.64 bp | 136 days |
   | maker entry, taker exit | 27.32 bp | 87 days |
   | maker both sides | 12.00 bp | 39 days |

4. **Correction to a published figure.** The earlier break-even tool searched a
   30/60/90/120/180/365 grid and reported `retail_taker_crossing_days = 180`. The exact
   day-search in this tool gives **136**. The grid number was the first row that cleared, not
   the crossing. Verdict unchanged (carry at retail taker does not beat cash on a hold a reader
   will run), precision now accurate.

## What was added

- `tools/vol_target_vs_hold.py` — vol targeting and SMA timing vs buy-and-hold, both yardsticks
  (Sharpe/CE and CAGR/MDD) reported separately so neither can be cherry-picked.
  Result: vol targeting a single asset *lowers* CE (9.81% → 7.06%); on 60/40 it *raises* CAGR
  by 1.43 pp, cuts MDD by 9 pp and raises CE by 1.32 pp. Risk control, not alpha.
- `plans/2026-11-22-50-action-items.md` + `.json` — the prioritised 50-item programme.
- `reports/2026-11-22-cost-is-the-constraint.md` — the per-class breakdown of what actually
  bound each class (2 cost, 1 multiplicity, 3 benchmark, 3 no-signal, 1 data integrity).
- Self-audit of Mercury3's positive-subset median defect class against
  `tools/per_class_edge_harness.py`: clean, all aggregates use the full array.

## How it was verified

- `python3 tools/funding_carry_maker_path.py` → exit 0, calibration gate passed at 42.64 bp,
  wrote `reports/funding_carry/funding_maker_breakeven.json`.
- `python3 tools/vol_target_vs_hold.py --start 2005-01-01` → exit 0, 5,507 rows
  2005-01-03 → 2026-11-20, wrote `reports/portfolio/vol_target_vs_hold.json`.
- Audit sweep: `grep` over both generator files for positive-subset aggregation and for
  `np.mean`/`median` call sites; all confirmed full-array.
- CI on PR #1063: gitleaks, password-grep, runs-for-real, both secret scans pass; the two
  pytest matrix jobs were still pending at the time of writing and are reported as pending,
  not as green.

## Not claimed

No forward observations. No capital. The maker path is a priced assumption, not a measurement of
fill quality; nothing on this box can test whether maker fills are achievable on both legs. The
60/40 vol-target improvement depends on 2005-2026 correlations persisting.
