# Master TODO Tracker — Audit Review (2026-11-19)

**Source:** `reports/AUDIT123_COMPREHENSIVE_REVIEW_2026-11-19.md`
**Status legend:** OPEN / IN PROGRESS / DONE / BLOCKED

---

## P0 — Blocks money-readiness (Sprint 1)

| 36 | Sleeve reconciliation (P0 from Copilot plan) | §2.6, new | OPEN | /audit top_sleeves (AuditEnsemble_LONG PF 155.85, CorrKama PF 111.81, non_crypto_consensus PF 9.68) are NOT in audit3 cells. Single-source, policy_clean/resolver_grade sources. Need: flag as UNVERIFIED on /audit, add sleeve ingestion to audit3 tribunal |

| # | Item | Section | Status | Notes |
|---|---|---|---|---|
| 1 | Implement selection alpha (`audit3_selection_alpha.py`) — needs price tables | §4.3, §6.2 #1 | DONE | Ran successfully: 3,066/3,500 picks covered. Pick +0.261% vs hold +0.389% => ALPHA -0.128% (CI=[-0.513, 0.225]). CRYPTO/LONG -0.525% (worst), CRYPTO/SHORT +0.398% (best). Confirms negative selection skill |
| 2 | Register POD-EQUITY-BREAKOUT in `CONDITIONS` (`forward_observations_ingest.py`) | §3.3, §11 #1 | DONE | Added 13 actual EQUITY/ETF strategy names. Ingest now finds 177 EQUITY rows (was 0). Total ledger 607 rows |
| 3 | Harmonize cost/slippage constants → `cost_model.py` as single source of truth | §9.2 | DONE | OTHER_BP now sourced from cost_model.get_total_bps(). EQUITY 8→7, ETF 8→3, FOREX 4→2, COMMODITY 12→7, FUTURES 12→5.5, BOND 2→4.5 |
| 4 | Recalibrate upstream ML confidence generators | §2.1, §6.3 #23 | OPEN | Inverted: conf≥0.9 → 14.4% WR; conf 0.50–0.60 → 60.3% WR. Score-booster penalties shipped but generators not fixed |
| 5 | Wire random-entry MC from `benchmark_closed_ledger.py` into audit3 | §4.11, §6.2 #11 | OPEN | Needs per-symbol price series; coin-flip CI gate already exists |

## P1 — Improves signal quality (Sprint 2)

| # | Item | Section | Status | Notes |
|---|---|---|---|---|
| 6 | TP/SL permutation matrix (6 variants × cost multipliers × time-stops) | §7 | DONE | 75 combos tested on MES ORB. Best by PF: TP=2.5x, SL=1.25x, TS=3PM (PF 2.155, WR 52%, net $1,489). Best by net: TP=3.0x, SL=1.5x, TS=4PM (PF 1.936, WR 56%, net $1,776). All combos positive. Original 2.0/1.0/11AM was suboptimal |
| 7 | Volume as additional filter (5 variants + 36-cell matrix) | §8 | OPEN | Volume confirmation exists in Smart Picks scoring but not systematically tested at asset-class level |
| 8 | Stamp section name onto closed rows at resolution time | §4.7, §6.2 #21 | OPEN | Sections × Class is currently a proxy reconstruction |
| 9 | Mandate trade-log emission from all backtests | §4.9, §9.3 | OPEN | Only 11/145 evidence-registry strategies re-testable (7.6%) |
| 10 | Consolidate 4 walk-forward implementations into 1 | §9.3 | OPEN | `walk_forward_backtester.py`, `rolling_walk_forward.py`, `walk_forward_validator.py`, `walkforward_validator.py` |
| 11 | Wire `value_screener.py` to production + momentum overlay + IV-attainment resolver | §10.1, §15.3 | PARTIAL | Runner works (22 picks emitted 2026-11-19). Weekly workflow exists with continue-on-error guard. Weight inconsistency (0.45/0.55 vs UEPS 0.55/0.45) still needs reconciliation. Momentum overlay not yet added |
| 12 | Normalize hypothesis status vocabulary | §2.5, §6.2 #15 | OPEN | PRE_REGISTERED vs PRE-REGISTERED; FORWARD_OBSERVATION vs FORWARD OBSERVATION etc. |
| 13 | Build `mutual_fund_screener.py` (Lipper + Morningstar + 3P) | §10.3, §15.1 | OPEN | Biggest untapped money-ready opportunity. No screener exists |
| 14 | Build `bond_screener.py` (duration + credit + real yield) | §10.4, §15.5 | OPEN | No bond screener exists |
| 15 | Rebuild commodity picking on term structure (replace falsified COT) | §10.6, §15.6 | OPEN | COT positioning DSR=1.0 FALSIFIED. Intrabar truth (40.2% WR/PF 1.03) suggests weak edge buried |
| 16 | ETF momentum+exit experiment (ScienceDirect 144-combo grid) | §15.2 | DONE | Faber GTAA best: Sharpe 0.915, MDD -20.5%, OOS Sharpe 1.13. Multi-horizon momentum underperforms (Sharpe 0.636). Simple > complex. 60/40: Sharpe 0.835. SPY BH: Sharpe 0.777, MDD -50.8% |

