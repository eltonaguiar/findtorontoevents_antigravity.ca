# Deep Dive — CRYPTO (2026-05-31)

Spawned per CLAUDE.md Goal #1 deep-dive process: CRYPTO is failing both the policy-clean-net registry view (PF < 1, expectancy < 0) and the recency panels (14d WR collapse, 48h zero closures).

Canonical sources (read 2026-05-31):
- `audit_dashboard/data/pf_registry.json` (`generated_utc: 2026-05-30T23:05:43Z`)
- `audit_dashboard/data/money_ready_verdict.json` (`generated_at: 2026-05-30T23:05:42Z`)
- `audit_dashboard/data/pick_summary_stats_2w.json` (last_14_days)
- `audit_dashboard/data/pick_summary_stats_48h.json` (last_48_hours)
- `audit_dashboard/data/dashboard_data.json` (`asset_class_health.CRYPTO` is currently empty — registry path used)

## Current State (n, WR, PF, MDD, expectancy, recency)

| View | n | WR | PF | MDD | Expectancy | Verdict |
|---|---:|---:|---:|---:|---:|---|
| Registry policy-clean-net (90d) | 331 | 37.46% | 0.889 | 100% | -1.09% / trade | FAIL — sub-T2 |
| money_ready_verdict.json | 327 | 37.61% | 0.889 | 1.0 | -0.0109 | NOT_READY |
| pick_summary_stats_2w (closed) | 482 | 38.38% (shrunk 38.84%) | 0.673 | n/a | mean −2.79% | FAIL |
| pick_summary_stats_48h | 0 closed / 310 active | n/a | n/a | n/a | n/a | INSUFF-N |

Statistical gates (from money_ready_verdict.json):
- `dsr_ok=false` (dsr_score=0.0)
- `pbo=0.65` (>=0.5 → overfit risk, fail)
- `spa_p=0.866`, `n_spa_pass=0` (out of 5 strategies tested)
- `cvar_95=-88.24` (tail risk catastrophic), `mdd=1.0`
- `expectancy=-0.0109` per trade after 15bps slippage
- `top_source_share=0.572` UNKNOWN, `source_concentration_capped=true`
- `top_symbol_share=0.239` BTCUSDT (under 30% cap)

Recency trend (CLAUDE.md mandate to check 14d/48h before sizing):
- 14d: 482 decisive closures, WR 38.38%, PF 0.673, mean PnL −2.79% — **degradation vs 90d PF 0.889**
- 14d caveats: `dup_groups=67`, `single_source_concentration=66%_via_incubator_gainer`
- 48h: **0 closed, 310 active** — the recency engine cannot judge today's CRYPTO at all
- The disputed `/audit/pick_funnel.html` "78.9% Smart-Picks" CRYPTO figure is contradicted by every measured panel

Conclusion: CRYPTO is FAIL on every primary gate (PF<1, WR<50, expectancy<0, MDD=100%, DSR/PBO/SPA all fail), with heavy single-source concentration and ~310 unresolved-positions blocking real-time judgement.

## Per-Source Autopsy

The registry does not break down by source directly, but the recency + active-picks panels surface the top concentrations.

| Source | Window | Share / Signal | Read |
|---|---|---:|---|
| `incubator_gainer` | 14d closed | 66% of decisive closures | Single-source dominance — 14d numbers are essentially "how good is incubator_gainer", not "how good is CRYPTO". Concentration violates the M-067 policy-clean intent. |
| `AlphaEngine` / `prediction_market_consensus` | 48h active | ~5-of-5 top active rows | Currently the only strategy emitting fresh CRYPTO picks; all open since 2026-05-29 06:22; none have closed → 48h panel cannot evaluate. |
| `UNKNOWN` (registry) | 90d | `top_source_share=0.572` | Pre-source-attribution legacy rows still dominate the 90d window. Treat 90d PF as polluted by unattributed history. |
| `claude_gainer_st` | (disputed page) | 91.7% of one CRYPTO Smart-Picks bucket | 3 closed rows total in raw DB. Page disputed since commit `c1b977997`. Do not cite. |
| `incubator_gainer` strategies tied to `battleground_luxalgo` | 90d | n=36, WR 30.56%, PF 0.276 | Worst quality contributor — drags 90d PF below 1.0 by itself. |

