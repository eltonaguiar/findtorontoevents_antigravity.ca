/**
 * Meme Coin ML Integration
 * Frontend JavaScript for ML-enhanced meme coin predictions
 */

// ML-enhanced scanner integration
const MemeML = {
    apiUrl: '/findcryptopairs/api/meme_ml_engine.php',
    currentPredictions: [],
    mlEnabled: true,
    
    /**
     * Initialize ML integration
     */
    init: function() {
        console.log('MemeML: Initializing...');
        this.checkModelStatus();
    },
    
    /**
     * Check if ML model is trained and available
     */
    checkModelStatus: function() {
        fetch(this.apiUrl + '?action=performance')
            .then(r => r.json())
            .then(data => {
                if (data.ok) {
                    console.log('MemeML: Model available', data.model);
                    this.mlEnabled = true;
                    this.updateUIForML(true);
                } else {
                    console.log('MemeML: No trained model, using rule-based only');
                    this.mlEnabled = false;
                    this.updateUIForML(false);
                }
            })
            .catch(err => {
                console.error('MemeML: Error checking model', err);
                this.mlEnabled = false;
            });
    },
    
    /**
     * Get ML prediction for a signal
     */
    predict: function(signalData) {
        if (!this.mlEnabled) {
            return Promise.resolve({
                ok: false,
                error: 'ML not available',
                rule_based_only: true
            });
        }
        
        return fetch(this.apiUrl + '?action=predict&signal=' + encodeURIComponent(JSON.stringify(signalData)))
            .then(r => r.json());
    },
    
    /**
     * Batch predict for multiple signals
     */
    batchPredict: function(signals) {
        if (!this.mlEnabled) {
            return Promise.resolve({ ok: false, error: 'ML not available' });
        }
        
        return fetch(this.apiUrl + '?action=batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: 'signals=' + encodeURIComponent(JSON.stringify(signals))
        }).then(r => r.json());
    },
    
    /**
     * Train or retrain the model
     */
    train: function() {
        return fetch(this.apiUrl + '?action=train')
            .then(r => r.json())
            .then(data => {
                if (data.ok) {
                    this.mlEnabled = true;
                    this.updateUIForML(true);
                }
                return data;
            });
    },
    
    /**
     * Compare ML vs rule-based performance
     */
    compare: function(days = 30) {
        return fetch(this.apiUrl + '?action=compare&days=' + days)
            .then(r => r.json());
    },
    
    /**
     * Update UI to show ML status
     */
    updateUIForML: function(enabled) {
        const mlBadge = document.getElementById('ml-status-badge');
        if (mlBadge) {
            if (enabled) {
                mlBadge.textContent = 'ML ENABLED';
                mlBadge.className = 'badge badge-strong';
                mlBadge.style.background = 'rgba(34,197,94,0.2)';
                mlBadge.style.color = '#22c55e';
                mlBadge.style.borderColor = 'rgba(34,197,94,0.4)';
            } else {
                mlBadge.textContent = 'ML DISABLED';
                mlBadge.className = 'badge';
                mlBadge.style.background = 'rgba(100,100,100,0.2)';
                mlBadge.style.color = '#888';
            }
        }
    },
    
    /**
     * Render ML-enhanced winner card
     */
    renderMLWinnerCard: function(signal, mlPrediction) {
        const mlScore = mlPrediction.ml_score || 0;
        const winProb = mlPrediction.win_probability || 0;
        const confidence = mlPrediction.confidence || 'low';
        const rec = mlPrediction.recommendation || { action: 'skip' };
        
        let probColor = winProb >= 60 ? 'var(--green)' : (winProb >= 45 ? 'var(--gold)' : 'var(--red)');
        let confidenceBadge = confidence === 'high' ? '●' : (confidence === 'medium' ? '◐' : '○');
        
        let html = `
        <div class="ml-prediction-bar" style="margin-top:12px;padding:12px;background:rgba(0,0,0,0.2);border-radius:8px;border:1px solid rgba(255,255,255,0.05);">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <span style="font-size:11px;color:var(--dim);text-transform:uppercase;letter-spacing:1px;">
                    🤖 ML Prediction ${confidenceBadge}
                </span>
                <span style="font-size:11px;color:${probColor};font-weight:700;">
                    ${winProb}% Win Probability
                </span>
            </div>
            <div style="height:6px;background:rgba(255,255,255,0.1);border-radius:3px;overflow:hidden;margin-bottom:8px;">
                <div style="height:100%;width:${winProb}%;background:linear-gradient(90deg,${probColor},${winProb > 70 ? '#22c55e' : probColor});border-radius:3px;transition:width 0.5s;"></div>
            </div>
            <div style="display:flex;gap:16px;flex-wrap:wrap;font-size:11px;">
                <span style="color:var(--dim);">ML Score: <strong style="color:var(--text);">${mlScore}/100</strong></span>
                <span style="color:var(--dim);">Confidence: <strong style="color:var(--text);">${confidence}</strong></span>
                <span style="color:var(--dim);">Rec: <strong style="color:${rec.action === 'strong_buy' ? 'var(--accent)' : (rec.action === 'buy' ? '#c084fc' : (rec.action === 'lean_buy' ? 'var(--gold)' : 'var(--red)'))};">${rec.action.replace('_', ' ').toUpperCase()}</strong></span>
            </div>
        </div>
        `;
        
        // Add feature contributions if available
        if (mlPrediction.feature_contributions) {
            html += `<div class="ml-features" style="margin-top:8px;display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:6px;">`;
            for (let feature in mlPrediction.feature_contributions) {
                let fc = mlPrediction.feature_contributions[feature];
                let pct = Math.round(fc.contribution * 100);
                html += `
                <div style="font-size:9px;padding:4px 6px;background:rgba(255,255,255,0.03);border-radius:4px;">
                    <span style="color:var(--dim);text-transform:capitalize;">${feature.replace(/_/g, ' ')}</span>
                    <span style="float:right;color:${pct > 10 ? 'var(--accent)' : 'var(--text)'};">${pct}%</span>
                </div>`;
            }
            html += `</div>`;
        }
        
        return html;
    },
    
    /**
     * Enhance existing winner cards with ML predictions
     */
    enhanceWinners: function() {
        if (!this.mlEnabled) return;
        
        // Get current winners from page
        const winners = window.currentWinners || [];
        if (winners.length === 0) return;
        
        // Batch predict
        this.batchPredict(winners).then(result => {
            if (result.ok) {
                this.currentPredictions = result.predictions;
                
                // Update each winner card
                result.predictions.forEach(pred => {
                    const card = document.querySelector(`[data-coin="${pred.coin}"]`);
                    if (card) {
                        const mlHtml = this.renderMLWinnerCard(pred, pred.prediction);
                        const mlContainer = card.querySelector('.ml-container') || card;
                        mlContainer.insertAdjacentHTML('beforeend', mlHtml);
                    }
                });
            }
        });
    },
    
    /**
     * Render ML vs Rule-based comparison
     */
    renderComparison: function(data) {
        if (!data.ok) return '<p>ML comparison data not available</p>';
        
        const comp = data.comparison;
        
        return `
        <div style="background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:16px;margin:16px 0;">
            <h4 style="font-size:14px;margin-bottom:12px;color:var(--accent);">🤖 ML vs Rule-Based Comparison</h4>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;">
                <div style="padding:12px;background:rgba(255,255,255,0.02);border-radius:8px;border:1px solid rgba(255,255,255,0.05);">
                    <div style="font-size:11px;color:var(--dim);margin-bottom:4px;">Rule-Based (Score ≥70)</div>
                    <div style="font-size:20px;font-weight:700;color:var(--text);">${comp.rule_based.win_rate}% WR</div>
                    <div style="font-size:11px;color:var(--dim);">${comp.rule_based.wins}W / ${comp.rule_based.losses}L</div>
                    <div style="font-size:11px;color:${comp.rule_based.avg_pl >= 0 ? 'var(--green)' : 'var(--red)'};margin-top:4px;">Avg P&L: ${comp.rule_based.avg_pl}%</div>
                </div>
                <div style="padding:12px;background:rgba(232,121,249,0.08);border-radius:8px;border:1px solid rgba(232,121,249,0.2);">
                    <div style="font-size:11px;color:var(--accent);margin-bottom:4px;">🤖 ML-Based (Prob ≥50%)</div>
                    <div style="font-size:20px;font-weight:700;color:var(--accent);">${comp.ml_based.win_rate}% WR</div>
                    <div style="font-size:11px;color:var(--dim);">${comp.ml_based.wins}W / ${comp.ml_based.losses}L</div>
                    <div style="font-size:11px;color:${comp.ml_based.avg_pl >= 0 ? 'var(--green)' : 'var(--red)'};margin-top:4px;">Avg P&L: ${comp.ml_based.avg_pl}%</div>
                </div>
            </div>
            <div style="font-size:11px;color:var(--dim);line-height:1.6;">
                <strong>Analysis:</strong> ${comp.ml_based.win_rate > comp.rule_based.win_rate 
                    ? '🤖 ML is outperforming rule-based by ' + (comp.ml_based.win_rate - comp.rule_based.win_rate).toFixed(1) + '%'
                    : (comp.ml_based.win_rate < comp.rule_based.win_rate 
                        ? '⚠️ ML underperforming by ' + (comp.rule_based.win_rate - comp.ml_based.win_rate).toFixed(1) + '% - more training needed'
                        : '📊 Performance equal - both methods showing similar results')}
            </div>
        </div>
        `;
    },
    
    /**
     * Show ML training interface
     */
    showTrainingInterface: function() {
        const html = `
        <div id="ml-training-modal" style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.8);z-index:1000;display:flex;align-items:center;justify-content:center;">
            <div style="background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:24px;max-width:500px;width:90%;max-height:80vh;overflow:auto;">
                <h3 style="font-size:18px;margin-bottom:16px;">🤖 Train ML Model</h3>
                <div id="ml-training-content">
                    <p style="font-size:13px;color:var(--dim);line-height:1.6;margin-bottom:16px;">
                        The ML model learns from historical signal outcomes to improve predictions. 
                        Training requires at least 50 closed signals with known outcomes.
                    </p>
                    <button onclick="MemeML.startTraining()" style="background:var(--accent);color:#fff;border:none;padding:10px 20px;border-radius:6px;cursor:pointer;font-size:14px;">
                        Start Training
                    </button>
                    <button onclick="document.getElementById('ml-training-modal').remove()" style="background:transparent;color:var(--dim);border:1px solid var(--border);padding:10px 20px;border-radius:6px;cursor:pointer;font-size:14px;margin-left:8px;">
                        Cancel
                    </button>
                </div>
                <div id="ml-training-results" style="display:none;"></div>
            </div>
        </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', html);
    },
    
    /**
     * Start training process
     */
    startTraining: function() {
        const content = document.getElementById('ml-training-content');
        const results = document.getElementById('ml-training-results');
        
        content.innerHTML = '<div style="text-align:center;padding:20px;"><div class="loading">Training model...</div><p style="font-size:12px;color:var(--dim);margin-top:8px;">This may take 30-60 seconds</p></div>';
        
        this.train().then(data => {
            results.style.display = 'block';
            
            if (data.ok) {
                results.innerHTML = `
                    <div style="background:rgba(34,197,94,0.1);border:1px solid rgba(34,197,94,0.3);border-radius:8px;padding:12px;margin-bottom:12px;">
                        <div style="font-size:14px;font-weight:700;color:var(--green);margin-bottom:8px;">✅ Training Complete!</div>
                        <div style="font-size:12px;color:var(--text);line-height:1.6;">
                            <div>Model ID: <code>${data.model_id}</code></div>
                            <div>Samples used: ${data.samples_used} (${data.winners} wins, ${data.losers} losses)</div>
                            <div>Base win rate: ${data.base_win_rate}%</div>
                            <div>Model accuracy: ${(data.metrics.accuracy * 100).toFixed(1)}%</div>
                            <div>F1 Score: ${(data.metrics.f1_score * 100).toFixed(1)}%</div>
                        </div>
                    </div>
                    <div style="font-size:12px;color:var(--dim);margin-bottom:12px;">
                        <strong>Optimized Weights:</strong>
                        <pre style="background:rgba(0,0,0,0.2);padding:8px;border-radius:4px;margin-top:4px;overflow:auto;">${JSON.stringify(data.optimized_weights, null, 2)}</pre>
                    </div>
                    <button onclick="document.getElementById('ml-training-modal').remove();location.reload()" style="background:var(--accent);color:#fff;border:none;padding:10px 20px;border-radius:6px;cursor:pointer;font-size:14px;width:100%;">
                        Close & Refresh
                    </button>
                `;
            } else {
                results.innerHTML = `
                    <div style="background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);border-radius:8px;padding:12px;">
                        <div style="font-size:14px;font-weight:700;color:var(--red);margin-bottom:8px;">❌ Training Failed</div>
                        <div style="font-size:12px;color:var(--text);">${data.error}</div>
                        ${data.recommendation ? `<div style="font-size:12px;color:var(--dim);margin-top:8px;">${data.recommendation}</div>` : ''}
                    </div>
                `;
            }
        });
    }
};

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        MemeML.init();
    });
} else {
    MemeML.init();
}

// Expose to global scope for debugging
window.MemeML = MemeML;
