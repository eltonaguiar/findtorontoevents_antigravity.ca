#!/usr/bin/env python3
"""
Elton's Predictions -- Pine Script Code Generator
Reads Alpha Engine + KIMI performance data -> generates TradingView indicator

Usage:
    python generate_pine.py                 # Generate .pine file
    python generate_pine.py --dry-run       # Print stats, don't write files
    python generate_pine.py --version 2.0   # Override version number
"""

import json
import math
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone

# Import transaction cost model (for net WR calculation)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ALPHA_ENGINE"))
try:
    from transaction_costs import (
        adjusted_win_rate as _compute_net_wr,
        COST_MODELS,
    )
    _HAS_TX_COSTS = True
except ImportError:
    _HAS_TX_COSTS = False
    def _compute_net_wr(gross_wr, avg_win, avg_loss, cost): return gross_wr
    COST_MODELS = {}

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
ALPHA_DATA = ROOT / "alpha_engine" / "data"
KIMI_DATA = ROOT / "KIMI_RISEOFTHECLAW" / "data"
TEMPLATE = Path(__file__).resolve().parent / "templates" / "base.pine"
OUTPUT_PINE = Path(__file__).resolve().parent / "output" / "eltons_predictions.pine"
OUTPUT_VERSION = Path(__file__).resolve().parent / "output" / "version.json"

# ---------------------------------------------------------------------------
# Strategy definitions (index 0-19)
# ---------------------------------------------------------------------------
STRATEGY_NAMES = [
    "Connors RSI-2",
    "VIX Spike Reversal",
    "MACD Momentum",
    "EMA Crossover",
    "Ichimoku Cloud",
    "Bollinger Squeeze",
    "VWAP Reversion",
    "RSI Divergence",
    "Supertrend",
    "Swing Failure (SFP)",
    "Break of Structure",
    "Liquidation Cascade",
    "Momentum Crash",
    "Multi-Strategy Consensus",
    "Seasonal Bias",
    "Halving Cycle",
    "Turn of Month",
    "Day of Week",
    "Cycle Detection",
    "S/R Magnetism",
    "Liquidity Sweep",
    "Nonlinear TSMOM",
    "CTREND Multi-MA",
    "Flash Crash Reversal",
    "HMA Trend",
    "Fair Value Gap",
    "Keltner Squeeze",
    "Order Block",
    "Wyckoff Spring",
    "CVD Divergence",
]

# Forward-test strategy-name mapping: maps active_picks.json "strategy" field
# values to our strategy index.  Only strategies that appear in both systems
# are listed; everything else is ignored during aggregation.
FORWARD_STRATEGY_MAP = {
    "connors_rsi2":           0,
    "connors_rsi2_spy":       0,
    "connors_rsi2_qqq":       0,
    "connors_rsi2_btc":       0,
    "vix_spike_reversal":     1,
    "vix_spike":              1,
    "macd_momentum":          2,
    "spike_macd_divergence":  2,
    "ema_crossover":          3,
    "ichimoku_cloud":         4,
    "bollinger_squeeze":      5,
    "vwap_reversion":         6,
    "vwap_mean_reversion":    6,
    "rsi_divergence":         7,
    "rsi_hidden_divergence":  7,
    "supertrend":             8,
    "sfp":                    9,
    "swing_failure":          9,
    "bos":                    10,
    "break_of_structure":     10,
    "liquidation_cascade":    11,
    "liquidation_cascade_buy":11,
    "momentum_crash":         12,
    "momentum_crash_hedge":   12,
    "multi_strategy":         13,
    "consensus":              13,
    "monthly_seasonality":    14,
    "seasonal_bias":          14,
    "halving_cycle":          15,
    "halving_cycle_position": 15,
    "turn_of_month":          16,
    "turn_of_month_effect":   16,
    "day_of_week":            17,
    "day_of_week_effect":     17,
    "fourier_cycle":          18,
    "fourier_cycle_detector": 18,
    "cycle_detection":        18,
    "sr_magnetism":           19,
    "price_touch_recurrence": 19,
    "fractal_sr_bounce":      19,
    "liquidity_sweep":        20,
    "liquidity_sweep_reversal": 20,
    "nonlinear_tsmom":        21,
    "tsmom":                  21,
    "s_shaped_momentum":      21,
    "ctrend":                 22,
    "ctrend_multi_ma":        22,
    "multi_ma_composite":     22,
    "flash_crash":            23,
    "flash_crash_reversal":   23,
    "hma_trend":              24,
    "hull_ma":                24,
    "hull_moving_average":    24,
    "fvg":                    25,
    "fair_value_gap":         25,
    "keltner_squeeze":        26,
    "ttm_squeeze":            26,
    "keltner":                26,
    "order_block":            27,
    "ob_detection":           27,
    "wyckoff_spring":         28,
    "wyckoff":                28,
    "spring_upthrust":        28,
    "cvd_divergence":         29,
    "cvd_approx":             29,
    "buying_pressure":        29,
}

