#!/usr/bin/env python3
"""Build audit_dashboard/data/operator_review_today.json from a hand-edited seed.

Why this exists
---------------
The /audit dashboard says exactly one thing about manual candidates today:
"0/6 money-ready; assistant verdict NOT_READY; the production lane won't size them." Yet
the operator still needs a way to see TODAY'S top candidates that the production
gates (M-036, M-036b, BLOCKED_ASSET_CLASSES, etc.) are filtering out, so a
human can decide whether to override or swing-and-miss.

This script takes a hand-edited seed (tools/operator_review_seed.json) listing
2-5 picks the operator wants surfaced tomorrow, enriches each pick with
live-data lookups (cohort n / WR / PF / restriction marks), and writes
audit_dashboard/data/operator_review_today.json. The /audit dashboard reads
that file via dashboard_enhancements.js::renderOperatorReviewToday() which is
intentional about the FAIL-CLOSED contract (renders NOTHING if the JSON is
missing or operator_review_only !== true).

This script NEVER mutates active_picks / trading_picks / any sizing surface.
The seeded picks remain visibility-only.

Usage
-----
    python3 tools/build_operator_review_today.py --apply     # write JSON
    python3 tools/build_operator_review_today.py --stdout   # print, do not write

Safety
------
- Reads tools/operator_review_seed.json (committed-to-git file).
- Writes audit_dashboard/data/operator_review_today.json.
- Schema is locked: any pick missing symbol/asset_class/direction FAILS the run.
- "LIVE" lookup data is informational only — do not edit picks[] in the seed
  based on lookup data; the operator's decision is the human authority.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from typing import Any

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

SEED_PATH = os.path.join(REPO, "tools", "operator_review_seed.json")
OUT_PATH = os.path.join(REPO, "audit_dashboard", "data", "operator_review_today.json")
ECF_PATH = os.path.join(REPO, "audit_dashboard", "data", "entry_conditions_forward.json")
MV_PATH = os.path.join(REPO, "audit_dashboard", "data", "money_ready_verdict.json")
ISF_PATH = os.path.join(REPO, "audit_dashboard", "data", "intrabar_sym_dir_fwd.json")

# Gates (all carry the same intent: this pick would be filtered out by the
# production lane). The names match audit_trail/quality_gates.py:7317-7349.
KNOWN_RESTRICTIONS = {
    # ("asset_class", "direction") -> default restriction text
    ("CRYPTO", "LONG"):    "M-036b BLOCKED — CRYPTO sized LONG hard-rejected at quality_gates.py:7317-7349 (CRYPTO_BLOCKED_DIRECTIONS_SIZED includes LONG; CRYPTO_SIZED_LONG_BLOCK=1 active).",
    ("CRYPTO", "BUY"):     "M-036 BLOCKED — CRYPTO direction=BUY anti-predictive (PF=0.38).",
    ("FOREX", "LONG"):     "BLOCKED_ASSET_CLASSES — FOREX class fully blocked except cta_cross_asset_tsmom SHORT (see reports/for-ex_rescue_consolidated_2026_05_03.md).",
    ("COMMODITY", "LONG"): "BLOCKED_ASSET_CLASSES — COMMODITY + FUTURES + BOND currently frozen per operator decision.",
    ("BOND", "LONG"):      "BLOCKED_ASSET_CLASSES — BOND class currently frozen.",
}


def _load(path: str) -> dict | None:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return None


def _lookup_condition_stats(ec: dict, condition_key: str) -> dict | None:
    if not ec:
        return None
    conds = ec.get("conditions", {}) or {}
    block = conds.get(condition_key)
    return block if isinstance(block, dict) else None


def _lookup_per_symbol_dir(isf: dict, sym: str, direction: str, strategy: str = "luxalgo_confluence") -> dict | None:
    if not isf:
        return None
    by_key = isf.get("by_key", {}) or {}
    key = f"{sym}|{direction.upper()}|{strategy}"
    return by_key.get(key)


def _lookup_class_verdict(mv: dict, asset_class: str) -> dict | None:
    if not mv:
        return None
    cls = (mv.get("classes", {}) or {}).get(asset_class.upper())
    return cls if isinstance(cls, dict) else None


def build_payload() -> dict[str, Any]:
    seed = _load(SEED_PATH)
    if not seed:
        # FAIL-OPEN the script (the file is optional), but mark the JSON empty.
        # The dashboard's fail-closed contract then renders NOTHING.
        return {
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "generated_by": "tools/build_operator_review_today.py (no seed file)",
            "ttl_hours": 24,
            "operator_review_only": True,
            "warning_banner": "No seed file present — operator-review panel is empty tonight.",
            "picks": [],
            "dismissed_picks_audit": "audit_dashboard/data/operator_review_dismissed.json (created by operator decisions)",
        }

    ec = _load(ECF_PATH)
    mv = _load(MV_PATH)
    isf = _load(ISF_PATH)

    picks_out = []
    now_iso = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

    for raw in seed.get("picks", []) or []:
        sym = (raw.get("symbol") or "").strip().upper()
        ac = (raw.get("asset_class") or "").strip().upper()
        d = (raw.get("direction") or "").strip().upper()
        if not sym or not ac or not d:
            raise SystemExit(f"SEED SCHEMA: pick missing symbol/asset_class/direction — {raw!r}")

        # 1. Default restriction from gate table (operator can override in seed).
        restriction = raw.get("restriction") or KNOWN_RESTRICTIONS.get((ac, d)) or (
            f"No canonical gate-known BLOCK on {ac} {d}; restriction unset — operator must decide."
        )

        # 2. Live cohort stats (luxalgo_short condition is the canonical reference).
        cond_key = raw.get("cite_condition_key") or (
            "luxalgo_short" if ac == "CRYPTO" and d == "SHORT" else None
        )
        cond_block = _lookup_condition_stats(ec, cond_key) if cond_key else None
        live_n = None
        live_wr_pct = None
        live_pf_net = None
        live_pf_gross = None
        live_verdict_note = None
        if cond_block:
            live_n = cond_block.get("n")
            live_wr_pct = cond_block.get("wr")
            live_pf_gross = cond_block.get("pf")
            live_pf_net = cond_block.get("net_pf")
            live_verdict_note = cond_block.get("verdict_note")

        # 3. Per-symbol-per-direction intrabar index lookup (sub-cohort n trace).
        sd = _lookup_per_symbol_dir(isf, sym, d, "luxalgo_confluence") if isf else None

        # 4. Class verdict anchor (so the operator sees the gate basis).
        cv = _lookup_class_verdict(mv, ac)

        picks_out.append({
            "id": raw.get("id") or f"oprt-{now_iso[:10]}-{len(picks_out)+1:03d}",
            "symbol": sym,
            "asset_class": ac,
            "direction": d,
            "stage": raw.get("stage") or "OPPORTUNITY",
            "restriction": restriction,
            "live_n": live_n,
            "live_wr_pct": live_wr_pct,
            "live_pf_gross": live_pf_gross,
            "live_pf_net": live_pf_net,
            "live_last30d_n": ((cond_block or {}).get("last30d") or {}).get("n"),
            "live_last30d_wr_pct": ((cond_block or {}).get("last30d") or {}).get("wr"),
            "live_last30d_pf_net": ((cond_block or {}).get("last30d") or {}).get("net_pf"),
            "live_verdict_note": live_verdict_note,
            "source_strategies": [
                {
                    "name": f"{cond_key} condition",
                    "strategy_id": (raw.get("source_strategies") or [{}])[0].get("strategy_id") if raw.get("source_strategies") else None,
                    "direction": d,
                    "cite": f"entry_conditions_forward.json::conditions.{cond_key}",
                    "cohort_n": live_n,
                    "net_wr_pct": live_wr_pct,
                    "net_pf": live_pf_net,
                } if cond_key else None,
                {
                    "name": f"{sym}|{d} per-symbol-per-dir intrabar index",
                    "cite": f"intrabar_sym_dir_fwd.json::by_key {sym}|{d}|luxalgo_confluence",
                    "cohort_n": (sd or {}).get("n") if sd else None,
                    "wr_pct": (sd or {}).get("wr_pct") if sd else None,
                    "pf": (sd or {}).get("pf") if sd else None,
                    "note": "sub-cohort trace; usually n<30 unless the per-(symbol,dir,strategy) cell is a top emitter.",
                } if sd else {
                    "name": f"{sym}|{d} per-symbol-per-dir intrabar index",
                    "cite": f"intrabar_sym_dir_fwd.json::by_key {sym}|{d}|luxalgo_confluence",
                    "cohort_n": None, "wr_pct": None, "pf": None,
                    "note": "no luxalgo_confluence row — pick not represented in the intrabar index; surfacing on the operator's hunt evidence only.",
                },
                {
                    "name": f"{ac} class-wide honest intrabar",
                    "cite": f"money_ready_verdict.json::classes.{ac}",
                    "cohort_n": (cv or {}).get("n_resolved") if cv else None,
                    "wr_pct": (cv or {}).get("wr_pct") if cv else None,
                    "pf": (cv or {}).get("pf") if cv else None,
                    "note": "basis of any class-wide SIZE-BLOCK; informational only.",
                },
            ],
            "expected_edge": raw.get("expected_edge") or "Operator must articulate the expected edge basis.",
            "suggested_size_pct_of_normal": raw.get("suggested_size_pct_of_normal"),
            "suggested_tp_pct": raw.get("suggested_tp_pct"),
            "suggested_sl_pct": raw.get("suggested_sl_pct"),
            "operator_decision_required": raw.get("operator_decision_required") or (
                "Operator: accept / reject / dismiss; tag entry as PAPER_PROBE if accepted."
            ),
            "added_to_review_at": raw.get("added_to_review_at") or now_iso,
        })

    return {
        "_schema_note": (
            "Generated by tools/build_operator_review_today.py from "
            "tools/operator_review_seed.json. Read-only to all sizing/sync paths "
            "— every config path that would treat this as a sizing surface must "
            "check operator_review_only=true and refuse to ingest. See "
            "updates/2026-06-22-operator-review-today-panel.md for spec."
        ),
        "generated_at": now_iso,
        "generated_by": "tools/build_operator_review_today.py",
        "ttl_hours": int(seed.get("ttl_hours") or 24),
        "operator_review_only": True,
        "warning_banner": seed.get("warning_banner") or (
            "MANUAL CANDIDATES — NOT auto-emitted tonight. Operator decides "
            "per-pick per-day. ADAUSDT LONG specifically is gated out of the "
            "production sizing lane by M-036b (CRYPTO_SIZED_LONG_BLOCK=1) — "
            "surfacing here is visibility-only; do not enable the kill-switch "
            "override without explicit confirmation."
        ),
        "console_banner_text": seed.get("console_banner_text") or "🌅 Operator Review — Manual Candidates",
        "picks": picks_out,
        "asof_references": {
            "money_ready_verdict_CRYPTO_verdict": (cv or {}).get("verdict") if (cv := _lookup_class_verdict(mv, "CRYPTO")) else None,
            "money_ready_verdict_CRYPTO_n_resolved": (cv or {}).get("n_resolved") if (cv := _lookup_class_verdict(mv, "CRYPTO")) else None,
            "money_ready_verdict_CRYPTO_intrabar_wr_pct": ((cv or {}).get("n_resolved") and round((cv.get("wr", 0)) * 100, 2)) if (cv := _lookup_class_verdict(mv, "CRYPTO")) else None,
            "money_ready_verdict_CRYPTO_sizing_source": (cv or {}).get("sizing_source") if (cv := _lookup_class_verdict(mv, "CRYPTO")) else None,
            "entry_conditions_forward_luxalgo_short_n": ((((ec or {}).get("conditions") or {}).get("luxalgo_short") or {}).get("n")),
            "entry_conditions_forward_luxalgo_short_wr_pct": ((((ec or {}).get("conditions") or {}).get("luxalgo_short") or {}).get("wr")),
            "entry_conditions_forward_luxalgo_short_pf_net": ((((ec or {}).get("conditions") or {}).get("luxalgo_short") or {}).get("net_pf")),
            "entry_conditions_forward_luxalgo_short_verdict_note": ((((ec or {}).get("conditions") or {}).get("luxalgo_short") or {}).get("verdict_note")),
        },
        "dismissed_picks_audit": "audit_dashboard/data/operator_review_dismissed.json (created by operator decisions; this panel must render against BOTH current picks[] AND dismissed[] for the past 7d for the operator's mental model)",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="Write operator_review_today.json to disk.")
    ap.add_argument("--stdout", action="store_true", help="Print the JSON, do not write.")
    ap.add_argument("--strict", action="store_true", help="Refuse to run if the seed has zero picks (default: OK with empty).")
    args = ap.parse_args()

    payload = build_payload()
    if args.strict and not payload["picks"]:
        raise SystemExit("STRICT: seed has zero picks; refusing to write an empty panel.")

    serialized = json.dumps(payload, indent=2, ensure_ascii=False)

    if args.stdout or not args.apply:
        print(serialized)
        if not args.apply:
            return 0

    if args.apply:
        os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
        with open(OUT_PATH, "w", encoding="utf-8") as fh:
            fh.write(serialized)
        os.chmod(OUT_PATH, 0o644)
        print(f"OK wrote {OUT_PATH} ({os.path.getsize(OUT_PATH)}B; picks={len(payload['picks'])})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
