/**
 * Discord Interactions Cloudflare Worker
 * Handles /fc-crypto, /fc-forex, /fc-picks, /fc-momentum, /fc-realtime
 * 
 * Deployed to: https://broad-sky-e096.zerounderscore.workers.dev
 */

const DISCORD_PUBLIC_KEY = '276870d26bca9f11def6dd538f7c207515075f6c41a02c3d6c2161f34547ac14';
const DASHBOARD_URL = 'https://findtorontoevents.ca/updates/antigravity-ml-gainer.html';
const LIVE_MONITOR_URL = 'https://findtorontoevents.ca/live-monitor/live-monitor.html';
const BABY_DASHBOARD_JSON_URL = 'https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/battleground/data/baby_strats_dashboard.json';

// Data URLs (PHP API endpoints to bypass ModSecurity JSON blocking)
const CRYPTO_API_URL = 'https://findtorontoevents.ca/fc/api/crypto_picks_api.php?source=all&format=discord';
// Fallback: direct JSON files (may be blocked by ModSecurity for some clients)  
const DATA_URLS = [
    'https://findtorontoevents.ca/updates/data/antigravity_ml_live_picks.json',
    'https://findtorontoevents.ca/updates/data/antigravity_ml_performance.json',
    'https://findtorontoevents.ca/updates/data/claude_ml_picks.json',
];

export default {
    async fetch(request) {
        if (request.method === 'GET') {
            return new Response('Method not allowed', { status: 405 });
        }

        if (request.method !== 'POST') {
            return new Response('Method not allowed', { status: 405 });
        }

        // Verify Discord signature
        const signature = request.headers.get('X-Signature-Ed25519');
        const timestamp = request.headers.get('X-Signature-Timestamp');
        const body = await request.text();

        const isVerified = await verifyDiscordSignature(body, signature, timestamp);
        if (!isVerified) {
            return new Response('Invalid signature', { status: 401 });
        }

        const interaction = JSON.parse(body);

        // Handle PING
        if (interaction.type === 1) {
            return jsonResponse({ type: 1 });
        }

        // Handle Application Commands
        if (interaction.type === 2) {
            return handleCommand(interaction);
        }

        return new Response('Unhandled interaction type', { status: 400 });
    }
};

async function verifyDiscordSignature(body, signature, timestamp) {
    if (!signature || !timestamp) return false;

    try {
        const key = await crypto.subtle.importKey(
            'raw',
            hexToUint8Array(DISCORD_PUBLIC_KEY),
            { name: 'Ed25519', namedCurve: 'Ed25519' },
            false,
            ['verify']
        );

        const message = new TextEncoder().encode(timestamp + body);
        const sig = hexToUint8Array(signature);

        return await crypto.subtle.verify('Ed25519', key, sig, message);
    } catch (e) {
        console.error('Verification error:', e);
        return false;
    }
}

function hexToUint8Array(hex) {
    const pairs = hex.match(/.{1,2}/g) || [];
    return new Uint8Array(pairs.map(byte => parseInt(byte, 16)));
}

function jsonResponse(data, status = 200) {
    return new Response(JSON.stringify(data), {
        status,
        headers: { 'Content-Type': 'application/json' }
    });
}

function embedResponse(title, description, color, fields = [], footer = 'Not financial advice') {
    const embed = { title, description, color };
    if (fields.length > 0) embed.fields = fields;
    if (footer) embed.footer = { text: footer };

    return jsonResponse({
        type: 4,
        data: {
            embeds: [embed]
        }
    });
}

function getOption(options, name, defaultVal = null) {
    if (!options) return defaultVal;
    const opt = options.find(o => o.name === name);
    return opt ? opt.value : defaultVal;
}

async function handleCommand(interaction) {
    const commandName = interaction.data?.name || '';
    const options = interaction.data?.options || [];

    switch (commandName) {
        case 'fc-crypto':
            return handleCrypto(options);
        case 'fc-forex':
            return embedResponse(
                '💱 Forex Signals',
                `Forex signal engine is being enhanced.\n\n🔗 [Live Monitor](${LIVE_MONITOR_URL})`,
                0x3b82f6
            );
        case 'fc-picks':
            return handleAllPicks();
        case 'fc-momentum':
            return handleMomentum();
        case 'fc-realtime':
            return embedResponse(
                '⚡ Real-Time Market Data',
                `View real-time trading signals:\n\n🔗 [Live Trading Monitor](${LIVE_MONITOR_URL})\n🔗 [ML Gainer Dashboard](${DASHBOARD_URL})\n🔗 [Crypto Pair Scanner](https://findtorontoevents.ca/findcryptopairs/)`,
                0x06b6d4
            );
        case 'fc-baby-winning':
            return handleBabyWinning();
        case 'top-graduation-candidates':
            return handleTopGraduationCandidates();
        default:
            return embedResponse('❓ Unknown Command', `Command \`/${commandName}\` is not recognized.`, 0xef4444);
    }
}

