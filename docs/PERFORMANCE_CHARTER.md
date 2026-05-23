# Performance Charter

**Version:** 1.0
**Last updated:** 2026-04-28
**Status:** CANONICAL — single source of truth for all tier thresholds, risk caps, and KPI definitions.

This charter is referenced by `CLAUDE.md` MAJOR GOAL #1 and the UEPS project (`updates/long_term_value_project_2026-04-27/`). Any strategy/pick promotion or demotion must cite this file.

## §1 Purpose

This document is the canonical KPI / risk-cap / tier-threshold authority for the entire repo. Strategies are promoted to live capital only when they clear the thresholds defined here, validated via walk-forward backtest. Demotions require the mutation-before-kill protocol (§8).

## §2 Tier framework (universal across all asset classes)

| Tier | PF | WR | MaxDD | n |
|---|---|---|---|---|
| **Tier 1 (Renaissance-grade, long-run target)** | ≥ 2.0 | ≥ 55% | ≤ 10% | ≥ 200 |
| **Tier 2 (sized-up live capital floor)** | ≥ 1.5 | ≥ 50% | ≤ 20% | ≥ 100 |
| **Tier 3 (paper-trading floor)** | ≥ 1.2 | ≥ 45% | ≤ 25% | ≥ 100 |
| **Below Tier 3** | < 1.2 OR WR < 45% OR MaxDD > 25% OR n < 100 | | | |

Below-Tier-3 strategies are paper-only, surveillance, and candidate for the mutation protocol (§8) before any kill.

**All claims require n ≥ 100 closed picks (post-noise-filter).** A strategy with n < 100 is "Building" — track-record-developing — not classified.

## §3 Long-term value-specific gates

In addition to §2 thresholds, long-term value picks must clear:

- **3y CAGR ≥ 10%** (Tier 2) / **≥ 15%** (Tier 1)
- **Sharpe ratio ≥ 0.8** (Tier 2) / **≥ 1.2** (Tier 1)
- **Max position size:** 5% of portfolio per long-term hold
- **Min holding period before close:** 90 days (regret-prevention floor unless thesis-break fires)

Long-term picks use `thesis_resolver.py` — they do NOT close on price drawdown alone.

## §4 Swing-trading-specific gates

Same Tier 1/2 PF/WR/MDD as §2. Plus:

- **Max position size:** 1% of portfolio per swing
- **Stop-loss must be set at entry** — no naked positions
- **Time-stop hard cap:** 30 days

Swing picks use `swing_resolver.py` — bar HIGH/LOW touch + bar-OPEN gap fills (replaces the broken `outcome_resolver.py:384-405` path).

## §5 Asset class current standing

Cited from `reports/asset_class_independent_recompute_2026_04_27_mercury2_copilot.md` (the canonical recompute as of 2026-04-27, cross-verified across 5 peer reports). Sample sizes are post-noise-filter for FOREX/COMMODITY (resolver-noise wins removed); raw n in parens.

| Class | n | WR | PF | MaxDD | Tier | Path |
|---|---|---|---|---|---|---|
| EQUITY | 381 | 51.97% | 1.385 | TBD | Tier 2 candidate (verify MDD) | promote on next 100 closed |
| CRYPTO | 1,598 | 42.18% | 1.140 | 178% | Below Tier 3 (MDD lethal) | vol-target rescue per `reports/deep_dive_crypto_mdd_reduction_2026_04_28.md` |
| ETF | 83 | 54.22% | 1.220 | TBD | Building (n < 100) | hold; expand emitter |
| FOREX | 794 raw / ~290 clean | 50.38% raw / ~10.5% clean | 1.349 raw | TBD | BLOCKED on resolver fix | ship `outcome_resolver.py:384-405` fix first |
| COMMODITY | 622 raw / ~205 clean | 42.60% raw | 0.896 | TBD | BLOCKED on resolver fix + zero-edge candidate | resolver fix → re-evaluate |
| BOND | 17 | 47.06% | 1.601 | TBD | Insufficient data | hold; expand emitter |

**Long-term value tier (UEPS):** newly built 2026-04-28, no closed picks yet → "Building (n=0/100)" until walk-forward backtest produces ≥100 closed.
**Swing tier (UEPS):** same — Building.

