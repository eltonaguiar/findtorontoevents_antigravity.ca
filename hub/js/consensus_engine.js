/**
 * Cross-System Consensus Engine
 * Fetches signals from all systems, calculates consensus, generates Super Signals
 */

class ConsensusEngine {
  constructor(manifestUrl = 'data/systems_manifest.json') {
    this.manifestUrl = manifestUrl;
    this.manifest = null;
    this.systemData = new Map();
    this.systemClosedData = new Map(); // Closed picks per system
    this.consensusMatrix = new Map();
    this.lastUpdate = null;
    this.refreshInterval = null;
    this.listeners = [];
    this.qualityScorer = typeof window !== 'undefined' && window.qualityScorer
      ? window.qualityScorer
      : new (this.getQualityScorerClass());
  }

  getQualityScorerClass() {
    // Fallback if quality_scorer.js not loaded
    return class {
      calculateSignalQuality(s) { 
        const sharpe = (s.sharpe_ratio || 0) * 20;
        const wr = (s.win_rate || 0) * 30;
        const dd = (1 - (s.max_drawdown || 0)) * 20;
        const consensus = (s.consensus_count || 0) >= 3 ? 15 : 0;
        let score = sharpe + wr + dd + consensus;
        if ((s.total_trades || 0) < 20) score *= 0.5;
        return Math.min(100, Math.max(0, Math.round(score)));
      }
    };
  }