# ---------------------------------------------------------------------------
# Default backtest values for strategies WITHOUT real JSON backtest data
# ---------------------------------------------------------------------------
# These are placeholder estimates used when no real backtest JSON exists.
# The `proven` flag below tracks which strategies have real data.
DEFAULTS = {
    # idx: (win_rate, sharpe, p_val_str, n_trades, timeframe, method, tested_symbol)
    0: (75.7,  4.84,  "6e-06",  74,  "Daily",     "RSI(2)<5+SMA200",  "SPY"),
    1: (72.0,  6.20,  "0.022",  25,  "Daily",     "VIX>30+RSI<20",    "SPY"),
    2: (0.0,   0.00,  "N/A",     0,  "5m-1H",     "MACD cross+RSI",   "BTCUSD"),
    3: (0.0,   0.00,  "N/A",     0,  "15m-4H",    "EMA9/21 cross",    "BTCUSD"),
    4: (0.0,   0.00,  "N/A",     0,  "Daily",     "TK cross+cloud",   "BTCUSD"),
    5: (0.0,   0.00,  "N/A",     0,  "1H-4H",     "BB/KC squeeze",    "BTCUSD"),
    6: (0.0,   0.00,  "N/A",     0,  "Intraday",  "VWAP z>2 sigma",   "BTCUSD"),
    7: (0.0,   0.00,  "N/A",     0,  "1H-Daily",  "Pivot divergence", "BTCUSD"),
    8: (0.0,   0.00,  "N/A",     0,  "15m-Daily", "ATR trail flip",   "BTCUSD"),
    9: (0.0,   0.00,  "N/A",     0,  "1H-Daily",  "Wick SFP",         "BTCUSD"),
    10: (0.0,   0.00,  "N/A",     0,  "1H-Daily",  "BOS/CHOCH",        "BTCUSD"),
    11: (0.0,   0.00,  "N/A",     0,  "1H-4H",     "RSI2<10+3red+vol", "BTCUSD"),
    12: (0.0,   0.00,  "N/A",     0,  "1H-Daily",  "MomVol 2x spike",  "BTCUSD"),
    13: (0.0,   0.00,  "N/A",     0,  "Multi",     "3+ agree",         "Multi"),
    14: (0.0,   0.00,  "N/A",     0,  "Daily",     "Month bias+RSI",   "BTCUSD"),
    15: (0.0,   0.00,  "N/A",     0,  "Daily",     "Halving phase",    "BTCUSD"),
    16: (0.0,   0.00,  "N/A",     0,  "Daily",     "DOM 28-3",         "SPY"),
    17: (0.0,   0.00,  "N/A",     0,  "Daily",     "DOW best/worst",   "BTCUSD"),
    18: (0.0,   0.00,  "N/A",     0,  "Daily",     "FFT cycle phase",  "BTCUSD"),
    19: (0.0,   0.00,  "N/A",     0,  "1H-Daily",  "Pivot S/R touch",  "BTCUSD"),
    20: (73.0,  2.50,  "N/A",     0,  "1H-Daily",  "Sweep+wick revert","BTCUSD"),
    21: (0.0,   0.00,  "N/A",     0,  "Daily",     "S-shaped TSMOM",   "Multi"),
    22: (0.0,   0.00,  "N/A",     0,  "Daily-Wkly","Multi-MA composite","Multi"),
    23: (71.0,  3.20,  "N/A",     0,  "5m-1H",     "Flash crash+RSI15","BTCUSD"),
    24: (59.1,  4.45,  "0.26",   22,  "1H-Daily",  "HMA50 dir+SMA50",  "SPY"),
    25: (65.0,  0.00,  "N/A",     0,  "1H-Daily",  "FVG retrace+HTF",  "BTCUSD"),
    26: (77.0,  0.00,  "N/A",     0,  "1H-Daily",  "BB/KC squeeze+mom","SPY"),
    27: (60.0,  0.00,  "N/A",     0,  "1H-Daily",  "OB retrace+disp",  "BTCUSD"),
    28: (63.0,  0.00,  "N/A",     0,  "1H-Daily",  "Spring/upthrust",  "BTCUSD"),
    29: (0.0,   0.00,  "N/A",     0,  "1H-Daily",  "CVD price diverg", "BTCUSD"),
}

