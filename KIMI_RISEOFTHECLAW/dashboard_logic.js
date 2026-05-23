// ─── Dynamic Portfolio Logic: dashboard_logic.js v2 ───
// Loads FORWARD TEST picks from the live scanner signals

function classifySym(s) {
    if (s.indexOf('USD=X') !== -1) return 'forex';
    if (s.length > 4 && s.substr(s.length - 4) === '-USD') return 'crypto';
    return 'stock';
}
function marketForCat(cat) {
    if (cat === 'crypto') return '24/7';
    if (cat === 'forex') return 'FX 24/5';
    return 'NYSE 9:30-4 ET';
}

// ──────── Load portfolio from real scanner signals ────────
function loadPortfolio() {
    // Primary: forward_signals_current.json (the real scanner output)
    return fetch('data/forward_signals_current.json?t=' + Date.now())
        .then(function (resp) {
            if (!resp.ok) throw new Error('HTTP ' + resp.status);
            return resp.json();
        })
        .then(function (data) {
            var allSignals = data.signals || [];
            var timestamp = data.timestamp_est || data.timestamp || '';
            var strategies = data.strategy_types || [];

            // Filter: only BUY, STRONG_BUY, MILD_BUY, LONG_BTC signals
            var buySignals = allSignals.filter(function (s) {
                var d = (s.direction || '').toUpperCase();
                return d === 'BUY' || d === 'STRONG_BUY' || d === 'MILD_BUY' || d === 'LONG_BTC';
            });

            // Group by symbol — a symbol can have multiple strategies agreeing
            var bySymbol = {};
            buySignals.forEach(function (s) {
                if (!bySymbol[s.symbol]) bySymbol[s.symbol] = [];
                bySymbol[s.symbol].push(s);
            });

            var positions = [];
            var syms = Object.keys(bySymbol);
            syms.forEach(function (sym) {
                var picks = bySymbol[sym];
                var cat = classifySym(sym);
                var best = picks[0];
                // Use highest confidence signal as primary
                picks.forEach(function (p) {
                    if (p.confidence > best.confidence) best = p;
                });

                var algoNames = picks.map(function (p) { return p.signal_type; });
                var uniqueAlgos = [];
                var seen = {};
                algoNames.forEach(function (a) { if (!seen[a]) { seen[a] = true; uniqueAlgos.push(a); } });

                var ep = best.current_price || best.levels.entry;
                var tp = (best.levels && best.levels.take_profit) || 0;
                var sl = (best.levels && best.levels.stop_loss) || 0;

                // Calculate TP/SL percentages
                var tpPct = tp > 0 ? ((tp - ep) / ep * 100).toFixed(1) : (cat === 'crypto' ? '15' : cat === 'forex' ? '3' : '8');
                var slPct = sl > 0 ? ((ep - sl) / ep * 100).toFixed(1) : (cat === 'crypto' ? '10' : cat === 'forex' ? '2' : '5');

                // Fallback TP/SL if not set
                if (!tp || tp === 0) tp = ep * (1 + parseFloat(tpPct) / 100);
                if (!sl || sl === 0) sl = ep * (1 - parseFloat(slPct) / 100);

                // Build audit trail from each signal
                var audit = picks.map(function (p) {
                    return {
                        time: p.timestamp || timestamp,
                        type: p.direction,
                        strategy: p.signal_type,
                        methodology: p.methodology || '',
                        confidence: p.confidence,
                        reason: p.reason || '',
                        proven_wr: p.proven_live_wr || p.recent_performance ?
                            (p.proven_live_wr || (p.recent_performance ? p.recent_performance.wr_90d + '% (90d)' : 'N/A')) : 'N/A',
                        indicators: p.indicators || {},
                        rr: (p.levels && p.levels.risk_reward) || 0,
                        review_date: p.review_date || '',
                        max_hold: p.max_hold_days || 0,
                        performance: p.recent_performance || null
                    };
                });

                // Strength label
                var strength = picks.length >= 3 ? 'STRONG' : picks.length === 2 ? 'MODERATE' : 'SINGLE';
                var strengthColor = picks.length >= 3 ? 'var(--green)' : picks.length === 2 ? 'var(--gold)' : 'var(--text2)';
                var avgConf = Math.round(picks.reduce(function (s, p) { return s + p.confidence; }, 0) / picks.length);

                var reason = picks.length + ' algorithm' + (picks.length > 1 ? 's' : '') + ' say ' + best.direction;
                reason += ' | Avg confidence: ' + avgConf + '%';
                reason += ' | ' + uniqueAlgos.join(' + ');

                positions.push({
                    symbol: sym,
                    name: NAMES[sym] || best.name || sym,
                    icon: ICONS[sym] || '\ud83d\udcca',
                    direction: best.direction === 'LONG_BTC' ? 'LONG' : 'LONG',
                    category: cat,
                    market: marketForCat(cat),
                    entry_price: ep,
                    invested: 2000,
                    tp: tp,
                    sl: sl,
                    tp_pct: parseFloat(tpPct),
                    sl_pct: parseFloat(slPct),
                    reason: reason,
                    strategies: uniqueAlgos,
                    coingecko_id: CG_IDS[sym] || null,
                    binance: BINANCE_IDS[sym] || null,
                    audit: audit,
                    signalCount: picks.length,
                    avgConfidence: avgConf,
                    strength: strength,
                    strengthColor: strengthColor,
                    bestDirection: best.direction,
                    timestamp: timestamp,
                    riskReward: (best.levels && best.levels.risk_reward) || 0,
                    isForwardTest: true
                });
            });

            // Sort: most signals first, then confidence
            positions.sort(function (a, b) {
                if (b.signalCount !== a.signalCount) return b.signalCount - a.signalCount;
                return b.avgConfidence - a.avgConfidence;
            });

            PORTFOLIO.positions = positions;
            PORTFOLIO.starting_capital = positions.length * 2000;
            PORTFOLIO.scan_timestamp = timestamp;
            PORTFOLIO.total_scanned = data.total_signals || 0;
            PORTFOLIO.active_signals = data.active_signals || 0;
            PORTFOLIO.assets_scanned = (data.assets_scanned || []).length;
            PORTFOLIO.strategy_count = strategies.length;

            // Update counts
            var el = function (id) { return document.getElementById(id); };
            if (el('cnt-all')) el('cnt-all').textContent = '(' + positions.length + ')';
            if (el('cnt-crypto')) el('cnt-crypto').textContent = '(' + positions.filter(function (p) { return p.category === 'crypto'; }).length + ')';
            if (el('cnt-stock')) el('cnt-stock').textContent = '(' + positions.filter(function (p) { return p.category === 'stock'; }).length + ')';
            if (el('cnt-forex')) {
                var fc = positions.filter(function (p) { return p.category === 'forex'; }).length;
                el('cnt-forex').textContent = fc ? '(' + fc + ')' : '';
            }

            console.log('Loaded ' + positions.length + ' forward test positions from ' + allSignals.length + ' total signals (' + buySignals.length + ' bullish)');
        })
        .catch(function (e) {
            console.error('Failed to load portfolio:', e);
            document.getElementById('positions').innerHTML = '<p style="text-align:center;color:var(--red);padding:40px">\u26a0 Failed to load scanner data. <br><span style="font-size:0.7rem;color:var(--text2)">Error: ' + e.message + '</span></p>';
        });
}

