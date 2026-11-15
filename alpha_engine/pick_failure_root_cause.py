#!/usr/bin/env python3
"""Root-cause labels and per-class success criteria. No price fetch. No future bars."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

# Calendar hours a thesis is allowed to live. Resolver class defaults (48-120h)
# are shorter than these on purpose for scalps; trend cards must set max_hold_hours.
HOLD_MIN_H = 24
HOLD_MAX_H = 24 * 90

SUCCESS_CRITERIA = {
    "ETF": {
        "monitor": "Signal uses bars through signal_asof only. Enter next session, not the signal close. Hold 21 calendar days (504h), not the 96h resolver default. Benchmark SPY.",
        "promote": "n>=100 horizon-closes, net PF>=1.5 after 10bps, beat SPY over the same windows, no same-bar entry. Until then sizing_allowed=false.",
        "horizon_hours": 504,
        "benchmark": "SPY",
        "emit_now": True,
    },
    "EQUITY": {
        "monitor": "Same as ETF. One name, ranked on data through signal_asof. Benchmark SPY. Hold 504h.",
        "promote": "n>=100, net PF>=1.5 after 10bps, beat SPY, no same-bar entry. sizing_allowed=false until then.",
        "horizon_hours": 504,
        "benchmark": "SPY",
        "emit_now": True,
    },
    "BOND": {
        "monitor": "Duration regime from TLT vs SMA200 known at signal_asof. SHY is ballast, not alpha. Hold 480h. Benchmark BIL.",
        "promote": "n>=100, beat BIL after costs, max drawdown under 5%. Not a TP/SL scalp.",
        "horizon_hours": 480,
        "benchmark": "BIL",
        "emit_now": True,
    },
    "CRYPTO": {
        "monitor": "No card unless close>SMA200 and 21d return>0 at signal_asof. Resolver window 48h matches a 4h/1d rule only. Benchmark BTC-USD.",
        "promote": "n>=100, net PF>=1.5, PBO<0.3, beat BTC-USD after costs. Shorts stay off.",
        "horizon_hours": 48,
        "benchmark": "BTC-USD",
        "emit_now": False,
    },
    "FOREX": {
        "monitor": "No card. Class is frozen for sign-flip and source-concentration contamination.",
        "promote": "Unfreeze only after a clean feed and n>=100 net of spread. Not this round.",
        "horizon_hours": 72,
        "benchmark": "USD",
        "emit_now": False,
    },
    "COMMODITY": {
        "monitor": "No card unless close>SMA200 and 21d return>0 at signal_asof. 96h resolver window is too short for 63d momentum.",
        "promote": "n>=100, beat DBC after costs, horizon explicit.",
        "horizon_hours": 504,
        "benchmark": "DBC",
        "emit_now": False,
    },
    "FUTURES": {
        "monitor": "No separate card. Index futures duplicate ETF beta. Commodity futures use COMMODITY rules.",
        "promote": "Not a separate book.",
        "horizon_hours": 96,
        "benchmark": "SPY",
        "emit_now": False,
    },
    "MUTUAL_FUND": {
        "monitor": "Not a TP/SL pick. Daily NAV only. Screen for passive core: ER, no load, no 12b-1, AUM, Admiral min <= $3000. Missing field is INSUFFICIENT, not a fail.",
        "promote": "Never promote as an active pick.",
        "horizon_hours": None,
        "benchmark": "stated index",
        "emit_now": False,
    },
    "PREDICTION_MARKET": {
        "monitor": "No card. Zero-sum minus fees and adverse selection.",
        "promote": "Rejected.",
        "horizon_hours": None,
        "benchmark": None,
        "emit_now": False,
    },
}


def explicit_hold_hours(pick: dict):
    """Return a sane per-pick hold, or None to keep the class default."""
    if not isinstance(pick, dict):
        return None
    raw = pick.get("max_hold_hours", pick.get("horizon_hours"))
    if raw in (None, ""):
        return None
    try:
        hours = int(float(raw))
    except (TypeError, ValueError):
        return None
    if HOLD_MIN_H <= hours <= HOLD_MAX_H:
        return hours
    return None


def _parse_ts(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def diagnose(pick: dict, now=None) -> dict:
    """Label why a pick cannot be treated as a measured result.

    Uses only fields on the pick. `now` is optional and must be timezone-aware.
    Does not look at prices after signal_asof.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    ac = str(pick.get("asset_class") or "UNKNOWN").upper()
    criteria = SUCCESS_CRITERIA.get(ac, {})
    reasons = []
    status = str(pick.get("status") or "OPEN").upper()
    signal_asof = _parse_ts(pick.get("signal_asof"))
    entry_time = _parse_ts(pick.get("entry_time") or pick.get("timestamp"))
    basis = str(pick.get("entry_basis") or "").lower()
    leakage = str(pick.get("leakage") or "")

    if "SAME_BAR" in leakage.upper() or basis in {"same_bar_close", "signal_close"}:
        reasons.append("SAME_BAR_ENTRY")
    if signal_asof and entry_time and entry_time <= signal_asof:
        reasons.append("LOOKAHEAD_ENTRY_NOT_AFTER_SIGNAL")

    hold = explicit_hold_hours(pick)
    class_default = {"ETF": 96, "EQUITY": 96, "BOND": 120, "CRYPTO": 48, "FOREX": 72, "COMMODITY": 96, "FUTURES": 96}.get(ac)
    thesis_h = criteria.get("horizon_hours")
    if thesis_h and class_default and thesis_h > class_default and hold is None:
        reasons.append("HORIZON_MISMATCH")
    if thesis_h and hold and hold < thesis_h:
        reasons.append("HORIZON_SHORTER_THAN_THESIS")

    if status in {"OPEN", "ACTIVE", "PENDING", "LIVE"}:
        if pick.get("pnl_pct") in (0, 0.0, "0", "0.0"):
            reasons.append("OPEN_PNL_UNMEASURED")
        for field in ("exit_price", "exit_time", "resolution_method"):
            if pick.get(field) in (None, ""):
                reasons.append("QA_FALSE_FAIL_IF_EXIT_REQUIRED")
                break
    if status in {"CLOSED", "TIME_EXIT", "EXPIRED"} and pick.get("pnl_pct") in (None, 0, 0.0):
        reasons.append("UNMEASURED_CLOSE")

    if criteria.get("emit_now") is False and status in {"OPEN", "ACTIVE", "PENDING", ""}:
        reasons.append("CLASS_SHOULD_NOT_EMIT")

    if pick.get("sizing_allowed") is True and "NO_EDGE" not in reasons:
        reasons.append("SIZING_WITHOUT_PROMOTION")

    # De-dupe, stable order
    seen = []
    for r in reasons:
        if r not in seen:
            seen.append(r)
    return {
        "id": pick.get("id"),
        "symbol": pick.get("symbol"),
        "asset_class": ac,
        "reasons": seen,
        "monitor": criteria.get("monitor"),
        "promote": criteria.get("promote"),
        "benchmark": criteria.get("benchmark"),
        "thesis_horizon_hours": thesis_h,
        "resolver_default_hours": class_default,
        "applied_hold_hours": hold,
        "promotable": False,
    }


def main():
    path = None
    out = None
    args = sys.argv[1:]
    if "--picks" in args:
        path = args[args.index("--picks") + 1]
    if "--out" in args:
        out = args[args.index("--out") + 1]
    if not path:
        print("usage: python3 -m alpha_engine.pick_failure_root_cause --picks FILE [--out FILE]")
        return 2
    payload = json.loads(open(path, encoding="utf-8").read())
    picks = payload.get("picks", payload if isinstance(payload, list) else [])
    rows = [diagnose(p) for p in picks if isinstance(p, dict)]
    text = json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(), "rows": rows}, indent=2)
    if out:
        open(out, "w", encoding="utf-8").write(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
