#!/usr/bin/env python3
"""forward_observations_ingest.py — fill the forward ledger from honest intrabar rows.

The contract in ``alpha_engine/forward_observations.py`` defines what a forward
observation is. This module is the missing **writer**: it reads the honest intrabar
cohort (``at_signal_outcomes`` entry-anchored first-touch, non-ambiguous) and turns
those rows into contract rows.

Why it cannot simply filter on ``strategy``
-------------------------------------------
H-119 (``crypto_rsi5070_us``) does not exist as a strategy label. Measured
2026-11-19: ``SELECT strategy ... LIKE '%rsi5070%'`` on the honest cohort returns
**zero rows**, while the tracker reports n=431 for the same condition. The cohort is
reconstructed from pre-entry features, not from the emitter's name, so this adapter
uses the project's canonical stampers (``tools/stamp_entry_conditions.py``:
``fetch_cohort`` / ``fetch_bars`` / ``features``) exactly as
``tools/crypto_rsi5070_forward_tracker.py`` does. Anything else would report a
different population than the gate it feeds.

The resolved return is authoritative; the price pair is reconciled to it
-----------------------------------------------------------------------
The cohort carries both prices and a resolved return, and they disagree on about
58% of honest rows (max observed 775pp), so the recorded ``exit_price`` is not a
reliable percentage of the entry price. Filtering on agreement was tried and is
wrong: it kept 180 of ~430 rows and moved net PF from 1.12 to 0.65 — a biased
subset, not the cohort the gate is supposed to measure.

So ``intrabar_pnl_pct`` is the authoritative outcome, and the pair is derived from it
(``exit_px = entry_px * (1 + sign * pnl/100)``) so the row reproduces the resolver's
own number under one arithmetic definition. The resolver's recorded exit and the
size of the disagreement are preserved on every row as ``resolver_exit_px`` and
``gross_mismatch_pp`` — labelled, never hidden.

Read-only: SELECTs only. Writes exactly one file (the ledger) and only with
``--apply``; the default is a dry run.

Usage::

    python3 -m alpha_engine.forward_observations_ingest            # dry run
    python3 -m alpha_engine.forward_observations_ingest --apply    # append to ledger
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:  # allow `python3 alpha_engine/forward_observations_ingest.py`
    sys.path.insert(0, str(REPO))

from alpha_engine import forward_observations as FO  # noqa: E402

RESOLVER_VERSION = "at_signal_outcomes.intrabar.v1"
DEFAULT_LIMIT = 4000
#: Cohort rows per fetch_bars call — see collect() for why this cannot be the limit.
CHUNK = 400
#: Crypto round-trip cost convention, same constant the H-119 tracker charges, so a
#: ledger-derived net PF is comparable with the tracker's number.
CRYPTO_RT_BP = 16.0
#: Non-crypto round-trip slippage, in bps, from the tribunal's per-class constants.
OTHER_BP = {"EQUITY": 8.0, "ETF": 8.0, "FOREX": 4.0, "COMMODITY": 12.0,
            "FUTURES": 12.0, "BOND": 2.0}

#: Condition -> hypothesis. Only registered hypotheses may receive forward rows.
#: A condition may match on asset class, an optional feature vector (`requires`),
#: and optionally on the emitter's `strategy` / `direction`. `requires` is empty for
#: strategy-keyed pods (the EQUITY/ETF breakout family has no F3/F5 entry condition).
CONDITIONS = {
    "H-119": {
        "name": "crypto_rsi5070_us",
        "asset_classes": {"CRYPTO"},
        "requires": {"F3": "50-70", "F5": "US"},
    },
    "H-BABY-EQUITY-VT-PATTERN-SWEEP-001": {
        "name": "equity_breakout_family",
        "asset_classes": {"EQUITY", "ETF"},
        "strategies": {
            "donchian-stock-breakout", "rs-breakout-scout",
            "vol-contraction-scout", "adx-trend-scout",
        },
        "directions": {"LONG"},
        "requires": {},
    },
}


# ------------------------------------------------------------------ pure helpers
def side_of(row: dict) -> str | None:
    """LONG/SHORT, or None when the direction is not compassable."""
    d = str(row.get("direction") or "").strip().upper()
    if d in ("LONG", "BUY", "BULL"):
        return "LONG"
    if d in ("SHORT", "SELL", "BEAR"):
        return "SHORT"
    return None


def gross_pct(entry_px: float, exit_px: float, side: str) -> float:
    sign = 1.0 if side == "LONG" else -1.0
    return sign * (exit_px - entry_px) / entry_px * 100.0


def slippage_bps(asset_class: str) -> float:
    return CRYPTO_RT_BP if asset_class.upper() == "CRYPTO" else OTHER_BP.get(
        asset_class.upper(), 8.0)


def row_id(hypothesis_id: str, symbol: str, side: str, opened_at: str) -> str:
    """Deterministic id, so re-running ingestion is idempotent rather than duplicative."""
    basis = f"{hypothesis_id}|{symbol.upper()}|{side}|{opened_at}"
    return "fwd_" + hashlib.sha256(basis.encode("utf-8")).hexdigest()[:20]


def _pairs(series: Iterable[Any]) -> list[tuple[int, float]]:
    """Normalise a bar series to sorted (ts_ms, close) without assuming the shape."""
    out: list[tuple[int, float]] = []
    for bar in series or []:
        ts = close = None
        if isinstance(bar, dict):
            ts = bar.get("ts") or bar.get("timestamp") or bar.get("open_time")
            close = bar.get("close")
        elif isinstance(bar, (list, tuple)) and len(bar) >= 2:
            ts, close = bar[0], bar[1]
        try:
            out.append((int(ts), float(close)))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            continue
    return sorted(out)


def close_at(series: list[tuple[int, float]], ts_ms: int,
             tol_ms: int = 6 * 3600_000) -> float | None:
    """Close of the first bar at or after ``ts`` (a fill happens after the signal)."""
    if not series:
        return None
    i = bisect.bisect_left([k for k, _ in series], ts_ms)
    if i >= len(series):
        return None
    k, v = series[i]
    return v if k - ts_ms <= tol_ms else None


def benchmark_leg(series: Iterable[Any], opened_ms: int | None,
                  closed_ms: int | None, side: str) -> float | None:
    """Direction-adjusted buy-and-hold over the same window, as a fraction.

    None when either end has no bar: a missing benchmark stays missing, because the
    promotion rule tests *coverage* of this field.
    """
    if opened_ms is None or closed_ms is None:
        return None
    bars = _pairs(series)
    p0 = close_at(bars, opened_ms)
    p1 = close_at(bars, closed_ms)
    if not p0 or not p1:
        return None
    move = p1 / p0 - 1.0
    return move if side == "LONG" else -move


def _ms(ts: Any) -> int | None:
    """Epoch ms for a DB datetime or an ISO string.

    The cohort query returns ``datetime`` objects, so a string-only parser silently
    returned ``None`` for every row: each bar window collapsed to ``(0, 0)`` at the
    epoch and ``fetch_bars`` correctly returned nothing (measured 2026-11-19: a
    3,756-row cohort stamped 0 rows with every class reporting ``no_bars``).
    """
    if isinstance(ts, datetime):
        dt = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    parsed = FO._parse(ts)  # same ISO-8601 tolerance as the ledger's validator
    return int(parsed.timestamp() * 1000) if parsed else None


def _iso(ts: Any) -> str:
    """Normalise a DB datetime (or string) to the ledger's ISO-8601 form."""
    if isinstance(ts, datetime):
        return (ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)).isoformat()
    return str(ts or "")