function fmt(p) {
    if (p >= 1000) return '$' + p.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (p >= 1) return '$' + p.toFixed(2);
    return '$' + p.toFixed(6);
}

// Track price sources globally
var PRICE_SOURCES = {};
var PRICE_API_LOG = [];

// ──────── MULTI-API PRICE CASCADE ────────
// Layer 1: CoinGecko (free, no key)
// Layer 2: Binance (free, no key, very reliable)
// Layer 3: CryptoCompare (API key)
// Layer 4: PHP server-side scraper (absolute last resort)

function fetchLivePrices() {
    var prices = {};
    PRICE_SOURCES = {};
    PRICE_API_LOG = [];

    // Mark stock positions upfront — no live API for stocks
    PORTFOLIO.positions.forEach(function (pos) {
        if (pos.category === 'stock') {
            prices[pos.symbol] = pos.entry_price;
            PRICE_SOURCES[pos.symbol] = 'no_stock_api';
        }
    });

    var cryptoPositions = PORTFOLIO.positions.filter(function (p) { return p.category === 'crypto'; });
    if (cryptoPositions.length === 0) {
        PRICE_API_LOG.push({ api: 'none', status: 'skip', msg: 'No crypto positions' });
        return Promise.resolve(prices);
    }

    // Layer 1: CoinGecko
    return fetchCoinGecko(prices, cryptoPositions)
        .then(function () {
            // Layer 2: Binance for any missing crypto
            var missing = cryptoPositions.filter(function (p) { return !prices[p.symbol]; });
            if (missing.length > 0) return fetchBinance(prices, missing);
        })
        .then(function () {
            // Layer 3: CryptoCompare for any still missing
            var missing = cryptoPositions.filter(function (p) { return !prices[p.symbol]; });
            if (missing.length > 0) return fetchCryptoCompare(prices, missing);
        })
        .then(function () {
            // Layer 4: PHP scraper fallback for any still missing
            var missing = cryptoPositions.filter(function (p) { return !prices[p.symbol]; });
            if (missing.length > 0) return fetchPHPScraper(prices, missing);
        })
        .then(function () {
            // Final fallback: use entry price for anything still missing
            PORTFOLIO.positions.forEach(function (pos) {
                if (!prices[pos.symbol]) {
                    prices[pos.symbol] = pos.entry_price;
                    PRICE_SOURCES[pos.symbol] = PRICE_SOURCES[pos.symbol] || 'all_apis_failed';
                }
            });
            var liveCount = Object.keys(PRICE_SOURCES).filter(function (k) {
                return PRICE_SOURCES[k] !== 'no_stock_api' && PRICE_SOURCES[k] !== 'entry' && PRICE_SOURCES[k] !== 'all_apis_failed';
            }).length;
            console.log('Price cascade complete: ' + liveCount + ' live prices. Sources:', JSON.stringify(PRICE_SOURCES));
            console.log('API log:', PRICE_API_LOG);
            return prices;
        });
}

// ─── Layer 1: CoinGecko ───
function fetchCoinGecko(prices, positions) {
    var ids = positions.filter(function (p) { return p.coingecko_id; }).map(function (p) { return p.coingecko_id; }).join(',');
    if (!ids) return Promise.resolve();
    return fetch('https://api.coingecko.com/api/v3/simple/price?ids=' + ids + '&vs_currencies=usd')
        .then(function (r) {
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
        })
        .then(function (data) {
            var count = 0;
            positions.forEach(function (pos) {
                if (pos.coingecko_id && data[pos.coingecko_id] && data[pos.coingecko_id].usd) {
                    prices[pos.symbol] = data[pos.coingecko_id].usd;
                    PRICE_SOURCES[pos.symbol] = 'coingecko';
                    count++;
                }
            });
            PRICE_API_LOG.push({ api: 'CoinGecko', status: 'ok', count: count });
            console.log('✅ CoinGecko: ' + count + ' prices');
        })
        .catch(function (err) {
            PRICE_API_LOG.push({ api: 'CoinGecko', status: 'failed', error: err.message });
            console.warn('❌ CoinGecko failed:', err.message, '→ trying Binance...');
        });
}

// ─── Layer 2: Binance (free, no key, very reliable) ───
function fetchBinance(prices, positions) {
    var symbols = positions.filter(function (p) { return BINANCE_IDS[p.symbol]; }).map(function (p) { return BINANCE_IDS[p.symbol]; });
    if (symbols.length === 0) return Promise.resolve();
    var url = 'https://api.binance.com/api/v3/ticker/price?symbols=[' + symbols.map(function (s) { return '"' + s + '"'; }).join(',') + ']';
    return fetch(url)
        .then(function (r) {
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
        })
        .then(function (data) {
            var count = 0;
            var binanceMap = {};
            data.forEach(function (d) { binanceMap[d.symbol] = parseFloat(d.price); });
            positions.forEach(function (pos) {
                var bId = BINANCE_IDS[pos.symbol];
                if (bId && binanceMap[bId] && !prices[pos.symbol]) {
                    prices[pos.symbol] = binanceMap[bId];
                    PRICE_SOURCES[pos.symbol] = 'binance';
                    count++;
                }
            });
            PRICE_API_LOG.push({ api: 'Binance', status: 'ok', count: count });
            console.log('✅ Binance: ' + count + ' prices');
        })
        .catch(function (err) {
            PRICE_API_LOG.push({ api: 'Binance', status: 'failed', error: err.message });
            console.warn('❌ Binance failed:', err.message, '→ trying CryptoCompare...');
        });
}

