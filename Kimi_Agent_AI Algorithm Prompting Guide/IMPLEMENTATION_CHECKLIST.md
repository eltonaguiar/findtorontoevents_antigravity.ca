# On-Chain Data Integration - Implementation Checklist

## Pre-Implementation

- [ ] Review all generated files
- [ ] Understand confidence calculation formula
- [ ] Identify integration points in your existing system

## API Setup

- [ ] Sign up for Whale Alert API key (https://whale-alert.io/)
- [ ] Sign up for Glassnode API key (https://glassnode.com/)
- [ ] Store API keys securely (environment variables)
- [ ] Test API connectivity

## Integration Steps

### Step 1: Copy Files
```bash
cp onchain_data_module.py /your/trading/system/
cp config.env.template /your/trading/system/.env
```

### Step 2: Install Dependencies
```bash
pip install requests pandas numpy
```

### Step 3: Configure Environment
```bash
# Edit .env file
WHALE_ALERT_API_KEY=your_actual_key
GLASSNODE_API_KEY=your_actual_key
```

### Step 4: Test Integration
```python
# Test basic functionality
from onchain_data_module import OnChainDataProvider

provider = OnChainDataProvider(
    whale_alert_api_key="your_key",
    glassnode_api_key="your_key",
)

# Test with mock data first
signal = provider.calculate_confidence_boost("BTC", "long")
print(f"Test confidence: {signal.combined_score}")
```

### Step 5: Integrate with Your Strategy
```python
# In your existing Keltner/RSI system
from onchain_data_module import SignalEnhancer

class YourStrategy:
    def __init__(self):
        self.enhancer = SignalEnhancer(
            OnChainDataProvider(api_key="your_key")
        )

    def generate_signal(self, ohlcv_df):
        # Your existing Keltner/RSI logic
        tech_signal = self.calculate_keltner_rsi(ohlcv_df)

        # Enhance with on-chain
        enhanced = self.enhancer.enhance_signal(
            symbol="BTC",
            base_signal=tech_signal["direction"],
            base_confidence=tech_signal["confidence"],
        )

        return enhanced
```

## Testing

- [ ] Run demo.py to verify functionality
- [ ] Test with historical data (backtest)
- [ ] Verify false positive filtering
- [ ] Check rate limiting works
- [ ] Validate confidence calculations

## Paper Trading

- [ ] Run for 2 weeks with paper trading
- [ ] Compare results with/without on-chain boost
- [ ] Monitor API usage
- [ ] Adjust confidence thresholds if needed

## Production Deployment

- [ ] Set up monitoring/logging
- [ ] Configure alerts for API limits
- [ ] Document position sizing rules
- [ ] Train team on new system

## Post-Deployment

- [ ] Track performance metrics
- [ ] Monitor win rate improvement
- [ ] Adjust weights if needed (70/30 split)
- [ ] Review and optimize

## Files to Keep

| File | Purpose | Keep? |
|------|---------|-------|
| onchain_data_module.py | Main module | ✅ Yes |
| integration_example.py | Reference | ✅ Yes |
| demo.py | Testing | ✅ Yes |
| API_DOCUMENTATION.md | Reference | ✅ Yes |
| QUICK_REFERENCE.md | Quick start | ✅ Yes |
| SUMMARY.md | Overview | ✅ Yes |
| config.env.template | Template | ✅ Yes |

## Key Configuration Values

```python
# Confidence weights
TECHNICAL_WEIGHT = 0.7
ONCHAIN_WEIGHT = 0.3
WHALE_SCORE_WEIGHT = 0.4
EXCHANGE_SCORE_WEIGHT = 0.6

# Position sizing thresholds
MIN_CONFIDENCE = 0.40  # Skip below this
FULL_POSITION = 0.65   # 100% size above this
BOOST_POSITION = 0.80  # 125% size above this

# Whale thresholds
WHALE_THRESHOLD_USD = 10_000_000
MAJOR_WHALE_THRESHOLD_USD = 50_000_000

# Rate limits
WHALE_ALERT_RATE_LIMIT = 10  # calls/min
GLASSNODE_RATE_LIMIT = 30    # calls/min

# Cache TTL
WHALE_CACHE_TTL = 60         # seconds
EXCHANGE_CACHE_TTL = 300     # seconds
```

## Expected Results

Based on your 62.4% win rate system:

| Metric | Before | After (Expected) |
|--------|--------|------------------|
| Win Rate | 62.4% | 65-67% |
| False Breakouts | Baseline | -20% |
| Position Sizing | Fixed | Dynamic |
| Risk-Adjusted Return | Baseline | +10-15% |

## Support

If you encounter issues:
1. Check API key validity
2. Verify rate limits not exceeded
3. Review logs for errors
4. Check cache is working
5. Validate symbol format

## Contact

For questions about implementation, refer to:
- API_DOCUMENTATION.md for technical details
- QUICK_REFERENCE.md for common patterns
- integration_example.py for working code
