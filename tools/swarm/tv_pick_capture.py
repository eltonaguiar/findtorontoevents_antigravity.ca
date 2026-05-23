#!/usr/bin/env python3
"""TV Pick Capture — auto-ingest TradingView paper fills into swarm_picks.json.

Per Agent#3 infra finding (2026-05-12): "GHA race + hand-curation are
fragile. Build tv_pick_capture.py next session = 10x leverage."

Hand-curated theswarm rounds had 0 auto-resolution because picks were
typed into TV separately from JSON entries. This module bridges the gap:

  source                          consumer
  ------                          --------
  TradingView paper account  -->  this module reads order history
       MCP / CSV export      -->  --> normalize to swarm_pick_schema
                             -->  --> append_picks() to swarm_picks.json
                             -->  outcome_resolver_swarm.py (existing)
                                  --> nightly via swarm-pick-review.yml

Three input modes (choose at CLI):

  --tv-mcp        Use TradingView MCP (mcp__tradingview-desktop) to read
                  the active account's trades. Requires the desktop app +
                  the MCP integration to be authorized.
  --csv PATH      Read a CSV export from TV (the "Account Statement"
                  export). One row per trade. Maps tv columns -> schema.
  --json PATH     Read a JSON file with array of TV fills (for testing
                  or hand-curated inputs).

NFA: doesn't place trades. Only ingests fills that already exist on TV.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from tools.swarm.swarm_pick_schema import (  # noqa: E402
    append_picks,
    SchemaError,
)


PICKS_PATH = ROOT / "audit_dashboard" / "data" / "swarm_picks.json"
CANDIDATES_PATH = (
    ROOT / "audit_dashboard" / "data" / "ai_leaderboard" / "swarm_pick_candidates.json"
)


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mint_pick_id() -> str:
    return f"tvcap-{uuid.uuid4().hex[:12]}"


def _normalize_direction(side: str) -> str:
    s = str(side or "").strip().upper()
    if s in ("BUY", "LONG", "L", "BID"):
        return "LONG"
    if s in ("SELL", "SHORT", "S", "ASK"):
        return "SHORT"
    return s or "LONG"


def _infer_asset_class(symbol: str) -> str:
    s = str(symbol or "").upper()
    if any(p in s for p in ("USDT", "USDC", "BTC", "ETH", "BINANCE", "COINBASE")):
        return "CRYPTO"
    if s.startswith("FX:") or any(s.endswith(x) for x in ("USD=X", "EUR=X", "JPY=X")):
        return "FOREX"
    if s.startswith("NYSE:") or s.startswith("NASDAQ:"):
        return "EQUITY"
    if s.endswith("=F") or "CT" in s:
        return "FUTURES"
    if s.startswith("ETF:") or any(t in s for t in ("SPY", "QQQ", "IWM", "XL")):
        return "ETF"
    return "UNKNOWN"


def _bare_symbol(sym) -> str:
    """Strip an exchange prefix (BINANCE:BTCUSDT -> BTCUSDT), upper-case."""
    return str(sym or "").split(":")[-1].strip().upper()


def load_candidate_attribution(path: Path) -> dict:
    """Build a {bare_symbol: models_consulted} map from a swarm-candidates file.

    M-051 (`tools/ai_attribution/multi_model_pick_gen.py`) writes
    swarm_pick_candidates.json — each candidate carries the multi-model
    `models_consulted[]`. When a TV fill is captured this map lets the
    fill inherit the candidate's per-engine attribution by symbol, so the
    AI Leaderboard ranks the engines that voted the placed trade.
    """
    out: dict = {}
    if not path or not path.exists():
        return out
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return out
    cands = data.get("candidates", data) if isinstance(data, dict) else data
    if not isinstance(cands, list):
        return out
    for c in cands:
        if not isinstance(c, dict):
            continue
        mc = c.get("models_consulted")
        sym = _bare_symbol(c.get("symbol"))
        if sym and mc:
            out[sym] = mc          # last candidate per symbol wins
    return out


def normalize_tv_fill(
    raw: dict,
    *,
    source_tag: str = "tv_capture",
    candidate_map: dict | None = None,
) -> dict:
    """Map a raw TV-fill dict to the swarm_pick schema.

    If *candidate_map* is given and the fill carries no `models_consulted`
    of its own, the matching candidate's attribution is inherited by
    bare-symbol match (M-051 multi-model wire-up).
    """
    symbol = raw.get("symbol") or raw.get("ticker") or raw.get("instrument")
    direction = _normalize_direction(raw.get("side") or raw.get("direction"))
    entry = raw.get("entry_price") or raw.get("price") or raw.get("avg_price")
    qty = raw.get("qty") or raw.get("quantity") or raw.get("size") or 0
    qty_unit = raw.get("qty_unit") or raw.get("unit") or "pct_balance"
    tp = raw.get("tp") or raw.get("take_profit") or raw.get("target")
    sl = raw.get("sl") or raw.get("stop_loss") or raw.get("stop")
    timeframe = raw.get("timeframe") or raw.get("tf") or "1h"
    account = raw.get("account") or "tv_paper"
    asset_class = raw.get("asset_class") or _infer_asset_class(symbol)
    created_at = raw.get("created_at") or raw.get("timestamp") or _utc_iso()
    models_consulted = raw.get("models_consulted") or []
    if not models_consulted and candidate_map:
        models_consulted = candidate_map.get(_bare_symbol(symbol), [])
    return {
        "pick_id": raw.get("pick_id") or _mint_pick_id(),
        "created_at": created_at,
        "session_id": raw.get("session_id") or f"tv-capture-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        "account": account,
        "symbol": symbol,
        "direction": direction,
        "entry": float(entry) if entry is not None else None,
        "tp": float(tp) if tp is not None else None,
        "sl": float(sl) if sl is not None else None,
        "qty": float(qty) if qty is not None else None,
        "qty_unit": qty_unit,
        "timeframe": timeframe,
        "asset_class": asset_class,
        "consensus_tier": raw.get("consensus_tier") or "tv_fill",
        "models_consulted": models_consulted,
        "_source": source_tag,
    }


def read_csv(path: Path) -> list[dict]:
    out: list[dict] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            out.append({k.strip().lower(): (v.strip() if isinstance(v, str) else v)
                        for k, v in row.items()})
    return out


def read_json(path: Path) -> list[dict]:
    d = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(d, dict):
        return d.get("fills") or d.get("trades") or d.get("picks") or []
    return d or []


def read_tv_mcp() -> list[dict]:
    """Pull current trades via TradingView MCP. Not implementable here
    (requires MCP-side tool call). Stub raises NotImplementedError so the
    caller surfaces it; v2 will wire to mcp__tradingview-desktop tools.
    """
    raise NotImplementedError(
        "TV MCP read is v2 — use --csv or --json for now. "
        "MCP wiring requires the assistant context that has the "
        "mcp__tradingview-desktop tools available; a separate orchestrator "
        "script should call mcp__tradingview-desktop__data_get_trades "
        "and pipe the JSON output to this module via --json."
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--tv-mcp", action="store_true",
                     help="Read fills from TradingView MCP (v2)")
    src.add_argument("--csv", type=Path,
                     help="CSV file path with TV account statement")
    src.add_argument("--json", type=Path,
                     help="JSON file path with array of fills")
    p.add_argument("--source-tag", default="tv_capture",
                   help="Marker stored as pick._source (default: tv_capture)")
    p.add_argument("--picks-path", type=Path, default=PICKS_PATH)
    p.add_argument("--candidates", type=Path, default=CANDIDATES_PATH,
                   help="swarm_pick_candidates.json — fills inherit a matching "
                        "candidate's models_consulted by bare-symbol (M-051). "
                        "Missing file is non-fatal.")
    p.add_argument("--dry-run", action="store_true",
                   help="Normalize + validate but do not write")
    args = p.parse_args()

    candidate_map = load_candidate_attribution(args.candidates)
    if candidate_map:
        print(f"# candidate attribution loaded — {len(candidate_map)} symbols",
              file=sys.stderr)

    if args.tv_mcp:
        try:
            raw = read_tv_mcp()
        except NotImplementedError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(2)
    elif args.csv:
        if not args.csv.exists():
            print(f"ERROR: csv {args.csv} not found", file=sys.stderr)
            sys.exit(1)
        raw = read_csv(args.csv)
    else:
        if not args.json.exists():
            print(f"ERROR: json {args.json} not found", file=sys.stderr)
            sys.exit(1)
        raw = read_json(args.json)

    print(f"# tv_pick_capture — read {len(raw)} raw fills", file=sys.stderr)

    normalized: list[dict] = []
    errors: list[dict] = []
    for i, r in enumerate(raw):
        try:
            normalized.append(normalize_tv_fill(
                r, source_tag=args.source_tag, candidate_map=candidate_map))
        except Exception as exc:
            errors.append({"index": i, "error": str(exc)[:160], "row_keys": list(r.keys())[:8]})

    if errors:
        print(f"# normalize errors: {len(errors)} (continuing with the {len(normalized)} valid rows)",
              file=sys.stderr)
        for e in errors[:5]:
            print(f"#   row {e['index']}: {e['error']}", file=sys.stderr)

    if args.dry_run:
        print(json.dumps({
            "n_raw": len(raw),
            "n_normalized": len(normalized),
            "n_errors": len(errors),
            "sample": normalized[:3],
        }, indent=2, default=str))
        return

    try:
        result = append_picks(args.picks_path, normalized)
    except SchemaError as exc:
        print(f"ERROR: schema validation failed: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"# appended {result.get('added', 0)} new picks; "
          f"skipped {result.get('skipped', 0)} duplicates; "
          f"store total now {result.get('total', 0)}", file=sys.stderr)


if __name__ == "__main__":
    main()