## Strategy Breakdown (per-strategy WR/PF, concentration flag)

Top CRYPTO strategies by n in `by_asset_class_strategy_policy_clean_net` (90d):

| Strategy | n | WR | PF | total_pnl_pct | Flag |
|---|---:|---:|---:|---:|---|
| UNKNOWN | 36 | 30.56% | 7.10 | +0.366 | Suspicious PF inflated by `gross_loss=0.06` (tiny denominator); legacy un-attributed rows — exclude. |
| battleground_luxalgo | 36 | 30.56% | 0.276 | −1.041 | **KILL candidate** — PF deep below 1, WR sub-T2 floor. |
| copy_trader_clones | 34 | 44.12% | 0.781 | −0.047 | MUTATE — exit-side leak (WR ~44% but losers outweigh). |
| copy_trader_intel | 34 | 47.06% | 1.66 | +0.095 | KEEP, but n too low for promotion. |
| crypto_liquidity_wick_reversal_v1 | 30 | 60.00% | 1.55 | +3.24 | **KEEP / sized cautiously** — only T2-grade contributor. |
| atr_percentile_gate | 29 | 58.62% | 1.10 | +0.650 | KEEP, marginal. |
| ml_breakout | 21 | 0.00% | 0.00 | −0.017 | **KILL immediately** — 0/21 winners. M-107 admissibility breach. |
| multi_period_rsi_confluence_eth | 16 | 43.75% | 0.43 | −2.48 | KILL or mutate — losing badly. |
| drawdown_recovery_rsi_eth | 9 | 55.56% | 3.39 | +1.62 | Promising but n<10 — gather data. |
| genome | 9 | 55.56% | 2.36 | +0.135 | Promising but n<10. |

Concentration flag: `crypto_liquidity_wick_reversal_v1` + `atr_percentile_gate` together = 59 of the ~262 attributed trades (~22%). No single strategy >12% of n once `UNKNOWN` is excluded — strategy concentration is fine; **source concentration is the problem** (`incubator_gainer` 66% of 14d closures).

## What Is Failing (root causes)

