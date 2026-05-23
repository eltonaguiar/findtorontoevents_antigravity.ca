"""
Publish comprehensive hedge-fund findings to Redis Bus.
Run once after all analysis is complete.
"""
import redis
import json
from datetime import datetime

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

KEY = 'HEDGE_FUND_ENHANCEMENT_COMPREHENSIVE_2026-04-06'

msg = {
    "type": KEY,
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "author": "copilot-agent",
    "session": "2026-04-06 hedge-fund quality uplift",
    "report_file": "docs/EDGE_FLAW_ANALYSIS_2026-04-06.md",
    "engine_file": "alpha_engine/smart_picks_engine.py",
    "last_commit": "7bb6b497b0",

    # ===================== IC SCORECARD =====================
    "ic_by_asset_class": {
        "CRYPTO": {
            "n": 2855,
            "win_rate_pct": 48.51,
            "mean_pnl_pct": 0.221,
            "smart_score_spearman": 0.259,
            "elite_score_spearman": 0.072,
            "score_quartile_spread_pp": 25.54,
            "best_predictor": "smart_score",
            "action": "Use smart_score as primary ranker for crypto; elite is near-worthless (rho=0.072)"
        },
        "EQUITY": {
            "n": 471,
            "win_rate_pct": 35.46,
            "mean_pnl_pct": -0.779,
            "smart_score_spearman": 0.217,
            "elite_score_spearman": 0.346,
            "score_quartile_spread_pp": 36.98,
            "best_predictor": "elite_score",
            "action": "Elite score best predictor BUT universe bleeds at -0.779% mean — needs strategy allowlist tightening BEFORE score upgrade"
        },
        "FOREX": {
            "n": 147,
            "win_rate_pct": 31.29,
            "mean_pnl_pct": -0.279,
            "smart_score_spearman": 0.127,
            "elite_score_spearman": 0.097,
            "confidence_spearman": -0.088,
            "score_quartile_spread_pp": 29.86,
            "best_predictor": "none_reliable",
            "action": "FOREX cannot be scored reliably with current signals. Conf inverted (rho=-0.088). Needs momentum/carry features or full ban."
        },
        "COMMODITY": {
            "n": 12,
            "win_rate_pct": 8.33,
            "mean_pnl_pct": -0.697,
            "note": "Sample too small (n=12) for IC — catastrophic WR, recommend pause until n>100"
        },
        "ETF": {
            "n": 12,
            "win_rate_pct": 41.67,
            "mean_pnl_pct": -0.951,
            "note": "Sample too small (n=12)"
        },
        "FUTURES": {
            "n": 3,
            "win_rate_pct": 0.0,
            "mean_pnl_pct": -0.449,
            "note": "Sample too small (n=3) — 0% WR, suspend"
        }
    },

    # ===================== IC GLOBAL RANKING =====================
    "global_ic_ranking": [
        {"rank": 1, "metric": "elite_score", "slice": "non_crypto", "spearman": 0.345},
        {"rank": 2, "metric": "score",       "slice": "non_crypto", "spearman": 0.283},
        {"rank": 3, "metric": "smart_score", "slice": "crypto",     "spearman": 0.234},
        {"rank": 4, "metric": "ml_composite","slice": "all",        "spearman": 0.208},
        {"rank": 5, "metric": "confidence",  "slice": "crypto",     "spearman": 0.188}
    ],

    # ===================== VERIFIED ALPHA =====================
    "verified_alpha_summary": {
        "active_va_count": 51,
        "smart_picks_va_count": 0,
        "realized_closed_n": 2552,
        "realized_win_rate_pct": 49.1,
        "realized_total_pnl_pct": 550.72,
        "realized_expectancy": 0.22,
        "audited_avg_wr_pct": 61.2,
        "audited_weighted_wr_pct": 49.8,
        "audited_median_wr_pct": 57.5,
        "note": "VA pool 49.1% WR vs all-systems 27-38% — VA is the signal, not the noise"
    },

    # ===================== ACTIVE BOOK SNAPSHOT =====================
    "active_book_snapshot": {
        "active_count": 58,
        "unrealized_sum_pct": -21.26,
        "unrealized_mean_pct": -0.367,
        "strategies_with_proven_history": [
            {"strategy": "st_fear_greed_contrarian", "n_closed": 434, "win_rate_pct": 80.88, "mean_pnl_pct": 1.28},
            {"strategy": "quan_engine",              "n_closed": 1037, "win_rate_pct": 40.41, "mean_pnl_pct": 0.053},
            {"strategy": "enhanced_ml_A_xgboost",   "n_closed": 124,  "win_rate_pct": 29.03, "mean_pnl_pct": -0.548}
        ],
        "zero_history_strategies_count": 20,
        "zero_history_strategies": [
            "BTC 4H RSI+MACD Confluence", "breakout_b_ml", "btc-4h-rsi-macd-scout",
            "contrarian_consensus_flip", "kalshi_mtf_consensus", "pm_consensus_high_conviction",
            "pm_whale_0xcc500c", "prediction_market_consensus", "regime_terminal",
            "tsmom_volscaled", "super signal (strong) via claude_gainer_st",
            "super signal (super) via kimi"
        ],
        "action": "20 of 28 active strategies have 0 closed-pick history — these are flying blind. Apply extra conf floor or quarantine."
    },

    # ===================== ENGINE CHANGES (THIS SESSION) =====================
    "engine_changes_committed": {
        "commit": "7bb6b497b0",
        "changes": [
            {
                "id": "BAN-01",
                "type": "strategy_ban",
                "details": "Banned proven_triple_ema_prop (14.0% WR / 980 picks) + proven_propfirm_cons_prop (17.0% WR / 1088 picks)",
                "impact": "Removes ~2000 losers from entry pipeline"
            },
            {
                "id": "BAN-02",
                "type": "symbol_blocklist",
                "details": "Added JTOUSDT (0% WR / 15 picks) to SYMBOL_BLOCKLIST",
                "impact": "Hard block on systematic loser"
            },
            {
                "id": "BOOST-01",
                "type": "proven_winner_promotion",
                "details": "volume_profile_deviation promoted to PROVEN_WINNERS (55.8% WR / 129 picks, boost=+10)",
                "impact": "Surfaces a credible edge"
            },
            {
                "id": "FLOOR-01",
                "type": "confidence_floor",
                "details": "SCALP confidence floor raised 0.65 -> 0.70 (0.65-0.70 band was 14.2% WR on 928 picks)",
                "impact": "Cuts worst SCALP entries"
            },
            {
                "id": "STEP-16",
                "type": "dow_scoring",
                "details": "Day-of-week adjustments: Mon=-7, Thu=-10, Sun=-7, Tue=+8, Wed=+6 pts; SWING+Tue=+15; SWING+Sun=hard_block",
                "data": "Based on 3,223-pick corpus: Wed=33.6%WR, Tue SWING=12/12 wins; Thu=21.9%, Sun=22.8%"
            },
            {
                "id": "STEP-17",
                "type": "position_mode_block",
                "details": "POSITION mode hard blocked (0/13 wins historically)",
                "impact": "Eliminates entire losing mode class"
            },
            {
                "id": "MODE-INF",
                "type": "mode_inference",
                "details": "Added mode inference fallback from strategy keywords + TP distance (<1.5%=SCALP, >=3%=SWING)",
                "impact": "Fixes silent no-op bug where mode-aware filters never applied"
            }
        ]
    },

    # ===================== TOP EDGES =====================
    "top_edges": [
        {"id": "E1", "finding": "st_fear_greed_contrarian: 80.88% WR on 434 picks, mean +1.28% — institutional-grade alpha", "priority": "P0"},
        {"id": "E2", "finding": "SWING Tuesday: 12/12 historical wins (100%) — add hard qualifier", "priority": "P0"},
        {"id": "E3", "finding": "CRYPTO smart score Q5-Q1 spread = +38.71 pp WR — score works for crypto", "priority": "P1"},
        {"id": "E4", "finding": "Confidence >=0.80: best decile by WR; conf 0.80+ cohort should get premium sizing", "priority": "P1"},
        {"id": "E5", "finding": "volume_profile_deviation: 55.8% WR / 129 picks — proven asymmetric edge", "priority": "P1"},
        {"id": "E6", "finding": "Verified Alpha realized 49.1% WR vs headline 27-38% — sourcing from VA is highest leverage action", "priority": "P0"}
    ],

    # ===================== TOP FLAWS =====================
    "top_flaws": [
        {"id": "F1", "finding": "EQUITY mean PnL = -0.779% (n=471) — entire universe bleeds despite scoring; strategy universe must be purged", "priority": "P0"},
        {"id": "F2", "finding": "FOREX conf spearman = -0.088 (inverted!); score spearman = 0.017 — FOREX is unscorable", "priority": "P0"},
        {"id": "F3", "finding": "20/28 active strategies have zero closed-pick history — flying blind", "priority": "P0"},
        {"id": "F4", "finding": "COMMODITY/FUTURES/ETF pools (n=3-12) — stats meaningless, all bleeding; suspend until n>100", "priority": "P1"},
        {"id": "F5", "finding": "64.8% of picks from PROBATION tier (Kimi finding) — score-to-tier graduation logic broken", "priority": "P1"}
    ],

    # ===================== PENDING IMPLEMENTATION (BACKLOG) =====================
    "pending_backlog": [
        {"id": "B6", "title": "Verified Alpha 4h+daily+weekly confluence gate"},
        {"id": "B7", "title": "VaR risk-parity position sizing"},
        {"id": "C4", "title": "Alt data factors: funding rate (<-0.05% = high-certainty long), on-chain netflow"},
        {"id": "C5", "title": "Monte Carlo gate before VA graduation"},
        {"id": "D1", "title": "TCA + alpha decay scoring"},
        {"id": "A5", "title": "Regime detection integration (regime_terminal strategy already live but unproven)"}
    ],

    "kimi_plan_summary": {
        "source": "ANTIGRAVITY_HEDGE_FUND_ENHANCEMENT_PLAN.md",
        "current_wr_range": "27-38%",
        "target_wr": "55%+",
        "profit_factor_current": 0.88,
        "profit_factor_target": 1.5,
        "key_quick_wins": [
            "MIN_SCORE=65 enforcement (partial done via conf floor)",
            "funding_rate < -0.05% + positive tech = HIGH CERTAINTY LONG",
            "Fix trust tier graduation (64.8% stuck in PROBATION)"
        ]
    },

    "next_actions": [
        "IMMEDIATE: Tighten EQUITY strategy allowlist — pick top quartile only (score Q4 WR=54% vs Q1 WR=17%)",
        "IMMEDIATE: Quarantine FOREX picks pending momentum/carry signal integration",
        "HIGH: Wire funding rate check for crypto entries (Kimi C4)",
        "HIGH: Implement trust tier graduation fix — PROBATION cap at 30% of pool",
        "MEDIUM: Add VaR risk parity sizing (B7) — position size by IC confidence per AC",
        "MEDIUM: Build closed-match validator before accepting zero-history strategies",
        "LOW: Monte Carlo gate + alpha decay (C5, D1)"
    ]
}

r.set(KEY, json.dumps(msg))
subs = r.publish('alpha_engine_bus', json.dumps(msg))
print(f"Published {KEY} -> {subs} subscribers")
print(f"Key size: {len(json.dumps(msg))} bytes")
