#!/usr/bin/env python3
"""hyrotrader_closed_picks_emitter.py — emit pf_registry-shaped closed picks
from the real-fills-only hyrotrader journal so the canonical PF/WR registry
sees hyrotrader outcomes alongside every other source.

Background
----------
`audit_dashboard/data/hyrotrader_journal.json` is the source of truth for
hyrotrader's REAL paper fills (logged via `tools/hyrotrader_log_trade.py`,
never auto-invented). Picks live in `hyrotrader_picks.json` /
`hyrotrader_enhanced_picks.json` (carry asset_class + strategy fields).

Until now the canonical pf_registry had no entry for hyrotrader, so even when
real fills got logged they were invisible to /audit's PF/WR view. This
emitter is the bridge: it reads the journal, joins to the picks file on
pick_id, and writes `audit_dashboard/data/hyrotrader_closed_picks.json` with
the same row shape as every other `closed_picks.json` source pf_registry
ingests.

It is READ-ONLY w.r.t. the journal (the file the operator hand-curates) and
idempotent. Empty journal → empty closed_picks file (still written so
pf_registry's source_files manifest can record presence).

Usage
-----
    python3 tools/hyrotrader_closed_picks_emitter.py
    python3 tools/hyrotrader_closed_picks_emitter.py --check       # exit 1 if output would change
    python3 tools/hyrotrader_closed_picks_emitter.py --self-test   # smoke
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
JOURNAL_PATH = REPO_ROOT / "audit_dashboard" / "data" / "hyrotrader_journal.json"
PICKS_PATH = REPO_ROOT / "audit_dashboard" / "data" / "hyrotrader_picks.json"
ENHANCED_PICKS_PATH = REPO_ROOT / "audit_dashboard" / "data" / "hyrotrader_enhanced_picks.json"
OUTPUT_PATH = REPO_ROOT / "audit_dashboard" / "data" / "hyrotrader_closed_picks.json"

SOURCE_SYSTEM = "hyrotrader"


def _load_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _pick_index(picks_doc: dict | list | None) -> dict:
    """Return {pick_id: pick_dict} from either `picks_doc['picks']` or list."""
    if picks_doc is None:
        return {}
    picks = picks_doc.get("picks") if isinstance(picks_doc, dict) else picks_doc
    if not isinstance(picks, list):
        return {}
    out: dict = {}
    for p in picks:
        if not isinstance(p, dict):
            continue
        pid = p.get("id") or p.get("pick_id")
        if pid is not None:
            out[str(pid)] = p
    return out


def emit(journal: dict | list | None, picks: dict | list | None,
         enhanced: dict | list | None = None) -> list[dict]:
    """Build pf_registry-shaped closed-pick rows from the journal trades."""
    trades = []
    if isinstance(journal, dict):
        trades = journal.get("trades") or []
    elif isinstance(journal, list):
        trades = journal
    if not isinstance(trades, list):
        return []

    pick_lookup = _pick_index(enhanced) or {}
    pick_lookup.update(_pick_index(picks))  # picks_doc wins on conflict

    out: list[dict] = []
    for t in trades:
        if not isinstance(t, dict):
            continue
        # Only emit closed trades — the journal also tracks open positions.
        closed_at = t.get("closed_at") or t.get("exit_time")
        pnl_pct = t.get("pnl_pct")
        if not closed_at or pnl_pct is None:
            continue

        pid = t.get("pick_id")
        pick = pick_lookup.get(str(pid)) if pid is not None else None
        strategy = (
            (pick.get("strategy") if pick else None)
            or t.get("strategy")
            or "hyrotrader_manual"
        )
        asset_class = (
            (pick.get("asset_class") if pick else None)
            or t.get("asset_class")
            or "UNKNOWN"
        )
        try:
            pnl_pct_num = float(pnl_pct)
        except (TypeError, ValueError):
            continue

        out.append({
            "strategy": str(strategy),
            "asset_class": str(asset_class),
            "source_system": SOURCE_SYSTEM,
            "symbol": str(t.get("symbol") or (pick.get("symbol_hint") if pick else "")),
            "direction": str(t.get("direction") or (pick.get("direction") if pick else "")),
            "entry_date": t.get("entry_time") or (pick.get("opened_at") if pick else None),
            "entry_price": t.get("entry_price") or (pick.get("entry_price") if pick else None),
            "exit_price": t.get("exit_price"),
            "exit_reason": t.get("exit_reason"),
            "closed_at": closed_at,
            "status": "WIN" if pnl_pct_num > 0 else "LOSS",
            "pnl_pct": pnl_pct_num,
            "pick_id": pid,
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="Exit 1 if the output would change (for CI drift detection).")
    ap.add_argument("--self-test", action="store_true",
                    help="Smoke test with synthetic data; do not touch real files.")
    args = ap.parse_args()

    if args.self_test:
        return _self_test()

    journal = _load_json(JOURNAL_PATH)
    picks = _load_json(PICKS_PATH)
    enhanced = _load_json(ENHANCED_PICKS_PATH)
    rows = emit(journal, picks, enhanced)
    out = {
        "schema_version": "1.0.0",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source": str(JOURNAL_PATH.relative_to(REPO_ROOT)),
        "source_system": SOURCE_SYSTEM,
        "note": (
            "Closed picks materialized from hyrotrader_journal.json. Real fills "
            "only — auto-invented PnL is forbidden by the journal contract."
        ),
        "n_closed": len(rows),
        "picks": rows,
    }
    new_text = json.dumps(out, indent=2, sort_keys=False)

    if args.check:
        existing = OUTPUT_PATH.read_text(encoding="utf-8") if OUTPUT_PATH.exists() else ""
        # Skip the generated_utc field for the drift check.
        try:
            existing_obj = json.loads(existing) if existing else {}
            existing_obj.pop("generated_utc", None)
            cur_obj = json.loads(new_text)
            cur_obj.pop("generated_utc", None)
            if existing_obj == cur_obj:
                print(f"[hyrotrader_emitter] no drift ({len(rows)} closed picks)")
                return 0
            print("[hyrotrader_emitter] DRIFT — re-run without --check to write",
                  file=sys.stderr)
            return 1
        except json.JSONDecodeError:
            print("[hyrotrader_emitter] DRIFT — existing file invalid JSON",
                  file=sys.stderr)
            return 1

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(new_text, encoding="utf-8")
    print(f"[hyrotrader_emitter] wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} "
          f"({len(rows)} closed picks)")
    return 0


def _self_test() -> int:
    journal = {
        "trades": [
            {  # closed winner
                "pick_id": "H1",
                "symbol": "BTCUSDT",
                "direction": "LONG",
                "entry_time": "2026-05-20T10:00:00Z",
                "entry_price": 95000.0,
                "exit_price": 100000.0,
                "closed_at": "2026-05-22T10:00:00Z",
                "pnl_pct": 0.0526,
                "exit_reason": "tp",
            },
            {  # closed loser
                "pick_id": "H2",
                "symbol": "ETHUSDT",
                "direction": "LONG",
                "entry_time": "2026-05-21T10:00:00Z",
                "entry_price": 3500.0,
                "exit_price": 3400.0,
                "closed_at": "2026-05-22T10:00:00Z",
                "pnl_pct": -0.0286,
                "exit_reason": "sl",
            },
            {  # open — should be skipped
                "pick_id": "H3",
                "symbol": "SOLUSDT",
                "direction": "LONG",
                "entry_time": "2026-05-21T10:00:00Z",
                "entry_price": 180.0,
                "closed_at": None,
                "pnl_pct": None,
            },
        ],
    }
    picks = {"picks": [
        {"id": "H1", "strategy": "cci_divergence", "asset_class": "CRYPTO", "symbol_hint": "BTCUSDT", "direction": "LONG"},
        {"id": "H2", "strategy": "adx_vol_breakout", "asset_class": "CRYPTO", "symbol_hint": "ETHUSDT", "direction": "LONG"},
    ]}
    rows = emit(journal, picks)
    assert len(rows) == 2, f"expected 2 closed rows, got {len(rows)}"
    assert {r["status"] for r in rows} == {"WIN", "LOSS"}
    assert rows[0]["strategy"] == "cci_divergence"
    assert rows[0]["source_system"] == SOURCE_SYSTEM
    print("[hyrotrader_emitter] self-test OK (2 rows, WIN+LOSS, joined on pick_id)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
