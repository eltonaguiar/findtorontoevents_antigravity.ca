"""
mega_data_bridge.py -- KIMI Rise of the Claw
Bridge between Alpha Engine's 308K-trade mega dataset and KIMI's ML Signal Ranker.

Loads resolved trades from alpha_engine/data/mega_training_data.json,
computes per-strategy statistics, and converts each trade into the 15-feature
format that MLSignalRanker expects.

Output: a pandas DataFrame with FEATURE_COLS + 'won' column, ready to concat
with KIMI's live_competition.json training data.
"""

import json
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)

# Path to mega dataset (relative to this file's location)
MEGA_DATA_PATH = Path(__file__).parent.parent / "alpha_engine" / "data" / "mega_training_data.json"

# KIMI's encoding maps (mirrored from ml_signal_ranker.py)
CAT_MAP = {"stock": 0, "crypto": 1, "meme": 2, "penny": 3, "forex": 4}
TIER_MAP = {"TIER_1": 1, "SCOUT": 0}
TOP_SYMBOLS = [
    "BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "BNB-USD",
    "AAPL", "MSFT", "NVDA", "TSLA", "META", "GOOGL", "AMZN", "SPY", "QQQ",
    "DOGE-USD", "SHIB-USD", "PEPE-USD", "EURUSD=X", "GBPUSD=X", "USDJPY=X",
    "LINK-USD", "XRP-USD", "ADA-USD", "MATIC-USD",
]
SYM_MAP = {sym: i for i, sym in enumerate(TOP_SYMBOLS)}

# Normalize mega dataset symbol names to KIMI's format
SYMBOL_NORMALIZE = {
    "BTC": "BTC-USD", "BTCUSDT": "BTC-USD", "BTC-USDT": "BTC-USD",
    "ETH": "ETH-USD", "ETHUSDT": "ETH-USD", "ETH-USDT": "ETH-USD",
    "SOL": "SOL-USD", "SOLUSDT": "SOL-USD", "SOL-USDT": "SOL-USD",
    "AVAX": "AVAX-USD", "AVAXUSDT": "AVAX-USD",
    "BNB": "BNB-USD", "BNBUSDT": "BNB-USD",
    "DOGE": "DOGE-USD", "DOGEUSDT": "DOGE-USD",
    "SHIB": "SHIB-USD", "SHIBUSDT": "SHIB-USD",
    "PEPE": "PEPE-USD", "PEPEUSDT": "PEPE-USD",
    "LINK": "LINK-USD", "LINKUSDT": "LINK-USD",
    "XRP": "XRP-USD", "XRPUSDT": "XRP-USD",
    "ADA": "ADA-USD", "ADAUSDT": "ADA-USD",
    "MATIC": "MATIC-USD", "MATICUSDT": "MATIC-USD",
    "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "USDJPY=X",
}


def _normalize_symbol(sym: str) -> str:
    """Normalize mega dataset symbol to KIMI format."""
    s = sym.upper().strip()
    if s in SYMBOL_NORMALIZE:
        return SYMBOL_NORMALIZE[s]
    # If it's a crypto symbol without suffix, add -USD
    if len(s) <= 6 and s.isalpha():
        candidate = f"{s}-USD"
        if candidate in SYM_MAP:
            return candidate
    return s


def _encode_symbol(sym: str) -> int:
    return SYM_MAP.get(sym, 99)


def _asset_class_to_category(asset_class: str) -> str:
    """Map mega dataset asset_class to KIMI category."""
    mapping = {"crypto": "crypto", "equity": "stock", "forex": "forex"}
    return mapping.get(asset_class, "crypto")


def _compute_strategy_stats(trades: list) -> dict:
    """Compute per-strategy aggregate stats from resolved trades.

    Returns dict[strategy_name] -> {win_rate, sharpe, kelly, closed, drought}
    """
    by_strategy = defaultdict(list)
    for t in trades:
        strat = t.get("strategy", "unknown")
        pnl = t.get("pnl_pct")
        if pnl is not None:
            by_strategy[strat].append({
                "pnl_pct": float(pnl),
                "is_win": t.get("is_win", pnl > 0),
            })

    stats = {}
    for strat, results in by_strategy.items():
        if not results:
            continue
        pnls = [r["pnl_pct"] for r in results]
        wins = sum(1 for r in results if r["is_win"])
        n = len(results)
        wr = wins / n if n > 0 else 0.5

        # Sharpe ratio (annualized, assuming daily trades)
        mean_pnl = np.mean(pnls)
        std_pnl = np.std(pnls) if len(pnls) > 1 else 1.0
        sharpe = (mean_pnl / std_pnl * np.sqrt(252)) if std_pnl > 0 else 0.0
        sharpe = min(max(sharpe, -5.0), 5.0)

        # Kelly criterion
        if wr > 0 and wr < 1:
            avg_win = np.mean([p for p in pnls if p > 0]) if any(p > 0 for p in pnls) else 1.0
            avg_loss = abs(np.mean([p for p in pnls if p <= 0])) if any(p <= 0 for p in pnls) else 1.0
            if avg_loss > 0:
                kelly = wr - (1 - wr) / (avg_win / avg_loss)
            else:
                kelly = wr
        else:
            kelly = 0.0
        kelly = min(max(kelly, -1.0), 1.0)

        stats[strat] = {
            "win_rate": round(wr, 4),
            "sharpe": round(sharpe, 4),
            "kelly": round(kelly, 4),
            "closed_picks": n,
            "drought": 0,  # Not available from historical data
        }
    return stats


