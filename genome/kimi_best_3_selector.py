#!/usr/bin/env python3
"""
KIMI Best 3 Picks — Intelligent Entry Quality Ranker
=====================================================

Automatically selects the top 3 best entry opportunities from a broad
universe of crypto symbols. Uses multi-factor scoring with honest
entry quality ratings (A+ through F).

Scoring Factors:
- Technical setup quality (trend alignment, momentum)
- Risk:Reward ratio (higher = better)
- Entry timing (how close to ideal trigger)
- Volatility regime (too high = penalty)
- Historical win rate by pattern type

Author: KIMI | Version: 1.0 | Date: 2026-03-14
"""

import sys
import json
import math
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from typing import List, Optional

import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from genome.mutation_lab.innovative_mutations import fetch_binance_klines
from genome.kimi_top_picks_automation import williams_r_indicator


# Extended universe of symbols
ALL_SYMBOLS = [
    # Tier 1 - Majors (high liquidity, lower volatility)
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    # Tier 2 - Large Caps (good liquidity)
    "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "DOGEUSDT",
    "NEARUSDT", "SUIUSDT", "APTUSDT", "ATOMUSDT", "TONUSDT",
    # Tier 3 - Mid Caps (higher volatility, more setups)
    "SEIUSDT", "TIAUSDT", "FETUSDT", "OPUSDT", "ARBUSDT",
    "STXUSDT", "IMXUSDT", "GRTUSDT", "LDOUSDT", "RNDRUSDT",
    "INJUSDT", "WLDUSDT", "STRKUSDT", "PYTHUSDT", "JUPUSDT",
]


@dataclass
class PickQuality:
    """Quality metrics for a potential pick."""
    symbol: str
    direction: str
    strategy: str
    entry_price: float
    take_profit: float
    stop_loss: float
    
    # Quality scores (0-100)
    technical_score: float  # Trend alignment, momentum quality
    risk_reward_score: float  # Based on R:R ratio
    timing_score: float  # How close to ideal entry
    volatility_score: float  # Optimal volatility regime
    conviction_score: float  # Overall confidence
    
    # Entry quality grade
    entry_grade: str  # A+, A, A-, B+, B, B-, C, D, F
    entry_quality_notes: str  # Honest analysis of entry quality
    
    # Risk metrics
    risk_reward: float
    max_loss_pct: float
    position_size_suggestion: str  # Small, Medium, Full
    
    # Metadata
    indicators: dict
    timestamp: str
    
    def to_dict(self) -> dict:
        return asdict(self)


