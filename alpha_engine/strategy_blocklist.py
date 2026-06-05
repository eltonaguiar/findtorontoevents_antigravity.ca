"""
Strategy blocklist - retire dead/toxic strategies at the feed level.

Strategies listed here are rejected by `feed_hygiene.is_valid_active_pick` so
no new active picks using them are emitted. Add entries only after a proper
investigation per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` and mutation
analysis per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`.

Two categories tracked:
  * RETIRED   - negative-EV proven from realized data (hard-block forever)
  * PAPER-ONLY - new strategies that haven't passed Strategy Factory S4
                 (forward paper test; see docs/STRATEGY_FACTORY_V1_1_AMENDMENTS.md).
                 Hard-blocked from live emission until validated; may still run
                 in paper-trading mode when feed_hygiene is bypassed intentionally.

Rollback flags:
  * RAPID_FIRE_MACD_KILL_DISABLED=1 — temporarily disables the
    ("rapid_fire", "macd_rsi_confluence") composite kill. Default off
    (kill active). Added 2026-04-29 alongside the surgical kill.
  * RAPID_FIRE_RSI_BOUNCE_KILL_DISABLED=1 — temporarily disables the
    ("rapid_fire", "rsi_bounce") composite kill. Default off (kill
    active). Added 2026-04-29 as the Phase 2-A panel-driven follow-up to
    the macd_rsi_confluence kill (PR #509).
  * GOLDMINE_STOCKS_KILL_DISABLED=1 — temporarily disables the
    ("goldmine_stocks", "goldmine_{5,6,7}x_consensus") composite kills
    on EQUITY. Default off (kill active). Added 2026-04-29.
"""

import os

# -----------------------------------------------------------------------
# FX Kill Switch — Dynamic FOREX strategy kill enforcement
#
# Strategies that pass fx_kill_switch.check_strategy_for_kill() (True,
# reason) are dynamically added to the retired set here, so any code path
# that calls is_blocked_strategy() or is_blocked_pick() respects the kill.
# The 7 known-toxic hard-blocks live in fx_kill_switch._KNOWN_TOXIC_FOREX_STRATEGIES;
# this section catches dynamically-detected FOREX decay/PF/WR kills.
#
# Rollback: FX_KILL_SWITCH_DISABLED=1 (see fx_kill_switch.py)
# -----------------------------------------------------------------------
try:
    from alpha_engine import fx_kill_switch as _fx_ks
    _FX_KILL_SWITCH = True
except ImportError:
    _FX_KILL_SWITCH = False

# COMMODITY Inverse Kill Switch — block inverse-COMMODITY strategies
# Rollback: COMMODITY_INVERSE_KILL_DISABLED=1 (see alpha_engine/commodity_kill_switch.py)
try:
    from alpha_engine import commodity_kill_switch as _cm_ks
    _COMMODITY_INVERSE_KILL_SWITCH = True
except ImportError:
    _COMMODITY_INVERSE_KILL_SWITCH = False


def is_fx_killed_strategy(name: str) -> bool:
    """Return True if the strategy is FOREX and failed FX kill rules.

    Checks the known-toxic hard-block list first (always active), then
    calls check_strategy_for_kill() for dynamic decay/PF/WR kills.

    Args:
        name: Strategy name (e.g. 'forex_rsi2_mean_reversion')

    Returns:
        True if FOREX strategy should be blocked
    """
    if not _FX_KILL_SWITCH:
        return False
    if not name:
        return False
    should_kill, _ = _fx_ks.check_strategy_for_kill(name)
    return should_kill


def is_commodity_inverse_killed_strategy(name: str, asset_class: str = "") -> bool:
    """Return True if the strategy is a COMMODITY inverse strategy to be killed.

    Checks:
    1. Known toxic COMMODITY strategies (hard-block list, always active)
    2. Any COMMODITY asset_class pick with inverse-direction naming
    3. Any strategy name that is both COMMODITY-focused AND inverse-named
    4. Dynamic PF/WR/decay kills via check_strategy_for_kill()

    Args:
        name: Strategy name (e.g. 'commodity_inverse_momentum')
        asset_class: Asset class from the pick (e.g. 'COMMODITY')

    Returns:
        True if COMMODITY inverse strategy should be blocked
    """
    if not _COMMODITY_INVERSE_KILL_SWITCH:
        return False
    if not name:
        return False
    should_kill, _ = _cm_ks.check_strategy_for_kill(name, asset_class=asset_class)
    return should_kill



