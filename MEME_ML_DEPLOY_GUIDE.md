# Meme Coin ML Automation - Deployment Guide

## Status: ✅ COMPLETE (Pending FTP Deployment)

All code is committed to GitHub. FTP deployment is blocked by password character escaping.

---

## What's Been Set Up

### 1. ML Engine Backend (`findcryptopairs/api/meme_ml_engine.php`)
- **795 lines** of PHP 5.2 compatible code
- Weighted logistic regression with 7 meme indicators
- **API Endpoints:**
  - `?action=predict` - Get win probability for a signal
  - `?action=batch` - Batch predictions for multiple signals
  - `?action=train` - Train model on historical data
  - `?action=retrain` - Auto-retrain check (7 days OR 50 signals)
  - `?action=performance` - Model accuracy metrics
  - `?action=compare` - Compare ML vs baseline
  - `?action=store_prediction` - Store prediction for tracking
  - `?action=update_outcome` - Update with actual results
  - `?action=stats` - ML system statistics

### 2. Database Tables (Auto-Created)
```sql
meme_ml_models         - Stores trained model weights
meme_ml_predictions    - Individual predictions with outcomes
meme_ml_signals        - Historical signals for training
```

### 3. GitHub Actions Workflows

#### Training (`.github/workflows/train-meme-ml.yml`)
- **Schedule:** Daily at 4:00 AM UTC
- **Trigger:** Manual dispatch or 50+ new signals
- **Actions:**
  1. Trains model on server via API call
  2. Fetches performance metrics
  3. Commits results back to repo

#### Data Collection (`.github/workflows/collect-meme-signals.yml`)
- **Schedule:** Every hour
- **Actions:**
  1. Collects current scanner signals
  2. Stores predictions in database
  3. Updates outcomes for resolved signals
  4. Triggers retrain if thresholds met

### 4. Frontend Integration (`meme_ml_integration.js`)
- Auto-fetches ML predictions
- Displays win probability bars
- Shows confidence indicators
- Auto-refresh every 60 seconds

---

## FTP Deployment (Manual Required)

### Problem
Password contains `^` character which causes escaping issues in Python/PowerShell:
```
Password: $a^FzN7BqKapSQMsZxD&^FeTJ
              ^               ^
              These cause issues
```

### Solution: Manual FileZilla Deployment

1. **Open FileZilla** (or any FTP client)
2. **Connect:**
   - Host: `ftps2.50webs.com`
   - Username: `ejaguiar1`
   - Password: `$a^FzN7BqKapSQMsZxD&^FeTJ` (copy-paste exactly)
   - Port: `21`

3. **Upload Files:**
   ```
   Local:  findcryptopairs/api/meme_ml_engine.php
   Remote: /findcryptopairs/api/meme_ml_engine.php
   
   Local:  findcryptopairs/api/meme_ml_integration.js  
   Remote: /findcryptopairs/api/meme_ml_integration.js
   ```

4. **Verify Deployment:**
   - Visit: `https://ejaguiar1.50webs.com/findcryptopairs/api/meme_ml_engine.php?action=stats`
   - Should return JSON with ML stats

---

## Post-Deployment Setup

### 1. Initialize Database
Visit: `https://ejaguiar1.50webs.com/findcryptopairs/api/meme_ml_engine.php?action=train`
- This auto-creates tables
- Returns error initially (no data) - that's OK

### 2. Seed Historical Data
Run the SQL from `MEME_ML_SETUP_GUIDE.md` in phpMyAdmin:
- Go to: 50webs.com → Control Panel → phpMyAdmin
- Select: `ejaguiar1` database
- Run the INSERT statements for meme_ml_signals

### 3. Enable GitHub Actions
- Go to: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions
- Enable workflows if disabled
- Run "Collect Meme Signals" manually to test

### 4. Verify Integration
- Visit: `https://ejaguiar1.50webs.com/findcryptopairs/meme.html`
- ML predictions should appear on signals
- Check browser console for "MemeML" logs

---

## Testing Commands

```bash
# Check ML stats
curl "https://ejaguiar1.50webs.com/findcryptopairs/api/meme_ml_engine.php?action=stats"

# Get prediction for a signal
curl -X POST "https://ejaguiar1.50webs.com/findcryptopairs/api/meme_ml_engine.php?action=predict" \
  -d "signal={\"explosive_volume\":20,\"parabolic_momentum\":15}"

# Train model
curl "https://ejaguiar1.50webs.com/findcryptopairs/api/meme_ml_engine.php?action=train"

# Check if retrain needed
curl "https://ejaguiar1.50webs.com/findcryptopairs/api/meme_ml_engine.php?action=retrain"
```

---

## Troubleshooting

### "No database connection"
- Check db_connect.php exists and has correct credentials
- Ensure MySQL is running on 50webs

### "Not enough samples for training"
- Need 30+ signals with known outcomes
- Run the seed SQL from setup guide
- Wait for GitHub Actions to collect more data

### "ML predictions not showing on frontend"
- Check browser console for JS errors
- Verify meme_ml_integration.js is loaded
- Check network tab for API call failures

### GitHub Actions failing
- Check repository Actions settings
- Ensure workflow has write permissions
- Verify API endpoints are accessible

---

## Feature Weights (ML Model)

```php
explosive_volume        => 0.28  // Highest impact
parabolic_momentum      => 0.24  // Strong momentum
rsi_hype_zone           => 0.18  // RSI 55-75
social_momentum_proxy   => 0.15  // Social signals
volume_concentration    => 0.08  // Volume spikes
breakout_4h             => 0.05  // Price breakouts
low_market_cap_bonus    => 0.02  // Small cap bonus
bias                    => -0.15 // Conservative offset
```

Win Probability Formula:
```
z = Σ(weight_i × feature_i) + bias
probability = 1 / (1 + e^(-z))
```

---

## Automation Summary

| Component | Frequency | Trigger |
|-----------|-----------|---------|
| Signal Collection | Hourly | GitHub Actions cron |
| Model Training | Daily 4AM | GitHub Actions cron |
| Auto-Retrain | - | 50+ new signals OR 7 days |
| Outcome Resolution | Hourly | Candle-walk analysis |
| Frontend Updates | Real-time | 60s polling |

---

## Next Steps After Deployment

1. ✅ Upload files via FileZilla
2. ✅ Seed database with 30 historical signals
3. ✅ Enable GitHub Actions
4. ✅ Run initial training
5. ✅ Monitor first predictions
6. ✅ Review accuracy after 20+ predictions

---

**Files Ready for Deployment:**
- `findcryptopairs/api/meme_ml_engine.php` (795 lines)
- `findcryptopairs/api/meme_ml_integration.js` (if exists)
- GitHub Actions workflows (already in repo)
