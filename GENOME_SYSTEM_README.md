# DNA Genome Trading System

## Overview
The DNA Genome system is a meta-strategy platform that:
1. Creates unique "DNA" fingerprints for each trading strategy
2. Generates permutations (combinations) of strategies
3. Evolves winning combinations through genetic algorithms
4. Provides hedge fund-quality signal validation

## Architecture

### Core Components
- **dna_engine.py**: Genetic algorithm and permutation engine
- **dna_backtester.py**: Walk-forward backtesting
- **strategy_registry.py**: SQLite database for strategy storage
- **quality_engine.py**: Signal quality scoring (0-100)
- **tp_sl_calculator.py**: Take profit / stop loss calculation
- **picks_generator.py**: Daily high-quality picks

### Data Flow
1. Market data fetched every 4 hours (GitHub Actions)
2. New DNA permutations generated and backtested
3. Quality scores calculated for all combinations
4. Top picks (Grade B+ only) selected
5. TP/SL levels calculated
6. Results deployed to website

## Usage

### Viewing Picks
Visit: https://findtorontoevents.ca/genome/

### Understanding Grades
- **A+ (95-100)**: Exceptional - Institutional quality
- **A (90-94)**: Excellent - Strong edge
- **A- (85-89)**: Very Good
- **B+ (80-84)**: Good
- **B (75-79)**: Above Average
- **B- (70-74)**: Minimum threshold

### Signal Format
```json
{
  "symbol": "BTCUSDT",
  "direction": "LONG",
  "entry": 85000,
  "take_profit": 93500,
  "stop_loss": 80750,
  "quality_score": 87,
  "grade": "A-",
  "confidence": 0.82
}
```

## Development

### Local Setup
```bash
cd genome
pip install -r requirements.txt
python picks_generator.py --min-quality 70
```

### Running Backtests
```bash
python dna_backtester.py --symbols BTC,ETH --lookback 90d
```

### Adding New Strategies
1. Add strategy DNA to `data/strategy_dna/`
2. Run registration: `python strategy_registry.py --register`
3. Backtest: `python dna_backtester.py --strategy <id>`
4. Quality check: `python quality_engine.py --score <id>`

## GitHub Actions
- **Schedule:** Every 4 hours
- **Workflow:** `.github/workflows/genome-daily-pipeline.yml`
- **Deployment:** Auto-deploys to 50webs and GoDaddy FTP

## Support
For issues or questions, check:
- Hub Dashboard: https://findtorontoevents.ca/hub/
- Updates: https://findtorontoevents.ca/updates/
