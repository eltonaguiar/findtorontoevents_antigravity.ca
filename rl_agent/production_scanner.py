# Production scanner for the RL adaptive trader (PPO agent)
# Loads a trained PPO model and outputs signals in the standard platform format.
# Handles missing model gracefully — returns empty signals if no model is available.

import os
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class RLProductionScanner:
    """Wraps a PPO agent to generate trading signals for the live system.

    If no trained model is available, returns empty signals gracefully.
    """
    def __init__(self, model_path=None, context=None):
        self.context = context or {}
        self.model_path = model_path or os.getenv(
            'RL_MODEL_PATH', 'rl_agent/model/ppo_latest.pt'
        )
        self.agent = None
        self._load_agent()

    def _load_agent(self):
        """Try to load the PPO agent. Fail gracefully if not available."""
        if not os.path.exists(self.model_path):
            logger.info(
                "RL model not found at %s — scanner will return empty signals. "
                "Train a model first with: python -m rl_agent.trainer",
                self.model_path
            )
            return

        try:
            from rl_agent.trainer import PPOAgent
            self.agent = PPOAgent()
            self.agent.load(self.model_path)
            logger.info("RL model loaded from %s", self.model_path)
        except ImportError:
            logger.warning("rl_agent.trainer not available — RL scanner disabled")
        except Exception as e:
            logger.warning("Failed to load RL model: %s — scanner disabled", e)

    def generate_signals(self) -> List[Dict]:
        """Generate signals from the PPO agent.

        Returns empty list if no model is loaded.
        """
        if self.agent is None:
            return []

        try:
            obs = self._build_observation()
            action = self.agent.act(obs)
        except Exception as e:
            logger.warning("RL inference failed: %s", e)
            return []

        signals = []
        if not isinstance(action, dict):
            return signals

        spot_prices = self.context.get('spot_price', {})
        for symbol, direction in action.items():
            price = spot_prices.get(symbol, None)
            if price is None:
                continue
            direction_str = "LONG" if direction > 0 else "SHORT"
            tp = price * (1.08 if direction > 0 else 0.92)
            sl = price * (0.92 if direction > 0 else 1.08)
            signals.append({
                "symbol": symbol,
                "direction": direction_str,
                "entry": price,
                "tp": tp,
                "sl": sl,
                "size": 0.015,
                "confidence": 0.55,
                "strategy": "rl_ppo_adaptive",
                "reason": "RL PPO adaptive signal"
            })
        return signals

    def _build_observation(self):
        """Flatten relevant market data from context into an array."""
        import numpy as np
        prices = self.context.get('spot_price', {})
        volumes = self.context.get('volume', {})
        momentum = self.context.get('momentum', {})
        symbols = list(prices.keys())
        obs = []
        for sym in symbols:
            p = prices.get(sym, 0)
            v = volumes.get(sym, 0)
            m = momentum.get(sym, 0)
            obs.extend([p, v, m])
        return np.array(obs, dtype=np.float32) if obs else np.zeros(3, dtype=np.float32)
