# Weekly scorecard + CI gate (2026-11-22)

Closes todo **48**.
Reproducer: `python3 tools/weekly_scorecard.py [--strict]`
Workflow: `.github/workflows/weekly-scorecard.yml` — Mondays 06:17 UTC.
Outputs: `reports/weekly_scorecard/scorecard.md`, `scorecard.json`

---

## What it does

Reads every measurement artifact the programme has produced and emits one page:
every verdict, every unmeasured state, and the alerts that block a promotion.

Current output (first run, 2026-11-22):

| item | verdict | evidence |
|---|---|---|
| Harness certification | **PASS** | 6 harnesses (5 deterministic, 1 live) |
| Integrity lint | **NOT RUN** | artifact absent |
| Live ledger net expectancy | **−15.24 bp** | n=10,968, PF 0.904, CI-LB 0.852, t=−3.91 |
| ⠀CRYPTO | **FAIL** | −18.17 bp, PF 0.885 (LB 0.829), n=9,099 |
| ⠀EQUITY | pf>1 but CI includes 1 | +18.60 bp, PF 1.088 (LB 0.885), n=936 |
| ⠀ETF | **FAIL** | −0.32 bp, PF 0.997 (LB 0.802), n=590 |
| ⠀FOREX | **FAIL** | −15.13 bp, PF 0.668, n=252 |
| ⠀COMMODITY | **FAIL** | −346.51 bp, PF 0.120, n=44 |
| ⠀BOND | **FAIL** | −18.22 bp, PF 0.657, n=35 |
| ⠀FUTURES | **INSUFF-N** | +57.09 bp, PF 1.556 (LB 0.341), n=12 |
| Funding carry, net of fees | **REFUTED** | +3.555%/yr but halves 5.96 → 1.24%/yr; 6/28 blocks negative |
| Vol risk premium (existence) | **ESTABLISHED** | +357.9 bp, t=46.50 |
| ⠀short-vol harvest | **RUINED** | worst period −102.9% |
| ⠀GDX/SLV pairs | **REFUTED** | ADF OOS 0.15, net +2.228%/yr |
| Prediction market calibration | **ESTABLISHED** | Brier skill 0.4956, n=362 |
| Execution capacity | **CAPPED** | largest size clearing the cliff: $500,000 |
| ⠀breakout gross edge | **UNMEASURED cost** | 0bp +22.43 (t 7.32) → 24bp −1.57 |
| ⠀fill-convention premium | **INFLATION** | lag-0 fill worth 2.54 bp/trade |
| ⠀turnover frequency | **cost dial** | best Sharpe 0.81 at monthly |

## Design decisions worth keeping

1. **Degrades to NOT RUN, never to an estimate.** A missing artifact prints the
   command that would produce it. It cannot silently omit a dead measurement.
2. **No ranking.** There is no "best strategy" row, by design. Ranking is the
   mechanism by which an unmeasured candidate acquires apparent authority; labels
   here come from evidence class, not from return.
3. **`--strict` exits 1 on any alert.** Wired into CI so harness drift or a new
   integrity finding fails the job. A scorecard that can only ever be green is
   decoration.
4. **No push trigger, own concurrency group, `[skip ci]` commit.** Follows the
   2026-05-19 precedent in `AGENTS.md` that removed push triggers from long
   audit jobs after cancel-cascades, and keeps this cron clear of `:10`
   (audit-dashboard) and `:41` (harness-certification).

## Bug I caught building it

The first version printed `deterministic changes: n/a` for the harness row and
`$n/a` for the capacity row, because it guessed field names (`section1_capacity`,
`n_changed`) that do not exist. The artifacts actually nest at
`results.todo4_capacity.curve[<size>].clears_cliff` and `harnesses[<name>]._class`.
Guessing field names produced a scorecard that looked complete and reported
nothing — the same failure mode as the dead `consult_multi` presets in todo 46.
Both are now read from the real schema, and the harness row states plainly that
drift-vs-baseline is decided by `tools/harness_certification.py --rerun`, not by
this script.

## Known gap

`Integrity lint` reads `reports/integrity_lint/latest.json`, which no run has
written yet. The lint currently writes its baseline elsewhere. Until
`tools/integrity_lint.py` emits `reports/integrity_lint/latest.json`, that row
reads **NOT RUN** — which is the honest state, not a passing state.
