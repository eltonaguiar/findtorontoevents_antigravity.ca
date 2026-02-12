# Frontend Dashboard Design
## Unified Predictions Hub Layout

**Focus:** Feature high-performing systems prominently while maintaining usability

---

## Dashboard Layout Structure

### Header Section

```html
<div class="predictions-header">
  <div class="regime-status-bar">
    <span class="regime-indicator regime-sideways">
      🌀 Sideways Market (99.94% confidence)
    </span>
    <span class="hurst-indicator">📊 Hurst: 0.560 (Trending)</span>
    <span class="vix-indicator">⚡ VIX: 18.12 (Normal)</span>
    <span class="health-indicator">✅ All Systems Healthy</span>
  </div>
  
  <div class="high-performer-grid">
    <div class="performer-card performer-gold">
      <div class="performer-icon">⭐</div>
      <div class="performer-info">
        <div class="performer-name">Cursor Genius</div>
        <div class="performer-stats">+1,324% Return • 65.3% WR</div>
      </div>
    </div>
    
    <div class="performer-card performer-silver">
      <div class="performer-icon">🔄</div>
      <div class="performer-info">
        <div class="performer-name">Sector Rotation</div>
        <div class="performer-stats">+354% Return • 64% WR</div>
      </div>
    </div>
    
    <div class="performer-card performer-bronze">
      <div class="performer-icon">⚽</div>
      <div class="performer-info">
        <div class="performer-name">Sports Betting</div>
        <div class="performer-stats">+25.3% ROI • 33.3% WR</div>
      </div>
    </div>
    
    <div class="performer-card performer-blue">
      <div class="performer-icon">📈</div>
      <div class="performer-info">
        <div class="performer-name">Blue Chip Growth</div>
        <div class="performer-stats">+1,648% Return • 60.57% WR</div>
      </div>
    </div>
  </div>
</div>
```

### Execution Quality Metrics

```html
<div class="execution-quality-section">
  <h3>🚨 Execution Quality Gap Analysis</h3>
  <div class="quality-metrics-grid">
    <div class="metric-card">
      <div class="metric-value">70.5%</div>
      <div class="metric-label">Signal Quality</div>
      <div class="metric-trend positive">✅ Excellent</div>
    </div>
    
    <div class="metric-card critical">
      <div class="metric-value">3.84%</div>
      <div class="metric-label">Execution Quality</div>
      <div class="metric-trend negative">❌ Critical Gap</div>
    </div>
    
    <div class="metric-card">
      <div class="metric-value">66.66%</div>
      <div class="metric-label">Quality Gap</div>
      <div class="metric-trend negative">⚠️ Needs Attention</div>
    </div>
    
    <div class="metric-card">
      <div class="metric-value">$8,340</div>
      <div class="metric-label">Commission Drag</div>
      <div class="metric-trend negative">💸 Major Issue</div>
    </div>
  </div>
  
  <div class="quality-improvements">
    <h4>🎯 Improvement Opportunities</h4>
    <ul>
      <li><strong>Commission Negotiation:</strong> Reduce fees by 83.4%</li>
      <li><strong>Win/Loss Ratio:</strong> Target 2:1 minimum</li>
      <li><strong>Trade Timing:</strong> Reduce 67% timeout rate</li>
    </ul>
  </div>
</div>
```

### Asset Class Navigation

```html
<div class="asset-class-navigation">
  <div class="asset-filters">
    <button class="asset-filter active" data-asset="all">🌐 All Assets</button>
    <button class="asset-filter" data-asset="stocks">📈 Stocks</button>
    <button class="asset-filter" data-asset="crypto">🪙 Crypto</button>
    <button class="asset-filter" data-asset="forex">💱 Forex</button>
    <button class="asset-filter" data-asset="sports">⚽ Sports</button>
  </div>
  
  <div class="strategy-filters">
    <select class="strategy-select">
      <option value="all">All Strategies</option>
      <option value="cursor_genius">⭐ Cursor Genius</option>
      <option value="sector_rotation">🔄 Sector Rotation</option>
      <option value="sports_betting">⚽ Sports Betting</option>
      <option value="mean_reversion">📊 Mean Reversion</option>
    </select>
    <select class="confidence-select">
      <option value="all">All Confidence Levels</option>
      <option value="high">High Confidence (70+)</option>
      <option value="medium">Medium Confidence (50-69)</option>
      <option value="low">Low Confidence (<50)</option>
    </select>
  </div>
</div>
```

### Unified Picks Grid