def classify(feats: dict | None, asset_class: str, strategy: str | None = None,
             direction: str | None = None) -> str | None:
    """Which registered condition (if any) this row satisfies.

    Matches on asset class, then an optional feature vector, and — for
    strategy-keyed pods — on the emitter's strategy and direction.
    """
    if not feats:
        return None
    name = str(strategy or "").strip().casefold()
    d = str(direction or "").strip().upper()
    for hid, cond in CONDITIONS.items():
        if asset_class.upper() not in cond["asset_classes"]:
            continue
        if cond.get("strategies") and name not in cond["strategies"]:
            continue
        if cond.get("directions") and d not in cond["directions"]:
            continue
        if all(str(feats.get(k)) == v for k, v in cond.get("requires", {}).items()):
            return hid
    return None


def row_from_cohort(p: dict, feats: dict | None, bars_for_symbol: Any,
                    hypothesis_id: str, now: datetime | None = None
                    ) -> tuple[dict | None, str | None]:
    """Build one contract row, or return (None, reason-it-is-not-evidence)."""
    now = now or datetime.now(timezone.utc)
    side = side_of(p)
    if side is None:
        return None, "uncompassable_direction"
    entry = FO._num(p.get("entry_price"))
    resolved_exit = FO._num(p.get("exit_price"))
    pnl = FO._num(p.get("intrabar_pnl_pct"))
    if not entry or entry <= 0 or pnl is None:
        return None, "missing_price_or_outcome"
    # The resolved return wins. The recorded exit price disagrees with it on ~58% of
    # honest rows, so deriving the pair from the outcome is the only way to keep one
    # return definition AND the full cohort (see module docstring).
    sign = 1.0 if side == "LONG" else -1.0
    exit_px = entry * (1.0 + sign * pnl / 100.0)
    mismatch_pp = (abs(gross_pct(entry, resolved_exit, side) - pnl)
                   if resolved_exit is not None else None)

    symbol = str(p.get("symbol") or "").strip().upper()
    opened = _iso(p.get("opened_at"))
    closed = _iso(p.get("intrabar_resolved_at") or p.get("closed_at"))
    if not symbol or not opened or not closed:
        return None, "missing_identity"
    asset_class = str(p.get("asset_class") or "").strip().upper() or "UNKNOWN"

    row = {
        "id": row_id(hypothesis_id, symbol, side, opened),
        "hypothesis_id": hypothesis_id,
        "opened_at": opened,
        "closed_at": closed,
        "symbol": symbol,
        "asset_class": asset_class,
        "side": side,
        "entry_px": float(entry),
        "exit_px": float(exit_px),
        "qty": 1.0,
        "fees": 0.0,
        "funding": 0.0,
        "slippage_bps": slippage_bps(asset_class),
        "resolver_version": RESOLVER_VERSION,
        # Only intrabar-resolved, non-ambiguous rows reach here (the cohort query
        # already excludes the rest), so this is a fact, not an assumption.
        "intrabar_first_touch": True,
        "benchmark_leg_ret": benchmark_leg(bars_for_symbol, _ms(opened), _ms(closed), side),
        # The stampers returned a complete pre-entry feature vector for this row,
        # which is the only regime statement this cohort supports.
        "regime_ok": True,
        "created_at": now.isoformat(),
        # Audit trail for the derivation above. Not contract fields; they exist so
        # nobody has to trust the reconciliation without seeing what it replaced.
        "resolver_exit_px": None if resolved_exit is None else float(resolved_exit),
        "gross_mismatch_pp": None if mismatch_pp is None else round(mismatch_pp, 4),
    }
    return row, None


