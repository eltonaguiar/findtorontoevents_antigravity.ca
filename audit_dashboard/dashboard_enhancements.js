// ============================================================
// DASHBOARD ENHANCEMENTS — Persistent features that survive merges
// Loaded by index.html & template.html via <script src="dashboard_enhancements.js">
//
// Because the workflow regenerates index.html from template.html
// (replacing the DATA placeholder), features added directly to
// either file get wiped. This external JS file is NEVER touched
// by the generator, so everything here persists across deploys.
// ============================================================

(function () {
  'use strict';

  // ── Helpers ──────────────────────────────────────────────────
  const el = id => document.getElementById(id);
  const fmt = (n, d) => Number(n).toFixed(d ?? 1);

  /** Escape user/API data before inserting into HTML to prevent XSS. */
  function htmlEscape(str) {
    return String(str == null ? '' : str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function isWin(p) {
    const rl = p._resolved_live || '';
    const st = p.status || '';
    const oc = p.outcome || '';
    return rl === 'TP_HIT' || st === 'TP_HIT' || oc === 'TP_HIT';
  }

  function isLoss(p) {
    const rl = p._resolved_live || '';
    const st = p.status || '';
    const oc = p.outcome || '';
    return rl === 'SL_HIT' || st === 'SL_HIT' || oc === 'SL_HIT';
  }

  function isClosed(p) {
    return isWin(p) || isLoss(p);
  }

  function pickTime(p) {
    const raw = p.closed_at || p.close_time || p.exit_time || p.timestamp || '';
    if (!raw) return 0;
    const d = new Date(raw);
    return isNaN(d.getTime()) ? 0 : d.getTime();
  }

  // ── CSS injection ──────────────────────────────────────────
  function injectStyles() {
    if (document.getElementById('enh-styles')) return;
    const style = document.createElement('style');
    style.id = 'enh-styles';
    style.textContent = `
      .enh-section { margin-bottom: 20px; background: var(--card, #141428); border: 1px solid var(--border, #2a2a4a); border-radius: 10px; padding: 18px; }
      .enh-section h3 { margin: 0 0 14px 0; font-size: 15px; color: var(--text, #e0e0f0); display: flex; align-items: center; gap: 8px; }
      .enh-badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; }
      .enh-badge-hot { background: rgba(34,197,94,0.15); color: #22c55e; }
      .enh-badge-cold { background: rgba(239,68,68,0.15); color: #ef4444; }
      .enh-badge-neutral { background: rgba(156,163,175,0.1); color: #9ca3af; }
      .enh-badge-high { background: rgba(168,85,247,0.2); color: #a855f7; }
      .enh-badge-med { background: rgba(59,130,246,0.15); color: #3b82f6; }
      .enh-badge-low { background: rgba(156,163,175,0.1); color: #9ca3af; }
      .enh-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 10px; }
      .enh-card { background: var(--bg, #0a0a14); border: 1px solid var(--border, #2a2a4a); border-radius: 8px; padding: 12px; }
      .enh-card-title { font-size: 12px; color: var(--text-dim, #888); margin-bottom: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .enh-card-value { font-size: 22px; font-weight: 700; }
      .enh-card-sub { font-size: 11px; color: var(--text-dim, #888); margin-top: 4px; }
      .enh-tabs { display: flex; gap: 4px; margin-bottom: 12px; flex-wrap: wrap; }
      .enh-tab { padding: 5px 14px; border-radius: 6px; font-size: 12px; cursor: pointer; border: 1px solid var(--border, #2a2a4a); background: var(--bg, #0a0a14); color: var(--text-dim, #888); transition: all 0.15s; }
      .enh-tab.active { background: var(--accent, #6366f1); color: #fff; border-color: var(--accent, #6366f1); }
      .enh-consensus-table { width: 100%; border-collapse: collapse; font-size: 12px; }
      .enh-consensus-table th { text-align: left; padding: 8px 10px; color: var(--text-dim, #888); border-bottom: 1px solid var(--border, #2a2a4a); font-weight: 600; }
      .enh-consensus-table td { padding: 7px 10px; border-bottom: 1px solid rgba(42,42,74,0.4); }
      .enh-trend-bar { display: flex; align-items: center; gap: 6px; }
      .enh-trend-fill { height: 6px; border-radius: 3px; min-width: 2px; transition: width 0.3s; }
      @media (max-width: 640px) {
        .enh-grid { grid-template-columns: 1fr 1fr; }
      }
    `;
    document.head.appendChild(style);
  }

  // ── Feature 1: System Health Trends (4h/8h/24h vs all-time) ──
  function renderSystemTrends(D) {
    const closed = (D.picks?.recent_closed || []).filter(p => isClosed(p));
    if (closed.length < 10) return;

    const now = Date.now();
    const windows = [
      { key: '4h', ms: 4 * 3600000, label: '4H' },
      { key: '8h', ms: 8 * 3600000, label: '8H' },
      { key: '24h', ms: 24 * 3600000, label: '24H' },
    ];

    // Collect all systems
    const allSystems = [...new Set(closed.map(p => p.source_system).filter(Boolean))];

    // Compute WR per system per window
    const systemStats = {};
    for (const sys of allSystems) {
      const sysPicks = closed.filter(p => p.source_system === sys);
      const allWins = sysPicks.filter(isWin).length;
      const allTotal = sysPicks.length;
      const allWR = allTotal > 0 ? (allWins / allTotal * 100) : 0;

      const windowStats = {};
      for (const w of windows) {
        const cutoff = now - w.ms;
        const wPicks = sysPicks.filter(p => pickTime(p) >= cutoff);
        const wWins = wPicks.filter(isWin).length;
        const wTotal = wPicks.length;
        windowStats[w.key] = { wins: wWins, total: wTotal, wr: wTotal >= 2 ? (wWins / wTotal * 100) : null };
      }

      systemStats[sys] = { allWR, allTotal, allWins, windows: windowStats };
    }

    // Find hot/cold streaks (4h WR is 20+ points above/below all-time)
    const streaks = [];
    for (const [sys, stats] of Object.entries(systemStats)) {
      const w4h = stats.windows['4h'];
      if (w4h.wr === null) continue; // not enough recent data
      const diff = w4h.wr - stats.allWR;
      if (diff >= 20) {
        streaks.push({ system: sys, type: 'HOT', wr4h: w4h.wr, wrAll: stats.allWR, diff, trades4h: w4h.total });
      } else if (diff <= -20) {
        streaks.push({ system: sys, type: 'COLD', wr4h: w4h.wr, wrAll: stats.allWR, diff, trades4h: w4h.total });
      }
    }

    // Build HTML
    let html = '<div class="enh-section" id="enh-system-trends">';
    html += '<h3>System Health Trends <span class="enh-badge enh-badge-neutral">PERSISTENT</span></h3>';

    // Streak alerts
    if (streaks.length > 0) {
      html += '<div style="margin-bottom:14px;">';
      for (const s of streaks.sort((a, b) => Math.abs(b.diff) - Math.abs(a.diff))) {
        const cls = s.type === 'HOT' ? 'enh-badge-hot' : 'enh-badge-cold';
        const arrow = s.type === 'HOT' ? '\u2191' : '\u2193';
        const sysName = s.system.replace(/_/g, ' ');
        html += `<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">`;
        html += `<span class="enh-badge ${cls}">${s.type} STREAK</span>`;
        html += `<span style="color:var(--text);font-size:13px;font-weight:600;">${sysName}</span>`;
        html += `<span style="color:var(--text-dim);font-size:12px;">${arrow} 4H: ${fmt(s.wr4h)}% (${s.trades4h} trades) vs All-time: ${fmt(s.wrAll)}%</span>`;
        html += `</div>`;
      }
      html += '</div>';
    }

    // System cards grid — show top systems sorted by all-time trades
    const topSystems = Object.entries(systemStats)
      .filter(([, s]) => s.allTotal >= 5)
      .sort((a, b) => b[1].allTotal - a[1].allTotal)
      .slice(0, 12);

    if (topSystems.length > 0) {
      html += '<div class="enh-grid">';
      for (const [sys, stats] of topSystems) {
        const wrColor = stats.allWR >= 55 ? '#22c55e' : stats.allWR >= 45 ? '#eab308' : '#ef4444';
        const sysName = sys.replace(/_/g, ' ');
        html += `<div class="enh-card">`;
        html += `<div class="enh-card-title">${sysName}</div>`;
        html += `<div class="enh-card-value" style="color:${wrColor}">${fmt(stats.allWR)}%</div>`;
        html += `<div class="enh-card-sub">${stats.allWins}W / ${stats.allTotal - stats.allWins}L (${stats.allTotal} trades)</div>`;
        // Mini window bars
        html += `<div style="display:flex;gap:8px;margin-top:8px;">`;
        for (const w of windows) {
          const ws = stats.windows[w.key];
          if (ws.wr === null) {
            html += `<span style="font-size:10px;color:var(--text-dim);">${w.label}: --</span>`;
          } else {
            const c = ws.wr >= stats.allWR + 10 ? '#22c55e' : ws.wr <= stats.allWR - 10 ? '#ef4444' : '#9ca3af';
            html += `<span style="font-size:10px;color:${c};font-weight:600;">${w.label}: ${fmt(ws.wr, 0)}%</span>`;
          }
        }
        html += `</div></div>`;
      }
      html += '</div>';
    }

    html += '</div>';

    // Inject before tab-overview
    const tabOverview = el('tab-overview');
    if (tabOverview) {
      tabOverview.insertAdjacentHTML('beforebegin', html);
    }
  }

  // ── Feature 2: Strategy Consensus Matrix (True Signal) ──
  function renderStrategyConsensus(D) {
    const active = (D.picks?.active || []);
    const closed = (D.picks?.recent_closed || []).filter(p => isClosed(p));
    if (active.length === 0) return;

    // Build per-strategy WR from closed picks
    const strategyWR = {}; // strategyName -> { wins, total, symbols: { sym -> { wins, total } } }
    for (const p of closed) {
      const strategies = p.source_strategies || {};
      const strats = Object.keys(strategies).length > 0 ? Object.keys(strategies) : [p.strategy || p.strategy_id || 'unknown'];
      const won = isWin(p);
      for (const strat of strats) {
        if (!strategyWR[strat]) strategyWR[strat] = { wins: 0, total: 0, symbols: {} };
        strategyWR[strat].total++;
        if (won) strategyWR[strat].wins++;
        const sym = (p.symbol || '').replace(/-/g, '');
        if (!strategyWR[strat].symbols[sym]) strategyWR[strat].symbols[sym] = { wins: 0, total: 0 };
        strategyWR[strat].symbols[sym].total++;
        if (won) strategyWR[strat].symbols[sym].wins++;
      }
    }

    // For each active pick, find which winning strategies agree
    const consensusData = [];
    for (const p of active) {
      const sym = (p.symbol || '').replace(/-/g, '');
      const dir = p.direction || 'LONG';
      const strategies = p.source_strategies || {};
      const strats = Object.keys(strategies).length > 0 ? Object.keys(strategies) : [p.strategy || p.strategy_id || 'unknown'];

      // Count strategies with WR >= 50%
      let winningStrats = [];
      let totalStrats = strats.length;
      for (const strat of strats) {
        const sr = strategyWR[strat];
        if (sr && sr.total >= 3) {
          const wr = sr.wins / sr.total * 100;
          if (wr >= 50) {
            winningStrats.push({ name: strat, wr, trades: sr.total });
          }
        }
      }

      // Also check symbol-specific WR
      let symbolWinStrats = [];
      for (const strat of strats) {
        const sr = strategyWR[strat];
        if (sr?.symbols?.[sym] && sr.symbols[sym].total >= 2) {
          const symWR = sr.symbols[sym].wins / sr.symbols[sym].total * 100;
          if (symWR >= 50) {
            symbolWinStrats.push({ name: strat, wr: symWR, trades: sr.symbols[sym].total });
          }
        }
      }

      const conviction = winningStrats.length >= 3 ? 'HIGH' : winningStrats.length >= 2 ? 'MEDIUM' : winningStrats.length === 1 ? 'LOW' : 'NONE';

      if (winningStrats.length > 0 || symbolWinStrats.length > 0) {
        consensusData.push({
          symbol: sym,
          direction: dir,
          score: p.score || 0,
          conviction,
          winningStrats,
          symbolWinStrats,
          totalStrats,
          sourceSystem: p.source_system || '',
        });
      }
    }

    if (consensusData.length === 0) return;

    // Sort: HIGH first, then MEDIUM, then LOW
    const convOrder = { HIGH: 0, MEDIUM: 1, LOW: 2, NONE: 3 };
    consensusData.sort((a, b) => (convOrder[a.conviction] - convOrder[b.conviction]) || (b.score - a.score));

    let html = '<div class="enh-section" id="enh-strategy-consensus">';
    html += '<h3>Strategy Consensus Matrix <span class="enh-badge enh-badge-neutral">TRUE SIGNAL</span></h3>';
    html += '<p style="font-size:12px;color:var(--text-dim);margin-bottom:12px;">Per-strategy conviction: how many historically <em>winning</em> strategies (WR &ge; 50%, 3+ trades) agree on each active pick. Higher conviction = more proven strategies backing the signal.</p>';

    html += '<table class="enh-consensus-table"><thead><tr>';
    html += '<th>Symbol</th><th>Dir</th><th>System</th><th>Conviction</th><th>Winning Strats</th><th>Score</th>';
    html += '</tr></thead><tbody>';

    for (const c of consensusData) {
      const badgeCls = c.conviction === 'HIGH' ? 'enh-badge-high' : c.conviction === 'MEDIUM' ? 'enh-badge-med' : 'enh-badge-low';
      const dirColor = (c.direction === 'LONG' || c.direction === 'BUY') ? '#22c55e' : '#ef4444';
      const sysName = htmlEscape(c.sourceSystem).replace(/_/g, ' ');
      const stratNames = c.winningStrats.map(s => `${htmlEscape(s.name).replace(/_/g, ' ')} (${fmt(s.wr, 0)}%)`).join(', ');

      html += `<tr>`;
      html += `<td style="font-weight:600;color:var(--text);">${htmlEscape(c.symbol)}</td>`;
      html += `<td style="color:${dirColor};font-weight:600;">${htmlEscape(c.direction)}</td>`;
      html += `<td style="color:var(--text-dim);">${sysName}</td>`;
      html += `<td><span class="enh-badge ${badgeCls}">${htmlEscape(c.conviction)}</span> (${c.winningStrats.length}/${c.totalStrats})</td>`;
      html += `<td style="font-size:11px;color:var(--text-dim);">${stratNames || '--'}</td>`;
      html += `<td style="text-align:center;">${fmt(c.score, 2)}</td>`;
      html += `</tr>`;
    }

    html += '</tbody></table></div>';

    // Inject after the agreement matrix
    const agreementMatrix = el('agreement-matrix');
    if (agreementMatrix) {
      agreementMatrix.insertAdjacentHTML('afterend', html);
    } else {
      const tabOverview = el('tab-overview');
      if (tabOverview) tabOverview.insertAdjacentHTML('afterend', html);
    }
  }

  // ── Feature 3: Time-Window Leaderboard ──
  function renderTimeWindowBreakdown(D) {
    const closed = (D.picks?.recent_closed || []).filter(p => isClosed(p));
    if (closed.length < 10) return;

    const windows = [
      { key: '4h', ms: 4 * 3600000, label: 'Last 4H' },
      { key: '24h', ms: 24 * 3600000, label: 'Last 24H' },
      { key: '7d', ms: 7 * 24 * 3600000, label: 'Last 7D' },
      { key: 'all', ms: Infinity, label: 'All Time' },
    ];

    const now = Date.now();
    const allSystems = [...new Set(closed.map(p => p.source_system).filter(Boolean))];

    // Compute per-system stats for each window
    const windowData = {};
    for (const w of windows) {
      const cutoff = w.ms === Infinity ? 0 : now - w.ms;
      const wPicks = closed.filter(p => pickTime(p) >= cutoff);

      const systems = {};
      for (const sys of allSystems) {
        const sp = wPicks.filter(p => p.source_system === sys);
        if (sp.length === 0) continue;
        const wins = sp.filter(isWin).length;
        const losses = sp.filter(isLoss).length;
        const total = sp.length;
        const wr = total > 0 ? (wins / total * 100) : 0;

        // Calculate PnL
        let pnl = 0;
        for (const p of sp) {
          if (p.pnl_pct != null) pnl += parseFloat(p.pnl_pct) || 0;
        }

        systems[sys] = { wins, losses, total, wr, pnl };
      }

      windowData[w.key] = systems;
    }

    let html = '<div class="enh-section" id="enh-time-window-leaderboard">';
    html += '<h3>Time-Window System Leaderboard <span class="enh-badge enh-badge-neutral">TREND</span></h3>';
    html += '<p style="font-size:12px;color:var(--text-dim);margin-bottom:12px;">Compare system performance across time windows. Spot which systems are improving or degrading recently.</p>';

    // Tab buttons
    html += '<div class="enh-tabs" id="enh-tw-tabs">';
    for (let i = 0; i < windows.length; i++) {
      const w = windows[i];
      html += `<div class="enh-tab${i === 0 ? ' active' : ''}" data-enh-tw="${w.key}" onclick="window._enhSwitchTW('${w.key}')">${w.label}</div>`;
    }
    html += '</div>';

    // Tab content panels
    for (let i = 0; i < windows.length; i++) {
      const w = windows[i];
      const systems = windowData[w.key];
      const sorted = Object.entries(systems)
        .filter(([, s]) => s.total >= 2)
        .sort((a, b) => b[1].wr - a[1].wr || b[1].total - a[1].total);

      html += `<div id="enh-tw-panel-${w.key}" style="display:${i === 0 ? 'block' : 'none'};">`;

      if (sorted.length === 0) {
        html += '<div style="color:var(--text-dim);padding:12px;font-size:13px;">No systems with 2+ trades in this window.</div>';
      } else {
        html += '<table class="enh-consensus-table"><thead><tr>';
        html += '<th>#</th><th>System</th><th>WR</th><th>W/L</th><th>Trades</th><th>PnL%</th><th>Trend</th>';
        html += '</tr></thead><tbody>';

        for (let j = 0; j < sorted.length; j++) {
          const [sys, s] = sorted[j];
          const sysName = sys.replace(/_/g, ' ');
          const wrColor = s.wr >= 55 ? '#22c55e' : s.wr >= 45 ? '#eab308' : '#ef4444';
          const pnlColor = s.pnl >= 0 ? '#22c55e' : '#ef4444';

          // Trend: compare this window vs all-time
          const allStats = windowData['all'][sys];
          let trendHtml = '';
          if (allStats && w.key !== 'all' && s.total >= 2) {
            const wrDiff = s.wr - allStats.wr;
            if (wrDiff >= 10) trendHtml = '<span style="color:#22c55e;font-weight:700;">\u2191 Improving</span>';
            else if (wrDiff <= -10) trendHtml = '<span style="color:#ef4444;font-weight:700;">\u2193 Degrading</span>';
            else trendHtml = '<span style="color:#9ca3af;">Stable</span>';
          } else if (w.key === 'all') {
            trendHtml = '<span style="color:var(--text-dim);">Baseline</span>';
          } else {
            trendHtml = '<span style="color:var(--text-dim);">--</span>';
          }

          html += `<tr>`;
          html += `<td style="color:var(--text-dim);">${j + 1}</td>`;
          html += `<td style="font-weight:600;color:var(--text);">${sysName}</td>`;
          html += `<td style="color:${wrColor};font-weight:700;">${fmt(s.wr)}%</td>`;
          html += `<td>${s.wins}/${s.losses}</td>`;
          html += `<td>${s.total}</td>`;
          html += `<td style="color:${pnlColor};">${s.pnl >= 0 ? '+' : ''}${fmt(s.pnl)}%</td>`;
          html += `<td>${trendHtml}</td>`;
          html += `</tr>`;
        }
        html += '</tbody></table>';
      }
      html += '</div>';
    }

    html += '</div>';

    // Inject after the system trends section or after tab-overview
    const trendsSection = el('enh-system-trends');
    if (trendsSection) {
      trendsSection.insertAdjacentHTML('afterend', html);
    } else {
      const tabOverview = el('tab-overview');
      if (tabOverview) tabOverview.insertAdjacentHTML('afterend', html);
    }
  }

  // Tab switching for time-window leaderboard
  window._enhSwitchTW = function (key) {
    document.querySelectorAll('[data-enh-tw]').forEach(t => t.classList.toggle('active', t.dataset.enhTw === key));
    document.querySelectorAll('[id^="enh-tw-panel-"]').forEach(p => p.style.display = p.id === 'enh-tw-panel-' + key ? 'block' : 'none');
  };

  // ── ml_gatekeeper A/B Sleeve Panel (2026-05-12 Phase C) ──────
  // Reads BOTH ml_gatekeeper/data/active_picks.json (OLD sleeve, with
  // leakage features) and ml_gatekeeper/data/active_picks_ab_new.json
  // (NEW sleeve, leakage-purged). Per design at
  // reports/ml_gatekeeper_ab_sleeve_design_2026-05-12.md.
  //
  // Note paths are project-relative to /audit. If 50/50 split holds and
  // either file is empty for >7 cron cycles, the Phase E auto-rollback
  // path expects an alert; this panel surfaces the warning.
  async function renderMLGatekeeperAB() {
    async function fetchJson(path) {
      try {
        const r = await fetch(path, {cache: 'no-cache'});
        if (!r.ok) return null;
        return await r.json();
      } catch (e) { return null; }
    }
    const oldData = await fetchJson('../ml_gatekeeper/data/active_picks.json');
    // 2026-05-19: active_picks_ab_new.json is never produced by any repo
    // pipeline -> permanent 404. Dropped. The NEW sleeve degrades to "no
    // data" until a real producer ships that file.
    const newData = null;
    if (!Array.isArray(oldData) && !Array.isArray(newData)) {
      return; // No A/B data shipped yet
    }
    const oldCount = Array.isArray(oldData) ? oldData.length : 0;
    const newCount = Array.isArray(newData) ? newData.length : 0;
    function avgScore(arr) {
      if (!Array.isArray(arr) || !arr.length) return null;
      const sum = arr.reduce((s, p) => s + (Number(p.gatekeeper_score) || 0), 0);
      return sum / arr.length;
    }
    function gradeBreakdown(arr) {
      if (!Array.isArray(arr)) return {};
      const b = {A: 0, B: 0, C: 0, D: 0};
      arr.forEach(p => {
        const g = p.gatekeeper_grade || '';
        if (b.hasOwnProperty(g)) b[g]++;
      });
      return b;
    }
    function classDist(arr) {
      if (!Array.isArray(arr)) return {};
      const d = {};
      arr.forEach(p => {
        const c = (p.asset_class || 'UNKNOWN').toUpperCase();
        d[c] = (d[c] || 0) + 1;
      });
      return d;
    }
    const oldGrades = gradeBreakdown(oldData);
    const newGrades = gradeBreakdown(newData);
    const oldAvg = avgScore(oldData);
    const newAvg = avgScore(newData);
    const oldClassDist = classDist(oldData);
    const newClassDist = classDist(newData);

    // Rollback armed if NEW emits 0 picks for one cycle. Real auto-rollback
    // requires 7 consecutive cycles tracked server-side; this panel just
    // surfaces the current cycle warning.
    const rollbackWarning = newCount === 0 && Array.isArray(newData);

    let html = '<div class="enh-section" id="enh-ml-gatekeeper-ab">';
    html += '<h3>&#x1F9EA; ML Gatekeeper A/B Sleeve <span class="enh-badge enh-badge-neutral">LEAKAGE PURGE TEST</span></h3>';
    html += '<div style="font-size:12px;color:#aaa;margin-bottom:10px;line-height:1.6;">' +
            '<strong style="color:#cbd5e1;">In plain English:</strong> the ML &ldquo;gatekeeper&rdquo; is the model that decides ' +
            'which picks are strong enough to surface. We suspect the OLD version was &ldquo;peeking at the answer&rdquo; &mdash; it ' +
            'learned partly from a pick&rsquo;s own forward win-rate, a clue that already hints at the outcome (data leakage). ' +
            'The NEW version has those leaky clues stripped out. New picks are split 50/50 between the two versions, and after ' +
            '30 days we keep whichever one actually surfaces more real winners. ' +
            '<em style="color:#fbbf24;">Right now the NEW side shows no data &mdash; its pick-producer was never built &mdash; so ' +
            'there is nothing to compare yet; the panel will stay half-empty until that ships.</em>' +
            '<details style="margin-top:6px"><summary style="cursor:pointer;color:#06b6d4;">Technical detail</summary>' +
            '<span style="color:#888;">OLD: trained WITH <code>forward_wr</code>+<code>strat_fwd_wr</code>+<code>eb_forward_wr</code>+<code>age_hours</code> features. ' +
            'NEW: leakage-purged via <code>ML_GATE_DROP_LEAKAGE=1</code>. Hash-bucket split (md5 mod 2). ' +
            'Decision rule at 30d: one-sided z-test, p&lt;0.10, WR delta &ge;2pp. ' +
            'Plan: <a href="/reports/ml_gatekeeper_ab_sleeve_design_2026-05-12.md" style="color:#06b6d4">design doc</a>.</span></details>' +
            '</div>';
    html += '<div class="enh-grid">';
    html += '<div class="enh-card">' +
            '<div class="enh-card-title">OLD sleeve (current production)</div>' +
            '<div class="enh-card-value" style="color:#a78bfa">' + oldCount + '</div>' +
            '<div class="enh-card-sub">avg score ' + (oldAvg != null ? oldAvg.toFixed(1) : '—') +
            ' &middot; A/B/C/D: ' + oldGrades.A + '/' + oldGrades.B + '/' + oldGrades.C + '/' + oldGrades.D +
            '</div></div>';
    const newHasData = Array.isArray(newData);
    html += '<div class="enh-card">' +
            '<div class="enh-card-title">NEW sleeve (leakage-purged)</div>' +
            '<div class="enh-card-value" style="color:' + (rollbackWarning ? '#ef4444' : '#22c55e') + '">' +
            (newHasData ? newCount : '—') + '</div>' +
            '<div class="enh-card-sub">' +
            (newHasData
              ? ('avg score ' + (newAvg != null ? newAvg.toFixed(1) : '—') +
                 ' &middot; A/B/C/D: ' + newGrades.A + '/' + newGrades.B + '/' + newGrades.C + '/' + newGrades.D +
                 (rollbackWarning ? ' &middot; <strong style="color:#ef4444">ROLLBACK WARNING — 0 emissions this cycle</strong>' : ''))
              : 'A/B NEW sleeve: no data') +
            '</div></div>';
    // Score delta diagnostic
    if (oldAvg != null && newAvg != null) {
      const delta = newAvg - oldAvg;
      html += '<div class="enh-card">' +
              '<div class="enh-card-title">NEW vs OLD score delta</div>' +
              '<div class="enh-card-value" style="color:' + (delta > 0 ? '#22c55e' : '#ef4444') + '">' +
              (delta > 0 ? '+' : '') + delta.toFixed(1) + '</div>' +
              '<div class="enh-card-sub">Pre-30d decision. Need realized WR delta &ge;2pp to declare NEW winner.</div></div>';
    }
    html += '</div>';
    // Class distribution side-by-side
    const allClasses = new Set([...Object.keys(oldClassDist), ...Object.keys(newClassDist)]);
    if (allClasses.size) {
      html += '<details style="margin-top:12px"><summary style="cursor:pointer;color:#06b6d4;font-size:12px">' +
              'Show per-class emission split</summary>';
      html += '<table style="width:100%;font-size:11px;margin-top:6px;border-collapse:collapse">';
      html += '<thead><tr><th style="text-align:left;padding:4px;color:#94a3b8">class</th><th style="text-align:right;padding:4px;color:#94a3b8">OLD</th><th style="text-align:right;padding:4px;color:#94a3b8">NEW</th></tr></thead><tbody>';
      Array.from(allClasses).sort().forEach(c => {
        html += '<tr style="border-top:1px solid rgba(42,42,74,0.4)"><td style="padding:3px 4px;color:#cbd5e1">' + htmlEscape(c) + '</td>' +
                '<td style="padding:3px 4px;text-align:right;font-variant-numeric:tabular-nums">' + (oldClassDist[c] || 0) + '</td>' +
                '<td style="padding:3px 4px;text-align:right;font-variant-numeric:tabular-nums">' + (newClassDist[c] || 0) + '</td></tr>';
      });
      html += '</tbody></table></details>';
    }
    html += '</div>';

    const host = el('enhancements-host') || el('tab-overview') || document.body;
    const existing = el('enh-ml-gatekeeper-ab');
    if (existing) existing.remove();
    const wrapper = document.createElement('div');
    wrapper.innerHTML = html;
    host.appendChild(wrapper.firstElementChild);
  }

  // ── DB Health Cards (async; reads audit_dashboard/data/db_health.json) ──
  // Surfaces PnL integrity %, ghost-row count, OPEN bloat warning. Generated
  // hourly by tools/db_health_check.py. Fully isolated — section is its own
  // <div id="enh-db-health">; if fetch fails, no other section is impacted.
  async function renderDbHealth() {
    let payload;
    try {
      const resp = await fetch('data/db_health.json', {cache: 'no-cache'});
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      payload = await resp.json();
    } catch (e) {
      console.warn('[Enhancements] db_health.json fetch failed:', e);
      return;
    }
    const checks = (payload && payload.checks) || {};
    // 2026-06-04: render timestamps as human-readable EST/EDT, not raw ISO
    // (was "2026-06-04T15:43:20.828520+00:00"). Reuse window._fmtEST when present.
    var _fmtEST = window._fmtEST || function (iso) {
      if (!iso) return 'unknown';
      try {
        var d = new Date(iso);
        if (isNaN(d.getTime())) return String(iso);
        var s = d.toLocaleString('en-CA', { timeZone: 'America/Toronto',
          year: 'numeric', month: '2-digit', day: '2-digit',
          hour: '2-digit', minute: '2-digit', hour12: false });
        var m = d.getUTCMonth() + 1;
        return s.replace(',', '') + ' ' + ((m > 3 && m < 11) ? 'EDT' : 'EST');
      } catch (e) { return String(iso); }
    };

    // helper: extract data + tier; degrade gracefully if check failed
    function pick(name) {
      const c = checks[name];
      if (!c || !c.ok || !c.data) return null;
      return c.data;
    }

    const tierColor = t => t === 'red' ? '#e74c3c' : t === 'yellow' ? '#f39c12' : t === 'green' ? '#27ae60' : '#888';

    // build 6 cards; missing data shows a dim placeholder
    const cards = [];

    const pnl = pick('pnl_integrity');
    if (pnl) {
      cards.push({
        title: 'PnL Integrity (sampled)',
        value: (100 - pnl.mismatch_pct).toFixed(1) + '%',
        sub: htmlEscape((pnl.gt1pct_mismatch || 0).toLocaleString()) + ' / ' +
             htmlEscape((pnl.sampled || 0).toLocaleString()) + ' mismatch >1pp',
        color: tierColor(pnl.tier),
      });
    }
    const ghosts = pick('ghost_rows');
    if (ghosts) {
      cards.push({
        title: 'Ghost Rows (constant pnl_pct)',
        value: (ghosts.total_ghost_rows || 0).toLocaleString(),
        sub: htmlEscape(String(ghosts.cohort_count || 0)) + ' cohorts (n>1000, distinct_entries<5)',
        color: tierColor(ghosts.tier),
      });
    }
    const openb = pick('open_bloat');
    if (openb) {
      const hr = openb.hours_since_last_close;
      cards.push({
        title: 'Forward Validator Freshness',
        value: hr == null ? 'NULL' : hr + 'h',
        sub: htmlEscape(openb.last_terminal_write || 'never') + ' last WON/LOST',
        color: tierColor(openb.tier),
      });
    }
    const phantom = pick('phantom_expired');
    if (phantom) {
      cards.push({
        title: 'Phantom EXPIRED rows',
        value: phantom.worst_phantom_pct.toFixed(1) + '%',
        sub: htmlEscape(String((phantom.by_class || []).length)) + ' classes, worst-case',
        color: tierColor(phantom.tier),
      });
    }
    const oc = pick('outcome_coverage');
    if (oc) {
      cards.push({
        title: 'Raw-Pick Outcome Coverage',
        value: oc.raw_resolved_pct.toFixed(2) + '%',
        sub: htmlEscape((oc.raw_picks_resolved || 0).toLocaleString()) + ' / ' +
             htmlEscape((oc.raw_picks_total || 0).toLocaleString()) + ' resolved',
        color: tierColor(oc.tier),
      });
    }
    const wp = pick('won_pnl_contradiction');
    if (wp && wp.contradiction_detected !== undefined) {
      cards.push({
        title: 'WON-vs-PnL contradiction',
        value: wp.contradiction_detected ? 'YES' : 'no',
        sub: 'avg pnl per status ' + (wp.contradiction_detected ? '— writer bug' : '— OK'),
        color: tierColor(wp.tier),
      });
    }

    if (cards.length === 0) return;

    let html = '<div class="enh-section" id="enh-db-health">';
    html += '<h3>DB Health <span style="font-size:11px;color:#888;font-weight:400;">— ' +
            htmlEscape(_fmtEST(payload.generated_at)) + '</span></h3>';
    html += '<div class="enh-grid">';
    for (const c of cards) {
      html += '<div class="enh-card">';
      html += '<div class="enh-card-title">' + htmlEscape(c.title) + '</div>';
      html += '<div class="enh-card-value" style="color:' + c.color + '">' + htmlEscape(c.value) + '</div>';
      html += '<div class="enh-card-sub">' + c.sub + '</div>';
      html += '</div>';
    }
    html += '</div>';
    // Only show alarm banner for Tier 1 RED checks (not Tier 2/3 informational)
    var isTier1Red = payload.overall && (payload.overall.any_red_t1 || payload.overall.any_red);
    if (isTier1Red) {
      // Build dynamic list of which checks are actually RED
      var _redChecks = [];
      var _checks = payload.checks || {};
      for (var _ck in _checks) {
        if (_checks[_ck] && _checks[_ck].data && _checks[_ck].data.tier === 'red') {
          _redChecks.push(_ck.replace(/_/g, ' '));
        }
      }
      var _redList = _redChecks.length > 0 ? _redChecks.join(', ') : 'unknown checks';
      var _ghostLive = (ghosts && ghosts.total_ghost_rows != null) ? Number(ghosts.total_ghost_rows).toLocaleString() : 'n/a';
      html += '<div style="margin-top:10px;padding:12px;background:#3b0d0d;border-left:4px solid #ef4444;border-radius:4px;font-size:13px;line-height:1.6;">';
      html += '<strong style="color:#fca5a5;font-size:14px;">&#x26A0; DATA INTEGRITY FAILURE &mdash; DO NOT TRADE ON THESE NUMBERS</strong><br>';
      html += '<span style="color:#fecaca;">The DB Health checks above are RED on metrics generated <code>' + htmlEscape(_fmtEST(payload.generated_at)) + '</code> (live, not stale). ' +
              'Failing checks: <strong>' + htmlEscape(_redList) + '</strong>. ' +
              'Ghost rows: ' + htmlEscape(_ghostLive) + '. ' +
              'Downstream panels (Top-N backtest, asset-class WR/PF, smart-picks scoring) read from the same DB and inherit this corruption.</span><br>';
      html += '<span style="color:#fde68a;font-size:12px;">Remediation status: <code>tools/cleanup_ghost_rows.py</code> shipped (2026-05-31: 0 ghost rows confirmed). <code>tools/db_health_check.py</code> emitting hourly; <code>forward_validator.py</code> writes canonical statuses. ' +
              'Ghost rows, status mismatch, non-canonical statuses, and _bak tables all cleared as of 2026-05-31 DB audit. ' +
              'See <a href="/updates/2026-05-31-pr1-data-integrity-repair.md" style="color:#fde68a;text-decoration:underline">PR #1 data integrity repair</a> and <a href="/updates/2026-05-31-incidents-enhancements-audit-summary.md" style="color:#fde68a;text-decoration:underline">incidents audit summary</a> for the full fix log.</span>';
      html += '</div>';
    } else if (payload.overall && payload.overall.harness_healthy === false) {
      // Soft-warning banner: harness itself is broken (one or more checks errored OR failed threshold),
      // so any_red may be falsely-green by exclusion. Distinct from the hard DATA INTEGRITY banner above.
      var _failedN = payload.overall.checks_failed != null ? payload.overall.checks_failed : '?';
      var _runN = payload.overall.checks_run != null ? payload.overall.checks_run : '?';
      html += '<div style="margin-top:10px;padding:12px;background:#3a2a0a;border-left:4px solid #f59e0b;border-radius:4px;font-size:13px;line-height:1.6;">';
      html += '<strong style="color:#fde68a;font-size:14px;">&#x26A0; DB HEALTH HARNESS DEGRADED &mdash; verdict may be incomplete</strong><br>';
      html += '<span style="color:#fef3c7;">' + htmlEscape(String(_failedN)) + ' of ' + htmlEscape(String(_runN)) + ' checks errored or failed threshold on <code>' + htmlEscape(_fmtEST(payload.generated_at)) + '</code>. ' +
              'The "any_red" gate only inspects checks that returned successfully, so a fully-broken harness can report green by exclusion. Treat the verdict above as provisional until the harness is healthy.</span>';
      html += '</div>';
    }
    html += '</div>';

    // Insert at top of #enh-host (or body if missing) so it's visible
    const host = document.getElementById('enh-host') || document.body;
    const wrapper = document.createElement('div');
    wrapper.innerHTML = html;
    const node = wrapper.firstElementChild;
    // Remove existing if re-rendering
    const existing = document.getElementById('enh-db-health');
    if (existing) existing.remove();
    host.insertBefore(node, host.firstChild);
  }

  // ── Top-N Rank Backtest card ─────────────────────────────────
  // Reads audit_dashboard/data/top_n_rank_backtest.json (hindsight replay:
  // rank each day's EQUITY closed picks by score, take top-10, measure
  // realized pnl_pct). Answers user's question: "if I bought the top-10
  // ranked scores today / yesterday / 1 month ago, would I have been
  // profitable?" Cron emits via tools/top_n_rank_backtest.py.
  let _topNRenderGen = 0;

  async function renderTopNRankBacktest() {
    const gen = ++_topNRenderGen;
    let payload;
    try {
      const resp = await fetch('data/top_n_rank_backtest.json', {cache: 'no-cache'});
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      payload = await resp.json();
    } catch (e) {
      console.warn('[Enhancements] top_n_rank_backtest.json fetch failed:', e);
      return;
    }
    if (gen !== _topNRenderGen) return;
    const windows = payload.windows || {};
    const detail = payload.per_day_detail || {};
    function pnlColor(v) {
      if (v == null || isNaN(v)) return '#888';
      if (v > 0) return '#22c55e';
      if (v < 0) return '#ef4444';
      return '#888';
    }
    function fmtPnl(v) {
      if (v == null || isNaN(v)) return '—';
      const sign = v > 0 ? '+' : '';
      return sign + v.toFixed(2) + '%';
    }
    function fmtCount(v) { return v == null ? '—' : String(v); }
    const order = [
      ['today', 'Today'],
      ['yesterday', 'Yesterday'],
      ['day_before_yesterday', '2 Days Ago'],
      ['last_7d', 'Last 7 Days'],
      ['last_30d', 'Last 30 Days'],
      ['all_lookback', 'All ' + (payload.lookback_days || 90) + 'd'],
    ];

    let html = '<div class="enh-section" id="enh-top-n-rank-backtest">';
    html += '<h3>Top-' + (payload.top_n || 10) + ' Rank Backtest — ' + htmlEscape(payload.asset_class || 'EQUITY') +
            ' <span class="enh-badge enh-badge-neutral">HINDSIGHT REPLAY</span></h3>';
    html += '<div style="font-size:12px;color:#888;margin-bottom:10px;line-height:1.5;">' +
            'If you had bought the top-' + (payload.top_n || 10) + ' ranked ' +
            htmlEscape(payload.asset_class || 'EQUITY') + ' picks by score on each day, ' +
            'this is the realized P&amp;L per window. <strong style="color:#f39c12">Hindsight only — validates the score ranker, does NOT prove forward edge.</strong> ' +
            (payload.generated_at ? '<span style="color:#94a3b8">Generated ' + htmlEscape(_fmtEST(payload.generated_at)) + '.</span>' : '') +
            '</div>';
    html += '<div class="enh-grid">';
    for (const [key, label] of order) {
      const w = windows[key] || {};
      const days = w.days != null ? w.days : 0;
      const picks = w.n_total_picks != null ? w.n_total_picks : 0;
      const mean = w.mean_daily_pnl_pct;
      const cum = w.cum_pnl_pct_if_held_daily_topn;
      const wr = w.wr_pct_across_topn_picks;
      html += '<div class="enh-card">';
      html += '<div class="enh-card-title">' + htmlEscape(label) + '</div>';
      if (picks === 0) {
        html += '<div class="enh-card-value" style="color:#666">—</div>';
        html += '<div class="enh-card-sub">no picks created in window</div>';
      } else {
        html += '<div class="enh-card-value" style="color:' + pnlColor(cum) + '">' + fmtPnl(cum) + '</div>';
        html += '<div class="enh-card-sub">' +
                fmtCount(days) + ' days · ' + fmtCount(picks) + ' picks · WR ' +
                (wr != null ? wr.toFixed(1) : '—') + '% · mean ' + fmtPnl(mean) + '/day</div>';
      }
      html += '</div>';
    }
    html += '</div>';

    // Per-day detail (today / yesterday / day_before): show which symbols
    const detailOrder = ['today', 'yesterday', 'day_before_yesterday'];
    const detailLabels = {today: 'Today', yesterday: 'Yesterday', day_before_yesterday: '2 Days Ago'};
    let hasDetail = false;
    for (const k of detailOrder) {
      if ((detail[k] || {}).picks && detail[k].picks.length) { hasDetail = true; break; }
    }
    if (hasDetail) {
      html += '<details style="margin-top:14px"><summary style="cursor:pointer;color:#06b6d4;font-size:12px;padding:6px 0">' +
              'Show top-' + (payload.top_n || 10) + ' picks per recent day</summary>';
      for (const k of detailOrder) {
        const d = detail[k] || {};
        if (!d.picks || !d.picks.length) continue;
        html += '<div style="margin-top:10px"><strong style="color:#cbd5e1;font-size:12px">' +
                htmlEscape(detailLabels[k]) + ' (' + htmlEscape(d.date || '') + ')</strong> ' +
                '<span style="color:#94a3b8;font-size:11px">WR ' + (d.wr_pct != null ? d.wr_pct.toFixed(1) : '—') +
                '% · mean ' + fmtPnl(d.mean_pnl_pct) + ' · cum ' + fmtPnl(d.cum_pnl_pct) + '</span></div>';
        html += '<table style="width:100%;font-size:11px;margin-top:4px;border-collapse:collapse">' +
                '<thead><tr><th style="text-align:left;padding:4px 6px;color:#94a3b8;font-weight:500">symbol</th>' +
                '<th style="text-align:left;padding:4px 6px;color:#94a3b8;font-weight:500">strategy</th>' +
                '<th style="text-align:left;padding:4px 6px;color:#94a3b8;font-weight:500">dir</th>' +
                '<th style="text-align:right;padding:4px 6px;color:#94a3b8;font-weight:500">score</th>' +
                '<th style="text-align:right;padding:4px 6px;color:#94a3b8;font-weight:500">pnl_pct</th>' +
                '<th style="text-align:left;padding:4px 6px;color:#94a3b8;font-weight:500">status</th></tr></thead><tbody>';
        for (const p of d.picks) {
          html += '<tr style="border-top:1px solid rgba(42,42,74,0.4)">' +
                  '<td style="padding:3px 6px;color:#c4b5fd">' + htmlEscape(p.symbol || '') + '</td>' +
                  '<td style="padding:3px 6px;color:#cbd5e1">' + htmlEscape(p.strategy || '') + '</td>' +
                  '<td style="padding:3px 6px">' + htmlEscape(p.direction || '') + '</td>' +
                  '<td style="padding:3px 6px;text-align:right;font-variant-numeric:tabular-nums">' + (p.score != null ? p.score.toFixed(2) : '—') + '</td>' +
                  '<td style="padding:3px 6px;text-align:right;font-variant-numeric:tabular-nums;color:' + pnlColor(p.pnl_pct) + '">' + fmtPnl(p.pnl_pct) + '</td>' +
                  '<td style="padding:3px 6px;color:#94a3b8">' + htmlEscape(p.status || '') + '</td></tr>';
        }
        html += '</tbody></table>';
      }
      html += '</details>';
    }
    html += '<div style="margin-top:10px;font-size:11px;color:#94a3b8">' +
            'Method: queries <code style="color:#c4b5fd">trading_picks</code> for closed ' +
            htmlEscape(payload.asset_class || 'EQUITY') + ' rows from the last ' +
            (payload.lookback_days || 90) + ' days, buckets by created_at day, ranks by score DESC, ' +
            'takes top-' + (payload.top_n || 10) + ', computes realized pnl_pct. ' +
            '<strong style="color:#f59e0b">NFA</strong> — validates the score field as a ranker; ' +
            'does NOT prove forward edge. Pair with <a href="anti_overfit.html" style="color:#06b6d4">DSR audit</a> + walk-forward.' +
            '</div>';
    html += '</div>';

    const host = el('enhancements-host') || el('tab-overview') || document.body;
    const existing = el('enh-top-n-rank-backtest');
    if (existing) existing.remove();
    const wrapper = document.createElement('div');
    wrapper.innerHTML = html;
    const node = wrapper.firstElementChild;
    if (gen !== _topNRenderGen) return;
    host.appendChild(node);
  }

  // ── Commodity / Futures friendly-name tooltips ───────────────
  // User feedback 2026-05-12: commodity symbols like CT=F, KC=F, GC=F are
  // opaque without context. Add hover tooltips with friendly names + a
  // one-liner of the contract spec. Decorates ANY text node containing one
  // of the known tickers; runs on init + after data refresh.
  //
  // Map: yfinance ticker → friendly name + contract hint.
  const COMMODITY_FRIENDLY = {
    // Softs / agricultural
    'CT=F':  { name: 'Cotton Futures',      hint: '50,000 lbs · ICE · $5/tick' },
    'KC=F':  { name: 'Coffee Futures',      hint: '37,500 lbs · ICE · $3.75/tick' },
    'SB=F':  { name: 'Sugar #11 Futures',   hint: '112,000 lbs · ICE · $11.20/tick' },
    'CC=F':  { name: 'Cocoa Futures',       hint: '10 metric tons · ICE · $10/tick' },
    'OJ=F':  { name: 'Orange Juice Futures', hint: '15,000 lbs · ICE · $1.50/tick' },
    'ZC=F':  { name: 'Corn Futures',        hint: '5,000 bu · CBOT · $12.50/tick' },
    'ZS=F':  { name: 'Soybean Futures',     hint: '5,000 bu · CBOT · $12.50/tick' },
    'ZW=F':  { name: 'Wheat Futures',       hint: '5,000 bu · CBOT · $12.50/tick' },
    'ZM=F':  { name: 'Soybean Meal Futures', hint: '100 tons · CBOT · $10/tick' },
    'ZL=F':  { name: 'Soybean Oil Futures',  hint: '60,000 lbs · CBOT · $6/tick' },
    'ZO=F':  { name: 'Oats Futures',        hint: '5,000 bu · CBOT' },
    'ZR=F':  { name: 'Rice Futures',        hint: '2,000 cwt · CBOT' },
    // Metals
    'GC=F':  { name: 'Gold Futures',        hint: '100 troy oz · COMEX · $10/tick' },
    'SI=F':  { name: 'Silver Futures',      hint: '5,000 troy oz · COMEX · $25/tick' },
    'HG=F':  { name: 'Copper Futures',      hint: '25,000 lbs · COMEX · $12.50/tick' },
    'PL=F':  { name: 'Platinum Futures',    hint: '50 troy oz · NYMEX · $5/tick' },
    'PA=F':  { name: 'Palladium Futures',   hint: '100 troy oz · NYMEX · $5/tick' },
    // Energy
    'CL=F':  { name: 'WTI Crude Oil Futures',    hint: '1,000 bbl · NYMEX · $10/tick' },
    'BZ=F':  { name: 'Brent Crude Futures',      hint: '1,000 bbl · ICE · $10/tick' },
    'NG=F':  { name: 'Natural Gas Futures',      hint: '10,000 MMBtu · NYMEX · $10/tick' },
    'RB=F':  { name: 'RBOB Gasoline Futures',    hint: '42,000 gal · NYMEX · $4.20/tick' },
    'HO=F':  { name: 'Heating Oil Futures',      hint: '42,000 gal · NYMEX · $4.20/tick' },
    // Livestock
    'LE=F':  { name: 'Live Cattle Futures',      hint: '40,000 lbs · CME · $10/tick' },
    'GF=F':  { name: 'Feeder Cattle Futures',    hint: '50,000 lbs · CME · $12.50/tick' },
    'HE=F':  { name: 'Lean Hogs Futures',        hint: '40,000 lbs · CME · $10/tick' },
    // Equity-index futures (sometimes tagged COMMODITY or FUTURES)
    'ES=F':  { name: 'S&P 500 E-mini',       hint: '$50 × index · CME · $12.50/tick' },
    'NQ=F':  { name: 'NASDAQ 100 E-mini',    hint: '$20 × index · CME · $5/tick' },
    'RTY=F': { name: 'Russell 2000 E-mini',  hint: '$50 × index · CME · $5/tick' },
    'YM=F':  { name: 'Dow E-mini',           hint: '$5 × index · CBOT · $5/tick' },
    'MES=F': { name: 'Micro S&P 500',        hint: '$5 × index · CME · $1.25/tick' },
    'MNQ=F': { name: 'Micro NASDAQ 100',     hint: '$2 × index · CME · $0.50/tick' },
    'M2K=F': { name: 'Micro Russell 2000',   hint: '$5 × index · CME · $0.50/tick' },
    'MYM=F': { name: 'Micro Dow',            hint: '$0.50 × index · CBOT · $0.50/tick' },
    // Rates / bonds
    'ZB=F':  { name: '30-Year T-Bond Futures', hint: '$100k face · CBOT · $31.25/tick' },
    'ZN=F':  { name: '10-Year T-Note Futures', hint: '$100k face · CBOT · $15.625/tick' },
    'ZF=F':  { name: '5-Year T-Note Futures',  hint: '$100k face · CBOT · $7.8125/tick' },
    'ZT=F':  { name: '2-Year T-Note Futures',  hint: '$200k face · CBOT · $7.8125/tick' },
    // Currencies (FX futures, distinct from yfinance =X pairs)
    '6E=F':  { name: 'Euro FX Futures',         hint: '€125k · CME · $12.50/tick' },
    '6J=F':  { name: 'Japanese Yen Futures',    hint: '¥12.5M · CME · $12.50/tick' },
    '6B=F':  { name: 'British Pound Futures',   hint: '£62.5k · CME · $6.25/tick' },
    '6A=F':  { name: 'Australian Dollar Futures', hint: 'A$100k · CME · $10/tick' },
    '6C=F':  { name: 'Canadian Dollar Futures', hint: 'C$100k · CME · $10/tick' },
    '6S=F':  { name: 'Swiss Franc Futures',     hint: 'CHF 125k · CME · $12.50/tick' },
    // Crypto futures
    'BTC=F': { name: 'Bitcoin Futures',         hint: '5 BTC · CME · $25/tick' },
    'MBT=F': { name: 'Micro Bitcoin Futures',   hint: '0.1 BTC · CME · $0.50/tick' },
    'ETH=F': { name: 'Ether Futures',           hint: '50 ETH · CME · $2.50/tick' },
    'MET=F': { name: 'Micro Ether Futures',     hint: '0.1 ETH · CME · $0.05/tick' },
  };

  function attachCommodityTooltips(root) {
    root = root || document;
    // Build a regex from the map keys, with word-ish boundaries that respect '=' / '_'.
    // Match `XX=F` or `XXX=F` (uppercase letters/digits before =F).
    const re = /\b([A-Z0-9]{1,4}=F)\b/g;
    // Walk text nodes; for each match, wrap the symbol in a <span title="...">.
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: function (n) {
        if (!n.nodeValue) return NodeFilter.FILTER_REJECT;
        // Skip nodes inside <script>, <style>, or already-decorated tooltip spans.
        const p = n.parentNode;
        if (!p) return NodeFilter.FILTER_REJECT;
        const tag = (p.tagName || '').toUpperCase();
        if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'TEXTAREA') return NodeFilter.FILTER_REJECT;
        if (p.classList && p.classList.contains('commodity-friendly')) return NodeFilter.FILTER_REJECT;
        // Cheap pre-filter — only walk into text that contains the '=F' suffix
        return n.nodeValue.indexOf('=F') >= 0 ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      }
    });
    const candidates = [];
    let node;
    while ((node = walker.nextNode())) candidates.push(node);
    candidates.forEach(function (tn) {
      const text = tn.nodeValue;
      let lastIdx = 0, m;
      re.lastIndex = 0;
      const frag = document.createDocumentFragment();
      let touched = false;
      while ((m = re.exec(text)) !== null) {
        const sym = m[1];
        const entry = COMMODITY_FRIENDLY[sym];
        if (!entry) continue;
        touched = true;
        if (m.index > lastIdx) frag.appendChild(document.createTextNode(text.slice(lastIdx, m.index)));
        const span = document.createElement('span');
        span.className = 'commodity-friendly';
        span.style.cssText = 'border-bottom:1px dotted rgba(167,139,250,0.5);cursor:help;';
        span.title = entry.name + ' — ' + entry.hint;
        span.textContent = sym;
        frag.appendChild(span);
        lastIdx = m.index + sym.length;
      }
      if (touched) {
        if (lastIdx < text.length) frag.appendChild(document.createTextNode(text.slice(lastIdx)));
        tn.parentNode.replaceChild(frag, tn);
      }
    });
  }

  // Expose so other scripts / template.html can trigger after dynamic renders.
  window.attachCommodityTooltips = attachCommodityTooltips;

  // ── EAGLE2 Phase 0: policy-clean honesty strip (sizes from money_ready only) ──
  async function renderEagle2PolicyStrip() {
    if (document.getElementById('enh-eagle2-policy-strip')) return;
    try {
      const resp = await fetch('./data/strategy_admissibility.json?_=' + Date.now());
      if (!resp.ok) return;
      const data = await resp.json();
      const mr = (data.live_money_ready || {});
      const verifiedLab = (((data.edge_surfaces || {}).verified_lab) || {});
      const bestPilot = verifiedLab.best_candidate || null;
      const ready = mr.money_ready_classes || [];
      const byClass = mr.by_class || {};
      const rows = Object.keys(byClass).sort().map(function (cls) {
        const v = byClass[cls] || {};
        const pf = v.pf != null ? Number(v.pf).toFixed(2) : '—';
        const wr = v.wr != null ? (Number(v.wr) <= 1 ? (Number(v.wr) * 100).toFixed(1) : Number(v.wr).toFixed(1)) : '—';
        return '<span style="margin-right:12px"><b>' + htmlEscape(cls) + '</b> PF ' + pf + ' WR ' + wr + '%</span>';
      }).join('');
      let pilotLine = '';
      if (bestPilot && bestPilot.label) {
        const nClosed = bestPilot.forward_n_closed != null ? String(bestPilot.forward_n_closed) : '0';
        const nTarget = bestPilot.forward_n_target != null ? String(bestPilot.forward_n_target) : '100';
        const blockers = Array.isArray(bestPilot.blockers) && bestPilot.blockers.length ? bestPilot.blockers.join(', ') : 'forward gate not cleared';
        const shadowReady = bestPilot.shadow_checkpoint_ready === true;
        const shadowKnown = bestPilot.shadow_checkpoint_ready === true || bestPilot.shadow_checkpoint_ready === false;
        const shadowBlockers = Array.isArray(bestPilot.shadow_blockers) && bestPilot.shadow_blockers.length
          ? ' [' + bestPilot.shadow_blockers.join(', ') + ']'
          : '';
        const openSymbol = bestPilot.open_symbol ? ' open ' + htmlEscape(String(bestPilot.open_symbol)) : '';
        const shadowState = shadowKnown
          ? ', shadow checkpoint ' + (shadowReady ? 'ready' : 'pending') + htmlEscape(shadowBlockers)
          : '';
        pilotLine = '<div style="line-height:1.5;margin-top:6px;color:#ddd6fe"><b>Best forward pilot:</b> ' +
          htmlEscape(bestPilot.label) + ' — WF ' + htmlEscape(String(bestPilot.lab_verdict || 'unknown')) +
          ', forward ' + htmlEscape(nClosed) + '/' + htmlEscape(nTarget) + openSymbol +
          shadowState + ', blockers: ' + htmlEscape(blockers) + '.</div>';
      }
      const banner = document.createElement('div');
      banner.id = 'enh-eagle2-policy-strip';
      banner.style.cssText = 'background:#1e1b4b;border:1px solid #6366f1;border-radius:8px;padding:10px 14px;margin:12px 0;font-size:12px;color:#c7d2fe';
      banner.innerHTML =
        '<div style="font-weight:700;color:#a5b4fc;margin-bottom:6px">EAGLE2 — Size capital on policy-clean only (' +
        ready.length + '/9 money-ready)</div>' +
        '<div style="line-height:1.6">Tournament &amp; pick_funnel cells are discovery/paper — not sizing surfaces. ' +
        rows + '</div>' + pilotLine;
      const anchor = document.querySelector('.header') || document.querySelector('header') || document.body.firstChild;
      if (anchor && anchor.parentNode) {
        anchor.parentNode.insertBefore(banner, anchor.nextSibling);
      } else {
        document.body.prepend(banner);
      }
    } catch (e) {
      console.warn('[Enhancements] EAGLE2 policy strip error:', e);
    }
  }

  // ── Main initialization ──────────────────────────────────────
  function initEnhancements() {
    if (!window.DASHBOARD_DATA) {
      setTimeout(initEnhancements, 500);
      return;
    }

    // Prevent double-init
    if (window._enhInitDone) return;
    window._enhInitDone = true;

    const D = window.DASHBOARD_DATA;
    injectStyles();

    try { renderSystemTrends(D); } catch (e) { console.warn('[Enhancements] System Trends error:', e); }
    try { renderStrategyConsensus(D); } catch (e) { console.warn('[Enhancements] Strategy Consensus error:', e); }
    try { renderTimeWindowBreakdown(D); } catch (e) { console.warn('[Enhancements] Time-Window Leaderboard error:', e); }
    // DB health cards — async; isolated try/catch so a fetch error never breaks other sections
    renderDbHealth().catch(e => console.warn('[Enhancements] DB Health error:', e));
    // Top-N rank backtest — async; reads data/top_n_rank_backtest.json
    renderTopNRankBacktest().catch(e => console.warn('[Enhancements] Top-N Rank Backtest error:', e));
    // ML Gatekeeper A/B sleeve panel — async; reads both ml_gatekeeper/data/* JSONs
    renderMLGatekeeperAB().catch(e => console.warn('[Enhancements] ML Gatekeeper A/B error:', e));
    // Commodity / futures friendly-name tooltips — decorate the whole page once
    // after enhancements rendered. Cheap idempotent walk; safe to re-run on
    // dashboard-data-loaded.
    try { attachCommodityTooltips(document.body); } catch (e) { console.warn('[Enhancements] Commodity tooltips error:', e); }
    renderEagle2PolicyStrip().catch(e => console.warn('[Enhancements] EAGLE2 policy strip error:', e));

    console.log('[Dashboard Enhancements] Loaded: System Trends, Strategy Consensus, Time-Window Leaderboard, DB Health, Top-N Backtest, Commodity Tooltips, EAGLE2 Policy Strip');
  }

  // Start on DOM ready or immediately
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => setTimeout(initEnhancements, 1000));
  } else {
    setTimeout(initEnhancements, 1000);
  }

  // Re-run once after external JSON lands (debounced — template may fire this event 2-3×
  // in quick succession: external-data path, embedded-data path, load event.
  // 3000ms debounce ensures only the last fire triggers a re-render.
  // Nodes are faded (not removed) while re-render is in-flight so sections
  // never flash blank — each render fn removes the faded node when ready.
  let _enhRefreshTimer = null;
  document.addEventListener('dashboard-data-loaded', function () {
    clearTimeout(_enhRefreshTimer);
    _enhRefreshTimer = setTimeout(function () {
      window._enhInitDone = false;
      ['enh-system-trends', 'enh-strategy-consensus', 'enh-time-window-leaderboard', 'enh-db-health', 'enh-top-n-rank-backtest', 'enh-ml-gatekeeper-ab'].forEach(id => {
        const node = document.getElementById(id);
        // Fade rather than delete — keeps section visible during async re-fetch
        if (node) { node.style.opacity = '0.45'; node.style.pointerEvents = 'none'; }
      });
      initEnhancements();
    }, 3000);
  });
})();
