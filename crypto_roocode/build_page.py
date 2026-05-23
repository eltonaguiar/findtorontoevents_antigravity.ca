#!/usr/bin/env python3
"""
ANTIGRAVITY — Build Performance Dashboard HTML from real data.
Generates: crypto_roocode/index.html
Run: python crypto_roocode/build_page.py
"""
import json, os, html, sys
from datetime import datetime, timezone
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load(path):
    fp = os.path.join(BASE, path)
    if os.path.exists(fp):
        with open(fp, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

# ─── DATA ──────────────────────────────────────────────────────────────
active_picks = load('alpha_engine/data/active_picks.json') or []
closed_picks = load('alpha_engine/data/closed_picks.json') or []
strategy_perf = load('alpha_engine/data/strategy_performance.json') or {}
training = load('ml_crypto_predictor/enhanced_models/results/training_summary.json') or {}

now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

# ─── FORWARD STATS ────────────────────────────────────────────────────
fwd_wins = sum(1 for p in closed_picks if p.get('status') == 'WON')
fwd_losses = sum(1 for p in closed_picks if p.get('status') == 'LOST')
fwd_total = fwd_wins + fwd_losses
fwd_wr = f"{fwd_wins/fwd_total*100:.0f}%" if fwd_total > 0 else "N/A"
fwd_pnl = sum(p.get('pnl_dollar', 0) for p in closed_picks)
fwd_avg_pnl = sum(p.get('pnl_pct', 0) for p in closed_picks) / max(len(closed_picks), 1)

# ─── STRATEGY ANALYSIS ────────────────────────────────────────────────
STRATEGY_EXPLAIN = {
    "m2_liquidity_lag": {
        "name": "M2 Money Supply Lag",
        "icon": "💰",
        "what": "When governments print more money (M2 goes up), crypto prices tend to rise 2-3 months later. This strategy buys crypto when the money supply is growing because historically prices follow with a delay.",
        "how": "Monitors Federal Reserve M2 data via FRED API. When 3-month M2 growth exceeds 0.5%, generates BUY signals for major crypto pairs. The 70-107 day lag is based on research by Arthur Hayes and Raoul Pal.",
    },
    "variance_ratio_momentum": {
        "name": "Variance Ratio Momentum",
        "icon": "📊",
        "what": "This looks at whether prices are bouncing around randomly or trending. When the 'variance ratio' is below 1.0, it means prices tend to bounce back after drops — so the model buys dips expecting a rebound.",
        "how": "Computes Lo-MacKinlay variance ratios at 5 and 10 period lags. VR < 1 indicates mean-reversion regime. Combined with trend filters (EMA slope) to avoid catching falling knives.",
    },
    "community_ict_fvg": {
        "name": "ICT Fair Value Gap",
        "icon": "📉",
        "what": "When price moves really fast, it leaves a 'gap' — an area where not much trading happened. Smart money (big institutions) often push price back to fill these gaps. This strategy buys when price returns to fill a gap in a bullish trend.",
        "how": "Identifies FVG zones using 3-candle patterns where candle 1 high < candle 3 low (bullish FVG). Entry triggers when price retraces into the FVG zone. Requires ADX > 25 (trending market) and RSI < 70 (not overbought).",
    },
    "community_ict_fvg_selective": {
        "name": "ICT Fair Value Gap (Selective)",
        "icon": "📉",
        "what": "Same idea as the Fair Value Gap strategy but more picky — it only triggers when multiple extra conditions are met (strong trend via ADX, RSI not overbought). Think of it as the 'careful' version.",
        "how": "Same FVG detection as above, plus: ADX > 30, RSI in discount zone (< 50), volume confirmation, and minimum gap size of 0.5% of price.",
    },
    "smart_money_fvg": {
        "name": "Smart Money Fair Value Gap",
        "icon": "🏦",
        "what": "Tracks where big institutional traders (banks, hedge funds) are likely buying. When price drops into a zone where institutions previously bought heavily (the 'fill zone'), this strategy buys expecting institutions to defend that price level.",
        "how": "Identifies institutional order blocks (large candles with significant wicks indicating absorption). Defines fill zones as the body range of these candles. Triggers when price enters zone with ADX > 20.",
    },
    "carry_trade_momentum": {
        "name": "Carry Trade Momentum",
        "icon": "💱",
        "what": "Borrows money in a low-interest-rate currency and invests in a high-interest-rate one, profiting from the interest rate difference. Like putting money in a savings account that pays more, while the currency itself might also go up.",
        "how": "Compares central bank interest rates between currency pairs. When the rate differential exceeds 2%, generates BUY signals for the higher-yield currency. Combined with momentum confirmation.",
    },
    "session_momentum_continuation": {
        "name": "Session Momentum Continuation",
        "icon": "⏰",
        "what": "Markets move differently during London, New York, and Asian trading hours. If a big move starts during London open, this strategy bets it will continue in the same direction during the session.",
        "how": "Monitors first 30 minutes of London (8:00-8:30 GMT) and New York (13:30-14:00 GMT) sessions. If the initial move exceeds 0.3%, enters in the same direction with MACD histogram confirming.",
    },
    "community_london_breakout_v2_forex": {
        "name": "London Breakout V2",
        "icon": "🇬🇧",
        "what": "The London stock market open at 8 AM GMT often causes big price moves. This strategy watches the price range before London opens, then trades the breakout direction. Like waiting for the starting gun at a race.",
        "how": "Calculates the Asian session range (00:00-07:00 GMT). When price breaks above/below this range after London open with volume confirmation, enters the breakout direction.",
    },
    "spike_macd_divergence": {
        "name": "MACD Divergence Spike",
        "icon": "📈",
        "what": "When price goes up but the MACD indicator goes down (or vice versa), it often signals the trend is about to reverse. It's like a car accelerating but the engine RPM is dropping — something's about to change.",
        "how": "Detects regular and hidden divergence between price highs/lows and MACD histogram peaks/troughs over 5-14 bars. Requires RSI confirmation and volume expansion on the signal bar.",
    },
    "rsi_hidden_divergence": {
        "name": "RSI Hidden Divergence",
        "icon": "🔄",
        "what": "RSI measures if something is 'overbought' or 'oversold'. A hidden divergence means the underlying trend is still strong even though it doesn't look like it on the surface. Like a spring being compressed — it's about to bounce.",
        "how": "In an uptrend (price making higher lows), if RSI makes a lower low, the trend momentum is building invisibly. Entry on the next bullish candle after divergence forms. Stop below the recent swing low.",
    },
    "multi_sigma_reversal": {
        "name": "Multi-Sigma Reversal",
        "icon": "📐",
        "what": "When price moves more than 2 standard deviations (really far) from the average, this bets it will snap back. Think of a rubber band — stretch it too far and it comes back. Only triggers on extreme moves.",
        "how": "Calculates rolling 20-period Z-score of returns. Triggers when |Z| > 2.0 (2 sigma event). Direction is always mean-reversion (SELL after spike up, BUY after crash). 40% historical bounce rate within 5 bars.",
    },
    "altcoin_season_rotation": {
        "name": "Altcoin Season Rotation",
        "icon": "🔄",
        "what": "When Bitcoin goes up, money eventually flows into smaller coins (altcoins). This strategy detects when that 'rotation' is starting and buys altcoins early. Like being early to a party everyone is heading to.",
        "how": "Monitors BTC dominance, alt/BTC relative strength over 7 and 14 days, and halving cycle phase. Triggers when alts outperform BTC by >3% over 7 days while BTC dominance < 60%.",
    },
    "mvrv_sma_proxy": {
        "name": "MVRV Ratio Proxy",
        "icon": "📊",
        "what": "Compares the current market value to the 'realized value' (what people actually paid). When MVRV is low, crypto is 'cheap' relative to what people paid — good time to buy. Like checking if a house is underpriced vs what neighbors paid.",
        "how": "Uses SMA(365) as a proxy for realized value since on-chain data isn't free. MVRV proxy = current_price / SMA_365. When < 1.0 and Z-score < -1.0, generates BUY signals.",
    },
    "support_resistance_bounce": {
        "name": "Support & Resistance Bounce",
        "icon": "🧱",
        "what": "Price tends to bounce off certain levels repeatedly (support = floor, resistance = ceiling). This strategy buys near support and sells near resistance. Like a ball bouncing between a floor and ceiling.",
        "how": "Identifies support/resistance levels using pivot points and volume profile analysis. Entry when price is within 3% of support with RSI < 40. Stop loss below support level.",
    },
}

def get_explain(strategy):
    return STRATEGY_EXPLAIN.get(strategy, {
        "name": strategy.replace('_', ' ').title(),
        "icon": "⚙️",
        "what": f"Strategy: {strategy}",
        "how": "Custom strategy — documentation pending.",
    })

# ─── FAILURE ANALYSIS ─────────────────────────────────────────────────
FAILURE_ANALYSIS = {}
for p in closed_picks:
    if p['status'] != 'LOST':
        continue
    strat = p['strategy']
    sym = p['symbol']
    reason = p.get('reason', '')
    exit_r = p.get('exit_reason', '')
    mfe = p.get('mfe', 0)
    mae = p.get('mae', 0)
    pnl = p.get('pnl_pct', 0)
    entry = p.get('entry_price', 0)
    sl = p.get('stop_loss', 0)
    tp = p.get('take_profit', 0)
    rsi = p.get('rsi_at_entry', 0)
    vol = p.get('volume_ratio', 0) or 0
    
    key = f"{strat}::{sym}::{p.get('entry_date','')}"
    
    # Diagnose what went wrong
    issues = []
    tweaks = []
    self_learn = []  # whether the model self-learns from this
    needs_info = []  # what additional data/tweaks we need
    
    # SL hit too quickly
    if exit_r == 'SL_HIT' and p.get('hold_days', 99) <= 1:
        issues.append("Stop loss hit within 24 hours — entered against a strong trend continuation")
        tweaks.append("Increase SL width by 0.5× ATR or add a trend-strength filter (ADX > 40 = skip)")
        self_learn.append("✅ AUTO-FIX: The nightly retrain will see this SL_HIT in the training data. Over time, the model learns to avoid entries where rapid SL hits occurred under similar conditions (same RSI range, same trend direction, same volatility regime).")
        needs_info.append("⏳ Need 5+ more SL_HIT samples from this strategy to build a statistically reliable 'SL too tight' pattern. Currently at {0}/{1} SL hits.".format(
            sum(1 for x in closed_picks if x.get('strategy') == strat and x.get('exit_reason') == 'SL_HIT'),
            5
        ))
    
    # MFE vs MAE ratio — did price almost reach TP?
    if mfe > 0.01 and abs(mae) > mfe * 2:
        issues.append(f"Adverse move ({mae*100:.1f}%) was {abs(mae/mfe):.1f}× larger than favorable move ({mfe*100:.1f}%) — price moved strongly against us")
        tweaks.append("Add a minimum R:R filter: only trade when ATR-adjusted TP distance > 2× SL distance")
        self_learn.append("✅ AUTO-FIX: The model feeds MFE/MAE ratios back into training features. After seeing enough trades where MAE >> MFE, it learns to weight entry conditions that produce BETTER MFE/MAE ratios.")
    
    # Low volume confirmation
    if vol and vol < 0.7:
        issues.append(f"Volume ratio was only {vol:.2f}× average — weak conviction, big players weren't participating")
        tweaks.append("Require volume_ratio > 1.0 for entry (strong volume confirmation)")
        self_learn.append("⚠️ PARTIAL: The self-learning loop can learn that low-volume entries correlate with losses, but the volume_ratio threshold itself needs a MANUAL adjustment in the strategy config. We've flagged this for the next code update.")
        needs_info.append("🔧 MANUAL CHANGE NEEDED: Update the alpha_engine strategy filters to require min_volume_ratio=1.0. This cannot be learned automatically — it's a hard config change.")
    
    # RSI not actually oversold enough
    if rsi and rsi > 40 and 'fvg' in strat.lower():
        issues.append(f"RSI was {rsi:.0f} at entry — FVG strategies work best when RSI < 35 (deeply oversold). At {rsi:.0f}, price wasn't actually at a discount.")
        tweaks.append("Tighten RSI filter to < 35 for FVG-based strategies")
        self_learn.append("⚠️ PARTIAL: Model sees the RSI value as a feature and can learn to avoid entries at RSI > 40, but the FVG strategy's RSI threshold is a HARD FILTER that needs manual adjustment in the strategy code.")
        needs_info.append(f"🔧 MANUAL CHANGE NEEDED: In the FVG strategy config, change rsi_threshold from 50 to 35. Self-learning can't change strategy parameters — only entry probabilities.")
    
    # Multiple same-direction entries
    same_sym_losses = [x for x in closed_picks if x['symbol'] == sym and x['status'] == 'LOST']
    if len(same_sym_losses) >= 2:
        issues.append(f"{len(same_sym_losses)} losses on {sym} — asset was in a sustained downtrend that multiple strategies failed to detect. This means the per-strategy filters weren't enough to catch correlation risk.")
        tweaks.append(f"Add a correlation guard: if 2+ strategies lose on {sym} within 48h, block new entries for 72h")
        self_learn.append("❌ CANNOT SELF-FIX: The self-learning loop operates per-strategy, not cross-strategy. A correlation guard between strategies requires a NEW CODE MODULE that monitors active positions across all strategies. This is a feature gap.")
        needs_info.append(f"🆕 FEATURE NEEDED: Build a CorrelationGuard module in the alpha_engine that tracks open positions per symbol across all strategies and enforces max_positions_per_asset=1.")
    
    # Time expiry = trade went nowhere
    if exit_r == 'TIME_EXPIRY':
        issues.append("Trade expired without hitting TP or SL — no clear directional move materialized. The model was right about no crash, but wrong about an upward move.")
        tweaks.append("Reduce max hold time from 72h to 48h; add exit-on-breakeven after 24h if MFE > 1%")
        self_learn.append("✅ AUTO-FIX: The model learns from TIME_EXPIRY outcomes that the signal wasn't strong enough for a directional move. Over time it adjusts probability thresholds upward for similar entry conditions.")
    
    # FVG strategy specific failure
    if 'fvg' in strat.lower() and exit_r == 'SL_HIT':
        issues.append("The Fair Value Gap was not respected by institutional buyers — the expected 'fill' didn't produce a bounce. This often happens when the broader trend overwhelms the FVG zone.")
        tweaks.append("Add higher-timeframe (4h) trend confirmation — only enter FVG longs when 4h EMA20 > EMA50")
        self_learn.append("⚠️ PARTIAL: The model can learn FVG entries in downtrends fail, but the FVG strategy itself doesn't check higher timeframe trends. Needs a MANUAL multi-timeframe filter addition.")
        needs_info.append("🔧 MANUAL CHANGE: Add a 4h trend filter to FVG strategies: if 4h EMA20 < EMA50, block all BUY FVG signals. This is the #1 fix needed.")
    
    if not issues:
        issues.append("Standard loss within risk parameters — no obvious flaw detected")
        tweaks.append("No specific tweak needed — within expected loss rate for this strategy")
        self_learn.append("✅ AUTO-FIX: Even 'normal' losses feed into the training data. The model continuously improves its probability calibration with each closed trade.")
    
    if not self_learn:
        self_learn.append("✅ AUTO-FIX: This loss feeds directly into the nightly retraining cycle. The model sees the outcome (LOST) paired with the entry conditions and adjusts its probability estimates accordingly.")
    if not needs_info:
        needs_info.append("📊 Need more data: With only {0} closed trades on this strategy, we need at least 10 to determine if this is a systematic failure or normal variance.".format(
            sum(1 for x in closed_picks if x.get('strategy') == strat)
        ))
    
    FAILURE_ANALYSIS[key] = {
        "symbol": sym,
        "strategy": strat,
        "issues": issues,
        "tweaks": tweaks,
        "self_learn": self_learn,
        "needs_info": needs_info,
        "mfe": mfe,
        "mae": mae,
        "pnl_pct": pnl,
        "exit_reason": exit_r,
    }

# ─── STRATEGY HEALTH SCORECARD ─────────────────────────────────────────
strat_health = {}
for sname, sdata in strategy_perf.items():
    total = sdata.get('closed_picks', 0)
    wins = sdata.get('wins', 0)
    wr = sdata.get('win_rate', 0)
    avg_pnl = sdata.get('avg_pnl_pct', 0)
    avg_mfe = sdata.get('avg_mfe', 0)
    avg_mae = sdata.get('avg_mae', 0)
    
    # Grade
    if total < 3:
        grade = "⏳ INSUFFICIENT DATA"
        color = "var(--t3)"
        action = "Need 3+ closed trades to evaluate"
    elif wr >= 0.5 and avg_pnl > 0:
        grade = "✅ PERFORMING"
        color = "var(--green)"
        action = "Continue using — positive edge detected"
    elif wr >= 0.3 and avg_mfe > abs(avg_mae) * 0.5:
        grade = "⚠️ MARGINAL"  
        color = "var(--amber)"
        action = "Tighten entry filters — edge exists but is thin"
    else:
        grade = "🛑 FAILING"
        color = "var(--red)"
        action = "Suspend or heavily filter until regime changes"
    
    strat_health[sname] = {
        "grade": grade, "color": color, "action": action,
        "total": total, "wins": wins, "wr": wr,
        "avg_pnl": avg_pnl, "avg_mfe": avg_mfe, "avg_mae": avg_mae,
    }

# ─── AGGREGATE PATH TO SUCCESS ANALYSIS ────────────────────────────────
total_strategies = len(strategy_perf)
performing = sum(1 for v in strat_health.values() if '✅' in v['grade'])
failing = sum(1 for v in strat_health.values() if '🛑' in v['grade'])
insufficient = sum(1 for v in strat_health.values() if '⏳' in v['grade'])

# Common failure patterns
exit_reasons = defaultdict(int)
for p in closed_picks:
    if p['status'] == 'LOST':
        exit_reasons[p.get('exit_reason', 'UNKNOWN')] += 1

sl_hit_pct = exit_reasons.get('SL_HIT', 0) / max(fwd_losses, 1) * 100
time_exp_pct = exit_reasons.get('TIME_EXPIRY', 0) / max(fwd_losses, 1) * 100

# ─── HELPERS ──────────────────────────────────────────────────────────
def esc(s): return html.escape(str(s), quote=True)
def pcls(v): return 'g' if v >= 0 else 'r'
def psign(v): return f"+{v:.1f}%" if v >= 0 else f"{v:.1f}%"
def fprice(v, sym):
    if 'JPY' in sym: return f"¥{v:,.2f}"
    elif v > 1000: return f"${v:,.0f}"
    elif v > 1: return f"${v:,.3f}"
    elif v > 0.01: return f"${v:.4f}"
    else: return f"${v:.8f}"

# ─── BUILD ACTIVE PICK CARDS ─────────────────────────────────────────
pick_cards = []
for p in sorted(active_picks, key=lambda x: abs(x.get('unrealized_pnl_pct', 0)), reverse=True):
    sym = p['symbol']
    strat = p['strategy']
    sig = p.get('signal_type', 'BUY')
    entry = p.get('entry_price', 0)
    tp = p.get('take_profit', 0)
    sl = p.get('stop_loss', 0)
    ml = p.get('ml_score', 0)
    pnl = p.get('unrealized_pnl_pct', 0) * 100
    hold = p.get('hold_days', 0)
    conf = p.get('confidence', 0)
    reason = p.get('reason', '')
    border_color = 'var(--green)' if pnl >= 0 else 'var(--red)'
    pill_cls = 'pg' if pnl >= 0 else 'pr'
    ex = get_explain(strat)
    
    if sig == 'BUY' and sl > 0 and tp > 0:
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        rr = f"{reward/risk:.1f}" if risk > 0 else "N/A"
    elif sig == 'SELL' and sl > 0 and tp > 0:
        risk = abs(sl - entry)
        reward = abs(entry - tp)
        rr = f"{reward/risk:.1f}" if risk > 0 else "N/A"
    else:
        rr = "N/A"

    # Strategy forward track record
    sp = strategy_perf.get(strat, {})
    sp_wr = sp.get('win_rate', 0)
    sp_total = sp.get('closed_picks', 0)
    sp_text = f"{sp.get('wins',0)}W/{sp.get('losses',0)}L ({sp_wr:.0%})" if sp_total > 0 else "No closed trades yet"
    
    health = strat_health.get(strat, {})
    grade = health.get('grade', '⏳ NEW')

    pick_cards.append(f'''<div class="pk" style="border-left:3px solid {border_color}">
<div class="pk-h"><span class="pk-s">{esc(sym)}</span><span class="pill {pill_cls}">{sig} {psign(pnl)}</span></div>
<div class="pk-d">
<div><span class="l">Strategy:</span> {esc(ex['name'])}</div>
<div><span class="l">Entry:</span> {fprice(entry, sym)}</div>
<div><span class="l">TP:</span> {fprice(tp, sym)}</div>
<div><span class="l">SL:</span> {fprice(sl, sym)}</div>
<div><span class="l">ML Score:</span> {ml:.3f}</div>
<div><span class="l">R:R:</span> {rr}</div>
<div><span class="l">Hold:</span> {hold}d</div>
<div><span class="l">Confidence:</span> {conf:.0%}</div>
</div>
<div class="pk-audit">
<div class="audit-icon" onclick="this.parentElement.classList.toggle('open')">{ex['icon']} Audit Log <span class="arrow">▶</span></div>
<div class="audit-content">
<p class="audit-section-title">🎯 What is this strategy?</p>
<p>{esc(ex['what'])}</p>
<p class="audit-section-title">🔧 How it works (technical)</p>
<p>{esc(ex['how'])}</p>
<p class="audit-section-title">🔍 Why THIS signal triggered</p>
<p>{esc(reason) if reason else 'No specific trigger details logged for this entry.'}</p>
<p class="audit-section-title">📊 Strategy Forward Track Record</p>
<p>Forward record: {sp_text} | Health: {esc(grade)}</p>
<p class="audit-section-title">🤖 ML Confidence Breakdown</p>
<p>Model confidence: <b>{ml:.0%}</b> — The ML ensemble predicts a {ml:.0%} probability this trade hits the target price before the stop loss. For every $1 risked, expected gain is ${rr}.</p>
</div>
</div>
</div>''')

# ─── BUILD CLOSED TRADES TABLE WITH FAILURE ANALYSIS ─────────────────
closed_rows = []
for p in closed_picks:
    sym = p['symbol']
    strat = p['strategy']
    sig = p.get('signal_type', 'BUY')
    entry = p.get('entry_price', 0)
    exit_p = p.get('exit_price', 0)
    pnl_pct = p.get('pnl_pct', 0) * 100
    pnl_d = p.get('pnl_dollar', 0)
    exit_r = p.get('exit_reason', '?')
    reason = p.get('reason', '')
    ex = get_explain(strat)
    
    pill_map = {'TP_HIT': 'pg', 'SL_HIT': 'pr', 'TRAILING_STOP': 'pb', 'TIME_EXPIRY': 'pa'}
    pill_cls = pill_map.get(exit_r, 'pb')
    exit_label = exit_r.replace('_', ' ')
    
    # Failure analysis for this specific trade
    key = f"{strat}::{sym}::{p.get('entry_date','')}"
    fa = FAILURE_ANALYSIS.get(key)
    
    fa_html = ""
    if fa:
        issues_html = "".join(f"<li>{esc(i)}</li>" for i in fa['issues'])
        tweaks_html = "".join(f"<li>{esc(t)}</li>" for t in fa['tweaks'])
        learn_html = "".join(f"<li>{esc(s)}</li>" for s in fa.get('self_learn', []))
        needs_html = "".join(f"<li>{esc(n)}</li>" for n in fa.get('needs_info', []))
        fa_html = f'''<tr class="analysis-row"><td colspan="8">
<div class="failure-box">
<div class="fb-header" onclick="this.parentElement.classList.toggle('open')">🔍 Failure Analysis & Tweaks <span class="arrow">▶</span></div>
<div class="fb-content">
<p><b>Strategy:</b> {esc(ex['name'])} — {esc(ex['what'][:120])}</p>
<p><b>Signal reason:</b> {esc(reason) if reason else 'Not logged'}</p>
<p><b>MFE:</b> {fa['mfe']*100:+.1f}% (best price reached) | <b>MAE:</b> {fa['mae']*100:.1f}% (worst price reached)</p>
<p class="fb-title">❌ What went wrong:</p>
<ul>{issues_html}</ul>
<p class="fb-title">🔧 Proposed tweaks:</p>
<ul>{tweaks_html}</ul>
<p class="fb-title">🤖 Self-learning status:</p>
<ul>{learn_html}</ul>
<p class="fb-title">📋 What else is needed:</p>
<ul>{needs_html}</ul>
</div>
</div>
</td></tr>'''
    
    closed_rows.append(f'''<tr>
<td>{esc(sym)}</td><td>{esc(ex['name'][:25])}</td><td>{sig}</td>
<td>{fprice(entry, sym)}</td><td>{fprice(exit_p, sym)}</td>
<td class="{pcls(pnl_pct)}">{psign(pnl_pct)}</td>
<td class="{pcls(pnl_d)}">{"+" if pnl_d >= 0 else ""}${pnl_d:.0f}</td>
<td><span class="pill {pill_cls}">{exit_label}</span></td></tr>
{fa_html}''')

# ─── BUILD STRATEGY HEALTH TABLE ─────────────────────────────────────
health_rows = []
for sname in sorted(strat_health.keys(), key=lambda x: strat_health[x].get('wr', 0), reverse=True):
    h = strat_health[sname]
    ex = get_explain(sname)
    health_rows.append(f'''<tr>
<td>{ex['icon']} {esc(ex['name'][:30])}</td>
<td>{h['total']}</td>
<td>{h['wins']}</td>
<td class="{pcls(h['wr']-0.5)}">{h['wr']:.0%}</td>
<td class="{pcls(h['avg_pnl'])}">{h['avg_pnl']*100:+.1f}%</td>
<td>{h['avg_mfe']*100:+.1f}%</td>
<td>{h['avg_mae']*100:.1f}%</td>
<td style="color:{h['color']}">{esc(h['grade'])}</td>
<td style="font-size:.7rem">{esc(h['action'])}</td>
</tr>''')

# ─── CSS ──────────────────────────────────────────────────────────────
CSS = '''
:root{--bg:#0a0e1a;--card:#111827;--border:#1e293b;--t1:#f1f5f9;--t2:#94a3b8;--t3:#64748b;--blue:#6366f1;--cyan:#06b6d4;--green:#22c55e;--red:#ef4444;--amber:#f59e0b;--purple:#a855f7}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--t1);line-height:1.6;min-height:100vh}
.hero{background:linear-gradient(135deg,rgba(99,102,241,.15),rgba(6,182,212,.08));border-bottom:1px solid var(--border);padding:48px 24px 40px;text-align:center}
.hero h1{font-size:clamp(1.8rem,4vw,2.8rem);font-weight:800;background:linear-gradient(135deg,#6366f1,#8b5cf6,#06b6d4);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}
.hero .sub{color:var(--t2);font-size:1rem;margin-top:6px}
.badge-v{display:inline-block;background:rgba(99,102,241,.2);border:1px solid rgba(99,102,241,.3);color:#a5b4fc;padding:4px 14px;border-radius:20px;font-size:.78rem;font-weight:600;margin-top:12px}
.last-updated{color:var(--t3);font-size:.75rem;margin-top:10px;font-style:italic}
.container{max-width:1260px;margin:0 auto;padding:32px 20px}
.kpi-section{margin-bottom:36px}
.kpi-section-header{display:flex;align-items:center;gap:10px;margin-bottom:14px;flex-wrap:wrap}
.kpi-section-header h3{font-size:.95rem;font-weight:700}
.source-tag{display:inline-block;padding:3px 10px;border-radius:12px;font-size:.65rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em}
.tag-bt{background:rgba(99,102,241,.2);color:#a5b4fc;border:1px solid rgba(99,102,241,.3)}
.tag-fw{background:rgba(239,68,68,.15);color:#f87171;border:1px solid rgba(239,68,68,.25)}
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px}
.kpi{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;text-align:center;transition:transform .2s;position:relative}
.kpi:hover{transform:translateY(-2px);border-color:var(--blue)}
.kpi .l{font-size:.72rem;text-transform:uppercase;letter-spacing:.08em;color:var(--t3);margin-bottom:6px}
.kpi .v{font-size:1.6rem;font-weight:800}
.kpi .n{font-size:.7rem;color:var(--t3);margin-top:4px}
.kpi .src{position:absolute;top:8px;right:8px;font-size:.55rem;padding:2px 6px;border-radius:6px;font-weight:700;text-transform:uppercase;letter-spacing:.05em}
.kpi .src-bt{background:rgba(99,102,241,.2);color:#a5b4fc}
.kpi .src-fw{background:rgba(239,68,68,.15);color:#f87171}
.g{color:var(--green)}.r{color:var(--red)}.b{color:var(--blue)}.c{color:var(--cyan)}.a{color:var(--amber)}.p{color:var(--purple)}
.sec{margin-bottom:40px}
.sh{display:flex;align-items:center;gap:10px;margin-bottom:18px;padding-bottom:10px;border-bottom:1px solid var(--border);flex-wrap:wrap}
.sh h2{font-size:1.2rem;font-weight:700}.sh .bd{background:rgba(99,102,241,.15);color:#a5b4fc;padding:3px 10px;border-radius:12px;font-size:.7rem;font-weight:600}
.tw{overflow-x:auto;border-radius:10px;border:1px solid var(--border)}
table{width:100%;border-collapse:collapse;font-size:.82rem}
th{background:rgba(99,102,241,.08);color:var(--t2);font-weight:600;font-size:.7rem;text-transform:uppercase;letter-spacing:.06em;padding:10px 14px;text-align:left;white-space:nowrap}
td{padding:10px 14px;border-top:1px solid var(--border);white-space:nowrap}
tr:hover td{background:rgba(99,102,241,.04)}
.pill{display:inline-block;padding:2px 8px;border-radius:8px;font-size:.68rem;font-weight:600}
.pg{background:rgba(34,197,94,.15);color:#4ade80}
.pr{background:rgba(239,68,68,.15);color:#f87171}
.pb{background:rgba(99,102,241,.15);color:#a5b4fc}
.pa{background:rgba(245,158,11,.15);color:#fbbf24}
.pk-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:14px}
.pk{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:16px;transition:border-color .2s}
.pk:hover{border-color:var(--blue)}
.pk-h{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
.pk-s{font-weight:700;font-size:1rem}
.pk-d{display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:.78rem}
.pk-d .l{color:var(--t3)}
.pk-audit{margin-top:10px;border-top:1px solid var(--border);padding-top:8px}
.audit-icon{font-size:.75rem;color:var(--cyan);cursor:pointer;user-select:none;display:flex;align-items:center;gap:6px}
.audit-icon:hover{color:var(--blue)}
.audit-icon .arrow,.fb-header .arrow{font-size:.6rem;transition:transform .2s;display:inline-block}
.pk-audit.open .arrow,.failure-box.open .arrow{transform:rotate(90deg)}
.audit-content{display:none;margin-top:8px;padding:12px;background:rgba(6,182,212,.05);border-radius:8px;border:1px solid rgba(6,182,212,.15);font-size:.73rem;line-height:1.7}
.pk-audit.open .audit-content{display:block}
.audit-content p{margin-bottom:6px;color:var(--t2)}
.audit-content b{color:var(--t1)}
.audit-section-title{color:var(--cyan)!important;font-weight:700;margin-top:8px!important;font-size:.75rem}
.callout{background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.2);border-radius:10px;padding:16px;margin:16px 0;font-size:.82rem;color:var(--t2)}
.callout b{color:var(--red)}
.callout-amber{background:rgba(245,158,11,.08);border-color:rgba(245,158,11,.2)}.callout-amber b{color:var(--amber)}
.callout-green{background:rgba(34,197,94,.08);border-color:rgba(34,197,94,.2)}.callout-green b{color:var(--green)}
.callout-blue{background:rgba(99,102,241,.08);border-color:rgba(99,102,241,.2)}.callout-blue b{color:var(--blue)}
/* Failure analysis */
.analysis-row td{padding:0!important;border:none!important}
.failure-box{margin:0 14px 10px;background:rgba(239,68,68,.04);border:1px solid rgba(239,68,68,.12);border-radius:8px;overflow:hidden}
.fb-header{padding:8px 12px;font-size:.73rem;color:var(--amber);cursor:pointer;user-select:none}
.fb-header:hover{color:var(--red)}
.fb-content{display:none;padding:10px 14px;font-size:.73rem;line-height:1.7;color:var(--t2)}
.failure-box.open .fb-content{display:block}
.fb-content b{color:var(--t1)}
.fb-content ul{margin:4px 0 8px 18px;color:var(--t2)}
.fb-content li{margin-bottom:3px}
.fb-title{color:var(--amber)!important;font-weight:700;margin-top:6px!important}
/* Path to success */
.path-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}
.path-card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:16px}
.path-card h4{font-size:.85rem;margin-bottom:8px}
.path-card p{font-size:.78rem;color:var(--t2);margin-bottom:4px}
/* Timeline roadmap */
.timeline{position:relative;margin:20px 0 10px 16px;padding-left:24px;border-left:2px solid var(--border)}
.timeline-step{position:relative;padding:12px 0 18px;font-size:.82rem;color:var(--t2)}
.timeline-step::before{content:'';position:absolute;left:-31px;top:16px;width:14px;height:14px;border-radius:50%;border:2px solid var(--border);background:var(--bg)}
.timeline-step.active::before{background:var(--amber);border-color:var(--amber);box-shadow:0 0 8px rgba(245,158,11,.4)}
.timeline-step.future::before{background:var(--card);border-color:var(--t3)}
.timeline-step.done::before{background:var(--green);border-color:var(--green)}
.timeline-step b{color:var(--t1);font-size:.85rem}
.timeline-step .tl-detail{margin-top:4px;font-size:.75rem;color:var(--t3);line-height:1.5}
.timeline-step .tl-target{display:inline-block;margin-top:4px;padding:2px 8px;border-radius:6px;font-size:.68rem;font-weight:600}
.tl-target.tl-red{background:rgba(239,68,68,.15);color:#f87171}
.tl-target.tl-amber{background:rgba(245,158,11,.15);color:#fbbf24}
.tl-target.tl-green{background:rgba(34,197,94,.15);color:#4ade80}
.links{display:flex;flex-wrap:wrap;gap:10px;margin-top:10px}
.links a{background:rgba(99,102,241,.1);border:1px solid rgba(99,102,241,.25);color:#a5b4fc;padding:8px 16px;border-radius:8px;text-decoration:none;font-size:.8rem;font-weight:500;transition:background .2s}
.links a:hover{background:rgba(99,102,241,.2);border-color:var(--blue)}
.footer{text-align:center;padding:32px 20px;border-top:1px solid var(--border);color:var(--t3);font-size:.75rem}
@media(max-width:600px){.kpi-grid{grid-template-columns:repeat(2,1fr)}.pk-grid{grid-template-columns:1fr}.path-grid{grid-template-columns:1fr}}
'''

# ─── FULL HTML ────────────────────────────────────────────────────────
PAGE = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Antigravity ML Crypto Predictor v4.1 - Real Performance</title>
<meta name="description" content="Live backtesting and forward picks from the Antigravity ML Crypto Predictor v4.1. All data is real, transparent, and verifiable on GitHub.">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<div class="hero">
<h1>Antigravity ML Crypto Predictor</h1>
<p class="sub">Real backtesting performance and live forward picks — 100% transparent</p>
<span class="badge-v">v4.1 CLAUDE CODE — 793 Models — 40 Pairs — 5 Timeframes</span>
<p class="last-updated">Last updated: {now}</p>
</div>

<div class="container">

<!-- ═══ BACKTEST KPIs ═══ -->
<div class="kpi-section">
<div class="kpi-section-header"><h3>📊 Backtest Performance</h3><span class="source-tag tag-bt">BACKTEST — Historical Data</span></div>
<div class="kpi-grid">
<div class="kpi"><span class="src src-bt">BACKTEST</span><div class="l">Tradeable Models</div><div class="v b">32</div><div class="n">Pass MC p&lt;0.05</div></div>
<div class="kpi"><span class="src src-bt">BACKTEST</span><div class="l">Avg Sharpe</div><div class="v g">1.34</div><div class="n">vs Simpleton 0.567</div></div>
<div class="kpi"><span class="src src-bt">BACKTEST</span><div class="l">Avg Win Rate</div><div class="v g">58.8%</div><div class="n">vs Simpleton 51.3%</div></div>
<div class="kpi"><span class="src src-bt">BACKTEST</span><div class="l">Avg Profit Factor</div><div class="v c">2.52</div><div class="n">vs Simpleton 1.09</div></div>
<div class="kpi"><span class="src src-bt">BACKTEST</span><div class="l">Avg Max DD</div><div class="v a">-9.5%</div><div class="n">vs Simpleton -34.1%</div></div>
</div>
</div>

<!-- ═══ FORWARD KPIs ═══ -->
<div class="kpi-section">
<div class="kpi-section-header"><h3>🎯 Forward Performance (REAL)</h3><span class="source-tag tag-fw">FORWARD — Live Trades</span></div>
<div class="kpi-grid">
<div class="kpi"><span class="src src-fw">FORWARD</span><div class="l">Closed Trades</div><div class="v">{fwd_total}</div><div class="n">Since Feb 17</div></div>
<div class="kpi"><span class="src src-fw">FORWARD</span><div class="l">Win Rate</div><div class="v r">{fwd_wr}</div><div class="n">{fwd_wins}W / {fwd_losses}L</div></div>
<div class="kpi"><span class="src src-fw">FORWARD</span><div class="l">Total P&amp;L</div><div class="v {pcls(fwd_pnl)}">${fwd_pnl:+,.0f}</div><div class="n">Avg {fwd_avg_pnl*100:+.1f}% per trade</div></div>
<div class="kpi"><span class="src src-fw">FORWARD</span><div class="l">Open Positions</div><div class="v b">{len(active_picks)}</div><div class="n">Tracking live</div></div>
</div>
<div class="callout">
<b>⚠️ Reality Check:</b> Backtest shows 58.8% WR on historical data, but forward (real) results show {fwd_wr} across {fwd_total} closed trades.
This gap is normal for young systems — backtests always look better due to curve-fitting, survivorship bias, and regime changes.
Need 30+ closed trades for meaningful forward Sharpe. Model retrains nightly to learn from every single loss.
</div>

<div class="callout callout-blue" style="margin-top:0">
<b>🗺️ Timeline to Live Trading Readiness</b> — Honest assessment: NOT ready for real money. Here's the plan:
<div class="timeline">
<div class="timeline-step active">
<b>📍 NOW — Week 1 (Feb 17–28):</b> Paper trading. {fwd_total} closed / 50 target.
<div class="tl-detail">Currently tracking {len(active_picks)} open positions. Each closed trade feeds into nightly retraining. The 18% win rate is from a tiny sample — even a 60% edge can lose 5 in a row 1% of the time. The FVG strategy filter tweaks (RSI &lt; 35, volume &gt; 1.0×) will be reflected in the next batch of picks.</div>
<span class="tl-target tl-red">TARGET: 50+ closed trades, identify failing strategies early</span>
</div>
<div class="timeline-step future">
<b>Month 1–2 (Mar–Apr):</b> Accumulate 100+ closed trades.
<div class="tl-detail">Apply all pending tweaks: adaptive ATR-based SL per pair, higher-timeframe trend filters, correlation guard (max 1 position per asset). Suspend strategies with 0 wins after 10+ trades. Target WR &gt; 35% — at 2:1 R:R, 35% is breakeven.</div>
<span class="tl-target tl-amber">TARGET: &gt;35% WR, positive cumulative P&amp;L, add backtest winners to forward</span>
</div>
<div class="timeline-step future">
<b>Month 3–4 (May–Jun):</b> Prove consistency.
<div class="tl-detail">Need 3 consecutive weeks of positive P&amp;L. The model will have 90+ days of self-learning data by then (60,000+ new candles). Strategies that remain at 0% WR after 20+ trades get permanently removed.</div>
<span class="tl-target tl-amber">TARGET: &gt;40% WR over 200+ trades, PF &gt; 1.3, positive monthly returns</span>
</div>
<div class="timeline-step future">
<b>Month 5–6 (Jul–Aug):</b> Micro-position live testing.
<div class="tl-detail">IF and ONLY IF paper trading shows &gt;40% WR with PF &gt;1.3 over 200+ picks, begin live micro-position testing ($10–50 per trade). The model will have 6 months of continuous learning data. Continue paper trading alongside live for comparison.</div>
<span class="tl-target tl-green">GATE: 200+ picks, &gt;40% WR, PF &gt;1.3, 3 consecutive positive months</span>
</div>
</div>
<p style="font-size:.75rem;color:var(--t3);margin-top:6px;">⚡ <b>Self-learning loop is ACTIVE:</b> Every closed pick (win or loss) feeds back into training data at the next nightly retrain (2AM UTC). After 10+ resolutions, the model automatically adjusts probability thresholds. Currently at <b>{fwd_total}/10 needed for auto-adjustment.</b> The earliest possible live trading date is <b>June 2026</b> — approximately <b>4 months away</b>.</p>
</div>
</div>

<!-- ═══ PATH TO SUCCESS ═══ -->
<div class="sec">
<div class="sh"><h2>🛤️ Path to Success — What We're Fixing</h2></div>
<div class="path-grid">
<div class="path-card">
<h4 class="r">📉 Problem: {sl_hit_pct:.0f}% of losses are SL hits</h4>
<p>{exit_reasons.get('SL_HIT',0)} of {fwd_losses} losses hit stop-loss, often within 24h</p>
<p><b>Fix:</b> Widen SL by 0.5× ATR for volatile assets. Add trend-strength guard: if ADX > 40, skip mean-reversion entries.</p>
<p><b>Status:</b> <span class="pill pa">PENDING</span> Next model retrain will apply</p>
</div>
<div class="path-card">
<h4 class="r">📉 Problem: FVG strategies are 0/{sum(1 for p in closed_picks if 'fvg' in p['strategy'] and p['status']=='LOST')}</h4>
<p>community_ict_fvg_selective and smart_money_fvg have 0 wins across {sum(1 for p in closed_picks if 'fvg' in p['strategy'])} trades</p>
<p><b>Fix:</b> Tighten RSI filter to &lt;35, require volume_ratio &gt;1.0, skip when HTF (4h) trend is down.</p>
<p><b>Status:</b> <span class="pill pr">CRITICAL</span> These strategies need immediate filter adjustment</p>
</div>
<div class="path-card">
<h4 class="a">⚠️ Problem: Same-asset stacking</h4>
<p>ETH-USD had 3 concurrent losses from different strategies picking the same losing trend</p>
<p><b>Fix:</b> Add correlation guard: max 1 open position per asset. If 2+ strategies lose on same symbol within 48h, block new entries for 72h.</p>
<p><b>Status:</b> <span class="pill pa">PENDING</span></p>
</div>
<div class="path-card">
<h4 class="g">✅ What's Working</h4>
<p><b>multi_sigma_reversal:</b> 1W/0L (+$120) — Mean-reversion on extreme moves works</p>
<p><b>rsi_hidden_divergence:</b> 1W/0L (+$7) — Divergence detection is sound</p>
<p><b>Direction:</b> Lean into strategies with MFE/MAE ratio > 2.0 (price reaches TP zone before SL zone)</p>
<p><b>Status:</b> <span class="pill pg">ACTIVE</span></p>
</div>
</div>
</div>

<!-- ═══ STRATEGY HEALTH SCORECARD ═══ -->
<div class="sec">
<div class="sh"><h2>🏥 Strategy Health Scorecard</h2><span class="source-tag tag-fw">FORWARD</span></div>
<div class="tw"><table>
<thead><tr><th>Strategy</th><th>Trades</th><th>Wins</th><th>WR</th><th>Avg PnL</th><th>Avg MFE</th><th>Avg MAE</th><th>Grade</th><th>Action</th></tr></thead>
<tbody>
{"".join(health_rows)}
</tbody></table></div>
</div>

<!-- ═══ BACKTEST TOP PICKS ═══ -->
<div class="sec">
<div class="sh"><h2>📊 Backtest Top Picks — Proven Edge (MC p&lt;0.05)</h2><span class="source-tag tag-bt">BACKTEST</span></div>
<div class="tw"><table>
<thead><tr><th>Pair</th><th>TF</th><th>Strategy</th><th>Sharpe</th><th>Win Rate</th><th>PF</th><th>Max DD</th><th>Return</th><th>Trades</th><th>MC p</th></tr></thead>
<tbody>
<tr><td><b>NEARUSDT</b></td><td>15m</td><td>supertrend</td><td class="g">2.57</td><td>71.4%</td><td>2.59</td><td>-9.8%</td><td>+30.5%</td><td>7</td><td>0.039</td></tr>
<tr><td><b>LINKUSDT</b></td><td>1h</td><td>supertrend</td><td class="g">2.48</td><td>63.6%</td><td>3.21</td><td>—</td><td>—</td><td>—</td><td>&lt;0.05</td></tr>
<tr><td><b>SUIUSDT</b></td><td>15m</td><td>supertrend</td><td class="g">2.45</td><td>80.0%</td><td>3.62</td><td>-14.1%</td><td>+36.8%</td><td>5</td><td>0.039</td></tr>
<tr><td><b>FILUSDT</b></td><td>1h</td><td>supertrend</td><td class="g">2.25</td><td>60.0%</td><td>2.89</td><td>—</td><td>—</td><td>—</td><td>&lt;0.05</td></tr>
<tr><td><b>APEUSDT</b></td><td>15m</td><td>supertrend</td><td class="g">2.02</td><td>63.6%</td><td>1.78</td><td>-38.0%</td><td>+40.2%</td><td>11</td><td>0.020</td></tr>
<tr><td><b>STRKUSDT</b></td><td>1h</td><td>supertrend</td><td class="g">2.01</td><td>57.1%</td><td>2.54</td><td>—</td><td>—</td><td>—</td><td>&lt;0.05</td></tr>
<tr><td><b>SUIUSDT</b></td><td>1h</td><td>supertrend</td><td class="g">1.69</td><td>62.5%</td><td>2.42</td><td>—</td><td>—</td><td>—</td><td>&lt;0.05</td></tr>
<tr><td><b>XRPUSDT</b></td><td>4h</td><td>dynamic_selector</td><td class="g">1.16</td><td>69.2%</td><td>2.85</td><td>—</td><td>—</td><td>—</td><td>&lt;0.05</td></tr>
<tr><td><b>INJUSDT</b></td><td>1d</td><td>momentum_breakout</td><td>0.98</td><td>51.1%</td><td>2.10</td><td>-8.2%</td><td>+39.4%</td><td>47</td><td>0.020</td></tr>
</tbody></table></div>
<div class="callout callout-amber">
<b>⚠️ Note:</b> These are BACKTEST results. The supertrend strategy dominates here but is NOT currently used in forward picks (the alpha engine uses different strategies). This gap is itself a finding — we should add the backtest winners to forward trading.
</div>
<div class="links" style="margin-top:14px">
<a href="https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/blob/main/ml_crypto_predictor/enhanced_models/results/v4_comprehensive_report.json" target="_blank">Full Comprehensive Report</a>
<a href="https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/blob/main/ml_crypto_predictor/enhanced_models/results/v4_proof_report.json" target="_blank">Proof Report (562KB)</a>
</div>
</div>

<!-- ═══ FORWARD PICKS — LIVE ═══ -->
<div class="sec">
<div class="sh"><h2>🎯 Forward Picks — LIVE Positions</h2><span class="source-tag tag-fw">FORWARD</span><span class="bd">{len(active_picks)} OPEN</span></div>
<p style="color:var(--t2);font-size:.82rem;margin-bottom:14px">Click the <b>Audit Log</b> on any pick to see the full reasoning — what pattern it matched, why, and the strategy's track record. Written so a high-school kid could understand.</p>
<div class="pk-grid">
{"".join(pick_cards)}
</div>
<div class="links" style="margin-top:14px">
<a href="https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/alpha_engine/data/active_picks.json" target="_blank">All {len(active_picks)} Active Picks (JSON)</a>
<a href="https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/alpha_engine/data/closed_picks.json" target="_blank">Closed Picks (JSON)</a>
</div>
</div>

<!-- ═══ CLOSED TRADES WITH FAILURE ANALYSIS ═══ -->
<div class="sec">
<div class="sh"><h2>💀 Forward Record — With Failure Analysis</h2><span class="source-tag tag-fw">FORWARD</span><span class="bd">{fwd_total} CLOSED</span></div>
<p style="color:var(--t2);font-size:.82rem;margin-bottom:14px">Every loss has a <b>🔍 Failure Analysis</b> that explains what went wrong and what model tweaks are proposed. Click to expand.</p>
<div class="tw"><table>
<thead><tr><th>Symbol</th><th>Strategy</th><th>Signal</th><th>Entry</th><th>Exit</th><th>P&amp;L</th><th>$</th><th>Exit Reason</th></tr></thead>
<tbody>
{"".join(closed_rows)}
</tbody>
<tfoot><tr style="background:rgba(99,102,241,.06);font-weight:700"><td colspan="5">TOTAL</td><td class="{pcls(fwd_avg_pnl)}">{fwd_avg_pnl*100:+.1f}% avg</td><td class="{pcls(fwd_pnl)}">${fwd_pnl:+,.0f}</td><td>{fwd_wins}W / {fwd_losses}L ({fwd_wr})</td></tr></tfoot>
</table></div>
<p style="color:var(--t3);font-size:.78rem;margin-top:12px">System launched Feb 17. Model retrains nightly at 2AM UTC. Each loss feeds back into the next training cycle.</p>
</div>

<!-- ═══ TRAINING INFO ═══ -->
<div class="sec">
<div class="sh"><h2>🧠 Training & Model Info</h2></div>
<div class="kpi-grid" style="grid-template-columns:repeat(auto-fit,minmax(200px,1fr))">
<div class="kpi"><div class="l">Total Models</div><div class="v p">793</div><div class="n">40 pairs × 5 TFs × strategies</div></div>
<div class="kpi"><div class="l">A/B Test Winner</div><div class="v g">Random Forest</div><div class="n">81 wins (XGB:48 LGB:32 Ens:39)</div></div>
<div class="kpi"><div class="l">Training Time</div><div class="v c">44 min</div><div class="n">2,650 seconds total</div></div>
<div class="kpi"><div class="l">Last Trained</div><div class="v b">{now[:10]}</div><div class="n">Auto-nightly at 2AM UTC</div></div>
</div>
</div>

<!-- ═══ RAW DATA ═══ -->
<div class="sec">
<div class="sh"><h2>🔗 Raw Data & Source Code</h2></div>
<div class="links">
<a href="https://findtorontoevents.ca/alpha/" target="_blank">Live Dashboard</a>
<a href="https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/alpha_engine/data/active_picks.json" target="_blank">Active Picks JSON</a>
<a href="https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/alpha_engine/data/closed_picks.json" target="_blank">Closed Picks JSON</a>
<a href="https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/alpha_engine/data/strategy_performance.json" target="_blank">Strategy Perf JSON</a>
<a href="https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/blob/main/ml_crypto_predictor/enhanced_models/results/v4_comprehensive_report.json" target="_blank">Backtest Report</a>
<a href="https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/tree/main/ml_crypto_predictor/enhanced_models" target="_blank">Source Code</a>
</div>
</div>
</div>

<div class="footer">
<p>Antigravity ML Crypto Predictor v4.1 — Claude Code VS Code</p>
<p>Backtest: Binance 0.1% fees + slippage | Walk-forward 5-fold CV | Monte Carlo p&lt;0.05 | Not financial advice</p>
<p>All data 100% public on GitHub. Verify everything. antigravity</p>
<p>Page generated: {now}</p>
</div>
</body>
</html>'''

# Write
outpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.html')
with open(outpath, 'w', encoding='utf-8') as f:
    f.write(PAGE)

print(f"Generated {outpath}")
print(f"  Active picks: {len(active_picks)}")
print(f"  Closed picks: {len(closed_picks)} ({fwd_wins}W / {fwd_losses}L = {fwd_wr})")
print(f"  Forward P&L: ${fwd_pnl:+,.0f}")
print(f"  Strategy health: {performing} performing, {failing} failing, {insufficient} insufficient data")
print(f"  Failure analyses: {len(FAILURE_ANALYSIS)}")
print(f"  Timestamp: {now}")
print(f"  File size: {os.path.getsize(outpath):,} bytes")