# 2026-04-18: retired after V3 playbook review (peer-review external AIs).
# All three have n >= 1500 closed trades with sub-30% WR and cumulative losses.
_RETIRED_STRATEGIES = frozenset({
    # fear_greed_contrarian: n=3525, WR 28.3%, -456% cumulative PnL
    "fear_greed_contrarian",
    # proven_propfirm_cons_prop: n=1832, WR 19.5%
    "proven_propfirm_cons_prop",
    # proven_triple_ema_prop: n=1616, WR 17.2%
    "proven_triple_ema_prop",
    # Additional deterministic-loser pattern found 2026-04-19:
    # copy_hl_lb_None on crypto: 25 picks, 0% WR, -270.8% PnL (MATIC-pattern)
    "copy_hl_lb_None",
    # 2026-04-20: st_fear_greed_contrarian promoted from paper-only to retired.
    # Data-pipeline gap check (docs/AUDIT_DATA_PIPELINE_GAP_CHECKS_2026_04_20.md)
    # found 640 closed picks under this st_ prefix variant — it's the #1
    # historical-damage driver in the entire closed ledger. Kimi fact-check
    # confirmed 10.5% WR / -381.62% cumulative PnL. Same underlying logic
    # as the already-retired `fear_greed_contrarian` but bypassed the block
    # via the `st_` prefix. Hard-retire to match the parent strategy.
    "st_fear_greed_contrarian",
    # 2026-04-22: non_crypto_consensus 0% WR on 87 trades (deep strategy investigation).
    # copy_trader_intel module building consensus from non-crypto copy traders.
    # Every single trade lost. Hard-retire to block emission.
    "non_crypto_consensus",
    # 2026-04-20: st_obv_support_divergence promoted from paper-only to retired
    # after effectiveness + additional-fixes audit found persistent negative
    # contribution. 17.0% WR / n=53 / 35.9pp drop from all-time baseline (per
    # Gemini walkthrough) + presence in every toxic consensus combo (Kimi
    # fact-check). Paper-only tier insufficient; hold-block emission.
    "st_obv_support_divergence",
    # 2026-04-21: non_crypto_consensus retired. Per per-asset-class pick
    # analysis 2026-04-21 (updates/per_asset_class_pick_analysis_2026-04-21.md)
    # and cycle-8/9 perf-reviews:
    #   FOREX: n=85 closed, WR 0.0%, cum +0.01% — the cum label makes it look
    #   harmless but the 0% WR is unambiguous. Likely TP-at-entry / resolver
    #   zeroing bug behind the pnl=0 pattern; whatever the cause, the
    #   strategy is not producing differentiable signal.
    #   System-wide: n=88 closed with the same pnl=0 pattern. Currently
    #   generating 2 of the 3 active FOREX picks; every active FOREX pick
    #   flags on the dashboard sanity filter.
    # Reference: x-post review + per-class analysis
    #   (updates/2026-04-21-x-post-repos-and-tweak-queue.md).
    "non_crypto_consensus",
    # 2026-04-22: quan_engine_scalp retired after deep asset-class edge analysis
    # (updates/2026-04-22-deep-asset-class-edge-analysis.md).
    # n=4741 closed picks, 29.7% WR, -810.12% cumulative PnL. Single largest
    # alpha destroyer in the entire closed ledger. Already blacklisted in
    # config.py, scanner.py, smart_picks_engine.py, auto_tuner.py, etc. but
    # was missing from the canonical _RETIRED_STRATEGIES set, allowing it to
    # slip through code paths that only check strategy_blocklist.is_blocked_strategy().
    "quan_engine_scalp",
    # 2026-04-22: inverse_quan_engine_scalp is the inverse mutation of the
    # parent quan_engine_scalp. The parent is retired (n=4741, 29.7% WR,
    # -810% PnL). The inverse mutation inherits the same toxic signal source.
    # Already blocked in quality_gates.py line 1075 but missing from the
    # canonical _RETIRED_STRATEGIES. Block here for defense-in-depth.
    "inverse_quan_engine_scalp",
    # 2026-04-22: enhanced_ml_A_xgboost retired after deep asset-class edge analysis.
    # 28% WR, PF 0.42, 189 picks, 0% winning days. Already in quality_gates
    # BLOCKED_STRATEGIES and forward_degradation_tracker but NOT in the
    # canonical blocklist. 24 active picks were leaking through code paths
    # that only check is_blocked_strategy().
    "enhanced_ml_A_xgboost",
    # 2026-05-02: cftc_cot_commercial_signal retired per 48h code review
    # (updates/2026-05-02-48h-code-review.md Finding #4). PR #542 drill-down:
    #   - 27/27 closed rows on COMMODITY_BLACKLIST symbols (CT=F, CL=F)
    #   - 23/24 on single ticker (CT=F cotton)
    #   - Wins clustered on one date (2026-04-28) at suspiciously similar %
    #   - Post-PR #535 blacklist, 0% of emitted candidates reach active book
    #   - Current active_raw: 3 picks, ALL on blacklisted symbols (CL=F, CT=F, ZW=F)
    # Strategy is CFTC-specific (Commitments of Traders) — commodity-only by
    # design. With its entire candidate universe blacklisted, it burns compute
    # every cycle for zero reachable picks. Kill until rewired to HG=F/PL=F.
    # Rollback: set CFTC_COT_KILL_DISABLED=1 to bypass.
    "cftc_cot_commercial_signal",
    # 2026-06-02: justin_breakout_volume_v2 retired after M-107 mutation hunt
    # (tools/mutation_hunt_2026-06-01.py + reports/mutation_hunt_2026-06-01.json).
    # Rigorous backtest: n=12658, WR 64.6%, PF 1.024, PF_LB95 0.982, DSR 0.12.
    # WR looks great but winners < losers (asymmetric payoff destroys edge).
    # All 4 mutation axes tested: inversion worse (PF 0.988), cross-asset
    # skipped (out of budget), parameter grid winners DSR=0 (Bailey-LdP
    # variance check failed on heavy-tailed n=730), hold-extension marginal
    # (96h PF 1.014). 0 T3-passing mutations. CLAUDE.md killbox protocol
    # satisfied. Prior "BT PF 2.5" claim was a measurement artifact — that
    # PF came from an opportunistic source_table query, not rigorous replay.
    "justin_breakout_volume_v2",
    # 2026-06-02: keltner_bounce (baseline mult=2.0) retired after M-107
    # mutation hunt. Rigorous 1y 1h backtest: n=2661, WR 43.6%, PF 0.995,
    # PF_LB95 0.934, DSR 0.008. Negative Sharpe -0.126. SL_HIT 1458 vs
    # TP_HIT 1063 dominates. Prior "BT PF 8.4" claim was a measurement
    # artifact (opportunistic query). The wider-band mutation
    # `keltner_bounce_v2_wide` (mult=3.0) DID pass T3 (PF 1.145, DSR 7.88,
    # n=677) and is wired separately as a paper-pilot strategy via
    # alpha_engine/dormant_winners_wrappers.py — that variant is NOT
    # affected by this block (exact-match is_blocked_strategy lookup).
    "keltner_bounce",
    # 2026-06-02: mega_mutation retired after forward-edge audit + sign-coherence
    # check found 141 rows with stored pnl_pct signs opposite to recomputed
    # (entry/exit/direction). The reported "CRYPTO T2 edge" (forward PF 3.33,
    # WR 65.4%, n=283) was a measurement artifact: after recomputing pnl from
    # prices, true cohort is PF 0.67, WR 36.8%, avg pnl -0.94%.
    # Evidence:
    #   - reports/sign_coherence_2026-06-02.json (367 total flips, mega 141)
    #   - audit_trail/sign_coherence_check.py (PR #431, read-only diagnostic)
    # The strategy is emitter-only (alpha_engine/isolated_signal_integrator.py
    # reads genome/data/mega_mutation_picks.json upstream). No backtest replay
    # path exists, so the bug cannot be fixed at the strategy level — must
    # be fixed at the genome -> trading_picks ingest path. Hard-retire until
    # the upstream JSON ingest writes correctly-signed pnl_pct.
    "mega_mutation",
    # 2026-06-02: genome_mega_mutation is the production source_system the
    # isolated_signal_integrator stamps onto the mega_mutation upstream JSON.
    # Same root cause as the bare 'mega_mutation' tag — block both names so
    # neither slip through is_blocked_strategy lookups.
    "genome_mega_mutation",
    # 2026-06-02: kimi_signal_tracking re-retired after sign-coherence check
    # found 142 sign-flipped rows — the WORST OFFENDER in the 367-flip
    # dataset (38.7% of all flips). Previously blocked then UNBLOCKED on
    # 2026-05-16 (per audit_trail/quality_gates.py:1926 comment claiming
    # "n=22, WR=18.2%, PF=0.20 (old)"), but the unblock did NOT address the
    # sign-flip root cause — it just used the apparent post-fix WR as
    # justification. With sign-flips, true PF is 0.48 / WR 22.9%, not the
    # forward-reported PF 2.46 / WR 72.7%. No new emissions since 2026-03-29
    # so this is defense-in-depth against accidental re-activation; the
    # composite (kimi_signal_tracking, default) block at line 210 remains
    # in force but only catches the FOREX-on-default-strategy combo. This
    # entry catches the bare strategy name lookup.
    "kimi_signal_tracking",
    # 2026-06-05: auto-killed by strategy_kill_switch.py
    # n=647 WR=35.39% avg_pnl=-0.752812% total_pnl=-487.0695%  reasons=wr_below_floor, total_pnl_destroyed
    "futures_momentum",
    # n=100 WR=19.0% avg_pnl=-1.428167% total_pnl=-142.8167%  reasons=wr_below_floor, total_pnl_destroyed
    "cta_cross_asset_tsmom",
    # n=103 WR=40.78% avg_pnl=-7.208242% total_pnl=-742.4489%  reasons=avg_pnl_below_floor, total_pnl_destroyed
    "ensemble",
    # n=54 WR=18.52% avg_pnl=-1.074074% total_pnl=-58.0%  reasons=wr_below_floor
    "MomentumEMA",
    # n=747 WR=42.17% avg_pnl=-0.178155% total_pnl=-133.0815%  reasons=total_pnl_destroyed
    "forex_rsi2_mean_reversion",
    # n=491 WR=36.86% avg_pnl=0.16641% total_pnl=81.7075%  reasons=wr_below_floor
    "ig_contrarian_sentiment",
    # n=476 WR=39.71% avg_pnl=0.050824% total_pnl=24.1924%  reasons=wr_below_floor
    "myfxbook_retail_contrarian",
    # n=154 WR=7.79% avg_pnl=5.03483% total_pnl=775.3638%  reasons=wr_below_floor
    "forex_carry_momentum",
    # n=55 WR=38.18% avg_pnl=-0.071695% total_pnl=-3.9432%  reasons=wr_below_floor
    "fx_smart_carry_trade_momentum",
})