async function handleCrypto(options) {
    const timeline = getOption(options, 'timeline', 'daytrader');
    const budget = getOption(options, 'budget', 'medium');

    let activePicks = [];
    let source = '';

    try {
        // Try PHP API first (most reliable, bypasses ModSecurity)
        const apiRes = await fetch(CRYPTO_API_URL, {
            headers: { 'User-Agent': 'Mozilla/5.0 MyFavCreators/2.0' }
        });

        if (apiRes.ok) {
            const data = await apiRes.json();
            if (data && data.active_picks && data.active_picks.length > 0) {
                activePicks = data.active_picks;
                source = data.source_requested || 'API';

                // If API returned discord embed directly, use it
                if (data.discord_embed) {
                    return jsonResponse({
                        type: 4,
                        data: {
                            embeds: [data.discord_embed]
                        }
                    });
                }
            }
        }
    } catch (e) {
        console.error('API fetch error:', e);
    }

    // Fallback: try direct JSON URLs
    if (activePicks.length === 0) {
        for (const url of DATA_URLS) {
            try {
                const res = await fetch(url, {
                    headers: { 'User-Agent': 'Mozilla/5.0 MyFavCreators/2.0' }
                });
                if (!res.ok) continue;
                const data = await res.json();

                if (Array.isArray(data) && data.length > 0) {
                    activePicks = data;
                    source = 'Antigravity ML';
                    break;
                }

                if (data?.active_picks?.length > 0) {
                    activePicks = data.active_picks;
                    source = 'Antigravity ML Performance';
                    break;
                }

                if (data?.picks?.length > 0) {
                    activePicks = data.picks.filter(p => !p.status || p.status === 'ACTIVE');
                    if (activePicks.length > 0) {
                        source = 'Claude Code ML';
                        break;
                    }
                }
            } catch (e) {
                continue;
            }
        }
    }

    // No picks found
    if (activePicks.length === 0) {
        return embedResponse(
            '📊 Crypto ML Picks — No Active Picks',
            `No active ML predictions currently available.\n\nThe ML scanner runs every 4 hours. Next scan should produce new picks.\n\n🔗 [View Dashboard](${DASHBOARD_URL})\n🔗 [Live Monitor](${LIVE_MONITOR_URL})`,
            0xf59e0b,
            [],
            'CLAUDE CODE ML v2.0 | Not financial advice'
        );
    }

    // Build embed fields
    const fields = [];
    for (const pick of activePicks.slice(0, 8)) {
        const symbol = (pick.symbol || pick.coin_id || '???').toUpperCase();

        let entry = pick.entry_price || pick.price || pick.current_price || 0;
        let tp = pick.tp_price || pick.tp1_price || entry * 1.10;
        let sl = pick.sl_price || entry * 0.93;

        let confidence = 'N/A';
        let prob = 0;
        if (pick.pump_probability) {
            prob = parseFloat(pick.pump_probability);
            if (prob >= 0.80) confidence = 'VERY HIGH';
            else if (prob >= 0.65) confidence = 'HIGH';
            else if (prob >= 0.50) confidence = 'MEDIUM';
            else confidence = 'LOW';
        } else if (pick.gainer_score) {
            prob = parseInt(pick.gainer_score) / 100;
            if (pick.gainer_score >= 70) confidence = 'HIGH';
            else if (pick.gainer_score >= 50) confidence = 'MEDIUM';
            else confidence = 'LOW';
        } else if (pick.confidence) {
            confidence = pick.confidence;
        }

        const signals = (pick.signals || ['ML Signal']).slice(0, 3).join(' | ');
        const tpPct = entry > 0 ? ((tp - entry) / entry * 100).toFixed(1) : '0';
        const slPct = entry > 0 ? ((sl - entry) / entry * 100).toFixed(1) : '0';

        fields.push({
            name: `${symbol} — ${confidence} (${Math.round(prob * 100)}%)`,
            value: `Entry: ${fmtPrice(entry)}\nTP: ${fmtPrice(tp)} (+${tpPct}%)  SL: ${fmtPrice(sl)} (${slPct}%)\nSignals: ${signals}`,
            inline: false
        });
    }

    return embedResponse(
        `📊 Crypto ML Picks — ${activePicks.length} Active`,
        `**CLAUDE CODE - REVERSE ENGINEERED DAILY TOP GAINERS STRAT**\nSource: ${source}\n\n🔗 [Full Dashboard](${DASHBOARD_URL}) | [Live Monitor](${LIVE_MONITOR_URL})`,
        0x22c55e,
        fields,
        `Timeline: ${timeline} | Budget: ${budget} | ⚠️ PAPER TRADE ONLY — Not financial advice`
    );
}