def build_rows(entries: Iterable[tuple[dict, dict | None, Any]], now: datetime | None = None
               ) -> tuple[list[dict], list[dict], dict[str, int]]:
    """Turn (cohort_row, features, bars) triples into ledger rows + rejection counts."""
    rows: list[dict] = []
    rejects: list[dict] = []
    counts: dict[str, int] = {}
    for p, feats, bars in entries:
        asset_class = str(p.get("asset_class") or "").strip().upper() or "UNKNOWN"
        hid = classify(feats, asset_class, strategy=p.get("strategy"),
                       direction=p.get("direction"))
        if hid is None:
            counts["not_in_any_condition"] = counts.get("not_in_any_condition", 0) + 1
            continue
        row, reason = row_from_cohort(p, feats, bars, hid, now=now)
        if row is None:
            codes = dict(counts)
            codes["rejected_" + str(reason)] = codes.get("rejected_" + str(reason), 0) + 1
            counts = codes
            rejects.append({"id": p.get("id"), "hypothesis_id": hid, "reason": reason})
            continue
        rows.append(row)
    return rows, rejects, counts


# ------------------------------------------------------------------ DB ingestion
def _hydrate(ids: list[int], chunk: int = 500) -> dict[int, dict]:
    """Read the two ledger fields ``fetch_cohort`` does not select.

    The stampers' cohort query returns id/symbol/direction/asset_class/strategy/
    source_system/opened_at/entry_price/status/pnl — no ``exit_price`` and no
    ``intrabar_resolved_at``. Rather than duplicating its dedupe and ordering (which
    would silently change the population the gate is measured on), the missing
    columns are read here by primary key. Read-only.
    """
    import pymysql
    from tools.db_env import get_stocks_creds

    keep = ("host", "user", "password", "database", "port", "connect_timeout")
    conn = pymysql.connect(cursorclass=pymysql.cursors.DictCursor,
                           **{k: v for k, v in get_stocks_creds().items() if k in keep})
    out: dict[int, dict] = {}
    try:
        cur = conn.cursor()
        for start in range(0, len(ids), chunk):
            part = ids[start:start + chunk]
            cur.execute(
                "SELECT id, exit_price, intrabar_resolved_at FROM at_signal_outcomes "
                "WHERE id IN (" + ",".join(["%s"] * len(part)) + ")", part)
            for r in cur.fetchall():
                out[int(r["id"])] = {"exit_price": r["exit_price"],
                                     "intrabar_resolved_at": r["intrabar_resolved_at"]}
    finally:
        conn.close()
    return out


