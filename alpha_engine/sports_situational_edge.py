#!/usr/bin/env python3
"""
sports_situational_edge.py
==========================
Research-backed situational adjustments to "true" win probabilities.
These edges are derived from academic literature and sharp-betting
communities, NOT from prediction markets.

Methodologies implemented:
- NBA rest advantage (Entine & Small 2008; back-to-back fatigue)
- NHL back-to-back / goalie-start effects
- MLB divisional underdogs in low-total games
- NFL key-number + home-underdog bias
- Soccer draw bias in low-scoring leagues

Usage:
    from alpha_engine.sports_situational_edge import SituationalEdgeEngine
    engine = SituationalEdgeEngine()
    adj = engine.adjust_nba_prob(home_prob=0.55, home_rest=3, away_rest=0)
"""
from __future__ import annotations

from typing import Dict, List, Optional


class SituationalEdgeEngine:
    """Applies situational adjustments based on sport-specific research."""

    # ------------------------------------------------------------------
    # NBA
    # ------------------------------------------------------------------
    def adjust_nba_prob(
        self,
        home_prob: float,
        home_rest: int = 1,
        away_rest: int = 1,
        home_b2b: bool = False,
        away_b2b: bool = False,
    ) -> Dict[str, float]:
        """
        Adjust home win probability for rest differentials.

        Research:
        - Back-to-back games reduce win probability by ~6-8% (Dean Oliver 2004).
        - Each additional day of rest above opponent adds ~1.5% (Entine & Small 2008).
        """
        adj = 0.0
        if home_b2b and not away_b2b:
            adj -= 0.065
        elif away_b2b and not home_b2b:
            adj += 0.065
        rest_diff = home_rest - away_rest
        if abs(rest_diff) >= 2:
            adj += 0.015 * rest_diff
        new_prob = max(0.05, min(0.95, home_prob + adj))
        return {
            "base_prob": round(home_prob, 4),
            "adjusted_prob": round(new_prob, 4),
            "adjustment": round(adj, 4),
            "edge_label": self._label(adj),
        }

    # ------------------------------------------------------------------
    # NHL
    # ------------------------------------------------------------------
    def adjust_nhl_prob(
        self,
        home_prob: float,
        home_b2b: bool = False,
        away_b2b: bool = False,
        home_goalie_starts_3in4: bool = False,
    ) -> Dict[str, float]:
        """
        NHL back-to-back fatigue is well documented (Hockey Graphs 2014).
        Goalie fatigue (3 starts in 4 nights) adds an extra ~3% edge.
        """
        adj = 0.0
        if home_b2b and not away_b2b:
            adj -= 0.055
        elif away_b2b and not home_b2b:
            adj += 0.055
        if home_goalie_starts_3in4:
            adj -= 0.030
        new_prob = max(0.05, min(0.95, home_prob + adj))
        return {
            "base_prob": round(home_prob, 4),
            "adjusted_prob": round(new_prob, 4),
            "adjustment": round(adj, 4),
            "edge_label": self._label(adj),
        }

    # ------------------------------------------------------------------
    # MLB
    # ------------------------------------------------------------------
    def adjust_mlb_prob(
        self,
        underdog_prob: float,
        is_divisional: bool = False,
        total_line: Optional[float] = None,
        is_home: bool = False,
    ) -> Dict[str, float]:
        """
        Divisional underdogs in low-total games show positive ROI
        (Sabermetric research, 2017-2020).
        Low totals (< 7.5) + divisional familiarity = underdog value.
        Home underdogs get a small boost.
        """
        adj = 0.0
        if is_divisional:
            adj += 0.020
        if total_line is not None and total_line < 7.5:
            adj += 0.015
        if is_home:
            adj += 0.010
        new_prob = max(0.05, min(0.95, underdog_prob + adj))
        return {
            "base_prob": round(underdog_prob, 4),
            "adjusted_prob": round(new_prob, 4),
            "adjustment": round(adj, 4),
            "edge_label": self._label(adj),
        }

    # ------------------------------------------------------------------
    # NFL
    # ------------------------------------------------------------------
    def adjust_nfl_prob(
        self,
        dog_prob: float,
        spread: float = 0.0,
        is_divisional: bool = False,
        is_home: bool = False,
        wind_mph: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        NFL key numbers (3, 7) matter enormously.
        Home dogs +3 or less in divisional games historically cover ~54%.
        Wind > 15 mph suppresses scoring and helps dogs.
        """
        adj = 0.0
        if is_divisional and is_home and spread >= -3.0:
            adj += 0.030
        if wind_mph is not None and wind_mph > 15.0:
            adj += 0.020
        new_prob = max(0.05, min(0.95, dog_prob + adj))
        return {
            "base_prob": round(dog_prob, 4),
            "adjusted_prob": round(new_prob, 4),
            "adjustment": round(adj, 4),
            "edge_label": self._label(adj),
        }

    # ------------------------------------------------------------------
    # Soccer
    # ------------------------------------------------------------------
    def adjust_soccer_draw_prob(
        self,
        draw_prob: float,
        total_line: Optional[float] = None,
        league_low_scoring: bool = False,
    ) -> Dict[str, float]:
        """
        In low-scoring leagues (Ligue 1, Serie A historically), the draw
        is often underpriced when totals are set <= 2.5.
        """
        adj = 0.0
        if league_low_scoring:
            adj += 0.015
        if total_line is not None and total_line <= 2.5:
            adj += 0.010
        new_prob = max(0.05, min(0.95, draw_prob + adj))
        return {
            "base_prob": round(draw_prob, 4),
            "adjusted_prob": round(new_prob, 4),
            "adjustment": round(adj, 4),
            "edge_label": self._label(adj),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _label(self, adj: float) -> str:
        if adj >= 0.04:
            return "strong_edge"
        if adj >= 0.02:
            return "moderate_edge"
        if adj >= 0.01:
            return "slight_edge"
        if adj <= -0.02:
            return "negative_edge"
        return "neutral"


# ------------------------------------------------------------------
# CLI / Standalone
# ------------------------------------------------------------------
if __name__ == "__main__":
    import json

    engine = SituationalEdgeEngine()
    examples = [
        ("NBA home fav vs B2B visitor", engine.adjust_nba_prob(0.60, home_rest=2, away_rest=0, away_b2b=True)),
        ("NHL rested home vs B2B", engine.adjust_nhl_prob(0.52, away_b2b=True)),
        ("MLB divisional home dog low total", engine.adjust_mlb_prob(0.38, is_divisional=True, total_line=7.0, is_home=True)),
        ("NFL home dog +3 divisional windy", engine.adjust_nfl_prob(0.45, spread=-3.0, is_divisional=True, is_home=True, wind_mph=18)),
        ("Soccer draw low total", engine.adjust_soccer_draw_prob(0.28, total_line=2.5, league_low_scoring=True)),
    ]
    for label, result in examples:
        print(f"{label}: {json.dumps(result)}")
