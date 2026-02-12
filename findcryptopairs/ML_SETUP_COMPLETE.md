# Meme Coin ML - Complete Setup Guide

## Overview
This guide walks through fully setting up the ML system for the meme coin scanner with automated GitHub Actions.

## Step 1: Database Initialization

### Option A: Web Interface
1. Visit: `https://findtorontoevents.ca/findcryptopairs/api/ml_database_init.php?action=init`
2. Should return: `{"ok": true, "tables_created": [...], "messages": [...]}`
3. Verify: `https://findtorontoevents.ca/findcryptopairs/api/ml_database_init.php?action=status`

### Option B: Manual SQL
Run this SQL in your database admin:

```sql
-- Signals table
CREATE TABLE meme_signals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    signal_id VARCHAR(50) UNIQUE,
    coin_symbol VARCHAR(20),
    coin_name VARCHAR(100),
    tier ENUM('tier1', 'tier2'),
    explosive_volume DECIMAL(5,2),
    parabolic_momentum DECIMAL(5,2),
    rsi_hype_zone DECIMAL(5,2),
    social_momentum_proxy DECIMAL(5,2),
    volume_concentration DECIMAL(5,2),
    breakout_4h DECIMAL(5,2),
    low_market_cap_bonus DECIMAL(5,2),
    total_score DECIMAL(5,2),
    verdict VARCHAR(20),
    entry_price DECIMAL(18,10),
    target_price DECIMAL(18,10),
    stop_price DECIMAL(18,10),
    signal_time DATETIME,
    resolve_time DATETIME,
    created_at DATETIME DEFAULT NOW(),
    INDEX idx_coin (coin_symbol),
    INDEX idx_time (signal_time),
    INDEX idx_score (total_score)
) ENGINE=MyISAM;

-- Results table
CREATE TABLE meme_signal_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    signal_id VARCHAR(50),
    outcome ENUM('win', 'loss', 'pending', 'expired'),
    profit_loss_pct DECIMAL(8,4),
    max_profit_pct DECIMAL(8,4),
    max_loss_pct DECIMAL(8,4),
    exit_price DECIMAL(18,10),
    resolved_at DATETIME,
    resolution_notes TEXT,
    INDEX idx_signal (signal_id),
    INDEX idx_outcome (outcome)
) ENGINE=MyISAM;

-- ML Models table
CREATE TABLE meme_ml_models (
    id INT AUTO_INCREMENT PRIMARY KEY,
    model_id VARCHAR(50) UNIQUE,
    model_version INT DEFAULT 1,
    weights_json TEXT,
    feature_importance_json TEXT,
    metrics_json TEXT,
    sample_count INT,
    training_samples_wins INT,
    training_samples_losses INT,
    base_win_rate DECIMAL(5,2),
    accuracy DECIMAL(5,4),
    precision_score DECIMAL(5,4),
    recall DECIMAL(5,4),
    f1_score DECIMAL(5,4),
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT NOW(),
    last_used DATETIME,
    INDEX idx_active (is_active)
) ENGINE=MyISAM;

-- ML Predictions table
CREATE TABLE meme_ml_predictions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    prediction_id VARCHAR(50) UNIQUE,
    signal_id VARCHAR(50),
    model_id VARCHAR(50),
    predicted_probability DECIMAL(5,4),
    predicted_outcome TINYINT,
    confidence_level VARCHAR(10),
    feature_values_json TEXT,
    actual_outcome TINYINT DEFAULT NULL,
    outcome_verified_at DATETIME,
    created_at DATETIME DEFAULT NOW(),
    INDEX idx_signal (signal_id),
    INDEX idx_model (model_id)
) ENGINE=MyISAM;

-- Training log
CREATE TABLE meme_ml_training_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    model_id VARCHAR(50),
    action VARCHAR(50),
    samples_used INT,
    accuracy DECIMAL(5,4),
    message TEXT,
    created_at DATETIME DEFAULT NOW()
) ENGINE=MyISAM;
```

## Step 2: Upload Files

### Required Files
Upload these to `/findcryptopairs/api/`:

1. `meme_ml_engine.php` - ML backend
2. `meme_ml_integration.js` - Frontend integration
3. `ml_database_init.php` - Database setup

### Verify Upload
```bash
curl "https://findtorontoevents.ca/findcryptopairs/api/ml_database_init.php?action=status"
```

Should return table counts.

## Step 3: Initialize with Sample Data

### Automatic (Recommended)
```bash
curl "https://findtorontoevents.ca/findcryptopairs/api/ml_database_init.php?action=init"
```

This creates:
- 100 sample signals with realistic outcomes
- Initial model with default weights
- All required tables

### Verify
```bash
curl "https://findtorontoevents.ca/findcryptopairs/api/ml_database_init.php?action=status"
```

Should show:
```json
{
  "ok": true,
  "table_counts": {
    "meme_signals": 100,
    "meme_signal_results": 100,
    "meme_ml_models": 1,
    "meme_ml_predictions": 0
  }
}
```

## Step 4: Train First Model

### Via GitHub Actions (Recommended)
1. Go to GitHub repo → Actions → "Meme Coin ML Training"
2. Click "Run workflow"
3. Or wait for automatic daily run at 6 AM UTC

### Manual Training
```bash
curl "https://findtorontoevents.ca/findcryptopairs/api/meme_ml_engine.php?action=train&min_samples=50"
```