# Composite (system, strategy) pairs that are toxic only in a specific combo.
# Use is_blocked_pick() to check — do not add generic strategy names here.
# 2026-04-19: kimi_signal_tracking/default on FOREX pairs. Verified from
# live /audit dashboard:
#   n=158 resolved, WR 30.4%, avg -6.17%/trade, total -974.66%
#   USDCHF=X: 8W/27L = 22.9% WR, -441.77% PnL
#   AUDJPY=X: 0W/18L = 0.0% WR, -208.60% PnL  (deterministic-loser pattern)
#   NZDJPY=X: 1W/16L = 5.9% WR, -204.47% PnL
# Accounts for 98% of the entire FOREX asset-class bleed (-816% of -833%).
# Blocking this flips FOREX aggregate from -816% to +17%.
# See docs/STRATEGY_SUMMARY_BY_ASSET_CLASS_EXTENSIVE_2026_04_19.md.
_RETIRED_SYSTEM_STRATEGY_PAIRS = frozenset({
    ("kimi_signal_tracking", "default"),
    # 2026-04-20: copy_hl_lb_None is already in _RETIRED_STRATEGIES, but
    # still emitted 233 closed picks through copy_trader_intel (n=233,
    # total -766%) and 45 through alpha_engine (-40%) in the current
    # window. Composite pair added for defense-in-depth so emitters
    # that bypass is_blocked_strategy(name) but pass through
    # is_blocked_pick(pick) get caught. See
    # docs/AUDIT_ADDITIONAL_FIXES_2026_04_20.md Finding #2.
    ("copy_trader_intel", "copy_hl_lb_None"),
    ("alpha_engine", "copy_hl_lb_None"),
    # 2026-04-29: rapid_fire x macd_rsi_confluence — surgical kill per
    # round 2 4-AI panel unanimous P0 (5/5 concurrence). This single
    # composite is the single largest contributor to BANNED-tier closures:
    #   n=133 closed picks (CRYPTO only, 100% LONG)
    #   100% BANNED trust_tier (133/133)
    #   WR 36.8%, sum pnl_pct -48.88%, avg -0.367% / trade
    #   Accounts for ~39% of all BANNED-tier closures system-wide
    # Mutation analysis (per docs/MUTATION_THREE_AXIS_PROTOCOL.md):
    #   - Direction axis: 100% LONG, 0 SHORT — no inverse evidence base.
    #   - Symbol axis: top 10 symbols (XAUTUSDT, XRPUSDT, ORDIUSDT, LINKUSDT,
    #     SOLUSDT, LTCUSDT, DOGEUSDT, ZECUSDT, APTUSDT, TAOUSDT) all n<=7;
    #     individual "winners" (LTCUSDT/ZECUSDT/APTUSDT/TAOUSDT 75% WR) are
    #     n=4 each — multi-comparison risk per panel Bonferroni caveat.
    #   - Timeframe axis: all picks have timeframe=None — no slice possible.
    # Mutation NOT viable: no SHORT data, no TF data, symbol "winners" are
    # cherry-picks. Surgical kill is the right escalation per
    # docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md (Stage-5 hard block when
    # rehab axes are unavailable, not just untested).
    # Investigation: reports/strategy_kill_rapid_fire_macd_rsi_confluence_2026_04_29.md
    # Round 2 panel synthesis: reports/ai_round2_synthesis_2026_04_29.md
    # Rollback: set env RAPID_FIRE_MACD_KILL_DISABLED=1 to bypass (off by
    # default — hard-block active).
    ("rapid_fire", "macd_rsi_confluence"),
    # 2026-04-29: rapid_fire x rsi_bounce — Phase 2-A CRYPTO panel 8/8
    # unanimous "kill / quarantine rapid_fire source" (Accepted). PR #509
    # already retired the macd_rsi_confluence sibling pair (n=133, sum
    # -48.88%); this is the second of the two remaining rapid_fire
    # composites. Closed-pick evidence (audit_dashboard/data/dashboard_data.json
    # snapshot 2026-04-29):
    #   n=23 closed picks (CRYPTO only, 100% LONG)
    #   100% BANNED trust_tier (23/23)
    #   WR 47.8%, sum pnl_pct -11.37%, avg -0.494% / trade
    # All three rehab axes blocked -> Stage-5 hard block per
    # docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md.
    # Investigation: reports/strategy_kill_rapid_fire_rsi_bounce_2026_04_29.md
    # Rollback: set env RAPID_FIRE_RSI_BOUNCE_KILL_DISABLED=1 to bypass.
    ("rapid_fire", "rsi_bounce"),
    # 2026-05-18: rapid_fire × volume_spike_breakout — C-006 backtest verdict.
    # n=78 closed CRYPTO picks, WR=16.7%, PF=0.014, cumPnL=-30.87%.
    # Root cause: buying volume spikes in CRYPTO is adverse-selection (retail FOMO
    # catches pump peak; professional capital on other side). Wins are tiny (+0.04% max),
    # losses up to -2.5% per pick — win/loss ratio 0.072. All 3 rehab axes blocked.
    # Investigation: reports/C006_rapid_fire_backtest_2026_05_18.md
    # Rollback: set env RAPID_FIRE_VSB_KILL_DISABLED=1 to bypass.
    ("rapid_fire", "volume_spike_breakout"),
    # 2026-05-18: rapid_fire × stochrsi_macd_combo — C-006 second-pass autopsy.
    # n=17 closed CRYPTO picks, WR=11.8%, PF=0.200, cumPnL=-0.24%.
    # Insufficient n for full three-axis mutation analysis, but WR=11.8% is below
    # NOISE floor (needs WR≥40% to justify "watch" status). n too small to rescue.
    # Reference: reports/C006_rapid_fire_backtest_2026_05_18.md
    # Rollback: set env RAPID_FIRE_STOCHRSI_KILL_DISABLED=1 to bypass.
    ("rapid_fire", "stochrsi_macd_combo"),
    # 2026-04-29: goldmine_stocks source on EQUITY — surgical kill per
    # orchestrator + Copilot cross-check (reports/COPILOT_CROSS_CHECK_2026_04_29.md).
    # Closed-pick evidence: n=13 EQUITY (100% LONG), WR 0.0%,
    # sum pnl_pct -53.36%, avg -4.10%/trade. All three consensus tiers
    # (5x/6x/7x) are 0% WR; higher-confluence "7x" lost MORE than lower —
    # signal itself is broken. Stage-5 hard block per protocol.
    # Investigation: reports/strategy_kill_goldmine_stocks_2026_04_29.md
    # Rollback: set env GOLDMINE_STOCKS_KILL_DISABLED=1 to bypass.
    ("goldmine_stocks", "goldmine_5x_consensus"),
    ("goldmine_stocks", "goldmine_6x_consensus"),
    ("goldmine_stocks", "goldmine_7x_consensus"),
})

