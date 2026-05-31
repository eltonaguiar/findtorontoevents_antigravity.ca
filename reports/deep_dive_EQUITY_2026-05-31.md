# Deep Dive — EQUITY (2026-05-31)

Sources (canonical, as of generation):
- `audit_dashboard/data/pf_registry.json` → `by_asset_class_policy_clean_net` (EQUITY) + `by_asset_class_strategy_policy_clean_net` + `by_asset_class_strategy_symbol`
- `audit_dashboard/data/money_ready_verdict.json` → `classes.EQUITY`
- `audit_dashboard/data/dashboard_data.json` → `performance.asset_class_health.EQUITY`
- `audit_dashboard/data/pick_summary_stats_2w.json` and `pick_summary_stats_48h.json` → `by_class.EQUITY`

Trigger: CLAUDE.md Goal #1 deep-dive process. EQUITY is currently in the FAIL+INSUFFICIENT_N bucket with PF well under 1, sub-30% WR after noise filter, and MDD ~98% (near-total drawdown of cumulative pnl curve). This report autopsies per source/strategy/symbol, lists external-replication anchors, and proposes a 30/60/90 rescue plan.

## Current State (n, WR, PF, MDD, expectancy, recency)

| Metric | Value | Source |
| --- | --- | --- |
| n (resolved, policy-clean, net) | **39** | pf_registry policy_clean_net |
| Wins / Losses | 11 / 28 | pf_registry |
| Win rate | **28.21 %** | pf_registry |
| Profit factor | **0.145** | pf_registry |
| Total PnL % (sum) | -2.12 % | pf_registry |
| Max drawdown % (cumulative curve) | **0.98** (~98% of cum peak) | pf_registry, money_ready_verdict |
| Expectancy (per pick, slippage 10 bp) | **-0.0554** | money_ready_verdict.details.expectancy |
| CVaR-95 | -83.91 | money_ready_verdict.details.mdd_cvar |
| DSR score | 0.0001 (FAIL) | money_ready_verdict.details.dsr |
| PBO / SPA | undefined (no strategy with n>=20) | money_ready_verdict.details |
| Top source share | **regime_terminal 38.46 %** | money_ready_verdict |
| Top symbol share | INTC 15.38 % | money_ready_verdict |
| Verdict (money-ready) | **INSUFFICIENT_DATA** (fails n_ok, wr_ok, pf_ok, dsr_ok, expectancy_ok, mdd_ok, cvar_ok) | money_ready_verdict |
| `asset_class_health` status | **thin_sample** (PF 0.046, WR 27.27%, MDD 0.97) | dashboard_data |
| 14-day window (raw, leakage-flagged) | n_closed 8506, WR 65.49 %, PF 5.324, top_source `smart_money` 59.9 %, AMZN 16.3 % | pick_summary_stats_2w |
| 48-hour window | n_closed **102**, WR **24.51 %**, PF **0.317**, mean PnL -1.21 %, top_source `AlphaEngine` **100 %** | pick_summary_stats_48h |
| Drift vs 2026-05-29 baseline | wr +5.99 pp, pf +0.111, n +12, verdict unchanged | money_ready_verdict.drift |

Notes:
- The 14-day window WR (65 %) is **incompatible** with both the policy-clean panel (28 %) and the 48-hour panel (24.5 %). Per CLAUDE.md the 14d/48h panels carry leakage caveats; the policy_clean_net + asset_class_health view is the verdict-grade truth, and the 48h panel is the most recent honest signal. Treat the 14d 65 % WR as a leakage artifact (dup_groups=6 flagged) until reconciled.
- 48h panel is 100 % single-source (`AlphaEngine`). This means the recent collapse cannot be attributed to a peer source — it is wholly internal.

## Per-Source Autopsy (top sources by volume; WR/PF each)

Sources in the policy-clean-net EQUITY cohort (n=39) bucket through `top_source = regime_terminal` (38.46 %, i.e. ~15 picks). The pf_registry stratifies EQUITY by `strategy`, not `source_system`; the 48h panel confirms `AlphaEngine` is the sole live source in recent flow. Combined with `top_source_share` in money_ready_verdict, the source picture is:

| Source / engine | Approx volume share (policy-clean) | WR | PF | Notes |
| --- | --- | --- | --- | --- |
| `AlphaEngine` (umbrella) — strategies regime_terminal, regime_mild_bear, regime_accumulation, regime_mild_bull, stocks_rsi2_pullback | dominant (100 % of last 48h, ~95 %+ of policy-clean cohort) | 28–33 % | 0.03–0.83 | Concentrated in regime_terminal (n=15, WR 33.3 %, PF 0.83 — best of the failing set) and stocks_rsi2_pullback (n=10, WR 30 %, PF 0.032 — catastrophic) |
| `multi_asset_copytrader` | 11/39 = 28.2 % | 18.2 % | 0.181 | Imitative source — copying losers from EQ leaders (INTC concentration) |
| `smart_money` | 0 % policy-clean, **59.9 % of 14d raw** | 14d WR 65 %, dup_groups=6 | leakage-flagged | Inflates 14d panel; absent from policy-clean — likely filtered out as duplicates or unresolved |
| External (CoinGecko/news/macro) | ~0 in cohort | n/a | n/a | EQUITY pipeline is internally-sourced; no external alpha entering the policy-clean view |

Bottom line: there is effectively **one source** (AlphaEngine / regime engines + copytrader). HHI on the source axis is >0.50 — well above the strategy-level concentration trigger (>0.30) from `feedback-concentration-strategy-not-engine.md`. This is a single-source failure dressed up as a multi-strategy result.

## Strategy Breakdown (per-strategy WR/PF/single_source_pct; flag concentration)

From `by_asset_class_strategy_policy_clean_net`:

| Strategy | n | Wins | Losses | WR % | PF | Single-source % (engine) | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `multi_asset_copytrader` | 11 | 2 | 9 | 18.18 | **0.181** | 100 % AlphaEngine | FAIL — copying a losing leader (INTC dominates: n=6, WR 16.7 %, PF 0.52) |
| `regime_accumulation` | 1 | 1 | 0 | 100.00 | n/a (no_losses) | 100 % | INSUFF — single pick (TSLA) |
| `regime_mild_bear` | 2 | 0 | 2 | 0.00 | **0.0** | 100 % | FAIL — too small to act on |
| `regime_terminal` | 15 | 5 | 10 | 33.33 | **0.830** | 100 % | NEAR-MISS — best of the cohort but still sub-1 PF; GOOGL/NVDA/AAPL drag |
| `stocks_rsi2_pullback` | 10 | 3 | 7 | 30.00 | **0.032** | 100 % | CRITICAL — wins are tiny, losses are catastrophic (gross_loss 1.74 % vs gross_profit 0.055 %) |

Concentration flags:
- All five strategies are 100 % AlphaEngine-sourced → **source HHI ~ 1.0** (worst possible).
- Strategy-share HHI (per CLAUDE.md M-067 rule, strategy-level): regime_terminal 0.38, multi_asset_copytrader 0.28, rsi2 0.26, others <0.05. HHI ≈ 0.32 — at the threshold; not single-strategy concentrated but the worst single strategy (rsi2) carries 80 % of the gross_loss budget.
- INTC dominates the symbol axis inside copytrader (6/11 picks) — symbol concentration inside the worst strategy.

## What Is Failing (root causes — name strategies, sources, patterns)

1. **`stocks_rsi2_pullback` is leaking catastrophic tail losses.** Gross loss 1.74 % vs gross profit 0.055 % on n=10. This is the single biggest drag on EQUITY PnL. The pattern is classic mean-reversion-without-stop: RSI(2) buys oversold pullbacks but holds through continuation moves. **Action: kill or hard-stop this strategy first.**
2. **`multi_asset_copytrader` is copying a known loser (INTC).** n=6 INTC, WR 16.7 %, PF 0.52 — and is the second largest loss contributor. The copytrader source signal needs a leader-quality filter; it currently imitates without per-leader gating.
3. **`regime_terminal` is the closest to viable (PF 0.83, WR 33 %)** but still sub-1. Wins are coming from speculative names (LCID, RIVN small wins) while losses are coming from megacaps (AAPL, NVDA, GOOGL, AMZN). The strategy may be regime-misclassifying: "terminal" tag is firing on names that mean-revert positively rather than crash.
4. **48h panel shows 100 % `AlphaEngine` source concentration with 24.5 % WR / PF 0.317.** Whatever changed in the last 48h made the engine worse, not better. The 14d 65 % WR (via `smart_money`) does not survive policy-clean filtering — it is leakage-tainted (dup_groups=6 flagged on a 14d window).
5. **Drawdown is near-total (MDD ~98 % of cumulative peak).** With n=39 and PF 0.15, the cumulative pnl curve never recovers; this is structural under-edge, not a bad streak.
6. **No external alpha source is in the policy-clean cohort.** EQUITY is fully internally generated → no triangulation, no out-of-sample anchor.