  /**
   * Initialize the engine and load manifest
   */
  async initialize() {
    try {
      const response = await fetch(this.manifestUrl, { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      this.manifest = await response.json();
      this.lastUpdate = new Date();
      console.log('[ConsensusEngine] Initialized with', this.manifest.systems?.length, 'systems');
      return true;
    } catch (error) {
      console.error('[ConsensusEngine] Failed to load manifest:', error);
      // Use default manifest as fallback
      this.manifest = this.getDefaultManifest();
      return false;
    }
  }

  /**
   * Get default manifest for fallback
   */
  getDefaultManifest() {
    return {
      systems: [
        { id: 'mercury2', name: 'ML: Mercury 2', data_endpoints: { active: 'https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/mercury2/data/active_picks.json', closed: 'https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/mercury2/data/closed_picks.json' } },
        { id: 'claws_of_doom', name: 'ML: Claws of Doom', data_endpoints: { active: 'https://raw.githubusercontent.com/eltonaguiar/CLAWSOFDOOM/main/docs/active_picks.json', closed: 'https://raw.githubusercontent.com/eltonaguiar/CLAWSOFDOOM/main/docs/closed_picks.json' } },
        { id: 'alpha_engine', name: 'ML: Alpha Engine', data_endpoints: { active: 'https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/alpha_engine/data/active_picks.json', closed: 'https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/alpha_engine/data/closed_picks.json' } },
        { id: 'kimi', name: 'KIMI Rise of the Claw', data_endpoints: { active: 'https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/KIMI_RISEOFTHECLAW/data/active_picks.json', closed: 'https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/KIMI_RISEOFTHECLAW/data/closed_picks.json' } },
        { id: 'crypto_ml_edge', name: 'ML: Crypto ML Edge', data_endpoints: { active: 'https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/crypto_ml_edge/data/active_picks.json' } },
        { id: 'dna_genome', name: 'DNA Genome Engine', data_endpoints: { active: 'https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/genome/active_picks.json' } }
      ],
      consensus_config: {
        super_signal_threshold: 0.60,
        system_agreement_threshold: 2,
        super_tier_threshold: 0.70,
        super_tier_systems: 3
      }
    };
  }

  /**
   * Fetch data from all active systems
   */
  async fetchAllSystems() {
    if (!this.manifest) await this.initialize();

    const systems = this.manifest.systems?.filter(s => s.status !== 'dormant') || [];

    // Fetch active and closed picks in parallel for all systems
    const activePromises = systems.map(sys => this.fetchSystemData(sys));
    const closedPromises = systems.map(sys => this.fetchSystemClosedData(sys));

    const [activeResults, closedResults] = await Promise.all([
      Promise.allSettled(activePromises),
      Promise.allSettled(closedPromises)
    ]);

    this.systemData.clear();
    this.systemClosedData.clear();

    activeResults.forEach((result, index) => {
      const sys = systems[index];
      if (result.status === 'fulfilled' && result.value) {
        this.systemData.set(sys.id, {
          system: sys,
          data: result.value,
          timestamp: new Date()
        });
      } else {
        console.warn(`[ConsensusEngine] Failed to fetch active ${sys.id}:`, result.reason);
      }
    });

    closedResults.forEach((result, index) => {
      const sys = systems[index];
      if (result.status === 'fulfilled' && result.value && result.value.length > 0) {
        this.systemClosedData.set(sys.id, result.value);
        console.log(`[ConsensusEngine] Loaded ${result.value.length} closed picks for ${sys.id}`);
      }
    });

    this.lastUpdate = new Date();
    this.calculateConsensus();
    this.notifyListeners();

    return this.systemData;
  }

  /**
   * Fetch active picks for a single system
   */
  async fetchSystemData(system) {
    const url = system.data_endpoints?.active;
    if (!url) return null;

    try {
      const response = await fetch(url, { cache: 'no-store' });
      if (!response.ok) return null;
      const data = await response.json();
      return this.normalizePicks(data, system, 'active');
    } catch (error) {
      throw error;
    }
  }

  /**
   * Fetch closed picks for a single system
   */
  async fetchSystemClosedData(system) {
    // Some systems embed closed picks inside the active endpoint
    const closedUrl = system.data_endpoints?.closed;
    const activeUrl = system.data_endpoints?.active;

    let closedPicks = [];

    // 1. Try dedicated closed endpoint
    if (closedUrl) {
      try {
        const response = await fetch(closedUrl, { cache: 'no-store' });
        if (response.ok) {
          const data = await response.json();
          closedPicks = this.normalizeClosedPicks(data, system);
        }
      } catch (e) {
        console.warn(`[ConsensusEngine] Failed to fetch closed for ${system.id}:`, e.message);
      }
    }

    // 2. If no dedicated closed endpoint or it returned empty, check if active endpoint
    //    contains embedded closed picks (e.g. crypto_ml_edge has closed_picks key)
    if (closedPicks.length === 0 && activeUrl) {
      try {
        const response = await fetch(activeUrl, { cache: 'no-store' });
        if (response.ok) {
          const data = await response.json();
          if (data && typeof data === 'object' && !Array.isArray(data)) {
            // Check for embedded closed picks keys
            const closedKeys = ['closed_picks', 'closedPicks', 'closed'];
            for (const key of closedKeys) {
              if (Array.isArray(data[key]) && data[key].length > 0) {
                closedPicks = this.normalizeClosedPicks(data[key], system);
                break;
              }
            }
            // Also check embedded performance data
            if (data.performance && closedPicks.length === 0) {
              // Store raw performance for systems that provide pre-calculated metrics
              closedPicks._embeddedPerformance = data.performance;
            }
          }
        }
      } catch (e) {
        // Ignore - active endpoint may have already been fetched
      }
    }

    return closedPicks;
  }

  /**
   * Normalize picks from different formats
   * @param {*} data - Raw data from endpoint
   * @param {Object} system - System config
   * @param {string} type - 'active' or 'closed'
   */
  normalizePicks(data, system, type = 'active') {
    let picks = [];

    if (Array.isArray(data)) {
      picks = data;
    } else if (data && typeof data === 'object') {
      // Try common array keys
      const keys = ['active_picks', 'activePicks', 'picks', 'signals', 'super_signals', 'active_predictions'];
      for (const key of keys) {
        if (Array.isArray(data[key])) {
          picks = data[key];
          break;
        }
      }
    }

    // For active picks, filter out closed ones (they belong in closed data)
    if (type === 'active') {
      picks = picks.filter(p => {
        const status = (p.status || '').toLowerCase();
        return !status.includes('closed') && !status.includes('exited');
      });
    }

    return picks.map(p => ({
      symbol: this.normalizeSymbol(p.symbol || p.pair || p.name || ''),
      direction: this.normalizeDirection(p.direction || p.signal_type || p.signal || ''),
      entryPrice: p.entry_price || p.entryPrice || p.price || 0,
      targetPrice: p.take_profit || p.tp_price || p.targetPrice || 0,
      stopPrice: p.stop_loss || p.sl_price || p.stopPrice || 0,
      timestamp: p.timestamp || p.entryDate || p.entry_date || p.created_at || new Date().toISOString(),
      algorithm: p.algorithm || p.algorithmName || p.strategy || system.name,
      quality: p.quality_score || p.sharpe_ratio || 0,
      systemId: system.id,
      systemName: system.name,
      raw: p
    })).filter(p => p.symbol && p.direction);
  }

  /**
   * Normalize closed picks from different formats
   * Handles various PnL field names across systems
   */
  normalizeClosedPicks(data, system) {
    let picks = [];

    if (Array.isArray(data)) {
      picks = data;
    } else if (data && typeof data === 'object') {
      const keys = ['closed_picks', 'closedPicks', 'closed', 'picks'];
      for (const key of keys) {
        if (Array.isArray(data[key])) {
          picks = data[key];
          break;
        }
      }
    }

    // Only keep picks that are actually closed (have exit info or closed status)
    return picks.filter(p => {
      const status = (p.status || '').toLowerCase();
      return p.exit_price || p.exitPrice ||
             p.realized_pnl_pct !== undefined || p.pnl_pct !== undefined ||
             p.result !== undefined ||
             status.includes('closed') || status.includes('exited') ||
             status.includes('stopped') || status.includes('tp_hit');
    }).map(p => ({
      symbol: this.normalizeSymbol(p.symbol || p.pair || p.name || ''),
      direction: this.normalizeDirection(p.direction || p.signal_type || p.signal || ''),
      entryPrice: p.entry_price || p.entryPrice || p.price || 0,
      exitPrice: p.exit_price || p.exitPrice || 0,
      // Normalize PnL: different systems use different field names
      pnlPct: p.realized_pnl_pct ?? p.pnl_pct ?? p.pnl ?? this.inferPnl(p),
      exitReason: p.exit_reason || p.exitReason || p.result || '',
      timestamp: p.timestamp || p.entryDate || p.entry_date || p.created_at || '',
      exitTime: p.exit_time || p.exitTime || p.exit_date || p.closed_at || '',
      algorithm: p.algorithm || p.algorithmName || p.strategy || system.name,
      systemId: system.id,
      systemName: system.name,
      raw: p
    }));
  }

  /**
   * Infer PnL from entry/exit prices when no explicit PnL field exists
   */
  inferPnl(pick) {
    const entry = pick.entry_price || pick.entryPrice || pick.price || 0;
    const exit = pick.exit_price || pick.exitPrice || 0;
    if (!entry || !exit) return 0;
    const dir = this.normalizeDirection(pick.direction || pick.signal_type || pick.signal || '');
    if (dir === 'LONG') return ((exit - entry) / entry) * 100;
    if (dir === 'SHORT') return ((entry - exit) / entry) * 100;
    return ((exit - entry) / entry) * 100;
  }

  /**
   * Normalize symbol format
   */
  normalizeSymbol(symbol) {
    return symbol.toUpperCase()
      .replace(/-/g, '')
      .replace(/USD$/g, 'USDT')
      .replace(/\/$/g, '');
  }

  /**
   * Normalize direction format
   */
  normalizeDirection(direction) {
    const d = direction.toString().toUpperCase();
    if (d.includes('BUY') || d.includes('LONG')) return 'LONG';
    if (d.includes('SELL') || d.includes('SHORT')) return 'SHORT';
    return d;
  }

  /**
   * Calculate consensus matrix across all systems
   */
  calculateConsensus() {
    this.consensusMatrix.clear();
    
    // Collect all symbols and their signals
    const symbolSignals = new Map(); // symbol -> [{system, direction, pick}]
    
    this.systemData.forEach((systemData, systemId) => {
      const picks = systemData.data || [];
      picks.forEach(pick => {
        if (!symbolSignals.has(pick.symbol)) {
          symbolSignals.set(pick.symbol, []);
        }
        symbolSignals.get(pick.symbol).push({
          system: systemId,
          systemName: pick.systemName,
          direction: pick.direction,
          pick: pick
        });
      });
    });
    
    // Calculate consensus for each symbol
    symbolSignals.forEach((signals, symbol) => {
      const longs = signals.filter(s => s.direction === 'LONG');
      const shorts = signals.filter(s => s.direction === 'SHORT');
      const total = signals.length;
      
      const longConsensus = longs.length / total;
      const shortConsensus = shorts.length / total;
      const dominantDirection = longs.length >= shorts.length ? 'LONG' : 'SHORT';
      const dominantSignals = dominantDirection === 'LONG' ? longs : shorts;
      const consensusRatio = Math.max(longConsensus, shortConsensus);
      
      // Calculate average quality using system-level metrics (from closed picks)
      const avgQuality = dominantSignals.reduce((sum, s) => {
        // Look up system-level quality score from closed pick metrics
        const systemId = s.system;
        const closedPicks = this.systemClosedData.get(systemId) || [];
        if (closedPicks.length > 0) {
          const pnls = closedPicks.map(p => p.pnlPct || 0);
          const wr = closedPicks.filter(p => (p.pnlPct || 0) > 0).length / closedPicks.length;
          const sharpe = this.calculateSharpe(pnls);
          return sum + this.qualityScorer.calculateSignalQuality({
            sharpe_ratio: sharpe,
            win_rate: wr,
            max_drawdown: 0.15,
            total_trades: closedPicks.length,
            consensus_count: dominantSignals.length
          });
        }
        // Fallback: use pick confidence as a rough quality proxy
        const conf = s.pick?.raw?.confidence || s.pick?.quality || 0;
        return sum + Math.min(100, Math.max(10, conf * 100));
      }, 0) / dominantSignals.length;
      
      // Determine signal tier
      const config = this.manifest?.consensus_config || {};
      let tier = 'NORMAL';
      if (consensusRatio >= (config.super_tier_threshold || 0.70) && 
          dominantSignals.length >= (config.super_tier_systems || 3)) {
        tier = 'SUPER';
      } else if (consensusRatio >= (config.super_signal_threshold || 0.60) && 
                 dominantSignals.length >= (config.system_agreement_threshold || 2)) {
        tier = 'STRONG';
      }
      
      this.consensusMatrix.set(symbol, {
        symbol,
        direction: dominantDirection,
        consensusRatio,
        agreeingSystems: dominantSignals.length,
        totalSystems: total,
        longCount: longs.length,
        shortCount: shorts.length,
        qualityScore: Math.round(avgQuality),
        tier,
        signals: dominantSignals,
        allSignals: signals,
        timestamp: new Date()
      });
    });
    
    return this.consensusMatrix;
  }

  /**
   * Get Super Signals (60%+ consensus)
   * @param {string} minTier - Minimum tier: 'STRONG' or 'SUPER'
   */
  getSuperSignals(minTier = 'STRONG') {
    const signals = [];
    const tierOrder = { 'SUPER': 2, 'STRONG': 1, 'NORMAL': 0 };
    const minTierLevel = tierOrder[minTier] || 1;
    
    this.consensusMatrix.forEach((consensus, symbol) => {
      const tierLevel = tierOrder[consensus.tier] || 0;
      if (tierLevel >= minTierLevel) {
        signals.push(consensus);
      }
    });
    
    // Sort by tier (SUPER first), then by consensus ratio
    return signals.sort((a, b) => {
      if (b.tier !== a.tier) return tierOrder[b.tier] - tierOrder[a.tier];
      return b.consensusRatio - a.consensusRatio;
    });
  }

  /**
   * Get consensus for a specific symbol
   */
  getSymbolConsensus(symbol) {
    const normalized = this.normalizeSymbol(symbol);
    return this.consensusMatrix.get(normalized) || null;
  }

  /**
   * Get full consensus matrix
   */
  getConsensusMatrix() {
    return this.consensusMatrix;
  }

  /**
   * Get system agreement matrix (which systems agree on which symbols)
   */
  getAgreementMatrix() {
    const matrix = {
      systems: [],
      symbols: [],
      agreements: {}
    };
    
    // Collect unique systems and symbols
    const systemSet = new Set();
    const symbolSet = new Set();
    
    this.consensusMatrix.forEach((consensus, symbol) => {
      symbolSet.add(symbol);
      consensus.allSignals.forEach(s => systemSet.add(s.system));
    });
    
    matrix.systems = [...systemSet];
    matrix.symbols = [...symbolSet].sort();
    
    // Build agreement grid
    matrix.symbols.forEach(symbol => {
      matrix.agreements[symbol] = {};
      const consensus = this.consensusMatrix.get(symbol);
      
      matrix.systems.forEach(systemId => {
        const signal = consensus?.allSignals.find(s => s.system === systemId);
        matrix.agreements[symbol][systemId] = signal ? signal.direction : null;
      });
    });
    
    return matrix;
  }

  /**
   * Get leaderboard of systems by performance
   * Uses closed picks (from dedicated closed endpoint) for WR/Sharpe calculation
   */
  getSystemLeaderboard() {
    const leaderboard = [];

    this.systemData.forEach((data, systemId) => {
      const activePicks = data.data || [];
      const closedPicks = this.systemClosedData.get(systemId) || [];
      const metrics = this.calculateSystemMetrics(activePicks, closedPicks);

      leaderboard.push({
        systemId,
        systemName: data.system.name,
        category: data.system.category,
        badge: data.system.badge,
        ...metrics,
        lastUpdate: data.timestamp
      });
    });

    // Sort by 30-day Sharpe ratio, then by win rate
    return leaderboard.sort((a, b) => {
      if ((b.sharpe30 || 0) !== (a.sharpe30 || 0)) return (b.sharpe30 || 0) - (a.sharpe30 || 0);
      return (b.winRate || 0) - (a.winRate || 0);
    });
  }

  /**
   * Calculate metrics for a system using both active and closed picks
   * @param {Array} activePicks - Normalized active picks
   * @param {Array} closedPicks - Normalized closed picks (from closed endpoint)
   */
  calculateSystemMetrics(activePicks, closedPicks) {
    const totalActive = activePicks.length;
    const totalClosed = closedPicks.length;

    // Calculate win/loss from closed picks using normalized pnlPct field
    const wins = closedPicks.filter(p => (p.pnlPct || 0) > 0).length;
    const losses = closedPicks.filter(p => (p.pnlPct || 0) < 0).length;
    const breakeven = totalClosed - wins - losses;
    const winRate = totalClosed > 0 ? wins / totalClosed : 0;

    // Calculate PnL stats from closed picks
    const pnls = closedPicks.map(p => p.pnlPct || 0);
    const avgPnl = pnls.length > 0 ? pnls.reduce((a, b) => a + b, 0) / pnls.length : 0;
    const totalPnl = pnls.reduce((a, b) => a + b, 0);

    // Calculate Sharpe (simplified)
    const sharpe = this.calculateSharpe(pnls);

    // Calculate max drawdown from sequential PnL
    const maxDrawdown = this.calculateMaxDrawdown(pnls);

    // Quality score uses system-level metrics (not individual pick fields)
    const qualityScore = this.qualityScorer.calculateSignalQuality({
      sharpe_ratio: sharpe,
      win_rate: winRate,
      max_drawdown: maxDrawdown,
      total_trades: totalClosed,
      consensus_count: 1
    });

    return {
      totalPicks: totalActive + totalClosed,
      activePicks: totalActive,
      closedPicks: totalClosed,
      wins,
      losses,
      breakeven,
      winRate,
      avgPnl,
      totalPnl,
      sharpe30: sharpe,
      maxDrawdown,
      qualityScore
    };
  }

  /**
   * Calculate max drawdown from a series of PnL values
   */
  calculateMaxDrawdown(pnls) {
    if (!pnls || pnls.length === 0) return 0;
    let cumulative = 0;
    let peak = 0;
    let maxDD = 0;
    for (const pnl of pnls) {
      cumulative += pnl;
      if (cumulative > peak) peak = cumulative;
      const dd = peak - cumulative;
      if (dd > maxDD) maxDD = dd;
    }
    // Normalize: convert from percentage points to ratio
    return peak > 0 ? maxDD / (peak + 100) : maxDD / 100;
  }

  /**
   * Calculate simplified Sharpe ratio
   */
  calculateSharpe(returns) {
    if (!returns || returns.length < 2) return 0;
    const mean = returns.reduce((a, b) => a + b, 0) / returns.length;
    const variance = returns.reduce((sum, r) => sum + Math.pow(r - mean, 2), 0) / returns.length;
    const stdDev = Math.sqrt(variance);
    return stdDev > 0 ? mean / stdDev : 0;
  }

  /**
   * Start auto-refresh
   */
  startAutoRefresh(intervalSeconds = 60) {
    this.stopAutoRefresh();
    this.refreshInterval = setInterval(() => {
      this.fetchAllSystems();
    }, intervalSeconds * 1000);
    console.log(`[ConsensusEngine] Auto-refresh started (${intervalSeconds}s)`);
  }

  /**
   * Stop auto-refresh
   */
  stopAutoRefresh() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
      this.refreshInterval = null;
      console.log('[ConsensusEngine] Auto-refresh stopped');
    }
  }