def load_mega_training_data(max_samples: int = 5000,
                            asset_class_filter: str = None,
                            mega_path: Path = None) -> pd.DataFrame:
    """Load mega dataset trades and convert to KIMI's 15-feature format.

    Args:
        max_samples: Maximum number of resolved trades to return (most recent first)
        asset_class_filter: Optional filter ('crypto', 'equity', 'forex')
        mega_path: Override path to mega_training_data.json

    Returns:
        DataFrame with KIMI FEATURE_COLS + 'won' + 'source_weight' columns,
        or empty DataFrame if mega data unavailable.
    """
    path = mega_path or MEGA_DATA_PATH
    if not path.exists():
        logger.info(f"Mega dataset not found at {path}")
        return pd.DataFrame()

    try:
        with open(path) as f:
            data = json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load mega dataset: {e}")
        return pd.DataFrame()

    trades = data.get("trades", [])
    if not trades:
        logger.info("Mega dataset has no trades")
        return pd.DataFrame()

    # Filter to only resolved trades (those with pnl_pct)
    resolved = [t for t in trades if t.get("pnl_pct") is not None]

    # Optional asset class filter
    if asset_class_filter:
        resolved = [t for t in resolved if t.get("asset_class") == asset_class_filter]

    if not resolved:
        logger.info("No resolved trades in mega dataset")
        return pd.DataFrame()

    # Sort by exit_date descending (most recent first), take max_samples
    def _sort_key(t):
        d = t.get("exit_date", t.get("entry_date", "2020-01-01"))
        return d if isinstance(d, str) else "2020-01-01"

    resolved.sort(key=_sort_key, reverse=True)
    resolved = resolved[:max_samples]

    # Compute per-strategy stats from ALL resolved trades (not just the subset)
    all_resolved = [t for t in trades if t.get("pnl_pct") is not None]
    strategy_stats = _compute_strategy_stats(all_resolved)

    # Build feature rows
    feature_rows = []
    for trade in resolved:
        strat = trade.get("strategy", "unknown")
        sym_raw = trade.get("symbol", "")
        sym = _normalize_symbol(sym_raw)
        asset_class = trade.get("asset_class", "crypto")
        category = _asset_class_to_category(asset_class)
        pnl_pct = float(trade.get("pnl_pct", 0))
        is_win = trade.get("is_win", pnl_pct > 0)

        s_stats = strategy_stats.get(strat, {})

        # Compute risk/reward from tp_pct/sl_pct if available
        tp_pct = trade.get("tp_pct")
        sl_pct = trade.get("sl_pct")
        if tp_pct and sl_pct and float(sl_pct) > 0:
            rr_raw = float(tp_pct) / float(sl_pct)
        else:
            # Estimate from entry/exit if possible
            entry = float(trade.get("entry_price", 0) or 0)
            exit_p = float(trade.get("exit_price", 0) or 0)
            if entry > 0 and exit_p > 0:
                rr_raw = 1.5  # Default when we can't compute
            else:
                rr_raw = 1.5
        risk_reward = min(max(rr_raw, 0.0), 5.0) / 5.0

        # Hour of day from entry_date
        hour = 12  # default
        entry_date = trade.get("entry_date", "")
        if entry_date and isinstance(entry_date, str):
            try:
                if len(entry_date) >= 13:  # Has time component
                    dt = datetime.fromisoformat(entry_date.replace("Z", "+00:00"))
                    hour = dt.hour
            except Exception:
                pass
        hour_of_day = hour / 23.0

        feat = {
            "algo_id_enc": hash(strat) % 1000,
            "category_enc": CAT_MAP.get(category, 1),
            "symbol_enc": _encode_symbol(sym),
            "tier_enc": 0,  # Mega data has no tier concept, default SCOUT
            "algo_wr": s_stats.get("win_rate", 0.5),
            "algo_sharpe": min(s_stats.get("sharpe", 0.0), 5.0),
            "algo_drought": s_stats.get("drought", 0),
            "algo_closed": s_stats.get("closed_picks", 0),
            "algo_kelly": s_stats.get("kelly", 0.0),
            "rsi_at_entry": 0.5,  # Not available, use neutral default
            "volume_ratio": 0.1,  # Not available, use neutral default (1.0/10.0)
            "fear_greed": 0.5,  # Not available, use neutral default
            "risk_reward": round(risk_reward, 4),
            "hour_of_day": round(hour_of_day, 4),
            "btc_24h_change": 0.0,  # Not available
            "won": 1 if is_win else 0,
            "source_weight": float(trade.get("source_weight", 0.5)),
        }
        feature_rows.append(feat)

    if not feature_rows:
        return pd.DataFrame()

    df = pd.DataFrame(feature_rows)
    wins = int(df["won"].sum())
    losses = len(df) - wins
    n_strategies = len(set(t.get("strategy", "") for t in resolved))
    logger.info(f"Mega bridge: loaded {len(df)} trades ({wins}W/{losses}L) "
                f"from {n_strategies} strategies")
    print(f"  [MEGA] Loaded {len(df)} resolved trades ({wins}W/{losses}L, "
          f"{n_strategies} strategies)")

    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Testing mega_data_bridge...")
    df = load_mega_training_data(max_samples=5000)
    if len(df) > 0:
        print(f"Shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        print(f"Win rate: {df['won'].mean():.2%}")
        print(f"Sample weights range: {df['source_weight'].min():.2f} - {df['source_weight'].max():.2f}")
        print(f"\nFirst 3 rows:")
        print(df.head(3).to_string())
    else:
        print("No data loaded")