async function handleAllPicks() {
    let total = 0;
    const lines = [];

    try {
        const res = await fetch(CRYPTO_API_URL.replace('&format=discord', ''), {
            headers: { 'User-Agent': 'Mozilla/5.0 MyFavCreators/2.0' }
        });
        if (res.ok) {
            const data = await res.json();
            total = data.summary?.total_active || 0;
            lines.push(`**All Sources**: ${total} active picks`);
            lines.push(`**Resolved**: ${data.summary?.total_resolved || 0} picks`);
        }
    } catch (e) {
        lines.push('Could not fetch all picks data.');
    }

    return embedResponse(
        `📋 All Active Picks — ${total} Total`,
        lines.join('\n') + `\n\n🔗 [Dashboard](${DASHBOARD_URL})`,
        0x6366f1
    );
}

async function handleMomentum() {
    return embedResponse(
        '📈 Momentum Indicators',
        `Visit the dashboard for real-time momentum data:\n\n🔗 [ML Dashboard](${DASHBOARD_URL})\n🔗 [Live Monitor](${LIVE_MONITOR_URL})\n\nThe ML scanner runs every 4 hours with adaptive thresholds.`,
        0x22c55e,
        [],
        'CLAUDE CODE ML | Not financial advice'
    );
}

function fmtPrice(price) {
    if (!price || price === 0) return '$0.00';
    if (price >= 100) return '$' + price.toFixed(2);
    if (price >= 1) return '$' + price.toFixed(4);
    if (price >= 0.001) return '$' + price.toFixed(6);
    return '$' + price.toExponential(3);
}

async function loadBabyDashboard() {
    try {
        const res = await fetch(BABY_DASHBOARD_JSON_URL, {
            headers: { 'User-Agent': 'Mozilla/5.0 MyFavCreators/2.0' }
        });
        if (!res.ok) return null;
        const data = await res.json();
        if (!data || !Array.isArray(data.strategies)) return null;
        return data;
    } catch (e) {
        return null;
    }
}

function isRealVerifiedStrategy(s) {
    return !!(s && s.verification && s.verification.real_data_verified === true);
}

function toPctVal(v) {
    if (v === null || v === undefined || Number.isNaN(Number(v))) return null;
    const n = Number(v);
    return Math.abs(n) <= 1.5 ? (n * 100) : n;
}

function compareWinners(a, b) {
    const awr = toPctVal(a?.forward_metrics?.win_rate) ?? -9999;
    const bwr = toPctVal(b?.forward_metrics?.win_rate) ?? -9999;
    if (awr !== bwr) return bwr - awr;
    const ash = Number(a?.forward_metrics?.sharpe ?? -9999);
    const bsh = Number(b?.forward_metrics?.sharpe ?? -9999);
    if (ash !== bsh) return bsh - ash;
    const at = Number(a?.forward_metrics?.total_trades ?? 0);
    const bt = Number(b?.forward_metrics?.total_trades ?? 0);
    return bt - at;
}

