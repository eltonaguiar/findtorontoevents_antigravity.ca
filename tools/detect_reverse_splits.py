"""
detect_reverse_splits.py — Reverse-split detector for MEME/PENNY/CHEAP_STOCKS
================================================================================

P2-11 follow-on.  This is the v2 of the reverse-split subsystem.  v1 lives at
`audit_trail/reverse_split_symbols.py` (a hand-curated static registry of
known split-affected tickers).  v2 augments v1 with a *discovery* layer:

    1. Read the live DB for symbols whose `entry_price` is implausibly small
       relative to a `current_price` snapshot (drift-based detection,
       re-uses the per-class thresholds from `tools/ai_tournament/price_tracker.py`).
    2. Cross-check candidate symbols against a yfinance split history with
       a 7-day local file cache (data/splits/<symbol>.json).
    3. Return a unified `SplitEvent` list usable by `flag_picks()` and
       `export_json()`.

This module is READ-ONLY against the production DB.  The only file I/O is
its own cache at `data/splits/`.  It does NOT mutate the live resolver
(`audit_trail/universal_pick_resolver.py:1242-1271` is the call site we
expect to wire into in a follow-up PR — see `## Wiring Plan` in
`reports/p2-11_reverse_split_detector_2026-06-13.md`).

CLI:
    python3 tools/detect_reverse_splits.py \\
        --class-filter MEME --since 2026-03-01 \\
        --out audit_dashboard/data/reverse_split_events.json

Idempotent: re-running the CLI with the same flags and cache produces an
identical JSON output (modulo `generated_at_utc`).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

# Make repo root importable when run as a script (per CLAUDE.md "relative
# imports vs script invocation" feedback)
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Soft imports — yfinance / pymysql are optional so the tool is still
# importable in environments without them (e.g. CI smoke test).
try:
    import yfinance as yf  # type: ignore
    _HAS_YFINANCE = True
except ImportError:
    yf = None
    _HAS_YFINANCE = False

try:
    import pymysql  # type: ignore
    _HAS_PYMYSQL = True
except ImportError:
    pymysql = None
    _HAS_PYMYSQL = False

# Re-use v1 helpers if available (do not duplicate the parse_ratio logic).
try:
    from audit_trail.reverse_split_symbols import (
        REVERSE_SPLIT_SYMBOLS,
        is_reverse_split_affected,
        should_adjust_for_split,
    )
    _HAS_V1 = True
except Exception:  # pragma: no cover — keep tool self-contained if v1 is missing
    REVERSE_SPLIT_SYMBOLS = {}
    is_reverse_split_affected = None  # type: ignore
    should_adjust_for_split = None  # type: ignore
    _HAS_V1 = False


LOG = logging.getLogger("detect_reverse_splits")

# Per-class drift thresholds (%).  Mirrors
# tools/ai_tournament/price_tracker.py:_DRIFT_BY_CLASS for the relevant
# classes — the same numbers used by the live MISPRICED_ENTRY guard.
# Anything below 50 is a likely normal drift; above is suspicious.
DRIFT_THRESHOLDS_BY_CLASS: dict[str, float] = {
    "PENNY_STOCK":  25.0,
    "PENNY":        25.0,
    "MEMECOIN":     50.0,  # crypto meme coins drift a lot
    "MEME":         50.0,
    "CHEAP_STOCKS": 25.0,
    "EQUITY":       10.0,
    "DEFAULT":      25.0,
}

# Source: enum values in trading_picks_v2 / at_signal_outcomes
ASSET_CLASS_ALIASES: dict[str, str] = {
    "MEME":   "MEMECOIN",
    "PENNY":  "PENNY_STOCK",
    "CHEAP_STOCKS": "CHEAP_STOCKS",
}

# yfinance cache TTL (days) — splits don't change retroactively, so a
# 7-day cache is safe.
YFINANCE_CACHE_TTL_DAYS = 7
SPLIT_CACHE_DIR = REPO_ROOT / "data" / "splits"

# Default DB creds (matches the convention in memory / CLAUDE.md):
#   50webs pw = `<name>1234560`
# Default DB creds (matches the convention in memory / CLAUDE.md):
#   50webs pw = `<name>1234560` — but never inlined as a literal.
#   Resolved at call time via tools.db_env.get_stocks_creds().
DB_DEFAULTS: dict[str, dict[str, str]] = {
    "stocks": {
        "host": "mysql.50webs.com",
        "user": "ejaguiar1_stocks",
        "password": "",  # resolved at runtime from env via tools.db_env
        "database": "ejaguiar1_stocks",
    },
}


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class SplitEvent:
    """A single reverse-split event, normalized for cross-source comparison.

    `ratio` is the price-multiplier factor (e.g. 10.0 for a 1-for-10 reverse
    split, 12.5 for an 8-for-100).  yfinance returns the inverse (0.1, 0.08);
    we convert to the multiplier on ingest.
    """
    symbol: str
    split_date: str  # ISO YYYY-MM-DD
    ratio: float     # price multiplier (1/ratio_yf for reverse splits)
    type: str        # 'reverse' or 'forward'
    source: str      # 'yfinance' | 'registry' | 'drift' | 'cache'
    confidence: float = 1.0  # 1.0 for confirmed, lower for drift-only
    notes: str = ""

    def to_json(self) -> dict[str, Any]:
        d = asdict(self)
        # Round to avoid float precision issues in JSON output
        d["ratio"] = round(float(d["ratio"]), 6)
        d["confidence"] = round(float(d["confidence"]), 3)
        return d


@dataclass
class PickForFlag:
    """Minimal pick shape the flagger needs.  We don't require a typed
    dataclass so callers can pass dicts from anywhere; this is for docs."""
    symbol: str
    entry_price: float | None
    signal_timestamp: str
    asset_class: str


# ---------------------------------------------------------------------------
# ReverseSplitDetector
# ---------------------------------------------------------------------------

class ReverseSplitDetector:
    """Discover reverse-split events and flag picks at risk.

    Usage:
        det = ReverseSplitDetector()
        events = det.detect("LODE", since=date(2024,1,1), until=date(2026,6,13))
        for p in picks:
            det.flag_picks([p])   # mutates each pick dict
        det.export_json("audit_dashboard/data/reverse_split_events.json")
    """

    def __init__(
        self,
        cache_dir: Path | str = SPLIT_CACHE_DIR,
        db_dsn: dict[str, str] | None = None,
        ttl_days: int = YFINANCE_CACHE_TTL_DAYS,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(days=ttl_days)
        # Resolve DSN: prefer caller-supplied, then DB_DEFAULTS, then the
        # canonical tools.db_env resolver. Never inline a literal password.
        if db_dsn is not None:
            self.db_dsn = db_dsn
        else:
            dsn = dict(DB_DEFAULTS["stocks"])
            if not dsn.get("password"):
                try:
                    from tools.db_env import get_stocks_creds  # type: ignore
                    creds = get_stocks_creds(raise_on_missing=False)
                    dsn.update({k: str(creds.get(k, "")) for k in ("host", "user", "password", "database", "port")})
                except Exception:
                    pass
            self.db_dsn = dsn
        LOG.debug("ReverseSplitDetector init: cache=%s ttl=%s yf=%s db=%s",
                  self.cache_dir, self.ttl, _HAS_YFINANCE, bool(self.db_dsn))

    # ------------------------------------------------------------------
    # yfinance split discovery (with file cache)
    # ------------------------------------------------------------------

    def _cache_path(self, symbol: str) -> Path:
        safe = re.sub(r"[^A-Z0-9_-]+", "_", symbol.upper())
        return self.cache_dir / f"{safe}.json"

    def _cache_fresh(self, symbol: str) -> bool:
        p = self._cache_path(symbol)
        if not p.exists():
            return False
        age = datetime.now(timezone.utc) - datetime.fromtimestamp(
            p.stat().st_mtime, tz=timezone.utc)
        return age < self.ttl

    def _read_cache(self, symbol: str) -> list[dict[str, Any]] | None:
        try:
            with open(self._cache_path(symbol), "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            LOG.debug("cache read %s: %s", symbol, e)
            return None

    def _write_cache(self, symbol: str, rows: list[dict[str, Any]]) -> None:
        try:
            with open(self._cache_path(symbol), "w") as f:
                json.dump(rows, f, indent=2, sort_keys=True)
        except OSError as e:
            LOG.warning("cache write %s: %s", symbol, e)

    def _yfinance_splits(self, symbol: str) -> list[dict[str, Any]]:
        """Query yfinance for splits.  Cached per-symbol."""
        if self._cache_fresh(symbol):
            cached = self._read_cache(symbol)
            if cached is not None:
                LOG.debug("cache HIT for %s (%d rows)", symbol, len(cached))
                return cached

        if not _HAS_YFINANCE:
            LOG.warning("yfinance not installed; cannot refresh %s", symbol)
            return self._read_cache(symbol) or []

        LOG.debug("yfinance fetching splits for %s", symbol)
        try:
            t = yf.Ticker(symbol)
            s = t.splits
        except Exception as e:
            LOG.warning("yfinance error on %s: %s", symbol, type(e).__name__)
            return self._read_cache(symbol) or []

        if s is None or len(s) == 0:
            # yfinance returns an empty Series for symbols with no splits
            rows: list[dict[str, Any]] = []
        else:
            rows = []
            for ts, ratio_yf in s.items():
                # yfinance returns the *divisor* ratio (e.g. 0.1 for 1:10 reverse).
                # We want the price-multiplier factor.
                try:
                    r = float(ratio_yf)
                except (TypeError, ValueError):
                    continue
                if r == 0:
                    continue
                price_multiplier = 1.0 / r if r != 0 else 0.0
                # Date comes back as a pandas Timestamp; coerce to ISO
                try:
                    iso_date = pd_ts_to_iso(ts)  # type: ignore[name-defined]
                except Exception:
                    iso_date = str(ts)[:10]
                if not iso_date:
                    continue
                rows.append({
                    "date": iso_date,
                    "ratio_yf": r,
                    "price_multiplier": price_multiplier,
                })

        self._write_cache(symbol, rows)
        # Sleep a hair to be nice to yfinance rate limits
        time.sleep(0.05)
        return rows

    def detect(
        self,
        symbol: str,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[SplitEvent]:
        """Return all reverse-split events for `symbol` in `[since, until]`.

        Merges three sources, in priority order:
        1. Hand-curated v1 registry (audit_trail.reverse_split_symbols)
        2. yfinance history (with disk cache)
        3. (Drift-based discovery is in `flag_picks()`, not here — it
           requires a pick context to score confidence.)
        """
        sym = str(symbol or "").strip().upper()
        if not sym:
            return []

        since = since or datetime(1900, 1, 1, tzinfo=timezone.utc)
        until = until or datetime.now(timezone.utc)
        out: list[SplitEvent] = []

        # 1. v1 registry
        if _HAS_V1 and sym in REVERSE_SPLIT_SYMBOLS:
            for ratio_str, date_str in REVERSE_SPLIT_SYMBOLS[sym]:
                factor = _parse_ratio(ratio_str)
                if factor is None:
                    continue
                evt_date = _parse_iso(date_str)
                if not evt_date:
                    continue
                if not (since <= evt_date <= until):
                    continue
                out.append(SplitEvent(
                    symbol=sym,
                    split_date=evt_date.date().isoformat(),
                    ratio=factor,
                    type="reverse" if factor > 1.0 else "forward",
                    source="registry",
                    confidence=1.0,
                    notes=ratio_str,
                ))

        # 2. yfinance
        yf_rows = self._yfinance_splits(sym)
        for r in yf_rows:
            try:
                evt_date = datetime.fromisoformat(str(r["date"]))
            except ValueError:
                continue
            if evt_date.tzinfo is None:
                evt_date = evt_date.replace(tzinfo=timezone.utc)
            if not (since <= evt_date <= until):
                continue
            mult = float(r.get("price_multiplier", 0.0))
            if mult == 0:
                continue
            # Don't double-add if registry already covered this date
            if any(e.split_date == evt_date.date().isoformat() and abs(e.ratio - mult) < 1e-6
                   for e in out):
                continue
            out.append(SplitEvent(
                symbol=sym,
                split_date=evt_date.date().isoformat(),
                ratio=mult,
                type="reverse" if mult > 1.0 else "forward",
                source="yfinance" if r.get("ratio_yf") is not None else "cache",
                confidence=1.0,
                notes=f"yf={r.get('ratio_yf')}",
            ))

        out.sort(key=lambda e: e.split_date)
        return out

    # ------------------------------------------------------------------
    # Drift-based candidate discovery (DB query)
    # ------------------------------------------------------------------

    def discover_drift_candidates(
        self,
        class_filter: str,
        since: datetime,
        until: datetime | None = None,
        max_rows: int = 5000,
    ) -> list[dict[str, Any]]:
        """Find picks whose `entry_price` is implausibly small relative to
        a current `lm_daily_price_history` snapshot.

        Returns a list of dicts with at minimum: symbol, asset_class, n_picks,
        max_drift_pct.  These are *candidates* — confirm via `detect()`.
        """
        if not _HAS_PYMYSQL:
            LOG.warning("pymysql not installed; cannot query DB")
            return []

        class_db = ASSET_CLASS_ALIASES.get(class_filter.upper(), class_filter.upper())
        threshold = DRIFT_THRESHOLDS_BY_CLASS.get(
            class_db, DRIFT_THRESHOLDS_BY_CLASS["DEFAULT"])

        sql = """
        SELECT t.symbol,
               t.asset_class,
               COUNT(*) n_picks,
               MIN(t.entry_price) min_entry,
               MAX(t.pnl_pct) max_pnl
          FROM trading_picks_v2 t
         WHERE t.asset_class = %s
           AND t.closed_at >= %s
           AND t.entry_price IS NOT NULL
           AND t.entry_price > 0
         GROUP BY t.symbol, t.asset_class
         ORDER BY n_picks DESC
         LIMIT %s
        """
        params: list[Any] = [class_db, since, max_rows]

        try:
            conn = pymysql.connect(**self.db_dsn)
            try:
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                    rows = cur.fetchall()
            finally:
                conn.close()
        except Exception as e:
            LOG.warning("DB query failed: %s", e)
            return []

        # Cross-reference with yfinance current price (best-effort, cached)
        candidates: list[dict[str, Any]] = []
        for sym, ac, n_picks, min_entry, max_pnl in rows:
            sym_u = str(sym or "").strip().upper()
            if not sym_u:
                continue
            try:
                current_price = self._yfinance_current_price(sym_u)
            except Exception:
                current_price = None
            drift = None
            if current_price and min_entry and min_entry > 0:
                drift = abs(current_price - float(min_entry)) / float(min_entry) * 100.0
            candidates.append({
                "symbol": sym_u,
                "asset_class": ac,
                "n_picks": int(n_picks),
                "min_entry": float(min_entry) if min_entry else None,
                "current_price": current_price,
                "max_drift_pct": drift,
                "above_threshold": drift is not None and drift > threshold,
            })
        return candidates

    def _yfinance_current_price(self, symbol: str) -> float | None:
        if not _HAS_YFINANCE:
            return None
        try:
            t = yf.Ticker(symbol)
            hist = t.history(period="5d")
            if hist is None or hist.empty:
                return None
            return float(hist["Close"].iloc[-1])
        except Exception as e:
            LOG.debug("yfinance current price %s: %s", symbol, type(e).__name__)
            return None

    # ------------------------------------------------------------------
    # Flag picks
    # ------------------------------------------------------------------

    def flag_picks(self, picks: list[dict]) -> list[dict]:
        """Annotate each pick in-place with `reverse_split_warning` and
        `reverse_split_event` keys.  Returns the same list for chaining.
        """
        # Cache split events by symbol to avoid redundant yfinance hits
        symbol_cache: dict[str, list[SplitEvent]] = {}

        for pick in picks:
            sym = str(pick.get("symbol") or "").strip().upper()
            ts_str = pick.get("signal_timestamp") or pick.get("timestamp") or ""
            if not sym or not ts_str:
                pick.setdefault("reverse_split_warning", False)
                pick.setdefault("reverse_split_event", None)
                continue

            if sym not in symbol_cache:
                symbol_cache[sym] = self.detect(sym)
            events = symbol_cache[sym]
            if not events:
                pick["reverse_split_warning"] = False
                pick["reverse_split_event"] = None
                continue

            # Pick a representative event.  For MEME/PENNY/CHEAP_STOCKS the
            # relevant question is "did a reverse split happen in the
            # lookback window of this pick's evaluation?" — i.e. between
            # the pick's signal_timestamp and the present.  Reverse splits
            # inflate historical WR for any pre-split pick indefinitely
            # (cumulative 1:9600 for FFIE in 12 months is still inflating
            # 2023 picks), so we do NOT bound by a 365-day window — the
            # v1.should_adjust_for_split() function decides applicability.
            pick_dt = _parse_iso(str(ts_str)[:19])
            matched: SplitEvent | None = None
            now_dt = datetime.now(timezone.utc)
            for evt in events:
                evt_dt = _parse_iso(evt.split_date)
                if not evt_dt:
                    continue
                # Match if the split occurred on/after the pick's signal
                # timestamp (any time horizon — the cumulative factor
                # applies even for old picks).
                if pick_dt and evt_dt >= pick_dt:
                    if matched is None or evt_dt < _parse_iso(matched.split_date):
                        matched = evt
                elif pick_dt is None:
                    # Couldn't parse pick date — match the most recent split
                    matched = matched or evt
            pick["reverse_split_warning"] = matched is not None
            pick["reverse_split_event"] = matched.to_json() if matched else None

        return picks

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_json(self, path: Path | str) -> Path:
        """Export a snapshot of split events for the *registered* symbols
        (no live DB scan here — the CLI does that and passes picks in).

        This method is here for completeness when called as a library with
        explicit pick lists; the CLI also writes the same JSON directly.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        snapshot = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": "registry+yfinance",
            "events": [],
        }
        # Pull events for all known registry symbols + any discovered drift
        # candidates.  For the library caller this is just registry coverage.
        for sym in sorted(REVERSE_SPLIT_SYMBOLS.keys()):
            for evt in self.detect(sym):
                snapshot["events"].append(evt.to_json())
        with open(path, "w") as f:
            json.dump(snapshot, f, indent=2, sort_keys=True)
        return path


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_ratio(s: str) -> float | None:
    """Best-effort ratio parser.  Mirrors v1.parse_split_ratio semantics
    but returns the *price-multiplier* factor (the inverse of yfinance's
    divisor)."""
    s = str(s or "").strip()
    m = re.match(r"1-for-(\d+)", s)
    if m:
        return float(m.group(1))
    m = re.match(r"(\d+)-for-(\d+)", s)
    if m:
        n, m_val = float(m.group(1)), float(m.group(2))
        if n > 0:
            return m_val / n
    return None


