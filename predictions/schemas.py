"""Pydantic schemas for the Social Media Prediction Competition."""
from __future__ import annotations
from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


class Prediction(BaseModel):
    predictor_id: str = Field(description="Platform-prefixed ID, e.g. tv:CryptoCapo")
    platform: Literal["tradingview", "reddit", "twitter", "blog", "youtube"]
    symbol: str = Field(description="Trading pair, e.g. BTCUSDT")
    direction: Literal["LONG", "SHORT"]
    entry_price: Optional[float] = None
    take_profit: Optional[float] = None
    stop_loss: Optional[float] = None
    sentiment_score: Optional[float] = Field(None, ge=-1.0, le=1.0)
    source_url: Optional[str] = None
    source_text: Optional[str] = None
    scraped_at: datetime = Field(default_factory=lambda: datetime.utcnow())


class PredictorStats(BaseModel):
    predictor_id: str
    platform: str
    display_name: str = ""
    total_predictions: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    avg_pnl_pct: float = 0.0
    best_pick_pnl: Optional[float] = None
    worst_pick_pnl: Optional[float] = None
    sharpe: float = 0.0
    tier: Literal["ELITE", "PROVEN", "MIXED", "LOSING", "UNRANKED"] = "UNRANKED"
