"""
COT (Commitment of Traders) Positioning Strategy for Forex

Uses free CFTC data to detect extreme institutional positioning.
When commercials are extremely long/short, it signals a reversal.

Evidence: 55-62% WR, free data, completely uncorrelated with technical signals.
Source: CFTC weekly reports via Quandl/FRED proxy.

This is the #1 gap identified in our forex strategy audit (0/8 wins).
"""

import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Optional


# CFTC COT contract codes for major forex pairs
COT_CONTRACTS = {
    "EURUSD": {"code": "099741", "name": "EURO FX", "cme_id": "EUR"},
    "GBPUSD": {"code": "096742", "name": "BRITISH POUND", "cme_id": "GBP"},
    "USDJPY": {"code": "097741", "name": "JAPANESE YEN", "cme_id": "JPY"},
    "AUDUSD": {"code": "232741", "name": "AUSTRALIAN DOLLAR", "cme_id": "AUD"},
    "USDCAD": {"code": "090741", "name": "CANADIAN DOLLAR", "cme_id": "CAD"},
    "NZDUSD": {"code": "112741", "name": "NEW ZEALAND DOLLAR", "cme_id": "NZD"},
    "USDCHF": {"code": "092741", "name": "SWISS FRANC", "cme_id": "CHF"},
}

# Extreme percentile thresholds for signal generation
EXTREME_LONG_PERCENTILE = 90   # Commercials extremely long → price likely to fall
EXTREME_SHORT_PERCENTILE = 10  # Commercials extremely short → price likely to rise
LOOKBACK_WEEKS = 52  # 1 year for percentile calculation

# CFTC publishes the COT report Friday ~3:30pm ET covering the prior Tuesday's
# settlement. Emitting a pick on the same day the report's `report_date` was
# settled (or the 2 calendar days after) uses information that wasn't public
# until Friday — a textbook look-ahead bias. Reviewed external models (DeepSeek
# V4-Pro / Loker-480B / GPT-OSS) + internal code audit converged 2026-05-13:
# the CT=F paper-pilot's DSR=1.0 / WR 90% / n=100 is most likely produced by
# this leakage. Lag-corrected backtests typically halve the WR. Required by
# docs/STRATEGY_PROPOSALS_V1_2026_04_19.md:205 ("Friday close at earliest").
# See reports/cot_timing_leakage_audit_2026-05-13.md.
COT_PUBLICATION_LAG_DAYS = 3

# Per-release emit ledger. Each CFTC weekly release should emit at most ONE pick
# per (symbol). Without this guard, every scanner cycle that runs between
# release-N (Friday) and release-N+1 (next Friday) re-emits the same pick from
# release-N — the over-emission bug audited 2026-05-13. Falsified the COT
# paper-pilot's TIER-1 status (WR 90.1% → 40%, PF 2.73 → 0.17, n=101 → 5 real
# releases). Refs: cot_paper_pilot_overemission_falsified_20260513.md,
# tools/verify_cot_post_patch.py.
EMITTED_RELEASES_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data", "cot_emitted_releases.json"
)


def _normalize_direction(direction: str) -> str:
    """Map BUY/SELL (scanner vocab) to LONG/SHORT (audit vocab) so the
    ledger has a single direction vocabulary regardless of caller."""
    d = (direction or "").upper().strip()
    if d == "BUY":
        return "LONG"
    if d == "SELL":
        return "SHORT"
    return d


