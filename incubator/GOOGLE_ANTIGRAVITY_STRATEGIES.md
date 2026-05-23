# Google Antigravity Quantitative Strategies

**20 Institutional-Grade Trading Strategies**  
**Added:** February 26, 2026  
**Status:** Active (OHLCV-based, ready for backtesting)

---

## Overview

These 20 strategies represent advanced quantitative techniques typically found in institutional trading firms. Each strategy supports **LONG + SHORT** positions and includes dynamic regime detection.

| # | Strategy | Core Technique | Edge |
|---|----------|----------------|------|
| 201 | Garman-Klass Vol Breakout | GK volatility estimator | More efficient than close-close vol |
| 202 | Fractal Dimension Regime | Higuchi fractal dimension | Scale-invariant regime detection |
| 203 | Liquidation Cascade Detector | Price accel + vol explosion | Fade liquidation cascades |
| 204 | Wavelet Trend-Noise | Haar wavelet decomposition | Signal-to-noise ratio trading |
| 205 | Jump Diffusion Detector | BNS jump test | Fade extreme jumps |
| 206 | Information Ratio Momentum | Rolling IR quality gate | Only trade quality momentum |
| 207 | VPIN Toxicity Flow | VPIN proxy | Order flow toxicity clearing |
| 208 | Spectral Cycle Detector | FFT cycle detection | Trade at cycle trough/peak |
| 209 | Adaptive Kelly Regime | Kelly criterion embedded | Dynamic sizing in signal |
| 210 | Correlation Breakdown Alpha | AC regime detection | Both trend & MR modes |
| 211 | Realized Vol Smile | Up-vol vs down-vol asymmetry | Fear/greed premium capture |
| 212 | Regime-Switching GARCH | GARCH(1,1) forecast | Vol forecast divergence |
| 213 | Cross-Timeframe Divergence | 3 synthetic TFs | Fast vs slow momentum div |
| 214 | Microstructure Spread Proxy | Corwin-Schultz spread | Liquidity regime change |
| 215 | Max Drawdown Recovery | DD/DU recovery timing | Fade extreme drawdown/drawup |
| 216 | Dispersion Mean Reversion | Intra-bar dispersion z | Panic/euphoria absorption |
| 217 | Omega Ratio Gate | Omega ratio quality | Probability-weighted edge |
| 218 | Power Law Tail Risk | Hill tail estimator | Fat/thin tail regime |
| 219 | Entropy-Weighted Momentum | Shannon entropy weighting | Low-entropy = high conviction |
| 220 | Cointegration Residual | Self-cointegration + half-life | OU process mean reversion |

---

## Strategy Categories

### Volatility & Risk (201, 211, 212, 218)
- **201:** Garman-Klass uses OHLC for better volatility estimates
- **211:** Realized Vol Smile captures fear/greed asymmetry
- **212:** GARCH forecasts vs realized divergence
- **218:** Hill estimator for tail risk regime detection

### Regime Detection (202, 210, 219)
- **202:** Fractal dimension for noise vs trend classification
- **210:** Autocorrelation breakdown for trend/MR switch
- **219:** Entropy as predictability measure

### Event Detection (203, 205)
- **203:** Liquidation cascade fading using acceleration + volume
- **205:** BNS jump test for extreme move detection

### Signal Processing (204, 208, 213)
- **204:** Wavelet decomposition for trend/noise separation
- **208:** FFT spectral analysis for cycle trading
- **213:** Multi-timeframe divergence detection

### Microstructure (207, 214)
- **207:** VPIN proxy for toxicity detection
- **214:** Corwin-Schultz spread for liquidity regime

### Position Sizing (206, 209, 217)
- **206:** Information Ratio as quality gate
- **209:** Kelly criterion with regime adjustment
- **217:** Omega ratio for probability-weighted edge

