/**
 * Signal Quality Scoring Engine
 * Calculates 0-100 quality scores for trading signals based on backtest metrics
 */

class QualityScorer {
  constructor(config = {}) {
    this.config = {
      weights: {
        sharpeRatio: 20,        // Sharpe 1.5 = 30 points
        winRate: 30,            // 60% WR = 18 points
        drawdownAdjustment: 20, // 15% DD = 17 points
        consensusBonus: 15,     // 3+ systems agree
        sampleSizePenalty: 0.5  // Halve score if <20 trades
      },
      minTradesForFullScore: 20,
      maxScore: 100,
      ...config
    };
  }

  /**
   * Calculate signal quality score (0-100)
   * @param {Object} signal - Signal object with metrics
   * @param {number} signal.sharpe_ratio - Sharpe ratio
   * @param {number} signal.win_rate - Win rate (0-1)
   * @param {number} signal.max_drawdown - Max drawdown (0-1, positive)
   * @param {number} signal.total_trades - Number of trades
   * @param {number} signal.consensus_count - Number of agreeing systems
   * @returns {number} Quality score (0-100)
   */
  calculateSignalQuality(signal) {
    const s = signal || {};
    const w = this.config.weights;
    
    // Base score from backtest metrics
    let score = 0;
    
    // Sharpe ratio component (Sharpe 1.5 = 30 points)
    const sharpe = parseFloat(s.sharpe_ratio) || 0;
    score += sharpe * w.sharpeRatio;
    
    // Win rate component (60% WR = 18 points)
    const wr = parseFloat(s.win_rate) || 0;
    const winRateNormalized = wr > 1 ? wr / 100 : wr; // Handle both 0.6 and 60
    score += winRateNormalized * w.winRate * 100; // Scale to match weight
    
    // Drawdown adjustment (15% DD = 17 points)
    // Lower drawdown = higher score
    const dd = parseFloat(s.max_drawdown) || 0;
    const ddNormalized = dd > 1 ? dd / 100 : dd;
    score += (1 - ddNormalized) * w.drawdownAdjustment;
    
    // Bonus for consensus
    const consensus = parseInt(s.consensus_count) || 0;
    if (consensus >= 3) {
      score += w.consensusBonus;
    } else if (consensus === 2) {
      score += w.consensusBonus * 0.5;
    }
    
    // Penalty for low sample size
    const trades = parseInt(s.total_trades) || 0;
    if (trades < this.config.minTradesForFullScore) {
      score *= this.config.weights.sampleSizePenalty;
    }
    
    // Clamp to 0-100 range
    return Math.min(this.config.maxScore, Math.max(0, Math.round(score)));
  }

  /**
   * Calculate quality score for a system based on its aggregated metrics
   * @param {Object} systemMetrics - System performance metrics
   * @returns {number} Quality score (0-100)
   */
  calculateSystemQuality(systemMetrics) {
    const m = systemMetrics || {};
    
    const signal = {
      sharpe_ratio: m.sharpe,
      win_rate: m.winRate,
      max_drawdown: m.maxDrawdown,
      total_trades: m.totalTrades,
      consensus_count: m.consensusCount || 1
    };
    
    return this.calculateSignalQuality(signal);
  }

