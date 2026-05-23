# Hourly Audit — 2026-05-17 08Z

**Auditor:** Claude Sonnet 4.6 (automated hourly check)  
**Audit time:** 2026-05-17T08:10Z  
**Dashboard snapshot:** 2026-05-17T06:19:07Z (~1h51m old; next cron expected ~07:19Z, may be delayed)  
**Context issues read:** #685 (resolver-rescope DONE), #686 (per-asset live attribution), #693 (EQUITY 7d/14d/30d monitor — closed completed)

---

## 1. Dashboard Refresh Status

Dashboard generated at `2026-05-17T06:19:07Z`. Approximately 2 hours old at audit time. The hourly `[skip ci]` cron was expected at ~07:19Z but dashboard has not refreshed since 06:19Z — possible cron delay. Numbers below are from the 06:19Z snapshot and may lag by up to 2 hours.

---

## 2. Per-Asset Metrics — asset_class_health (Full Dataset, Authoritative Post-Resolver-v2)

| Class     | PF    | WR%   | n     | Status             | vs Baseline             |
|-----------|-------|-------|-------|--------------------|-------------------------|
| CRYPTO    | 1.33  | 47.2% | 7748  | stable             | ≈ (baseline 1.33)       |
| EQUITY    | 1.65  | 53.2% | 393   | stable             | ↑ (baseline 1.41)       |
| FOREX     | 0.85  | 57.8% | 251   | watch              | ↑↑ (baseline 0.27 pre-#687) |
| COMMODITY | 7.71  | 85.5% | 228   | stable             | ↑↑ (baseline 1.78)      |
| ETF       | 2.25  | 66.7% | 75    | candidate (n→100)  | ↑ (baseline 1.24)       |
| BOND      | 0.66  | 54.5% | 11    | thin_sample        | ↓ (baseline PF 1.72)    |
| FUTURES   | —     | 100%  | 2     | insufficient_data  | n/a                     |

**Notes:**
- FOREX full-dataset PF=0.85 is already a massive improvement over pre-PR-#687 PF=0.27. The `watch` status reflects that the full dataset still contains historical pre-kill contamination.
- COMMODITY PF=7.71 is anomalously high — likely driven by `multi_asset_copytrader CT=F 57.1% WR / n=175` concentration.
- BOND PF=0.66 on n=11 is below charter minimum (n=100 for Tier assessment); do not act.

---

## 3. Windowed Metrics — recent_closed n=3500 (computed from closed_at timestamps)

### CRYPTO
| Window | n    | WR%  | PF   | Sum PnL% | Delta vs Baseline   |
|--------|------|------|------|----------|---------------------|
| 24h    | 119  | 44.5 | 1.12 | +8.26    | ↓↓ (baseline 3.54)  |
| 7d     | 845  | 43.2 | 1.14 | +106.08  | ↓ (baseline 1.33)   |
| 30d    | 2901 | 45.6 | 1.28 | +663.39  | ≈ (baseline 1.33)   |

**Assessment:** CRYPTO 24h PF dropped from baseline 3.54 → 1.12 (n=119, meaningful sample). Regime shift or `quan_engine` residual drag post-HYPEUSDT block (PR #694). 30d stable. Do not destabilize (issue #686 §CRYPTO).

### EQUITY
| Window | n  | WR%  | PF   | Sum PnL% | Delta vs Baseline   |
|--------|----|------|------|----------|---------------------|
| 24h    | 0  | —    | —    | —        | n/a                 |
| 7d     | 25 | 16.0 | 0.62 | -13.88   | ↓↓ (baseline 0.87)  |
| 30d    | 98 | 54.1 | 2.47 | +179.20  | ↑↑ (baseline 2.18)  |

**🚨 P1 — EQUITY 7d continued deterioration.** Issue #693 predicted partial recovery post-PR-#692 (goldmine_6x kill). Current 7d PF=0.62 is worse than the 0.87 at issue-open time. Strategy breakdown (7d):

| Strategy                              | n | WR%  | PF   | Sum PnL% |
|---------------------------------------|---|------|------|----------|
| stocksunify2_adversarial_trend_v2     | 8 | 0%   | inf  | 0.00%    |
| macd-hidden-div-scout                 | 2 | 0%   | 0.00 | -8.14%   |
| price-accel-scout                     | 2 | 0%   | 0.00 | -8.45%   |
| adx-trend-scout                       | 2 | 50%  | 0.47 | -3.05%   |
| gap-and-go-stocks                     | 2 | 50%  | 1.38 | +2.60%   |
| moderate consensus                    | 2 | 50%  | 0.32 | -0.41%   |

`stocksunify2_adversarial_trend_v2` has n=8 with sum=0.00% and WR=0% — all trades resolved at $0 pnl (unresolved/open outcomes leaking into closed_at window). `price-accel-scout` and `macd-hidden-div-scout` each at 0% WR account for -16.59% sum pnl (the bulk of 7d loss). Neither meets n>=20 threshold for kill protocol yet; monitor at next hourly.

### FOREX
| Window | n  | WR%  | PF   | Sum PnL% | Delta vs Baseline          |
|--------|----|------|------|----------|----------------------------|
| 24h    | 7  | 42.9 | 1.22 | +1.18    | n/a (small)                |
| 7d     | 18 | 27.8 | 1.60 | +3.65    | ↑↑↑ (baseline 0.14 pre-#687) |
| 30d    | 48 | 33.3 | 2.30 | +16.47   | ↑↑ (baseline 0.97)         |

**✅ FOREX recovery confirmed.** `forex_carry_momentum` (killed PR #692) absent from 7d. `forex_rsi2_mean_reversion` volume collapsed (n=1 in 7d vs n=52 7d at issue-open). PF=1.60 on 7d vs 0.14 — PRs #687 + #692 working. WR 27.8% reflects PF powered by large win sizes relative to losses (positive skew), not high win count. Acceptable post-kill regime.

### COMMODITY
| Window | n  | WR%  | PF   | Sum PnL% | Delta vs Baseline   |
|--------|----|------|------|----------|---------------------|
| 24h    | 0  | —    | —    | —        | n/a                 |
| 7d     | 27 | 29.6 | 0.64 | -24.33   | ↓↓ (long-run 7.71)  |
| 30d    | 65 | 56.9 | 1.97 | +88.85   | ≈ (baseline 1.78)   |

**🚨 NEW FINDING — COMMODITY 7d regression.** 7d PF=0.64, WR=29.6%, n=27 is sub-breakeven. Long-run PF=7.71 suggests this is recent. Mutation analysis reveals `cta_replicator` symbol drag:
- `NG=F`: 0.0% WR, n=24 — **meets n>=20 threshold for kill-protocol consideration**
- `ZC=F`: 0.0% WR, n=8 — below threshold, watch
- `CL=F`: 19.1% WR, n=47 — sub-threshold WR, high-n
This is not documented in issue #686. **Post to issue #686 as a comment.**

### ETF
| Window | n  | WR%  | PF   | Sum PnL% | Delta             |
|--------|----|------|------|----------|-------------------|
| 24h    | 0  | —    | —    | —        | n/a               |
| 7d     | 13 | 46.2 | 0.66 | -7.14    | 7d softness       |
| 30d    | 48 | 70.8 | 2.48 | +50.56   | strong 30d        |

7d softness (n=13) is too small for action. 30d strong at PF=2.48.

### BOND
No entries in recent_closed n=3500 (all BOND activity predates the 3500-cap window). Full-dataset n=11 at PF=0.66 — thin_sample, no action.

---

## 4. PR Triage

`gh pr list --state open` result: **1 open PR** (#1143 only).

| PR    | Title                                          | Mergeable     | CI          | Reviews | Action        |
|-------|------------------------------------------------|---------------|-------------|---------|---------------|
| #1143 | docs(updates): CRYPTO audit de-contamination   | DIRTY (conflicts) | No checks | None | HOLD — conflicts |

**HOLD set (#660, #658, #681, #661) status:**
- #660: Already merged 2026-05-03 (was Plan v2.1 family — contains WINNER_FILTER claims; cannot unmerge)
- #658: Closed without merge 2026-05-03 ✅
- #681: Closed without merge 2026-05-03 ✅
- #661: Already merged 2026-05-03 (infrastructure modules — Wire-Up Rule concern noted in comments but merged by owner)

**AUTHOR REBASES (#669, #676, #608, #665, #644, #597, #615, #655):** All already closed/merged prior to this audit window. No action needed.

**Merged this hour:** 0 (no mergeable PRs available)

---

## 5. Mutation Analysis — New Kill Candidates

`python tools/mutation_analysis.py --json` run at 08:10Z:

- **PF<0.5 + n>=20 kill candidates: 0 new** (no new emergent kills meeting the threshold)
- **WR<35% + PF<1.0 + n>=20 watch:** `[FOREX] unknown` n=21, WR=33.3%, PF=0.86 — marginal, below kill threshold

**Direction-flip candidates (existing, not new — for reference):**
- `ig_contrarian_sentiment`: SHORT 61.4% / LONG 16.8%, spread 45pp — long-side drag
- `myfxbook_retail_contrarian`: SHORT 50% / LONG 13.8%, spread 36pp
- `forex_rsi2_mean_reversion`: SHORT 34.8% / LONG 7.4%, spread 27pp — kill pending from issue #686

**Symbol-level candidates (cta_replicator):**
- `NG=F` (Natural Gas Futures): WR=0%, n=24 — **meets BLOCKED_STRATEGY_SYMBOL_PAIRS threshold** (n>=20, WR<35%). Propose add `("cta_replicator","NG=F")` to `BLOCKED_STRATEGY_SYMBOL_PAIRS`. Needs 3-AI consensus before action.
- `ZC=F` (Corn Futures): WR=0%, n=8 — below threshold, monitor.

---

## 6. Issue #686 Comment Required — COMMODITY 7d + cta_replicator NG=F

New evidence for issue #686: COMMODITY 7d PF=0.64 driven by `cta_replicator` symbol drag (NG=F 0% WR n=24, CL=F 19.1% WR n=47). This is not covered by the existing forex-focused attribution in issue #686. Recommend posting.

---

## 7. Summary Table vs Documented Baselines

| Class     | Window | Baseline PF | Current PF | Delta   | Flag |
|-----------|--------|-------------|------------|---------|------|
| CRYPTO    | 24h    | 3.54        | 1.12       | -2.42   | 🟡   |
| CRYPTO    | 7d     | 1.33        | 1.14       | -0.19   | 🟡   |
| CRYPTO    | 30d    | 1.33        | 1.28       | -0.05   | ✅   |
| EQUITY    | 7d     | 0.87        | 0.62       | -0.25   | 🔴   |
| EQUITY    | 30d    | 1.41-2.18   | 2.47       | +0.29   | ✅   |
| FOREX     | 7d     | 0.14        | 1.60       | +1.46   | ✅   |
| FOREX     | 30d    | 0.97        | 2.30       | +1.33   | ✅   |
| COMMODITY | 7d     | n/a         | 0.64       | new     | 🔴   |
| COMMODITY | 30d    | n/a         | 1.97       | ok      | ✅   |
| ETF       | 7d     | n/a         | 0.66       | soft    | 🟡   |
| ETF       | 30d    | n/a         | 2.48       | strong  | ✅   |

---

## 8. Actions Taken This Hour

1. **Merged PRs:** 0
2. **New findings:** 2
   - EQUITY 7d PF=0.62 (continued deterioration below issue #693 baseline of 0.87; `price-accel-scout` + `macd-hidden-div-scout` the current culprits)
   - COMMODITY 7d PF=0.64 regression — `cta_replicator` NG=F (0% WR, n=24) + CL=F (19.1% WR, n=47) are the drivers
3. **Kill candidates posted to issue #686:** Pending (see below — posting COMMODITY/cta_replicator finding)
4. **No strategy kills executed** (no 3-AI consensus; NG=F requires mutation-before-kill per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`)

---

## 9. Next Hour Priorities

1. Monitor EQUITY 7d — if `price-accel-scout` or `macd-hidden-div-scout` reach n>=20, trigger mutation protocol
2. Post COMMODITY/NG=F finding to issue #686 (see §6)
3. Watch CRYPTO 24h PF — if stays <1.5 for another hourly check, investigate `quan_engine` post-HYPEUSDT-block residual
4. PR #1143 author needs to rebase before merge review can proceed
5. `forex_rsi2_mean_reversion` LONG-side kill (issue #686 P1) still pending — needs mutation analysis export per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`

---

*Generated by Claude Sonnet 4.6 | Branch: audit/hourly-08z | Refs: #685 #686 #693 | dashboard_data.json @ 2026-05-17T06:19:07Z*
