# Find Stocks Setup & Deployment

## Overview

The Find Stocks page (`/findstocks`) provides daily stock picks powered by multiple AI-validated algorithms from 11+ stock analysis repositories.

## Files Created

### Page Component
- `src/app/findstocks/page.tsx` - Main Find Stocks page component

### Scripts
- `scripts/generate-daily-stocks.ts` - Generates daily stock picks JSON
- `scripts/sync-to-stocksunify.ts` - Syncs data to STOCKSUNIFY GitHub repo

### Data Files
- `data/daily-stocks.json` - Source data file
- `public/data/daily-stocks.json` - Public web-accessible data file

## Usage

### Generate Daily Stock Picks

```bash
npm run stocks:generate
```

This script:
1. Generates stock picks using multiple algorithms
2. Saves to `data/daily-stocks.json`
3. Also saves to `public/data/daily-stocks.json` for web access

### Sync to STOCKSUNIFY Repository

```bash
npm run stocks:sync
```

This script:
1. Clones/updates the STOCKSUNIFY repository
2. Copies daily stock picks to `data/` folder
3. Copies analysis documents to **root directory** (for GitHub Pages)
4. Creates/updates `README.md` (serves as GitHub Pages landing page)
5. Commits and pushes changes to `main` branch

**Note:** STOCKSUNIFY GitHub Pages is configured to serve from `main` branch / root directory, so files are placed accordingly.

### Full Workflow

```bash
npm run stocks:full
```

Runs both generation and sync in sequence.

## Data Structure

The `daily-stocks.json` file follows this structure:

```json
{
  "lastUpdated": "2026-01-27T00:00:00.000Z",
  "totalPicks": 5,
  "stocks": [
    {
      "symbol": "NVDA",
      "name": "NVIDIA Corporation",
      "price": 125.50,
      "change": 2.30,
      "changePercent": 1.87,
      "rating": "STRONG BUY",
      "timeframe": "3m",
      "algorithm": "CAN SLIM",
      "score": 92,
      "risk": "Medium",
      "lastUpdated": "2026-01-27",
      "indicators": {
        "rsRating": 95,
        "revenueGrowth": 28.5,
        "rsi": 65
      }
    }
  ]
}
```

## Algorithms Integrated

1. **CAN SLIM Growth Screener** (Long-term, 3-12 months)
   - RS Rating ≥ 90
   - Stage-2 Uptrend
   - Revenue Growth ≥ 25%
   - Institutional Accumulation

2. **Technical Momentum** (Short-term, 24h-1 week)
   - Volume Surge Detection
   - RSI Extremes
   - Breakout Patterns
   - Bollinger Band Squeeze

3. **ML Ensemble** (Portfolio Management)
   - XGBoost/Gradient Boosting
   - Sentiment Analysis
   - Portfolio Optimization
   - Risk Metrics (VaR, Sharpe)

## STOCKSUNIFY Repository

The STOCKSUNIFY repository (`https://github.com/eltonaguiar/STOCKSUNIFY`) receives:
- Daily stock picks (`data/daily-stocks.json`)
- Analysis documents (root directory `*.md` files)
- Generation scripts (`scripts/generate-daily-stocks.ts`)
- README.md (GitHub Pages landing page)

**GitHub Pages Configuration:**
- Branch: `main`
- Directory: `/` (root)
- Live URL: `https://eltonaguiar.github.io/STOCKSUNIFY/`

## Deployment

The Find Stocks page is automatically included in the build and deployed to:
- **Live URL (lowercase)**: https://findtorontoevents.ca/findstocks
- **Live URL (uppercase)**: https://findtorontoevents.ca/STOCKS
- **GitHub Pages**: https://eltonaguiar.github.io/TORONTOEVENTS_ANTIGRAVITY/findstocks

The deployment script automatically uploads the page to both `/findstocks` and `/STOCKS` directories for maximum compatibility.

## Automation

To set up daily automation:

1. **GitHub Actions** (recommended):
   - Create `.github/workflows/daily-stocks.yml`
   - Schedule: `0 9 * * *` (9 AM daily)
   - Run: `npm run stocks:full`

2. **Cron Job** (local/server):
   ```bash
   0 9 * * * cd /path/to/repo && npm run stocks:full
   ```

3. **Manual**:
   ```bash
   npm run stocks:full
   ```

## Next Steps

1. **Connect Real APIs**: Replace mock data in `generate-daily-stocks.ts` with actual API calls to your stock repositories
2. **Add More Algorithms**: Integrate additional algorithms from your 11 repositories
3. **Historical Tracking**: Add historical performance tracking
4. **User Preferences**: Allow users to filter by risk tolerance, timeframe, etc.
5. **Alerts**: Set up email/push notifications for high-scoring picks

## Related Documents

- [Stock Repository Analysis](STOCK_REPOSITORY_ANALYSIS.md)
- [Algorithm Summary](STOCK_ALGORITHM_SUMMARY.md)
- [Google Gemini Analysis](STOCK_GOOGLEGEMINI_ANALYSIS.md)
- [Comet Browser AI Analysis](STOCK_COMETBROWSERAI_ANALYSIS.md)
- [ChatGPT Analysis](STOCK_CHATGPT_ANALYSIS.md)