# 2026-04-19: 6 strategies landed on main from 2 different Copilot PRs
# without passing Strategy Factory v1.1 gate (S0 hypothesis, S1 backtest,
# S2 OOS, S3 Monte Carlo, S4 forward paper). Paper-flagging until validated.
# Revive by removing entry here AFTER:
#   - docs/hypotheses/<strategy>.md with falsifiable claims
#   - backtest_results/<strategy>_IS.json with Sharpe > 1.0 and realistic costs
#   - 50 resolved forward-paper trades OR 30-day calendar (whichever first)
#   - Wilson LB > 50% with Bonferroni correction
# See docs/STRATEGY_FACTORY_V1_1_AMENDMENTS.md for full ladder.
_PAPER_ONLY_STRATEGIES = frozenset({
    # PR #256 (branch copilot/add-integration-strategies) - ARE/RC/SWEEP
    # Volume threshold 1.15x is below normal breakout bar (1.5-2x); RC RSI
    # upper 78 buys into overbought territory; no OOS or calibration data.
    "ARE_LONG",
    "RC_LONG",
    "SWEEP_SHORT",
    # Commit 90c88b53c7 - 3 more strategies added same day, same pattern.
    # Classic pattern detectors (squeeze breakout, MACD+OBV, Fibonacci RSI)
    # with no backtest data in the commit.
    "bollinger_squeeze_stochastic_breakout",
    "macd_obv_momentum",
    "fibonacci_rsi_mean_reversion",
    # 2026-04-19: ETF-1 Intermarket-Flow-Scout flagged by DeepSeek-v3.1:671b
    # peer review: "Recent 85% WR vs all-time 52.2% is a red flag for
    # overfitting. Immediately paper-trade only until it passes full S1-S3."
    # Currently wired live in backtest-and-deploy.yml workflow but lacks
    # hypothesis doc, formal backtest, and Monte Carlo validation.
    # Lives at KIMI_RISEOFTHECLAW/live_scanner.py:1525-4413.
    "intermarket-flow-scout",
    "intermarket_flow_scout",
    # 2026-04-19: PR #256 (copilot/add-integration-strategies) — 20 new
    # strategies across alpha_engine/{bond,etf,forex,futures}_strategies.py,
    # no v1.1 gate validation. Paper-flag per Cloud Agent's named list.
    # 2026-05-03: UNBLOCKED — bond strategies with FRED data integration.
    # Phase 3 remediation. These use bond_data_fred.py for macro signals.
    # Paper-trade first, graduate to live after 2 weeks of positive PF.
    # "bond_credit_spread", "bond_inflation_breakeven", "bond_high_yield_rotation",
    # "bond_term_premium", "bond_curve_steepener", "bond_vol_regime_mr",
    "silver_gold_ratio_breakout",
    "futures_rsi_divergence", "futures_overnight_gap", "futures_dollar_trend",
    "futures_equity_seasonality", "futures_macd_momentum", "futures_metals_momentum",
    "etf_volatility_target", "etf_small_cap_premium", "etf_gold_miners_ratio",
    "etf_equal_weight_rotation", "etf_emerging_market_momentum",
    # 2026-05-03: UNBLOCKED — forex strategies with session-aware features.
    # Phase 3 remediation. kimi_signal_tracking was the real poison (still blocked).
    # These use RSI/stochastic/USD-index signals — fundamentally different from kimi.
    # "stochastic_mean_reversion_forex", "forex_stochastic_mr",
    # "usd_index_trend_forex", "forex_usd_trend",
    # 2026-04-19: PR #265 — commodity range-position reversion, no S2/S3/S4
    "commodity_range_position_reversion",
    # 2026-05-03: BANNED — cta_commodity_momentum_term PF 0.02, 58% flat exits.
    # Proven toxic per FOOLPROOF_ACTION_PLAN.docx and ROOT_CAUSE_ANALYSIS.
    # Replace with triple-screen (momentum + term structure + volatility).
    "cta_commodity_momentum_term",
    # 2026-04-19: PR #262 — 10 baby strategies, backtest-only evidence
    "mfi_extreme_reversion", "cmo_extreme_reversion",
    "keltner_fresh_break_reversion", "aroon_oscillator_reversal",
    "crypto_elders_ray_bear_power", "equity_rsi2_volume_confirmed",
    "price_sma_deviation_reversion", "stochastic_slow_extreme_reversion",
    "trix_extreme_reversion", "daily_range_extreme_reversion",
    # 2026-04-19: Gemini walkthrough decay analysis — rolling 7d WR < 35% with
    # large sample size (n>=10) and >20pp drop from all-time baseline. Paper-flag
    # pending rehab per STRATEGY_INVESTIGATION_BEFORE_KILL.md escalation ladder.
    # NOTE: st_fear_greed_contrarian was promoted to _RETIRED_STRATEGIES on
    # 2026-04-20 after 640 closed picks confirmed catastrophic baseline
    # performance (see entry above in _RETIRED_STRATEGIES).
    # NOTE: st_obv_support_divergence was promoted to _RETIRED_STRATEGIES on
    # 2026-04-20 after persistent negative contribution (see entry above).
    # crypto_mtf_ema_slope_alignment_v1: 9.1% WR n=11
    "crypto_mtf_ema_slope_alignment_v1",
    # 2026-04-19: GitHub Copilot audit converged with Kimi + Cursor + Claude: high-score/low-PnL
    # cohort (n=395, total -1911.6%) is dominated by copy_trader_intel/copy_hl_lb_None at n=143
    # avg -11.34%/trade. copy_hl_lb_None is already RETIRED (hard-block). copy_hl_whale shares
    # the same copy-trader lineage with no S2/S4 evidence — paper-flag defensively.
    "copy_hl_whale",
    # 2026-04-19: Kimi Code fact-check — luxalgo_confluence appears in every
    # toxic consensus combo with n>=5. luxalgo_confluence + st_obv_support_divergence
    # = 8.3% WR n=12. See .planning/md_review/script_fact_check_feedback.md.
    # 2026-04-29: REMOVED per Near-Miss Deep-Dive panel (3-AI unanimous,
    # reports/NEAR_MISS_DEEP_DIVE_2026_04_29.md). Standalone metrics:
    #   n=205, WR 52.2%, PF 1.66 — already past Tier 2 PF>=1.5 threshold.
    #   Already past PROVEN n>=200 floor (Q6=B graduated thresholds).
    #   Symmetric LONG/SHORT (52.4%/52.0%) + 73 TP / 73 SL split + win/loss
    #   magnitude asymmetry (2.21%/1.45% = 1.52x) confirms real edge.
    # The Apr-19 rationale was a CONSENSUS-COMBO observation, not a
    # standalone kill — and its partner `st_obv_support_divergence` has
    # already been retired (see _RETIRED_STRATEGIES above). With the toxic
    # partner gone, luxalgo_confluence's standalone PROVEN metrics surface.
    # If consensus-combo toxicity returns, re-add as a composite-pair entry
    # in _BLOCKED_SOURCE_STRATEGY_PAIRS, not a strategy-wide kill.
    # 2026-04-19: feat/golden-combos-across-assets proposed Golden Combo super-picks
    # at 0.80-0.95 confidence from small-n consensus mining. Some combos claim
    # PF=inf / 100% WR (zero losing trades = n likely <10). Mercury BH-FDR on
    # 45 parallel tests: zero clearing 5% FDR. Kimi fact-check confirmed the
    # mine_consensus_edge.py math is broken (sums averaged %s). Paper-flag until
    # S2 walk-forward + n-disclosure + BH-FDR gate clears.
    "golden_combo_crypto_quan_rsi",
    "golden_combo_equity_quality_rs",
    "golden_combo_forex_rsi_ema",
    "golden_combo_commodity_tsmom",
    "golden_combo_crypto_choppiness_quan",
})