  /**
   * Get quality grade and color based on score
   * @param {number} score - Quality score (0-100)
   * @returns {Object} Grade info with label, color, and description
   */
  getQualityGrade(score) {
    if (score >= 90) {
      return {
        grade: 'A+',
        label: 'Exceptional',
        color: '#22c55e',
        bgColor: '#22c55e22',
        borderColor: '#22c55e44',
        description: 'Outstanding risk-adjusted returns with strong statistical significance'
      };
    } else if (score >= 80) {
      return {
        grade: 'A',
        label: 'Excellent',
        color: '#22c55e',
        bgColor: '#22c55e22',
        borderColor: '#22c55e44',
        description: 'Strong performance with good risk management'
      };
    } else if (score >= 70) {
      return {
        grade: 'B+',
        label: 'Very Good',
        color: '#84cc16',
        bgColor: '#84cc1622',
        borderColor: '#84cc1644',
        description: 'Above average performance with acceptable risk'
      };
    } else if (score >= 60) {
      return {
        grade: 'B',
        label: 'Good',
        color: '#eab308',
        bgColor: '#eab30822',
        borderColor: '#eab30844',
        description: 'Solid performance, suitable for allocation'
      };
    } else if (score >= 50) {
      return {
        grade: 'C+',
        label: 'Moderate',
        color: '#f97316',
        bgColor: '#f9731622',
        borderColor: '#f9731644',
        description: 'Average performance, consider with caution'
      };
    } else if (score >= 40) {
      return {
        grade: 'C',
        label: 'Fair',
        color: '#f97316',
        bgColor: '#f9731622',
        borderColor: '#f9731644',
        description: 'Below average, limited allocation recommended'
      };
    } else if (score >= 30) {
      return {
        grade: 'D',
        label: 'Poor',
        color: '#ef4444',
        bgColor: '#ef444422',
        borderColor: '#ef444444',
        description: 'Weak performance, avoid or paper trade'
      };
    } else {
      return {
        grade: 'F',
        label: 'Fail',
        color: '#991b1b',
        bgColor: '#991b1b22',
        borderColor: '#991b1b44',
        description: 'Unacceptable risk-adjusted returns'
      };
    }
  }

  /**
   * Calculate aggregate quality for a set of picks
   * @param {Array} picks - Array of pick objects
   * @returns {Object} Aggregate quality metrics
   */
  calculateAggregateQuality(picks) {
    if (!picks || picks.length === 0) {
      return {
        averageScore: 0,
        medianScore: 0,
        minScore: 0,
        maxScore: 0,
        highQualityCount: 0,  // >= 70
        mediumQualityCount: 0, // 40-69
        lowQualityCount: 0,    // < 40
        totalCount: 0
      };
    }

    const scores = picks.map(p => this.calculateSignalQuality(p)).sort((a, b) => a - b);
    const sum = scores.reduce((a, b) => a + b, 0);
    
    return {
      averageScore: Math.round(sum / scores.length),
      medianScore: scores[Math.floor(scores.length / 2)],
      minScore: scores[0],
      maxScore: scores[scores.length - 1],
      highQualityCount: scores.filter(s => s >= 70).length,
      mediumQualityCount: scores.filter(s => s >= 40 && s < 70).length,
      lowQualityCount: scores.filter(s => s < 40).length,
      totalCount: scores.length
    };
  }

  /**
   * Render quality badge HTML
   * @param {number} score - Quality score
   * @param {boolean} showLabel - Whether to show text label
   * @returns {string} HTML string
   */
  renderQualityBadge(score, showLabel = true) {
    const grade = this.getQualityGrade(score);
    const label = showLabel ? ` ${grade.grade}` : '';
    
    return `
      <span class="quality-badge" 
            style="
              background: ${grade.bgColor}; 
              color: ${grade.color}; 
              border: 1px solid ${grade.borderColor};
              padding: 2px 8px;
              border-radius: 10px;
              font-size: 0.75rem;
              font-weight: 600;
            "
            title="${grade.description}"
      >
        ${score}${label}
      </span>
    `;
  }

  /**
   * Render quality gauge HTML (visual bar)
   * @param {number} score - Quality score
   * @param {number} width - Width in pixels
   * @returns {string} HTML string
   */
  renderQualityGauge(score, width = 100) {
    const grade = this.getQualityGrade(score);
    const percentage = Math.min(100, Math.max(0, score));
    
    return `
      <div class="quality-gauge" style="width: ${width}px; position: relative;">
        <div class="quality-gauge-bg" style="
          height: 6px;
          background: #1e1e3a;
          border-radius: 3px;
          overflow: hidden;
        ">
          <div class="quality-gauge-fill" style="
            height: 100%;
            width: ${percentage}%;
            background: linear-gradient(90deg, ${grade.color}88, ${grade.color});
            border-radius: 3px;
            transition: width 0.3s ease;
          "></div>
        </div>
        <span class="quality-gauge-label" style="
          font-size: 0.65rem;
          color: ${grade.color};
          position: absolute;
          right: -35px;
          top: -3px;
          font-weight: 600;
        ">${score}</span>
      </div>
    `;
  }
}

// Create global instance for use in other scripts
if (typeof window !== 'undefined') {
  window.qualityScorer = new QualityScorer();
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
  module.exports = QualityScorer;
}