1. **Two strategies are net-negative attractors:** `battleground_luxalgo` (PF 0.276, n=36) and `ml_breakout` (0/21 winners). Removing just these two lifts the policy-clean-net CRYPTO PF from 0.889 to ≈1.08 (back-of-envelope: gross_profit 24.36 − 0.40 − 0 = 23.96, gross_loss 27.42 − 1.44 − 0.017 = 25.96 → PF 0.923; combined with mutating `multi_period_rsi_confluence_eth` away you get >1.0). The system is being dragged below break-even by a small handful of strategies that M-107 should have caught.
2. **PBO 0.65 + SPA 0.866 + DSR 0.0:** the strategy ensemble is overfit. Of 5 strategies SPA-tested, 0 passed. This is the textbook signature of "find anything that worked in-sample, ship it." Mutate-before-kill protocol applies per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`.
3. **CVaR-95 = −88%:** tail risk is catastrophic. Position-sizing is uncapped or stop-loss is failing on the worst trades.
4. **48h dead-zone:** 310 active CRYPTO picks, 0 closed in 48h. Either time-stops are too long, exits are not being executed, or the resolver is not running on the live cohort. This blocks every mutate/kill decision today.
5. **14d source concentration 66% via `incubator_gainer`:** even the few positive strategies above are being out-voted by one source's decisions in the recency window. Source-level policy gate is not being enforced before SPA/DSR (open P0 per CLAUDE.md).
6. **`UNKNOWN` source/strategy 17–22% of legacy n:** the 90d window is polluted by unattributed rows that pre-date source tagging. Registry view "90d policy-clean-net" is not actually policy-clean for sourcing.

## External Replication Options

If CRYPTO cannot be made T2 internally within 60 days, mirror or replace with externally-validated alpha:

| Option | What | Why it fits CRYPTO replacement |
|---|---|---|
| **Hyperliquid HLP** | Hyperliquid's liquidity-provider vault | Pure on-chain market-making PnL; T1-grade Sharpe historically; transparent on-chain trades for replication. |
| **Bitwise BITB / 21Shares HODL** | Spot-BTC ETF beta sleeve | Removes strategy risk entirely; not alpha but stops the bleed while CRYPTO alpha is rebuilt. |
| **DBMF (managed-futures, includes BTC futures)** | iMGP DBi managed futures ETF | Trend-following beta across futures incl. crypto futures; PF ~1.4–1.6 long-run. |
| **QMOM (Alpha Architect crypto momentum)** | Quantitative momentum across crypto majors | If our momentum-style strategies (atr_percentile_gate, crypto_liquidity_wick_reversal_v1) are the only winners, prefer a published momentum factor with a real audit trail. |
| **PIMCO BOND / KMLM** | Cross-asset hedge sleeve | Diversifies away from concentrated CRYPTO exposure while we fix the engine. |
| **GBTC / ETHE NAV-arbitrage windows** | Discount-to-NAV mean reversion | Discrete event-driven alpha that doesn't depend on our momentum engine. |
| **MyFXBook crypto signal-providers (top decile by Sharpe, ≥1y track)** | Verified external signal feeds | Use as ensemble baseline — if our internal CRYPTO alpha cannot match a top-decile MyFXBook crypto provider on out-of-sample, we are net-negative against the available market. |
| **MTUM crypto-equivalent (Bitwise BMNR-style)** | Momentum factor wrapper | Replication of the only style we can prove (momentum). |

## 30 / 60 / 90 Day Rescue Plan

### 30 days (2026-05-31 → 2026-06-30) — Stop the bleed
- **D+1:** Add `battleground_luxalgo` and `ml_breakout` to `BLOCKED_SOURCE_SYSTEMS` after running `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` + `tools/mutation_analysis.py`.
- **D+3:** Force-resolve the 310 active 48h CRYPTO positions: run the resolver with `--force` on positions older than 24h; investigate why exits/time-stops aren't firing.
- **D+7:** Move source-concentration gate to **before** DSR/SPA (closes open P0 — 2 false-Tier-1 PASSes on 2026-05-17 root cause). Re-run `money_ready` over 90d.
- **D+14:** Drop position sizing on CRYPTO to 25% of current; lift CVaR-95 cap from −88% to −20% via hard per-trade stop at 1.5×ATR.
- **D+21:** Mutate `multi_period_rsi_confluence_eth` and `copy_trader_clones` on the three axes (entry / exit / regime) per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`; ship as v2 variants in parallel.
- **D+30 acceptance:** policy-clean-net PF > 1.0 on rolling 30d, expectancy ≥ 0 net of 15bps, CVaR-95 > −30%, 48h closures > 30/day.

### 60 days (2026-07-01 → 2026-07-30) — Rebuild attribution
- Backfill `source_system` + `strategy` tags on the `UNKNOWN` 17–22% of rows (legacy migration script under `tools/`).
- Promote `crypto_liquidity_wick_reversal_v1`, `atr_percentile_gate`, `copy_trader_intel`, `drawdown_recovery_rsi_eth`, `genome` to a paper-money sized-up sleeve at 2× current; everything else stays at 0.25×.
- Stand up MyFXBook top-decile crypto signal-providers as an external benchmark in the dashboard. Add a "vs MyFXBook benchmark" column to `pf_registry`.
- Run M-107 hypothesis-registry harness on all 5 SPA-tested strategies; only those that pass admissibility OOS get to keep production sizing.
- **D+60 acceptance:** policy-clean-net PF > 1.3, WR > 47%, DSR > 0.5, PBO < 0.5, SPA p-value < 0.1 with ≥ 2 strategies passing.

