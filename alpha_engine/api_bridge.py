"""
PHP API Bridge

Exports Alpha Engine picks in a format compatible with the existing
findstocks PHP frontend. Generates JSON that can be consumed by the
portfolio dashboard.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class APIBridge:
    """
    Bridge between Alpha Engine (Python) and findstocks (PHP).
    
    Exports picks, backtests, and metrics as JSON files that
    the PHP API can serve to the frontend.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        from . import config
        self.output_dir = output_dir or config.OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_picks(self, picks: pd.DataFrame, filename: str = "alpha_picks.json") -> Path:
        """
        Export picks in findstocks-compatible format.
        
        Format matches the existing stock_picks table schema:
        {ticker, algorithm, score, rating, risk_level, pick_date, notes}
        """
        if picks.empty:
            return self._write_json([], filename)

        records = []
        for _, row in picks.iterrows():
            score = row.get("score", 0)
            records.append({
                "ticker": row.get("ticker", ""),
                "algorithm": f"alpha_{row.get('category', 'mixed')}",
                "score": round(score * 100, 1),  # Scale to 0-100
                "rating": self._score_to_rating(score),
                "risk_level": self._category_to_risk(row.get("category", "")),
                "pick_date": datetime.now().strftime("%Y-%m-%d"),
                "notes": row.get("contributing_strategies", ""),
                "conviction": row.get("conviction", ""),
                "entry_price": row.get("entry_price", 0),
                "stop_loss": row.get("stop_loss", 0),
                "take_profit": row.get("take_profit", 0),
                "position_pct": row.get("position_pct", 0),
                "expected_horizon": row.get("expected_horizon", ""),
                "regime": row.get("regime", "neutral"),
            })

        return self._write_json(records, filename)

    def export_algorithms(self, filename: str = "alpha_algorithms.json") -> Path:
        """Export algorithm definitions for the frontend."""
        algorithms = [
            {"name": "alpha_momentum", "display_name": "Alpha Momentum", "description": "Classic + trend + breakout momentum", "family": "momentum"},
            {"name": "alpha_mean_reversion", "display_name": "Alpha Mean Reversion", "description": "Bollinger + reversal strategies", "family": "mean_reversion"},
            {"name": "alpha_earnings_drift", "display_name": "Alpha Earnings Drift", "description": "PEAD + consecutive beats", "family": "earnings"},
            {"name": "alpha_quality", "display_name": "Alpha Quality", "description": "Quality compounders + ROIC + FCF", "family": "quality"},
            {"name": "alpha_value", "display_name": "Alpha Value+Quality", "description": "Value investing with quality filter", "family": "value"},
            {"name": "alpha_dividend", "display_name": "Alpha Dividend Aristocrats", "description": "25+ years consecutive div increases", "family": "dividend"},
            {"name": "alpha_safe_bet", "display_name": "Alpha Safe Bet", "description": "3+ consecutive earnings beats >5%", "family": "safe_bet"},
            {"name": "alpha_ml_ranker", "display_name": "Alpha ML Ranker", "description": "LightGBM cross-sectional ranker", "family": "ml"},
            {"name": "alpha_meta_ensemble", "display_name": "Alpha Meta Ensemble", "description": "Regime-aware multi-strategy ensemble", "family": "ensemble"},
        ]
        return self._write_json(algorithms, filename)

    def export_regime(self, regime_data: Dict, filename: str = "alpha_regime.json") -> Path:
        """Export current regime data for the frontend dashboard."""
        # Clean up non-serializable values
        clean = {}
        for k, v in regime_data.items():
            if isinstance(v, (str, int, float, bool)):
                clean[k] = v
            elif hasattr(v, "item"):  # numpy types
                clean[k] = v.item()
        clean["updated_at"] = datetime.now().isoformat()
        return self._write_json(clean, filename)

    def export_backtest_results(self, results: Dict, filename: str = "alpha_backtests.json") -> Path:
        """Export backtest results for the frontend."""
        records = []
        for name, result in results.items():
            records.append({
                "strategy": name,
                "total_return_pct": result.total_return_pct,
                "annual_return_pct": result.annual_return_pct,
                "sharpe_ratio": result.sharpe_ratio,
                "sortino_ratio": result.sortino_ratio,
                "max_drawdown_pct": result.max_drawdown_pct,
                "win_rate": result.win_rate,
                "profit_factor": result.profit_factor,
                "total_trades": result.total_trades,
                "total_costs": result.total_costs,
            })
        return self._write_json(records, filename)

    def _write_json(self, data, filename: str) -> Path:
        """Write JSON file."""
        filepath = self.output_dir / filename
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
        logger.info(f"Exported {filename}")
        return filepath

    def _score_to_rating(self, score: float) -> str:
        if score >= 0.8:
            return "Strong Buy"
        elif score >= 0.6:
            return "Buy"
        elif score >= 0.4:
            return "Moderate Buy"
        elif score >= 0.2:
            return "Hold"
        return "Watch"

    def _category_to_risk(self, category: str) -> str:
        low_risk = {"safe_bet", "dividend_aristocrat", "quality", "dividend"}
        med_risk = {"value", "earnings_drift", "momentum"}
        if category in low_risk:
            return "Low"
        elif category in med_risk:
            return "Medium"
        return "High"
