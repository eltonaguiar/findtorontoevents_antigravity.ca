# Deep Dive — ETF (2026-05-31)

Canonical data sources (read 2026-05-31):
- `audit_dashboard/data/pf_registry.json` (generated 2026-05-30T23:05:43Z)
- `audit_dashboard/data/money_ready_verdict.json`
- `audit_dashboard/data/dashboard_data.json` (`asset_class_health.ETF`)
- `audit_dashboard/data/pick_summary_stats_{2w,48h}.json`

NOTE on n discrepancy: CLAUDE.md cites ETF INSUFF-N at PF 11.99 / WR 50% / n=2 (2026-05-24/25 snapshot). The current `pf_registry.by_asset_class_policy_clean_net` row shows **n=4 / WR 50% / PF 0.476 / MDD 6.16%**, i.e. the cohort grew by 2 net-new closes and PF collapsed from a degenerate-positive figure to a sub-1 FAIL. All numbers below are sourced from the 2026-05-30T23:05:43Z `pf_registry.json` unless noted.

---

## Current State (n, WR, PF, MDD, expectancy, recency)

| View | n | wins | losses | WR | PF | Total PnL % | MDD |
|---|---|---|---|---|---|---|---|
| `by_asset_class_raw` | 6 | 2 | 3 (+1 unresolved) | 33.33% | 0.295 | -7.28% | n/a |
| `by_asset_class` (flicker-deduped) | 4 | 2 | 2 | 50.00% | 0.495 | -3.11% | n/a |
| `by_asset_class_policy_clean` | 4 | 2 | 2 | 50.00% | 0.495 | -3.11% | n/a |
| **`by_asset_class_policy_clean_net`** (verdict-grade) | **4** | **2** | **2** | **50.00%** | **0.476** | **-3.27%** | **6.16%** |

Expectancy per trade (policy_clean_net) = (-3.27% / 4) = **-0.82% per closed pick** (net of slippage).

Recency: all 4 closed picks fall within **2026-05-25 → 2026-05-30** (6-day window). No `pick_summary_stats_{2w,48h}` row exists for ETF (asset class returned `None`) — confirming **n is too sparse to populate the recency panels**. The class is simultaneously **FAIL** (PF<1, expectancy<0) **and INSUFF-N** (n=4 << the n>=30 floor for any statistical claim, n>=100 for "proven").

