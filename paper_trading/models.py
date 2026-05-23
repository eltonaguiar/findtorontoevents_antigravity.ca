"""Data models for picks, portfolios, and performance metrics."""
from dataclasses import dataclass, field, asdict
from typing import Optional, List
from datetime import datetime, timezone


@dataclass
class NormalizedPick:
    symbol: str                                     # e.g. "BTCUSDT"
    direction: str                                  # "LONG" or "SHORT"
    entry_price: float
    tp: float
    sl: float
    strategy: str                                   # e.g. "defi_tvl_momentum"
    strategy_name: str                              # e.g. "DeFi TVL Momentum"
    category: str                                   # "crypto", "defi", "derivatives"
    confidence: float = 0.5                         # 0-1
    reason: str = ""
    raw_signal: Optional[dict] = None
    risk_reward: float = 0.0
    picked_at: str = ""
    expires_at: Optional[str] = None
    id: str = ""

    def __post_init__(self):
        if not self.picked_at:
            self.picked_at = datetime.now(timezone.utc).isoformat()
        if not self.id:
            date_part = self.picked_at[:10]
            self.id = f"{self.strategy}::{self.symbol}::{date_part}"
        if self.risk_reward == 0 and self.entry_price and self.sl:
            dist_tp = abs(self.tp - self.entry_price)
            dist_sl = abs(self.entry_price - self.sl)
            self.risk_reward = round(dist_tp / dist_sl, 2) if dist_sl > 0 else 0

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}