# Legacy symbol kept for any caller still importing it.
_BLOCKED_STRATEGIES = _RETIRED_STRATEGIES | _PAPER_ONLY_STRATEGIES


def is_blocked_strategy(name, asset_class: str = "") -> bool:
    """Return True if the strategy name is retired, paper-only, FX-killed, or
    COMMODITY-inverse-killed."""
    if not name:
        return False
    s = str(name).strip().casefold()  # P0 §15 Trap #1 — case-insensitive matching
    # Check both casefolded and original for backward compat with mixed-case DB entries
    s_orig = str(name).strip()
    if s in {k.casefold() for k in _BLOCKED_STRATEGIES} or s_orig in _BLOCKED_STRATEGIES:
        return True
    # FX Kill Switch: dynamic FOREX strategy kills
    if is_fx_killed_strategy(s) or is_fx_killed_strategy(s_orig):
        return True
    # COMMODITY Inverse Kill Switch
    if is_commodity_inverse_killed_strategy(s, asset_class=asset_class) or is_commodity_inverse_killed_strategy(s_orig, asset_class=asset_class):
        return True
    return False


def block_reason(name, asset_class: str = "") -> str:
    """Return why a strategy is blocked: 'retired', 'paper-only', 'fx-kill',
    'commodity-inverse-kill', or ''."""
    if not name:
        return ""
    s = str(name).strip().casefold()
    s_orig = str(name).strip()
    if s in {k.casefold() for k in _RETIRED_STRATEGIES} or s_orig in _RETIRED_STRATEGIES:
        return "retired"
    if s in {k.casefold() for k in _PAPER_ONLY_STRATEGIES} or s_orig in _PAPER_ONLY_STRATEGIES:
        return "paper-only"
    if is_fx_killed_strategy(s) or is_fx_killed_strategy(s_orig):
        return "fx-kill"
    if is_commodity_inverse_killed_strategy(s, asset_class=asset_class) or is_commodity_inverse_killed_strategy(s_orig, asset_class=asset_class):
        return "commodity-inverse-kill"
    return ""


