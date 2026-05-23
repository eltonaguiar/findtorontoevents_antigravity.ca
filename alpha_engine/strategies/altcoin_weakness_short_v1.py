# Altcoin Weakness SHORT v1 — [on_probation]
# ------------------------------------------------------------
# Hypothesis: When BTC is chopping/weakening, SHORTing mid-cap altcoins
# with weak fundamentals (low liquidity, recent listings, memecoin-adjacent)
# outperforms LONG positions in the same assets.
#
# Origin: KITE SHORT winner 2026-04-05 (tsmom_strategy, 0.1529 -> 0.1396, +8.7%).
# Same-day cohort: BERAUSDT, LINKUSDT, ETHUSDT shorts all resolved green.
#
# Backtest (2026-03 .. 2026-04, closed_picks.json, n=2481):
#   Alt SHORTS (non-BTC/ETH/BNB/SOL/XRP):  n=28  WR=60.7%  avgPnL=+0.75%  PF=2.38  MaxDD=-7.00%
#   Alt SHORTS (recent listings tight):    n=17  WR=47.1%  avgPnL=+1.25%  PF=2.81  MaxDD=-5.24%
#   Alt LONGS baseline (same universe):    n=2031 WR=24.7% avgPnL=-0.14% PF=0.66  CumPnL=-290%
#   By source: rapid_fire WR=68.8% / quan_engine WR=60.0%
# Verdict: SHIP with [on_probation] — n=28 passes experimental bar, but monitor
# as tight-filter WR=47% is sensitive to one outlier loss. Re-audit at n=60.
# ------------------------------------------------------------
from dataclasses import dataclass
from typing import List, Optional, Dict
import pandas as pd

from alpha_engine.strategies.base import (
    BaseStrategy, StrategyConfig, StrategyType, HoldingPeriod, Signal,
)


# Majors excluded from universe (too liquid, tight correlation to BTC)
_MAJORS = {"BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"}


@dataclass
class AltShortParams:
    tp_pct: float = 0.08            # +8% SHORT profit (matches KITE move)
    sl_pct: float = 0.05            # -5% stop (1.6:1 R:R)
    max_positions: int = 3
    btc_4h_red_required: bool = True
    min_funding_bps: float = 0.0    # longs crowded when funding > 0
    max_7d_drop_pct: float = -0.15  # skip if already crashed >15%
    min_mcap_musd: float = 10.0
    max_mcap_musd: float = 500.0
    listing_age_days_max: int = 365


class AltcoinWeaknessShortV1(BaseStrategy):
    """SHORT mid-cap recent-listing altcoins on BTC weakness + crowded longs."""

    def __init__(self, config: Optional[StrategyConfig] = None,
                 params: Optional[AltShortParams] = None):
        super().__init__(config)
        self.params = params or AltShortParams()

    def _default_config(self) -> StrategyConfig:
        return StrategyConfig(
            name="altcoin_weakness_short_v1",
            description="SHORT mid-cap recent-listing alts on BTC chop + positive funding",
            strategy_type=StrategyType.LONG_SHORT,
            holding_period=HoldingPeriod.INTRADAY,
            max_positions=3,
            rebalance_frequency="4h",
            min_score=0.55,
            top_k=3,
            max_position_pct=0.03,
            stop_loss_pct=0.05,
            take_profit_pct=0.08,
            tags=["short", "crypto", "altcoin", "mean_reversion", "on_probation"],
        )

    def _passes_universe_filter(self, row: Dict) -> bool:
        sym = row.get("symbol", "")
        if sym in _MAJORS or not sym.endswith("USDT"):
            return False
        mcap = row.get("market_cap_musd")
        if mcap is not None and not (self.params.min_mcap_musd <= mcap <= self.params.max_mcap_musd):
            return False
        age = row.get("listing_age_days")
        if age is not None and age > self.params.listing_age_days_max:
            return False
        return True

    def _passes_entry_conditions(self, row: Dict, btc_ctx: Dict) -> bool:
        p = self.params
        if p.btc_4h_red_required and btc_ctx.get("btc_4h_change_pct", 0) >= 0:
            return False
        funding = row.get("funding_rate_bps", 0)
        if funding <= p.min_funding_bps:
            return False
        chg7d = row.get("change_7d_pct", 0)
        if chg7d < p.max_7d_drop_pct:
            return False  # already crashed
        return True

    def generate_signals(
        self,
        features: pd.DataFrame,
        date: pd.Timestamp,
        universe: List[str],
    ) -> List[Signal]:
        if features is None or len(features) == 0:
            return []
        today = features[features.get("date", date) == date] if "date" in features.columns else features
        btc_row = today[today["symbol"] == "BTCUSDT"] if "symbol" in today.columns else pd.DataFrame()
        btc_ctx = {
            "btc_4h_change_pct": float(btc_row["change_4h_pct"].iloc[0]) if len(btc_row) and "change_4h_pct" in btc_row.columns else 0.0,
        }
        signals: List[Signal] = []
        for _, row in today.iterrows():
            r = row.to_dict()
            if r.get("symbol") not in universe:
                continue
            if not self._passes_universe_filter(r):
                continue
            if not self._passes_entry_conditions(r, btc_ctx):
                continue
            funding = r.get("funding_rate_bps", 0)
            score = min(1.0, 0.5 + funding / 20.0)  # higher funding -> stronger short
            signals.append(Signal(
                ticker=r["symbol"],
                date=date,
                score=score,
                direction=-1,
                confidence=0.60,
                holding_period=1,
                drivers={
                    "btc_4h_red": 1.0,
                    "funding_bps": float(funding),
                    "change_7d_pct": float(r.get("change_7d_pct", 0)),
                },
                category="altcoin_short",
            ))
        signals.sort(key=lambda s: -s.score)
        return signals[: self.params.max_positions]