async function handleBabyWinning() {
    const data = await loadBabyDashboard();
    if (!data) {
        return embedResponse('🍼 Baby Winning Strategy', 'Could not load baby strategy dashboard data right now.', 0xef4444);
    }

    const eligible = data.strategies.filter((s) =>
        isRealVerifiedStrategy(s) &&
        Number(s?.forward_metrics?.total_trades || 0) > 0 &&
        s?.forward_metrics?.win_rate !== null &&
        s?.forward_metrics?.win_rate !== undefined
    );

    if (eligible.length === 0) {
        return embedResponse(
            '🍼 Baby Winning Strategy',
            'No real forward winners yet.\n\nForward stats only appear after real matched forward trades close.\nUse `/top-graduation-candidates` to see who is closest.',
            0xf59e0b,
            [],
            'Forward-only, real-data policy enforced'
        );
    }

    eligible.sort(compareWinners);
    const top = eligible[0];
    const wr = toPctVal(top?.forward_metrics?.win_rate);
    const sh = top?.forward_metrics?.sharpe;
    const dd = toPctVal(top?.forward_metrics?.max_drawdown);
    const tr = Number(top?.forward_metrics?.total_trades || 0);

    return embedResponse(
        '🍼 Baby Winning Strategy',
        `**Top Forward Winner (Real Data)**\n\n` +
        `**${top?.name || 'unknown'}** (${String(top?.status || 'unknown').toUpperCase()})\n` +
        `FW Win Rate: ${wr === null ? 'n/a' : wr.toFixed(1) + '%'}\n` +
        `FW Sharpe: ${Number.isFinite(Number(sh)) ? Number(sh).toFixed(2) : 'n/a'}\n` +
        `FW Max DD: ${dd === null ? 'n/a' : dd.toFixed(1) + '%'}\n` +
        `FW Trades: ${tr}\n\n` +
        `🔗 https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/battleground/`,
        0x22c55e,
        [],
        'Forward-only winner from real matched trades'
    );
}

function graduationScore(s) {
    const wr = toPctVal(s?.forward_metrics?.win_rate);
    const sh = Number(s?.forward_metrics?.sharpe ?? 0);
    const dd = toPctVal(s?.forward_metrics?.max_drawdown);
    const tr = Number(s?.forward_metrics?.total_trades || 0);
    const days = Number(s?.paper_trading?.days_elapsed || 0);

    const wrC = wr === null ? 0 : Math.min(1, Math.max(0, wr / 60));
    const shC = Math.min(1, Math.max(0, sh / 1.5));
    const ddC = dd === null ? 0 : Math.min(1, Math.max(0, (20 - Math.abs(dd)) / 20));
    const trC = Math.min(1, Math.max(0, tr / 20));
    const dyC = Math.min(1, Math.max(0, days / 30));
    return (0.30 * wrC) + (0.25 * shC) + (0.20 * ddC) + (0.15 * trC) + (0.10 * dyC);
}

async function handleTopGraduationCandidates() {
    const data = await loadBabyDashboard();
    if (!data) {
        return embedResponse('🎓 Top Graduation Candidates', 'Could not load baby strategy data right now.', 0xef4444);
    }

    const cands = data.strategies
        .filter((s) => isRealVerifiedStrategy(s) && String(s?.status || '').toLowerCase() === 'paper_trading')
        .map((s) => ({ ...s, _score: graduationScore(s) }))
        .sort((a, b) => (b._score - a._score) || compareWinners(a, b))
        .slice(0, 5);

    if (cands.length === 0) {
        return embedResponse('🎓 Top Graduation Candidates', 'No paper-trading strategies found in real-only feed.', 0xf59e0b);
    }

    const fields = cands.map((s) => {
        const wr = toPctVal(s?.forward_metrics?.win_rate);
        const sh = Number(s?.forward_metrics?.sharpe);
        const dd = toPctVal(s?.forward_metrics?.max_drawdown);
        const tr = Number(s?.forward_metrics?.total_trades || 0);
        const days = Number(s?.paper_trading?.days_elapsed || 0);
        return {
            name: `${s?.name || 'unknown'} (score ${Number(s._score || 0).toFixed(2)})`,
            value:
                `FW WR: ${wr === null ? 'n/a' : wr.toFixed(1) + '%'} | ` +
                `FW Sharpe: ${Number.isFinite(sh) ? sh.toFixed(2) : 'n/a'} | ` +
                `FW DD: ${dd === null ? 'n/a' : dd.toFixed(1) + '%'}\n` +
                `FW Trades: ${tr} | Days elapsed: ${days}/30`,
            inline: false
        };
    });

    return embedResponse(
        '🎓 Top Graduation Candidates',
        'Real-data paper strategies ranked by graduation readiness (forward performance + maturity).',
        0x3b82f6,
        fields,
        'Forward-paper readiness only; not financial advice'
    );
}