Verdict: **DOUBLE-FAIL** — sub-1 PF on a tiny, brand-new cohort. Cannot be sized up. Cannot be killed off statistically (n too small to reject H0). Sits in the "investigate before kill" pen per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`.

---

## Per-Source Autopsy (top sources by volume; WR/PF each)

The `pf_registry` rolls ETF up by `strategy` (proxy for source-system here — each ETF strategy has a 1:1 source-system mapping in this cohort). Total volume is so low that strategy and source merge.

| Source-System / Strategy | n | wins | losses | WR | PF | Net PnL % | Verdict |
|---|---|---|---|---|---|---|---|
| `etf_scanner` | 2 | 0 | 2 | **0%** | **0.0** | **-6.25%** | **PRIMARY FAILURE** — losses are USO (-2.0%) and XLE (-4.17%), both energy-sector ETFs closing same-week. Single-strategy concentration = 50% of cohort, and **100% of losses**. |
| `etf_rsi2_pullback` | 1 | 1 | 0 | 100% | undefined (no losses) | +1.77% | XLI win on 2026-05-30. n=1 — meaningless. |
| `regime_mild_bull` | 1 | 1 | 0 | 100% | undefined (no losses) | +1.20% | SPY win on 2026-05-28. n=1 — meaningless. |

**Concentration finding (per `feedback-concentration-strategy-not-engine`):** measuring at the **strategy** level (correct axis): `etf_scanner` is 2/4 = **50% of cohort by count, 100% of losses by sign**. Single-strategy concentration HHI ≈ (0.5² + 0.25² + 0.25²) = **0.375**, well above the 0.30 red-line. Combine with **100% of losses concentrated in energy-ETF tickers (USO, XLE) emitted by a single strategy on 2026-05-25 / 2026-05-27**, and this is functionally a **one-strategy, one-sector loss event** wearing a "diversified ETF book" label.

By symbol:
- **XLE** (Energy Select Sector SPDR) — n=1, loss -4.17% (the largest single loss in the cohort, 67% of gross loss).
- **USO** (US Oil Fund) — n=1, loss -2.00%.
- **XLI** (Industrial SPDR) — n=1, win +1.81% (rsi2 pullback).
- **SPY** — n=1, win +1.24% (regime_mild_bull).

The two winners are broad/sector-rotation plays; the two losers are both **WTI-correlated energy ETFs** picked by the same scanner during a sharp oil drawdown 2026-05-25 → 2026-05-27. **This is one trade economically, not two.**

---

## Strategy Breakdown (per-strategy WR/PF/single_source_pct; flag concentration)

| Strategy | n | WR | PF | single_strategy_share_of_cohort | flag |
|---|---|---|---|---|---|
| `etf_scanner` | 2 | 0% | 0.0 | 50.0% | **HHI=0.375 + 100% energy concentration in losses → KILL-CANDIDATE pending mutate-axis review** |
| `etf_rsi2_pullback` | 1 | 100% | n/a | 25.0% | INSUFF-N — provisional |
| `regime_mild_bull` | 1 | 100% | n/a | 25.0% | INSUFF-N — provisional |

Per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` — `etf_scanner` warrants a **mutate-before-kill** pass on the three axes (entry filter, sizing/timing, exit) before being added to `BLOCKED_SOURCE_SYSTEMS`. Specifically: was the energy-ETF emission gated by any oil-regime check? If no, **add a WTI 20D-momentum or 50D-trend gate as Axis-1 mutation**.

---

## What Is Failing (root causes — named)

1. **`etf_scanner` has no sector-regime gate.** It emitted XLE + USO into a falling-oil regime on 2026-05-25 and 2026-05-27 with no apparent override. Both closed losses, both energy. Root cause = missing macro/sector filter in the strategy itself.
2. **No diversification floor on the ETF strategy book.** Across n=4, 50% of picks came from one strategy and 50% of picks were correlated energy plays. A class-level "max 30% single-strategy share" rule would have blocked the second `etf_scanner` emission.
3. **Cohort age = 6 days.** ETF is a **brand-new asset class** in `pf_registry`. The CLAUDE.md "PF 11.99 / n=2" snapshot from 2026-05-24/25 is degenerate (one outlier win, no losses yet). The "new" PF 0.476 reflects the first losses landing — this is normal "regression-from-degenerate" not necessarily strategy collapse. **The right call is suspend-and-investigate, not kill.**
4. **No recency panels.** `pick_summary_stats_2w.json` and `pick_summary_stats_48h.json` both return `None` for ETF, so the 14d/48h sanity checks mandated by CLAUDE.md (`never size up without verifying the 14d/48h panels first`) are **structurally unavailable** for this class. Fix: ensure the recency aggregator emits an explicit `INSUFF_N` row instead of dropping the key.
5. **Possible mislabel risk.** XLE/USO/SPY/XLI sit on the equity/ETF boundary — confirm `asset_class='ETF'` is not being applied to single-equity tickers that should be `EQUITY`. (Quick check: all 4 tickers ARE legitimate ETFs, so no mislabel here; flagged for future audits.)

---

## External Replication Options

Per CLAUDE.md Goal #1 process — when a class is failing/insufficient, surface external products that already deliver the desired exposure, so we can either benchmark against them or hand the exposure off.

