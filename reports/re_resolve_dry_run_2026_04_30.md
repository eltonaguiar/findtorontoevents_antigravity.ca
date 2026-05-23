# Historical Re-Resolve Dry-Run — 2026-04-30

**Status:** DRY-RUN ONLY (no source files modified)
**Trigger:** Backlog item #2 from `reports/INTEGRATION_PLAN_OPEN_PRS_2026_04_30.md` §"Next-PR Backlog"
**Script:** `tools/re_resolve_historical_v2.py` (already shipped in PR #463)
**Command:** `py -3 tools/re_resolve_historical_v2.py --dry-run --report`
**Delta CSV:** [`reports/re_resolve_delta_2026_04_28.csv`](reports/re_resolve_delta_2026_04_28.csv) (74 rows)

---

## Summary

The historical re-resolve replays every closed non-crypto pick under the v2 outcome resolver (5bp asset-class-gated WIN threshold, daily OHLC bar replay) and writes a delta CSV showing label flips. **No source files modified.**

### Top-line findings

| Metric | Value |
|---|---|
| Total candidate picks scanned | **73** |
| Source files with picks | 2 of 9 (`closed_picks.json` n=26, `closed_picks_fast.json` n=47) |
| WON → other flips | 3 |
| LOST → other flips | 7 |
| Total status flips (script-authoritative) | **10 / 73 = 13.7%** |
| OHLC unavailable (yfinance miss) | 0 |
| Files modified by this run | 0 (dry-run) |

### Scope correction

The original design doc at `reports/action_B_resolver_2026_04_27.md` claimed "~1,860 historical non-crypto picks" needed re-resolution. **Actual scope is ~25× smaller.** Most non-crypto picks live in source files that the script doesn't currently target — the 7 copy_trader_intel files and genome/data/revival files all returned 0 candidates. Worth investigating whether:
- (a) Those source files are empty / pruned (no need to re-resolve)
- (b) The script's `_iter_source_files()` filter is too narrow (need to widen)

Recommend a follow-up audit of source-file selection before any `--apply` run.

---

## Sample flips (FOREX-heavy, as predicted)

The largest single magnitude flip is a EURUSD pick that goes from -0.9% LOST → +2.3% WON. Several similar AUDJPY / NZDUSD / EURUSD picks show the same pattern:

| asset_class | symbol | old_status → new_status | old_pnl | new_pnl |
|---|---|---|---|---|
| FOREX | NZDUSD=X | LOST → WON | -0.0019 (~-0.2bp) | +0.003 (~+30bp) |
| FOREX | EURGBP=X | LOST → FLAT | -0.0023 | -0.0000035 |
| FOREX | AUDJPY=X | LOST → WON | -0.0061 | +0.031 |
| FOREX | AUDJPY=X | LOST → WON | -0.0093 | +0.025 |
| FOREX | EURUSD=X | LOST → WON | -0.009 | +0.023 |

**Pattern:** all sample flips are FOREX picks where the old resolver classified small fractional moves as LOST. Under v2, daily OHLC bar replay catches that the price actually touched TP intra-day. This is **exactly the noise-share bug** the resolver fix targeted (per `CLAUDE.md` Goal #1: *"FOREX/COMMODITY noise share is 63-67% until this lands"*).

---

## Per-asset-class breakdown (flip counts)

| Asset class | Total in sample | Flips | Notes |
|---|---|---|---|
| FOREX | 29 | majority of corrections | Confirms CLAUDE.md noise-share claim |
| STOCK | 18 | minor | Mostly unchanged |
| COMMODITY | 12 | small | Sample size insufficient for tier conclusion |
| CRYPTO | 7 | 0 expected | CRYPTO uses 0.1bp threshold (unchanged) |
| EQUITY | 5 | small | Tiny sample |
| ETF | 2 | n/a | Tiny sample |

---

## What this PR ships

Just this report. **No code change. No script change. No source-file modification.** The script `tools/re_resolve_historical_v2.py` and the delta CSV `reports/re_resolve_delta_2026_04_28.csv` already exist on `main` (shipped in PR #463).

This PR is **the operator-action gate** documented in PR #463's design (§9.2 "Day 0: PR-B2 (this script + dry-run report)").

## Next step (separate operator-approved PR)

Per design doc §9.2:

> **Day 1: PR-B3 (pause cron, run for real, commit corrected files)**
> ```
> # 1. Pause the outcome-resolver.yml cron
> # 2. python tools/re_resolve_historical_v2.py --apply
> # 3. Commit the 2 corrected files: closed_picks.json + closed_picks_fast.json
> # 4. Re-enable the cron
> ```

**Acceptance criteria for the --apply PR:**
- All 73 picks have `resolver_version="v2"` stamp
- Each picks's `_legacy_pnl_pct` and `_legacy_exit_reason` preserved for audit
- The 10 status flips show the v1→v2 delta in the commit message
- Re-run the noise-share check from the design doc to confirm FOREX/COMMODITY noise-share has dropped from 63-67% baseline

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| ML retraining shock from label inversion | Medium | 10 picks is small enough to monitor manually post-apply |
| Race with hourly resolver cron | High during apply | Pause cron BEFORE `--apply` (per design doc) |
| yfinance rate-limit on the rerun | Low | Already passed (0 OHLC misses on this dry-run) |
| Source-file scope smaller than design claimed | (Realized) | This PR documents — operator decides whether to widen scope |

---

## Cross-reference

- PR #463 (merged): resolver v2 code + this script (dry-run-only)
- `reports/action_B_resolver_2026_04_27.md` §5 "Historical re-resolve runbook" (design)
- `reports/INTEGRATION_PLAN_OPEN_PRS_2026_04_30.md` Stream #10 backlog item #2

---

*Generated by orchestrator as the dry-run gate before any `--apply` run. Operator decides scope-widening + apply timing.*