```html
<div class="picks-grid-section">
  <h3>🎯 Current Top Picks</h3>
  <div class="picks-grid">
    <!-- High Confidence Picks -->
    <div class="pick-card high-confidence">
      <div class="pick-header">
        <span class="pick-symbol">AMZN</span>
        <span class="pick-score">63</span>
      </div>
      <div class="pick-details">
        <div class="pick-strategy">Mean Reversion Sniper</div>
        <div class="pick-metrics">
          <span class="kelly-size">🎯 Kelly: 15%</span>
          <span class="timeframe">⏰ 1-3 days</span>
        </div>
      </div>
    </div>
    
    <div class="pick-card high-confidence">
      <div class="pick-header">
        <span class="pick-symbol">SMCI</span>
        <span class="pick-score">60</span>
      </div>
      <div class="pick-details">
        <div class="pick-strategy">Earnings Catalyst Runner</div>
        <div class="pick-metrics">
          <span class="kelly-size">🎯 Kelly: 12%</span>
          <span class="timeframe">⏰ 2-5 days</span>
        </div>
      </div>
    </div>
    
    <!-- Medium Confidence Picks -->
    <div class="pick-card medium-confidence">
      <div class="pick-header">
        <span class="pick-symbol">GOOG</span>
        <span class="pick-score">58</span>
      </div>
      <div class="pick-details">
        <div class="pick-strategy">Mean Reversion Sniper</div>
        <div class="pick-metrics">
          <span class="kelly-size">🎯 Kelly: 8%</span>
          <span class="timeframe">⏰ 1-3 days</span>
        </div>
      </div>
    </div>
    
    <div class="pick-card medium-confidence">
      <div class="pick-header">
        <span class="pick-symbol">GS</span>
        <span class="pick-score">55</span>
      </div>
      <div class="pick-details">
        <div class="pick-strategy">Momentum Continuation</div>
        <div class="pick-metrics">
          <span class="kelly-size">🎯 Kelly: 10%</span>
          <span class="timeframe">⏰ 3-7 days</span>
        </div>
      </div>
    </div>
    
    <div class="pick-card medium-confidence">
      <div class="pick-header">
        <span class="pick-symbol">SHOP</span>
        <span class="pick-score">55</span>
      </div>
      <div class="pick-details">
        <div class="pick-strategy">Gap Up Momentum</div>
        <div class="pick-metrics">
          <span class="kelly-size">🎯 Kelly: 9%</span>
          <span class="timeframe">⏰ 2-4 days</span>
        </div>
      </div>
    </div>
    
    <div class="pick-card medium-confidence">
      <div class="pick-header">
        <span class="pick-symbol">BTC/USDT</span>
        <span class="pick-score">52</span>
      </div>
      <div class="pick-details">
        <div class="pick-strategy">Momentum Continuation</div>
        <div class="pick-metrics">
          <span class="kelly-size">🎯 Kelly: 6%</span>
          <span class="timeframe">⏰ 4-8 hours</span>
        </div>
      </div>
    </div>
  </div>
</div>
```

---

## CSS Styling

### High-Performer Cards

```css
.performer-card {
  background: var(--surface-1);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 15px;
  transition: all 0.3s ease;
  border: 1px solid transparent;
}

.performer-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 30px rgba(0,0,0,0.2);
}

.performer-gold {
  border-left: 4px solid #fbbf24;
  background: linear-gradient(135deg, var(--surface-1), #fef3c7);
}

.performer-silver {
  border-left: 4px solid #94a3b8;
  background: linear-gradient(135deg, var(--surface-1), #f1f5f9);
}

.performer-bronze {
  border-left: 4px solid #f59e0b;
  background: linear-gradient(135deg, var(--surface-1), #fef3c7);
}

.performer-blue {
  border-left: 4px solid #3b82f6;
  background: linear-gradient(135deg, var(--surface-1), #dbeafe);
}

.performer-icon {
  font-size: 2rem;
  width: 60px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255,255,255,0.1);
  border-radius: 50%;
}

.performer-name {
  font-weight: bold;
  font-size: 1.1rem;
  color: var(--text-1);
}

.performer-stats {
  font-size: 0.9rem;
  color: var(--text-2);
  margin-top: 5px;
}
```

### Execution Quality Metrics

```css
.quality-metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin: 20px 0;
}

.metric-card {
  background: var(--surface-1);
  padding: 20px;
  border-radius: 8px;
  text-align: center;
  border: 1px solid var(--surface-2);
}

.metric-card.critical {
  border: 2px solid #ef4444;
  background: linear-gradient(135deg, var(--surface-1), #fef2f2);
}

.metric-value {
  font-size: 2rem;
  font-weight: bold;
  color: var(--text-1);
}

.metric-label {
  font-size: 0.9rem;
  color: var(--text-2);
  margin: 5px 0;
}

.metric-trend.positive {
  color: #22c55e;
  font-weight: bold;
}

.metric-trend.negative {
  color: #ef4444;
  font-weight: bold;
}
```