| External vehicle | Exposure | Why relevant for ETF book |
|---|---|---|
| **DBMF** (iMGP DBi Managed Futures) | Trend-following across equity, rates, FX, commodity futures | Reference Tier-1 for "diversified macro ETF" performance. Use as a beta-replication benchmark for any in-house multi-sector ETF strategy. |
| **KMLM** (KFA Mount Lucas Managed Futures) | Equal-weight CTA-style trend (commodity-heavy) | Direct comparable for `etf_scanner` energy/commodity picks — if KMLM is flat/up and our scanner lost on USO+XLE same week, the scanner has negative alpha vs the obvious replacement. |
| **MTUM** (iShares MSCI USA Momentum) | Single-factor momentum, equity ETF | Benchmark for `etf_rsi2_pullback` and `regime_mild_bull` — if MTUM is up X% in the holding period and our strategy returns 1.2-1.8%, gross-of-fee alpha is the test, not absolute return. |
| **QMOM** (Alpha Architect US Quantitative Momentum) | Concentrated momentum, top-decile | Same benchmark, more aggressive variant. |
| **PIMCO BOND** (PTTRX / BOND ETF) | Active bond | Cross-class — only relevant once ETF book includes fixed-income wrappers. |
| **Hyperliquid HLP** (vault) | Market-making yield | Irrelevant for ETF, listed in CLAUDE.md template — skip. |
| **MyFXBook signal pools** | FX signal benchmarking | Cross-class — skip for ETF. |
| **Composer.trade symphonies** | Rules-based ETF rotation strategies | **Most direct comparable** for `regime_mild_bull` — Composer has dozens of public regime-rotation ETF symphonies with multi-year live track records. Pull a top-10 list and benchmark our regime strategy in-sample. |
| **Allocate Smartly model portfolios** | Subscription service tracking 60+ TAA ETF strategies | Same — `regime_mild_bull` is a TAA strategy; benchmark vs the AllocateSmartly leaderboard before claiming edge. |

Action: open `reports/etf_external_benchmark_<date>.md` once we have a 30-trade in-house cohort, comparing realized PnL vs DBMF, KMLM, MTUM same-window.

---

## 30 / 60 / 90 Day Rescue Plan

**30 days (by 2026-06-30):**
- Freeze new `etf_scanner` emissions involving energy-sector ETFs (XLE, XOP, USO, BNO, UNG, OIH) until a WTI-regime gate ships. (Code edit: `alpha_engine/etf_scanner.py` — add 50D SMA filter on `CL=F`.)
- Add an explicit ETF row to `pick_summary_stats_2w.json` and `pick_summary_stats_48h.json` generator so INSUFF_N is visible, not silently `None`.
- Apply the mutate-three-axis protocol to `etf_scanner`: (a) entry — add macro-regime gate; (b) sizing — cap 25% of ETF book per strategy; (c) exit — add 2× ATR stop hard floor.
- Target end-state: n>=15 closed ETF picks, with no single strategy >40% share.

**60 days (by 2026-07-31):**
- Reach n>=50 closed ETF picks across **>=4 distinct strategies**, with `etf_scanner` reduced to <=30% share.
- Run first external benchmark report (`reports/etf_external_benchmark_*.md`) — compare cohort PnL vs DBMF / KMLM / MTUM same-window. Net-of-cost alpha must be >=0 to continue.
- Publish per-strategy WR/PF on `audit_dashboard/template.html` ETF panel.

**90 days (by 2026-08-31):**
- Reach n>=100 closed ETF picks → eligible for "proven" labeling per CLAUDE.md rule.
- Target Tier 2 minimum: **PF>=1.5, WR>=50%, MDD<=20%, single-strategy HHI<=0.30**.
- If not met: demote to opt-in/research-only and route ETF exposure to one of the DBMF/MTUM/Composer external vehicles above.

---