def collect(limit: int = DEFAULT_LIMIT) -> tuple[list[dict], list[dict], dict[str, int], dict]:
    """Read the honest cohort (read-only) and build rows. No writes.

    ``fetch_bars`` is called per chunk of 400 cohort rows, not once for the whole
    cohort: at ~800 distinct symbols in one call it returns no bars at all (measured
    2026-11-19 — 3,756-row cohort gave 2,845 ``CRYPTO:no_bars`` skips and 0 matches,
    while the same code on 400 rows matched 51). Bars are cached and merged across
    chunks, so a symbol spanning two chunks is fetched once.
    """
    import tools.stamp_entry_conditions as S  # the canonical stampers

    cohort = S.fetch_cohort(limit)
    extra = _hydrate([int(p["id"]) for p in cohort if p.get("id") is not None])
    for p in cohort:
        p.update(extra.get(int(p["id"]), {}))
    skips: dict[str, int] = {}
    entries: list[tuple[dict, dict | None, Any]] = []
    cache: dict[str, list[tuple[int, float]]] = {}   # flat: symbol -> bars
    chunk_marks: list[int] = []

    for p in cohort:
        cls = (p.get("asset_class") or "UNKNOWN").upper()
        is_crypto = cls in ("CRYPTO", "MEMECOIN")
        p["_table"] = "crypto_ohlcv" if is_crypto else "stock_ohlcv"
        cands = [p["symbol"]]
        if is_crypto:
            alt = p["symbol"].upper().replace("-", "").replace("/", "")
            if alt.endswith("USD") and not alt.endswith("USDT"):
                alt += "T"
            if alt != p["symbol"]:
                cands.append(alt)
        p["_barsyms"] = cands

    for start in range(0, len(cohort), CHUNK):
        chunk = cohort[start:start + CHUNK]
        window: dict[str, dict[str, tuple[int, int]]] = {"crypto_ohlcv": {}, "stock_ohlcv": {}}
        for p in chunk:
            entry_ms = _ms(p.get("opened_at")) or 0
            # The window must reach the resolution time, not just entry: the
            # benchmark leg is measured over entry..exit. Stopping at entry is why
            # benchmark coverage came out at 64%.
            exit_ms = _ms(p.get("intrabar_resolved_at")) or entry_ms
            for sym in p["_barsyms"]:
                lo, hi = window[p["_table"]].get(sym, (entry_ms, exit_ms))
                window[p["_table"]][sym] = (min(lo, entry_ms), max(hi, exit_ms))
        # fetch_bars returns a FLAT {symbol: [(ts_ms, close), ...]} mapping.
        fetched = S.fetch_bars(window) or {}
        for sym, series in fetched.items():
            cache[sym] = sorted(set(cache.get(sym, [])) | set(series or []))
        marks = 0
        for p in chunk:
            series = next((cache[s] for s in p["_barsyms"] if cache.get(s)), [])
            feats = S.features(p, series, skips)
            marks += 1 if feats else 0
            entries.append((p, feats, series))
        chunk_marks.append(marks)

    rows, rejects, counts = build_rows(entries)
    meta = {"cohort_n": len(cohort), "chunk_size": CHUNK,
            "stamped_rows_by_chunk": chunk_marks, "stamper_skips": skips}
    return rows, rejects, counts, meta


