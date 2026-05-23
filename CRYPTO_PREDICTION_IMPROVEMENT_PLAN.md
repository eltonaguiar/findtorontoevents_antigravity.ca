# Crypto Prediction System Improvement Plan
## Master Coordination Document
**Date:** March 2, 2026  
**Status:** IMPLEMENTATION COMPLETE - READY FOR DEPLOYMENT

---

## Executive Summary

This document outlines the comprehensive upgrade to the findtorontoevents.ca crypto prediction system, implementing a DNA-based strategy permutation engine with hedge fund-quality signal validation.

### Key Achievements
- ✅ DNA-based genetic algorithm for strategy evolution
- ✅ Signal quality scoring (0-100, Grade A+ to D)
- ✅ Automated TP/SL calculation with Kelly criterion
- ✅ Consolidated hub dashboard with 25+ systems
- ✅ Cross-system consensus detection (Super Signals)
- ✅ GitHub Actions automation (4-hour cycles)
- ✅ Auto-deployment to FTP servers

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CRYPTO PREDICTION SYSTEM v2.0                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  LAYER 1: DATA INGESTION (GitHub Actions / 4hrs)                            │
│  ├── Binance API (price data)                                               │
│  ├── Fear & Greed Index                                                     │
│  └── Funding rates / On-chain metrics                                       │
│                                                                              │
│  LAYER 2: STRATEGY DNA ENGINE                                               │
│  ├── Individual strategies → DNA encoding                                   │
│  ├── Permutation generation (AND, OR, MAJORITY, WEIGHTED)                   │
│  ├── Genetic algorithm evolution                                            │
│  └── Phoenix revival (failed → recovered strategies)                        │
│                                                                              │
│  LAYER 3: QUALITY VALIDATION                                                │
│  ├── 6-dimension scoring (0-100)                                            │
│  ├── Grade assignment (A+ to D)                                             │
│  ├── Pre-trade validation (9 checks)                                        │
│  └── TP/SL calculation (ATR-based + Kelly sizing)                           │
│                                                                              │
│  LAYER 4: PICKS GENERATION                                                  │
│  ├── Filter: Grade B- or higher (70+)                                       │
│  ├── Diversify: max 2 per symbol, 10 total                                  │
│  └── Output: active_picks.json with full metrics                            │
│                                                                              │
│  LAYER 5: DEPLOYMENT                                                        │
│  ├── GitHub Pages (static dashboard)                                        │
│  ├── FTP: findtorontoevents.ca                                              │
│  ├── FTP: tdotevent.ca                                                      │
│  └── Hub dashboard with consensus matrix                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
findtorontoevents_antigravity.ca/
├── genome/                                    # NEW: DNA Permutation System
│   ├── dna_engine.py                          # Core genetic algorithm
│   ├── dna_backtester.py                      # Walk-forward backtesting
│   ├── strategy_registry.py                   # SQLite registry
│   ├── quality_engine.py                      # Signal quality scoring
│   ├── tp_sl_calculator.py                    # TP/SL + Kelly sizing
│   ├── signal_validator.py                    # Pre-trade validation
│   ├── picks_generator.py                     # Main orchestrator
│   ├── generate_picks.py                      # CLI pick generator
│   ├── evolve_strategies.py                   # GA evolution runner
│   ├── run_quality_system.py                  # CLI runner
│   ├── test_quality_system.py                 # Unit tests (22 tests)
│   ├── active_picks.json                      # Live picks output
│   ├── grades_explained.md                    # Grading documentation
│   ├── README.md                              # Quick start
│   ├── requirements.txt                       # Dependencies
│   ├── __init__.py                            # Package init
│   └── data/
│       ├── unified_strategy_catalog.json      # 15 sample strategies
│       ├── strategy_dna/                      # Individual DNA files
│       └── market/                            # Fetched market data
│
├── hub/                                       # UPDATED: Consolidated dashboard
│   ├── index.html                             # Enhanced (138KB)
│   ├── js/
│   │   ├── consensus_engine.js                # Cross-system consensus
│   │   └── quality_scorer.js                  # Signal quality scoring
│   └── data/
│       └── systems_manifest.json              # 25+ systems registry
│
├── .github/workflows/                         # NEW/UPDATED: Automation
│   ├── genome-daily-pipeline.yml              # Main 4-hour pipeline
│   ├── genome-evolution.yml                   # Genetic algorithm
│   └── hub-sync.yml                           # 15-min sync
│
├── updates/                                   # NEW: Update documentation
│   └── 2026-03-02-crypto-prediction-upgrade.md
│
├── GENOME_SYSTEM_README.md                    # System documentation
└── CRYPTO_PREDICTION_IMPROVEMENT_PLAN.md      # This document
```

---

## DNA Strategy System

### Strategy DNA Format

```python
{
  "strategy_id": "ema_cross_btc_1h_v1",
  "dna_hash": "a1b2c3d4e5f6",
  "genes": {
    "timeframe": "1h",
    "primary_indicator": "EMA",
    "entry_logic": "golden_cross",
    "exit_logic": "death_cross",
    "risk_profile": "medium",
    "position_sizing": "kelly_half",
    "market_regime": "trending"
  },
  "mutation_history": [],
  "parent_strategies": [],
  "created_at": "2026-03-02T00:00:00Z"
}
```

### Combination Logic Types

| Type | Description | Use Case |
|------|-------------|----------|
| **AND** | All strategies must agree | High conviction, fewer trades |
| **OR** | Any strategy triggers | More signals, higher frequency |
| **MAJORITY** | >50% agreement | Balanced approach |
| **WEIGHTED** | Confidence-weighted voting | Dynamic based on performance |
| **SEQUENTIAL** | Primary triggers, secondary confirms | Confirmation-based |
| **CONSENSUS_75** | 75% agreement required | Institutional quality |

### Phoenix Revival System

Failed strategies are monitored for revival conditions:
- Market regime alignment
- Symbol-specific performance improvement
- Combined with complementary strategies
- Reactivated when conditions match historical winning periods

---

## Signal Quality Grading

### Scoring Components

| Component | Weight | Description |
|-----------|--------|-------------|
| Backtest Validity | 25% | Sharpe, Profit Factor, Max DD |
| Statistical Significance | 20% | Sample size, confidence intervals |
| Risk-Adjusted Return | 20% | Sortino, Calmar ratios |
| Regime Alignment | 15% | Current market regime fit |
| Consensus Strength | 10% | Multi-system agreement |
| Market Structure | 10% | Liquidity, spreads, volume |

### Grade Scale

| Grade | Score | Action |
|-------|-------|--------|
| A+ | 95-100 | Exceptional - Max allocation |
| A | 90-94 | Excellent - Full allocation |
| A- | 85-89 | Very Good - Standard allocation |
| B+ | 80-84 | Good - Reduced allocation |
| B | 75-79 | Above Average - Caution |
| B- | 70-74 | Acceptable - Minimum threshold |
| C+ | 65-69 | Marginal - Paper trade only |
| C | 60-64 | Weak - Do not trade |
| D | <60 | Reject - Eliminate |

---

## Pick Format

```json
{
  "id": "pick_btc_20260302_001",
  "symbol": "BTCUSDT",
  "direction": "LONG",
  "entry_price": 85000.00,
  "take_profit": 93500.00,
  "stop_loss": 80750.00,
  "risk_reward": 2.0,
  "strategy_dna": "combo_ema_rsi_funding_btc",
  "quality_score": 87,
  "grade": "A-",
  "verdict": "STRONG_BUY",
  "confidence": 0.82,
  "position_size_pct": 3.5,
  "expected_return_pct": 10.0,
  "max_risk_pct": 5.0,
  "backtest_metrics": {
    "sharpe": 1.85,
    "win_rate": 0.68,
    "profit_factor": 2.3,
    "max_drawdown": 0.12,
    "total_trades": 156
  },
  "regime": "trending_bull",
  "consensus_count": 4,
  "agreeing_systems": ["alpha_engine", "mercury2", "dna_genome", "kimi"],
  "validation_checks": {
    "sufficient_backtest_data": true,
    "no_recent_similar_signal": true,
    "liquidity_sufficient": true
  }
}
```

---

## GitHub Actions Workflows

### 1. genome-daily-pipeline.yml (Every 4 Hours)

```
data-collection → strategy-permutation → quality-scoring → deploy-to-ftp
```

**Jobs:**
1. **Data Collection**: Fetches market data from Binance
2. **Strategy Permutation**: Generates DNA combinations, runs backtests
3. **Quality Scoring**: Calculates scores, generates picks (Grade B+ only)
4. **Deploy**: Auto-deploys to FTP servers

### 2. hub-sync.yml (Every 15 Minutes)

- Aggregates data from all systems
- Updates consensus matrix
- Refreshes Super Signals

---

## Systems Registry (25+ Systems)

| System | Category | Status |
|--------|----------|--------|
| Mercury 2 | ML Ensemble | Active |
| Claws of Doom | ML Ensemble | Active |
| Alpha Engine | ML Ensemble | Active |
| KIMI Rise of the Claw | Signal Aggregation | Active |
| Crypto ML Edge | ML Specialized | Active |
| Claude Gainer Tracker | ML Specialized | Active |
| ML Battleground A-E | Battleground | Mixed |
| ML Battleground Ensemble | Battleground | Active |
| DNA Genome Engine | Permutation | NEW |
| Super Signal Engine | Consensus | Active |
| Predictions Engine | Signal Aggregation | Active |
| Regime Terminal | Specialized | Active |
| Quantum Fusion | Specialized | Active |

---

## Deployment Checklist

### Pre-Deployment
- [x] All Python modules created
- [x] Unit tests passing (22/22)
- [x] GitHub Actions workflows configured
- [x] FTP credentials in GitHub Secrets
- [ ] Test deployment to staging

### Deployment Steps
1. **Commit to GitHub**
   ```bash
   git add genome/ hub/ .github/workflows/ updates/
   git commit -m "Add DNA Genome system and quality scoring"
   git push origin main
   ```

2. **Verify GitHub Actions**
   - Check Actions tab for workflow runs
   - Verify no errors in pipeline

3. **Verify FTP Deployment**
   - Check findtorontoevents.ca/genome/
   - Check findtorontoevents.ca/hub/
   - Verify active_picks.json is live

4. **Update Website Links**
   - Add Genome link to main navigation
   - Update Investment Hub section

### Post-Deployment Monitoring
- [ ] Monitor quality scores for 48 hours
- [ ] Verify TP/SL levels are reasonable
- [ ] Check consensus matrix updates
- [ ] Review Phoenix revivals

---

## Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| Signal Quality Score | >75 (Grade B+) | Baseline |
| Win Rate | >55% | TBD |
| Sharpe Ratio | >1.5 | TBD |
| Max Drawdown | <20% | TBD |
| Profit Factor | >1.8 | TBD |
| Consensus Accuracy | >60% | TBD |

---

## Risk Management

### Position Sizing (Kelly Criterion)
```
Position Size = (Win Rate - (1 - Win Rate) / (Avg Win / Avg Loss)) * Capital
Max: 5% per trade
```

### Pre-Trade Validation
1. Sufficient backtest data (>20 trades)
2. No recent similar signal (24h cooldown)
3. Market hours appropriate
4. Liquidity sufficient (>100 BTC daily volume)
5. Correlation within limits (<0.7 to existing)
6. Daily loss limit not exceeded

### Circuit Breakers
- Daily loss >5%: Pause new signals
- Consecutive losses >5: Reduce position size 50%
- Volatility spike (>3x ATR): Skip signals

---

## Next Steps (Phase 2)

1. **ML Enhancements**
   - Add LSTM-based regime detection
   - Implement meta-learning layer
   - Train symbol-specific models

2. **Portfolio Optimization**
   - Mean-variance optimization
   - Risk parity allocation
   - Dynamic rebalancing

3. **Expansion**
   - Top 50 altcoins
   - Forex pairs
   - Equity indices

4. **Advanced Features**
   - Options strategies
   - Funding rate arbitrage
   - Cross-exchange arbitrage

---

## Support & Documentation

| Resource | URL |
|----------|-----|
| Genome Dashboard | https://findtorontoevents.ca/genome/ |
| Hub Dashboard | https://findtorontoevents.ca/hub/ |
| Updates | https://findtorontoevents.ca/updates/ |
| Documentation | GENOME_SYSTEM_README.md |
| Grades Explained | genome/grades_explained.md |

---

## Appendix: Commands Reference

### Local Development
```bash
# Install dependencies
pip install -r genome/requirements.txt

# Run quality system demo
python genome/run_quality_system.py demo

# Run unit tests
python genome/run_quality_system.py test

# Generate picks
python genome/run_quality_system.py generate

# Evolve strategies
python genome/evolve_strategies.py --generations 10

# Backtest specific combo
python genome/dna_backtester.py --symbols BTC,ETH --lookback 90d
```

### GitHub Actions
```bash
# Trigger manually
gh workflow run genome-daily-pipeline.yml

# View logs
gh run list --workflow=genome-daily-pipeline.yml
```

---

**Document Version:** 1.0  
**Last Updated:** March 2, 2026  
**Author:** AI Coordination Team