// ─── Layer 3: CryptoCompare (with API key) ───
function fetchCryptoCompare(prices, positions) {
    var ccKey = 'qb8ddikglknpseumlz4w';
    var syms = positions.filter(function (p) { return CC_SYMS[p.symbol]; }).map(function (p) { return CC_SYMS[p.symbol]; });
    if (syms.length === 0) return Promise.resolve();
    var url = 'https://min-api.cryptocompare.com/data/pricemulti?fsyms=' + syms.join(',') + '&tsyms=USD&api_key=' + ccKey;
    return fetch(url)
        .then(function (r) {
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
        })
        .then(function (data) {
            var count = 0;
            positions.forEach(function (pos) {
                var cc = CC_SYMS[pos.symbol];
                if (cc && data[cc] && data[cc].USD && !prices[pos.symbol]) {
                    prices[pos.symbol] = data[cc].USD;
                    PRICE_SOURCES[pos.symbol] = 'cryptocompare';
                    count++;
                }
            });
            PRICE_API_LOG.push({ api: 'CryptoCompare', status: 'ok', count: count });
            console.log('✅ CryptoCompare: ' + count + ' prices');
        })
        .catch(function (err) {
            PRICE_API_LOG.push({ api: 'CryptoCompare', status: 'failed', error: err.message });
            console.warn('❌ CryptoCompare failed:', err.message, '→ trying PHP scraper...');
        });
}

// ─── Layer 4: Server-side PHP scraper (absolute last resort) ───
function fetchPHPScraper(prices, positions) {
    var syms = positions.filter(function (p) { return !prices[p.symbol]; }).map(function (p) { return p.symbol; });
    if (syms.length === 0) return Promise.resolve();
    var url = '/KIMI_RISEOFTHECLAW/price_scraper.php?symbols=' + encodeURIComponent(syms.join(','));
    return fetch(url)
        .then(function (r) {
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
        })
        .then(function (data) {
            var count = 0;
            if (data && data.prices) {
                positions.forEach(function (pos) {
                    if (data.prices[pos.symbol] && !prices[pos.symbol]) {
                        prices[pos.symbol] = data.prices[pos.symbol];
                        PRICE_SOURCES[pos.symbol] = 'php_scraper';
                        count++;
                    }
                });
            }
            PRICE_API_LOG.push({ api: 'PHP Scraper', status: 'ok', count: count });
            console.log('✅ PHP Scraper: ' + count + ' prices');
        })
        .catch(function (err) {
            PRICE_API_LOG.push({ api: 'PHP Scraper', status: 'failed', error: err.message });
            console.warn('❌ PHP Scraper failed:', err.message, '→ using entry prices');
        });
}

// ──────── Generate dynamic commentary ────────
function generateCommentary(posData, totalPnl, winners, losers) {
    var lines = [];
    var now = new Date();
    var hour = now.getHours();
    var isWeekend = now.getDay() === 0 || now.getDay() === 6;
    var btcPos = posData.find(function (p) { return p.symbol === 'BTC-USD'; });
    var cryptoCount = posData.filter(function (p) { return p.category === 'crypto'; }).length;
    var stockCount = posData.filter(function (p) { return p.category === 'stock'; }).length;
    var liveAPIs = ['coingecko', 'binance', 'cryptocompare', 'php_scraper'];
    var livePrices = posData.filter(function (p) { return liveAPIs.indexOf(PRICE_SOURCES[p.symbol]) !== -1; }).length;
    var stalePrices = posData.length - livePrices;

    // Market status
    if (isWeekend) {
        lines.push('\ud83d\udfe1 <strong>Weekend mode</strong> \u2014 Stock markets closed. Crypto markets active 24/7.');
    } else if (hour < 9 || hour >= 16) {
        lines.push('\ud83c\udf19 <strong>After hours</strong> \u2014 US stock markets closed until 9:30 AM ET. Crypto is live.');
    } else {
        lines.push('\ud83d\udfe2 <strong>Markets open</strong> \u2014 All positions being tracked with live data.');
    }

    // Price source transparency
    // Build live source breakdown
    var cgC = posData.filter(function (p) { return PRICE_SOURCES[p.symbol] === 'coingecko'; }).length;
    var bnC = posData.filter(function (p) { return PRICE_SOURCES[p.symbol] === 'binance'; }).length;
    var ccC = posData.filter(function (p) { return PRICE_SOURCES[p.symbol] === 'cryptocompare'; }).length;
    var phC = posData.filter(function (p) { return PRICE_SOURCES[p.symbol] === 'php_scraper'; }).length;
    var srcParts = [];
    if (cgC > 0) srcParts.push(cgC + ' via CoinGecko');
    if (bnC > 0) srcParts.push(bnC + ' via Binance');
    if (ccC > 0) srcParts.push(ccC + ' via CryptoCompare');
    if (phC > 0) srcParts.push(phC + ' via PHP Scraper');
    if (livePrices > 0 && stalePrices > 0) {
        lines.push('\ud83d\udce1 <strong>Live prices:</strong> ' + livePrices + ' positions via API cascade (' + srcParts.join(', ') + '). ' + stalePrices + ' stock positions use entry price (no free stock API).');
    } else if (livePrices > 0) {
        lines.push('\ud83d\udce1 <strong>All ' + livePrices + ' prices live</strong> via API cascade (' + srcParts.join(', ') + ').');
    } else {
        lines.push('\u26a0\ufe0f <strong>All 4 price APIs failed</strong> (CoinGecko, Binance, CryptoCompare, PHP Scraper). P&L at $0. Auto-retrying in 30s.');
    }

    // P&L commentary
    if (totalPnl > 0) {
        lines.push('\u2705 Portfolio is UP \u2014 ' + winners + ' winning position' + (winners !== 1 ? 's' : '') + '.');
    } else if (totalPnl < -50) {
        lines.push('\u26a0\ufe0f Portfolio currently down. These are forward test signals \u2014 no real money at risk.');
    } else if (winners === 0 && losers === 0) {
        lines.push('\u23f3 <strong>P&L is $0</strong> \u2014 This means prices haven\u2019t moved since the signal was generated, OR the live price feed hasn\u2019t loaded yet. Crypto prices update every 30 seconds via CoinGecko. Stock prices require a paid API (not yet integrated).');
    } else {
        lines.push('\u23f3 Positions recently opened \u2014 watching for price movement.');
    }

    // BTC specific
    if (btcPos) {
        var btcPnl = btcPos.pnlPct || 0;
        if (btcPnl < -5) {
            lines.push('\ud83d\udcca BTC is down ' + Math.abs(btcPnl).toFixed(1) + '% \u2014 broader crypto may follow.');
        } else if (btcPnl > 5) {
            lines.push('\ud83d\ude80 BTC is up ' + btcPnl.toFixed(1) + '% \u2014 bullish momentum could lift altcoins.');
        }
    }

    // Signal strength
    var strongPicks = posData.filter(function (p) { return p.signalCount >= 3; });
    if (strongPicks.length > 0) {
        lines.push('\ud83d\udcaa ' + strongPicks.length + ' position' + (strongPicks.length > 1 ? 's have' : ' has') + ' 3+ algorithms agreeing \u2014 highest conviction picks.');
    }

    // Scan info
    if (PORTFOLIO.scan_timestamp) {
        lines.push('\ud83d\udd0d Last scan: ' + PORTFOLIO.scan_timestamp + ' \u2014 ' + PORTFOLIO.total_scanned + ' signals across ' + PORTFOLIO.assets_scanned + ' assets from ' + PORTFOLIO.strategy_count + ' strategies.');
    }

    return lines;
}