  /**
   * Add event listener
   */
  addListener(callback) {
    this.listeners.push(callback);
  }

  /**
   * Remove event listener
   */
  removeListener(callback) {
    this.listeners = this.listeners.filter(l => l !== callback);
  }

  /**
   * Notify all listeners of update
   */
  notifyListeners() {
    const data = {
      systemData: this.systemData,
      systemClosedData: this.systemClosedData,
      consensusMatrix: this.consensusMatrix,
      superSignals: this.getSuperSignals(),
      lastUpdate: this.lastUpdate
    };
    
    this.listeners.forEach(callback => {
      try {
        callback(data);
      } catch (error) {
        console.error('[ConsensusEngine] Listener error:', error);
      }
    });
  }

  /**
   * Render Super Signal banner HTML
   */
  renderSuperSignalBanner(signals) {
    if (!signals || signals.length === 0) {
      return '';
    }
    
    const hasSuper = signals.some(s => s.tier === 'SUPER');
    const borderColor = hasSuper ? '#8b5cf6' : '#3b82f6';
    const bgColor = hasSuper ? '#8b5cf611' : '#3b82f611';
    
    let html = `
      <div class="super-signal-banner" style="
        background: ${bgColor};
        border: 1px solid ${borderColor}44;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 20px;
      ">
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
          <span style="font-size: 1.3rem;">⚡</span>
          <span style="font-size: 1rem; font-weight: 700; color: ${hasSuper ? '#8b5cf6' : '#3b82f6'};">
            ${hasSuper ? 'SUPER SIGNALS' : 'STRONG SIGNALS'} — Cross-System Consensus
          </span>
          <span style="font-size: 0.7rem; color: #888; margin-left: auto;">
            ${signals.length} signal${signals.length > 1 ? 's' : ''} detected
          </span>
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 10px;">
    `;
    
    signals.slice(0, 6).forEach(signal => {
      const dirColor = signal.direction === 'LONG' ? '#22c55e' : '#ef4444';
      const tierColor = signal.tier === 'SUPER' ? '#8b5cf6' : '#3b82f6';
      const qualityGrade = signal.qualityScore >= 70 ? 'A' : signal.qualityScore >= 50 ? 'B' : 'C';
      
      html += `
        <div style="
          background: #12121e;
          border: 1px solid ${dirColor}44;
          border-radius: 8px;
          padding: 12px;
          display: flex;
          justify-content: space-between;
          align-items: center;
        ">
          <div>
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
              <span style="font-weight: 700; font-size: 1rem; color: #fff;">${signal.symbol}</span>
              <span style="
                font-size: 0.65rem;
                padding: 2px 8px;
                border-radius: 4px;
                background: ${dirColor}22;
                color: ${dirColor};
                font-weight: 600;
              ">${signal.direction}</span>
              <span style="
                font-size: 0.6rem;
                padding: 1px 6px;
                border-radius: 4px;
                background: ${tierColor}22;
                color: ${tierColor};
                font-weight: 600;
              ">${signal.tier}</span>
            </div>
            <div style="font-size: 0.7rem; color: #888;">
              ${signal.agreeingSystems}/${signal.totalSystems} systems agree • 
              ${(signal.consensusRatio * 100).toFixed(0)}% consensus
            </div>
          </div>
          <div style="text-align: right;">
            <div style="font-size: 0.75rem; color: ${signal.qualityScore >= 70 ? '#22c55e' : '#888'}; font-weight: 600;">
              Q: ${signal.qualityScore}
            </div>
            <div style="font-size: 0.6rem; color: #666;">${qualityGrade} grade</div>
          </div>
        </div>
      `;
    });
    
    html += '</div></div>';
    return html;
  }