def _rapid_fire_macd_kill_active() -> bool:
    """Return True iff the ("rapid_fire","macd_rsi_confluence") kill is hot.

    Default: True (kill active). Set env RAPID_FIRE_MACD_KILL_DISABLED=1 to
    bypass for rollback / investigation. Any non-empty truthy value disables
    the kill; falsy / unset / "0" / "false" keeps it active.
    """
    flag = (os.environ.get("RAPID_FIRE_MACD_KILL_DISABLED") or "").strip().lower()
    if flag in ("1", "true", "yes", "on"):
        return False
    return True


def _rapid_fire_rsi_bounce_kill_active() -> bool:
    """Return True iff the ("rapid_fire","rsi_bounce") kill is hot.

    Default: True (kill active). Set env RAPID_FIRE_RSI_BOUNCE_KILL_DISABLED=1
    to bypass for rollback / investigation.
    """
    flag = (os.environ.get("RAPID_FIRE_RSI_BOUNCE_KILL_DISABLED") or "").strip().lower()
    if flag in ("1", "true", "yes", "on"):
        return False
    return True


def _rapid_fire_vsb_kill_active() -> bool:
    """Return True iff the ("rapid_fire","volume_spike_breakout") kill is hot.

    Default: True (kill active). Set env RAPID_FIRE_VSB_KILL_DISABLED=1 to
    bypass for rollback / investigation.
    """
    flag = (os.environ.get("RAPID_FIRE_VSB_KILL_DISABLED") or "").strip().lower()
    if flag in ("1", "true", "yes", "on"):
        return False
    return True


