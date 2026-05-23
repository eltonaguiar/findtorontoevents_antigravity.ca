#!/usr/bin/env python3
"""Fork 1 — feature-backfill for the closed-pick ledger.

RESEARCH / SIDECAR ONLY. Touches no production scoring or pick-generation path.
Reads `alpha_engine/data/closed_picks.json`, derives per-pick features, and
writes a NEW sidecar `alpha_engine/data/closed_picks_enriched.json`. The source
ledger is never modified.

Why this exists
---------------
`reports/EDGE_VERDICT_2026-05-18.md` ran every pipeline score through
`tools/edge_stability_harness.py` and admitted NONE. Two candidate score
families could not even be tested because the ledger lacks their inputs:

  (a) regime-conditioned scores — `regime` is present on 3 / 8421 picks.
  (b) qlib Alpha158 factors (`pv_corr30`, `vol_ratio`, `realized_vol30`,
      shipped in PR #1178) — not in the ledger at all.

This script backfills both so the harness can honestly verdict them. If a
candidate still cannot be measured (sparse data, no OHLCV coverage), that is
reported as-is — an honest "not testable" closes the in-house sweep just as
validly as a kill, per EDGE_VERDICT's own framing.

What is backfilled, per pick
----------------------------
  * qlib factors  — `vol_ratio`, `pv_corr30`, `realized_vol30` computed from
    daily OHLCV ending the bar BEFORE entry_date (no look-ahead). Uses the
    exact functions from `alpha_engine/technical_features.py` (PR #1178).
  * `regime_at_entry` — recomputed from the same OHLCV: a simple, transparent
    3-state classifier (BULL / BEAR / CHOPPY) from SMA20 slope + realized vol.
    This is a *recompute*, NOT a stored regime timeseries — the repo has no
    usable regime history (`regime_performance_history.json` does not exist;
    the only regime signal in the ledger is `extra.fast_regime` on 3 picks).
  * `regime_score` — a numeric proxy (+1 BULL / 0 CHOPPY / -1 BEAR) so the
    harness, which needs a numeric field, can bucket it.

OHLCV is fetched via yfinance with a per-symbol on-disk cache
(`tools/_backfill_cache/`). No network call is repeated for a symbol once
cached. Symbols that cannot be resolved or fetched are recorded in the
output's `_backfill_meta` and left without enriched features.

    python tools/backfill_pick_features.py            # full run
    python tools/backfill_pick_features.py --limit 50 # smoke test
    python tools/backfill_pick_features.py --offline  # cache-only, no network
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLOSED = ROOT / "alpha_engine" / "data" / "closed_picks.json"
OUT = ROOT / "alpha_engine" / "data" / "closed_picks_enriched.json"
CACHE_DIR = Path(__file__).resolve().parent / "_backfill_cache"

# qlib factor functions — imported from the PR #1178 production module so the
# backfilled values are identical to what the live feature path would produce.
sys.path.insert(0, str(ROOT))
try:
    from alpha_engine.technical_features import (  # noqa: E402
        compute_volume_ratio,
        compute_price_volume_corr,
        compute_realized_vol,
    )
    _HAVE_QLIB_FN = True
except ImportError:
    # Branch may predate PR #1178; provide local stdlib copies (same math).
    import math

    def compute_volume_ratio(volumes, short=5, long=30):  # type: ignore
        if len(volumes) < long:
            return 0.0
        sa = sum(volumes[-short:]) / short
        la = sum(volumes[-long:]) / long
        if la <= 0:
            return 0.0
        r = sa / la
        return max(-1.0, min(1.0, math.log(r) if r > 0 else 0.0))

    def compute_price_volume_corr(closes, volumes, period=30):  # type: ignore
        if len(closes) < period or len(volumes) < period:
            return 0.0
        c, v = closes[-period:], volumes[-period:]
        n = period
        mc, mv = sum(c) / n, sum(v) / n
        cov = sum((c[i] - mc) * (v[i] - mv) for i in range(n))
        vc = sum((x - mc) ** 2 for x in c)
        vv = sum((x - mv) ** 2 for x in v)
        d = math.sqrt(vc * vv)
        return 0.0 if d == 0 else max(-1.0, min(1.0, cov / d))

    def compute_realized_vol(closes, period=30):  # type: ignore
        if len(closes) < period + 1:
            return 0.0
        rets = []
        for i in range(len(closes) - period, len(closes)):
            if closes[i - 1] > 0:
                rets.append(closes[i] / closes[i - 1] - 1.0)
        if len(rets) < 2:
            return 0.0
        m = sum(rets) / len(rets)
        var = sum((r - m) ** 2 for r in rets) / (len(rets) - 1)
        return max(0.0, min(1.0, math.sqrt(var) * 10.0))

    _HAVE_QLIB_FN = False


# --------------------------------------------------------------------------
# symbol resolution: ledger symbol -> yfinance ticker
# --------------------------------------------------------------------------
def to_yf_ticker(symbol: str) -> str | None:
    """Map a ledger symbol to a yfinance ticker, or None if unresolvable."""
    if not symbol:
        return None
    s = symbol.strip()
    # FOREX / futures already yfinance-native ("USDJPY=X", "CT=F").
    if s.endswith("=X") or s.endswith("=F"):
        return s
    # Crypto USDT pairs -> "<base>-USD".
    for quote in ("USDT", "USD", "USDC", "BUSD"):
        if s.endswith(quote) and len(s) > len(quote):
            base = s[: -len(quote)]
            # yfinance crypto uses MATIC->MATIC-USD etc.
            return f"{base}-USD"
    # Bare equity ticker — but not a bare quote currency.
    if s.isalpha() and 1 <= len(s) <= 6 and s.upper() not in (
            "USDT", "USD", "USDC", "BUSD"):
        return s
    return None


def _entry_dt(pick: dict):
    """Best-effort entry date for a pick (date object) or None."""
    for k in ("entry_date", "timestamp", "resolved_at", "exit_date"):
        v = pick.get(k)
        if v:
            try:
                return date.fromisoformat(str(v)[:10])
            except ValueError:
                continue
    return None


# --------------------------------------------------------------------------
# OHLCV fetch with on-disk cache
# --------------------------------------------------------------------------
def fetch_ohlcv(ticker: str, offline: bool) -> list[dict] | None:
    """Return list of {date, high, low, close, volume} daily bars, cached.

    Fetches a wide window (full ledger span + buffer) once per ticker.
    """
    CACHE_DIR.mkdir(exist_ok=True)
    cf = CACHE_DIR / f"{ticker.replace('=', '_').replace('/', '_')}.json"
    if cf.exists():
        try:
            return json.loads(cf.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass
    if offline:
        return None
    try:
        import yfinance as yf  # noqa: PLC0415
    except ImportError:
        return None
    try:
        df = yf.download(
            ticker,
            start="2025-11-01",
            end="2026-05-20",
            interval="1d",
            progress=False,
            auto_adjust=False,
            threads=False,
        )
    except Exception:  # noqa: BLE001
        return None
    if df is None or len(df) == 0:
        cf.write_text("[]", encoding="utf-8")  # negative-cache empties
        return []
    bars = []
    for idx, row in df.iterrows():
        try:
            # yfinance may return MultiIndex columns when one ticker is passed.
            def _g(col):
                v = row[col]
                return float(v.iloc[0]) if hasattr(v, "iloc") else float(v)
            bars.append({
                "date": str(idx)[:10],
                "high": _g("High"),
                "low": _g("Low"),
                "close": _g("Close"),
                "volume": _g("Volume"),
            })
        except Exception:  # noqa: BLE001
            continue
    cf.write_text(json.dumps(bars), encoding="utf-8")
    return bars


def _bars_before(bars: list[dict], entry: date, lookback: int = 60) -> list[dict]:
    """Bars strictly before `entry`, most-recent `lookback` of them."""
    eligible = [b for b in bars if b["date"] < entry.isoformat()]
    return eligible[-lookback:]


# --------------------------------------------------------------------------
# regime recompute (transparent 3-state, no stored timeseries available)
# --------------------------------------------------------------------------
def classify_regime(closes: list[float]) -> tuple[str, int]:
    """3-state regime from SMA20 slope + realized vol. Returns (label, score).

    BULL  (+1): SMA20 rising and price above it.
    BEAR  (-1): SMA20 falling and price below it.
    CHOPPY ( 0): everything else (incl. high-vol whipsaw, flat trend).
    """
    if len(closes) < 25:
        return "UNKNOWN", 0
    sma_now = sum(closes[-20:]) / 20.0
    sma_prev = sum(closes[-25:-5]) / 20.0
    px = closes[-1]
    rising = sma_now > sma_prev * 1.005
    falling = sma_now < sma_prev * 0.995
    if rising and px > sma_now:
        return "BULL", 1
    if falling and px < sma_now:
        return "BEAR", -1
    return "CHOPPY", 0


# --------------------------------------------------------------------------
# main backfill
# --------------------------------------------------------------------------
def backfill(limit: int | None, offline: bool) -> dict:
    raw = json.loads(CLOSED.read_text(encoding="utf-8"))
    picks = raw if isinstance(raw, list) else raw.get("picks", raw.get("closed", []))
    picks = [p for p in picks if isinstance(p, dict)]
    if limit:
        picks = picks[:limit]

    # Pre-resolve unique tickers to fetch each once.
    sym_to_yf: dict[str, str | None] = {}
    for p in picks:
        s = p.get("symbol")
        if s and s not in sym_to_yf:
            sym_to_yf[s] = to_yf_ticker(s)

    ohlcv_cache: dict[str, list[dict] | None] = {}
    resolved = sum(1 for v in sym_to_yf.values() if v)
    print(f"[backfill] {len(picks)} picks, {len(sym_to_yf)} distinct symbols, "
          f"{resolved} resolvable to yfinance tickers", file=sys.stderr)

    fetched = 0
    for yf_ticker in sorted({v for v in sym_to_yf.values() if v}):
        bars = fetch_ohlcv(yf_ticker, offline)
        ohlcv_cache[yf_ticker] = bars
        if bars:
            fetched += 1
        if not offline:
            time.sleep(0.15)  # gentle on yfinance
    print(f"[backfill] OHLCV available for {fetched} tickers", file=sys.stderr)

    stats = {
        "picks_total": len(picks),
        "qlib_backfilled": 0,
        "regime_backfilled": 0,
        "no_symbol": 0,
        "symbol_unresolved": 0,
        "no_ohlcv": 0,
        "insufficient_bars": 0,
        "no_entry_date": 0,
    }
    unresolved_syms: set[str] = set()
    no_ohlcv_syms: set[str] = set()

    enriched = []
    for p in picks:
        out = dict(p)  # shallow copy; never mutate source
        symbol = p.get("symbol")
        entry = _entry_dt(p)
        out["_backfill_status"] = None

        if not symbol:
            stats["no_symbol"] += 1
            out["_backfill_status"] = "no_symbol"
            enriched.append(out)
            continue
        yf_t = sym_to_yf.get(symbol)
        if not yf_t:
            stats["symbol_unresolved"] += 1
            unresolved_syms.add(symbol)
            out["_backfill_status"] = "symbol_unresolved"
            enriched.append(out)
            continue
        if entry is None:
            stats["no_entry_date"] += 1
            out["_backfill_status"] = "no_entry_date"
            enriched.append(out)
            continue
        bars = ohlcv_cache.get(yf_t)
        if not bars:
            stats["no_ohlcv"] += 1
            no_ohlcv_syms.add(symbol)
            out["_backfill_status"] = "no_ohlcv"
            enriched.append(out)
            continue

        window = _bars_before(bars, entry, lookback=60)
        if len(window) < 31:
            stats["insufficient_bars"] += 1
            out["_backfill_status"] = f"insufficient_bars({len(window)})"
            enriched.append(out)
            continue

        closes = [b["close"] for b in window]
        vols = [b["volume"] for b in window]

        # qlib factors (no look-ahead — window is strictly pre-entry)
        out["qlib_vol_ratio"] = round(compute_volume_ratio(vols), 6)
        out["qlib_pv_corr30"] = round(compute_price_volume_corr(closes, vols), 6)
        out["qlib_realized_vol30"] = round(compute_realized_vol(closes), 6)
        stats["qlib_backfilled"] += 1

        # regime recompute
        label, score = classify_regime(closes)
        out["regime_at_entry"] = label
        out["regime_score"] = score
        if label != "UNKNOWN":
            stats["regime_backfilled"] += 1

        out["_backfill_status"] = "ok"
        enriched.append(out)

    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(CLOSED.relative_to(ROOT)),
        "script": "tools/backfill_pick_features.py",
        "research_only": True,
        "production_wiring": False,
        "qlib_fn_imported_from_pr1178": _HAVE_QLIB_FN,
        "regime_method": "recomputed SMA20-slope + realized-vol 3-state "
                         "(no stored regime timeseries exists in repo)",
        "ohlcv_source": "yfinance daily, pre-entry window, on-disk cached",
        "stats": stats,
        "unresolved_symbols": sorted(unresolved_syms),
        "no_ohlcv_symbols": sorted(no_ohlcv_syms),
        "coverage_pct": {
            "qlib": round(100.0 * stats["qlib_backfilled"] / max(1, stats["picks_total"]), 1),
            "regime": round(100.0 * stats["regime_backfilled"] / max(1, stats["picks_total"]), 1),
        },
    }
    payload = {"_backfill_meta": meta, "picks": enriched}
    OUT.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"[backfill] wrote {OUT.relative_to(ROOT)}", file=sys.stderr)
    print(json.dumps(meta, indent=2), file=sys.stderr)
    return meta


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=None,
                    help="only process first N picks (smoke test)")
    ap.add_argument("--offline", action="store_true",
                    help="cache-only, no network fetches")
    args = ap.parse_args()
    backfill(args.limit, args.offline)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
