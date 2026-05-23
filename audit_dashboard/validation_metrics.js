/**
 * Audit Dashboard - Quant-Grade Validation Metrics
 * Phase 1: Walk-Forward Efficiency (WFE) & Transaction Cost Modeling
 * 
 * Based on institutional quant validation frameworks from top firms.
 */

(function() {
  'use strict';

  // ============================================================
  // TRANSACTION COST MODELS (per asset class)
  // Based on alpha_engine/transaction_costs.py
  // ============================================================
  
  const COST_MODELS = {
    CRYPTO: {
      major: { total: 0.0025, name: 'crypto_spot' },      // 0.25% BTC/ETH
      altcoin: { total: 0.007, name: 'crypto_altcoin' },  // 0.70% alts
      meme: { total: 0.01, name: 'meme_coins' }           // 1.00% memes
    },
    FOREX: {
      default: { total: 0.0003, name: 'forex_majors' }    // 0.03%
    },
    EQUITY: {
      etf: { total: 0.0003, name: 'stocks_etf' },         // 0.03%
      penny: { total: 0.015, name: 'penny_stocks' }       // 1.50%
    },
    ETF: {
      default: { total: 0.0003, name: 'etf' }             // 0.03%
    },
    COMMODITY: {
      default: { total: 0.0005, name: 'commodity' }       // 0.05%
    },
    FUTURES: {
      default: { total: 0.0008, name: 'futures' }         // 0.08%
    }
  };

  // Major crypto symbols for tight spreads
  const MAJOR_CRYPTO = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT'];
  const MEME_INDICATORS = ['MEME', 'PEPE', 'DOGE', 'SHIB', 'WIF', 'BONK', 'MOG'];

  /**
   * Get transaction cost for a symbol
   */
  function getTransactionCost(symbol, assetClass) {
    if (!symbol) return { cost: 0, model: 'unknown' };
    
    const sym = symbol.toUpperCase();
    const asset = (assetClass || 'CRYPTO').toUpperCase();
    
    // Crypto handling
    if (asset === 'CRYPTO') {
      if (MAJOR_CRYPTO.includes(sym)) {
        return COST_MODELS.CRYPTO.major;
      }
      // Check for meme coins
      for (const m of MEME_INDICATORS) {
        if (sym.includes(m)) {
          return COST_MODELS.CRYPTO.meme;
        }
      }
      return COST_MODELS.CRYPTO.altcoin;
    }
    
    // Other asset classes
    if (asset === 'FOREX') return COST_MODELS.FOREX.default;
    if (asset === 'ETF') return COST_MODELS.ETF.default;
    if (asset === 'COMMODITY') return COST_MODELS.COMMODITY.default;
    if (asset === 'FUTURES') return COST_MODELS.FUTURES.default;
    if (asset === 'EQUITY') return COST_MODELS.EQUITY.etf;
    
    return { cost: 0, model: 'unknown' };
  }

  /**
   * Apply transaction costs to calculate net P&L
   */
  function calculateNetPnL(grossPnlPct, symbol, assetClass) {
    const { total: cost } = getTransactionCost(symbol, assetClass);
    const netPnl = grossPnlPct - cost;
    return {
      grossPnlPct: grossPnlPct,
      netPnlPct: netPnl,
      transactionCostPct: cost,
      isPositiveAfterCosts: netPnl > 0
    };
  }

  // ============================================================
  // WALK-FORWARD EFFICIENCY (WFE) CALCULATION
  // 
  // WFE = OOS Sharpe / IS Sharpe
  // Target: > 0.7 (AlgoXpert standard)
  // ============================================================

  /**
   * Calculate WFE from walk-forward validation data
   * @param {Array} windows - Array of window metrics from walk-forward validator
   * @returns {Object} WFE metrics
   */
  function calculateWFE(windows) {
    if (!windows || windows.length < 2) {
      return { wfe: null, status: 'insufficient_data', reason: 'Need at least 2 windows' };
    }

    // Split into in-sample (IS) and out-of-sample (OOS) - typically 80/20 or 70/30
    const midIdx = Math.floor(windows.length * 0.7); // 70% IS, 30% OOS
    const isWindows = windows.slice(0, midIdx);
    const oosWindows = windows.slice(midIdx);

    // Calculate Sharpe for each window
    function windowSharpe(w) {
      if (!w.sharpe && w.sharpe !== 0) return 0;
      return parseFloat(w.sharpe) || 0;
    }

    // Aggregate metrics for IS and OOS
    function aggregateWindowMetrics(ws) {
      if (ws.length === 0) return { sharpe: 0, wr: 0, pf: 0, n: 0 };
      
      const totalN = ws.reduce((sum, w) => sum + (w.n || 0), 0);
      const totalWin = ws.reduce((sum, w) => sum + (w.wins || 0), 0);
      const totalLoss = ws.reduce((sum, w) => sum + (w.losses || 0), 0);
      const totalPnl = ws.reduce((sum, w) => sum + (w.total_pnl || 0), 0);
      
      const wr = totalN > 0 ? (totalWin / totalN) * 100 : 0;
      const grossWin = ws.reduce((sum, w) => sum + (w.gross_win || 0), 0);
      const grossLoss = ws.reduce((sum, w) => sum + (w.gross_loss || 0), 0);
      const pf = grossLoss > 0 ? grossWin / grossLoss : (grossWin > 0 ? 999 : 0);
      
      // Average Sharpe across windows
      const avgSharpe = ws.reduce((sum, w) => sum + windowSharpe(w), 0) / ws.length;
      
      return { sharpe: avgSharpe, wr, pf, n: totalN, totalPnl };
    }

    const isMetrics = aggregateWindowMetrics(isWindows);
    const oosMetrics = aggregateWindowMetrics(oosWindows);

    // Calculate WFE
    let wfe = 0;
    if (isMetrics.sharpe > 0) {
      wfe = oosMetrics.sharpe / isMetrics.sharpe;
    }

    // Determine status based on AlgoXpert standard (> 0.7)
    // Using simple text icons to avoid encoding issues
    let status = 'unknown';
    let statusIcon = '';
    
    if (wfe >= 0.7) {
      status = 'excellent';
      statusIcon = '[OK]'; // Green check
    } else if (wfe >= 0.5) {
      status = 'acceptable';
      statusIcon = '[~]'; // Yellow
    } else if (wfe >= 0.3) {
      status = 'warning';
      statusIcon = '[!]'; // Orange
    } else {
      status = 'overfitting';
      statusIcon = '[X]'; // Red - significant overfitting
    }

    return {
      wfe: wfe.toFixed(2),
      status: status,
      statusIcon: statusIcon,
      isMetrics: isMetrics,
      oosMetrics: oosMetrics,
      target: 0.7,
      interpretation: getWFEInterpretation(wfe)
    };
  }

  /**
   * Get human-readable WFE interpretation
   */
  function getWFEInterpretation(wfe) {
    if (wfe >= 0.9) return 'Excellent - Model generalizes well';
    if (wfe >= 0.7) return 'Good - Real edge, low overfitting';
    if (wfe >= 0.5) return 'Acceptable - Some degradation';
    if (wfe >= 0.3) return 'Warning - Significant overfitting';
    return 'Critical - Curve-fitting likely';
  }

  // ============================================================
  // CV SHARPE (Cross-Validation Sharpe)
  // Target: < 0.5 for low overfitting
  // ============================================================

  /**
   * Calculate CV Sharpe - measures stability of Sharpe across folds
   * Lower is better (more stable = less overfitting)
   */
  function calculateCVSharpe(windows) {
    if (!windows || windows.length < 2) {
      return { cvSharpe: null, status: 'insufficient_data' };
    }

    const sharpes = windows.map(w => parseFloat(w.sharpe) || 0).filter(s => s !== 0);
    
    if (sharpes.length < 2) {
      return { cvSharpe: null, status: 'insufficient_data' };
    }

    const meanSharpe = sharpes.reduce((a, b) => a + b, 0) / sharpes.length;
    const variance = sharpes.reduce((sum, s) => sum + Math.pow(s - meanSharpe, 2), 0) / sharpes.length;
    const stdDev = Math.sqrt(variance);

    // CV Sharpe = stdDev of Sharpe / mean Sharpe
    // This is coefficient of variation - lower means more stable
    const cvSharpe = meanSharpe > 0 ? stdDev / Math.abs(meanSharpe) : 999;

    let status = 'unknown';
    if (cvSharpe < 0.3) status = 'excellent';
    else if (cvSharpe < 0.5) status = 'acceptable';
    else if (cvSharpe < 0.8) status = 'warning';
    else status = 'overfitting';

    return {
      cvSharpe: cvSharpe.toFixed(2),
      meanSharpe: meanSharpe.toFixed(3),
      stdDev: stdDev.toFixed(3),
      status: status,
      target: 0.5
    };
  }

  // ============================================================
  // RISK METRICS (VaR, CVaR, Drawdown)
  // ============================================================

  /**
   * Calculate Value at Risk (VaR) - historical method
   */
  function calculateVaR(returns, confidence = 0.05) {
    if (!returns || returns.length < 10) return null;
    
    const sorted = [...returns].sort((a, b) => a - b);
    const idx = Math.floor(sorted.length * confidence);
    return sorted[idx] || 0;
  }

  /**
   * Calculate Conditional VaR (CVaR / Expected Shortfall)
   */
  function calculateCVaR(returns, confidence = 0.05) {
    if (!returns || returns.length < 10) return null;
    
    const sorted = [...returns].sort((a, b) => a - b);
    const cutoff = Math.floor(sorted.length * confidence);
    const tail = sorted.slice(0, cutoff);
    
    if (tail.length === 0) return null;
    return tail.reduce((a, b) => a + b, 0) / tail.length;
  }

  /**
   * Calculate maximum drawdown from equity curve
   */
  function calculateMaxDrawdown(equityCurve) {
    if (!equityCurve || equityCurve.length < 2) return null;
    
    let peak = equityCurve[0];
    let maxDD = 0;
    
    for (const val of equityCurve) {
      if (val > peak) peak = val;
      const dd = ((val - peak) / peak) * 100;
      if (dd < maxDD) maxDD = dd;
    }
    
    return maxDD;
  }

  /**
   * Calculate Calmar Ratio (Annualized Return / Max Drawdown)
   */
  function calculateCalmar(annualizedReturn, maxDrawdown) {
    if (!maxDrawdown || maxDrawdown === 0) return null;
    return annualizedReturn / Math.abs(maxDrawdown);
  }

  // ============================================================
  // CSS STYLES (injected when needed)
  // ============================================================

  function injectStyles() {
    if (document.getElementById('validation-metrics-styles')) return;
    
    const styles = document.createElement('style');
    styles.id = 'validation-metrics-styles';
    styles.textContent = `
      .validation-metrics-panel {
        background: linear-gradient(135deg, rgba(15, 15, 25, 0.98), rgba(25, 25, 45, 0.95));
        border: 1px solid #3a3a5a;
        border-radius: 8px;
        padding: 12px;
        margin: 8px 0;
        font-size: 12px;
      }
      .validation-metrics-panel h4 {
        color: #a78bfa;
        margin: 0 0 10px 0;
        font-size: 14px;
        border-bottom: 1px solid #3a3a5a;
        padding-bottom: 6px;
      }
      .vm-section {
        margin-bottom: 10px;
      }
      .vm-section h5 {
        color: #60a5fa;
        margin: 0 0 6px 0;
        font-size: 12px;
      }
      .vm-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 11px;
      }
      .vm-table td {
        padding: 4px 8px;
        border-bottom: 1px solid #2a2a4a;
      }
      .vm-table td:first-child {
        color: #9ca3af;
      }
      .vm-table td.positive { color: #10b981; }
      .vm-table td.negative { color: #ef4444; }
      .vm-table td.cost { color: #f59e0b; }
      .vm-table td.status-excellent { color: #10b981; }
      .vm-table td.status-acceptable { color: #fbbf24; }
      .vm-table td.status-warning { color: #f97316; }
      .vm-table td.status-overfitting { color: #ef4444; }
      .vm-table td.status-insufficient_data { color: #6b7280; }
    `;
    document.head.appendChild(styles);
  }

  // ============================================================
  // UI DISPLAY FUNCTIONS
  // ============================================================

  /**
   * Initialize validation metrics - call on dashboard load
   */
  function initialize() {
    injectStyles();
    console.log('[ValidationMetrics] Initialized with WFE and Transaction Cost tracking');
  }

  /**
   * Display validation metrics panel for a pick/strategy
   */
  function displayValidationMetrics(pick, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const symbol = pick.symbol || '';
    const assetClass = pick.asset_class || 'CRYPTO';
    const grossPnl = pick.pnl_pct || 0;
    
    // Transaction costs
    const tc = calculateNetPnL(grossPnl, symbol, assetClass);
    
    // WFE (if windows data available)
    const wfe = pick.windows ? calculateWFE(pick.windows) : null;
    const cvSharpe = pick.windows ? calculateCVSharpe(pick.windows) : null;

    const html = `
      <div class="validation-metrics-panel">
        <h4>Quant Validation Metrics</h4>
        
        <div class="vm-section">
          <h5>Transaction Costs</h5>
          <table class="vm-table">
            <tr><td>Gross P&L</td><td class="${grossPnl >= 0 ? 'positive' : 'negative'}">${(grossPnl * 100).toFixed(2)}%</td></tr>
            <tr><td>Transaction Cost</td><td class="cost">-${(tc.transactionCostPct * 100).toFixed(2)}%</td></tr>
            <tr><td>Net P&L</td><td class="${tc.netPnlPct >= 0 ? 'positive' : 'negative'}">${(tc.netPnlPct * 100).toFixed(2)}%</td></tr>
            <tr><td>Cost Model</td><td>${tc.model}</td></tr>
          </table>
        </div>
        
        ${wfe ? `
        <div class="vm-section">
          <h5>Walk-Forward Efficiency</h5>
          <table class="vm-table">
            <tr><td>WFE</td><td class="status-${wfe.status}">${wfe.wfe} ${wfe.statusIcon}</td></tr>
            <tr><td>Target</td><td>> ${wfe.target}</td></tr>
            <tr><td>Interpretation</td><td>${wfe.interpretation}</td></tr>
          </table>
        </div>
        ` : ''}
        
        ${cvSharpe ? `
        <div class="vm-section">
          <h5>CV Sharpe (Stability)</h5>
          <table class="vm-table">
            <tr><td>CV Sharpe</td><td class="status-${cvSharpe.status}">${cvSharpe.cvSharpe}</td></tr>
            <tr><td>Target</td><td>< ${cvSharpe.target}</td></tr>
            <tr><td>Mean Sharpe</td><td>${cvSharpe.meanSharpe}</td></tr>
          </table>
        </div>
        ` : ''}
      </div>
    `;

    container.innerHTML = html;
  }

  /**
   * Add validation metrics column to picks table
   */
  function addValidationColumnToTable() {
    // Find the picks table and add validation column header
    const tables = document.querySelectorAll('table');
    tables.forEach(table => {
      const headers = table.querySelectorAll('th');
      const hasSymbolCol = Array.from(headers).some(h => h.textContent.includes('Symbol'));
      if (hasSymbolCol) {
        // Add validation column after status
        const statusHeader = Array.from(headers).find(h => h.textContent.includes('Status'));
        if (statusHeader && !headers.some(h => h.textContent.includes('WFE'))) {
          const wfeHeader = document.createElement('th');
          wfeHeader.textContent = 'WFE';
          wfeHeader.title = 'Walk-Forward Efficiency (target > 0.7)';
          statusHeader.after(wfeHeader);
        }
      }
    });
  }

  // ============================================================
  // AUTO-INITIALIZE
  // ============================================================

  // Auto-initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize);
  } else {
    initialize();
  }

  // ============================================================
  // EXPORTS
  // ============================================================

  window.ValidationMetrics = {
    // Initialization
    initialize,
    
    // Transaction costs
    getTransactionCost,
    calculateNetPnL,
    COST_MODELS,
    
    // WFE
    calculateWFE,
    calculateCVSharpe,
    
    // Risk metrics
    calculateVaR,
    calculateCVaR,
    calculateMaxDrawdown,
    calculateCalmar,
    
    // UI
    displayValidationMetrics,
    addValidationColumnToTable
  };

  console.log('[ValidationMetrics] Phase 1 loaded - WFE & Transaction Costs ready');
})();