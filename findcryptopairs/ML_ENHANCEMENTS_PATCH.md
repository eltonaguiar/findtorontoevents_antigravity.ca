# Meme Coin ML Integration - Patch Instructions

## Files Created

| File | Size | Purpose |
|------|------|---------|
| `api/meme_ml_engine.php` | 26.8 KB | ML backend with training/prediction |
| `api/meme_ml_integration.js` | 15.6 KB | Frontend ML integration |

## Changes Needed in meme.html

### 1. Add ML Status Badge (after line 181)

```html
<!-- ML Status Badge -->
<div style="display:flex;gap:8px;align-items:center;margin-bottom:12px;">
  <span id="ml-status-badge" class="badge">ML CHECKING...</span>
  <button onclick="MemeML.showTrainingInterface()" style="background:transparent;border:1px solid var(--border);color:var(--dim);padding:3px 10px;border-radius:4px;font-size:11px;cursor:pointer;">🤖 Train Model</button>
  <button onclick="MemeML.compare().then(d => alert(JSON.stringify(d.comparison, null, 2)))" style="background:transparent;border:1px solid var(--border);color:var(--dim);padding:3px 10px;border-radius:4px;font-size:11px;cursor:pointer;">📊 Compare</button>
</div>
```

### 2. Add ML Script Include (before closing </body>)

```html
<!-- ML Integration -->
<script src="api/meme_ml_integration.js"></script>
```

### 3. Enhance renderWinnerCard function

Add to your existing `renderWinnerCard` function:

```javascript
// After creating the winner card HTML, add ML prediction container
const mlContainerId = 'ml-' + winner.coin_symbol;
html += `<div id="${mlContainerId}" class="ml-container"></div>`;

// Then fetch and render ML prediction
if (window.MemeML && MemeML.mlEnabled) {
    MemeML.predict(winner).then(prediction => {
        if (prediction.ok) {
            const container = document.getElementById(mlContainerId);
            if (container) {
                container.innerHTML = MemeML.renderMLWinnerCard(winner, prediction);
            }
        }
    });
}
```

### 4. Add ML Section to System Analysis Tab (after line 412)

```html
<h4 style="font-size:15px;margin-bottom:10px;color:#a855f7;">🤖 Machine Learning Status</h4>
<div style="background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:16px;margin-bottom:16px;">
  <div id="ml-comparison-container">
    <div style="font-size:12px;color:var(--dim);">Loading ML comparison...</div>
  </div>
</div>
<script>
// Load ML comparison
if (window.MemeML) {
    MemeML.compare(30).then(data => {
        const container = document.getElementById('ml-comparison-container');
        if (container && data.ok) {
            container.innerHTML = MemeML.renderComparison(data);
        }
    });
}
</script>
```

### 5. Add ML to Research Tab Comparison Table (around line 477)

Add row to the comparison table:

```html
<tr style="border-bottom:1px solid rgba(42,42,74,0.5);">
  <td style="padding:6px 8px;">ML Prediction</td>
  <td style="padding:6px 8px;color:var(--green);">Adaptive learning from outcomes</td>
  <td style="padding:6px 8px;color:var(--gold);">Rule-based with ML overlay</td>
  <td style="padding:6px 8px;color:var(--gold);">Medium</td>
</tr>
```

## Database Tables (Auto-Created)

The ML engine will auto-create these tables on first run:

```sql
CREATE TABLE meme_ml_models (
    model_id VARCHAR(50) PRIMARY KEY,
    weights_json TEXT,
    feature_importance_json TEXT,
    metrics_json TEXT,
    sample_count INT,
    created_at DATETIME
);

CREATE TABLE meme_ml_predictions (
    signal_id VARCHAR(50),
    model_id VARCHAR(50),
    predicted_probability DECIMAL(5,4),
    predicted_outcome TINYINT,
    actual_outcome TINYINT,
    feature_values_json TEXT,
    created_at DATETIME
);
```

## API Endpoints

```
GET  /api/meme_ml_engine.php?action=train          # Train/retrain model
GET  /api/meme_ml_engine.php?action=predict        # Single prediction
POST /api/meme_ml_engine.php?action=batch          # Batch predictions
GET  /api/meme_ml_engine.php?action=performance    # Model performance
GET  /api/meme_ml_engine.php?action=compare&days=30 # ML vs rule comparison
GET  /api/meme_ml_engine.php?action=retrain        # Auto-retrain check
```

## ML Algorithm Features

### 7 Input Features (same as rule-based)
1. `explosive_volume` - 0-25 points
2. `parabolic_momentum` - 0-20 points  
3. `rsi_hype_zone` - 0-15 points
4. `social_momentum_proxy` - 0-15 points
5. `volume_concentration` - 0-10 points
6. `breakout_4h` - 0-10 points
7. `low_market_cap_bonus` - 0-5 points

### Algorithm
- **Method:** Weighted logistic regression with gradient descent
- **Output:** Win probability (0-100%)
- **Training:** Correlation analysis + gradient descent optimization
- **Auto-retrain:** Every 7 days or 50 new signals

### Performance Metrics
- Accuracy
- Precision
- Recall
- F1 Score
- Feature importance ranking

## Testing

```bash
# Check model status
curl "https://findtorontoevents.ca/findcryptopairs/api/meme_ml_engine.php?action=performance"

# Train model
curl "https://findtorontoevents.ca/findcryptopairs/api/meme_ml_engine.php?action=train"

# Compare methods
curl "https://findtorontoevents.ca/findcryptopairs/api/meme_ml_engine.php?action=compare&days=30"

# Predict single signal
curl "https://findtorontoevents.ca/findcryptopairs/api/meme_ml_engine.php?action=predict&signal={...}"
```

## Deployment

1. Upload `api/meme_ml_engine.php`
2. Upload `api/meme_ml_integration.js`
3. Apply HTML patches to `meme.html`
4. Access page - ML will auto-check status
5. Click "Train Model" when sufficient data exists (50+ signals)

## Expected Behavior

| Data Status | ML Behavior |
|-------------|-------------|
| < 50 signals | Shows "ML DISABLED", trains automatically when ready |
| 50+ signals | Shows "Train Model" button, user-initiated training |
| Trained model | Shows "ML ENABLED", real-time predictions on all signals |
| Stale model | Auto-retriggers training after 7 days |

## Visual Indicators

- 🟢 **ML ENABLED** - Model trained, predictions active
- 🟡 **ML DISABLED** - Not enough data or training needed
- **Win Probability Bar** - Visual indicator with confidence
- **Feature Contributions** - Shows which factors drove the prediction