## Risk Register

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | `etf_scanner` continues to emit energy ETFs into falling-oil regimes | High (no gate exists) | High (largest losses in cohort) | Ship WTI-regime gate in 30d window |
| R2 | n stays <30 — never reaches statistical significance | Medium | Medium | Loosen non-loss-driving filters; widen universe; or accept research-only label |
| R3 | The two winners (XLI, SPY) are also degenerate — small n inflates apparent edge | High | Medium | Re-evaluate after n>=30; do not promote `etf_rsi2_pullback` or `regime_mild_bull` until then |
| R4 | Cross-class mislabel: an EQUITY pick gets tagged ETF and contaminates the cohort | Low (current 4 tickers verified ETF) | Medium | Add a `tools/audit_asset_class_labels.py` sanity check |
| R5 | External replication (DBMF/MTUM) outperforms in-house cohort net-of-cost | Medium-High | High (Goal #1 invalidated for class) | If confirmed at 90d, route exposure externally and close the class |
| R6 | Concentration gate still not enforced before DSR/SPA (open P0 from CLAUDE.md) — ETF could falsely PASS at small n if it ever pops PF>2 | Medium | High | Honor the existing P0; do not rely on DSR/SPA until the concentration gate sits ahead of it |
| R7 | `etf_scanner` is killed prematurely without mutate-axis review | Medium | Medium | Run `tools/mutation_analysis.py` before any addition to `BLOCKED_SOURCE_SYSTEMS` |

---

## Acceptance Criteria

The ETF class graduates from "deep-dive investigation" to "production tier-eligible" when **all** of these hold simultaneously, sourced from `pf_registry.by_asset_class_policy_clean_net` and `by_asset_class_strategy_policy_clean_net`:

1. **n>=100** closed, policy-clean, net-of-slippage picks.
2. **PF>=1.5** (Tier 2 floor).
3. **WR>=50%**.
4. **MDD<=20%** cumulative-peak-to-trough.
5. **Single-strategy HHI<=0.30** measured per `feedback-concentration-strategy-not-engine`.
6. **>=4 distinct strategies** each contributing >=5% of cohort volume.
7. **Net-of-cost alpha >= 0** vs DBMF + MTUM benchmark over the same 90d window.
8. **14d and 48h `pick_summary_stats` panels populated** (no `None`) and consistent with the long-run figures.
9. **No active P0** from the concentration-gate-before-DSR/SPA issue affecting ETF rows.

Falling Tier 1 (Renaissance) target — separate track once Tier 2 holds for 60 consecutive days: PF>=2.0, WR>=55%, MDD<=10%.

---

## Hard Rule (Until Met)

**Until the Acceptance Criteria above hold, the ETF class is on the following hard rule:**

> **No paper-money sizing >=1% NAV and no real-money allocation may be applied to any ETF pick from any strategy.** ETF emissions remain logged + tracked but are **not** eligible for Smart Picks / High Conviction / Money Ready promotion. Specifically: `etf_scanner` is suspended from emitting any energy-sector ETF (XLE/XOP/USO/BNO/UNG/OIH) until the WTI-regime gate ships. `etf_rsi2_pullback` and `regime_mild_bull` continue to emit but are tagged `INSUFF_N — research only` on the dashboard until n>=30 per-strategy.

This rule supersedes any automated tier promotion until either (a) the acceptance criteria are met or (b) a follow-up `reports/deep_dive_ETF_*.md` formally rescinds it with new evidence.

---

Sources (all read 2026-05-31):
- `audit_dashboard/data/pf_registry.json` @ 2026-05-30T23:05:43Z
- `audit_dashboard/data/money_ready_verdict.json` (ETF row absent — INSUFF-N)
- `audit_dashboard/data/dashboard_data.json` (`asset_class_health.ETF` absent in current snapshot)
- `audit_dashboard/data/pick_summary_stats_2w.json` (ETF key absent)
- `audit_dashboard/data/pick_summary_stats_48h.json` (ETF key absent)
- `CLAUDE.md` (Goal #1, mutation-protocol, concentration rules)
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md`
- `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`