## External Replication Options

The goal here is **external benchmarks to verify or refute the regime/copytrader/rsi2 thesis** and to seed Tier-2-grade external signal:

- **MTUM (iShares MSCI USA Momentum)** — 12-month momentum portfolio. If `regime_terminal`'s long thesis on growth names matches MTUM's holdings drift, we can mirror sleeve weights as a regime overlay. Free daily holdings on iShares.
- **QMOM (Alpha Architect Quantitative Momentum)** — concentrated high-momentum portfolio (~50 names, monthly rebalance). Better replication target than MTUM for "high-conviction momentum" because it's more discriminating.
- **VLUE / RPV (iShares MSCI USA Value / Invesco S&P 500 Pure Value)** — to anchor `multi_asset_copytrader`'s INTC tilt; INTC is a deep-value name, copying value-leader without a momentum filter is a known anti-pattern.
- **DBMF (iMGP DBi Managed Futures Strategy)** — trend-following overlay; not equity per se but the gating logic (don't fight regime) maps directly. Use as a regime kill-switch: when DBMF goes risk-off, derate equity longs.
- **KMLM (KFA Mount Lucas Managed Futures)** — alternative trend overlay; cross-check against DBMF.
- **AQR / Two Sigma factor sheets (public quarterly factsheets)** — long-horizon factor returns (mom, val, quality, low-vol) to size strategy weights. Free PDFs.
- **Quiver Quantitative (`quiverquant.com`)** — congressional/insider trades, used as a `multi_asset_copytrader`-style external leader feed. Replace internal copytrader with a vetted external one.
- **Hyperliquid HLP** — not for EQUITY (perp DEX), excluded from replication anchors here.
- **PIMCO BOND ETFs** — not for EQUITY.
- **Robintrack-style retail-positioning aggregators (Stocktwits sentiment, FinPie, Composer)** — for contrarian signal vs the copytrader herd.

Acquisition cost: all of the ETF anchors are free daily-holdings JSON/CSV; Quiver and Composer have free tiers; AQR/2-sig factsheets are PDF.

## 30 / 60 / 90 Day Rescue Plan

**Days 0–30 — Stop the bleed and shrink the surface.**
- Day 1: Move `stocks_rsi2_pullback` to `BLOCKED_SOURCE_SYSTEMS` after running `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` + `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutation analysis on closed CSV). Hard-stop justification: PF 0.032 on n=10, gross_loss 31× gross_profit.
- Day 1: Hard-cap `multi_asset_copytrader` exposure to non-INTC symbols only (or block entirely pending leader-quality filter). Single-symbol concentration inside the worst strategy is unacceptable.
- Days 2–7: Wire MTUM + QMOM daily holdings into `audit_dashboard/data/` as an external EQUITY anchor; expose top-10 holdings drift on `/audit`.
- Days 7–21: Reframe `regime_terminal` — the strategy's wins (LCID, RIVN, TSLA) suggest it's actually a speculative-growth long, not a terminal/regime call. Rename + retag, then refit thresholds on the closed-CSV with mutation analysis. Acceptance: PF >= 1.2 on backtest + forward 14d.
- Day 30: Re-run `pf_registry` + `money_ready_verdict`; require **n>=50 policy-clean, WR>=45 %, PF>=1.1, MDD<=50 %** to clear "stop the bleed" gate.

**Days 31–60 — Rebuild from external anchors.**
- New sleeve: **MTUM/QMOM-mirror long-only** with weekly rebalance, paper-traded into `audit_dashboard/data/`. Goal: 100 picks, WR>=50, PF>=1.3.
- New sleeve: **Quiver congressional copytrader** replacing internal copytrader. Goal: 50 picks, WR>=45, PF>=1.2.
- Wire DBMF/KMLM regime overlay (risk-on / risk-off flag from external managed-futures funds) into `passes_active_gate` for EQUITY. When DBMF is in drawdown >5 %, derate EQUITY position size by 50 %.
- Day 60 gate: combined EQUITY cohort n>=150 policy-clean, WR>=50 %, PF>=1.3, MDD<=20 % (Tier-2 minimum per CLAUDE.md).

**Days 61–90 — Promote to candidate-Tier-2.**
- Run DSR + PBO + SPA on the new cohort (need n>=20 per strategy for PBO/SPA to even compute).
- Cross-asset correlation check (EQUITY vs CRYPTO vs COMMODITY) to ensure diversification before sizing up.
- Day 90 gate (Tier-2 promote): n>=200 policy-clean, WR>=52 %, PF>=1.5, MDD<=20 %, DSR pass, PBO<0.5, SPA p<0.05, single-source share<=30 %, single-symbol share<=15 %. Update `updates/index.html` (per CLAUDE.md entry-insertion-rule, above the `:START` marker, then FTP-deploy).

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Killing `stocks_rsi2_pullback` removes signal we don't fully understand | Med | Low (PF 0.032, contribution net-negative) | Move to dormant, not deleted; keep paper-only for 60d |
| Copytrader fix breaks other asset classes that share the engine | Med | Med | Scope copytrader gate change to EQUITY-only via `asset_class` filter in `multi_asset_copytrader` |
| External ETF holdings feeds drift / get rate-limited | Med | Low | 3+ fallback chain per CLAUDE.md API rule (iShares → SS&C → ETF.com → web scrape) |
| `regime_terminal` rename loses backtest continuity | Low | Med | Keep raw strategy tag in `pf_registry_strategy` column, alias for display |
| Day-30 gate passes but is a fluke due to a single hot week | Med | High | Require n>=50 AND require WR/PF on a rolling 14d window not just cumulative |
| Single-source HHI stays at 1.0 even after adding MTUM/QMOM (because they all route through `AlphaEngine`) | High | High | Tag external sleeves with distinct `source_system` strings (`mtum_mirror`, `quiver_copy`, etc.) so HHI is measured honestly |
| 14d/48h panel discrepancy (65 % vs 24 %) hides a leakage bug we haven't fixed | High | High | Open a P0 to resolve dup_groups=6 in the 14d window before any sizing decision |
| FTP not deployed after `updates/` write (CLAUDE.md repeat violation) | Med | Med | Always end with `python3 tools/deploy_audit_files.py --only updates` |
| Tier-2 promote happens without 100+ clean trades (per CLAUDE.md M-067) | Low | High | Hard-coded gate in `money_ready_verdict` already enforces n>=100 stable; do not bypass |

## Acceptance Criteria

EQUITY is considered **rescued / Tier-2-eligible** when, on a single regeneration of `pf_registry.json` + `money_ready_verdict.json`:

1. `by_asset_class_policy_clean_net.EQUITY.n >= 200`
2. `win_rate_pct >= 52`
3. `profit_factor >= 1.5`
4. `max_drawdown_pct <= 0.20`
5. `money_ready_verdict.classes.EQUITY.verdict == "READY"` (all gates `*_ok = true`)
6. `dsr_ok = true`, `pbo < 0.5`, `spa_p < 0.05`
7. `top_source_share <= 0.30` AND `top_symbol_share <= 0.15`
8. At least 2 distinct source_system tags, at least one explicitly external (MTUM/QMOM mirror, Quiver, etc.)
9. 14d and 48h panels are **directionally consistent** with policy-clean (within 10 pp WR) — no leakage discrepancy
10. Update card added on `updates/index.html` (above `:START`) and FTP-deployed; verified live via `curl -sI`

## Hard Rule (Until Met)

**EQUITY is sizing-blocked.** Until the Acceptance Criteria above clear:

- `sizing_allowed = false` (already enforced by `asset_class_health.EQUITY.status = "thin_sample"`)
- No new EQUITY strategies wired into `calculate_smart_score` / `passes_active_gate` / `passes_smart_gate` unless they ship with `## Wiring Plan` per CLAUDE.md Wire-Up Rule
- `stocks_rsi2_pullback` paper-only (no live picks) until mutation analysis clears
- `multi_asset_copytrader` blocked on INTC; whitelisted symbols only
- Any peer agent claim of "EQUITY tier-2 ready" must cite `pf_registry.json` + `money_ready_verdict.json` regenerated **after** the date of this report, OR the claim is rejected per CLAUDE.md "DO NOT trust unsourced model claims about /audit numbers"
- No promotion card on `updates/index.html` for EQUITY until acceptance #10 is satisfied (with FTP-deploy proof)
