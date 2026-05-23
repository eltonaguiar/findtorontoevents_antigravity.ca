"""
Train PPO agent on historical crypto data and generate trading signals.

Usage:
    python -m rl_agent.train --pair BTCUSDT --episodes 100
    python -m rl_agent.train --mode predict
"""
import os
import sys
import json
import argparse
import numpy as np
import logging
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rl_agent.trading_env import CryptoTradingEnv
from rl_agent.ppo_agent import SimplePPOAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).parent / "models"
DATA_DIR = Path(__file__).parent / "data"
PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT"]


def fetch_real_prices(symbol: str, limit: int = 500) -> np.ndarray:
    """Fetch real 1h kline close prices from Binance."""
    try:
        import requests
        url = "https://api.binance.com/api/v3/klines"
        resp = requests.get(url, params={
            "symbol": symbol, "interval": "1h", "limit": limit
        }, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        prices = np.array([float(k[4]) for k in data])  # close prices
        logger.info("Fetched %d real prices for %s", len(prices), symbol)
        return prices
    except Exception as exc:
        logger.warning("Failed to fetch real prices for %s: %s", symbol, exc)
        return generate_synthetic_prices(limit, symbol=symbol)


# Approximate base prices for synthetic fallback (prevents all symbols using BTC price)
_SYMBOL_BASE_PRICES = {
    "BTCUSDT": 60000, "ETHUSDT": 2000, "SOLUSDT": 90, "BNBUSDT": 300,
    "DOGEUSDT": 0.10, "XRPUSDT": 0.55, "ADAUSDT": 0.35, "AVAXUSDT": 20,
    "DOTUSDT": 5, "LINKUSDT": 12, "MATICUSDT": 0.50, "SHIBUSDT": 0.000008,
}


def generate_synthetic_prices(n: int = 5000, mu: float = 0.0001, sigma: float = 0.02,
                              symbol: str = "BTCUSDT") -> np.ndarray:
    """Generate synthetic GBM price series using symbol-appropriate base price."""
    base_price = _SYMBOL_BASE_PRICES.get(symbol, 100)
    returns = np.random.normal(mu, sigma, n)
    prices = base_price * np.exp(np.cumsum(returns))
    return prices


def train(
    prices: np.ndarray,
    n_episodes: int = 100,
    sharpe_penalty: float = 0.1,
) -> tuple:
    """Train PPO agent on price data. Returns (agent, summary)."""
    env = CryptoTradingEnv(prices, sharpe_penalty=sharpe_penalty)
    agent = SimplePPOAgent(obs_dim=env.observation_dim, n_actions=env.n_actions)

    best_sharpe = -np.inf
    history = []

    for episode in range(n_episodes):
        obs = env.reset()
        observations, actions, rewards, log_probs, values, dones = [], [], [], [], [], []

        while not env.done:
            action, log_prob, value = agent.act(obs)
            next_obs, reward, done, info = env.step(action)

            observations.append(obs)
            actions.append(action)
            rewards.append(reward)
            log_probs.append(log_prob)
            values.append(value)
            dones.append(done)

            obs = next_obs

        agent.update(observations, actions, rewards, log_probs, values, dones)

        stats = env.get_episode_stats()
        history.append(stats)

        if stats["sharpe"] > best_sharpe:
            best_sharpe = stats["sharpe"]

        if (episode + 1) % 10 == 0:
            logger.info(
                "Episode %d/%d: return=%.2f%%, sharpe=%.2f, max_dd=%.1f%%, best_sharpe=%.2f",
                episode + 1, n_episodes,
                stats["total_return"] * 100,
                stats["sharpe"],
                stats["max_drawdown"] * 100,
                best_sharpe,
            )

    summary = {
        "n_episodes": n_episodes,
        "best_sharpe": float(best_sharpe),
        "final_return": float(history[-1]["total_return"]),
        "final_sharpe": float(history[-1]["sharpe"]),
        "history": history,
    }
    return agent, summary


def predict(symbol: str, agent: SimplePPOAgent) -> dict:
    """Use trained agent to generate a trading signal for a symbol."""
    prices = fetch_real_prices(symbol, limit=100)
    if len(prices) < 25:
        return {}

    # Sanity check: reject synthetic/corrupt prices
    current = float(prices[-1])
    expected = _SYMBOL_BASE_PRICES.get(symbol)
    if expected and expected < 10000:
        # Non-BTC symbol should not have BTC-like prices
        if current > expected * 100:
            logger.warning("Price sanity check FAILED for %s: %.2f >> expected ~%.2f (likely synthetic)", symbol, current, expected)
            return {}

    env = CryptoTradingEnv(prices)
    obs = env.reset()

    # Walk to the last bar
    while env.step_idx < len(prices) - 2 and not env.done:
        action, _, _ = agent.act(obs)
        obs, _, _, _ = env.step(action)

    # Get final action
    action, log_prob, value = agent.act(obs)
    confidence = float(np.exp(log_prob))

    if action == CryptoTradingEnv.HOLD:
        return {}

    direction = "LONG" if action == CryptoTradingEnv.BUY else "SHORT"
    current_price = float(prices[-1])

    # Simple ATR for TP/SL
    returns = np.diff(prices[-15:]) / prices[-15:-1]
    atr = float(np.std(returns) * current_price * np.sqrt(14))

    if direction == "LONG":
        tp = round(current_price + atr * 1.5, 2)
        sl = round(current_price - atr * 1.0, 2)
    else:
        tp = round(current_price - atr * 1.5, 2)
        sl = round(current_price + atr * 1.0, 2)

    return {
        "symbol": symbol,
        "direction": direction,
        "confidence": round(min(confidence * 2, 0.75), 3),
        "entry_price": current_price,
        "take_profit": tp,
        "stop_loss": sl,
        "strategy": "rl_ppo_agent",
        "source": "rl_agent",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def run_train_all():
    """Train models for all pairs and save."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    results = {}
    for symbol in PAIRS:
        logger.info("Training PPO agent for %s...", symbol)
        prices = fetch_real_prices(symbol, limit=500)
        agent, summary = train(prices, n_episodes=50, sharpe_penalty=0.1)
        model_path = str(MODELS_DIR / f"{symbol}_ppo")
        agent.save(model_path)
        logger.info("Saved model to %s.npz", model_path)
        results[symbol] = {
            "best_sharpe": summary["best_sharpe"],
            "final_return": summary["final_return"],
        }

    summary_path = DATA_DIR / "training_summary.json"
    summary_path.write_text(json.dumps({
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "pairs": results,
    }, indent=2))
    logger.info("Training complete for all pairs")


def _track_existing_picks():
    """Check existing active picks for TP/SL hits and move to closed."""
    active_path = DATA_DIR / "active_picks.json"
    closed_path = DATA_DIR / "closed_picks.json"

    if not active_path.exists():
        return []

    try:
        active = json.loads(active_path.read_text())
    except Exception:
        return []

    try:
        closed = json.loads(closed_path.read_text()) if closed_path.exists() else []
    except Exception:
        closed = []

    still_active = []
    newly_closed = []

    for pick in active:
        symbol = pick.get("symbol", "")
        tp = pick.get("take_profit")
        sl = pick.get("stop_loss")
        direction = pick.get("direction", "LONG")
        entry = pick.get("entry_price", 0)

        # Fetch current price
        try:
            import requests
            url = "https://api.binance.com/api/v3/ticker/price"
            resp = requests.get(url, params={"symbol": symbol}, timeout=10)
            current = float(resp.json()["price"]) if resp.ok else None
        except Exception:
            # Fallback: try Bybit
            try:
                resp = requests.get(
                    f"https://api.bybit.com/v5/market/tickers?symbol={symbol}&category=spot",
                    timeout=10)
                data = resp.json()
                current = float(data["result"]["list"][0]["lastPrice"]) if resp.ok else None
            except Exception:
                current = None

        if current is None:
            still_active.append(pick)
            continue

        # Check TP/SL
        tp_hit = sl_hit = False
        if direction == "LONG":
            if tp and current >= tp:
                tp_hit = True
            if sl and current <= sl:
                sl_hit = True
        else:  # SHORT
            if tp and current <= tp:
                tp_hit = True
            if sl and current >= sl:
                sl_hit = True

        # Check time expiry (48h max hold)
        generated = pick.get("generated_at", "")
        expired = False
        if generated:
            try:
                gen_dt = datetime.fromisoformat(generated.replace("Z", "+00:00"))
                age_hours = (datetime.now(timezone.utc) - gen_dt).total_seconds() / 3600
                if age_hours > 48:
                    expired = True
            except Exception:
                pass

        if tp_hit or sl_hit or expired:
            pnl = ((current - entry) / entry * 100) if entry > 0 else 0
            if direction == "SHORT":
                pnl = -pnl
            pick["close_price"] = current
            pick["closed_at"] = datetime.now(timezone.utc).isoformat()
            pick["pnl_pct"] = round(pnl, 2)
            pick["outcome"] = "TP_HIT" if tp_hit else ("SL_HIT" if sl_hit else "EXPIRED")
            newly_closed.append(pick)
            logger.info("CLOSED %s %s: %s (PnL=%.2f%%)", direction, symbol, pick["outcome"], pnl)
        else:
            still_active.append(pick)

    if newly_closed:
        closed.extend(newly_closed)
        closed_path.write_text(json.dumps(closed, indent=2, default=str))
        logger.info("Moved %d picks to closed_picks.json (total: %d)", len(newly_closed), len(closed))

    return still_active


def run_predict_all():
    """Track existing picks for TP/SL, then generate new predictions."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # First: track existing picks for TP/SL hits
    still_active = _track_existing_picks()

    # Collect symbols already active to avoid duplicates
    active_symbols = {p["symbol"] for p in still_active}

    picks = list(still_active)  # Keep surviving picks
    for symbol in PAIRS:
        if symbol in active_symbols:
            continue  # Don't open duplicate

        model_path = MODELS_DIR / f"{symbol}_ppo.npz"
        if not model_path.exists():
            logger.warning("No model for %s, skipping", symbol)
            continue

        agent = SimplePPOAgent()
        agent.load(str(model_path))

        pick = predict(symbol, agent)
        if pick:
            picks.append(pick)
            logger.info("Signal: %s %s (conf=%.3f)", pick["direction"], symbol, pick["confidence"])

    picks_path = DATA_DIR / "active_picks.json"
    # Feed hygiene: strip resolved/zero-entry picks before persisting
    try:
        import sys as _sys
        _sys.path.insert(0, str(DATA_DIR.parent.parent))
        from alpha_engine.feed_hygiene import sanitize_active_picks
        picks = sanitize_active_picks(picks)
    except Exception:
        picks = [p for p in picks if float(p.get("entry_price") or 0) > 0]
    picks_path.write_text(json.dumps(picks, indent=2, default=str))
    logger.info("Wrote %d picks to %s (%d carried, %d new)",
                len(picks), picks_path, len(still_active), len(picks) - len(still_active))
    return picks


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train PPO Trading Agent")
    parser.add_argument("--mode", choices=["train", "predict", "both"], default="both")
    parser.add_argument("--episodes", type=int, default=50)
    parser.add_argument("--sharpe-penalty", type=float, default=0.1)
    args = parser.parse_args()

    if args.mode in ("train", "both"):
        run_train_all()
    if args.mode in ("predict", "both"):
        run_predict_all()