  /**
   * Render consensus matrix table HTML
   */
  renderConsensusMatrixTable() {
    const matrix = this.getAgreementMatrix();
    
    if (matrix.symbols.length === 0) {
      return '<div style="color: #666; padding: 20px; text-align: center;">No consensus data available</div>';
    }
    
    let html = `
      <div style="overflow-x: auto; margin-top: 20px;">
        <div style="font-size: 0.9rem; font-weight: 700; margin-bottom: 12px; color: #a855f7;">
          Cross-System Agreement Matrix
        </div>
        <div style="font-size: 0.7rem; color: #888; margin-bottom: 12px;">
          Shows which systems agree on which symbols. Green = LONG consensus, Red = SHORT consensus.
        </div>
        <table style="width: 100%; border-collapse: collapse; font-family: 'SF Mono', monospace; font-size: 11px;">
          <thead>
            <tr>
              <th style="padding: 8px; text-align: left; color: #888; border-bottom: 1px solid #1e1e3a;">System</th>
    `;
    
    // Symbol columns
    matrix.symbols.forEach(symbol => {
      html += `<th style="padding: 6px; text-align: center; color: #888; border-bottom: 1px solid #1e1e3a; min-width: 50px;">${symbol.replace('USDT', '')}</th>`;
    });
    
    html += '</tr></thead><tbody>';
    
    // System rows
    matrix.systems.forEach(systemId => {
      const system = this.manifest?.systems?.find(s => s.id === systemId);
      const name = system ? system.name.replace('ML: ', '').substring(0, 12) : systemId;
      
      html += `<tr><td style="padding: 6px 8px; color: #ccc; border-bottom: 1px solid #0e0e1a; white-space: nowrap;">${name}</td>`;
      
      matrix.symbols.forEach(symbol => {
        const direction = matrix.agreements[symbol]?.[systemId];
        let cell = '<span style="color: #333">-</span>';
        if (direction === 'LONG') cell = '<span style="color: #22c55e; font-weight: 700;">▲</span>';
        else if (direction === 'SHORT') cell = '<span style="color: #ef4444; font-weight: 700;">▼</span>';
        
        html += `<td style="padding: 4px; text-align: center; border-bottom: 1px solid #0e0e1a;">${cell}</td>`;
      });
      
      html += '</tr>';
    });
    
    // Agreement count row
    html += `<tr style="border-top: 2px solid #1e1e3a;"><td style="padding: 8px; color: #a855f7; font-weight: 700;">AGREE</td>`;
    
    matrix.symbols.forEach(symbol => {
      const consensus = this.consensusMatrix.get(symbol);
      const agree = consensus ? Math.max(consensus.longCount, consensus.shortCount) : 0;
      const color = agree >= 3 ? (consensus.direction === 'LONG' ? '#22c55e' : '#ef4444') : agree >= 2 ? '#eab308' : '#666';
      
      html += `<td style="padding: 6px; text-align: center; font-weight: 700; color: ${color};">${agree > 0 ? agree : '-'}</td>`;
    });
    
    html += '</tr></tbody></table></div>';
    return html;
  }
}

// Create global instance
if (typeof window !== 'undefined') {
  window.consensusEngine = new ConsensusEngine();
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ConsensusEngine;
}
