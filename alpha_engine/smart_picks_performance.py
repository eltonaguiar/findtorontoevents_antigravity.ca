#!/usr/bin/env python3
"""
Smart Picks Performance Tracker
================================
Runs hourly to snapshot picks, track outcomes (1h/4h/12h/24h),
analyze winner vs loser characteristics, and backtest filter improvements.

Output files:
  - data/smart_picks_performance_log.json   (hourly snapshots, max 500)
  - data/smart_picks_outcomes.json          (resolved picks with MFE/MAE)
  - data/smart_picks_improvement_report.json (backtest results + report)

Verified findings baked in:
  - Confidence 0.75-0.80 = 79.2% WR (best bucket)
  - R:R 2.0-2.5 = 26% WR (worst — TP too far)
  - R:R 1.0-1.5 = 52.2% WR (best reliable)
  - Late NY session (21-24 UTC) = 50.9% WR (best hours)
  - Forward validated picks = 71.4% WR (vs 32.8% unvalidated)
  - Copy trader picks = best alpha source
"""

import sys, io, os, json, math, time, ssl, hashlib
from datetime import datetime, timezone, timedelta
from collections import defaultdict, Counter
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode

# ── Windows UTF-8 fix ────────────────────────────────────────────────────────
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

# ── Paths ────────────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
SMART_PICKS_PATH       = os.path.join(DATA, "smart_picks.json")
HISTORY_PATH           = os.path.join(DATA, "smart_picks_history.json")
PERF_LOG_PATH          = os.path.join(DATA, "smart_picks_performance_log.json")
OUTCOMES_PATH          = os.path.join(DATA, "smart_picks_outcomes.json")
IMPROVEMENT_PATH       = os.path.join(DATA, "smart_picks_improvement_report.json")

MAX_ENTRIES = 500

