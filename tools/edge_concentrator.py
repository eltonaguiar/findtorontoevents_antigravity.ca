"""Hard risk/quality concentrator layer — sits above the pick pipeline.

Reduces 110 picks/week → 5-10 elite picks via:
  - Rolling 20d IC filter (kills anti-predictive strategy families)
  - Tier filter (WR>50%, PF>1.30, n>50 in 90d)
  - Regime routing (BULL/BEAR/CHOPPY caps)
  - 7d PF auto-pause (48h halt when PF<1.0)
  - Max 3 concurrent positions, 25% capital cap

## Wiring Plan
Target caller: audit_trail/quality_gates.py::passes_smart_gate() or
               alpha_engine/smart_picks_engine.py::run()
Integration: wrap the final pick list in EdgeConcentrator().apply(picks_df, regime)
             before returning to the TV paper-trade or real-money sizing step.
Target PR: after 30-day shadow comparison confirms WR lift >= +5pp
"""

# edge_concentrator.py

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# ============================================================
# CONFIG
# ============================================================

ROLLING_IC_WINDOW_DAYS = 20
IC_MIN_THRESHOLD = 0.05

TIER_MIN_WR = 0.50
TIER_MIN_PF = 1.30
TIER_MIN_TRADES = 50
TIER_LOOKBACK_DAYS = 90

AUTO_PAUSE_LOOKBACK_DAYS = 7
AUTO_PAUSE_MIN_TRADES = 20
AUTO_PAUSE_MIN_PF = 1.0
AUTO_PAUSE_DURATION_HOURS = 48

ATR_MULTIPLIER = 2.0

MAX_CONCURRENT_POSITIONS = 3
MAX_POSITION_CAPITAL = 0.25

# ============================================================
# UTILS
# ============================================================

def profit_factor(pnl_series: pd.Series) -> float:
    gains = pnl_series[pnl_series > 0].sum()
    losses = -pnl_series[pnl_series < 0].sum()
    if losses == 0:
        return np.inf
    return gains / losses


def win_rate(pnl_series: pd.Series) -> float:
    if len(pnl_series) == 0:
        return 0.0
    return (pnl_series > 0).mean()


def information_coefficient(scores: pd.Series, pnl: pd.Series) -> float:
    if len(scores) < 5:
        return 0.0
    return scores.corr(pnl, method="spearman")


# ============================================================
# CORE ENGINE
# ============================================================

class EdgeConcentrator:

    def __init__(self):
        self.paused_until: Optional[datetime] = None
        self.active_positions = 0

    def filter_by_ic(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        allowed_families = []
        for family, g in df.groupby("family"):
            recent = g[g["date"] >= df["date"].max() - timedelta(days=ROLLING_IC_WINDOW_DAYS)]
            ic = information_coefficient(recent["score"], recent["pnl"])
            if ic >= IC_MIN_THRESHOLD:
                allowed_families.append(family)
        return df[df["family"].isin(allowed_families)]

    def filter_by_tier(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        cutoff = df["date"].max() - timedelta(days=TIER_LOOKBACK_DAYS)
        recent = df[df["date"] >= cutoff]
        allowed_families = []
        for family, g in recent.groupby("family"):
            if len(g) < TIER_MIN_TRADES:
                continue
            if win_rate(g["pnl"]) > TIER_MIN_WR and profit_factor(g["pnl"]) > TIER_MIN_PF:
                allowed_families.append(family)
        return df[df["family"].isin(allowed_families)]

    def apply_atr_stop(self, entry_price: float, atr_value: float, side: str) -> float:
        if side.lower() == "long":
            return entry_price - ATR_MULTIPLIER * atr_value
        return entry_price + ATR_MULTIPLIER * atr_value

    def regime_limit(self, regime: str) -> int:
        return {"CHOPPY": 4, "BULL": 10, "BEAR": 7}.get(regime, 5)

    def route_by_regime(self, df: pd.DataFrame, regime: str) -> pd.DataFrame:
        df = df.copy()
        if regime == "BEAR":
            df = df[df["side"] == "short"]
        return df.sort_values("score", ascending=False).head(self.regime_limit(regime))

    def check_auto_pause(self, df: pd.DataFrame) -> None:
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        cutoff = df["date"].max() - timedelta(days=AUTO_PAUSE_LOOKBACK_DAYS)
        recent = df[df["date"] >= cutoff]
        if len(recent) >= AUTO_PAUSE_MIN_TRADES and profit_factor(recent["pnl"]) < AUTO_PAUSE_MIN_PF:
            self.paused_until = datetime.utcnow() + timedelta(hours=AUTO_PAUSE_DURATION_HOURS)

    def is_paused(self) -> bool:
        return self.paused_until is not None and datetime.utcnow() < self.paused_until

    def can_open_position(self) -> bool:
        return self.active_positions < MAX_CONCURRENT_POSITIONS

    def position_size(self, kelly_fraction: float) -> float:
        return min(kelly_fraction, MAX_POSITION_CAPITAL)

    def apply(self, df: pd.DataFrame, regime: str) -> pd.DataFrame:
        if self.is_paused():
            print("SYSTEM PAUSED — EdgeConcentrator auto-pause active")
            return pd.DataFrame()
        df = self.filter_by_ic(df)
        df = self.filter_by_tier(df)
        return self.route_by_regime(df, regime)


def demo(csv_path: str) -> None:
    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"])
    before_pf = profit_factor(df["pnl"])
    before_wr = win_rate(df["pnl"])
    concentrator = EdgeConcentrator()
    df["regime"] = np.random.choice(["BULL", "BEAR", "CHOPPY"], size=len(df))
    filtered = pd.concat([concentrator.apply(df[df["regime"] == r], r) for r in ["BULL", "BEAR", "CHOPPY"]])
    print(f"Before: WR={before_wr:.1%} PF={before_pf:.2f} n={len(df)}")
    print(f"After:  WR={win_rate(filtered['pnl']):.1%} PF={profit_factor(filtered['pnl']):.2f} n={len(filtered)}")
    print(f"Reduction: {(1 - len(filtered)/len(df)):.1%}")


if __name__ == "__main__":
    demo("closed_picks.csv")