// ──────── Render ────────
function render(prices) {
    if (!PORTFOLIO.positions.length) {
        document.getElementById('positions').innerHTML = '<p style="text-align:center;color:var(--text2);padding:40px">\u23f3 No active bullish signals detected by the scanner right now. <br><span style="font-size:0.7rem;opacity:0.6">Scanner runs automatically and will display picks when algorithms fire.</span></p>';
        return;
    }
    var totalPnl = 0, winners = 0, losers = 0;
    var posData = [];

    PORTFOLIO.positions.forEach(function (pos) {
        var current = prices[pos.symbol] || pos.entry_price;
        var pnlPct = (current - pos.entry_price) / pos.entry_price * 100;
        var pnlDollar = pos.invested * pnlPct / 100;
        totalPnl += pnlDollar;
        if (pnlPct > 0) winners++; else if (pnlPct < 0) losers++;
        var tpDist = (pos.tp - current) / current * 100;
        var slDist = (current - pos.sl) / current * 100;
        var status = pnlPct > 0.5 ? '\ud83d\udfe2 WINNING' : (pnlPct < -0.5 ? '\ud83d\udd34 BEHIND' : '\u26aa IN PLAY');
        if (current >= pos.tp) status = '\ud83c\udfc6 TP HIT!';
        if (current <= pos.sl) status = '\ud83d\udc80 SL HIT';
        var d = {};
        for (var k in pos) d[k] = pos[k];
        d.current = current; d.pnlPct = pnlPct; d.pnlDollar = pnlDollar; d.tpDist = tpDist; d.slDist = slDist; d.status = status;
        posData.push(d);
    });

    posData.sort(function (a, b) {
        if (b.signalCount !== a.signalCount) return b.signalCount - a.signalCount;
        return b.avgConfidence - a.avgConfidence;
    });

    var ret = totalPnl / PORTFOLIO.starting_capital * 100;

    // Stats row with tooltips
    var liveSources = ['coingecko', 'binance', 'cryptocompare', 'php_scraper'];
    var liveCount = PORTFOLIO.positions.filter(function (p) { return liveSources.indexOf(PRICE_SOURCES[p.symbol]) !== -1; }).length;
    var staleCount = PORTFOLIO.positions.length - liveCount;
    var pnlTip = 'Profit & Loss across all positions. Crypto prices come from a 4-layer API cascade (CoinGecko > Binance > CryptoCompare > PHP Scraper). Stocks: entry price only (no free stock API).';
    var retTip = 'Portfolio return %. Based on $2,000 hypothetical per position. Crypto P&L is real-time via multi-API cascade. Stock P&L needs a paid market data feed.';
    var winTip = 'Positions where current price > entry price. Click to filter.';
    var loseTip = 'Positions where current price < entry price. Click to filter.';
    var picksTip = PORTFOLIO.positions.length + ' bullish signals. ' + liveCount + ' have live prices via API cascade, ' + staleCount + ' use entry price.';
    var statsHtml = '';
    statsHtml += '<div class="stat-card clickable" onclick="setFilter(\'all\')" title="Total hypothetical portfolio value. Each position starts at $2,000.">';
    statsHtml += '<div class="label">Portfolio</div>';
    statsHtml += '<div class="value blue">$' + (PORTFOLIO.starting_capital + totalPnl).toLocaleString('en-US', { maximumFractionDigits: 0 }) + '</div>';
    statsHtml += '<div class="click-hint">click \u2192 show all</div></div>';
    statsHtml += '<div class="stat-card clickable" onclick="setFilter(\'all\')" title="' + pnlTip + '">';
    statsHtml += '<div class="label">P&amp;L</div>';
    statsHtml += '<div class="value ' + (totalPnl >= 0 ? 'green' : 'red') + '">' + (totalPnl >= 0 ? '+' : '') + '$' + totalPnl.toFixed(2) + '</div>';
    if (totalPnl === 0 && staleCount > 0) statsHtml += '<div style="font-size:0.55rem;color:var(--gold);margin-top:2px">\u26a0 ' + staleCount + ' picks lack live price</div>';
    statsHtml += '<div class="click-hint">click \u2192 show all</div></div>';
    statsHtml += '<div class="stat-card clickable" onclick="setFilter(\'all\')" title="' + retTip + '">';
    statsHtml += '<div class="label">Return</div>';
    statsHtml += '<div class="value ' + (ret >= 0 ? 'green' : 'red') + '">' + (ret >= 0 ? '+' : '') + ret.toFixed(2) + '%</div>';
    statsHtml += '<div class="click-hint">click \u2192 show all</div></div>';
    statsHtml += '<div class="stat-card clickable" onclick="setFilter(\'winning\')" title="' + winTip + '">';
    statsHtml += '<div class="label">Winners</div><div class="value green">' + winners + '</div>';
    statsHtml += '<div class="click-hint">click \u2192 filter</div></div>';
    statsHtml += '<div class="stat-card clickable" onclick="setFilter(\'losing\')" title="' + loseTip + '">';
    statsHtml += '<div class="label">Losers</div><div class="value red">' + losers + '</div>';
    statsHtml += '<div class="click-hint">click \u2192 filter</div></div>';
    statsHtml += '<div class="stat-card" title="' + picksTip + '">';
    statsHtml += '<div class="label">Active Picks</div><div class="value blue">' + PORTFOLIO.positions.length + '</div></div>';
    document.getElementById('stats-row').innerHTML = statsHtml;

    // Dynamic commentary
    var commentary = generateCommentary(posData, totalPnl, winners, losers);
    var commentaryDiv = document.getElementById('commentary');
    if (commentaryDiv) {
        var cHtml = '';
        commentary.forEach(function (line) {
            cHtml += '<div style="padding:4px 0;font-size:0.75rem;color:var(--text);line-height:1.5">' + line + '</div>';
        });
        commentaryDiv.innerHTML = cHtml;
    }

    document.getElementById('last-update').textContent = 'Last update: ' + new Date().toLocaleTimeString() + ' \u00b7 ' + PORTFOLIO.positions.length + ' forward test positions tracked';

    // Data transparency banner
    var transparencyDiv = document.getElementById('data-transparency');
    if (!transparencyDiv) {
        transparencyDiv = document.createElement('div');
        transparencyDiv.id = 'data-transparency';
        var positionsEl = document.getElementById('positions');
        positionsEl.parentNode.insertBefore(transparencyDiv, positionsEl);
    }
    var cgCount = posData.filter(function (p) { return PRICE_SOURCES[p.symbol] === 'coingecko'; }).length;
    var bnCount = posData.filter(function (p) { return PRICE_SOURCES[p.symbol] === 'binance'; }).length;
    var ccCount = posData.filter(function (p) { return PRICE_SOURCES[p.symbol] === 'cryptocompare'; }).length;
    var phpCount = posData.filter(function (p) { return PRICE_SOURCES[p.symbol] === 'php_scraper'; }).length;
    var noApi = posData.filter(function (p) { return PRICE_SOURCES[p.symbol] === 'no_stock_api'; }).length;
    var allFailed = posData.filter(function (p) { return PRICE_SOURCES[p.symbol] === 'all_apis_failed'; }).length;
    var totalLive = cgCount + bnCount + ccCount + phpCount;
    var tHtml = '<div style="padding:12px 16px;background:var(--surface);border:1px solid var(--border);border-radius:10px;margin-bottom:12px">';
    tHtml += '<div style="font-size:0.8rem;font-weight:700;color:var(--text);margin-bottom:8px">\ud83d\udce1 Data Source Transparency</div>';
    tHtml += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:8px">';
    if (totalLive > 0) {
        var sourceList = [];
        if (cgCount > 0) sourceList.push(cgCount + ' via CoinGecko');
        if (bnCount > 0) sourceList.push(bnCount + ' via Binance');
        if (ccCount > 0) sourceList.push(ccCount + ' via CryptoCompare');
        if (phpCount > 0) sourceList.push(phpCount + ' via PHP Scraper');
        tHtml += '<div style="padding:8px;background:rgba(0,200,100,0.08);border-radius:6px;border-left:3px solid var(--green)">';
        tHtml += '<div style="font-size:0.7rem;font-weight:700;color:var(--green)">\u2705 ' + totalLive + ' Crypto \u2014 LIVE</div>';
        tHtml += '<div style="font-size:0.6rem;color:var(--text2)">' + sourceList.join(' | ') + '. P&L updates every 30s. 4-layer API cascade ensures data even if one API is down.</div>';
        tHtml += '</div>';
    }
    if (noApi > 0) {
        tHtml += '<div style="padding:8px;background:rgba(255,200,0,0.08);border-radius:6px;border-left:3px solid var(--gold)">';
        tHtml += '<div style="font-size:0.7rem;font-weight:700;color:var(--gold)">\u26a0 ' + noApi + ' Stock \u2014 NO LIVE FEED</div>';
        tHtml += '<div style="font-size:0.6rem;color:var(--text2)">Stock prices show P&L as $0. Free real-time stock APIs don\'t exist. Signal direction + TP/SL levels are still valid.</div>';
        tHtml += '</div>';
    }
    if (allFailed > 0) {
        tHtml += '<div style="padding:8px;background:rgba(255,60,60,0.08);border-radius:6px;border-left:3px solid var(--red)">';
        tHtml += '<div style="font-size:0.7rem;font-weight:700;color:var(--red)">\u274c ' + allFailed + ' \u2014 ALL 4 APIs FAILED</div>';
        tHtml += '<div style="font-size:0.6rem;color:var(--text2)">CoinGecko, Binance, CryptoCompare, and PHP Scraper all failed. Auto-retrying every 30s.</div>';
        tHtml += '</div>';
    }
    if (PRICE_API_LOG.length > 0) {
        tHtml += '<div style="grid-column:1/-1;padding:8px;background:rgba(0,122,255,0.05);border-radius:6px;border-left:3px solid var(--blue)">';
        tHtml += '<div style="font-size:0.65rem;font-weight:700;color:var(--blue);margin-bottom:4px">\ud83d\udd17 API Cascade Log (this refresh)</div>';
        PRICE_API_LOG.forEach(function (log) {
            var icon = log.status === 'ok' ? '\u2705' : '\u274c';
            var detail = log.status === 'ok' ? log.count + ' prices' : (log.error || log.msg || 'unknown');
            tHtml += '<div style="font-size:0.6rem;color:var(--text2)">' + icon + ' ' + log.api + ': ' + detail + '</div>';
        });
        tHtml += '</div>';
    }
    tHtml += '</div></div>';
    transparencyDiv.innerHTML = tHtml;


    // Position cards
    var html = '';
    posData.forEach(function (p) {
        var priceSrc = PRICE_SOURCES[p.symbol] || 'unknown';
        var isStale = ['coingecko', 'binance', 'cryptocompare', 'php_scraper'].indexOf(priceSrc) === -1;
        var cls = p.pnlPct > 0.5 ? 'winning' : (p.pnlPct < -0.5 ? 'losing' : '');
        var color = p.pnlPct > 0 ? 'var(--green)' : (p.pnlPct < 0 ? 'var(--red)' : 'var(--text2)');
        var catLabel = p.category === 'crypto' ? '\ud83e\ude99 CRYPTO' : (p.category === 'forex' ? '\ud83d\udcb1 FOREX' : '\ud83d\udcca STOCK');
        var catClass = 'cat-' + p.category;
        var isLive = p.category === 'crypto' || p.category === 'forex';
        var mStatus = isLive ? 'live' : 'closed';
        var curPct = Math.max(0, Math.min(100, (p.current - p.sl) / (p.tp - p.sl) * 100));
        var entPct = Math.max(0, Math.min(100, (p.entry_price - p.sl) / (p.tp - p.sl) * 100));

        // Signal strength badge
        var strengthTip = p.signalCount + ' independent algorithms detected a bullish signal for ' + p.symbol + '. Average confidence across all algorithms: ' + p.avgConfidence + '%. More algorithms agreeing = higher conviction.';
        var strengthBadge = '<span title="' + strengthTip + '" style="background:' + (p.signalCount >= 3 ? 'rgba(0,200,100,0.2)' : p.signalCount === 2 ? 'rgba(255,200,0,0.2)' : 'rgba(100,100,100,0.2)') + ';color:' + p.strengthColor + ';padding:2px 8px;border-radius:4px;font-size:0.6rem;font-weight:700;margin-left:6px;cursor:help">' + p.signalCount + ' algo' + (p.signalCount > 1 ? 's' : '') + ' \u2022 ' + p.avgConfidence + '% conf</span>';

        // Forward test badge
        var ftBadge = '<span title="This is a FORWARD TEST: a real-time signal being tracked with $0 real money. We lock entry price at signal time and track it forward to verify the algorithm works." style="background:rgba(0,122,255,0.15);color:var(--blue);padding:2px 6px;border-radius:4px;font-size:0.55rem;margin-left:4px;letter-spacing:0.5px;cursor:help">FORWARD TEST</span>';

        html += '<div class="position ' + cls + '" data-category="' + p.category + '" data-live="' + isLive + '" data-winning="' + (p.pnlPct > 0) + '" data-losing="' + (p.pnlPct < 0) + '">';
        html += '<div class="pos-header">';
        html += '<span class="pos-icon">' + p.icon + '</span>';
        html += '<div class="pos-name">' + p.name + '<br><span class="pos-sym">' + p.symbol + '</span></div>';
        html += '<span class="cat-badge ' + catClass + '" title="Asset category: ' + p.category.toUpperCase() + '. Market: ' + p.market + '.">' + catLabel + '</span>' + strengthBadge + ftBadge;
        var marketTip = isLive ? 'This market is currently LIVE and trading. Price updates every 30s.' : 'US stock market is CLOSED (open 9:30 AM - 4 PM ET weekdays). No live price feed available for stocks.';
        html += '<div class="market-status ' + mStatus + '" title="' + marketTip + '"><span class="status-dot"></span>' + (isLive ? 'LIVE' : 'CLOSED') + '</div>';
        html += '</div>';

        // Price source warning for stale prices
        if (isStale) {
            var staleMsg = priceSrc === 'no_stock_api' ? '\u26a0 No real-time stock price API. Showing entry price. P&L will be $0. Signal direction and TP/SL are still valid.' : priceSrc === 'all_apis_failed' ? '\u274c All 4 APIs failed (CoinGecko, Binance, CryptoCompare, PHP Scraper). Retrying in 30s.' : '\u23f3 Using entry price. Live price loading...';
            html += '<div style="grid-column:1/-1;padding:6px 10px;background:rgba(255,200,0,0.08);border-radius:6px;border:1px solid rgba(255,200,0,0.2);font-size:0.65rem;color:var(--gold);margin-bottom:4px" title="This is why P&L shows $0 for this position">' + staleMsg + '</div>';
        }

        // Price details with tooltips
        html += '<div class="pos-details">';
        html += '<div class="detail-row" title="Signal direction: LONG means buy/bullish. The algorithm expects price to go UP."><span class="detail-label">Direction</span><span style="color:var(--green);font-weight:700">' + p.direction + '</span></div>';
        html += '<div class="detail-row" title="The price when the signal was generated. This is the benchmark for calculating P&L."><span class="detail-label">Entry</span><span>' + fmt(p.entry_price) + '</span></div>';
        var srcLabels = { coingecko: 'CoinGecko', binance: 'Binance', cryptocompare: 'CryptoCompare', php_scraper: 'PHP Scraper' };
        var currentTip = srcLabels[priceSrc] ? 'Real-time price from ' + srcLabels[priceSrc] + ' API (updates every 30s)' : priceSrc === 'no_stock_api' ? 'Same as entry price! No free real-time stock API available.' : 'Entry price used as fallback. All 4 APIs failed.';
        var liveLabel = !isStale ? '<span style="color:var(--green);font-size:0.5rem">\u25cf LIVE' + (srcLabels[priceSrc] ? ' (' + srcLabels[priceSrc] + ')' : '') + '</span>' : '<span style="color:var(--gold);font-size:0.5rem">\u25cb STALE</span>';
        html += '<div class="detail-row" title="' + currentTip + '"><span class="detail-label">Current ' + liveLabel + '</span><span style="color:' + color + ';font-weight:700">' + fmt(p.current) + '</span></div>';
        html += '<div class="detail-row" title="Hypothetical investment amount for P&L tracking. No real money is at risk."><span class="detail-label">Risked</span><span>$' + p.invested.toLocaleString() + '</span></div>';
        html += '<div class="detail-row" title="When the scanner generated this signal. The scanner runs every few hours analyzing 127 assets."><span class="detail-label">Signal Time</span><span>' + p.timestamp + '</span></div>';
        html += '<div class="detail-row" title="Current position status based on price movement since entry."><span class="detail-label">Status</span><span>' + p.status + '</span></div>';
        if (p.riskReward > 0) {
            html += '<div class="detail-row" title="Risk/Reward ratio: potential profit vs potential loss. Higher is better. 2:1+ is considered good."><span class="detail-label">Risk/Reward</span><span style="color:var(--gold)">' + p.riskReward.toFixed(2) + ':1</span></div>';
        }
        html += '</div>';

        // TP/SL bar with tooltips
        html += '<div class="pos-levels" title="Take Profit = target exit price for gains. Stop Loss = maximum acceptable loss exit price."><div><div class="lbl">Take Profit</div><div class="val green">' + fmt(p.tp) + ' (+' + p.tp_pct + '%)</div></div>';
        html += '<div><div class="lbl">Stop Loss</div><div class="val red">' + fmt(p.sl) + ' (-' + p.sl_pct + '%)</div></div></div>';
        html += '<div class="tp-sl-bar" title="Visual: price position between Stop Loss (left) and Take Profit (right). Green marker = current price.">';
        html += '<div style="position:absolute;left:0;top:0;width:' + curPct + '%;height:100%;border-radius:4px;background:' + (p.pnlPct >= 0 ? 'linear-gradient(90deg,var(--surface2),var(--green-dim))' : 'linear-gradient(90deg,var(--red-dim),var(--surface2))') + '"></div>';
        html += '<div class="marker entry-m" style="left:' + entPct + '%" title="Entry price: ' + fmt(p.entry_price) + '"></div>';
        html += '<div class="marker current-m" style="left:' + curPct + '%" title="Current price: ' + fmt(p.current) + '"></div>';
        html += '</div>';
        html += '<div style="display:flex;justify-content:space-between;margin-top:4px;font-size:0.65rem;color:var(--text2)">';
        html += '<span>SL ' + fmt(p.sl) + '</span><span>TP ' + fmt(p.tp) + ' (' + (p.tpDist >= 0 ? '+' : '') + p.tpDist.toFixed(1) + '% away)</span></div>';

        // P&L cell with tooltip
        var pnlTipCard = isStale ? 'P&L is $0 because there is no live price feed for this asset. The signal\'s direction, entry, TP, and SL are still valid.' : 'Real-time P&L based on CoinGecko price vs entry price.';
        html += '<div class="pnl-cell" title="' + pnlTipCard + '">';
        html += '<div class="pnl-pct" style="color:' + color + '">' + (p.pnlPct >= 0 ? '+' : '') + p.pnlPct.toFixed(3) + '%</div>';
        html += '<div class="pnl-dollar" style="color:' + color + '">' + (p.pnlDollar >= 0 ? '+' : '') + '$' + p.pnlDollar.toFixed(2) + '</div>';
        html += '</div>';

        // Signal summary
        html += '<div style="grid-column:1/-1;margin-top:8px;padding:10px;background:var(--surface2);border-radius:8px">';
        html += '<div style="font-size:0.7rem;color:var(--text2)">' + p.reason + '</div>';
        html += '<div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:6px">';
        p.strategies.forEach(function (s) {
            html += '<span style="background:rgba(0,122,255,0.1);color:var(--blue);padding:2px 6px;border-radius:4px;font-size:0.6rem">' + s + '</span>';
        });
        html += '</div></div>';

        // ─── AUDIT LOG BUTTON (expandable) ───
        html += '<details style="grid-column:1/-1;margin-top:6px">';
        html += '<summary style="cursor:pointer;font-size:0.75rem;color:var(--blue);font-weight:600;padding:8px 12px;background:var(--surface2);border-radius:8px;border:1px solid var(--border)">';
        html += '\ud83d\udcdd View Full Audit Log & Methodology (' + p.audit.length + ' signal' + (p.audit.length > 1 ? 's' : '') + ')</summary>';
        html += '<div style="margin-top:6px;padding:12px;background:var(--surface2);border-radius:8px;border:1px solid var(--border)">';

        // Forward test notice
        html += '<div style="padding:8px 12px;background:rgba(0,122,255,0.1);border-radius:6px;margin-bottom:10px;font-size:0.7rem;color:var(--blue)">';
        html += '\u2139\ufe0f <strong>FORWARD TEST</strong> \u2014 This is a real-time signal detected by the scanner. No money at risk. Tracking to verify strategy performance. Entry price locked at signal time.';
        html += '</div>';

        p.audit.forEach(function (ae, idx) {
            var dirColor = ae.type === 'STRONG_BUY' ? 'var(--green)' : ae.type === 'BUY' ? '#4CAF50' : ae.type === 'MILD_BUY' ? 'var(--gold)' : 'var(--blue)';
            html += '<div style="margin-bottom:10px;padding:10px;background:rgba(255,255,255,0.02);border-radius:6px;border-left:3px solid ' + dirColor + '">';
            html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">';
            html += '<span style="font-weight:700;font-size:0.75rem;color:' + dirColor + '">' + ae.strategy + ' \u2014 ' + ae.type + '</span>';
            html += '<span style="font-size:0.65rem;color:var(--text2);background:rgba(0,200,100,0.1);padding:2px 6px;border-radius:4px">' + ae.confidence + '% confidence</span>';
            html += '</div>';

            // Methodology
            if (ae.methodology) {
                html += '<div style="font-size:0.65rem;color:var(--text2);margin-bottom:4px">\ud83d\udcda <strong>Methodology:</strong> ' + ae.methodology + '</div>';
            }

            // Reason
            html += '<div style="font-size:0.7rem;color:var(--text);margin-bottom:4px">' + ae.reason + '</div>';

            // Proven win rate
            if (ae.proven_wr && ae.proven_wr !== 'N/A') {
                html += '<div style="font-size:0.65rem;color:var(--gold)">\ud83c\udfc6 Proven WR: ' + ae.proven_wr + '</div>';
            }

            // Performance stats
            if (ae.performance) {
                html += '<div style="font-size:0.65rem;color:var(--text2);margin-top:4px">\ud83d\udcca 90-day track: ' + ae.performance.wins_90d + '/' + ae.performance.trades_90d + ' wins (' + ae.performance.wr_90d + '% WR)</div>';
            }

            // Risk/Reward
            if (ae.rr > 0) {
                html += '<div style="font-size:0.65rem;color:var(--text2)">\u2696\ufe0f Risk/Reward: ' + ae.rr.toFixed(2) + ':1</div>';
            }

            // Review date
            if (ae.review_date) {
                html += '<div style="font-size:0.6rem;color:var(--text2);margin-top:4px">\ud83d\udcc5 Review by: ' + ae.review_date + (ae.max_hold ? ' (max ' + ae.max_hold + ' days)' : '') + '</div>';
            }

            // Key indicators
            if (ae.indicators && Object.keys(ae.indicators).length > 0) {
                html += '<div style="margin-top:6px;display:flex;flex-wrap:wrap;gap:4px">';
                var indKeys = Object.keys(ae.indicators);
                indKeys.forEach(function (ik) {
                    var v = ae.indicators[ik];
                    if (typeof v === 'boolean') v = v ? '\u2705' : '\u274c';
                    else if (typeof v === 'number') v = v.toFixed ? v.toFixed(2) : v;
                    html += '<span style="font-size:0.55rem;background:rgba(255,255,255,0.05);padding:2px 6px;border-radius:3px;color:var(--text2)">' + ik + ': ' + v + '</span>';
                });
                html += '</div>';
            }
            html += '</div>';
        });

        html += '</div></details>';
        html += '</div>';
    });

    document.getElementById('positions').innerHTML = html;
}