def _load_emitted_releases() -> set:
    """Return set of (symbol, direction, latest_cot_date) 3-tuples
    already emitted.

    Direction is included so within-week SHORT->LONG flips on the same
    symbol pass the dedup gate (otherwise a genuine signal reversal
    gets silently suppressed). Reviewer concern on PR #994 2026-05-14.
    """
    if not os.path.exists(EMITTED_RELEASES_PATH):
        return set()
    try:
        with open(EMITTED_RELEASES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return set()
    return {
        (
            e.get("symbol", ""),
            _normalize_direction(e.get("direction", "")),
            e.get("latest_cot_date", ""),
        )
        for e in data.get("emitted", [])
        if e.get("symbol") and e.get("latest_cot_date")
    }


def _acquire_ledger_lock(timeout: float = 5.0, retry: float = 0.05) -> "Optional[str]":
    """Best-effort O_EXCL sidecar lock for cross-process serialization
    of read-modify-write on EMITTED_RELEASES_PATH.

    PR #994 review (2026-05-14) flagged the race: multi-asset-scanner
    (every 30 min) + audit-dashboard (every hour at :10) both call into
    `_record_emitted_release`. The bare read+json.load+open(w)+json.dump
    sequence is NOT atomic at the application level (last writer wins).
    O_EXCL on a sidecar `.lock` file is stdlib-only and cross-platform.

    Returns the lock-path on success, None on timeout (caller proceeds
    best-effort — single-process-wide loss of a dedup entry is far less
    harmful than crashing the scanner).
    """
    import errno
    import time as _time
    lock_path = EMITTED_RELEASES_PATH + ".lock"
    deadline = _time.time() + timeout
    while _time.time() < deadline:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            return lock_path
        except OSError as e:
            if e.errno != errno.EEXIST:
                return None
            _time.sleep(retry)
    # Timeout: best-effort nuke stale lock and proceed unsynchronized
    try:
        os.unlink(lock_path)
    except OSError:
        pass
    return None


def _release_ledger_lock(lock_path: "Optional[str]") -> None:
    if not lock_path:
        return
    try:
        os.unlink(lock_path)
    except OSError:
        pass


def _record_emitted_release(symbol: str, direction: str,
                            latest_cot_date: str, emitted_at: str) -> None:
    """Append one (symbol, direction, latest_cot_date) row to the ledger.

    Concurrency: serializes on a sidecar O_EXCL `.lock` file; commits
    via tmp+os.replace() atomic-rename so a partial write never lands
    on disk. Both protections added per PR #994 review 2026-05-14.

    Prunes rows older than LOOKBACK_WEEKS so the file stays bounded
    (~7 pairs * 52 weeks = ~365 rows steady state).
    """
    os.makedirs(os.path.dirname(EMITTED_RELEASES_PATH), exist_ok=True)
    lock_path = _acquire_ledger_lock()
    try:
        try:
            with open(EMITTED_RELEASES_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            data = {"emitted": []}
        cutoff_dt = datetime.now(timezone.utc).date() - timedelta(weeks=LOOKBACK_WEEKS)
        cutoff_iso = cutoff_dt.isoformat()
        kept = []
        for e in data.get("emitted", []):
            rd = e.get("latest_cot_date", "")
            if not rd or rd >= cutoff_iso:
                kept.append(e)
        kept.append({
            "symbol": symbol,
            "direction": _normalize_direction(direction),
            "latest_cot_date": latest_cot_date,
            "emitted_at": emitted_at,
        })
        data["emitted"] = kept
        tmp_path = EMITTED_RELEASES_PATH + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, EMITTED_RELEASES_PATH)
    finally:
        _release_ledger_lock(lock_path)


def fetch_cot_data_cftc(contract_code: str) -> Optional[list]:
    """
    Fetch COT data from CFTC public API.
    Returns list of weekly reports with commercial/non-commercial positions.
    """
    try:
        # CFTC SOCRATA API (free, no key needed)
        import urllib.parse
        params = urllib.parse.urlencode({
            "$where": f"cftc_contract_market_code='{contract_code}'",
            "$order": "report_date_as_yyyy_mm_dd DESC",
            "$limit": str(LOOKBACK_WEEKS),
        })
        url = f"https://publicreporting.cftc.gov/resource/6dca-aqww.json?{params}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        return data
    except Exception as e:
        print(f"  [COT] CFTC API failed for {contract_code}: {e}")
        return None


def fetch_cot_data_proxy() -> Optional[dict]:
    """
    Fallback: Fetch pre-aggregated COT data from a known proxy.
    Returns dict keyed by currency code.
    """
    try:
        # Alternative: use tradingster.com COT data (public)
        url = "https://www.tradingster.com/cot/legacy-futures/099741"
        # This is a web page, not API -- skip for now
        return None
    except Exception:
        return None


def compute_net_positioning(reports: list) -> dict:
    """
    Compute net commercial positioning and percentile rank.

    Commercial hedgers are the "smart money" in forex COT.
    When they're extremely positioned, price tends to revert.
    """
    if not reports or len(reports) < 10:
        return {"signal": "NEUTRAL", "confidence": 0, "reason": "Insufficient data"}

    # Extract net commercial positions
    net_positions = []
    for r in reports:
        try:
            comm_long = int(r.get("comm_positions_long_all", 0) or 0)
            comm_short = int(r.get("comm_positions_short_all", 0) or 0)
            net = comm_long - comm_short
            net_positions.append({
                "date": r.get("report_date_as_yyyy_mm_dd", ""),
                "net": net,
                "comm_long": comm_long,
                "comm_short": comm_short,
            })
        except (ValueError, TypeError):
            continue

    if len(net_positions) < 10:
        return {"signal": "NEUTRAL", "confidence": 0, "reason": "Insufficient valid data"}

    # Current net position
    current_net = net_positions[0]["net"]

    # Calculate percentile rank over lookback
    all_nets = sorted([p["net"] for p in net_positions])
    rank = sum(1 for n in all_nets if n <= current_net) / len(all_nets) * 100

    # Compute z-score (used by quality_gates.py COT gate as cot_net_z)
    import statistics as _stats
    _all_raw = [p["net"] for p in net_positions]
    _mean = _stats.mean(_all_raw)
    _std = _stats.stdev(_all_raw) if len(_all_raw) >= 2 else 1.0
    cot_net_z = round((current_net - _mean) / (_std if _std else 1.0), 3)

    # Determine signal
    if rank >= EXTREME_LONG_PERCENTILE:
        signal = "SELL"  # Commercials extremely long = bearish reversal coming
        confidence = min(95, 50 + (rank - EXTREME_LONG_PERCENTILE) * 2)
        reason = f"Commercial net at {rank:.0f}th percentile (extremely long). Bearish reversal likely."
    elif rank <= EXTREME_SHORT_PERCENTILE:
        signal = "BUY"  # Commercials extremely short = bullish reversal coming
        confidence = min(95, 50 + (EXTREME_SHORT_PERCENTILE - rank) * 2)
        reason = f"Commercial net at {rank:.0f}th percentile (extremely short). Bullish reversal likely."
    else:
        signal = "NEUTRAL"
        confidence = 0
        reason = f"Commercial net at {rank:.0f}th percentile. No extreme positioning."

    return {
        "signal": signal,
        "confidence": confidence,
        "reason": reason,
        "percentile_rank": round(rank, 1),
        "cot_net_z": cot_net_z,
        "current_net": current_net,
        "lookback_weeks": len(net_positions),
        "latest_date": net_positions[0]["date"],
    }


def _is_cot_row_public(report_date_str: str, today: Optional["datetime"] = None,
                      lag_days: int = COT_PUBLICATION_LAG_DAYS) -> bool:
    """Return True if a CFTC COT row with the given report_date is already
    publicly released (Friday ~3:30pm ET) and therefore safe to use for a
    signal generated `today`. See module-level COT_PUBLICATION_LAG_DAYS doc.
    """
    if not report_date_str:
        return False
    try:
        report_dt = datetime.strptime(report_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return False
    today_dt = (today or datetime.now(timezone.utc)).date()
    return (today_dt - report_dt).days >= lag_days


def cot_positioning_strategy(data: dict, symbol: str = "") -> list:
    """
    Scanner-compatible strategy function.
    Generates BUY/SELL signals based on COT extreme positioning.
    """
    picks = []
    now_dt = datetime.now(timezone.utc)
    now = now_dt.isoformat()
    emitted_keys = _load_emitted_releases()

    for pair, info in COT_CONTRACTS.items():
        # Skip if symbol filter doesn't match
        if symbol and pair not in symbol and symbol not in pair:
            continue

        reports = fetch_cot_data_cftc(info["code"])
        if not reports:
            continue

        result = compute_net_positioning(reports)

        if result["signal"] == "NEUTRAL":
            continue

        # Publication-lag guard: do not emit a pick that depends on COT data
        # released after `now`. See COT_PUBLICATION_LAG_DAYS at top of module.
        if not _is_cot_row_public(result.get("latest_date", ""), today=now_dt):
            continue

        # Per-release dedup: one pick per (symbol, direction, CFTC release).
        # Direction is in the key so an intra-week SHORT->LONG flip emits as
        # a new signal rather than being silently suppressed (PR #994 review
        # 2026-05-14).
        _release_dir = _normalize_direction(result["signal"])
        release_key = (pair, _release_dir, result.get("latest_date", ""))
        if release_key in emitted_keys:
            continue
        emitted_keys.add(release_key)

        # Map pair to tradeable symbol
        tradeable = pair
        if "=X" not in pair:
            tradeable = pair + "=X"  # Yahoo format

        _record_emitted_release(pair, result["signal"],
                                result.get("latest_date", ""), now)
        picks.append({
            "symbol": tradeable.replace("=X", ""),
            "signal": result["signal"],
            "direction": result["signal"],
            "strategy": "cot_positioning",
            "confidence": result["confidence"],
            "reason": result["reason"],
            "percentile_rank": result["percentile_rank"],
            "cot_net_z": result.get("cot_net_z", 0.0),
            "current_net": result["current_net"],
            "lookback_weeks": result["lookback_weeks"],
            "latest_cot_date": result["latest_date"],
            "timeframe": "1w",  # COT is weekly data
            "source": "alpha_engine",
            "timestamp": now,
            "asset_class": "forex",
            "notes": f"CFTC COT {info['name']}: {result['reason']}",
        })

    return picks


# Strategy registry for scanner integration
COT_STRATEGIES = {
    "cot_positioning": cot_positioning_strategy,
}


if __name__ == "__main__":
    print("=" * 60)
    print("  COT POSITIONING SCANNER")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 60)

    now_dt = datetime.now(timezone.utc)
    now = now_dt.isoformat()
    emitted_keys = _load_emitted_releases()
    all_picks = []
    for pair, info in COT_CONTRACTS.items():
        print(f"\n  Fetching COT for {pair} ({info['name']})...")
        reports = fetch_cot_data_cftc(info["code"])
        if reports:
            print(f"    Got {len(reports)} weekly reports")
            result = compute_net_positioning(reports)
            print(f"    Signal: {result['signal']} | Confidence: {result['confidence']}%")
            print(f"    Reason: {result['reason']}")
            if result["signal"] != "NEUTRAL":
                if not _is_cot_row_public(result.get("latest_date", ""), today=now_dt):
                    print(f"    SKIP: report_date {result.get('latest_date')} not yet public (lag guard)")
                    continue
                direction = "SHORT" if result["signal"] == "SELL" else "LONG"
                release_key = (pair, direction, result.get("latest_date", ""))
                if release_key in emitted_keys:
                    print(f"    SKIP: release {result.get('latest_date')} already emitted for {pair} {direction} (dedup)")
                    continue
                emitted_keys.add(release_key)
                _record_emitted_release(pair, direction,
                                        result.get("latest_date", ""), now)
                all_picks.append({
                    # Full pick schema compatible with dashboard_generator._extract_picks
                    "symbol": pair + "=X",
                    "direction": direction,
                    "strategy": "cftc_cot_commercial_signal",
                    "asset_class": "FOREX",
                    "timeframe": "1w",
                    "confidence": result["confidence"],
                    "generated_at": now,
                    # COT-specific extras
                    "pair": pair,
                    "signal": result["signal"],
                    "percentile": result["percentile_rank"],
                    "cot_net_z": result.get("cot_net_z", 0.0),
                    "cot_reason": result["reason"],
                    "current_net": result.get("current_net"),
                    "lookback_weeks": result.get("lookback_weeks"),
                    "latest_cot_date": result.get("latest_date"),
                })
        else:
            print(f"    No data available")

    print(f"\n{'='*60}")
    print(f"  RESULTS: {len(all_picks)} COT signals")
    for p in all_picks:
        print(f"    {p['direction']:5s} {p['pair']:8s} conf={p['confidence']}% rank={p['percentile']}")

    # Save results
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "cot_signals.json")
    with open(out_path, "w") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "scanner": "cot_positioning",
            "picks": all_picks,
        }, f, indent=2)
    print(f"\n  Saved to {out_path}")