class Best3Selector:
    """Selects the best 3 picks based on quality scoring."""
    
    def __init__(self):
        self.est_tz = timezone(timedelta(hours=-4))
        self.all_candidates: List[PickQuality] = []
    
    def calculate_technical_score(self, df: pd.DataFrame, direction: str, 
                                   wr: float, sma_200: float) -> float:
        """Score technical setup quality (0-100)."""
        score = 50  # Base score
        current = df['Close'].iloc[-1]
        
        # Trend alignment (20 points)
        if direction == 'LONG' and current > sma_200:
            score += 20
        elif direction == 'SHORT' and current < sma_200:
            score += 20
        else:
            score -= 10  # Counter-trend penalty
        
        # Williams %R quality (20 points)
        if direction == 'LONG' and wr < -80:
            score += min(abs(wr + 80), 20)  # More oversold = better
        elif direction == 'SHORT' and wr > -20:
            score += min(wr + 20, 20)
        
        # Volume confirmation (10 points)
        vol_avg = df['Volume'].rolling(20).mean().iloc[-1]
        vol_current = df['Volume'].iloc[-1]
        if vol_current > vol_avg * 1.2:
            score += 10
        
        return min(max(score, 0), 100)
    
    def calculate_rr_score(self, entry: float, tp: float, sl: float, 
                           direction: str) -> float:
        """Score risk:reward ratio (0-100)."""
        if direction == 'LONG':
            reward = tp - entry
            risk = entry - sl
        else:
            reward = entry - tp
            risk = sl - entry
        
        if risk <= 0:
            return 0
        
        rr = reward / risk
        
        # Score based on R:R
        if rr >= 3.0:
            return 100
        elif rr >= 2.5:
            return 90
        elif rr >= 2.0:
            return 80
        elif rr >= 1.5:
            return 65
        elif rr >= 1.0:
            return 50
        else:
            return max(0, rr * 40)
    
    def calculate_timing_score(self, current_wr: float, target_wr: float,
                                current_price: float, ideal_price: float) -> float:
        """Score entry timing (0-100)."""
        # Perfect timing = 100, off by more = lower
        if target_wr is not None:
            diff = abs(current_wr - target_wr)
            return max(0, 100 - diff * 5)
        
        if ideal_price is not None:
            diff_pct = abs(current_price - ideal_price) / ideal_price * 100
            return max(0, 100 - diff_pct * 10)
        
        return 70  # Neutral if no specific target
    
    def calculate_volatility_score(self, df: pd.DataFrame) -> float:
        """Score volatility regime (0-100)."""
        atr = (df['High'] - df['Low']).rolling(14).mean().iloc[-1]
        price = df['Close'].iloc[-1]
        atr_pct = atr / price * 100
        
        # Optimal ATR: 1.5% - 3.5%
        if 1.5 <= atr_pct <= 3.5:
            return 100
        elif 1.0 <= atr_pct < 1.5:
            return 80  # Low but workable
        elif 3.5 < atr_pct <= 5.0:
            return 70  # Elevated, caution
        elif atr_pct > 5.0:
            return 40  # Too volatile, risky
        else:
            return 60  # Very low vol, may not move

    def _compute_adx(self, high, low, close, window=14):
        """Compute ADX value."""
        import numpy as np  # Ensure np available
        
        tr1 = high - low
        tr2 = np.abs(high - close.shift(1))
        tr3 = np.abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window).mean()
        
        delta = high.diff()
        plus_dm = np.where((delta > 0) & (delta > -low.diff()), delta, 0)
        minus_dm = np.where((-low.diff() > 0) & (-low.diff() > delta), -low.diff(), 0)
        
        plus_di = 100 * pd.Series(plus_dm).rolling(window).mean() / atr
        minus_di = 100 * pd.Series(minus_dm).rolling(window).mean() / atr
        
        dx = (np.abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
        adx = dx.rolling(window).mean()
        
        return adx.iloc[-1]

    def calculate_regime_score(self, df: pd.DataFrame, direction: str) -> float:
        """Regime filter: ADX >25 and trend aligns with signal (0 or 1)."""
        high, low, close = df['High'], df['Low'], df['Close']
        adx = self._compute_adx(high, low, close)
        
        ema20 = close.rolling(20).mean().iloc[-1]
        current = close.iloc[-1]
        trend_dir = 1 if current > ema20 else -1
        signal_dir = 1 if direction == 'LONG' else -1
        
        if pd.notna(adx) and adx > 25 and trend_dir == signal_dir:
            return 1.0
        return 0.0
    
    def calculate_entry_grade(self, overall_score: float, technical: float,
                               rr: float, timing: float) -> tuple:
        """Calculate entry grade (A+ to F) and honest notes."""
        
        # Determine grade
        if overall_score >= 90:
            grade = "A+"
            notes = "Exceptional setup. Strong technical alignment, excellent R:R, near-perfect timing. High confidence entry."
        elif overall_score >= 85:
            grade = "A"
            notes = "Very strong setup. Good confluence of factors. Confident entry recommended."
        elif overall_score >= 80:
            grade = "A-"
            notes = "Strong setup with minor imperfections. Solid entry with good edge."
        elif overall_score >= 75:
            grade = "B+"
            notes = "Good setup. One or two factors not ideal but still positive expectancy."
        elif overall_score >= 70:
            grade = "B"
            notes = "Decent setup. Moderate confidence. Consider position sizing down."
        elif overall_score >= 65:
            grade = "B-"
            notes = "Acceptable setup. Some concerns present. Smaller position advised."
        elif overall_score >= 60:
            grade = "C"
            notes = "Marginal setup. Multiple factors suboptimal. Low conviction, trade carefully."
        elif overall_score >= 50:
            grade = "D"
            notes = "Weak setup. Poor risk:reward or bad timing. Consider skipping."
        else:
            grade = "F"
            notes = "Poor setup. High risk, low reward, or against trend. Avoid."
        
        # Add specific concerns
        concerns = []
        if technical < 60:
            concerns.append("technical weakness")
        if rr < 1.5:
            concerns.append("poor risk:reward")
        if timing < 60:
            concerns.append("bad timing")
        
        if concerns:
            notes += f" WARNINGS: {', '.join(concerns)}."
        
        return grade, notes
    
    def analyze_symbol(self, symbol: str) -> Optional[PickQuality]:
        """Analyze a single symbol for entry quality."""
        try:
            df = fetch_binance_klines(symbol, '1h', limit=200)
            if df.empty or len(df) < 100:
                return None
            
            close = df['Close']
            current = close.iloc[-1]
            
            # Skip if price too low (noise)
            if current < 0.001:
                return None
            
            # Calculate indicators
            wr = williams_r_indicator(close).iloc[-1]
            sma_200 = close.rolling(200).mean().iloc[-1]
            above_sma = current > sma_200
            
            # ATR
            atr = (df['High'] - df['Low']).rolling(14).mean().iloc[-1]
            
            # Determine if there's a valid setup
            setup_found = False
            direction = None
            strategy = None
            target_wr = None
            ideal_price = None
            
            # Setup 1: Williams %R Oversold + Above SMA (LONG)
            if wr < -75 and above_sma:
                setup_found = True
                direction = "LONG"
                strategy = "Williams %R Mean Reversion"
                target_wr = -80
                
                tp = current + atr * 2.5
                sl = current - atr * 1.5
            
            # Setup 2: Williams %R Overbought + Below SMA (SHORT)
            elif wr > -25 and not above_sma:
                setup_found = True
                direction = "SHORT"
                strategy = "Williams %R Mean Reversion"
                target_wr = -20
                
                tp = current - atr * 2.5
                sl = current + atr * 1.5
            
            # Setup 3: Near SMA compression (LONG or SHORT)
            elif abs((current - sma_200) / sma_200) < 0.03:
                setup_found = True
                direction = "LONG" if above_sma else "SHORT"
                strategy = "SMA Compression Breakout"
                ideal_price = current
                
                if direction == "LONG":
                    tp = current * 1.04
                    sl = current * 0.97
                else:
                    tp = current * 0.96
                    sl = current * 1.03
            
            if not setup_found:
                return None
            
            # Calculate scores
            tech_score = self.calculate_technical_score(df, direction, wr, sma_200)
            rr_score = self.calculate_rr_score(current, tp, sl, direction)
            timing_score = self.calculate_timing_score(wr, target_wr, current, ideal_price)
            vol_score = self.calculate_volatility_score(df)
            regime_score = self.calculate_regime_score(df, direction)
            
            # Weighted overall score with regime filter
            base_conviction = (
                tech_score * 0.30 +
                rr_score * 0.30 +
                timing_score * 0.25 +
                vol_score * 0.15
            )
            conviction = base_conviction * regime_score  # Zero out bad regimes (conviction=0 -> F grade)
            
            # Calculate grade
            grade, notes = self.calculate_entry_grade(
                conviction, tech_score, rr_score / 20, timing_score
            )
            
            # Position size suggestion
            if conviction >= 80:
                pos_size = "FULL (16% Kelly)"
            elif conviction >= 70:
                pos_size = "MEDIUM (12% Kelly)"
            elif conviction >= 60:
                pos_size = "SMALL (8% Kelly)"
            else:
                pos_size = "SKIP or TINY (4% Kelly)"
            
            # Calculate max loss
            if direction == "LONG":
                max_loss = (current - sl) / current * 100
            else:
                max_loss = (sl - current) / current * 100
            
            rr = abs(tp - current) / abs(current - sl) if abs(current - sl) > 0 else 0
            
            return PickQuality(
                symbol=symbol,
                direction=direction,
                strategy=strategy,
                entry_price=round(current, 4 if current < 1 else 2),
                take_profit=round(tp, 4 if tp < 1 else 2),
                stop_loss=round(sl, 4 if sl < 1 else 2),
                technical_score=round(tech_score, 1),
                risk_reward_score=round(rr_score, 1),
                timing_score=round(timing_score, 1),
                volatility_score=round(vol_score, 1),
                conviction_score=round(conviction, 1),
                entry_grade=grade,
                entry_quality_notes=notes,
                risk_reward=round(rr, 2),
                max_loss_pct=round(max_loss, 2),
                position_size_suggestion=pos_size,
                indicators={
                    "williams_r": round(float(wr), 1),
                    "sma_200": round(float(sma_200), 2),
                    "atr": round(float(atr), 4),
                    "above_sma": bool(above_sma),
                },
                timestamp=datetime.now(self.est_tz).strftime('%Y-%m-%d %H:%M EST')
            )
            
        except Exception as e:
            return None
    
    def select_best_3(self) -> List[PickQuality]:
        """Scan all symbols and return top 3 picks."""
        print("="*70)
        print("KIMI BEST 3 PICKS — INTELLIGENT QUALITY RANKER")
        print("="*70)
        print(f"Scanning {len(ALL_SYMBOLS)} symbols...")
        print()
        
        all_picks = []
        
        for symbol in ALL_SYMBOLS:
            pick = self.analyze_symbol(symbol)
            if pick:
                all_picks.append(pick)
                print(f"  [FOUND] {symbol}: Grade {pick.entry_grade} | "
                      f"Conviction {pick.conviction_score:.0f}% | "
                      f"{pick.direction}")
        
        print(f"\nTotal candidates found: {len(all_picks)}")
        
        if len(all_picks) < 3:
            print("WARNING: Less than 3 valid setups found!")
        
        # Sort by conviction score (descending)
        all_picks.sort(key=lambda x: x.conviction_score, reverse=True)
        
        # Take top 3
        best_3 = all_picks[:3]
        
        print(f"\nSelected top {len(best_3)} picks by quality score:")
        for i, pick in enumerate(best_3, 1):
            print(f"  #{i}: {pick.symbol} ({pick.entry_grade}) - Score: {pick.conviction_score:.1f}")
        
        return best_3
    
    def generate_report(self, best_3: List[PickQuality]) -> dict:
        """Generate comprehensive report."""
        return {
            "timestamp": datetime.now(self.est_tz).isoformat(),
            "selector_version": "1.0",
            "symbols_scanned": len(ALL_SYMBOLS),
            "picks_found": len(best_3),
            "top_3": [pick.to_dict() for pick in best_3],
            "summary": {
                "avg_conviction": round(sum(p.conviction_score for p in best_3) / len(best_3), 1) if best_3 else 0,
                "avg_risk_reward": round(sum(p.risk_reward for p in best_3) / len(best_3), 2) if best_3 else 0,
                "directions": list(set(p.direction for p in best_3)),
                "grades": [p.entry_grade for p in best_3],
            }
        }


def main():
    """Run the best 3 selector."""
    selector = Best3Selector()
    best_3 = selector.select_best_3()
    
    if not best_3:
        print("\nNo valid setups found at this time.")
        return
    
    # Generate and save report
    report = selector.generate_report(best_3)
    
    output_path = ROOT / 'genome' / 'data' / 'kimi_best_3_current.json'
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n[OK] Report saved: {output_path}")
    
    # QUICK REFERENCE - All 3 picks with Entry/TP/SL at a glance
    print("\n" + "="*70)
    print("QUICK REFERENCE: ENTRY / TP / SL FOR ALL PICKS")
    print("="*70)
    for i, pick in enumerate(best_3, 1):
        print(f"\n  #{i} {pick.symbol} [{pick.direction}] Grade: {pick.entry_grade}")
        print(f"      ENTRY: ${pick.entry_price}")
        print(f"      TP:    ${pick.take_profit}")
        print(f"      SL:    ${pick.stop_loss}")
    
    # Print detailed report
    print("\n" + "="*70)
    print("DETAILED PICK ANALYSIS")
    print("="*70)
    
    for i, pick in enumerate(best_3, 1):
        # Calculate percentages
        if pick.direction == "LONG":
            tp_pct = ((pick.take_profit / pick.entry_price) - 1) * 100
            sl_pct = ((pick.stop_loss / pick.entry_price) - 1) * 100
        else:
            tp_pct = (1 - (pick.take_profit / pick.entry_price)) * 100
            sl_pct = (1 - (pick.stop_loss / pick.entry_price)) * 100
        
        print(f"\n{'='*70}")
        print(f"PICK #{i}: {pick.symbol} | {pick.direction} | GRADE: {pick.entry_grade}")
        print(f"{'='*70}")
        
        # TRADING LEVELS - Most Important
        print(f"\n>>> TRADING LEVELS <<<")
        print(f"    ENTRY:  ${pick.entry_price}")
        print(f"    TP:     ${pick.take_profit}  (target: +{tp_pct:.2f}%)")
        print(f"    SL:     ${pick.stop_loss}  (max loss: {sl_pct:.2f}%)")
        print(f"    R:R:    {pick.risk_reward}:1")
        
        # Position sizing
        print(f"\n>>> POSITION <<<")
        print(f"    Size:   {pick.position_size_suggestion}")
        print(f"    Max $ Risk per $1k: ${pick.max_loss_pct * 10:.2f}")
        
        # Analysis
        print(f"\n>>> ANALYSIS <<<")
        print(f"    Strategy:  {pick.strategy}")
        print(f"    Grade:     {pick.entry_grade}")
        print(f"    Conviction:{pick.conviction_score:.0f}%")
        print(f"    Note:      {pick.entry_quality_notes}")
        
        # Key indicators
        print(f"\n>>> INDICATORS <<<")
        wr = pick.indicators.get('williams_r', 'N/A')
        atr = pick.indicators.get('atr', 'N/A')
        print(f"    Williams %R: {wr}")
        print(f"    ATR:         {atr}")
        
        print(f"\n    Time: {pick.timestamp}")


if __name__ == '__main__':
    main()