> **Footnote on the CRYPTO row (added 2026-04-28 per `research/24_meme_unmap_recompute.md`):**
> The numbers above (`n=1,598 / WR 42.18% / PF 1.140 / MaxDD 178%`) describe a CURATED slice from the mercury2/Copilot recompute — strategies with valid resolver outcomes, post-noise-filter, after the standard exclusions documented in the source report. The RAW closed-pick book is materially worse: **n=6,886 / PF 0.409 / MaxDD ~23,500%** (peak-to-trough on cumulative fractional PnL). The 178% figure is the size of the worst peak-to-trough as a percentage of cumulative-peak; the 23,500% figure is on a different scale because cumulative PnL crosses the zero line, making percentage drawdown denominator-fragile. Both are correct under their respective definitions.
>
> When citing CRYPTO Tier classification per §2, use the CURATED slice numbers (which reflect what the system would do with proper noise filtering applied). When characterizing the worst-case drag of a single bad cluster (e.g., the `quan_engine_scalp::DOGEUSDT` 2026-03-28 stack per `research/26`), use the raw-book numbers because that cluster sits in the unfiltered raw book.
>
> Per `research/24`: removing the 165 meme picks (2.4% of n) does NOT materially improve either slice. Memes had per-pick WR 46.67%, slightly higher than non-meme crypto. The CRYPTO MaxDD problem is dominated by position-stacking on a small number of strategy×symbol pairs, NOT meme contamination.

## §6 KPI definitions (so everyone uses the same math)

| Metric | Formula |
|---|---|
| **WR** (Win Rate) | `wins / (wins + losses)` — closed picks only, exclude `still_active` |
| **PF** (Profit Factor) | `sum(gross_profit) / abs(sum(gross_loss))` |
| **MaxDD** (Max Drawdown) | peak-to-trough on cumulative pnl curve, expressed as % of peak |
| **CAGR** | `(final_value / initial_value)^(1/years) - 1` |
| **Sharpe Ratio** | `mean(daily_returns) / std(daily_returns) * sqrt(252)` |
| **Sortino Ratio** | same as Sharpe but std uses only negative returns |
| **Calmar Ratio** | `CAGR / abs(MaxDD)` |
| **n** (sample size) | count of CLOSED picks (entry+exit), NOT active positions |

**Resolver-noise filter rule:** for FOREX/COMMODITY claims, `realized_pnl_pct` must exceed ±0.10% (10bp) to count as a true win/loss. Wins below that threshold are resolver noise from the `outcome_resolver.py:384-405` 1bp WIN threshold + yfinance-spot-on-every-run bug. The `swing_resolver.py` (built 2026-04-28) replaces this path with bar HIGH/LOW touch detection.

## §7 Risk caps (firm limits, never bypass)

- **Daily loss cap (cumulative):** -3% of portfolio → halt new entries until next session
- **Per-trade max loss:** 1% (long-term: 2%)
- **Max correlated exposure:** 30% per sector for long-term, 20% for swing
- **Max single-position size:** 5% (long-term) / 1% (swing)
- **Margin buffer:** maintain ≥ 80% across all paper accounts

## §8 Promotion / demotion process

**Promotion to Tier 2 live capital:** requires 3 consecutive months of clean Tier 2 metrics in walk-forward + n ≥ 100 closed picks.

**Strategy demotion:** requires the mutation-before-kill protocol per CLAUDE.md "Strategy demotion" rule:
1. `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` (3-axis investigation)
2. `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (export closed CSV → `python tools/mutation_analysis.py`)

`BLOCKED_SOURCE_SYSTEMS` additions are demotions and follow the same protocol — never just-add.

## §9 Walk-forward backtest standard

- **4 overlapping sleeves**, quarterly rebalance
- **Train:** 2012-2018 / **Validate:** 2019-2021 / **Test:** 2022-2025 (rolling)
- No in-sample backtests permitted as "proven edge" claims
- EDGAR XBRL coverage 2012-2025 = 13y window
- Implementation: `alpha_engine/value_backtest.py` (built 2026-04-28; opt-in sidecar)

## §10 Sample-size discipline

Every aggregate stat in dashboards / PRs / reports MUST display `n=value`.

| n | Tag |
|---|---|
| < 30 | "insufficient data" — no inference permitted |
| 30 ≤ n < 100 | "developing" — directional only, not promotable |
| n ≥ 100 | clean tier classification permitted |

## §11 Reference materials

- `updates/long_term_value_project_2026-04-27/findings/SYNTHESIS.md` — value-investing methodology details (Magic Formula + Piotroski + Acquirer's Multiple composite)
- `reports/hedge_fund_performance_review_*.md` — current asset-class state
- `reports/asset_class_independent_recompute_2026_04_27_mercury2_copilot.md` — canonical n+WR+PF source for §5
- `outcome_resolver.py:384-405` — the broken non-crypto resolver bug (replaced by `swing_resolver.py` for swing picks; do not extend)
- `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` — required for demotions
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md` — required for demotions
- `CLAUDE.md` MAJOR GOALS section — top-level priority order

## §12 Version history

| Version | Date | Author | Notes |
|---|---|---|---|
| 1.0 | 2026-04-28 | Claude Opus 4.7 | Initial charter. Created during UEPS build. Replaces ad-hoc tier definitions scattered across `reports/`. |