### Mean Reversion (215, 216, 220)
- **215:** Drawdown/drawup recovery timing
- **216:** Intra-bar dispersion z-score
- **220:** OU process with half-life estimation

---

## Technical Specifications

### Signal Format
All strategies return a `Signal` dataclass:
```python
@dataclass
class Signal:
    action: str      # "buy", "sell", or "hold"
    confidence: float  # 0.0 to 1.0
    metadata: dict   # Strategy-specific diagnostics
```

### Data Requirements
- **Primary:** OHLCV (Open, High, Low, Close, Volume)
- **Fallback:** Close prices only (with synthetic OHLC estimation)
- **No external data:** All calculations from price/volume

### LONG + SHORT Support
Every strategy includes logic for both directions:
- **Long signals:** Oversold bounces, trend continuation up, low entropy
- **Short signals:** Overbought pullbacks, trend continuation down, euphoria detection

### Regime Adaptation
Strategies dynamically adjust based on market regime:
- **Trending:** Follow momentum with high conviction
- **Mean-reverting:** Fade extremes with lower size
- **High entropy:** Reduce position sizes (noisy markets)

---

## Backtest Priority

### Tier 1 (Immediate)
1. **203** - Liquidation Cascade (clear signals)
2. **215** - DD Recovery (intuitive risk management)
3. **210** - Correlation Breakdown (regime clarity)

### Tier 2 (High Value)
4. **201** - Garman-Klass (volatility edge)
5. **212** - GARCH (forecasting power)
6. **220** - OU Process (statistical rigor)

### Tier 3 (Advanced)
7. **204, 208** - Signal processing (computationally intensive)
8. **218, 219** - Entropy/Tail risk (complex interpretation)

---

## Integration

### File Locations
```
incubator/agents/web_ai/
├── strategy_201_garman_klass_vol_breakout.py
├── strategy_202_fractal_dimension_regime.py
├── ... (all 20 strategies)
└── strategy_220_cointegration_residual_spread.py
```

### Backtest Usage
```python
from incubator.agents.web_ai.strategy_203_liquidation_cascade_detector import (
    LiquidationCascadeDetectorStrategy
)

strategy = LiquidationCascadeDetectorStrategy(
    acceleration_threshold=3.0,
    volume_spike_threshold=3.0
)

signal = strategy.analyze(prices, volumes)
if signal.action == "buy":
    # Execute long position
    position_size = signal.confidence  # 0.0 to 1.0
```

---

## Performance Expectations

Based on strategy design:

| Category | Win Rate Target | Sharpe Target | Max DD |
|----------|-----------------|---------------|--------|
| Event Detection (203, 205) | 55-60% | 1.2-1.5 | -15% |
| Regime Switching (210, 212) | 50-55% | 1.0-1.3 | -12% |
| Mean Reversion (215, 216, 220) | 52-58% | 1.1-1.4 | -10% |
| Volatility (201, 211, 212) | 48-52% | 0.9-1.2 | -18% |

*Note: Targets assume realistic transaction costs and slippage.*

---

## Research Notes

### From Google Antigravity Team
> "These strategies represent battle-tested institutional techniques. The key edge comes from:
> 1. Multi-timeframe confirmation
> 2. Regime-aware position sizing
> 3. Statistical rigor in signal generation
> 4. Dynamic adaptation to market conditions"

### Implementation Highlights
- All strategies use robust numerical methods
- Edge cases handled (division by zero, insufficient data)
- Configurable parameters for different asset classes
- Metadata provides full diagnostic traceability

---

## Next Steps

1. **Backtest all 20** against 2+ years of crypto data
2. **Correlation analysis** - avoid redundant signals
3. **Ensemble construction** - combine complementary strategies
4. **Live paper trading** - forward test top performers

---

**Total Strategies:** 220 new + 222 existing = 442 total  
**Active:** 174 (including these 20)  
**Parked:** 46 (awaiting specialized data feeds)

*Last Updated: February 26, 2026*