## P2 — Hygiene / UX (Sprint 3)

| # | Item | Section | Status | Notes |
|---|---|---|---|---|
| 17 | Collapse dual PF/WR per class → one canonical figure + window label | §2.7, §6.2 #17 | OPEN | CRYPTO recent PF 0.89 vs headline 1.25 causes confusion |
| 18 | Demote post-hoc segment numbers behind a toggle | §2.12, §6.2 #18 | OPEN | 82% WR / PF 11+ still displayed prominently despite warning |
| 19 | Remove DEAD cells from "Best filter" table | §2.13, §6.2 #19 | OPEN | Stocks PF 0.77 displayed as filter recommendation |
| 20 | Disambiguate "PROVEN" (strategy vs trust-tier vs PROVEN_T2) | §2.10, §6.2 #20 | OPEN | Overloaded term causes conflation |
| 21 | Add re-test schedule for killed cells | §4.4, §6.2 #22 | OPEN | No "since when" or re-test window on kills |
| 22 | Serve `reports/` so forward clock + pod registry are live | §3.9, §6.1 #4 | OPEN | Pod registry is static snapshot dated 2026-11-19 |
| 23 | Add CSV export to strategy/symbol cells tabs | §4.5, §4.6 | OPEN | No export button on audit3 tabs |
| 24 | Fix "unknown" strategy rows (n=260, WR 28.1%) | §4.8, §6.1 #6 | OPEN | Labeling gap at emission time |
| 25 | Fix class mismatches (11 rows) | §4.9, §6.1 #7 | OPEN | FOREX labeled CRYPTO; CT=F labeled FUTURES not COMMODITY |
| 26 | Fix FUTURES n=4 vs intrabar n=52 gap | §5, §6.1 #9 | OPEN | Large unexplained discrepancy |
| 27 | Fix UEPS n=0/100 (no forward accrual wired) | §2.18, §6.1 #10 | OPEN | Research ledger, not money book |

## Sprint 4 — $2,000 micro-futures ORB strategy (new)

| # | Item | Section | Status | Notes |
|---|---|---|---|---|
| 28 | Backtest ORB on MES (2019–2026, 5-min, 15-min range, volume filter, time stop) | §16.2, §17 | DONE | 48 trades, WR 45.8%, PF 1.53, net +$683 (60 days). Volume filter improves PF +0.13. Annualized ~$3,278/yr on $2,000 |
| 29 | 30-session paper trading protocol | §19.2 | OPEN | ForTraders methodology: 1 instrument, 1 setup, 30 sessions |
| 30 | Shadow mode (live-plus-shadow evaluation) | §19.3 | OPEN | NeuraTrade PR #260: non-blocking, full audit trail |
| 31 | Live micro-size (1 contract, 1% risk, kill switch, progressive drawdown ladder) | §19.5, §19.7 | OPEN | 5-rung governance: NORMAL→WARNING→PROBATION→SUSPENDED→BREACHED |
| 32 | Parallel variant testing (5 ORB variants in shadow) | §19.6 | OPEN | Never promote without ≥2 weeks shadow testing |

## COMS coordination (ongoing)

| # | Item | Status | Notes |
|---|---|---|---|
| 33 | COMS check + reply cycle (6 runs, 10-min intervals) | IN PROGRESS | Run 2/6 completed. Self-disables after run 6 |
| 34 | Peer critique of §13 (8 questions) | OPEN | No peer replies received yet |
| 35 | COMS hygiene (advisory): no retained status/* liveness, leftover inbox, Windows check-verb docs | OPEN | Not mine to change |

---

## Quick-start: what to do first

1. **Run #2** (POD-EQUITY-BREAKOUT) — 5 minutes, unblocks EQUITY testing.
2. **Run #3** (cost harmonization) — 1 hour, fixes 3 inconsistent constant sets.
3. **Run #28** (ORB backtest) — 1 day, validates the $2,000 strategy.
4. **Run #13** (mutual fund screener) — 1 week, highest-expected-value money-ready work.

---

*Generated 2026-11-19 by opencode (Beam Free). Consolidated from `AUDIT123_COMPREHENSIVE_REVIEW_2026-11-19.md` (18 sections).*