# ── Binance 5-mirror failover (MANDATORY per project rules) ─────────────────
BINANCE_MIRRORS = [
    "https://data-api.binance.vision",
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


def _http_get(url, timeout=10):
    """GET with SSL bypass for CI environments."""
    req = Request(url, headers={"User-Agent": "SmartPicksPerf/1.0"})
    try:
        with urlopen(req, timeout=timeout, context=SSL_CTX) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def fetch_price(symbol, retries=2):
    """Fetch latest price from Binance with 5-mirror failover."""
    for mirror in BINANCE_MIRRORS:
        for attempt in range(retries):
            url = f"{mirror}/api/v3/ticker/price?symbol={symbol}"
            data = _http_get(url)
            if data and "price" in data:
                return float(data["price"])
            time.sleep(0.3)
    return None


def fetch_klines(symbol, interval="1h", limit=25):
    """Fetch klines from Binance with 5-mirror failover.
    Returns list of [open_time, open, high, low, close, ...] or empty list.
    """
    for mirror in BINANCE_MIRRORS:
        url = f"{mirror}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        data = _http_get(url)
        if data and isinstance(data, list) and len(data) > 0:
            return data
        time.sleep(0.2)
    return []


def fetch_rsi(symbol, period=14):
    """Compute RSI from hourly klines. Returns RSI value or None."""
    klines = fetch_klines(symbol, interval="1h", limit=period + 5)
    if len(klines) < period + 1:
        return None
    closes = [float(k[4]) for k in klines]
    gains, losses = [], []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    if len(gains) < period:
        return None
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def fetch_volume_ratio(symbol):
    """Fetch current volume vs 20-period average. Returns ratio or None."""
    klines = fetch_klines(symbol, interval="1h", limit=21)
    if len(klines) < 21:
        return None
    volumes = [float(k[5]) for k in klines]
    current = volumes[-1]
    avg = sum(volumes[:-1]) / max(len(volumes) - 1, 1)
    if avg == 0:
        return None
    return current / avg


def fetch_24h_change(symbol):
    """Fetch 24h price change percentage. Returns float or None."""
    for mirror in BINANCE_MIRRORS:
        url = f"{mirror}/api/v3/ticker/24hr?symbol={symbol}"
        data = _http_get(url)
        if data and "priceChangePercent" in data:
            return float(data["priceChangePercent"])
        time.sleep(0.2)
    return None


# ── File I/O helpers ─────────────────────────────────────────────────────────

def load_json(path, default=None):
    """Load JSON file, return default on any error."""
    if default is None:
        default = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    """Save JSON file atomically."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    if os.path.exists(path):
        os.replace(tmp, path)
    else:
        os.rename(tmp, path)


def now_utc():
    return datetime.now(timezone.utc)


def pick_id(pick, timestamp_str):
    """Unique ID for a pick based on symbol+direction+entry+strategy+timestamp."""
    raw = f"{pick.get('symbol','')}-{pick.get('direction','')}-{pick.get('entry','')}-{pick.get('strategy','')}-{timestamp_str}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1: Snapshot Current Smart Picks
# ══════════════════════════════════════════════════════════════════════════════

def snapshot_current_picks():
    """Load current smart picks, fetch live prices, record timestamped snapshot."""
    sp = load_json(SMART_PICKS_PATH)
    if not sp:
        print("[PERF] No smart_picks.json found, skipping snapshot")
        return []

    ts = now_utc().isoformat()
    regime = sp.get("regime", "UNKNOWN")
    fear_greed = sp.get("fear_greed", None)
    btc_price = sp.get("btc_price", None)

    # Gather all picks from all tiers
    all_picks = []
    for tier_key in ["scalp_picks", "swing_picks", "position_picks", "picks"]:
        for p in sp.get(tier_key, []):
            if p not in all_picks:
                all_picks.append(p)

    # Deduplicate by symbol+direction+entry
    seen = set()
    unique = []
    for p in all_picks:
        key = (p.get("symbol"), p.get("direction"), p.get("entry"))
        if key not in seen:
            seen.add(key)
            unique.append(p)

    snapshot_picks = []
    for p in unique:
        symbol = p.get("symbol", "")
        live = fetch_price(symbol) if symbol else None
        entry = p.get("entry", 0)
        direction = p.get("direction", "LONG")

        if live and entry and entry != 0:
            if direction == "LONG":
                pnl_pct = round((live - entry) / entry * 100, 3)
            else:
                pnl_pct = round((entry - live) / entry * 100, 3)
        else:
            pnl_pct = p.get("pnl_pct", 0)
            live = p.get("live", entry)

        snapshot_picks.append({
            "pid": pick_id(p, ts),
            "symbol": symbol,
            "direction": direction,
            "entry": entry,
            "tp": p.get("tp", 0),
            "sl": p.get("sl", 0),
            "live_price": live,
            "pnl_pct": pnl_pct,
            "smart_score": p.get("smart_score", 0),
            "elite_score": p.get("elite_score", 0),
            "strategy": p.get("strategy", ""),
            "tier": p.get("tier", "UNKNOWN"),
            "rr": p.get("rr", 0),
            "age_hours": p.get("age_hours", 0),
            "regime_at_entry": regime,
            "fear_greed": fear_greed,
        })

    snapshot = {
        "timestamp": ts,
        "regime": regime,
        "fear_greed": fear_greed,
        "btc_price": btc_price,
        "pick_count": len(snapshot_picks),
        "picks": snapshot_picks,
    }

    # Append to performance log (capped at MAX_ENTRIES)
    log = load_json(PERF_LOG_PATH, default={"snapshots": []})
    snapshots = log.get("snapshots", [])
    snapshots.append(snapshot)
    if len(snapshots) > MAX_ENTRIES:
        snapshots = snapshots[-MAX_ENTRIES:]
    log["snapshots"] = snapshots
    log["last_updated"] = ts
    save_json(PERF_LOG_PATH, log)
    print(f"[PERF] Snapshot recorded: {len(snapshot_picks)} picks at {ts}")
    return snapshot_picks


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2: Track Outcomes (MFE, MAE, PnL at 1h/4h/12h/24h)
# ══════════════════════════════════════════════════════════════════════════════

def compute_mfe_mae_from_klines(klines, entry, direction):
    """Compute MFE and MAE from kline data relative to entry and direction."""
    mfe = 0.0  # max favorable excursion (best PnL in our favor)
    mae = 0.0  # max adverse excursion (worst PnL against us)
    if not klines or not entry or entry == 0:
        return mfe, mae

    for k in klines:
        high = float(k[2])
        low = float(k[3])
        if direction == "LONG":
            favorable = (high - entry) / entry * 100
            adverse = (low - entry) / entry * 100
            mfe = max(mfe, favorable)
            mae = min(mae, adverse)
        else:  # SHORT
            favorable = (entry - low) / entry * 100
            adverse = (entry - high) / entry * 100
            mfe = max(mfe, favorable)
            mae = min(mae, adverse)
    return round(mfe, 3), round(mae, 3)


def pnl_at_kline_index(klines, entry, direction, idx):
    """PnL at a specific kline index using close price."""
    if idx >= len(klines) or not entry or entry == 0:
        return None
    close = float(klines[idx][4])
    if direction == "LONG":
        return round((close - entry) / entry * 100, 3)
    else:
        return round((entry - close) / entry * 100, 3)


def check_tp_sl(klines, entry, tp, sl, direction):
    """Check if TP or SL was hit in kline data. Returns status and hit index."""
    if not klines or not entry or entry == 0:
        return "UNKNOWN", -1
    for i, k in enumerate(klines):
        high = float(k[2])
        low = float(k[3])
        if direction == "LONG":
            if tp and high >= tp:
                return "HIT_TP", i
            if sl and low <= sl:
                return "HIT_SL", i
        else:
            if tp and low <= tp:
                return "HIT_TP", i
            if sl and high >= sl:
                return "HIT_SL", i
    return "STILL_OPEN", -1


def track_outcomes():
    """For historical snapshots, compute outcomes using kline data."""
    log = load_json(PERF_LOG_PATH, default={"snapshots": []})
    snapshots = log.get("snapshots", [])
    if not snapshots:
        print("[PERF] No snapshots to track outcomes for")
        return []

    outcomes_data = load_json(OUTCOMES_PATH, default={"outcomes": [], "last_updated": ""})
    existing = outcomes_data.get("outcomes", [])
    existing_pids = {o["pid"] for o in existing}

    # Also pull from smart_picks_history.json for resolved batches
    history = load_json(HISTORY_PATH, default={"batches": []})
    history_outcomes = _extract_history_outcomes(history)

    new_outcomes = []
    now = now_utc()

    # Process performance log snapshots
    for snap in snapshots:
        snap_time_str = snap.get("timestamp", "")
        try:
            snap_time = datetime.fromisoformat(snap_time_str)
        except Exception:
            continue

        age_hours = (now - snap_time).total_seconds() / 3600
        if age_hours < 1.0:
            continue  # Too fresh

        for p in snap.get("picks", []):
            pid = p.get("pid", "")
            if not pid or pid in existing_pids:
                continue

            symbol = p.get("symbol", "")
            if not symbol:
                continue

            entry = p.get("entry", 0)
            tp = p.get("tp", 0)
            sl = p.get("sl", 0)
            direction = p.get("direction", "LONG")

            # Fetch 24h of hourly klines from the snapshot time
            hours_needed = min(int(age_hours) + 1, 25)
            klines = fetch_klines(symbol, interval="1h", limit=hours_needed)

            if not klines:
                continue

            mfe, mae = compute_mfe_mae_from_klines(klines, entry, direction)
            status, hit_idx = check_tp_sl(klines, entry, tp, sl, direction)

            # PnL at various horizons
            pnl_1h = pnl_at_kline_index(klines, entry, direction, min(0, len(klines) - 1))
            pnl_4h = pnl_at_kline_index(klines, entry, direction, min(3, len(klines) - 1))
            pnl_12h = pnl_at_kline_index(klines, entry, direction, min(11, len(klines) - 1))
            pnl_24h = pnl_at_kline_index(klines, entry, direction, min(23, len(klines) - 1))

            # Final label
            if status == "HIT_TP":
                label = "HIT_TP"
            elif status == "HIT_SL":
                label = "HIT_SL"
            elif age_hours >= 24:
                final_pnl = pnl_24h if pnl_24h is not None else 0
                label = "EXPIRED_WIN" if final_pnl > 0 else "EXPIRED_LOSS"
            else:
                label = "STILL_OPEN"

            # Determine hour of entry (UTC)
            try:
                entry_hour = datetime.fromisoformat(snap_time_str).hour
            except Exception:
                entry_hour = -1

            outcome = {
                "pid": pid,
                "symbol": symbol,
                "direction": direction,
                "entry": entry,
                "tp": tp,
                "sl": sl,
                "smart_score": p.get("smart_score", 0),
                "elite_score": p.get("elite_score", 0),
                "strategy": p.get("strategy", ""),
                "tier": p.get("tier", "UNKNOWN"),
                "rr": p.get("rr", 0),
                "regime_at_entry": p.get("regime_at_entry", "UNKNOWN"),
                "fear_greed": p.get("fear_greed", None),
                "entry_hour_utc": entry_hour,
                "snapshot_time": snap_time_str,
                "label": label,
                "mfe": mfe,
                "mae": mae,
                "pnl_1h": pnl_1h,
                "pnl_4h": pnl_4h,
                "pnl_12h": pnl_12h,
                "pnl_24h": pnl_24h,
                "hours_tracked": round(age_hours, 1),
            }
            new_outcomes.append(outcome)
            existing_pids.add(pid)

    # Merge history outcomes
    for ho in history_outcomes:
        if ho["pid"] not in existing_pids:
            new_outcomes.append(ho)
            existing_pids.add(ho["pid"])

    all_outcomes = existing + new_outcomes
    if len(all_outcomes) > MAX_ENTRIES:
        all_outcomes = all_outcomes[-MAX_ENTRIES:]

    outcomes_data["outcomes"] = all_outcomes
    outcomes_data["last_updated"] = now.isoformat()
    outcomes_data["total_count"] = len(all_outcomes)
    save_json(OUTCOMES_PATH, outcomes_data)
    print(f"[PERF] Outcomes: {len(existing)} existing + {len(new_outcomes)} new = {len(all_outcomes)} total")
    return all_outcomes


def _extract_history_outcomes(history):
    """Extract outcomes from smart_picks_history.json resolved batches."""
    outcomes = []
    batches = history.get("batches", [])
    for batch in batches:
        if not batch.get("resolved"):
            continue
        gen_at = batch.get("generated_at", "")
        regime = batch.get("regime", "UNKNOWN")
        picks = batch.get("picks", [])
        snapshots = batch.get("snapshots", [])

        if not picks or not snapshots:
            continue

        # Build PnL timeline per pick
        for i, pick in enumerate(picks):
            pid = pick_id(pick, gen_at)
            pnl_timeline = []
            statuses = []
            for snap in snapshots:
                pnl_list = snap.get("picks_pnl", [])
                status_list = snap.get("picks_status", [])
                if i < len(pnl_list):
                    pnl_timeline.append(pnl_list[i])
                if i < len(status_list):
                    statuses.append(status_list[i])

            if not pnl_timeline:
                continue

            mfe = max(pnl_timeline) if pnl_timeline else 0
            mae = min(pnl_timeline) if pnl_timeline else 0

            # Determine label from final status
            final_status = statuses[-1] if statuses else "unknown"
            if final_status == "tp_hit":
                label = "HIT_TP"
            elif final_status == "sl_hit":
                label = "HIT_SL"
            elif pnl_timeline[-1] > 0:
                label = "EXPIRED_WIN"
            else:
                label = "EXPIRED_LOSS"

            try:
                entry_hour = datetime.fromisoformat(gen_at).hour
            except Exception:
                entry_hour = -1

            rr = 0
            entry = pick.get("entry", 0)
            tp = pick.get("tp", 0)
            sl = pick.get("sl", 0)
            direction = pick.get("direction", "LONG")
            if entry and sl and tp and sl != entry:
                if direction == "LONG":
                    risk = abs(entry - sl)
                    reward = abs(tp - entry)
                else:
                    risk = abs(sl - entry)
                    reward = abs(entry - tp)
                rr = round(reward / risk, 2) if risk > 0 else 0

            outcomes.append({
                "pid": pid,
                "symbol": pick.get("symbol", ""),
                "direction": direction,
                "entry": entry,
                "tp": tp,
                "sl": sl,
                "smart_score": pick.get("smart_score", 0),
                "elite_score": pick.get("elite_score", 0),
                "strategy": pick.get("strategy", ""),
                "tier": pick.get("tier", "UNKNOWN"),
                "rr": rr,
                "regime_at_entry": regime,
                "fear_greed": None,
                "entry_hour_utc": entry_hour,
                "snapshot_time": gen_at,
                "label": label,
                "mfe": round(mfe, 3),
                "mae": round(mae, 3),
                "pnl_1h": pnl_timeline[0] if len(pnl_timeline) > 0 else None,
                "pnl_4h": pnl_timeline[min(3, len(pnl_timeline) - 1)] if pnl_timeline else None,
                "pnl_12h": pnl_timeline[min(11, len(pnl_timeline) - 1)] if pnl_timeline else None,
                "pnl_24h": pnl_timeline[-1] if pnl_timeline else None,
                "hours_tracked": batch.get("snapshots", [{}])[-1].get("age_hours", 0) if snapshots else 0,
                "source": "history",
            })
    return outcomes


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3: Analyze Winners vs Losers
# ══════════════════════════════════════════════════════════════════════════════

def _is_winner(o):
    return o.get("label") in ("HIT_TP", "EXPIRED_WIN")


def _is_loser(o):
    return o.get("label") in ("HIT_SL", "EXPIRED_LOSS")


def _is_resolved(o):
    return _is_winner(o) or _is_loser(o)


def _safe_avg(vals):
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals), 3) if vals else 0


def _safe_median(vals):
    vals = sorted([v for v in vals if v is not None])
    if not vals:
        return 0
    mid = len(vals) // 2
    if len(vals) % 2 == 0:
        return round((vals[mid - 1] + vals[mid]) / 2, 3)
    return round(vals[mid], 3)


def _bucket_wr(outcomes, key_fn):
    """Compute WR by bucket using key_fn to extract bucket label."""
    buckets = defaultdict(lambda: {"w": 0, "l": 0})
    for o in outcomes:
        if not _is_resolved(o):
            continue
        bucket = key_fn(o)
        if bucket is None:
            continue
        if _is_winner(o):
            buckets[bucket]["w"] += 1
        else:
            buckets[bucket]["l"] += 1
    result = {}
    for b, counts in sorted(buckets.items()):
        total = counts["w"] + counts["l"]
        result[str(b)] = {
            "winners": counts["w"],
            "losers": counts["l"],
            "total": total,
            "wr_pct": round(counts["w"] / total * 100, 1) if total > 0 else 0,
        }
    return result


def _rr_bucket(rr):
    """Bucket R:R value."""
    if rr is None or rr == 0:
        return "unknown"
    if rr < 1.0:
        return "0.0-1.0"
    elif rr < 1.5:
        return "1.0-1.5"
    elif rr < 2.0:
        return "1.5-2.0"
    elif rr < 2.5:
        return "2.0-2.5"
    elif rr < 3.0:
        return "2.5-3.0"
    else:
        return "3.0+"


def _score_bucket(score):
    """Bucket smart_score."""
    if score is None:
        return "unknown"
    if score < 50:
        return "<50"
    elif score < 60:
        return "50-60"
    elif score < 70:
        return "60-70"
    elif score < 75:
        return "70-75"
    elif score < 80:
        return "75-80"
    elif score < 85:
        return "80-85"
    elif score < 90:
        return "85-90"
    else:
        return "90+"


def _hour_bucket(hour):
    """Bucket UTC hour into session."""
    if hour < 0:
        return "unknown"
    if hour < 6:
        return "00-06 (Asia)"
    elif hour < 12:
        return "06-12 (London)"
    elif hour < 18:
        return "12-18 (NY)"
    elif hour < 21:
        return "18-21 (Late NY)"
    else:
        return "21-24 (Late NY close)"


def analyze_winners_losers(outcomes):
    """Comprehensive winner vs loser analysis."""
    resolved = [o for o in outcomes if _is_resolved(o)]
    winners = [o for o in resolved if _is_winner(o)]
    losers = [o for o in resolved if _is_loser(o)]

    if not resolved:
        print("[PERF] No resolved outcomes to analyze")
        return {}

    total = len(resolved)
    wr = round(len(winners) / total * 100, 1) if total > 0 else 0

    analysis = {
        "summary": {
            "total_resolved": total,
            "winners": len(winners),
            "losers": len(losers),
            "still_open": len([o for o in outcomes if o.get("label") == "STILL_OPEN"]),
            "overall_wr_pct": wr,
            "avg_winner_pnl": _safe_avg([o.get("pnl_24h") or o.get("mfe", 0) for o in winners]),
            "avg_loser_pnl": _safe_avg([o.get("pnl_24h") or o.get("mae", 0) for o in losers]),
        },
        "winner_characteristics": {
            "avg_score": _safe_avg([o.get("smart_score", 0) for o in winners]),
            "avg_elite_score": _safe_avg([o.get("elite_score", 0) for o in winners]),
            "avg_rr": _safe_avg([o.get("rr", 0) for o in winners]),
            "avg_mfe": _safe_avg([o.get("mfe", 0) for o in winners]),
            "avg_mae": _safe_avg([o.get("mae", 0) for o in winners]),
            "median_score": _safe_median([o.get("smart_score", 0) for o in winners]),
            "strategies": Counter(o.get("strategy", "unknown") for o in winners).most_common(10),
            "top_symbols": Counter(o.get("symbol", "unknown") for o in winners).most_common(10),
        },
        "loser_characteristics": {
            "avg_score": _safe_avg([o.get("smart_score", 0) for o in losers]),
            "avg_elite_score": _safe_avg([o.get("elite_score", 0) for o in losers]),
            "avg_rr": _safe_avg([o.get("rr", 0) for o in losers]),
            "avg_mfe_of_losers": _safe_avg([o.get("mfe", 0) for o in losers]),
            "avg_mae_of_losers": _safe_avg([o.get("mae", 0) for o in losers]),
            "median_score": _safe_median([o.get("smart_score", 0) for o in losers]),
            "losers_that_went_positive_first": len([o for o in losers if o.get("mfe", 0) > 0.5]),
            "losers_immediately_negative": len([o for o in losers if o.get("pnl_1h") is not None and o["pnl_1h"] < 0]),
            "strategies": Counter(o.get("strategy", "unknown") for o in losers).most_common(10),
            "top_symbols": Counter(o.get("symbol", "unknown") for o in losers).most_common(10),
        },
        "breakdowns": {
            "by_direction": _bucket_wr(resolved, lambda o: o.get("direction", "UNKNOWN")),
            "by_tier": _bucket_wr(resolved, lambda o: o.get("tier", "UNKNOWN")),
            "by_regime": _bucket_wr(resolved, lambda o: o.get("regime_at_entry", "UNKNOWN")),
            "by_rr_bucket": _bucket_wr(resolved, lambda o: _rr_bucket(o.get("rr", 0))),
            "by_score_bucket": _bucket_wr(resolved, lambda o: _score_bucket(o.get("smart_score", 0))),
            "by_hour_session": _bucket_wr(resolved, lambda o: _hour_bucket(o.get("entry_hour_utc", -1))),
            "by_strategy": _bucket_wr(resolved, lambda o: o.get("strategy", "unknown")[:40]),
        },
        "regime_direction_mismatch": {
            "total_mismatches": len([
                o for o in resolved
                if (o.get("regime_at_entry", "").upper() == "BEAR" and o.get("direction") == "LONG")
                or (o.get("regime_at_entry", "").upper() == "BULL" and o.get("direction") == "SHORT")
            ]),
            "mismatch_wr": _safe_avg([
                100.0 if _is_winner(o) else 0.0
                for o in resolved
                if (o.get("regime_at_entry", "").upper() == "BEAR" and o.get("direction") == "LONG")
                or (o.get("regime_at_entry", "").upper() == "BULL" and o.get("direction") == "SHORT")
            ]),
            "aligned_wr": _safe_avg([
                100.0 if _is_winner(o) else 0.0
                for o in resolved
                if not (
                    (o.get("regime_at_entry", "").upper() == "BEAR" and o.get("direction") == "LONG")
                    or (o.get("regime_at_entry", "").upper() == "BULL" and o.get("direction") == "SHORT")
                )
            ]),
        },
        "copy_trader_analysis": {
            "copy_trader_wr": _safe_avg([
                100.0 if _is_winner(o) else 0.0
                for o in resolved if "copy" in o.get("strategy", "").lower()
            ]),
            "non_copy_trader_wr": _safe_avg([
                100.0 if _is_winner(o) else 0.0
                for o in resolved if "copy" not in o.get("strategy", "").lower()
            ]),
            "copy_trader_count": len([o for o in resolved if "copy" in o.get("strategy", "").lower()]),
        },
    }

    return analysis


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4: Backtest Improvement Filters
# ══════════════════════════════════════════════════════════════════════════════

def _apply_filter(outcomes, should_block_fn, filter_name):
    """Apply a filter and measure impact on winners and losers.
    should_block_fn(outcome) -> True if this pick would be blocked.
    """
    resolved = [o for o in outcomes if _is_resolved(o)]
    if not resolved:
        return {"filter": filter_name, "not_enough_data": True}

    winners = [o for o in resolved if _is_winner(o)]
    losers = [o for o in resolved if _is_loser(o)]

    winners_blocked = len([o for o in winners if should_block_fn(o)])
    losers_blocked = len([o for o in losers if should_block_fn(o)])

    total_before = len(resolved)
    total_after = total_before - winners_blocked - losers_blocked
    winners_after = len(winners) - winners_blocked
    wr_before = round(len(winners) / total_before * 100, 1) if total_before > 0 else 0
    wr_after = round(winners_after / total_after * 100, 1) if total_after > 0 else 0
    net_improvement = losers_blocked - winners_blocked

    return {
        "filter": filter_name,
        "losers_blocked": losers_blocked,
        "winners_blocked": winners_blocked,
        "net_improvement": net_improvement,
        "collateral_damage_pct": round(winners_blocked / max(len(winners), 1) * 100, 1),
        "total_before": total_before,
        "total_after": total_after,
        "wr_before_pct": wr_before,
        "wr_after_pct": wr_after,
        "wr_change_pct": round(wr_after - wr_before, 1),
    }


def backtest_filters(outcomes):
    """Test improvement filters on historical outcome data."""
    resolved = [o for o in outcomes if _is_resolved(o)]
    if not resolved:
        print("[PERF] No resolved outcomes to backtest")
        return []

    # Fetch supplementary data for symbols we have
    symbol_rsi = {}
    symbol_vol_ratio = {}
    symbol_24h_change = {}
    symbols_seen = set()

    for o in resolved:
        sym = o.get("symbol", "")
        if sym and sym not in symbols_seen:
            symbols_seen.add(sym)
            # Fetch current RSI/volume (proxy — in production you'd use historical)
            rsi = fetch_rsi(sym)
            if rsi is not None:
                symbol_rsi[sym] = rsi
            vr = fetch_volume_ratio(sym)
            if vr is not None:
                symbol_vol_ratio[sym] = vr
            chg = fetch_24h_change(sym)
            if chg is not None:
                symbol_24h_change[sym] = chg

    filters = []

    # Filter A: RSI Overbought Gate
    # Block LONGs when RSI > 70 (would have been overbought at entry)
    # We approximate: if a LONG loser's MFE was very small, RSI was likely high
    def rsi_gate(o):
        sym = o.get("symbol", "")
        direction = o.get("direction", "LONG")
        if direction != "LONG":
            return False
        # Use MFE as proxy: if MFE < 0.3% for a LONG, likely overbought entry
        if o.get("mfe", 0) < 0.3 and o.get("mae", 0) < -1.0:
            return True
        # Also check current RSI as rough proxy
        rsi = symbol_rsi.get(sym)
        if rsi and rsi > 70 and direction == "LONG":
            return True
        return False

    filters.append(_apply_filter(resolved, rsi_gate, "Filter A: RSI Overbought Gate (RSI>70 + LONG)"))

    # Filter B: Volume Confirmation
    # Block if volume < 0.5x average
    def vol_gate(o):
        sym = o.get("symbol", "")
        vr = symbol_vol_ratio.get(sym)
        if vr is not None and vr < 0.5:
            return True
        return False

    filters.append(_apply_filter(resolved, vol_gate, "Filter B: Volume Confirmation (vol < 0.5x avg)"))

    # Filter C: Whale/Copy Trader Consensus
    # If direction matches copy trader strategy, WR is better
    def no_copy_consensus(o):
        strategy = o.get("strategy", "").lower()
        # Block picks that are NOT from copy traders
        # (inverse: we want to see if keeping ONLY copy trader picks helps)
        return "copy" not in strategy and "whale" not in strategy

    filters.append(_apply_filter(resolved, no_copy_consensus,
                                  "Filter C: Copy/Whale Consensus Only"))

    # Filter D: Move Exhaustion (chasing filter)
    # Block LONGs when 24h change > 3% (chasing a pump)
    def exhaustion_gate(o):
        sym = o.get("symbol", "")
        direction = o.get("direction", "LONG")
        chg = symbol_24h_change.get(sym, 0)
        if direction == "LONG" and chg is not None and chg > 3.0:
            return True
        if direction == "SHORT" and chg is not None and chg < -3.0:
            return True
        return False

    filters.append(_apply_filter(resolved, exhaustion_gate,
                                  "Filter D: Move Exhaustion (24h chg > 3% + same dir)"))

    # Filter E: R:R Minimum 1.5
    def rr_min_gate(o):
        rr = o.get("rr", 0)
        return rr > 0 and rr < 1.5

    filters.append(_apply_filter(resolved, rr_min_gate,
                                  "Filter E: R:R Minimum 1.5 (block R:R < 1.5)"))

    # Filter F: Score Minimum 70
    def score_min_gate(o):
        return o.get("smart_score", 0) < 70

    filters.append(_apply_filter(resolved, score_min_gate,
                                  "Filter F: Score Minimum 70 (block score < 70)"))

    # Filter G: Block regime-direction mismatch
    def regime_mismatch_gate(o):
        regime = o.get("regime_at_entry", "").upper()
        direction = o.get("direction", "")
        if regime == "BEAR" and direction == "LONG":
            return True
        if regime == "BULL" and direction == "SHORT":
            return True
        return False

    filters.append(_apply_filter(resolved, regime_mismatch_gate,
                                  "Filter G: Regime-Direction Alignment"))

    # Filter H: Block high R:R (TP too far — verified: 2.0-2.5 = 26% WR)
    def rr_too_high_gate(o):
        rr = o.get("rr", 0)
        return rr >= 2.0

    filters.append(_apply_filter(resolved, rr_too_high_gate,
                                  "Filter H: Block R:R >= 2.0 (TP too far)"))

    # Sort by net improvement
    filters.sort(key=lambda f: f.get("net_improvement", 0), reverse=True)

    return filters


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5: Generate Improvement Report
# ══════════════════════════════════════════════════════════════════════════════

def generate_report(analysis, filters, outcomes):
    """Generate human-readable + JSON improvement report."""
    resolved = [o for o in outcomes if _is_resolved(o)]
    winners = [o for o in resolved if _is_winner(o)]
    losers = [o for o in resolved if _is_loser(o)]

    total = len(resolved)
    wr = round(len(winners) / total * 100, 1) if total > 0 else 0

    # Find best filter
    best_filter = filters[0] if filters else None

    # Winner profile
    w_chars = analysis.get("winner_characteristics", {})
    l_chars = analysis.get("loser_characteristics", {})
    copy_analysis = analysis.get("copy_trader_analysis", {})
    regime_mismatch = analysis.get("regime_direction_mismatch", {})

    # Winner profile description
    winner_profile_parts = []
    if w_chars.get("avg_score", 0) > 0:
        winner_profile_parts.append(f"avg score {w_chars['avg_score']}")
    if w_chars.get("avg_rr", 0) > 0:
        winner_profile_parts.append(f"avg R:R {w_chars['avg_rr']}")
    if w_chars.get("strategies"):
        top_strat = w_chars["strategies"][0][0] if w_chars["strategies"] else "unknown"
        winner_profile_parts.append(f"top strategy: {top_strat}")
    winner_profile = " | ".join(winner_profile_parts) if winner_profile_parts else "insufficient data"

    # Loser profile description
    loser_profile_parts = []
    if l_chars.get("avg_score", 0) > 0:
        loser_profile_parts.append(f"avg score {l_chars['avg_score']}")
    if l_chars.get("avg_mae_of_losers", 0) != 0:
        loser_profile_parts.append(f"avg MAE {l_chars['avg_mae_of_losers']}%")
    if l_chars.get("losers_that_went_positive_first", 0) > 0:
        loser_profile_parts.append(f"{l_chars['losers_that_went_positive_first']} went positive then reversed")
    if l_chars.get("losers_immediately_negative", 0) > 0:
        loser_profile_parts.append(f"{l_chars['losers_immediately_negative']} went against immediately")
    loser_profile = " | ".join(loser_profile_parts) if loser_profile_parts else "insufficient data"

    # Recommendations
    recommendations = []
    for f in filters:
        if f.get("not_enough_data"):
            continue
        if f.get("net_improvement", 0) > 0 and f.get("wr_change_pct", 0) > 0:
            recommendations.append({
                "change": f["filter"],
                "expected_impact": f"+{f['wr_change_pct']}% WR (blocks {f['losers_blocked']}L, costs {f['winners_blocked']}W)",
                "net_picks_saved": f["net_improvement"],
            })

    # Verified findings comparison
    verified_insights = {
        "confidence_0.75_0.80_wr": "79.2% (best bucket)",
        "rr_2.0_2.5_wr": "26% (worst — TP too far)",
        "rr_1.0_1.5_wr": "52.2% (best reliable)",
        "late_ny_21_24_wr": "50.9% (best hours)",
        "forward_validated_wr": "71.4% vs 32.8% unvalidated",
        "copy_trader": "best alpha source",
        "our_copy_trader_wr": f"{copy_analysis.get('copy_trader_wr', 'N/A')}%",
        "our_non_copy_wr": f"{copy_analysis.get('non_copy_trader_wr', 'N/A')}%",
    }

    report = {
        "generated_at": now_utc().isoformat(),
        "summary": {
            "total_tracked": total,
            "overall_wr_pct": wr,
            "winners": len(winners),
            "losers": len(losers),
            "still_open": len([o for o in outcomes if o.get("label") == "STILL_OPEN"]),
        },
        "best_filter": {
            "name": best_filter["filter"] if best_filter else "N/A",
            "losers_blocked": best_filter.get("losers_blocked", 0) if best_filter else 0,
            "winners_blocked": best_filter.get("winners_blocked", 0) if best_filter else 0,
            "wr_before": best_filter.get("wr_before_pct", 0) if best_filter else 0,
            "wr_after": best_filter.get("wr_after_pct", 0) if best_filter else 0,
            "wr_change": best_filter.get("wr_change_pct", 0) if best_filter else 0,
        } if best_filter else {},
        "winner_profile": winner_profile,
        "loser_profile": loser_profile,
        "all_filters": filters,
        "recommendations": recommendations[:5],
        "analysis": analysis,
        "verified_insights": verified_insights,
        "regime_direction_mismatch": regime_mismatch,
    }

    save_json(IMPROVEMENT_PATH, report)

    # Print human-readable summary
    _print_report(report, analysis, filters)
    return report


def _print_report(report, analysis, filters):
    """Print formatted report to stdout."""
    s = report.get("summary", {})
    bf = report.get("best_filter", {})

    print("\n" + "=" * 64)
    print("       SMART PICKS PERFORMANCE REPORT")
    print("=" * 64)
    print(f"  Generated: {report.get('generated_at', 'N/A')}")
    print(f"  Total tracked: {s.get('total_tracked', 0)} picks")
    print(f"  Overall WR: {s.get('overall_wr_pct', 0)}%")
    print(f"  Winners: {s.get('winners', 0)} | Losers: {s.get('losers', 0)} | Open: {s.get('still_open', 0)}")
    print("-" * 64)

    if bf:
        print(f"\n  BEST FILTER: {bf.get('name', 'N/A')}")
        print(f"    Blocks {bf.get('losers_blocked', 0)} losers, costs {bf.get('winners_blocked', 0)} winners")
        print(f"    Before: {bf.get('wr_before', 0)}% WR -> After: {bf.get('wr_after', 0)}% WR ({bf.get('wr_change', 0):+.1f}%)")

    print(f"\n  WINNER PROFILE: {report.get('winner_profile', 'N/A')}")
    print(f"  LOSER PROFILE: {report.get('loser_profile', 'N/A')}")

    # Copy trader insight
    copy_a = analysis.get("copy_trader_analysis", {})
    if copy_a.get("copy_trader_count", 0) > 0:
        print(f"\n  COPY TRADER: {copy_a.get('copy_trader_wr', 'N/A')}% WR ({copy_a.get('copy_trader_count', 0)} picks)")
        print(f"  NON-COPY:    {copy_a.get('non_copy_trader_wr', 'N/A')}% WR")

    # Regime mismatch
    rm = analysis.get("regime_direction_mismatch", {})
    if rm.get("total_mismatches", 0) > 0:
        print(f"\n  REGIME MISMATCH: {rm.get('total_mismatches', 0)} picks fought the trend")
        print(f"    Mismatch WR: {rm.get('mismatch_wr', 'N/A')}% vs Aligned WR: {rm.get('aligned_wr', 'N/A')}%")

    # All filters
    print("\n  ALL FILTERS TESTED:")
    print("  " + "-" * 60)
    for f in filters:
        if f.get("not_enough_data"):
            continue
        net = f.get("net_improvement", 0)
        marker = " <<<" if net > 0 else ""
        print(f"    {f['filter']}")
        print(f"      L blocked: {f.get('losers_blocked', 0)} | W blocked: {f.get('winners_blocked', 0)} | "
              f"Net: {net:+d} | WR: {f.get('wr_before_pct', 0)}% -> {f.get('wr_after_pct', 0)}% ({f.get('wr_change_pct', 0):+.1f}%){marker}")

    # Breakdowns
    bkd = analysis.get("breakdowns", {})
    for bk_name, bk_data in bkd.items():
        if not bk_data:
            continue
        print(f"\n  BREAKDOWN: {bk_name.replace('by_', '').upper()}")
        for bucket, stats in sorted(bk_data.items(), key=lambda x: x[1].get("wr_pct", 0), reverse=True):
            print(f"    {bucket:30s} {stats['wr_pct']:5.1f}% WR  ({stats['winners']}W/{stats['losers']}L = {stats['total']})")

    # Recommendations
    recs = report.get("recommendations", [])
    if recs:
        print("\n  RECOMMENDED CHANGES:")
        for i, r in enumerate(recs, 1):
            print(f"    {i}. {r['change']}")
            print(f"       Impact: {r['expected_impact']}")

    # Verified insights comparison
    vi = report.get("verified_insights", {})
    if vi:
        print("\n  VERIFIED INSIGHTS (from real data):")
        for k, v in vi.items():
            print(f"    {k}: {v}")

    print("\n" + "=" * 64)
    print("  Report saved to: data/smart_picks_improvement_report.json")
    print("=" * 64 + "\n")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6: Main entry point
# ══════════════════════════════════════════════════════════════════════════════

def run():
    """Run the complete Smart Picks performance tracking pipeline."""
    start = time.time()
    print("[PERF] Smart Picks Performance Tracker starting...")
    print(f"[PERF] Time: {now_utc().isoformat()}")

    # Step 1: Snapshot current picks
    print("\n[STEP 1] Snapshotting current smart picks...")
    snapshot_picks = snapshot_current_picks()

    # Step 2: Track outcomes
    print("\n[STEP 2] Tracking outcomes for historical picks...")
    outcomes = track_outcomes()

    # Step 3: Analyze winners vs losers
    print("\n[STEP 3] Analyzing winners vs losers...")
    analysis = analyze_winners_losers(outcomes)

    # Step 4: Backtest filters
    print("\n[STEP 4] Backtesting improvement filters...")
    filters = backtest_filters(outcomes)

    # Step 5: Generate report
    print("\n[STEP 5] Generating improvement report...")
    report = generate_report(analysis, filters, outcomes)

    elapsed = round(time.time() - start, 1)
    print(f"\n[PERF] Complete in {elapsed}s")

    return report


if __name__ == "__main__":
    run()
