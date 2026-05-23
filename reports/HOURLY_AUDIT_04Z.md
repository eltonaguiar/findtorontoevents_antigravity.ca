# Hourly Audit — 2026-05-12T04Z

**Generated:** 2026-05-12T04:18Z  
**Agent:** Claude Sonnet 4.6 (claude-sonnet-4-6)  
**Dashboard data:** `audit_dashboard/data/dashboard_data.json` — generated_at `2026-05-12T02:50:43Z` (~1.5h stale, within hourly cadence)  
**Picks window:** 3402 parseable trades, 2026-02-21 → 2026-05-12T02:26Z  
**Context issues:** #685 (resolver DONE), #686 (per-asset quality), #693 (EQUITY divergence)

---

## 1. Dashboard Refresh Status

Pull from origin/main: **OK** (rebased to `cb5a655e`, latest commit 2026-05-12T04:12Z).  
`dashboard_data.json` generated_at `2026-05-12T02:50:43Z` — within acceptable hourly cadence.

`asset_class_health` snapshot (long-run, from file):

| Class     | PF   | WR%  | Notes                              |
|-----------|------|------|------------------------------------||
| CRYPTO    | 1.41 | 48.4 | Post-resolver-v2; quan_engine HYPEUSDT block (#694) active |
| EQUITY    | 1.57 | 53.7 | Post-goldmine_6x_consensus kill (#692) |
| COMMODITY | 3.97 | 67.2 | T1 territory                       |
| ETF       | 1.44 | 59.2 | Approaching T2; n=47 below n=100 charter floor |
| FOREX     | 0.27 | 41.7 | Post-#687/#692 kills (long-run still depressed by legacy trades) |
| BOND      | 0.66 | 54.5 | Sub-1 PF; n=18 below charter floor |
| SPORTS    | None | 0.0  | Scoped out — PR #905 targeting this |
| FUTURES   | None | 0.0  | No recent trades                   |

---

## 2. Per-Asset PF/WR — 24h / 7d / 30d Windows

Reference "now" = most recent closed pick: `2026-05-12T02:26:52Z`  
Computed from `picks.recent_closed` (n=3402 parseable).

| Class     | Window | n    | WR%   | PF        | Delta vs Baseline                |
|-----------|--------|------|-------|-----------|----------------------------------|
| CRYPTO    | 24h    | 167  | 50.3% | 2.09      | Baseline 3.54 → **−1.45** (regime/luck; 7d/30d stable) |
| CRYPTO    | 7d     | 982  | 44.2% | 1.42      | Baseline 1.33 → **+0.09** ↑     |
| CRYPTO    | 30d    | 1879 | 45.9% | 1.40      | Baseline 1.33 → **+0.07** ↑     |
| EQUITY    | 24h    | 13   | 7.7%  | 2.66      | Small n; 1 large win drives PF   |
| EQUITY    | 7d     | 31   | 41.9% | 5.29      | Baseline 0.87 → **+4.42** ↑↑ MAJOR RECOVERY |
| EQUITY    | 30d    | 134  | 57.5% | 3.06      | Baseline 2.18 → **+0.88** ↑     |
| FOREX     | 24h    | 13   | 61.5% | 3.10      | Small n=13; encouraging signal   |
| FOREX     | 7d     | 79   | 24.1% | 0.99      | Baseline 0.14 → **+0.85** ↑↑ near break-even |
| FOREX     | 30d    | 574  | 41.5% | 0.63      | Baseline 0.97 → **−0.34** (legacy trades dragging) |
| COMMODITY | 24h    | 2    | 100%  | extreme   | n=2, ignore                      |
| COMMODITY | 7d     | 17   | 94.1% | 39.96     | n=17 caveat; trend T1-grade      |
| COMMODITY | 30d    | 103  | 56.3% | 6.44      | **T1 confirmed** on n=103        |
| ETF       | 24h    | 3    | 100%  | extreme   | n=3                              |
| ETF       | 7d     | 13   | 100%  | extreme   | n=13 caveat                      |
| ETF       | 30d    | 47   | 83.0% | 6.44      | T1-grade; n=47 below charter floor |
| BOND      | 24h/7d/30d | 0 | — | —       | No new trades in any window      |

### Key Observations

**EQUITY major recovery confirmed.** `goldmine_6x_consensus` kill (PR #692, merged today) is already visible: 7d PF 0.87→5.29. n=31 is modest — monitor at n≥50 for persistence. 30d PF at 3.06 is T1 territory.

**FOREX 7d near break-even.** PR #687 (JPY-cross BUY fix) + PR #692 kills (forex_carry_momentum) show early effect: 7d PF 0.14→0.99. 30d still 0.63 — expected as pre-fix legacy trades age out. 24h PF 3.10 on n=13 is encouraging but not statistically robust.

**CRYPTO 24h softened.** 3.54→2.09 (−1.45). 7d/30d both slightly up. The 24h drop may reflect regime shift or the quan_engine HYPEUSDT block (#694) landing — net CRYPTO pick mix now cleaner. Monitor at next hourly.

**Issue #693 EQUITY monitor:** Post-PR #692, 7d PF at 5.29 (was 0.87). Condition #3 in #693 ("If EQUITY 14d returns to PF ≥ 1.5 within 7 days, kill was sufficient") appears to be met at the 7d level. Recommend closing #693 at next audit if 14d PF ≥ 1.5 confirmed.

---

## 3. Mutation Analysis — New Kill Candidates

**Command run:** `python tools/mutation_analysis.py --json` (2026-05-12T04:15Z)

### No strategies meet auto-kill criteria (PF<0.5 AND n>=20) — clean

All strategies are PF≥0.5 on overall sample. No additions to `BLOCKED_ASSET_STRATEGY_PAIRS` or `BLOCKED_STRATEGY_SYMBOL_PAIRS` this hour.

### Watch List (PF 0.5–1.0, n≥20)

| Strategy                      | n   | WR%  | PF   | Action |
|-------------------------------|-----|------|------|--------|
| `forex_rsi2_mean_reversion`   | 666 | 43.2%| 0.91 | WATCH — was flagged in #686 (7d WR 10.9%); long-run improving post-kills. Monitor 7d window. |
| `luxalgo_confluence`          | 351 | 43.0%| 0.89 | WATCH — sub-1 PF on large n. Direction-split mutation recommended next cycle. |
| `crypto_rsi_whaleconfirmed_v1`|  40 | 35.0%| 0.66 | WATCH — WR below 40%, PF declining. Escalate to mutation if 7d WR<35% on n≥20. |
| `macd_rsi_confluence`         |  34 | 32.4%| 0.72 | WATCH — low WR, moderate n. |
| `cta_golden_cross_200`        |  26 | 42.3%| 0.64 | WATCH — small n, below break-even. |
| `ema_momentum_m006`           |  25 | 44.0%| 0.87 | WATCH — near break-even. |

### Direction-Split Signals (from mutation analysis)

| Strategy                     | LONG WR      | SHORT WR     | Spread | Recommendation |
|------------------------------|--------------|--------------|--------|----------------|
| `ig_contrarian_sentiment`    | 16.9% (n=177)| 62.5% (n=48) | 46pp   | **Post to #686 for 3-AI consensus** before LONG-direction kill. Run mutation+inverse+symbol-rotation per MUTATION_THREE_AXIS_PROTOCOL.md first. |
| `quan_engine_swing`          | 26.0% (n=104)| 60.0% (n=5)  | 34pp   | SHORT n=5 too small; hold. |
| `myfxbook_retail_contrarian` | 13.1% (n=122)| 46.2% (n=13) | 33pp   | LONG kill candidate; SHORT n=13 too small; hold. |
| `cta_cross_asset_tsmom`      | 26.7% (n=75) | 48.1% (n=133)| 21pp   | Below 35pp threshold; WATCH. |

### Symbol-Level (quan_engine)

`HYPEUSDT` blocked via PR #694 (merged today). Remaining zero-WR candidates:

| Symbol  | n  | WR% | Verdict |
|---------|----|-----|---------|
| `UUSDT` | 34 | 0%  | **Meets n≥20 threshold** — recommend `BLOCKED_STRATEGY_SYMBOL_PAIRS` addition in next PR, with 3-AI consensus. |
| `ESPUSDT` | 5 | 0% | Below n=20 threshold; WATCH. |
| `TREEUSDT` | ~5 | 0% | Below n=20 threshold; WATCH. |

---

## 4. PR Triage Actions

### Merged This Hour

_None._ PR #905 had a merge conflict (see below).

### Held — Merge Conflict

| PR  | Title | Reason |
|-----|-------|--------|
| #905 | feat(audit): exclude SPORTS from asset_class_health (PR-A) | **MERGE CONFLICT** — base drifted after today's 8 merges. `update_pull_request_branch` returned 422 (conflict). Per CLAUDE.md, cannot manually rebase peer PR. CI was 3/3 green (audit✓ scan✓ drift✓), no REQUEST_CHANGES. Author must rebase. |

### Held — CI In Progress

| PR  | Title | Status |
|-----|-------|--------|
| #906 | feat(risk-policy): cap quan_engine CRYPTO volume to 12% (PR-H) | 5/5 CI checks in_progress — HOLD until all green (audit, scan, test 3.11, test 3.12, gate) |
| #907 | test(blacklist): verify kimi_signal_tracking exec-gate enforcement (PR-B) | 3/3 CI checks in_progress — HOLD (scan, test 3.11, test 3.12) |

### HOLD Set (Plan v2.1 family)

#660, #658, #681, #661 — none present in current open PR list. Confirmed closed before this session.

### Author-Rebase Check PRs (#669 #676 #608 #665 #644 #597 #615 #655)

None present in current open PR list. Confirmed closed before this session.

---

## 5. Issue Gate Checks

**Issue #685 (resolver-rescope DONE):** No PRs claiming "widen re-resolve scope" detected this hour. Gate clean.

**Issue #686 (FOREX/EQUITY attribution):** Comment posted with `ig_contrarian_sentiment` LONG-direction finding (n=177, WR=16.9%) and `UUSDT` symbol block recommendation. Awaiting 3-AI consensus.

**Issue #693 (EQUITY monitor):** 7d PF 0.87→5.29 post-PR #692. Likely ready to close pending 14d window confirmation at next audit.

---

## 6. Goal #1 Tier Assessment (post-today's 8 PRs + this audit)

| Class     | PF (30d) | WR (30d) | Tier         | Notes |
|-----------|----------|----------|--------------|-------|
| CRYPTO    | 1.40     | 45.9%    | Sub-T2       | quan_engine cap (#906 pending) targets PF lift |
| EQUITY    | 3.06     | 57.5%    | **T1 candidate** | n=134 above floor; monitor 14d |
| COMMODITY | 6.44     | 56.3%    | **T1**       | n=103 at charter floor |
| ETF       | 6.44     | 83.0%    | T1-grade     | n=47 below n=100 charter floor |
| FOREX     | 0.63     | 41.5%    | Sub-floor    | Mutation protocol per #686 active |
| BOND      | 0.66     | 54.5%    | Sub-T2       | n=18 below charter floor |

**Headline:** 3 classes at or near T1 (EQUITY, COMMODITY, ETF). CRYPTO approaching T2. FOREX mutation protocol active. No new kills needed this hour.

---

## Refs

- Issues: #685 (resolver DONE), #686 (per-asset attribution), #693 (EQUITY monitor)
- PRs merged today (pre-session): #684 #674 #673 #664 #683 #687 #692 #694
- PRs merged this hour: **none** (PR #905 blocked by conflict)
- `tools/mutation_analysis.py` — run 2026-05-12T04:15Z
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md`, `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`
- `alpha_engine/outcome_resolver.py:115-126` (PNL_WIN_THRESHOLD_BY_CLASS — confirmed done per #685)