### Picks Grid

```css
.picks-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 15px;
  margin: 20px 0;
}

.pick-card {
  background: var(--surface-1);
  border-radius: 8px;
  padding: 15px;
  border: 1px solid var(--surface-2);
  transition: all 0.3s ease;
}

.pick-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 5px 20px rgba(0,0,0,0.1);
}

.pick-card.high-confidence {
  border-left: 4px solid #22c55e;
}

.pick-card.medium-confidence {
  border-left: 4px solid #f59e0b;
}

.pick-card.low-confidence {
  border-left: 4px solid #ef4444;
}

.pick-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.pick-symbol {
  font-weight: bold;
  font-size: 1.2rem;
  color: var(--text-1);
}

.pick-score {
  background: var(--pk-500);
  color: white;
  padding: 4px 8px;
  border-radius: 20px;
  font-size: 0.9rem;
  font-weight: bold;
}

.pick-strategy {
  font-size: 0.9rem;
  color: var(--text-2);
  margin-bottom: 8px;
}

.pick-metrics {
  display: flex;
  justify-content: space-between;
  font-size: 0.8rem;
  color: var(--text-3);
}
```

---

## JavaScript Functionality

### Asset Filtering

```javascript
// Filter picks by asset class
function filterPicksByAsset(assetClass) {
  const picks = document.querySelectorAll('.pick-card');
  picks.forEach(pick => {
    const pickAsset = pick.getAttribute('data-asset') || 'stocks';
    if (assetClass === 'all' || pickAsset === assetClass) {
      pick.style.display = 'block';
    } else {
      pick.style.display = 'none';
    }
  });
}

// Filter by strategy
function filterPicksByStrategy(strategy) {
  const picks = document.querySelectorAll('.pick-card');
  picks.forEach(pick => {
    const pickStrategy = pick.getAttribute('data-strategy') || '';
    if (strategy === 'all' || pickStrategy === strategy) {
      pick.style.display = 'block';
    } else {
      pick.style.display = 'none';
    }
  });
}
```

### Real-time Updates

```javascript
// Fetch real-time data
async function updateDashboardData() {
  try {
    const response = await fetch('/api/predictions/v1/leaderboard');
    const data = await response.json();
    
    // Update high performers
    updateHighPerformers(data.high_performers);
    
    // Update regime status
    updateRegimeStatus(data.market_regime);
    
    // Update picks
    updatePicksGrid(data.picks);
    
  } catch (error) {
    console.error('Failed to update dashboard:', error);
  }
}

// Update every 30 seconds
setInterval(updateDashboardData, 30000);
```

---

## Responsive Design

### Mobile Layout

```css
@media (max-width: 768px) {
  .high-performer-grid {
    grid-template-columns: 1fr;
    gap: 10px;
  }
  
  .picks-grid {
    grid-template-columns: 1fr;
  }
  
  .quality-metrics-grid {
    grid-template-columns: 1fr 1fr;
  }
  
  .asset-filters {
    flex-direction: column;
    gap: 10px;
  }
}
```

### Tablet Layout

```css
@media (max-width: 1024px) and (min-width: 769px) {
  .high-performer-grid {
    grid-template-columns: 1fr 1fr;
  }
  
  .picks-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
```

---

## Navigation Integration

### Update Main Navigation

Add to `index.html` navigation:

```html
<details class="group/predictions nav-glow-predictions" open>
  <summary>⭐ Predictions Hub</summary>
  <div class="space-y-0.5 mt-1 ml-3">
    <a href="/predictions/dashboard.html" class="gold-glow-nav">
      ⭐ Unified Dashboard
    </a>
    <a href="/predictions/leaderboard.html">
      🏆 Performance Leaderboard
    </a>
    <a href="/predictions/sports.html">
      ⚽ Sports Betting
    </a>
    <details class="group/asset-classes">
      <summary>📊 Asset Classes</summary>
      <div class="space-y-0.5 mt-0.5 ml-3">
        <a href="/predictions/stocks.html">📈 Stocks</a>
        <a href="/predictions/crypto.html">🪙 Crypto</a>
        <a href="/predictions/forex.html">💱 Forex</a>
      </div>
    </details>
  </div>
</details>
```

---

## Implementation Priority

### Phase 1 (Week 1)
- Create basic dashboard layout
- Implement high-performer grid
- Add asset class filtering
- Basic picks grid

### Phase 2 (Week 2)
- Add execution quality metrics
- Implement real-time updates
- Add regime detection display
- Mobile responsiveness

### Phase 3 (Week 3)
- Advanced filtering (strategy, confidence)
- Performance charts
- User preferences/settings
- Advanced analytics integration

---

**Ready for frontend implementation review.**