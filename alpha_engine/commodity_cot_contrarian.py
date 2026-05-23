"""Commodity COT non-commercial contrarian — freebuff B4 sidecar.

Mirrors live champion `cftc_cot_commercial_signal` (n=32, WR 68.8%, PF 3.5)
but FADES non-commercials (speculators / CTAs) at 52w percentile extremes:
  pct >=90 -> SHORT (crowd long), pct <=10 -> LONG (crowd short).
Universe: TIER1_COMMODITY (GC SI CL NG HG PL PA + spot variants).
Output schema matches cot_positioning.py so the existing dashboard adapter
can ingest it once registered.

OPT-IN SIDECAR per Wire-Up Rule (CLAUDE.md): no production caller yet.

## Wiring Plan
Target:  audit_trail/dashboard_generator.py JSON_PICK_SOURCES
Path:    alpha_engine/data/commodity_cot_contrarian_signals.json
Adapter: extend cot_positioning adapter to also accept
         strategy='commodity_cot_contrarian' rows (same schema).
Date:    after 2-week paper validation (target 2026-05-23).
Sync:    .github/workflows/forex-agent.yml already fetches CFTC weekly;
         reuse that step — add `python -m alpha_engine.commodity_cot_contrarian`
         after the existing cot_positioning invocation.

Rollback: COMMODITY_COT_CONTRARIAN_DISABLED=1 -> returns [].
Stale-data guard: skip if latest CFTC report > 14d old.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# TP/SL for COT macro signals (weekly horizon, based on synthetic backtest params)
_COT_TP_PCT = float(os.environ.get("COT_TP_PCT", "0.08"))   # 8% take profit
_COT_SL_PCT = float(os.environ.get("COT_SL_PCT", "0.05"))   # 5% stop loss


def _fetch_current_price(ticker: str) -> Optional[float]:
    """Fetch the latest close price for *ticker* via yfinance. Returns None on failure."""
    try:
        import yfinance as yf
        df = yf.download(ticker, period="5d", interval="1d",
                         progress=False, auto_adjust=True)
        if df.empty:
            return None
        close = df["Close"] if "Close" in df.columns else df.iloc[:, 0]
        val = close.dropna().iloc[-1]
        if hasattr(val, "iloc"):
            val = val.iloc[0]
        return float(val) if val is not None else None
    except Exception as exc:
        logger.debug("COT price fetch failed for %s: %s", ticker, exc)
        return None

# CFTC contract codes for the TIER1_COMMODITY universe (legacy futures-only TFF).
# Spot variants (XAUUSD/XAGUSD/etc.) inherit signal from their nearest future.
# 2026-05-14: Expanded 7→21 contracts (swarm 3-engine consensus P1).
# All codes verified against CFTC public reporting API (publicreporting.cftc.gov).
COMMODITY_CONTRACTS: dict[str, dict] = {
    # ── Metals ──────────────────────────────────────────────────────────────────
    "GC": {"code": "088691", "name": "GOLD",         "yahoo": "GC=F"},
    "SI": {"code": "084691", "name": "SILVER",        "yahoo": "SI=F"},
    "HG": {"code": "085692", "name": "COPPER",        "yahoo": "HG=F"},
    "PL": {"code": "076651", "name": "PLATINUM",      "yahoo": "PL=F"},
    "PA": {"code": "075651", "name": "PALLADIUM",     "yahoo": "PA=F"},
    # ── Energy ──────────────────────────────────────────────────────────────────
    "CL": {"code": "067651", "name": "CRUDE OIL WTI", "yahoo": "CL=F"},
    "NG": {"code": "023651", "name": "NATURAL GAS",   "yahoo": "NG=F"},
    "HO": {"code": "022651", "name": "HEATING OIL",   "yahoo": "HO=F"},
    "RB": {"code": "111659", "name": "RBOB GASOLINE",  "yahoo": "RB=F"},
    # ── Grains ──────────────────────────────────────────────────────────────────
    "ZC": {"code": "002602", "name": "CORN",          "yahoo": "ZC=F"},
    "ZW": {"code": "001602", "name": "WHEAT SRW",     "yahoo": "ZW=F"},
    "ZS": {"code": "005602", "name": "SOYBEANS",      "yahoo": "ZS=F"},
    "ZL": {"code": "007601", "name": "SOYBEAN OIL",   "yahoo": "ZL=F"},
    "ZM": {"code": "026603", "name": "SOYBEAN MEAL",  "yahoo": "ZM=F"},
    "ZO": {"code": "004603", "name": "OATS",          "yahoo": "ZO=F"},
    # ── Softs ───────────────────────────────────────────────────────────────────
    "CT": {"code": "033661", "name": "COTTON NO. 2",  "yahoo": "CT=F"},  # top edge: WR 90%+ in paper pilot
    "SB": {"code": "080732", "name": "SUGAR NO. 11",  "yahoo": "SB=F"},
    "KC": {"code": "083731", "name": "COFFEE C",      "yahoo": "KC=F"},
    "CC": {"code": "073732", "name": "COCOA",         "yahoo": "CC=F"},
    # ── Livestock ───────────────────────────────────────────────────────────────
    "LE": {"code": "057642", "name": "LIVE CATTLE",   "yahoo": "LE=F"},
    "HE": {"code": "054642", "name": "LEAN HOGS",     "yahoo": "HE=F"},
}

# CFTC publishes Friday ~3:30pm ET for Tuesday settlement. Picking up on the
# same day or within 3 calendar days uses pre-release data (look-ahead bias).
# Mirror of cot_positioning.py COT_PUBLICATION_LAG_DAYS guard.
COT_PUBLICATION_LAG_DAYS = 3

EXTREME_LONG_PERCENTILE = 90   # speculators extremely net-long  → fade SHORT
EXTREME_SHORT_PERCENTILE = 10  # speculators extremely net-short → fade LONG
LOOKBACK_WEEKS = 52
MAX_REPORT_AGE_DAYS = 14       # freshness gate


# ──────────────────────────────────────────────────────────────────────────────
# CFTC fetch
# ──────────────────────────────────────────────────────────────────────────────
def _fetch_cftc_reports(contract_code: str) -> Optional[list]:
    """Pull last 52 weekly TFF reports for a contract. None on failure."""
    try:
        params = urllib.parse.urlencode({
            "$where": f"cftc_contract_market_code='{contract_code}'",
            "$order": "report_date_as_yyyy_mm_dd DESC",
            "$limit": str(LOOKBACK_WEEKS),
        })
        url = f"https://publicreporting.cftc.gov/resource/6dca-aqww.json?{params}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (commodity_cot_contrarian)",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [COT-CONTRARIAN] CFTC fetch failed for {contract_code}: {e}")
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Signal computation
# ──────────────────────────────────────────────────────────────────────────────
def _is_stale(latest_iso: str, now: Optional[datetime] = None) -> bool:
    """True if latest report is older than MAX_REPORT_AGE_DAYS."""
    if not latest_iso:
        return True
    try:
        d = datetime.strptime(latest_iso[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return True
    n = now or datetime.now(timezone.utc)
    return (n - d) > timedelta(days=MAX_REPORT_AGE_DAYS)


def compute_noncomm_signal(reports: list, now: Optional[datetime] = None) -> dict:
    """
    Net-non-commercial percentile over LOOKBACK_WEEKS, with contrarian mapping.

    Returns dict with: signal (BUY/SELL/NEUTRAL), direction (LONG/SHORT/NEUTRAL),
    confidence (0-95, scales with percentile extremity), percentile_rank,
    current_net, latest_date, stale (bool).
    """
    if not reports or len(reports) < 10:
        return {"signal": "NEUTRAL", "direction": "NEUTRAL", "confidence": 0,
                "reason": "Insufficient data", "stale": False}

    nets: list[int] = []
    dates: list[str] = []
    for r in reports:
        try:
            nc_long = int(r.get("noncomm_positions_long_all", 0) or 0)
            nc_short = int(r.get("noncomm_positions_short_all", 0) or 0)
            nets.append(nc_long - nc_short)
            dates.append(r.get("report_date_as_yyyy_mm_dd", "") or "")
        except (ValueError, TypeError):
            continue

    if len(nets) < 10:
        return {"signal": "NEUTRAL", "direction": "NEUTRAL", "confidence": 0,
                "reason": "Insufficient valid data", "stale": False}

    latest_date = dates[0] if dates else ""
    stale = _is_stale(latest_date, now=now)
    if stale:
        return {"signal": "NEUTRAL", "direction": "NEUTRAL", "confidence": 0,
                "reason": f"Latest CFTC report {latest_date} > {MAX_REPORT_AGE_DAYS}d old",
                "stale": True, "latest_date": latest_date}

    arr = np.asarray(nets, dtype=float)
    current_net = float(arr[0])
    # Percentile rank of current within the 52w window (inclusive lower).
    rank = float(np.mean(arr <= current_net) * 100.0)

    if rank >= EXTREME_LONG_PERCENTILE:
        # Speculators piled long → contrarian SHORT
        signal, direction = "SELL", "SHORT"
        confidence = float(min(95, 50 + (rank - EXTREME_LONG_PERCENTILE) * 4))
        reason = (f"Non-commercial net at {rank:.0f}th percentile (52w). "
                  "Speculator crowd extremely long — fade.")
    elif rank <= EXTREME_SHORT_PERCENTILE:
        # Speculators piled short → contrarian LONG
        signal, direction = "BUY", "LONG"
        confidence = float(min(95, 50 + (EXTREME_SHORT_PERCENTILE - rank) * 4))
        reason = (f"Non-commercial net at {rank:.0f}th percentile (52w). "
                  "Speculator crowd extremely short — fade.")
    else:
        signal, direction = "NEUTRAL", "NEUTRAL"
        confidence = 0.0
        reason = f"Non-commercial net at {rank:.0f}th percentile. No extreme."

    return {
        "signal": signal,
        "direction": direction,
        "confidence": round(confidence, 1),
        "reason": reason,
        "percentile_rank": round(rank, 1),
        "current_net": current_net,
        "lookback_weeks": len(nets),
        "latest_date": latest_date,
        "stale": False,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Public entry point
# ──────────────────────────────────────────────────────────────────────────────
def commodity_cot_contrarian_picks() -> list[dict]:
    """Pull CFTC TFF for the TIER1_COMMODITY universe and emit contrarian picks.

    Returns [] cleanly when COMMODITY_COT_CONTRARIAN_DISABLED=1, on any fetch
    failure, on stale (>14d) reports, or when no symbol shows extreme positioning.
    """
    if os.environ.get("COMMODITY_COT_CONTRARIAN_DISABLED") == "1":
        return []

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    picks: list[dict] = []

    for sym, info in COMMODITY_CONTRACTS.items():
        reports = _fetch_cftc_reports(info["code"])
        if not reports:
            continue
        result = compute_noncomm_signal(reports, now=now)
        if result["signal"] == "NEUTRAL":
            continue

        # COT timing lag guard: CFTC data is published Friday ~3:30pm ET for
        # the prior Tuesday. Do not emit if the report date is within
        # COT_PUBLICATION_LAG_DAYS of today (pick would use pre-release data).
        latest_cot_date = result.get("latest_date", "")
        if latest_cot_date:
            try:
                report_dt = datetime.strptime(latest_cot_date[:10], "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
                if (now - report_dt).days < COT_PUBLICATION_LAG_DAYS:
                    print(
                        f"  [COT-LAG-GUARD] {sym}: report {latest_cot_date} within "
                        f"{COT_PUBLICATION_LAG_DAYS}d — skip (look-ahead risk)"
                    )
                    continue
            except (ValueError, TypeError):
                pass

        # Fetch current price so the pick passes the entry_price gate downstream.
        current_price = _fetch_current_price(info["yahoo"])
        entry_price = current_price  # mark-to-market at signal time
        take_profit: Optional[float] = None
        stop_loss: Optional[float] = None
        if entry_price is not None and entry_price > 0:
            direction = result["direction"]
            if direction == "SHORT":
                take_profit = round(entry_price * (1 - _COT_TP_PCT), 4)
                stop_loss = round(entry_price * (1 + _COT_SL_PCT), 4)
            else:  # LONG
                take_profit = round(entry_price * (1 + _COT_TP_PCT), 4)
                stop_loss = round(entry_price * (1 - _COT_SL_PCT), 4)

        picks.append({
            "symbol": info["yahoo"],
            "direction": result["direction"],
            "signal": result["signal"],
            "strategy": "commodity_cot_contrarian",
            "asset_class": "COMMODITY",
            "category": "commodity",
            "timeframe": "1w",
            "confidence": round(result["confidence"] / 100.0, 4),  # normalize 0-100 → 0-1
            "generated_at": now_iso,
            "timestamp": now_iso,
            "source": "alpha_engine",
            "source_system": "commodity_cot_contrarian",
            "pair": sym,
            "percentile": result["percentile_rank"],
            "current_net": result["current_net"],
            "lookback_weeks": result["lookback_weeks"],
            "latest_cot_date": result["latest_date"],
            "cot_reason": result["reason"],
            "reason": (f"Non-commercial CONTRARIAN {info['name']}: "
                       f"{result['reason']}"),
            "notes": ("Contrarian: fades crowded speculator positioning. "
                      f"Twin to cftc_cot_commercial_signal."),
            "entry_price": entry_price,
            "take_profit": take_profit,
            "stop_loss": stop_loss,
            "price": current_price,
        })

    return picks


# ──────────────────────────────────────────────────────────────────────────────
# Synthetic backtest (mock CFTC, deterministic)
# ──────────────────────────────────────────────────────────────────────────────
def _synthetic_backtest(seed: int = 42, weeks: int = 104,
                        tp_pct: float = 0.08, sl_pct: float = 0.05,
                        horizon_weeks: int = 4) -> dict:
    """Generate 2y of synthetic non-commercial net + price series and replay
    the strategy. Mean-reverting price w/ noise; signals fired at extreme
    percentiles, evaluated on next 4w return vs ±tp/sl."""
    rng = np.random.default_rng(seed)
    # Synthetic non-commercial net (random walk with drift back to 0)
    nc = np.zeros(weeks)
    price = np.zeros(weeks)
    price[0] = 100.0
    for t in range(1, weeks):
        nc[t] = nc[t - 1] * 0.95 + rng.normal(0, 50_000)
        # Price reverts inversely to spec positioning + noise
        revert = -0.0008 * nc[t - 1] / 50_000  # spec long → next-week price drag
        price[t] = price[t - 1] * (1.0 + revert + rng.normal(0, 0.025))

    n_signals = 0
    wins = 0
    losses = 0
    for t in range(LOOKBACK_WEEKS, weeks - horizon_weeks):
        window = nc[t - LOOKBACK_WEEKS:t + 1]
        rank = float(np.mean(window <= nc[t]) * 100.0)
        if rank >= EXTREME_LONG_PERCENTILE:
            direction = "SHORT"
        elif rank <= EXTREME_SHORT_PERCENTILE:
            direction = "LONG"
        else:
            continue
        n_signals += 1
        # Evaluate path over next horizon_weeks for first TP/SL touch
        entry = price[t]
        outcome = None
        for k in range(1, horizon_weeks + 1):
            ret = (price[t + k] - entry) / entry
            if direction == "LONG":
                if ret >= tp_pct:
                    outcome = "WIN"; break
                if ret <= -sl_pct:
                    outcome = "LOSS"; break
            else:  # SHORT
                if ret <= -tp_pct:
                    outcome = "WIN"; break
                if ret >= sl_pct:
                    outcome = "LOSS"; break
        if outcome is None:
            # mark-to-market at horizon end
            ret = (price[t + horizon_weeks] - entry) / entry
            if direction == "SHORT":
                ret = -ret
            outcome = "WIN" if ret > 0 else "LOSS"
        if outcome == "WIN":
            wins += 1
        else:
            losses += 1

    wr = (wins / n_signals * 100.0) if n_signals else 0.0
    return {
        "n_signals": n_signals,
        "wins": wins,
        "losses": losses,
        "win_rate_pct": round(wr, 1),
        "tp_pct": tp_pct,
        "sl_pct": sl_pct,
        "horizon_weeks": horizon_weeks,
        "weeks_simulated": weeks,
    }


if __name__ == "__main__":
    bt = _synthetic_backtest()
    print(f"COMMODITY_COT_CONTRARIAN backtest: "
          f"weeks={bt['weeks_simulated']} signals={bt['n_signals']} "
          f"WR={bt['win_rate_pct']}% (W{bt['wins']}/L{bt['losses']}, "
          f"TP{bt['tp_pct']*100:.0f}% SL{bt['sl_pct']*100:.0f}% "
          f"horiz{bt['horizon_weeks']}w)")
    live = commodity_cot_contrarian_picks()
    print(f"live picks emitted: {len(live)}")
    for p in live:
        print(f"  {p['direction']:5s} {p['symbol']:6s} "
              f"conf={p['confidence']}% pct={p['percentile']}")
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "commodity_cot_contrarian_signals.json")
    with open(out_path, "w") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "scanner": "commodity_cot_contrarian",
            "backtest": bt, "picks": live,
        }, f, indent=2)
    print(f"saved -> {out_path}")
