#!/usr/bin/env python3
"""Resolve provenance-ledger picks into outcomes — without ever touching the picks.

THE OTHER HALF OF THE LOOP
    tools/provenance_ledger.py records intent at emit time. On its own that proves
    a pick existed before an outcome, but nothing ever computes the outcome, so
    pct_forward stays null and no statistic can be formed.

    This reads the pick ledger, decides each pick's outcome from market data, and
    appends the outcome to a SEPARATE append-only file. The pick records are never
    modified — that is the entire guarantee. If a resolver could rewrite the picks
    it could backfill them, and the ledger would be worthless.

CONVENTIONS (chosen to be pessimistic, and stated so they can be argued with)
  * Entry at the FIRST bar OPEN at or after signal_ts. Never at the signal price.
  * If a bar's range touches BOTH TP and SL, the SL is assumed to have filled
    first. Intrabar ordering is unknowable from OHLC, so the pessimistic branch is
    the only defensible one. This systematically understates win rate.
  * A pick with no resolution within MAX_DAYS stays OPEN, not "expired as a win".
  * Outcomes are appended with their own hash chain, so a resolution cannot be
    edited after the fact either.
  * `resolved_at` is stamped when THIS PROCESS decides, and must be > created_at.

WHAT IT REPORTS
    n_emitted / n_resolved / n_open / pct_forward / hit rate / mean / PF,
    and per-strategy and per-side breakdowns.

Read-only on picks. Append-only on resolutions. No orders, no keys. Not advice.

Usage:
    python3 tools/provenance_resolver.py --status
    python3 tools/provenance_resolver.py --resolve
    python3 tools/provenance_resolver.py --selftest
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PICKS = REPO / "reports/provenance/picks_provenance.jsonl"
RES = REPO / "reports/provenance/resolutions.jsonl"
STATUS = REPO / "reports/provenance/resolved_status.json"
GENESIS = "0" * 64
MAX_DAYS = 45

# --- gate thresholds (see cmd_gate) ---
PCT_FORWARD_MIN = 95.0     # resolved-after-creation share required to pass
MIN_RESOLVED = 20          # below this pct_forward is too noisy to enforce
STARVE_GRACE_DAYS = 7      # picks pending longer than MAX_DAYS + this = starved


# ---------------------------------------------------------------- helpers
def _canon(rec: dict) -> bytes:
    return json.dumps(rec, sort_keys=True, separators=(",", ":")).encode()


def _sha(rec: dict) -> str:
    return hashlib.sha256(_canon(rec)).hexdigest()


def read_jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    out = []
    for line in p.open():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


# ------------------------------------------------------- symbol resolution
# BTC-only resolution would leave every FOREX / COMMODITY / EQUITY / BOND pick
# permanently OPEN, which is indistinguishable from "never resolved" and would
# silently understate pct_forward. So map every class onto a yfinance symbol.

_CRYPTO_QUOTE = ("USDT", "USDC", "BUSD", "USDP", "TUSD", "FDUSD", "DAI", "PERP")

# Known coin bases. Needed only for the separator-less "BTCUSD" form; the guard
# exists so a 6-letter equity ticker cannot be silently rewritten into a crypto
# pair that returns no data.
_CRYPTO_BASES = frozenset({
    "BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "BNB", "AVAX", "DOT", "LINK",
    "MATIC", "POL", "LTC", "BCH", "ATOM", "NEAR", "APT", "ARB", "OP", "SUI",
    "INJ", "TIA", "SEI", "PEPE", "SHIB", "TRX", "TON", "XLM", "ETC", "FIL",
    "RNDR", "AAVE", "UNI", "MKR", "CRV", "LDO", "FET", "WLD", "JUP", "PYTH",
    "STRK", "ENA", "ONDO", "JTO", "WIF", "BONK", "FLOKI", "HBAR", "ICP",
})

# ISO-4217 codes. A 6-letter token is only treated as an FX pair when BOTH halves
# are real currencies -- otherwise 6-letter equity tickers get silently mangled
# into a nonexistent FX pair that simply returns no data.
_FX_CCY = frozenset({
    "USD", "EUR", "GBP", "JPY", "CHF", "AUD", "NZD", "CAD", "CNH", "CNY",
    "SEK", "NOK", "DKK", "MXN", "ZAR", "TRY", "SGD", "HKD", "PLN", "HUF",
    "CZK", "ILS", "INR", "BRL", "RUB", "THB", "KRW", "TWD",
})

# Metals / energy quoted as CFD-style spot codes but only tradeable on yfinance as
# the front future. Gold and silver were the two named in the roadmap.
_CFD_TO_FUT = {
    "XAUUSD": "GC=F", "XAGUSD": "SI=F", "XPTUSD": "PL=F", "XPDUSD": "PA=F",
    "WTIUSD": "CL=F", "BRENTUSD": "BZ=F", "NATGAS": "NG=F", "COPPER": "HG=F",
    "USOIL": "CL=F", "UKOIL": "BZ=F",
}

_INDEX_CFD = {
    "SPX500": "^GSPC", "US500": "^GSPC", "SPX": "^GSPC",
    "NAS100": "^NDX", "US100": "^NDX", "NDX": "^NDX",
    "US30": "^DJI", "DJI": "^DJI",
    "GER40": "^GDAXI", "DAX": "^GDAXI", "UK100": "^FTSE", "JP225": "^N225",
}

# Treasury / credit ETFs are ordinary tickers, so without this they get labelled
# EQUITY and the per-class provenance breakdown silently misattributes bonds.
_BOND_ETFS = frozenset({
    "TLT", "IEF", "SHY", "AGG", "BND", "LQD", "HYG", "TIP", "GOVT", "TLH",
    "EMB", "JNK", "MUB", "VCIT", "VCSH", "BIL", "SHV", "SGOV", "IGSB", "HYLB",
})


def resolve_symbol(sym: str) -> tuple[str, str]:
    """Map a repo symbol onto (yfinance_symbol, asset_class).

    Handles crypto pairs, FX pairs, CFD-style metals/energy, index CFDs and
    leaves plain tickers (SPY, AAPL, TLT) untouched.
    """
    raw = (sym or "").strip().upper()
    # normalise separators: BTC/USDT, BTC_USDT, BTC-USDT all become BTCUSDT
    compact = raw.replace("/", "").replace("_", "").replace("-", "")
    if not compact:
        return raw, "UNKNOWN"

    # 1. explicit CFD / index tables win before anything else
    if compact in _CFD_TO_FUT:
        return _CFD_TO_FUT[compact], "COMMODITY"
    if compact in _INDEX_CFD:
        return _INDEX_CFD[compact], "INDEX"

    # 2. crypto quote suffixes
    for q in _CRYPTO_QUOTE:
        if compact.endswith(q) and len(compact) > len(q) + 1:
            return f"{compact[:-len(q)]}-USD", "CRYPTO"

    # 2b. "BTCUSD" (USD quote, no separator) -- only when the base is a KNOWN coin,
    #     so a 6-letter equity ticker is never mistaken for a crypto pair
    if compact.endswith("USD") and len(compact) > 3:
        base = compact[:-3]
        if base in _CRYPTO_BASES:
            return f"{base}-USD", "CRYPTO"

    # 3. FX pair -- only when both halves are currencies
    if len(compact) == 6 and compact.isalpha():
        base, quote = compact[:3], compact[3:]
        if base in _FX_CCY and quote in _FX_CCY:
            return f"{compact}=X", "FOREX"

    # 4. already a yfinance future / index
    if raw.endswith("=F") or raw.startswith("^"):
        return raw, "FUTURE" if raw.endswith("=F") else "INDEX"

    # 5. plain ticker. Crypto pairs written as "BTC-USD" survive here because the
    #    dash was stripped to BTCUSD and matched rule 2 already.
    if raw in _BOND_ETFS:
        return raw, "BOND"
    return raw, "EQUITY"


def yf_symbol(sym: str) -> str:
    """Backwards-compatible thin wrapper -> just the yfinance symbol."""
    return resolve_symbol(sym)[0]


_INTERVALS = ("1h", "1d")   # 1h first, daily as the fallback


def load_bars(symbols: list[str], start: datetime) -> tuple[dict, dict]:
    """Download bars, falling back 1h -> 1d per symbol.

    Returns (frames, interval_by_symbol). The interval matters: `bars_held` is
    only comparable within an interval, so the resolution record stores it rather
    than silently mixing hour-counts and day-counts in one column.

    1h data on yfinance is capped at ~730 calendar days, so old picks legitimately
    fall back to daily rather than being reported as "no data".
    """
    import yfinance as yf
    frames: dict = {}
    used: dict = {}
    for s in symbols:
        for interval in _INTERVALS:
            try:
                df = yf.download(s, start=start.date(), progress=False,
                                 auto_adjust=False, interval=interval, timeout=25)
            except Exception:  # noqa: BLE001
                continue
            if df is None or df.empty:
                continue
            if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
                df.columns = [c[0] for c in df.columns]
            frames[s] = df
            used[s] = interval
            break
    return frames, used


def decide(pick: dict, bars) -> dict | None:
    """Return an outcome dict or None if still open / no data."""
    side = pick["side"]
    tp, sl = float(pick["tp"]), float(pick["sl"])
    start = datetime.fromisoformat(pick["created_at"])
    if bars is None or bars.empty:
        return None
    idx = bars.index
    try:
        # entry at the first bar at/after creation
        if idx.tz is not None:
            mask = idx >= start
        else:
            mask = idx >= start.replace(tzinfo=None)
        pos = int(mask.argmax()) if mask.any() else -1
    except (TypeError, ValueError):
        return None
    if pos < 0:
        return None
    entry = float(bars["Open"].iloc[pos]) if "Open" in bars else float(bars["Close"].iloc[pos])
    if not (entry > 0):
        return None
    # Guard: a level on the wrong side of the ACTUAL fill is a data defect, not a
    # trade. provenance_ledger.validate_pick() checks TP/SL against the signal-time
    # entry_ref, but the resolver fills at a different bar's open; if the market
    # gapped between signal and fill, TP/SL can end up inverted relative to the real
    # entry and would otherwise be booked as a "TP" that lost money (observed on real
    # data: SPY "TP" at -746.8bp, TLT "SL" at +203.0bp). Refuse those instead.
    if side == "LONG" and not (tp > entry > sl):
        return {"outcome": "INVALID_LEVELS", "entry_px": entry, "exit_px": entry,
                "exit_utc": start.isoformat(), "bars_held": 0}
    if side == "SHORT" and not (tp < entry < sl):
        return {"outcome": "INVALID_LEVELS", "entry_px": entry, "exit_px": entry,
                "exit_utc": start.isoformat(), "bars_held": 0}
    deadline = start + timedelta(days=MAX_DAYS)
    for i in range(pos, len(bars)):
        ts = idx[i]
        t = ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        if t > deadline:
            break
        hi = float(bars["High"].iloc[i]) if "High" in bars else float(bars["Close"].iloc[i])
        lo = float(bars["Low"].iloc[i]) if "Low" in bars else float(bars["Close"].iloc[i])
        hit_tp = hi >= tp if side == "LONG" else lo <= tp
        hit_sl = lo <= sl if side == "LONG" else hi >= sl
        if hit_sl:                      # pessimistic: SL first on ambiguity
            return {"outcome": "SL", "exit_px": sl, "exit_utc": t.isoformat(),
                    "entry_px": entry, "bars_held": i - pos + 1}
        if hit_tp:
            return {"outcome": "TP", "exit_px": tp, "exit_utc": t.isoformat(),
                    "entry_px": entry, "bars_held": i - pos + 1}
    return None


def ret_bp(pick: dict, o: dict) -> float:
    r = (o["exit_px"] / o["entry_px"] - 1) * 1e4
    return -r if pick["side"] == "SHORT" else r


def append_resolutions(rows: list[dict], path: Path | None = None) -> int:
    # NB: default must be resolved at CALL time, not bound at def time. A
    # `path: Path = RES` signature captures the original Path object forever, so any
    # later re-pointing of RES is silently ignored and the chain is written/verified
    # against the wrong file. Same bug class in verify_resolutions() below.
    path = path or RES
    prev = GENESIS
    existing = read_jsonl(path)
    if existing:
        prev = existing[-1]["sha256"]
    seq = len(existing)
    with path.open("a") as f:
        for r in rows:
            seq += 1
            rec = dict(r, seq=seq, prev_sha256=prev)
            rec["sha256"] = _sha(rec)
            prev = rec["sha256"]
            f.write(json.dumps(rec, sort_keys=True) + "\n")
    return len(rows)


def verify_resolutions(path: Path | None = None) -> dict:
    path = path or RES
    recs = read_jsonl(path)
    prev = GENESIS
    for i, r in enumerate(recs):
        stored = r.get("sha256")
        body = {k: v for k, v in r.items() if k != "sha256"}
        if r.get("seq") != i + 1:
            return {"ok": False, "index": i, "reason": "seq gap"}
        if r.get("prev_sha256") != prev:
            return {"ok": False, "index": i, "reason": "prev_sha256 mismatch"}
        if _sha(body) != stored:
            return {"ok": False, "index": i, "reason": "sha256 mismatch"}
        prev = stored
    return {"ok": True, "n": len(recs)}


def compute_status() -> dict:
    picks = read_jsonl(PICKS)
    res = read_jsonl(RES)
    by_pick = {r["pick_seq"]: r for r in res}
    resolved = [p for p in picks if p["seq"] in by_pick]
    # pct_forward: resolved picks whose resolution was decided AFTER creation
    fwd = 0
    for p in resolved:
        r = by_pick[p["seq"]]
        try:
            if datetime.fromisoformat(r["resolved_at"]) > datetime.fromisoformat(p["created_at"]):
                fwd += 1
        except (KeyError, ValueError):
            pass
    rets = []
    for p in resolved:
        r = by_pick[p["seq"]]
        try:
            rets.append(ret_bp(p, {"exit_px": float(r["exit_px"]),
                                   "entry_px": float(r["entry_px"])}))
        except (KeyError, TypeError, ValueError):
            continue

    def pf(xs):
        w = sum(v for v in xs if v > 0)
        l = -sum(v for v in xs if v < 0)
        return (w / l) if l > 0 else (float("nan") if not w else float("inf"))

    st = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_emitted": len(picks),
        "n_resolved": len(resolved),
        "n_open": len(picks) - len(resolved),
        "n_forward": fwd,
        "pct_forward": (100 * fwd / len(resolved)) if resolved else None,
        "resolution_chain_ok": verify_resolutions(RES).get("ok"),
    }
    if rets:
        st.update({
            "mean_bp": sum(rets) / len(rets),
            "median_bp": sorted(rets)[len(rets) // 2],
            "hit_rate": 100 * sum(1 for v in rets if v > 0) / len(rets),
            "profit_factor": pf(rets),
            "worst_bp": min(rets),
            "best_bp": max(rets),
        })
    return st


def cmd_resolve() -> int:
    picks = read_jsonl(PICKS)
    if not picks:
        print("BLOCKED: pick ledger is empty. Nothing to resolve.")
        print("It fills the first time alpha_engine/production_scanner.py runs with")
        print("the section-6y provenance hook merged.")
        return 3
    res = read_jsonl(RES)
    done = {r["pick_seq"] for r in res}
    todo = [p for p in picks if p["seq"] not in done]
    print(f"picks {len(picks)}  already resolved {len(done)}  to resolve {len(todo)}")
    if not todo:
        print("nothing new to resolve")
        return 0

    # map every pick once; a pick whose symbol cannot be mapped must be counted as
    # no_data, never silently dropped
    mapped = {p["seq"]: resolve_symbol(p["symbol"]) for p in todo}
    symbols = sorted({m[0] for m in mapped.values() if m[0]})
    oldest = min(datetime.fromisoformat(p["created_at"]) for p in todo)
    print(f"resolving {len(todo)} pick(s) across {len(symbols)} yfinance symbol(s) "
          f"from {oldest:%Y-%m-%d}")
    for cls in sorted({m[1] for m in mapped.values()}):
        n = sum(1 for m in mapped.values() if m[1] == cls)
        print(f"  {cls:<10} {n} pick(s)")
    bars, intervals = load_bars(symbols, oldest - timedelta(days=2))
    print(f"loaded {len(bars)}/{len(symbols)} series")
    if intervals:
        by_iv: dict[str, int] = {}
        for iv in intervals.values():
            by_iv[iv] = by_iv.get(iv, 0) + 1
        print(f"  intervals: {by_iv}")

    rows, still_open, no_data, invalid = [], 0, 0, 0
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for p in todo:
        yfs, asset_class = mapped[p["seq"]]
        b = bars.get(yfs)
        if b is None:
            no_data += 1
            continue
        o = decide(p, b)
        if o is None:
            still_open += 1
            continue
        if o["outcome"] == "INVALID_LEVELS":
            invalid += 1
            continue
        rows.append({"pick_seq": p["seq"], "symbol": p["symbol"],
                     "yf_symbol": yfs, "asset_class": asset_class,
                     "bar_interval": intervals.get(yfs), "side": p["side"],
                     "outcome": o["outcome"], "entry_px": o["entry_px"],
                     "exit_px": o["exit_px"], "exit_utc": o["exit_utc"],
                     "bars_held": o["bars_held"], "resolved_at": now,
                     "convention": "next_bar_open_entry, SL_first_on_ambiguity"})
    if rows:
        n = append_resolutions(rows)
        print(f"appended {n} resolution(s) -> {RES.relative_to(REPO)}")
    elif no_data:
        print("::warning::no market data for any pending pick this pass")
    if invalid:
        print(f"::warning::{invalid} pick(s) had TP/SL inverted vs the actual fill "
              f"(gap between signal and entry) -- NOT recorded as outcomes")
    print(f"still open {still_open}  no data {no_data}  invalid levels {invalid}")
    st = compute_status()
    STATUS.write_text(json.dumps(st, indent=1))
    print(json.dumps(st, indent=1))
    return 0


def selftest() -> int:
    """Prove the pessimistic tie-break and the no-mutation guarantee."""
    print("=" * 78)
    print("SELFTEST -- pessimistic tie-break, no-mutation, forward clock")
    print("=" * 78)
    import pandas as pd

    # a bar that touches BOTH levels must resolve as SL, never TP
    idx = pd.date_range("2026-01-01", periods=3, freq="h", tz="UTC")
    bars = pd.DataFrame({
        "Open": [100.0, 100.0, 100.0],
        "High": [100.0, 120.0, 100.0],     # touches TP 110 on bar 1
        "Low":  [100.0,  90.0, 100.0],     # AND SL 95 on the same bar
        "Close": [100.0, 100.0, 100.0],
    }, index=idx)
    pick = {"seq": 1, "symbol": "X", "side": "LONG", "entry_ref": 100.0,
            "tp": 110.0, "sl": 95.0, "created_at": "2026-01-01T00:00:00+00:00"}
    o = decide(pick, bars)
    print(f"  bar touches TP and SL together -> outcome={o['outcome']} "
          f"(must be SL)")
    assert o["outcome"] == "SL", "pessimistic tie-break violated"

    # a clean TP touch resolves as TP
    bars2 = bars.copy()
    bars2.loc[idx[1], "Low"] = 99.0
    o2 = decide(pick, bars2)
    print(f"  bar touches TP only            -> outcome={o2['outcome']} (must be TP)")
    assert o2["outcome"] == "TP"

    # entry must be a bar OPEN, not the signal price
    print(f"  entry price used               -> {o2['entry_px']} (must be a bar Open)")
    assert o2["entry_px"] == 100.0

    # resolutions append without touching picks
    tmp = Path(tempfile.mkdtemp())
    pf_, rf_ = tmp / "p.jsonl", tmp / "r.jsonl"
    pf_.write_text(json.dumps(dict(pick, sha256="x", prev_sha256=GENESIS)) + "\n")
    before = pf_.read_text()
    rf_.write_text("")
    append_resolutions([{"pick_seq": 1, "symbol": "X", "side": "LONG",
                         "outcome": "TP", "entry_px": 100.0, "exit_px": 110.0,
                         "exit_utc": "2026-01-01T01:00:00+00:00", "bars_held": 2,
                         "resolved_at": "2026-01-02T00:00:00+00:00",
                         "convention": "t"}], rf_)
    print(f"  pick file unchanged after resolving -> {pf_.read_text() == before}")
    assert pf_.read_text() == before, "resolver MUTATED the pick ledger"

    # chain detects an edited resolution
    recs = read_jsonl(rf_)
    recs[0]["exit_px"] = 999.0
    rf_.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in recs))
    v = verify_resolutions(rf_)
    print(f"  edited resolution detected          -> ok={v['ok']} "
          f"reason={v.get('reason')}")
    assert not v["ok"], "edited resolution NOT detected"

    # ---- symbol mapping must cover every asset class, not just BTC ----
    cases = [
        ("BTCUSDT", "BTC-USD", "CRYPTO"),
        ("BTC/USDT", "BTC-USD", "CRYPTO"),
        ("BTC-USD", "BTC-USD", "CRYPTO"),
        ("ETHUSDT", "ETH-USD", "CRYPTO"),
        ("BTCUSD", "BTC-USD", "CRYPTO"),
        ("EURUSD", "EURUSD=X", "FOREX"),
        ("EUR/USD", "EURUSD=X", "FOREX"),
        ("GBPJPY", "GBPJPY=X", "FOREX"),
        ("XAUUSD", "GC=F", "COMMODITY"),
        ("WTIUSD", "CL=F", "COMMODITY"),
        ("SPY", "SPY", "EQUITY"),
        ("AAPL", "AAPL", "EQUITY"),
        ("TLT", "TLT", "BOND"),
        ("IEF", "IEF", "BOND"),
        ("BRK.B", "BRK.B", "EQUITY"),
        ("^GSPC", "^GSPC", "INDEX"),
        ("CL=F", "CL=F", "FUTURE"),
        # a 6-letter equity ticker must NOT become an FX pair
        ("ALPHAB", "ALPHAB", "EQUITY"),
    ]
    print("  symbol mapping:")
    bad = []
    for raw, want_sym, want_cls in cases:
        got_sym, got_cls = resolve_symbol(raw)
        ok = (got_sym == want_sym and got_cls == want_cls)
        if not ok:
            bad.append((raw, want_sym, want_cls, got_sym, got_cls))
        print(f"    {raw:<10} -> {got_sym:<10} {got_cls:<10} {'ok' if ok else 'FAIL'}")
    assert not bad, f"symbol mapping failures: {bad}"

    # ---- coarser (daily) bars: SL-first must still hold with wider ranges ----
    didx = pd.date_range("2026-01-01", periods=4, freq="D", tz="UTC")
    dbars = pd.DataFrame({
        "Open": [100.0, 100.0, 100.0, 100.0],
        "High": [100.0, 121.0, 100.0, 100.0],
        "Low":  [100.0,  89.0, 100.0, 100.0],   # daily bar spans TP 110 AND SL 95
        "Close": [100.0, 100.0, 100.0, 100.0],
    }, index=didx)
    od = decide(pick, dbars)
    print(f"  daily bar spans TP+SL         -> outcome={od['outcome']} (must be SL)")
    assert od["outcome"] == "SL", "daily-bar pessimistic tie-break violated"
    print(f"  daily bars_held is day-counted -> {od['bars_held']}")

    # ---- inverted levels vs the ACTUAL fill must be refused, not booked ----
    # LONG whose "TP" sits BELOW the entry bar's open: a gapped-down market after
    # the signal. Booking this as a TP that lost money is how a resolver lies.
    inv = dict(pick, tp=98.0, sl=105.0)     # LONG with tp < sl is caught by the ledger
    gapped = pd.DataFrame({
        "Open": [150.0, 150.0], "High": [150.0, 150.0],
        "Low": [150.0, 149.0], "Close": [150.0, 150.0],
    }, index=pd.date_range("2026-01-01", periods=2, freq="h", tz="UTC"))
    # ledger-valid LONG (tp>sl) but the fill is 150 while levels are 110/95 -> both
    # levels are BELOW the fill, so any touch is a loss disguised as a TP
    legit_but_gapped = {"seq": 9, "symbol": "X", "side": "LONG", "entry_ref": 100.0,
                        "tp": 110.0, "sl": 95.0,
                        "created_at": "2026-01-01T00:00:00+00:00"}
    oi = decide(legit_but_gapped, gapped)
    print(f"  fill gaps above both levels  -> outcome={oi['outcome']} "
          f"(must be INVALID_LEVELS)")
    assert oi["outcome"] == "INVALID_LEVELS", "inverted-levels guard failed"
    _ = inv

    print("\n  ALL RESOLVER SELFTESTS PASSED")
    return 0


def cmd_gate() -> int:
    """Hard CI gate. Exit 1 only on a condition that is genuinely actionable.

    Deliberately tolerant of the two states that mean "not yet measurable", because
    a gate that fires before there is data gets disabled within a week and then
    protects nothing:

      * n_emitted == 0            -> nothing has been emitted yet (pre-merge)
      * n_resolved < MIN_RESOLVED -> too few outcomes to judge pct_forward

    It DOES fail on:
      * pct_forward < PCT_FORWARD_MIN once n_resolved >= MIN_RESOLVED
      * a broken resolution chain (outcomes were edited)
      * a starved resolver: picks exist, none resolved, and the oldest pending pick
        is older than MAX_DAYS + grace. That is the exact no-op this whole ledger
        exists to catch -- an instrument that measures nothing looks identical to a
        measurement of nothing.
    """
    st = compute_status()
    picks = read_jsonl(PICKS)
    res = read_jsonl(RES)
    problems: list[str] = []

    if not st["resolution_chain_ok"]:
        v = verify_resolutions(RES)
        problems.append(f"resolution chain BROKEN at index {v.get('index')}: "
                        f"{v.get('reason')}")

    if st["n_emitted"] == 0:
        print("GATE: PASS (no picks emitted yet -- nothing to measure)")
        return 0

    n_res = st["n_resolved"]
    if n_res < MIN_RESOLVED:
        print(f"GATE: PASS (only {n_res} resolved; need {MIN_RESOLVED} to judge "
              f"pct_forward)")
    elif st["pct_forward"] is not None and st["pct_forward"] < PCT_FORWARD_MIN:
        problems.append(f"pct_forward {st['pct_forward']:.1f}% < {PCT_FORWARD_MIN}% "
                        f"over {n_res} resolved picks -- picks are not resolving "
                        f"after creation")

    # starved resolver: picks exist and are old, but nothing has been resolved
    done = {r["pick_seq"] for r in res}
    pending = [p for p in picks if p["seq"] not in done]
    if pending:
        oldest = min(datetime.fromisoformat(p["created_at"]) for p in pending)
        age_days = (datetime.now(timezone.utc) - oldest).days
        if age_days > MAX_DAYS + STARVE_GRACE_DAYS:
            problems.append(f"resolver starved: {len(pending)} pick(s) pending, "
                            f"oldest {age_days}d (limit {MAX_DAYS}d + "
                            f"{STARVE_GRACE_DAYS}d grace) -- no market data path "
                            f"or a broken symbol map")

    print(json.dumps(st, indent=1))
    if problems:
        for p in problems:
            print(f"::error::provenance gate: {p}")
        print(f"\nGATE: FAIL ({len(problems)} problem(s))")
        return 1
    print("\nGATE: PASS")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--resolve", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--gate", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.gate:
        return cmd_gate()
    if a.resolve:
        return cmd_resolve()
    if a.status:
        st = compute_status()
        STATUS.parent.mkdir(parents=True, exist_ok=True)
        STATUS.write_text(json.dumps(st, indent=1))
        print(json.dumps(st, indent=1))
        print(f"\nwrote {STATUS.relative_to(REPO)}")
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