# ---------------------------------------------------------------------------
# Real backtest data sources
# ---------------------------------------------------------------------------
# Maps strategy index to a list of (json_file_relative_to_alpha_data, key_path, significance_threshold)
# A strategy is PROVEN if it has a real backtest file AND binomial_p < 0.05
BACKTEST_SOURCES = {
    # Connors RSI-2 (index 0): use SPY results from connors_rsi2_backtest.json
    0: {"file": "connors_rsi2_backtest.json", "symbol_key": "SPY"},
    # VIX Spike Reversal (index 1): top-level object
    1: {"file": "vix_spike_backtest.json", "symbol_key": None},
}
# Significance threshold for marking a strategy as PROVEN
PROVEN_P_THRESHOLD = 0.05


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_json(path: Path) -> object:
    """Load a JSON file, returning None if missing or malformed."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        print(f"  [WARN] Could not load {path}: {exc}")
        return None


def fmt_pval(val) -> str:
    """Format a p-value for display.  Returns string like '6e-06' or 'N/A'."""
    if val is None:
        return "N/A"
    if isinstance(val, str):
        return val
    if val == 0:
        return "0"
    # Use scientific notation for very small values
    if val < 0.001:
        return f"{val:.1e}"
    return f"{val:.6f}".rstrip("0").rstrip(".")


def composite_score(win_rate: float, sharpe: float, p_val_str: str) -> float:
    """
    Compute ranking score:
        score = win_rate * sharpe * significance_bonus * log10(1/p_value)
    significance_bonus = 2.0 if p < 0.05, else 1.0
    If p_value is N/A or unparseable, log10 term = 1.0 and bonus = 1.0
    """
    # Parse p-value
    p_val = None
    if p_val_str and p_val_str != "N/A":
        try:
            p_val = float(p_val_str)
        except (ValueError, TypeError):
            p_val = None

    if p_val is not None and p_val > 0:
        sig_bonus = 2.0 if p_val < 0.05 else 1.0
        log_term = math.log10(1.0 / p_val)
    else:
        sig_bonus = 1.0
        log_term = 1.0

    # win_rate is in percent (e.g. 75.7) -- normalise to fraction for scoring
    wr_frac = win_rate / 100.0 if win_rate > 1.0 else win_rate
    return wr_frac * sharpe * sig_bonus * log_term


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
class StrategyData:
    """Holds backtest + forward-test stats for a single strategy slot."""

    def __init__(self, idx: int):
        self.idx = idx
        self.name = STRATEGY_NAMES[idx]
        # Backtest
        defaults = DEFAULTS[idx]
        self.bt_wr = defaults[0]
        self.bt_sharpe = defaults[1]
        self.bt_pval = defaults[2]
        self.bt_trades = defaults[3]
        self.bt_tf = defaults[4]
        self.bt_method = defaults[5]
        self.bt_symbol = defaults[6]
        # Forward-test
        self.ft_wr = 0.0
        self.ft_trades = 0
        # Transaction cost adjusted
        self.net_wr = 0.0       # Win rate after transaction costs
        self.tx_cost = 0.03     # Estimated round-trip cost % (default stocks)
        # Composite score (computed later)
        self.score = 0.0
        # Proven flag: True only if real backtest JSON exists with p < 0.05
        self.proven = False
        # Source of data: "real_backtest" or "placeholder"
        self.data_source = "placeholder"

    def __repr__(self):
        proven_tag = "PROVEN" if self.proven else "UNPROVEN"
        return (
            f"<Strategy[{self.idx}] {self.name} [{proven_tag}]: "
            f"BT_WR={self.bt_wr:.1f}% Sharpe={self.bt_sharpe:.2f} "
            f"p={self.bt_pval} symbol={self.bt_symbol} score={self.score:.2f}>"
        )


def load_backtest_data(strategies: list[StrategyData]) -> None:
    """
    Load real backtest data from JSON files for strategies that have them.
    Sets the `proven` flag based on statistical significance (p < 0.05).
    Strategies without real backtest files keep their placeholder defaults.
    """
    for idx, source in BACKTEST_SOURCES.items():
        if idx >= len(strategies):
            continue

        filepath = ALPHA_DATA / source["file"]
        data = load_json(filepath)
        if not data or not isinstance(data, dict):
            print(f"  [WARN] No real backtest data for strategy {idx} ({strategies[idx].name})")
            continue

        # Navigate to the correct sub-key if needed
        symbol_key = source.get("symbol_key")
        if symbol_key:
            record = data.get(symbol_key, {})
        else:
            record = data

        if not record:
            print(f"  [WARN] Empty record in {filepath} for strategy {idx}")
            continue

        # Extract stats
        win_rate_raw = record.get("win_rate", 0)
        # win_rate may be 0-1 fraction or 0-100 percentage
        if 0 < win_rate_raw <= 1.0:
            win_rate_pct = round(win_rate_raw * 100, 1)
        else:
            win_rate_pct = round(win_rate_raw, 1)

        sharpe = round(record.get("sharpe", 0), 3)
        binomial_p = record.get("binomial_p")
        n_trades = record.get("n_trades", 0)

        strategies[idx].bt_wr = win_rate_pct
        strategies[idx].bt_sharpe = sharpe
        strategies[idx].bt_pval = fmt_pval(binomial_p)
        strategies[idx].bt_trades = n_trades
        strategies[idx].data_source = "real_backtest"

        # Determine proven status: real data + statistically significant
        if binomial_p is not None and n_trades >= 10:
            try:
                p_float = float(binomial_p)
                strategies[idx].proven = p_float < PROVEN_P_THRESHOLD
            except (ValueError, TypeError):
                strategies[idx].proven = False
        else:
            strategies[idx].proven = False

        status = "PROVEN" if strategies[idx].proven else "UNPROVEN"
        print(f"  [{status}] {strategies[idx].name}: WR={win_rate_pct:.1f}% "
              f"Sharpe={sharpe:.3f} p={fmt_pval(binomial_p)} trades={n_trades} "
              f"(source: {source['file']})")

    # Also try to load additional backtest data from rigorous_battle_results.json
    # This file contains promoted strategies from rigorous forward testing
    _load_rigorous_results(strategies)

    # Print summary of unproven strategies
    unproven = [s for s in strategies if not s.proven]
    if unproven:
        print(f"\n  [INFO] {len(unproven)} strategies are UNPROVEN (no real backtest data with p<0.05):")
        for s in unproven:
            print(f"    - {s.idx}: {s.name} (source: {s.data_source})")


def _load_rigorous_results(strategies: list[StrategyData]) -> None:
    """
    Check rigorous_battle_results.json for any strategies that were
    promoted with statistical significance. This is secondary evidence.
    """
    rigorous = load_json(ALPHA_DATA / "rigorous_battle_results.json")
    if not rigorous or not isinstance(rigorous, dict):
        return

    strategy_analysis = rigorous.get("strategy_analysis", {})
    verdicts = rigorous.get("verdicts", {})
    promoted = verdicts.get("promoted", [])

    # Map rigorous strategy names to our indices
    rigorous_map = {
        "spike_macd_divergence": 2,
        "spike_momentum_ignition": None,  # Not in our 24-strategy list
        "btc_ichimoku_cloud": 4,
        "community_ema_9_21_rsi_crypto": 3,
        "community_bb_squeeze_breakout_crypto": 5,
        "rsi_hidden_divergence": 7,
        "spike_zscore_extreme": None,  # Z-score, not directly mapped
        "liquidity_sweep": 20,
        "nonlinear_tsmom": 21,
        "ctrend_multi_ma": 22,
        "flash_crash_reversal": 23,
        "fair_value_gap": 25,
        "keltner_squeeze": 26,
        "order_block": 27,
        "wyckoff_spring": 28,
        "cvd_divergence": 29,
    }

    for strat_name, analysis in strategy_analysis.items():
        idx = rigorous_map.get(strat_name)
        if idx is None or idx >= len(strategies):
            continue

        # Only use if the strategy was promoted AND has significant p-value
        binom_p = analysis.get("p_value_binomial")
        monte_p = analysis.get("p_value_montecarlo")
        total_picks = analysis.get("total_picks", 0)

        if strat_name in promoted and total_picks >= 30:
            # Use the more conservative p-value
            best_p = None
            if binom_p is not None:
                best_p = binom_p
            if monte_p is not None and (best_p is None or monte_p < best_p):
                best_p = monte_p

            if best_p is not None and best_p < PROVEN_P_THRESHOLD:
                wr_pct = round(analysis.get("win_rate", 0) * 100, 1)
                sharpe = round(analysis.get("sharpe", 0), 3)

                # Only upgrade if we don't already have proven data
                if not strategies[idx].proven:
                    strategies[idx].bt_wr = wr_pct
                    strategies[idx].bt_sharpe = sharpe
                    strategies[idx].bt_pval = fmt_pval(best_p)
                    strategies[idx].bt_trades = total_picks
                    strategies[idx].proven = True
                    strategies[idx].data_source = "rigorous_battle_test"
                    print(f"  [PROVEN via rigorous test] {strategies[idx].name}: "
                          f"WR={wr_pct:.1f}% Sharpe={sharpe:.3f} p={fmt_pval(best_p)} "
                          f"trades={total_picks}")


def load_forward_test_data(strategies: list[StrategyData]) -> None:
    """
    Aggregate forward-test win-rate and trade count from active_picks.json
    (Alpha Engine) and closed picks.  Only closed (WON/LOST) picks count.
    """
    picks = load_json(ALPHA_DATA / "active_picks.json")
    if not picks or not isinstance(picks, list):
        picks = []

    # Also try closed_picks.json
    closed = load_json(ALPHA_DATA / "closed_picks.json")
    if closed and isinstance(closed, list):
        picks = picks + closed

    # Aggregate per-strategy-slot
    # wins[idx], total[idx]
    n = len(STRATEGY_NAMES)
    wins = [0] * n
    total = [0] * n

    for pick in picks:
        status = pick.get("status", "").upper()
        if status not in ("WON", "LOST"):
            continue
        strat_name = pick.get("strategy", "")
        idx = FORWARD_STRATEGY_MAP.get(strat_name)
        if idx is None:
            continue
        total[idx] += 1
        if status == "WON":
            wins[idx] += 1

    for i in range(min(n, len(strategies))):
        strategies[i].ft_trades = total[i]
        if total[i] > 0:
            strategies[i].ft_wr = round(100.0 * wins[i] / total[i], 1)
        else:
            strategies[i].ft_wr = 0.0


def compute_transaction_costs(strategies: list[StrategyData]) -> None:
    """
    Estimate transaction costs and net win rate for each strategy
    based on the symbol it was tested on.
    """
    # Map tested symbol to estimated round-trip cost %
    SYMBOL_COST_MAP = {
        "SPY":    0.03,   # stocks_etf: 0.03%
        "QQQ":    0.03,
        "BTCUSD": 0.25,   # crypto_spot: 0.25%
        "ETHUSD": 0.25,
        "Multi":  0.50,   # blended average (crypto-heavy consensus)
    }
    # Default average win/loss assumptions for net WR calculation
    # These are conservative estimates
    AVG_WIN_PCT = {
        "SPY":    0.04,   # 4% avg win on equities
        "QQQ":    0.04,
        "BTCUSD": 0.08,   # 8% avg win on crypto
        "ETHUSD": 0.08,
        "Multi":  0.06,
    }
    AVG_LOSS_PCT = {
        "SPY":    0.02,
        "QQQ":    0.02,
        "BTCUSD": 0.05,
        "ETHUSD": 0.05,
        "Multi":  0.04,
    }

    for s in strategies:
        symbol = s.bt_symbol
        cost_pct = SYMBOL_COST_MAP.get(symbol, 0.25)  # default to crypto
        s.tx_cost = cost_pct

        if s.bt_wr > 0 and s.proven:
            avg_win = AVG_WIN_PCT.get(symbol, 0.06)
            avg_loss = AVG_LOSS_PCT.get(symbol, 0.04)
            gross_wr_frac = s.bt_wr / 100.0
            cost_frac = cost_pct / 100.0  # convert from % to decimal
            net_wr_frac = _compute_net_wr(gross_wr_frac, avg_win, avg_loss, cost_frac)
            s.net_wr = round(net_wr_frac * 100.0, 1)
        else:
            s.net_wr = 0.0


def compute_scores(strategies: list[StrategyData]) -> None:
    """Compute composite ranking score using NET win rate (after costs).
    Only PROVEN strategies get a real score; UNPROVEN get 0."""
    for s in strategies:
        if s.proven:
            # Use NET win rate for composite score (accounts for real-world costs)
            s.score = composite_score(s.net_wr if s.net_wr > 0 else s.bt_wr,
                                      s.bt_sharpe, s.bt_pval)
        else:
            s.score = 0.0


# ---------------------------------------------------------------------------
# Version management
# ---------------------------------------------------------------------------
def resolve_version(override: str | None) -> str:
    """
    Return the version string.
    - If override is given, use it directly.
    - If version.json exists, auto-increment the patch number.
    - Otherwise start at 1.0.0
    """
    if override:
        return override

    ver_data = load_json(OUTPUT_VERSION)
    if ver_data and isinstance(ver_data, dict):
        prev = ver_data.get("version", "1.0.0")
        parts = prev.split(".")
        try:
            major = int(parts[0]) if len(parts) > 0 else 1
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0
            patch += 1
            return f"{major}.{minor}.{patch}"
        except (ValueError, IndexError):
            return "1.0.0"
    return "1.0.0"


# ---------------------------------------------------------------------------
# Template rendering
# ---------------------------------------------------------------------------
def build_replacements(
    strategies: list[StrategyData],
    version: str,
    generated_date: str,
) -> dict[str, str]:
    """Build the {PLACEHOLDER} -> value mapping dictionary."""
    proven_count = sum(1 for s in strategies if s.proven)
    total_count = len(STRATEGY_NAMES)

    reps: dict[str, str] = {
        "{VERSION}": version,
        "{STRATEGY_COUNT}": str(total_count),
        "{GENERATED_DATE}": generated_date,
        "{TEMPLATE_VERSION}": "5.0",  # v6.0 FVG+Keltner+OB+Wyckoff+CVD (30 total)
        "{PROVEN_COUNT}": str(proven_count),
        "{TOTAL_COUNT}": str(total_count),
    }

    for s in strategies:
        i = s.idx
        # Float arrays: no quotes needed
        reps[f"{{BT_WR_{i}}}"] = f"{s.bt_wr:.1f}"
        reps[f"{{BT_SHARPE_{i}}}"] = f"{s.bt_sharpe:.3f}"
        # Int arrays: no quotes needed
        reps[f"{{BT_TRADES_{i}}}"] = str(s.bt_trades)
        # String arrays: must be wrapped in double quotes for Pine Script
        reps[f"{{BT_PVAL_{i}}}"] = f'"{s.bt_pval}"'
        reps[f"{{BT_TF_{i}}}"] = f'"{s.bt_tf}"'
        reps[f"{{BT_METHOD_{i}}}"] = f'"{s.bt_method}"'
        reps[f"{{BT_SYMBOL_{i}}}"] = f'"{s.bt_symbol}"'
        # Proven status: boolean for Pine Script (true/false lowercase)
        reps[f"{{PROVEN_{i}}}"] = "true" if s.proven else "false"

        reps[f"{{FT_WR_{i}}}"] = f"{s.ft_wr:.1f}"
        reps[f"{{FT_TRADES_{i}}}"] = str(s.ft_trades)

        # Transaction cost placeholders
        reps[f"{{NET_WR_{i}}}"] = f"{s.net_wr:.1f}"
        reps[f"{{TX_COST_{i}}}"] = f"{s.tx_cost:.2f}"

    return reps


def render_template(template_text: str, replacements: dict[str, str]) -> str:
    """Replace all placeholder tokens in the template."""
    result = template_text
    for token, value in replacements.items():
        result = result.replace(token, value)
    return result


def validate_pine_output(pine_text: str) -> list[str]:
    """Post-generation Pine Script syntax validation.

    Checks for common issues that would cause TradingView compile errors:
    1. Unreplaced {PLACEHOLDER} tokens
    2. Variables used before declaration (use-before-decl)
    3. ta.* functions inside for loops (Pine v6 consistency warning)
    Returns list of error/warning strings (empty = all good).
    """
    import re
    errors: list[str] = []
    lines = pine_text.split("\n")

    # --- Check 1: Unreplaced placeholders ---
    placeholder_re = re.compile(r"\{[A-Z_]+_\d+\}")
    for i, line in enumerate(lines, 1):
        if line.lstrip().startswith("//"):
            continue  # skip comments
        matches = placeholder_re.findall(line)
        for m in matches:
            errors.append(f"ERROR line {i}: Unreplaced placeholder {m}")

    # --- Check 2: Variable use-before-declaration ---
    declared_arrays: dict[str, int] = {}
    used_arrays: dict[str, int] = {}
    array_decl_re = re.compile(r"var\s+(?:bool|float|int|string)\[\]\s+(\w+)\s*=")
    # Also match local array declarations: `name = array.from(...)`
    local_array_decl_re = re.compile(r"^\s+(\w+)\s*=\s*array\.from\(")
    array_use_re = re.compile(r"array\.(?:get|size|set)\((\w+)")
    for i, line in enumerate(lines, 1):
        for m in array_decl_re.finditer(line):
            name = m.group(1)
            if name not in declared_arrays:
                declared_arrays[name] = i
        for m in local_array_decl_re.finditer(line):
            name = m.group(1)
            if name not in declared_arrays:
                declared_arrays[name] = i
        for m in array_use_re.finditer(line):
            name = m.group(1)
            if name not in used_arrays:
                used_arrays[name] = i
    for name, first_use in used_arrays.items():
        decl_line = declared_arrays.get(name)
        if decl_line is None:
            errors.append(f"ERROR line {first_use}: Undeclared array '{name}'")
        elif decl_line > first_use:
            errors.append(
                f"WARN line {first_use}: Array '{name}' used before declaration "
                f"(declared at line {decl_line})"
            )

    # --- Check 3: ta.* inside for loops ---
    ta_in_loop_re = re.compile(r"\bta\.\w+\(")
    in_for = False
    for_indent = -1
    for i, line in enumerate(lines, 1):
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if stripped.startswith("for ") or stripped.startswith("for\t"):
            in_for = True
            for_indent = indent
        elif in_for and indent <= for_indent and stripped:
            in_for = False
        if in_for and ta_in_loop_re.search(stripped):
            errors.append(
                f"WARN line {i}: ta.* function inside for loop — "
                f"may cause inconsistent calculations in Pine v6"
            )

    if errors:
        print(f"\n{'='*60}")
        print(f"  PINE SCRIPT VALIDATION: {len(errors)} issue(s) found")
        print(f"{'='*60}")
        for e in errors:
            print(f"  {e}")
        print()
    else:
        print("\n  PINE SCRIPT VALIDATION: All checks passed\n")

    return errors


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
def write_outputs(
    pine_text: str,
    version: str,
    generated_date: str,
    strategies: list[StrategyData],
    dry_run: bool,
) -> None:
    """Write the .pine file and version.json (unless --dry-run)."""
    if dry_run:
        print("\n[DRY RUN] Skipping file writes.")
        return

    # Ensure output directory exists
    OUTPUT_PINE.parent.mkdir(parents=True, exist_ok=True)

    # Write .pine file
    with open(OUTPUT_PINE, "w", encoding="utf-8") as f:
        f.write(pine_text)
    print(f"\n  -> Wrote Pine Script: {OUTPUT_PINE}")
    print(f"     Size: {len(pine_text):,} bytes")

    # Write version.json
    proven_count = sum(1 for s in strategies if s.proven)
    version_payload = {
        "version": version,
        "generated_at": generated_date,
        "strategy_count": len(STRATEGY_NAMES),
        "proven_count": proven_count,
        "proven_strategies": [
            {
                "index": s.idx,
                "name": s.name,
                "score": round(s.score, 4),
                "bt_win_rate": s.bt_wr,
                "bt_sharpe": s.bt_sharpe,
                "bt_pval": s.bt_pval,
                "data_source": s.data_source,
            }
            for s in sorted(
                [s for s in strategies if s.proven],
                key=lambda x: x.score,
                reverse=True,
            )
        ],
        "unproven_strategies": [
            {
                "index": s.idx,
                "name": s.name,
                "data_source": s.data_source,
            }
            for s in strategies if not s.proven
        ],
    }
    with open(OUTPUT_VERSION, "w", encoding="utf-8") as f:
        json.dump(version_payload, f, indent=2)
    print(f"  -> Wrote version.json: {OUTPUT_VERSION}")


# ---------------------------------------------------------------------------
# Summary printer
# ---------------------------------------------------------------------------
def print_summary(strategies: list[StrategyData], version: str) -> None:
    """Print a human-readable summary of rankings and stats."""
    proven = [s for s in strategies if s.proven]
    unproven = [s for s in strategies if not s.proven]
    proven_ranked = sorted(proven, key=lambda x: x.score, reverse=True)

    print("=" * 72)
    print(f"  Elton's Predictions -- Pine Script Generator v{version}")
    print("=" * 72)
    print()
    print(f"  Total Strategies: {len(strategies)}")
    print(f"  PROVEN:           {len(proven)}/{len(strategies)} (real backtest data, p<0.05)")
    print(f"  UNPROVEN:         {len(unproven)}/{len(strategies)} (no real backtest data)")
    print(f"  Template:         {TEMPLATE}")
    print(f"  Output:           {OUTPUT_PINE}")
    print()

    # Proven strategies
    if proven_ranked:
        print("  PROVEN STRATEGIES (real backtest data with p<0.05)")
        print("  " + "-" * 88)
        print(
            f"  {'Rank':<5} {'Strategy':<28} {'BT WR%':<8} {'Net WR%':<9} {'Costs':<7} "
            f"{'Sharpe':<8} {'p-val':<10} {'Score':<10}"
        )
        print("  " + "-" * 88)
        for rank, s in enumerate(proven_ranked, 1):
            print(
                f"  {rank:<5} {s.name:<28} {s.bt_wr:<8.1f} {s.net_wr:<9.1f} {s.tx_cost:<7.2f} "
                f"{s.bt_sharpe:<8.3f} {s.bt_pval:<10} {s.score:<10.2f}"
            )
        print("  " + "-" * 88)
    else:
        print("  No PROVEN strategies found.")

    # Unproven strategies
    if unproven:
        print(f"\n  UNPROVEN STRATEGIES (placeholder data -- no real backtests)")
        print("  " + "-" * 68)
        for s in unproven:
            print(f"    [{s.idx:>2}] {s.name:<28} (source: {s.data_source})")
        print("  " + "-" * 68)

    # Forward-test summary
    ft_total = sum(s.ft_trades for s in strategies)
    if ft_total > 0:
        ft_wins = sum(
            int(s.ft_wr * s.ft_trades / 100) for s in strategies if s.ft_trades > 0
        )
        print(f"\n  Forward-test: {ft_total} closed trades, ~{ft_wins} wins")
    else:
        print("\n  Forward-test: No closed trades yet (all open or no data)")

    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate TradingView Pine Script from Alpha Engine data"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print stats without writing output files",
    )
    parser.add_argument(
        "--version",
        type=str,
        default=None,
        dest="version_override",
        help="Override the version string (e.g. '2.0')",
    )
    args = parser.parse_args()

    # 1. Initialise strategy slots
    strategies = [StrategyData(i) for i in range(len(STRATEGY_NAMES))]

    # 2. Load backtest data from JSON files
    print("Loading backtest data...")
    load_backtest_data(strategies)

    # 3. Load forward-test data
    print("Loading forward-test data...")
    load_forward_test_data(strategies)

    # 3b. Compute transaction costs and net win rates
    print("Computing transaction costs and net win rates...")
    compute_transaction_costs(strategies)

    # 4. Compute composite scores and rank (uses NET win rate)
    compute_scores(strategies)

    # 5. Resolve version
    version = resolve_version(args.version_override)
    generated_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 6. Print summary
    print_summary(strategies, version)

    # 7. Load template
    if not TEMPLATE.exists():
        print(f"  [ERROR] Template not found: {TEMPLATE}")
        print("  Create the template file and re-run.")
        print(f"  Expected path: {TEMPLATE}")
        return 1

    template_text = TEMPLATE.read_text(encoding="utf-8")
    print(f"  Template loaded: {len(template_text):,} chars")

    # 8. Build replacements and render
    replacements = build_replacements(strategies, version, generated_date)
    pine_text = render_template(template_text, replacements)

    # 9. Comprehensive Pine Script validation (unreplaced placeholders,
    #    use-before-decl, ta.* in loops, etc.)
    validation_errors = validate_pine_output(pine_text)
    hard_errors = [e for e in validation_errors if e.startswith("ERROR")]
    if hard_errors:
        print(f"\n  [ABORT] {len(hard_errors)} hard error(s) found — fix before shipping!")
        return 1

    # 10. Write outputs
    write_outputs(pine_text, version, generated_date, strategies, args.dry_run)

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