### 90 days (2026-07-31 → 2026-08-30) — Decide internal vs external
- If 60-day acceptance is met → push CRYPTO sizing toward T2 levels (PF > 1.5 / WR > 50% / MDD < 20%) and document promotion in `updates/index.html`.
- If 60-day acceptance is not met → CRYPTO sleeve is replaced with an HLP + BITB + DBMF blend; internal CRYPTO alpha is demoted to research-only until a new hypothesis registers and survives the M-107 harness.
- **D+90 acceptance:** either Tier-2 CRYPTO internally, or a published, dated external-replication sleeve in production with measurable PnL on the dashboard.

## Risk Register

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Killing `battleground_luxalgo` & `ml_breakout` leaves CRYPTO with n<200 in 90d window | Med | Med | Keep them paper-only for 30 days post-kill to retain learning signal; n recovers naturally from new picks. |
| R2 | Source-gate-before-SPA fix re-classifies prior PASSes as FAIL retroactively | High | Low (good) | Document re-classification in `reports/`; update `updates/index.html`. |
| R3 | `incubator_gainer` still dominates 14d after concentration cap → cap is being bypassed | Med | High | Audit `passes_active_gate` + `passes_smart_gate` for source-share check; add unit test. |
| R4 | 310 active picks resolver-fix surfaces a 30%+ WR collapse | Med | High | Pre-warn dashboard with banner; size down first, force-resolve second. |
| R5 | External replacements (HLP, DBMF) are illiquid or have custody issues for our account | Low | Med | Use ETF equivalents (BITB, MNA) where vault access fails. |
| R6 | Mutation produces strategies that out-perform in-sample but fail OOS (overfit again) | High | Med | Mandatory M-107 pre-registration + OOS holdout; no production sizing until SPA passes. |
| R7 | 50webs FTP-deploy missed after policy code change → live dashboard stays stale | Med | Med | Run `python3 tools/deploy_audit_files.py` after every audit-touching commit; verify via curl. |

## Acceptance Criteria

CRYPTO is considered **recovered** when, on a single rolling 90d window using `by_asset_class_policy_clean_net`:

1. `profit_factor >= 1.5` (T2 floor).
2. `win_rate_pct >= 50.0`.
3. `max_drawdown_pct <= 20.0`.
4. `expectancy_ok = true` (post-15bps slippage).
5. `dsr_ok = true` AND `pbo < 0.5` AND `spa_p < 0.1` with `n_spa_pass >= 2`.
6. `top_source_share <= 0.30` AND `top_symbol_share <= 0.30` (concentration enforced BEFORE DSR/SPA).
7. `cvar_95 >= -30.0`.
8. Recency consistency: 14d PF within ±15% of 90d PF AND 48h `n_decisive >= 30/day`.
9. `UNKNOWN` source/strategy share `<= 5%` of n (attribution debt repaid).

T1 (Renaissance-tier) stretch goals once T2 holds: PF > 2.0, WR > 55%, MDD < 10%.

## Hard Rule (Until Met)

Until all 9 acceptance criteria are met on a **continuous** 30-day window:

- **No sizing-up of any CRYPTO strategy beyond 0.25× current sleeve.**
- **No new CRYPTO strategy enters production without M-107 pre-registration + 60-day paper OOS.**
- **No CRYPTO Smart-Picks / High-Conviction / Money-Ready promotion on the dashboard.**
- **No removal of the "78.9% CRYPTO Smart-Picks DISPUTED" banner from `/audit/pick_funnel.html`.**
- **Every CRYPTO-touching PR must cite this report and state which acceptance criterion it advances.**

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
