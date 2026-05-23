"""Funding Rate Carry - short overheated perps (funding > 0.05%), long underfunded."""
from typing import List
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from paper_trading.helpers import fetch_json, rate_limited, cached

HIGH_FUNDING_THRESHOLD = 0.0005
LOW_FUNDING_THRESHOLD = -0.0003
TP_PCT = 0.04
SL_PCT = 0.025


class FundingRateCarry(BaseStrategy):
    name = "funding_rate_carry"
    display_name = "Funding Rate Carry"
    source = "Binance Futures"
    category = "derivatives"
    portfolio_type = "derivatives"

    @rate_limited("binance_futures", 0.5)
    @cached(ttl_seconds=1800)
    def fetch_data(self) -> dict:
        data = fetch_json("https://fapi.binance.com/fapi/v1/premiumIndex")
        return {"funding_rates": data}

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        rates = data.get("funding_rates", [])

        for item in rates:
            symbol = item.get("symbol", "")
            if not symbol.endswith("USDT"):
                continue

            funding = float(item.get("lastFundingRate", 0))
            mark_price = float(item.get("markPrice", 0))

            if mark_price <= 0:
                continue

            if funding > HIGH_FUNDING_THRESHOLD:
                direction = "SHORT"
                tp = round(mark_price * (1 - TP_PCT), 6)
                sl = round(mark_price * (1 + SL_PCT), 6)
                confidence = min(0.85, 0.5 + (funding - HIGH_FUNDING_THRESHOLD) * 500)
                reason = f"High funding {funding*100:.4f}% -> short carry"
            elif funding < LOW_FUNDING_THRESHOLD:
                direction = "LONG"
                tp = round(mark_price * (1 + TP_PCT), 6)
                sl = round(mark_price * (1 - SL_PCT), 6)
                confidence = min(0.85, 0.5 + abs(funding - LOW_FUNDING_THRESHOLD) * 500)
                reason = f"Negative funding {funding*100:.4f}% -> long carry"
            else:
                continue

            picks.append(NormalizedPick(
                symbol=symbol,
                direction=direction,
                entry_price=mark_price,
                tp=tp,
                sl=sl,
                strategy=self.name,
                strategy_name=self.display_name,
                category=self.category,
                confidence=round(confidence, 3),
                reason=reason,
                raw_signal={"funding_rate": funding, "mark_price": mark_price},
            ))

        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]
