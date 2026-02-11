/**
 * Regime Integration Layer — Connects Python intelligence to Live Monitor UI.
 *
 * Fetches regime data from regime.php API and provides:
 *   1. Regime dashboard panel (HMM state, Hurst, VIX, composite score)
 *   2. Strategy toggle display (which bundles are active)
 *   3. Position sizing recommendations per algorithm
 *   4. Alpha decay warnings
 *   5. Meta-labeler status
 *   6. World-class checklist score
 *
 * Usage: Include in live-monitor.html after main JS.
 *   <script src="regime-integration.js"></script>
 */

(function() {
    'use strict';

    const API_BASE = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
        ? '/live-monitor/api'
        : 'https://findtorontoevents.ca/live-monitor/api';

    // ─── Fetch Helpers ──────────────────────────────────────────────

    async function fetchRegime() {
        try {
            const resp = await fetch(API_BASE + '/regime.php?action=get_regime');
            const data = await resp.json();
            return data.ok ? data.regime : null;
        } catch (e) {
            console.warn('Regime fetch failed:', e);
            return null;
        }
    }

    async function fetchPositionSizing() {
        try {
            const resp = await fetch(API_BASE + '/regime.php?action=get_position_sizing');
            const data = await resp.json();
            return data.ok ? data.sizing : [];
        } catch (e) {
            console.warn('Position sizing fetch failed:', e);
            return [];
        }
    }

    async function fetchMetaLabeler() {
        try {
            const resp = await fetch(API_BASE + '/regime.php?action=get_meta_labeler');
            const data = await resp.json();
            return data.ok ? data.meta_labeler : null;
        } catch (e) {
            console.warn('Meta-labeler fetch failed:', e);
            return null;
        }
    }

    // ─── Regime Dashboard Panel ─────────────────────────────────────

    function renderRegimePanel(regime) {
        if (!regime) return '';

        const market = regime.market || {};
        const macro = regime.macro || {};
        const toggles = market.strategy_toggles || {};

        // Color coding
        const regimeColors = {
            bull: '#22c55e',
            sideways: '#eab308',
            bear: '#ef4444'
        };
        const hurstColors = {
            trending: '#3b82f6',
            mean_reverting: '#8b5cf6',
            random: '#6b7280'
        };
        const vixColors = {
            normal: '#22c55e',
            elevated: '#eab308',
            fear: '#ef4444',
            fear_peak: '#dc2626',
            complacent: '#f97316'
        };

        const hmm = market.hmm_regime || 'unknown';
        const hurst = market.hurst_regime || 'unknown';
        const composite = market.composite_score || 50;
        const vix = macro.vix_regime || 'unknown';

        // Composite score bar
        const barWidth = Math.max(0, Math.min(100, composite));
        const barColor = composite > 65 ? '#22c55e' : (composite > 40 ? '#eab308' : '#ef4444');

        let html = '<div class="regime-panel" style="background:#1a1a2e;border:1px solid #333;border-radius:8px;padding:16px;margin-bottom:16px;">';
        html += '<h3 style="color:#e0e0e0;margin:0 0 12px 0;font-size:14px;">🧠 Market Regime Intelligence</h3>';

        // Row 1: HMM + Hurst + VIX
        html += '<div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:12px;">';

        // HMM badge
        html += '<div style="flex:1;min-width:120px;">';
        html += '<div style="color:#999;font-size:11px;">HMM State</div>';
        html += '<div style="color:' + (regimeColors[hmm] || '#999') + ';font-size:18px;font-weight:bold;text-transform:uppercase;">' + hmm + '</div>';
        html += '<div style="color:#666;font-size:10px;">' + Math.round((market.hmm_confidence || 0) * 100) + '% confidence</div>';
        html += '</div>';

        // Hurst badge
        html += '<div style="flex:1;min-width:120px;">';
        html += '<div style="color:#999;font-size:11px;">Hurst Regime</div>';
        html += '<div style="color:' + (hurstColors[hurst] || '#999') + ';font-size:18px;font-weight:bold;text-transform:uppercase;">' + hurst + '</div>';
        html += '<div style="color:#666;font-size:10px;">H=' + (market.hurst || 0).toFixed(3) + '</div>';
        html += '</div>';

        // VIX badge
        html += '<div style="flex:1;min-width:120px;">';
        html += '<div style="color:#999;font-size:11px;">VIX Regime</div>';
        html += '<div style="color:' + (vixColors[vix] || '#999') + ';font-size:18px;font-weight:bold;text-transform:uppercase;">' + vix + '</div>';
        html += '<div style="color:#666;font-size:10px;">Level: ' + (macro.vix_level || '?') + '</div>';
        html += '</div>';

        // Composite score
        html += '<div style="flex:1;min-width:160px;">';
        html += '<div style="color:#999;font-size:11px;">Composite Score</div>';
        html += '<div style="font-size:24px;font-weight:bold;color:' + barColor + ';">' + composite.toFixed(1) + '</div>';
        html += '<div style="background:#333;border-radius:4px;height:6px;width:100%;margin-top:4px;">';
        html += '<div style="background:' + barColor + ';border-radius:4px;height:100%;width:' + barWidth + '%;transition:width 0.5s;"></div>';
        html += '</div>';
        html += '</div>';

        html += '</div>';

        // Row 2: Strategy Toggles
        if (Object.keys(toggles).length > 0) {
            html += '<div style="border-top:1px solid #333;padding-top:8px;">';
            html += '<div style="color:#999;font-size:11px;margin-bottom:6px;">Strategy Bundle Weights</div>';
            html += '<div style="display:flex;gap:8px;flex-wrap:wrap;">';

            var bundleIcons = {
                momentum: '🚀',
                reversion: '↩️',
                fundamental: '📊',
                sentiment: '💭',
                ml_alpha: '🤖'
            };

            for (var bundle in toggles) {
                var weight = toggles[bundle];
                var pct = Math.round(weight * 100);
                var color = weight > 0.7 ? '#22c55e' : (weight > 0.4 ? '#eab308' : '#ef4444');
                var icon = bundleIcons[bundle] || '📈';
                html += '<div style="background:#222;border:1px solid #444;border-radius:6px;padding:4px 10px;font-size:12px;">';
                html += '<span>' + icon + ' ' + bundle + '</span> ';
                html += '<span style="color:' + color + ';font-weight:bold;">' + pct + '%</span>';
                html += '</div>';
            }

            html += '</div>';
            html += '</div>';
        }

        // Row 3: Yield Curve + Vol
        html += '<div style="display:flex;gap:16px;margin-top:8px;border-top:1px solid #333;padding-top:8px;">';
        html += '<div style="color:#999;font-size:11px;">Yield Curve: <span style="color:#e0e0e0;">' + (macro.yield_curve || '?') + '</span></div>';
        html += '<div style="color:#999;font-size:11px;">EWMA Vol: <span style="color:#e0e0e0;">' + ((market.vol_annualized || 0) * 100).toFixed(1) + '%</span> ann.</div>';
        html += '<div style="color:#999;font-size:11px;">Updated: <span style="color:#e0e0e0;">' + (regime.updated_at || '?') + '</span></div>';
        html += '</div>';

        html += '</div>';
        return html;
    }

    // ─── Position Sizing Table ──────────────────────────────────────

    function renderSizingPanel(sizing) {
        if (!sizing || sizing.length === 0) return '';

        let html = '<div class="sizing-panel" style="background:#1a1a2e;border:1px solid #333;border-radius:8px;padding:16px;margin-bottom:16px;">';
        html += '<h3 style="color:#e0e0e0;margin:0 0 12px 0;font-size:14px;">📐 Half-Kelly Position Sizing</h3>';
        html += '<div style="overflow-x:auto;">';
        html += '<table style="width:100%;border-collapse:collapse;font-size:12px;">';
        html += '<tr style="color:#999;border-bottom:1px solid #333;">';
        html += '<th style="text-align:left;padding:4px;">Algorithm</th>';
        html += '<th style="text-align:right;padding:4px;">Kelly</th>';
        html += '<th style="text-align:right;padding:4px;">Vol×</th>';
        html += '<th style="text-align:right;padding:4px;">Regime×</th>';
        html += '<th style="text-align:right;padding:4px;">Decay×</th>';
        html += '<th style="text-align:right;padding:4px;">Size%</th>';
        html += '<th style="text-align:right;padding:4px;">$</th>';
        html += '<th style="text-align:right;padding:4px;">30d Sharpe</th>';
        html += '</tr>';

        sizing.forEach(function(s) {
            var decayColor = s.is_decaying ? '#ef4444' : '#22c55e';
            var sharpeColor = s.algo_sharpe_30d > 1.0 ? '#22c55e' : (s.algo_sharpe_30d > 0.5 ? '#eab308' : '#ef4444');

            html += '<tr style="border-bottom:1px solid #222;color:#e0e0e0;">';
            html += '<td style="padding:4px;">' + (s.is_decaying ? '⚠️ ' : '') + s.algorithm_name + '</td>';
            html += '<td style="text-align:right;padding:4px;">' + (s.kelly_base * 100).toFixed(1) + '%</td>';
            html += '<td style="text-align:right;padding:4px;">' + s.vol_scalar.toFixed(1) + 'x</td>';
            html += '<td style="text-align:right;padding:4px;">' + s.regime_modifier.toFixed(1) + 'x</td>';
            html += '<td style="text-align:right;padding:4px;color:' + decayColor + ';">' + s.decay_weight.toFixed(1) + 'x</td>';
            html += '<td style="text-align:right;padding:4px;font-weight:bold;">' + s.final_size_pct.toFixed(1) + '%</td>';
            html += '<td style="text-align:right;padding:4px;">$' + s.dollar_amount.toFixed(0) + '</td>';
            html += '<td style="text-align:right;padding:4px;color:' + sharpeColor + ';">' + s.algo_sharpe_30d.toFixed(2) + '</td>';
            html += '</tr>';
        });

        html += '</table></div></div>';
        return html;
    }

    // ─── Meta-Labeler Status ────────────────────────────────────────

    function renderMetaPanel(meta) {
        if (!meta) {
            return '<div style="background:#1a1a2e;border:1px solid #333;border-radius:8px;padding:16px;margin-bottom:16px;">' +
                '<h3 style="color:#e0e0e0;margin:0 0 8px 0;font-size:14px;">🤖 Meta-Labeler</h3>' +
                '<div style="color:#999;font-size:12px;">Not trained yet. Will train on Sunday with 50+ closed trades.</div></div>';
        }

        var precColor = meta.avg_precision > 0.60 ? '#22c55e' : (meta.avg_precision > 0.45 ? '#eab308' : '#ef4444');

        let html = '<div style="background:#1a1a2e;border:1px solid #333;border-radius:8px;padding:16px;margin-bottom:16px;">';
        html += '<h3 style="color:#e0e0e0;margin:0 0 12px 0;font-size:14px;">🤖 Meta-Labeler (XGBoost Signal Filter)</h3>';
        html += '<div style="display:flex;gap:16px;flex-wrap:wrap;">';
        html += '<div style="color:#999;font-size:12px;">Precision: <span style="color:' + precColor + ';font-weight:bold;">' + (meta.avg_precision * 100).toFixed(1) + '%</span></div>';
        html += '<div style="color:#999;font-size:12px;">Recall: <span style="color:#e0e0e0;">' + (meta.avg_recall * 100).toFixed(1) + '%</span></div>';
        html += '<div style="color:#999;font-size:12px;">F1: <span style="color:#e0e0e0;">' + meta.avg_f1.toFixed(3) + '</span></div>';
        html += '<div style="color:#999;font-size:12px;">Samples: <span style="color:#e0e0e0;">' + meta.training_samples + '</span></div>';
        html += '<div style="color:#999;font-size:12px;">Trained: <span style="color:#e0e0e0;">' + meta.trained_at + '</span></div>';
        html += '</div>';

        // Top features
        if (meta.top_features && meta.top_features.length > 0) {
            html += '<div style="margin-top:8px;border-top:1px solid #333;padding-top:8px;">';
            html += '<div style="color:#999;font-size:11px;margin-bottom:4px;">Top Predictive Features:</div>';
            meta.top_features.slice(0, 5).forEach(function(f) {
                var barW = Math.round(f.importance * 500);
                html += '<div style="display:flex;align-items:center;gap:8px;margin:2px 0;">';
                html += '<span style="color:#e0e0e0;font-size:11px;width:140px;">' + f.name + '</span>';
                html += '<div style="background:#333;height:4px;flex:1;border-radius:2px;">';
                html += '<div style="background:#3b82f6;height:100%;width:' + barW + '%;border-radius:2px;"></div>';
                html += '</div>';
                html += '<span style="color:#666;font-size:10px;">' + (f.importance * 100).toFixed(1) + '%</span>';
                html += '</div>';
            });
            html += '</div>';
        }

        html += '</div>';
        return html;
    }

    // ─── Initialize ─────────────────────────────────────────────────

    async function initRegimePanel() {
        // Find insertion point (after system health, before signals)
        var target = document.getElementById('regime-intelligence-panel');

        if (!target) {
            // Create target if it doesn't exist
            var healthPanel = document.querySelector('.system-health, #system-health, [data-panel="health"]');
            if (healthPanel) {
                target = document.createElement('div');
                target.id = 'regime-intelligence-panel';
                healthPanel.parentNode.insertBefore(target, healthPanel.nextSibling);
            } else {
                // Fallback: prepend to main content
                var main = document.querySelector('main, .main-content, #content, .container');
                if (main) {
                    target = document.createElement('div');
                    target.id = 'regime-intelligence-panel';
                    main.insertBefore(target, main.firstChild);
                }
            }
        }

        if (!target) {
            console.warn('Regime panel: no insertion point found');
            return;
        }

        // Fetch all data in parallel
        var results = await Promise.all([
            fetchRegime(),
            fetchPositionSizing(),
            fetchMetaLabeler()
        ]);

        var regime = results[0];
        var sizing = results[1];
        var meta = results[2];

        var html = '';
        html += renderRegimePanel(regime);
        html += renderSizingPanel(sizing);
        html += renderMetaPanel(meta);

        target.innerHTML = html;
    }

    // ─── Expose API ─────────────────────────────────────────────────

    window.RegimeIntegration = {
        fetch: fetchRegime,
        fetchSizing: fetchPositionSizing,
        fetchMeta: fetchMetaLabeler,
        init: initRegimePanel,
        render: {
            regime: renderRegimePanel,
            sizing: renderSizingPanel,
            meta: renderMetaPanel
        }
    };

    // Auto-init when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initRegimePanel);
    } else {
        // Small delay to ensure page structure exists
        setTimeout(initRegimePanel, 500);
    }

})();