// ──────── Filter Logic ────────
function setFilter(filter) {
    var btns = document.querySelectorAll('[data-filter]');
    for (var i = 0; i < btns.length; i++) btns[i].classList.remove('active');
    var btn = document.querySelector('[data-filter="' + filter + '"]');
    if (btn) btn.classList.add('active');
    var cards = document.querySelectorAll('.position');
    for (i = 0; i < cards.length; i++) {
        var card = cards[i];
        var cat = card.getAttribute('data-category');
        var isLive = card.getAttribute('data-live') === 'true';
        var isWinning = card.getAttribute('data-winning') === 'true';
        var show = true;
        if (filter === 'crypto') show = cat === 'crypto';
        else if (filter === 'stock') show = cat === 'stock';
        else if (filter === 'forex') show = cat === 'forex';
        else if (filter === 'winning') show = isWinning;
        else if (filter === 'losing') show = card.getAttribute('data-losing') === 'true';
        else if (filter === 'live') show = isLive;
        card.style.display = show ? '' : 'none';
    }
}

// ──────── Refresh ────────
function refresh() {
    return fetchLivePrices().then(function (prices) {
        render(prices);
    }).catch(function (e) {
        console.error('Refresh failed:', e);
        var fallback = {};
        PORTFOLIO.positions.forEach(function (p) { fallback[p.symbol] = p.entry_price; });
        render(fallback);
    });
}

