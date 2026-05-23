"""Adaptive Regime Wrapper — wraps IRB Hoffman with regime state machine (Quant League 2025)."""
from typing import List
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.strategies.irb_hoffman import IRBHoffman
from paper_trading.models import NormalizedPick


class AdaptiveIRBHoffman(BaseStrategy):
    """Wraps IRB Hoffman with adaptive regime state machine that monitors rolling WR."""
    name = "adaptive_irb_hoffman"
    display_name = "Adaptive IRB Hoffman"
    source = "Multi-Source"
    category = "crypto"
    portfolio_type = "technical"

    NORMAL_THRESHOLD = 0.48
    HALT_THRESHOLD = 0.43

    def __init__(self):
        super().__init__()
        self._inner = IRBHoffman()
        self._trade_history: list = []  # True=win, False=loss
        self._state = "NORMAL"

    def fetch_data(self) -> dict:
        return self._inner.fetch_data()

    def _rolling_wr(self) -> float:
        if len(self._trade_history) < 5:
            return 0.50
        window = self._trade_history[-50:]
        return sum(window) / len(window)

    def _update_state(self):
        wr = self._rolling_wr()
        if wr >= self.NORMAL_THRESHOLD:
            self._state = "NORMAL"
        elif wr >= self.HALT_THRESHOLD:
            self._state = "DEGRADED"
        else:
            self._state = "HALTED"

    def record_outcome(self, won: bool):
        """Record trade outcome for adaptive state tracking."""
        self._trade_history.append(won)
        if len(self._trade_history) > 100:
            self._trade_history = self._trade_history[-50:]
        self._update_state()

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        self._update_state()

        if self._state == "HALTED":
            return []

        picks = self._inner.generate_picks(data)

        if self._state == "DEGRADED":
            for p in picks:
                p.confidence = round(p.confidence * 0.5, 3)
                p.reason = f"[DEGRADED WR={self._rolling_wr():.0%}] {p.reason}"
                p.strategy = self.name
                p.strategy_name = self.display_name
        else:
            for p in picks:
                p.strategy = self.name
                p.strategy_name = self.display_name

        return picks
