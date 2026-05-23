"""Base strategy interface and Signal container."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class Signal:
    """A trading signal emitted by a strategy."""
    symbol: str
    direction: str          # "LONG" or "SHORT"
    strategy: str           # strategy function name
    confidence: float       # 0.0 to 1.0
    reason: str
    ratios: Dict = field(default_factory=dict)
    entry_price: float = 0.0
    take_profit: float = 0.0
    stop_loss: float = 0.0
    signal_id: str = ""
    generated_at: str = ""

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).isoformat()
        if not self.signal_id:
            self.signal_id = f"{self.strategy}::{self.symbol}::{self.generated_at[:19]}"

    def to_dict(self) -> Dict:
        return {
            "signal_id": self.signal_id,
            "symbol": self.symbol,
            "direction": self.direction,
            "strategy": self.strategy,
            "confidence": self.confidence,
            "reason": self.reason,
            "ratios": self.ratios,
            "entry_price": self.entry_price,
            "take_profit": self.take_profit,
            "stop_loss": self.stop_loss,
            "generated_at": self.generated_at,
            "source": "coinglass_strategies",
        }