// Init
loadPortfolio().then(function () {
    refresh();
    setInterval(refresh, 30000);
});

// ─── Scanner Picks (live_signals_now.json — bottom section) ───
var scannerPicks = [];
var pickFilter = 'all';

function classifySymbol(sym) {
    if (sym.indexOf('USD=X') !== -1) return 'forex';
    if (sym.length > 4 && sym.substr(sym.length - 4) === '-USD') return 'crypto';
    return 'stock';
}
function pickIcon(cat) {
    return cat === 'crypto' ? '\ud83e\ude99' : cat === 'forex' ? '\ud83d\udcb1' : '\ud83d\udcca';
}

function loadScannerPicks() {
    fetch('data/live_signals_now.json?t=' + Date.now())
        .then(function (resp) { return resp.json(); })
        .then(function (data) {
            // Merge crypto + stock + forex signals
            var all = [];
            (data.crypto_signals || []).forEach(function (s) { s._cat = 'crypto'; all.push(s); });
            (data.stock_signals || []).forEach(function (s) { s._cat = 'stock'; all.push(s); });
            (data.forex_signals || []).forEach(function (s) { s._cat = 'forex'; all.push(s); });

            // Sort by composite_score first, then confidence
            all.sort(function (a, b) { return (b.composite_score || b.confidence || 0) - (a.composite_score || a.confidence || 0); });

            scannerPicks = all;

            // Fetch live prices for crypto picks
            var cryptoIds = { 'BTC-USD': 'bitcoin', 'ETH-USD': 'ethereum', 'SOL-USD': 'solana', 'DOGE-USD': 'dogecoin', 'BNB-USD': 'binancecoin', 'ADA-USD': 'cardano', 'AVAX-USD': 'avalanche-2', 'LTC-USD': 'litecoin', 'XRP-USD': 'ripple', 'LINK-USD': 'chainlink', 'DOT-USD': 'polkadot', 'MATIC-USD': 'matic-network', 'SHIB-USD': 'shiba-inu', 'BCH-USD': 'bitcoin-cash', 'NEAR-USD': 'near', 'ATOM-USD': 'cosmos', 'INJ-USD': 'injective-protocol' };
            var idsToFetch = [];
            all.forEach(function (s) { if (cryptoIds[s.symbol] && idsToFetch.indexOf(cryptoIds[s.symbol]) === -1) idsToFetch.push(cryptoIds[s.symbol]); });

            if (idsToFetch.length) {
                fetch('https://api.coingecko.com/api/v3/simple/price?ids=' + idsToFetch.join(',') + '&vs_currencies=usd')
                    .then(function (r) { return r.json(); })
                    .then(function (cgData) {
                        var keys = Object.keys(cryptoIds);
                        keys.forEach(function (sym) {
                            var id = cryptoIds[sym];
                            if (cgData[id]) {
                                all.forEach(function (p) { if (p.symbol === sym) p._livePrice = cgData[id].usd; });
                            }
                        });
                        renderScannerPicks();
                    })
                    .catch(function () { renderScannerPicks(); });
            } else {
                renderScannerPicks();
            }
        })
        .catch(function (e) {
            var el = document.getElementById('scanner-picks');
            if (el) el.innerHTML = '<p style="color:var(--red)">Failed to load scanner picks.</p>';
        });
}