def ingest(apply: bool = False, limit: int = DEFAULT_LIMIT,
           ledger: str | Path = FO.DEFAULT_LEDGER) -> dict:
    rows, rejects, counts, meta = collect(limit)
    report: dict[str, Any] = {
        "schema": "forward_observations.ingest.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "read_only_source": "at_signal_outcomes intrabar first-touch (non-ambiguous)",
        "ledger": str(ledger),
        "applied": False,
        "n_admissible": len(rows),
        "n_by_hypothesis": {},
        **meta,
        "skipped": counts,
        "rejected_sample": rejects[:10],
        "n_rejected": len(rejects),
    }
    for row in rows:
        hid = row["hypothesis_id"]
        report["n_by_hypothesis"][hid] = report["n_by_hypothesis"].get(hid, 0) + 1
    if apply:
        written = FO.append(rows, ledger)
        report["applied"] = True
        report["write"] = {"added": written["added"], "duplicates": written["duplicates"],
                           "rejected": len(written["rejected"])}
        report["ledger_verify"] = FO.verify(ledger)
        for hid in sorted(report["n_by_hypothesis"]):
            subset = [r for r in FO.load(ledger)[0]
                      if str(r.get("hypothesis_id") or "").upper() == hid]
            report.setdefault("promotion", {})[hid] = FO.promotion(subset)
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Ingest honest intrabar rows into the forward-observations ledger")
    ap.add_argument("--apply", action="store_true",
                    help="append admissible rows (default: dry run, writes nothing)")
    ap.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    ap.add_argument("--ledger", default=str(FO.DEFAULT_LEDGER))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    try:
        report = ingest(apply=args.apply, limit=args.limit, ledger=args.ledger)
    except Exception as exc:  # no DB / no creds -> honest failure, never a fake ledger
        print(f"ERROR: ingestion unavailable ({type(exc).__name__}: {exc})", file=sys.stderr)
        return 3
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(f"cohort {report['cohort_n']} -> admissible {report['n_admissible']} "
              f"({report['n_by_hypothesis']}), rejected {report['n_rejected']}, "
              f"skipped {report['skipped']}")
        if report["applied"]:
            v = report["ledger_verify"]
            print(f"wrote {report['write']}, ledger now {v['n_rows']} rows ok={v['ok']}")
            for hid, promo in (report.get("promotion") or {}).items():
                print(f"  {hid}: eligible={promo['eligible']} n={promo['n_forward']}"
                      + ("" if promo["eligible"] else f" — {'; '.join(promo.get('reasons') or [])}"))
        else:
            print("dry run — nothing written (pass --apply to append)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
