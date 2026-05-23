"""
Pick List Generator

Generates actionable daily/weekly pick lists with:
- Conviction score
- Position sizing suggestions
- Stop loss / take profit levels
- Key drivers ("why this pick?")
- Risk warnings
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class PickListGenerator:
    """Generate actionable pick lists with full rationale."""

    def generate(
        self,
        picks: pd.DataFrame,
        prices: Dict[str, float],
        portfolio_value: float = 100000,
        regime: str = "neutral",
    ) -> pd.DataFrame:
        """
        Generate a detailed, actionable pick list.
        
        Adds:
        - Suggested position size (shares + $ value)
        - Entry price
        - Stop loss level
        - Take profit target
        - Risk/reward ratio
        - Key driver explanation
        """
        if picks.empty:
            return pd.DataFrame()

        detailed = []
        for _, row in picks.iterrows():
            ticker = row.get("ticker", "")
            score = row.get("score", 0)
            confidence = row.get("confidence", 0.5)
            category = row.get("category", "momentum")
            conviction = row.get("conviction", "WATCH")

            price = prices.get(ticker, 0)
            if price <= 0:
                continue

            # Position sizing
            if category in ["safe_bet", "dividend_aristocrat", "quality"]:
                max_pct = 0.05
                stop_pct = 0.12
                tp_pct = 0.30
            elif category in ["momentum", "breakout"]:
                max_pct = 0.03
                stop_pct = 0.08
                tp_pct = 0.20
            elif category in ["mean_reversion", "reversal"]:
                max_pct = 0.02
                stop_pct = 0.05
                tp_pct = 0.10
            else:
                max_pct = 0.03
                stop_pct = 0.10
                tp_pct = 0.20

            position_value = portfolio_value * max_pct * confidence
            shares = int(position_value / price)
            actual_value = shares * price

            stop_price = price * (1 - stop_pct)
            tp_price = price * (1 + tp_pct)
            risk_reward = tp_pct / stop_pct if stop_pct > 0 else 0
            risk_amount = actual_value * stop_pct

            detailed.append({
                "rank": row.get("rank", 0),
                "ticker": ticker,
                "conviction": conviction,
                "score": round(score, 3),
                "category": category,
                "entry_price": round(price, 2),
                "shares": shares,
                "position_value": round(actual_value, 2),
                "position_pct": round(actual_value / portfolio_value * 100, 2),
                "stop_loss": round(stop_price, 2),
                "take_profit": round(tp_price, 2),
                "risk_reward": round(risk_reward, 2),
                "risk_amount": round(risk_amount, 2),
                "expected_horizon": row.get("expected_horizon", ""),
                "n_strategies": row.get("n_strategies", 0),
                "key_drivers": row.get("contributing_strategies", ""),
                "regime": regime,
            })

        result = pd.DataFrame(detailed)
        if not result.empty:
            result = result.sort_values("rank")

        return result

    def format_as_text(self, pick_list: pd.DataFrame) -> str:
        """Format pick list as readable text."""
        if pick_list.empty:
            return "No picks available."

        lines = [
            "=" * 80,
            f"  ALPHA ENGINE PICK LIST — {datetime.now().strftime('%Y-%m-%d')}",
            "=" * 80,
            "",
        ]

        for _, row in pick_list.iterrows():
            lines.extend([
                f"  #{row['rank']}  {row['ticker']:6s}  [{row['conviction']}]",
                f"       Score: {row['score']:.3f}  |  Category: {row['category']}",
                f"       Entry: ${row['entry_price']:.2f}  |  Shares: {row['shares']}  |  Value: ${row['position_value']:,.0f} ({row['position_pct']:.1f}%)",
                f"       Stop:  ${row['stop_loss']:.2f}  |  Target: ${row['take_profit']:.2f}  |  R:R = {row['risk_reward']:.1f}:1",
                f"       Risk:  ${row['risk_amount']:,.0f}  |  Horizon: {row['expected_horizon']}",
                f"       Why:   {row['key_drivers'][:70]}",
                f"  {'─' * 76}",
            ])

        total_value = pick_list["position_value"].sum()
        total_risk = pick_list["risk_amount"].sum()
        lines.extend([
            "",
            f"  Total Allocation: ${total_value:,.0f}  |  Total Risk: ${total_risk:,.0f}",
            f"  Picks: {len(pick_list)}  |  Regime: {pick_list['regime'].iloc[0] if len(pick_list) > 0 else 'N/A'}",
            "=" * 80,
        ])

        return "\n".join(lines)

    def to_json(self, pick_list: pd.DataFrame) -> str:
        """Export pick list as JSON for API consumption."""
        if pick_list.empty:
            return "[]"
        return pick_list.to_json(orient="records", indent=2)