function renderScannerPicks() {
    var filtered = pickFilter === 'all' ? scannerPicks : scannerPicks.filter(function (p) { return (p._cat || classifySymbol(p.symbol)) === pickFilter; });
    var countEl = document.getElementById('picks-count');
    if (countEl) countEl.textContent = scannerPicks.length;

    var html = '';
    filtered.forEach(function (p) {
        var cat = p._cat || classifySymbol(p.symbol);
        var currentPrice = p._livePrice || p.price;
        var pnlPct = p.price ? ((currentPrice - p.price) / p.price * 100) : 0;
        var color = pnlPct > 0.01 ? 'var(--green)' : (pnlPct < -0.01 ? 'var(--red)' : 'var(--text2)');
        var signalColor = (p.signal || '').indexOf('STRONG') !== -1 ? 'var(--green)' : (p.signal || '').indexOf('BUY') !== -1 ? '#4CAF50' : 'var(--text2)';
        var reasons = (p.reasons || []).join(' \u2022 ');

        html += '<div style="background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:12px 16px;display:flex;align-items:center;gap:12px;flex-wrap:wrap" data-pcat="' + cat + '">';
        html += '<span style="font-size:1.2rem">' + pickIcon(cat) + '</span>';
        html += '<div style="min-width:100px"><div style="font-weight:700;font-size:0.85rem">' + p.symbol + '</div>';
        html += '<div style="font-size:0.6rem;color:' + signalColor + ';text-transform:uppercase;font-weight:700">' + (p.signal || 'WATCH') + ' \u2022 ' + (p.confidence || 0) + '% conf</div></div>';
        html += '<div style="flex:1;min-width:180px"><div style="font-size:0.65rem;color:var(--text2)">' + reasons + '</div>';
        if (p.risk_reward) html += '<div style="font-size:0.55rem;color:var(--gold);margin-top:2px">R/R: ' + p.risk_reward.toFixed(2) + ':1</div>';
        html += '</div>';
        html += '<div style="text-align:right;min-width:80px"><div style="font-family:monospace;font-size:0.75rem;color:var(--text)">$' + (p.price < 0.01 ? p.price.toFixed(8) : p.price < 1 ? p.price.toFixed(4) : p.price.toFixed(2)) + '</div>';
        html += '<div style="font-size:0.55rem;color:var(--text2)">RSI: ' + (p.rsi || '--') + '</div></div>';
        html += '<div style="text-align:right;min-width:70px"><div style="font-family:monospace;font-weight:700;font-size:0.8rem;color:' + color + '">' + (pnlPct >= 0 ? '+' : '') + pnlPct.toFixed(2) + '%</div></div>';
        html += '</div>';
    });
    var picksEl = document.getElementById('scanner-picks');
    if (picksEl) picksEl.innerHTML = html || '<p style="color:var(--text2)">No picks in this category.</p>';
}

function setPickFilter(filter) {
    pickFilter = filter;
    var btns = document.querySelectorAll('[data-pfilter]');
    for (var i = 0; i < btns.length; i++) btns[i].classList.remove('active');
    var btn = document.querySelector('[data-pfilter="' + filter + '"]');
    if (btn) btn.classList.add('active');
    renderScannerPicks();
}

loadScannerPicks();
setInterval(loadScannerPicks, 60000);