def _parse_iso(s: str) -> datetime | None:
    s = str(s or "").strip()
    if not s:
        return None
    # Trim trailing Z for fromisoformat
    s = s.rstrip("Z")
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def pd_ts_to_iso(ts: Any) -> str:
    """Convert a pandas Timestamp / datetime / string to ISO date string."""
    # Avoid importing pandas at module load time — handle common types
    if hasattr(ts, "date"):
        try:
            return ts.date().isoformat()  # type: ignore[union-attr]
        except Exception:
            pass
    if isinstance(ts, str):
        return ts[:10]
    return str(ts)[:10]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Detect reverse-split events affecting MEME/PENNY/CHEAP_STOCKS picks.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--class-filter", default="MEME",
                   choices=["MEME", "PENNY", "CHEAP_STOCKS", "ALL"],
                   help="Asset-class filter for drift-based candidate discovery. "
                        "DB enum mapping: MEME->MEMECOIN, PENNY->PENNY_STOCK, CHEAP_STOCKS->CHEAP_STOCKS.")
    p.add_argument("--since", default="2026-03-01",
                   help="ISO date; only events/picks on/after this date are scanned.")
    p.add_argument("--until", default=None,
                   help="ISO date; default = now.")
    p.add_argument("--symbols", nargs="*", default=None,
                   help="Override symbol list (default: registry symbols + DB top symbols).")
    p.add_argument("--out", default="audit_dashboard/data/reverse_split_events.json",
                   help="Output JSON path.")
    p.add_argument("--drift-scan", action="store_true",
                   help="Run drift-based candidate discovery (DB query).")
    p.add_argument("--dry-run", action="store_true",
                   help="Do not write the output JSON; print summary only.")
    p.add_argument("--verbose", "-v", action="store_true",
                   help="Verbose logging.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_argparser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    since = _parse_iso(args.since) or datetime(2026, 3, 1, tzinfo=timezone.utc)
    until = _parse_iso(args.until) if args.until else datetime.now(timezone.utc)

    det = ReverseSplitDetector()

    # 1. Collect candidate symbols.
    symbols: set[str] = set()
    if args.symbols:
        symbols.update(s.upper() for s in args.symbols if s)
    else:
        symbols.update(REVERSE_SPLIT_SYMBOLS.keys())
        # Cheap_stocks universe is the seed file at data/penny_universe_seed.json
        seed = REPO_ROOT / "data" / "penny_universe_seed.json"
        if seed.exists():
            try:
                with open(seed) as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    for v in data.values():
                        if isinstance(v, str):
                            symbols.add(v.upper())
                        elif isinstance(v, list):
                            symbols.update(str(s).upper() for s in v)
                elif isinstance(data, list):
                    symbols.update(str(s).upper() for s in data)
            except Exception as e:
                LOG.warning("penny_universe_seed.json: %s", e)

    # 2. Optional drift-based discovery
    drift_candidates: list[dict] = []
    if args.drift_scan:
        LOG.info("Drift scan for class=%s since=%s", args.class_filter, since.date())
        drift_candidates = det.discover_drift_candidates(
            class_filter=args.class_filter,
            since=since, until=until,
        )
        for c in drift_candidates:
            if c.get("symbol"):
                symbols.add(c["symbol"])

    # 3. Collect events for all symbols
    all_events: list[dict] = []
    for sym in sorted(symbols):
        for evt in det.detect(sym, since=since, until=until):
            all_events.append(evt.to_json())

    snapshot = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "registry+yfinance",
        "filter": {
            "class_filter": args.class_filter,
            "since": since.date().isoformat(),
            "until": until.date().isoformat(),
        },
        "symbols_scanned": sorted(symbols),
        "drift_candidates": drift_candidates,
        "events": all_events,
    }

    out = Path(args.out)
    if not args.dry_run:
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as f:
            json.dump(snapshot, f, indent=2, sort_keys=True)
        LOG.info("wrote %s (%d events across %d symbols)",
                 out, len(all_events), len(symbols))
    else:
        LOG.info("[dry-run] would write %d events to %s", len(all_events), out)

    # 4. Print summary
    print(f"Symbols scanned: {len(symbols)}")
    print(f"Split events found: {len(all_events)}")
    print(f"Drift candidates: {len([c for c in drift_candidates if c.get('above_threshold')])}")
    if all_events:
        print("\nEvents:")
        for e in all_events:
            print(f"  {e['symbol']:6} {e['split_date']} x{e['ratio']:>7.2f}  {e['type']:7}  src={e['source']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
