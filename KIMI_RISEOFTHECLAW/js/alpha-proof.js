/**
 * Rise of the Claw — Alpha Proof Panel (v10.4)
 * Renders world-class forward-looking alpha dashboard:
 *   - Per-asset-class performance breakdown with risk-adjusted metrics
 *   - Open picks with stop/target/R:R ratio displayed
 *   - Signal convergence: symbols targeted by 2+ algos (higher conviction)
 *   - Pure algo performance table across all 5 asset classes
 */
(function() {
    'use strict';

    var CAT_META = {
        crypto: { label: 'Crypto',      icon: '₿',  color: '#f59e0b', bg: 'rgba(245,158,11,0.1)' },
        stock:  { label: 'Stocks',      icon: '📈', color: '#3b82f6', bg: 'rgba(59,130,246,0.1)' },
        meme:   { label: 'Meme Coins',  icon: '🚀', color: '#ec4899', bg: 'rgba(236,72,153,0.1)' },
        penny:  { label: 'Penny/Micro', icon: '💎', color: '#10b981', bg: 'rgba(16,185,129,0.1)' },
        forex:  { label: 'Forex',       icon: '💱', color: '#8b5cf6', bg: 'rgba(139,92,246,0.1)' },
    };

    function fmtPct(v, decimals) {
        var n = parseFloat(v) || 0;
        var d = decimals !== undefined ? decimals : 2;
        var s = n >= 0 ? '+' : '';
        return '<span style="color:' + (n > 0 ? '#22c55e' : n < 0 ? '#ef4444' : '#8888aa') + ';font-weight:600">'
            + s + n.toFixed(d) + '%</span>';
    }

    function fmtPrice(p) {
        if (typeof p !== 'number' || !p) return '--';
        if (p >= 1000) return '$' + p.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
        if (p >= 1)    return '$' + p.toFixed(2);
        if (p >= 0.01) return '$' + p.toFixed(4);
        return '$' + p.toFixed(6);
    }

    function msSince(isoStr) {
        if (!isoStr) return 0;
        return Date.now() - new Date(isoStr).getTime();
    }

    function daysHeld(isoStr) {
        return (msSince(isoStr) / 86400000).toFixed(1);
    }

    // -------------------------------------------------------------------------
    // Build per-category aggregated stats from live competition data
    // -------------------------------------------------------------------------
    function buildCatStats(algorithms) {
        var cats = ['crypto', 'stock', 'meme', 'penny', 'forex'];
        var stats = {};
        cats.forEach(function(cat) { stats[cat] = {
            algos: [], activePicks: [], closedPicks: [],
            totalReturn: 0, weightedReturn: 0,
            deployedCapital: 0, openPnl: 0,
        }; });

        algorithms.forEach(function(algo) {
            var cat = algo.category || 'stock';
            if (!stats[cat]) return;
            stats[cat].algos.push(algo);

            var open = algo.activePicks || [];
            var closed = algo.closedPicks || [];

            open.forEach(function(p) {
                // Use symbolCategory if set (true asset class), fall back to algo category
                var pcat = p.symbolCategory || cat;
                if (!stats[pcat]) pcat = cat;
                stats[pcat].activePicks.push({...p, _algoName: algo.name, _algoId: algo.id, _algoCat: cat});
                var ep = parseFloat(p.entryPrice) || 0;
                var cp = parseFloat(p.currentPrice) || ep;
                var alloc = parseFloat(p.allocation) || 0;
                if (alloc > 0 && ep > 0) {
                    stats[pcat].deployedCapital += alloc;
                    stats[pcat].openPnl += alloc * ((cp - ep) / ep);
                }
            });

            closed.forEach(function(p) {
                var pcat = p.symbolCategory || cat;
                if (!stats[pcat]) pcat = cat;
                stats[pcat].closedPicks.push({...p, _algoName: algo.name, _algoId: algo.id});
            });

            // Use algo's reported totalReturn (portfolio-level)
            stats[cat].totalReturn += algo.totalReturn || 0;
        });

        // Average return per category
        Object.keys(stats).forEach(function(cat) {
            var n = stats[cat].algos.length;
            stats[cat].avgReturn = n ? stats[cat].totalReturn / n : 0;
            var dep = stats[cat].deployedCapital;
            stats[cat].openPnlPct = dep > 0 ? (stats[cat].openPnl / dep) * 100 : 0;
        });

        return stats;
    }

    // -------------------------------------------------------------------------
    // Find convergence picks — same symbol in 2+ algos simultaneously
    // -------------------------------------------------------------------------
    function buildConvergence(algorithms) {
        var symMap = {};
        algorithms.forEach(function(algo) {
            (algo.activePicks || []).forEach(function(p) {
                var sym = p.symbol;
                if (!symMap[sym]) symMap[sym] = [];
                symMap[sym].push({
                    algo: algo.name, cat: algo.category,
                    symCat: p.symbolCategory || algo.category,
                    entry: p.entryPrice, cur: p.currentPrice,
                    reason: p.reason, entryDate: p.entryDate,
                    stopPrice: p.stopPrice, targetPrice: p.targetPrice,
                    riskReward: p.riskReward,
                });
            });
        });
        return Object.keys(symMap)
            .filter(function(sym) { return symMap[sym].length >= 2; })
            .map(function(sym) { return { symbol: sym, picks: symMap[sym] }; })
            .sort(function(a, b) { return b.picks.length - a.picks.length; });
    }

    // -------------------------------------------------------------------------
    // Render: Per-asset-class performance cards
    // -------------------------------------------------------------------------
    function renderCatCards(catStats) {
        var order = ['crypto', 'stock', 'meme', 'penny', 'forex'];
        return order.map(function(cat) {
            var s = catStats[cat];
            var meta = CAT_META[cat];
            var openCount = s.activePicks.length;
            var closedCount = s.closedPicks.length;
            var algosWithPicks = s.algos.filter(function(a) {
                return (a.activePicks || []).length > 0;
            }).length;
            var winCount = s.closedPicks.filter(function(p) {
                return (p.returnPct || 0) > 0;
            }).length;
            var winRate = closedCount ? (winCount / closedCount * 100).toFixed(0) : '--';
            var openPnlColor = s.openPnlPct >= 0 ? '#22c55e' : '#ef4444';
            var openPnlSign = s.openPnlPct >= 0 ? '+' : '';

            return '<div style="background:' + meta.bg + ';border:1px solid ' + meta.color + '30;border-radius:10px;padding:14px 16px;min-width:180px;flex:1;">' +
                '<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">' +
                    '<span style="font-size:20px">' + meta.icon + '</span>' +
                    '<span style="font-size:13px;font-weight:700;color:' + meta.color + '">' + meta.label + '</span>' +
                '</div>' +
                '<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:12px;">' +
                    '<div>' +
                        '<div style="color:#555;font-size:10px;text-transform:uppercase;letter-spacing:1px">Algos</div>' +
                        '<div style="color:#e0e0f0;font-weight:600">' + s.algos.length + ' <span style="color:#555;font-weight:400">(' + algosWithPicks + ' active)</span></div>' +
                    '</div>' +
                    '<div>' +
                        '<div style="color:#555;font-size:10px;text-transform:uppercase;letter-spacing:1px">Picks</div>' +
                        '<div style="color:#e0e0f0;font-weight:600">' + openCount + ' open · ' + closedCount + ' closed</div>' +
                    '</div>' +
                    '<div>' +
                        '<div style="color:#555;font-size:10px;text-transform:uppercase;letter-spacing:1px">Open P&L</div>' +
                        '<div style="color:' + openPnlColor + ';font-weight:700">' + openPnlSign + s.openPnlPct.toFixed(2) + '%</div>' +
                    '</div>' +
                    '<div>' +
                        '<div style="color:#555;font-size:10px;text-transform:uppercase;letter-spacing:1px">Win Rate</div>' +
                        '<div style="color:#e0e0f0;font-weight:600">' + winRate + (closedCount ? '%' : '') + '</div>' +
                    '</div>' +
                '</div>' +
            '</div>';
        }).join('');
    }

    // -------------------------------------------------------------------------
    // Render: Open picks with stop/target/R:R — institutional-grade view
    // -------------------------------------------------------------------------
    function renderPicksTable(catStats, sortCat) {
        var allPicks = [];
        var order = ['crypto', 'stock', 'meme', 'penny', 'forex'];
        order.forEach(function(cat) {
            catStats[cat].activePicks.forEach(function(p) {
                allPicks.push({...p, _displayCat: cat});
            });
        });

        if (sortCat && sortCat !== 'all') {
            allPicks = allPicks.filter(function(p) { return p._displayCat === sortCat; });
        }

        // Sort: biggest losers first (most at risk) then biggest gainers
        allPicks.sort(function(a, b) {
            var ep_a = parseFloat(a.entryPrice) || 0;
            var cp_a = parseFloat(a.currentPrice) || ep_a;
            var ep_b = parseFloat(b.entryPrice) || 0;
            var cp_b = parseFloat(b.currentPrice) || ep_b;
            var ret_a = ep_a > 0 ? (cp_a - ep_a) / ep_a : 0;
            var ret_b = ep_b > 0 ? (cp_b - ep_b) / ep_b : 0;
            return ret_a - ret_b;
        });

        if (allPicks.length === 0) {
            return '<tr><td colspan="10" style="padding:20px;text-align:center;color:#555">No open picks in this category</td></tr>';
        }

        return allPicks.map(function(p) {
            var meta = CAT_META[p._displayCat] || CAT_META.stock;
            var ep = parseFloat(p.entryPrice) || 0;
            var cp = parseFloat(p.currentPrice) || ep;
            var stop = parseFloat(p.stopPrice) || 0;
            var target = parseFloat(p.targetPrice) || 0;
            var rr = parseFloat(p.riskReward) || 0;
            var ret = ep > 0 ? (cp - ep) / ep * 100 : 0;
            var alloc = parseFloat(p.allocation) || 0;
            var pnlDollar = alloc > 0 && ep > 0 ? alloc * ((cp - ep) / ep) : 0;
            var days = daysHeld(p.entryDate);
            var mh = p.maxHoldDays || '?';

            // Progress bar: 0% = stop, 100% = target
            var progressPct = 50; // default center
            if (stop > 0 && target > 0 && target > stop) {
                progressPct = Math.max(0, Math.min(100, ((cp - stop) / (target - stop)) * 100));
            }
            var progressColor = progressPct > 60 ? '#22c55e' : progressPct > 30 ? '#f59e0b' : '#ef4444';

            // How far to stop vs target
            var distStop = stop > 0 && ep > 0 ? ((cp - stop) / cp * 100).toFixed(1) : '?';
            var distTarget = target > 0 && ep > 0 ? ((target - cp) / cp * 100).toFixed(1) : '?';

            // Multi-signal badge: check if _algoName signals convergence
            var retClass = ret >= 0 ? '#22c55e' : '#ef4444';
            var pnlClass = pnlDollar >= 0 ? '#22c55e' : '#ef4444';

            return '<tr style="font-size:12px;border-bottom:1px solid #0f0f1e;">' +
                // Symbol + category badge
                '<td style="padding:8px 6px;white-space:nowrap;">' +
                    '<strong style="color:#e0e0f0;font-size:13px">' + p.symbol + '</strong>' +
                    '<div><span style="background:' + meta.color + '22;color:' + meta.color + ';border-radius:4px;font-size:9px;padding:1px 5px;">' + meta.label + '</span></div>' +
                '</td>' +
                // Algo name
                '<td style="padding:8px 6px;color:#8888aa;max-width:120px;font-size:11px;">' + p._algoName + '</td>' +
                // Entry → Current price
                '<td style="padding:8px 6px;white-space:nowrap;">' +
                    '<div style="color:#8888aa;font-size:10px">entry</div>' +
                    '<div>' + fmtPrice(ep) + '</div>' +
                    '<div style="color:#e0e0f0">' + fmtPrice(cp) + '</div>' +
                '</td>' +
                // P&L %
                '<td style="padding:8px 6px;text-align:right;font-weight:700;color:' + retClass + '">' +
                    (ret >= 0 ? '+' : '') + ret.toFixed(2) + '%' +
                    '<div style="color:' + pnlClass + ';font-size:10px;font-weight:400">' +
                        (pnlDollar >= 0 ? '+' : '') + '$' + Math.abs(pnlDollar).toFixed(0) +
                    '</div>' +
                '</td>' +
                // Stop / Target / R:R
                '<td style="padding:8px 6px;white-space:nowrap;">' +
                    '<div style="color:#ef4444;font-size:10px">stop ' + fmtPrice(stop) + ' <span style="color:#6b6b8a">(-' + distStop + '%)</span></div>' +
                    '<div style="color:#22c55e;font-size:10px">tgt  ' + fmtPrice(target) + ' <span style="color:#6b6b8a">(+' + distTarget + '%)</span></div>' +
                    '<div style="color:#f59e0b;font-size:10px;font-weight:600">R:R ' + rr + ':1</div>' +
                '</td>' +
                // Progress bar: stop → target
                '<td style="padding:8px 10px;min-width:80px">' +
                    '<div style="font-size:9px;color:#555;margin-bottom:2px">stop — target</div>' +
                    '<div style="background:#1a1a2e;border-radius:3px;height:6px;width:80px;overflow:hidden;">' +
                        '<div style="width:' + progressPct.toFixed(0) + '%;height:100%;background:' + progressColor + ';border-radius:3px;transition:width 0.4s"></div>' +
                    '</div>' +
                    '<div style="font-size:9px;color:#555;margin-top:2px">' + progressPct.toFixed(0) + '% to target</div>' +
                '</td>' +
                // Days held / max
                '<td style="padding:8px 6px;text-align:center;color:#8888aa;font-size:11px">' + days + 'd<div style="font-size:9px">of ' + mh + 'd</div></td>' +
                // Allocation
                '<td style="padding:8px 6px;text-align:right;color:#8888aa;font-size:11px">$' + alloc.toFixed(0) + '</td>' +
                // Entry thesis
                '<td style="padding:8px 6px;color:#f59e0b;font-size:11px;max-width:220px;line-height:1.4">' + (p.reason || '--') + '</td>' +
            '</tr>';
        }).join('');
    }

    // -------------------------------------------------------------------------
    // Render: Signal convergence — symbols with 2+ algo agreement
    // -------------------------------------------------------------------------
    function renderConvergence(convergence) {
        if (!convergence.length) {
            return '<div style="padding:12px;color:#555;font-size:12px;">No convergence signals yet. Appears when 2+ algorithms independently signal the same symbol simultaneously.</div>';
        }

        return convergence.map(function(cv) {
            var ep = cv.picks[0].entry || 0;
            var cp = cv.picks[0].cur || ep;
            var ret = ep > 0 ? ((cp - ep) / ep * 100) : 0;
            var cats = [...new Set(cv.picks.map(function(p) { return p.symCat; }))];
            var catLabel = cats.map(function(c) { return CAT_META[c] ? CAT_META[c].label : c; }).join('/');
            var strength = cv.picks.length >= 4 ? 'EXTREME' : cv.picks.length >= 3 ? 'HIGH' : 'MODERATE';
            var strengthColor = cv.picks.length >= 4 ? '#ef4444' : cv.picks.length >= 3 ? '#f59e0b' : '#3b82f6';

            return '<div style="background:rgba(30,30,60,0.6);border:1px solid #2a2a4e;border-radius:8px;padding:12px 14px;margin-bottom:8px;">' +
                '<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">' +
                    '<strong style="font-size:15px;color:#e0e0f0">' + cv.symbol + '</strong>' +
                    '<span style="background:' + strengthColor + '22;color:' + strengthColor + ';border:1px solid ' + strengthColor + '44;border-radius:4px;font-size:10px;padding:1px 7px;font-weight:700">' + strength + ' CONVICTION</span>' +
                    '<span style="color:#555;font-size:11px">' + cv.picks.length + ' algos · ' + catLabel + '</span>' +
                    '<span style="margin-left:auto;font-size:12px;font-weight:700;color:' + (ret >= 0 ? '#22c55e' : '#ef4444') + '">' + (ret >= 0 ? '+' : '') + ret.toFixed(2) + '%</span>' +
                '</div>' +
                '<div style="display:flex;flex-wrap:wrap;gap:6px;">' +
                    cv.picks.map(function(p) {
                        return '<div style="background:#12122a;border-radius:6px;padding:5px 9px;font-size:11px;">' +
                            '<div style="color:#8888aa">' + p.algo + '</div>' +
                            '<div style="color:#f59e0b;font-size:10px;margin-top:2px">' + (p.reason || '').substring(0, 55) + '</div>' +
                        '</div>';
                    }).join('') +
                '</div>' +
            '</div>';
        }).join('');
    }

    // -------------------------------------------------------------------------
    // Render: Pure algo performance across all asset classes
    // -------------------------------------------------------------------------
    function renderAlgoPerformanceTable(algorithms) {
        var cats = ['crypto', 'stock', 'meme', 'penny', 'forex'];
        var rows = '';

        cats.forEach(function(cat) {
            var catAlgos = algorithms
                .filter(function(a) { return a.category === cat; })
                .sort(function(a, b) {
                    // Sort: has open picks first, then by return
                    var a_active = (a.activePicks || []).length;
                    var b_active = (b.activePicks || []).length;
                    if (a_active !== b_active) return b_active - a_active;
                    return (b.totalReturn || 0) - (a.totalReturn || 0);
                });

            if (!catAlgos.length) return;
            var meta = CAT_META[cat];

            // Category header row
            rows += '<tr><td colspan="8" style="padding:10px 8px 4px;font-size:10px;text-transform:uppercase;' +
                'letter-spacing:1.5px;color:' + meta.color + ';border-top:1px solid #1a1a2e;background:#09091a">' +
                meta.icon + '  ' + meta.label + ' (' + catAlgos.length + ' algos)' +
                '</td></tr>';

            catAlgos.forEach(function(algo) {
                var ret = algo.totalReturn || 0;
                var n_open = (algo.activePicks || []).length;
                var n_closed = (algo.closedPicks || []).length;
                var drought = algo.droughtScans || 0;
                var val = algo.currentValue || 10000;
                var wr = algo.winRate;
                var sharpe = algo.sharpe;
                var status = algo.status || 'READY';
                var retColor = ret > 0 ? '#22c55e' : ret < 0 ? '#ef4444' : '#8888aa';
                var droughtColor = drought > 10 ? '#ef4444' : drought > 5 ? '#f59e0b' : '#555';
                var hasActive = n_open > 0;
                var tier = algo.tier || 'SCOUT';
                var tierColor = tier === 'TIER_1' ? '#f59e0b' : '#6b7280';

                // Compute open P&L for this algo specifically
                var openPnl = 0;
                (algo.activePicks || []).forEach(function(p) {
                    var ep = parseFloat(p.entryPrice) || 0;
                    var cp = parseFloat(p.currentPrice) || ep;
                    var alloc = parseFloat(p.allocation) || 0;
                    if (ep > 0 && alloc > 0) openPnl += alloc * ((cp - ep) / ep);
                });
                var openPnlStr = n_open > 0
                    ? '<span style="color:' + (openPnl >= 0 ? '#22c55e' : '#ef4444') + ';font-size:10px">' +
                      (openPnl >= 0 ? '+' : '') + '$' + Math.abs(openPnl).toFixed(0) + '</span>'
                    : '<span style="color:#333;font-size:10px">—</span>';

                rows += '<tr style="font-size:12px;' + (hasActive ? 'background:rgba(34,197,94,0.03);' : '') + '">' +
                    '<td style="padding:7px 8px;white-space:nowrap;">' +
                        '<span style="color:' + tierColor + ';font-size:9px;margin-right:4px">' + (tier === 'TIER_1' ? 'T1' : 'SC') + '</span>' +
                        '<span style="color:#c0c0d8">' + algo.name + '</span>' +
                        (hasActive ? ' <span style="background:#22c55e22;color:#22c55e;border-radius:3px;font-size:9px;padding:0 4px;">ACTIVE</span>' : '') +
                    '</td>' +
                    '<td style="padding:7px 8px;color:' + retColor + ';font-weight:700;text-align:right">' +
                        (ret >= 0 ? '+' : '') + ret.toFixed(2) + '%' +
                    '</td>' +
                    '<td style="padding:7px 8px;text-align:right">' + openPnlStr + '</td>' +
                    '<td style="padding:7px 8px;color:#8888aa;text-align:center">' + n_open + '</td>' +
                    '<td style="padding:7px 8px;color:#555;text-align:center">' + n_closed + '</td>' +
                    '<td style="padding:7px 8px;color:' + droughtColor + ';text-align:center">' + drought + '</td>' +
                    '<td style="padding:7px 8px;color:#e0e0f0;text-align:right">$' + val.toLocaleString(undefined, {maximumFractionDigits: 0}) + '</td>' +
                    '<td style="padding:7px 8px;color:#555;font-size:10px">' + status + '</td>' +
                '</tr>';
            });
        });

        return rows;
    }

    // -------------------------------------------------------------------------
    // Main render — injects into #alphaProofPanel
    // -------------------------------------------------------------------------
    function renderAlphaProof(data) {
        var container = document.getElementById('alphaProofPanel');
        if (!container) return;
        if (!data || !data.algorithms) {
            container.innerHTML = '<div style="color:#555;padding:20px;font-size:13px">Loading alpha data...</div>';
            return;
        }

        var algorithms = data.algorithms;
        var catStats = buildCatStats(algorithms);
        var convergence = buildConvergence(algorithms);

        // Count totals
        var totalOpen = algorithms.reduce(function(s, a) { return s + (a.activePicks || []).length; }, 0);
        var totalClosed = algorithms.reduce(function(s, a) { return s + (a.closedPicks || []).length; }, 0);
        var totalDeployed = Object.values(catStats).reduce(function(s, c) { return s + c.deployedCapital; }, 0);
        var totalOpenPnl = Object.values(catStats).reduce(function(s, c) { return s + c.openPnl; }, 0);
        var openPnlPct = totalDeployed > 0 ? (totalOpenPnl / totalDeployed * 100) : 0;
        var pnlColor = openPnlPct >= 0 ? '#22c55e' : '#ef4444';
        var pnlSign = openPnlPct >= 0 ? '+' : '';
        var lastUpdated = data.competition ? (data.competition.lastUpdated || '').slice(0, 16) : '';

        var activeCatFilter = 'all';

        container.innerHTML =

            // ---- Top summary bar ----
            '<div style="display:flex;flex-wrap:wrap;gap:12px;align-items:center;padding:10px 0 16px;border-bottom:1px solid #1a1a2e;margin-bottom:16px">' +
                '<div style="font-size:11px;color:#555;text-transform:uppercase;letter-spacing:1px">Live Forward Test</div>' +
                '<div style="display:flex;gap:20px;flex-wrap:wrap">' +
                    '<div><span style="color:#555;font-size:11px">Open Picks: </span><strong style="color:#e0e0f0">' + totalOpen + '</strong></div>' +
                    '<div><span style="color:#555;font-size:11px">Closed: </span><strong style="color:#e0e0f0">' + totalClosed + '</strong></div>' +
                    '<div><span style="color:#555;font-size:11px">Capital Deployed: </span><strong style="color:#e0e0f0">$' + totalDeployed.toLocaleString(undefined, {maximumFractionDigits: 0}) + '</strong></div>' +
                    '<div><span style="color:#555;font-size:11px">Open P&L: </span><strong style="color:' + pnlColor + '">' + pnlSign + openPnlPct.toFixed(2) + '% (' + pnlSign + '$' + Math.abs(totalOpenPnl).toFixed(0) + ')</strong></div>' +
                    '<div><span style="color:#555;font-size:11px">Convergence: </span><strong style="color:' + (convergence.length > 0 ? '#f59e0b' : '#555') + '">' + convergence.length + ' symbol' + (convergence.length !== 1 ? 's' : '') + '</strong></div>' +
                '</div>' +
                '<div style="margin-left:auto;font-size:10px;color:#555">as of ' + lastUpdated + ' UTC</div>' +
            '</div>' +

            // ---- Asset class cards ----
            '<div style="margin-bottom:20px;">' +
                '<div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#555;margin-bottom:10px">Performance by Asset Class</div>' +
                '<div style="display:flex;flex-wrap:wrap;gap:10px">' + renderCatCards(catStats) + '</div>' +
            '</div>' +

            // ---- Signal Convergence ----
            (convergence.length > 0 ? (
                '<div style="margin-bottom:20px;">' +
                    '<div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#f59e0b;margin-bottom:10px">' +
                        '⚡ Signal Convergence — ' + convergence.length + ' symbol' + (convergence.length !== 1 ? 's' : '') + ' targeted by multiple algorithms (high conviction)' +
                    '</div>' +
                    renderConvergence(convergence) +
                '</div>'
            ) : '') +

            // ---- Open picks with Risk/Reward ----
            '<div style="margin-bottom:20px;">' +
                '<div style="display:flex;align-items:center;gap:12px;margin-bottom:10px">' +
                    '<div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#555">Open Picks — Risk/Reward & Thesis</div>' +
                    '<div id="alphaPickFilter" style="display:flex;gap:6px;flex-wrap:wrap">' +
                        '<button onclick="alphaFilterPicks(\'all\',this)" style="background:#3b82f622;color:#3b82f6;border:1px solid #3b82f644;border-radius:4px;padding:2px 9px;font-size:10px;cursor:pointer" class="apf-active">All</button>' +
                        ['crypto','stock','meme','penny','forex'].map(function(c) {
                            var m = CAT_META[c];
                            return '<button onclick="alphaFilterPicks(\'' + c + '\',this)" style="background:' + m.color + '22;color:' + m.color + ';border:1px solid ' + m.color + '44;border-radius:4px;padding:2px 9px;font-size:10px;cursor:pointer">' + m.icon + ' ' + m.label + '</button>';
                        }).join('') +
                    '</div>' +
                '</div>' +
                '<div style="overflow-x:auto">' +
                    '<table style="width:100%;border-collapse:collapse;min-width:800px">' +
                        '<thead><tr style="color:#555;font-size:10px;text-transform:uppercase;letter-spacing:0.5px;border-bottom:1px solid #1a1a2e">' +
                            '<th style="text-align:left;padding:6px">Symbol</th>' +
                            '<th style="text-align:left;padding:6px">Algorithm</th>' +
                            '<th style="text-align:left;padding:6px">Price</th>' +
                            '<th style="text-align:right;padding:6px">P&L</th>' +
                            '<th style="text-align:left;padding:6px">Stop / Target / R:R</th>' +
                            '<th style="text-align:left;padding:6px">Progress</th>' +
                            '<th style="text-align:center;padding:6px">Held</th>' +
                            '<th style="text-align:right;padding:6px">Alloc</th>' +
                            '<th style="text-align:left;padding:6px">Entry Thesis</th>' +
                        '</tr></thead>' +
                        '<tbody id="alphaPicksBody">' + renderPicksTable(catStats, 'all') + '</tbody>' +
                    '</table>' +
                '</div>' +
            '</div>' +

            // ---- Pure algo performance table ----
            '<div>' +
                '<div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#555;margin-bottom:10px">Algorithm Performance — All Asset Classes</div>' +
                '<div style="overflow-x:auto">' +
                    '<table style="width:100%;border-collapse:collapse;min-width:600px">' +
                        '<thead><tr style="color:#555;font-size:10px;text-transform:uppercase;letter-spacing:0.5px;border-bottom:1px solid #1a1a2e">' +
                            '<th style="text-align:left;padding:6px">Algorithm</th>' +
                            '<th style="text-align:right;padding:6px">Return</th>' +
                            '<th style="text-align:right;padding:6px">Open P&L</th>' +
                            '<th style="text-align:center;padding:6px">Open</th>' +
                            '<th style="text-align:center;padding:6px">Closed</th>' +
                            '<th style="text-align:center;padding:6px">Drought</th>' +
                            '<th style="text-align:right;padding:6px">Value</th>' +
                            '<th style="text-align:left;padding:6px">Status</th>' +
                        '</tr></thead>' +
                        '<tbody>' + renderAlgoPerformanceTable(algorithms) + '</tbody>' +
                    '</table>' +
                '</div>' +
            '</div>';

        // Store catStats for filter callback
        container._catStats = catStats;
    }

    // Global filter function for the pick filter buttons
    window.alphaFilterPicks = function(cat, btn) {
        // Update active button
        var panel = document.getElementById('alphaProofPanel');
        if (!panel) return;
        panel.querySelectorAll('#alphaPickFilter button').forEach(function(b) {
            b.classList.remove('apf-active');
            b.style.fontWeight = '';
        });
        if (btn) { btn.classList.add('apf-active'); btn.style.fontWeight = '700'; }

        var body = document.getElementById('alphaPicksBody');
        if (body && panel._catStats) {
            body.innerHTML = renderPicksTable(panel._catStats, cat);
        }
    };

    // -------------------------------------------------------------------------
    // Hook into dashboard data load cycle
    // -------------------------------------------------------------------------
    var _origLoad = window.loadDashboardData;
    function runAlphaProof() {
        if (window.currentData) {
            renderAlphaProof(window.currentData);
        }
    }

    // Poll until currentData is available, then render; re-render on every refresh
    var _checkInterval = setInterval(function() {
        if (window.currentData) {
            clearInterval(_checkInterval);
            renderAlphaProof(window.currentData);
            // Re-render every 60s (dashboard refreshes every 30s, we piggyback)
            setInterval(function() {
                if (window.currentData) renderAlphaProof(window.currentData);
            }, 60000);
        }
    }, 500);

})();