def _rapid_fire_stochrsi_kill_active() -> bool:
    """Return True iff the ("rapid_fire","stochrsi_macd_combo") kill is hot.

    Default: True (kill active). Set env RAPID_FIRE_STOCHRSI_KILL_DISABLED=1 to
    bypass for rollback / investigation.
    """
    flag = (os.environ.get("RAPID_FIRE_STOCHRSI_KILL_DISABLED") or "").strip().lower()
    if flag in ("1", "true", "yes", "on"):
        return False
    return True


def _goldmine_stocks_kill_active() -> bool:
    """Return True iff the goldmine_stocks composite kills are hot.

    Default: True (kill active). Set env GOLDMINE_STOCKS_KILL_DISABLED=1 to
    bypass for rollback / investigation.
    """
    flag = (os.environ.get("GOLDMINE_STOCKS_KILL_DISABLED") or "").strip().lower()
    if flag in ("1", "true", "yes", "on"):
        return False
    return True


_GOLDMINE_STOCKS_KILLED_PAIRS = frozenset({
    ("goldmine_stocks", "goldmine_5x_consensus"),
    ("goldmine_stocks", "goldmine_6x_consensus"),
    ("goldmine_stocks", "goldmine_7x_consensus"),
})



def _pair_is_blocked(sys_name: str, strat: str) -> bool:
    """Composite-pair blocklist check honoring per-pair rollback flags."""
    pair = (sys_name, strat)
    if pair not in _RETIRED_SYSTEM_STRATEGY_PAIRS:
        return False
    # Per-pair rollback flags
    if pair == ("rapid_fire", "macd_rsi_confluence") and not _rapid_fire_macd_kill_active():
        return False
    if pair == ("rapid_fire", "rsi_bounce") and not _rapid_fire_rsi_bounce_kill_active():
        return False
    if pair == ("rapid_fire", "volume_spike_breakout") and not _rapid_fire_vsb_kill_active():
        return False
    if pair == ("rapid_fire", "stochrsi_macd_combo") and not _rapid_fire_stochrsi_kill_active():
        return False
    if pair in _GOLDMINE_STOCKS_KILLED_PAIRS and not _goldmine_stocks_kill_active():
        return False
    return True


def is_blocked_pick(pick) -> bool:
    """Return True if the pick should be blocked, checking both strategy name
    and system-strategy composite pairs.

    Accepts a pick dict with optional 'strategy' and 'source_system' fields."""
    if not isinstance(pick, dict):
        return False
    strat = str(pick.get("strategy") or "").strip()
    sys_name = str(pick.get("source_system") or "").strip()
    if is_blocked_strategy(strat):
        return True
    if _pair_is_blocked(sys_name, strat):
        return True
    return False


def pick_block_reason(pick) -> str:
    """Return the reason a pick is blocked, or ''."""
    if not isinstance(pick, dict):
        return ""
    strat = str(pick.get("strategy") or "").strip()
    sys_name = str(pick.get("source_system") or "").strip()
    r = block_reason(strat)
    if r:
        return r
    if _pair_is_blocked(sys_name, strat):
        return "retired-composite"
    return ""