Expected output:
```json
{
  "ok": true,
  "model_id": "meme_ml_20240215_083000",
  "samples_used": 100,
  "winners": 45,
  "losers": 55,
  "base_win_rate": 45.0,
  "optimized_weights": {
    "explosive_volume": 0.28,
    "parabolic_momentum": 0.22,
    ...
  },
  "metrics": {
    "accuracy": 0.68,
    "f1_score": 0.65
  }
}
```

## Step 5: Update meme.html

### Add ML Script
Before `</body>`:
```html
<script src="api/meme_ml_integration.js"></script>
```

### Add ML Status Badge
After header section:
```html
<div style="display:flex;gap:8px;align-items:center;margin-bottom:12px;">
  <span id="ml-status-badge" class="badge">ML CHECKING...</span>
  <button onclick="MemeML.showTrainingInterface()">🤖 Train</button>
</div>
```

### Enhance Winner Cards
In your `renderWinnerCard` function, add:
```javascript
// Add ML container
html += `<div id="ml-${winner.coin_symbol}" class="ml-container"></div>`;

// Fetch prediction
if (window.MemeML && MemeML.mlEnabled) {
    MemeML.predict(winner).then(pred => {
        if (pred.ok) {
            document.getElementById(`ml-${winner.coin_symbol}`).innerHTML = 
                MemeML.renderMLWinnerCard(winner, pred);
        }
    });
}
```

## Step 6: Configure GitHub Actions

### Workflows Created

1. **meme-ml-training.yml**
   - Runs: Daily at 6 AM UTC
   - Action: Checks if retraining needed, trains model
   - Auto-triggers: Every 7 days or 50 new signals

2. **meme-signal-collector.yml**
   - Runs: Every 10 minutes
   - Action: Collects signals, resolves expired, updates predictions

### Enable Workflows
1. Push files to `.github/workflows/`
2. GitHub → Actions → Enable workflows
3. Workflows will run automatically

### Manual Trigger
- Go to Actions → Select workflow → "Run workflow"
- Can force retrain with `force_train: true`

## Step 7: Verify Everything Works

### Test 1: Database Status
```bash
curl "https://findtorontoevents.ca/findcryptopairs/api/ml_database_init.php?action=status"
```

### Test 2: Model Performance
```bash
curl "https://findtorontoevents.ca/findcryptopairs/api/meme_ml_engine.php?action=performance"
```

### Test 3: Prediction
```bash
curl -X POST "https://findtorontoevents.ca/findcryptopairs/api/meme_ml_engine.php?action=predict" \
  -d "signal={\"coin_symbol\":\"DOGE\",\"explosive_volume\":20,\"parabolic_momentum\":15,...}"
```

### Test 4: Comparison
```bash
curl "https://findtorontoevents.ca/findcryptopairs/api/meme_ml_engine.php?action=compare&days=30"
```

### Test 5: Frontend
1. Load `meme.html` in browser
2. Check browser console for "MemeML: Initializing..."
3. Verify ML badge shows status
4. Click "Train" button to test interface

## Step 8: Monitoring

### GitHub Actions Dashboard
- Monitor workflow runs: GitHub → Actions
- Check for failures daily
- Review training reports

### Key Metrics to Watch
| Metric | Good | Warning | Bad |
|--------|------|---------|-----|
| Win Rate | >40% | 30-40% | <30% |
| ML Accuracy | >65% | 55-65% | <55% |
| F1 Score | >60% | 50-60% | <50% |
| Signals/Day | 5-20 | <5 | >50 |

### Alerts
GitHub Actions will create issues if:
- Training fails
- Workflow errors occur

## Troubleshooting

### "ML DISABLED" Badge
**Cause:** No trained model or <50 samples
**Fix:** Run training workflow or wait for auto-train

### Training Fails with "Insufficient data"
**Cause:** <50 closed signals with outcomes
**Fix:** Let scanner collect more data over time

### Predictions Not Showing
**Cause:** JavaScript not loading
**Fix:** Check browser console, verify file paths

### Database Errors
**Cause:** Tables not created
**Fix:** Run initialization: `ml_database_init.php?action=init`

## File Structure

```
findcryptopairs/
├── api/
│   ├── meme_ml_engine.php          # ML backend (26 KB)
│   ├── meme_ml_integration.js      # Frontend (15 KB)
│   ├── ml_database_init.php        # DB setup (14 KB)
│   └── meme_scanner.php            # Existing scanner
├── meme.html                       # Main page (add ML script)
└── MODEL_STATUS.md                 # Auto-generated by Actions

.github/
└── workflows/
    ├── meme-ml-training.yml        # Daily training
    └── meme-signal-collector.yml   # Signal collection
```

## Maintenance

### Weekly
- Review ML vs rule-based comparison
- Check GitHub Actions for failures
- Monitor prediction accuracy

### Monthly
- Analyze feature importance changes
- Review if weight adjustments needed
- Check model drift

### Quarterly
- Full model retrain with all data
- Algorithm review
- Performance audit

## Support

### Logs Location
- GitHub Actions: GitHub → Actions → Workflow runs
- Training logs: `meme_ml_training_log` table
- Predictions: `meme_ml_predictions` table

### Reset Everything
```bash
curl "https://findtorontoevents.ca/findcryptopairs/api/ml_database_init.php?action=reset"
```
**Warning:** This deletes all training data!

---

**Setup Complete!** The ML system will now:
1. ✅ Auto-collect signals every 10 minutes
2. ✅ Auto-resolve outcomes after 2 hours
3. ✅ Auto-retrain model every 7 days
4. ✅ Serve predictions on every page load
5. ✅ Track performance vs rule-based
