#!/usr/bin/env python3
"""
Non-crypto pick class audit: counts active picks per dashboard category (mirrors
audit_dashboard/template.html matchCategory) and optionally compares to
multi_asset/data/active_picks.json.

Outputs: audit_trail/data/non_crypto_pick_audit.json

Environment (optional strict mode):
  STRICT_PICK_CLASS_COUNTS=1  — exit 1 if any minimum is violated
  PICK_COUNT_MIN_COMMODITY, PICK_COUNT_MIN_FOREX, PICK_COUNT_MIN_FUTURES,
  PICK_COUNT_MIN_EQUITY, PICK_COUNT_MIN_ETF — integers (default: no minimum)

Live dashboard JSON is often not on GitHub Pages under /data/; compare against
local dashboard_payload.json produced by audit_trail.dashboard_generator.

Keep BLOCKED_SYSTEMS in sync with audit_dashboard/template.html (search BLOCKED_SYSTEMS).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PAYLOAD = ROOT / "audit_trail" / "data" / "dashboard_payload.json"
DEFAULT_MIRROR = ROOT / "multi_asset" / "data" / "active_picks.json"
OUT_JSON = ROOT / "audit_trail" / "data" / "non_crypto_pick_audit.json"

# Sync with audit_dashboard/template.html — BLOCKED_SYSTEMS (exact names, lowercased for check)
BLOCKED_SYSTEMS = frozenset(
    x.lower()
    for x in (
        "mercury2_fast",
        "stocks_competition",
        "fast_stocks_competition",
        "kimi_signal_tracking",
        "ml_bg_system_a",
        "ml_bg_system_b",
        "ml_crypto_pred_v12",
        "crypto_winners",
        "ml_bg_system_c",
        "ml_bg_ensemble",
        "signal_validation",
        "ml_bg_system_f",
        "quan_engine_scalp",
        "quan_engine_swing",
    )
)


def _blocked(source: str) -> bool:
    return (source or "").strip().lower() in BLOCKED_SYSTEMS


def match_category(pick: dict, cat_key: str) -> bool:
    """Mirror template.html matchCategory (non-crypto drill-down)."""
    ac = ((pick.get("asset_class") or "") + "").upper()
    cat = ((pick.get("category") or "") + "").upper()
    sym = ((pick.get("symbol") or "") + "").upper()
    if cat_key == "FOREX":
        return ac == "FOREX" or cat == "FOREX" or "=X" in sym
    if cat_key == "EQUITY":
        return (
            ac == "EQUITY"
            or ac == "STOCK"
            or cat == "EQUITY"
            or cat == "STOCK"
            or cat == "STOCKS"
        )
    if cat_key == "COMMODITY":
        return (
            ac == "COMMODITY"
            or cat == "COMMODITY"
            or cat == "COMMODITIES"
            or sym.startswith("XAG")
            or sym.startswith("XAU")
        )
    if cat_key == "FUTURES":
        return ac == "FUTURES" or cat == "FUTURES" or cat == "FUTURE"
    if cat_key == "ETF":
        return ac == "ETF" or cat == "ETF"
    return False


def load_json(path: Path):
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"WARNING: could not load {path}: {e}", file=sys.stderr)
        return None


def count_categories(active: list) -> dict[str, int]:
    keys = ("EQUITY", "FOREX", "COMMODITY", "FUTURES", "ETF")
    out = {k: 0 for k in keys}
    for p in active:
        if not isinstance(p, dict):
            continue
        if _blocked(str(p.get("source_system") or "")):
            continue
        for k in keys:
            if match_category(p, k):
                out[k] += 1
    return out


def commodity_symbols(picks: list) -> list[str]:
    syms = []
    for p in picks:
        if isinstance(p, dict) and match_category(p, "COMMODITY"):
            syms.append(str(p.get("symbol") or ""))
    return sorted(set(s for s in syms if s))


def compare_mirror(payload_active: list, mirror_path: Path) -> dict:
    mirror_data = load_json(mirror_path)
    if not mirror_data:
        return {"error": "mirror_missing_or_invalid", "path": str(mirror_path)}
    if isinstance(mirror_data, list):
        mirror_picks = mirror_data
    else:
        mirror_picks = mirror_data.get("picks")
        if not isinstance(mirror_picks, list):
            mirror_picks = []

    m_commod = {p.get("symbol") for p in mirror_picks if isinstance(p, dict) and match_category(p, "COMMODITY")}
    p_commod = {p.get("symbol") for p in payload_active if isinstance(p, dict) and match_category(p, "COMMODITY")}

    return {
        "mirror_path": str(mirror_path),
        "mirror_commodity_symbols": sorted(m_commod),
        "payload_commodity_symbols": sorted(p_commod),
        "only_in_mirror": sorted(m_commod - p_commod),
        "only_in_payload": sorted(p_commod - m_commod),
    }


def check_strict(counts: dict[str, int]) -> list[str]:
    if os.environ.get("STRICT_PICK_CLASS_COUNTS", "").strip() not in ("1", "true", "yes", "Y"):
        return []
    violations = []
    env_map = {
        "COMMODITY": "PICK_COUNT_MIN_COMMODITY",
        "FOREX": "PICK_COUNT_MIN_FOREX",
        "FUTURES": "PICK_COUNT_MIN_FUTURES",
        "EQUITY": "PICK_COUNT_MIN_EQUITY",
        "ETF": "PICK_COUNT_MIN_ETF",
    }
    for cat, env_key in env_map.items():
        raw = os.environ.get(env_key, "").strip()
        if not raw:
            continue
        try:
            need = int(raw)
        except ValueError:
            continue
        got = counts.get(cat, 0)
        if got < need:
            violations.append(f"{cat}: count {got} < minimum {need} ({env_key})")
    return violations


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit non-crypto pick counts vs dashboard categories.")
    ap.add_argument(
        "payload",
        nargs="?",
        default=str(DEFAULT_PAYLOAD),
        help="Path to dashboard_payload.json",
    )
    ap.add_argument(
        "--multi-asset",
        default=os.environ.get("MULTI_ASSET_MIRROR", str(DEFAULT_MIRROR)),
        help="Optional multi_asset active_picks.json for commodity symbol diff",
    )
    args = ap.parse_args()
    payload_path = Path(args.payload)

    data = load_json(payload_path)
    if not data or not isinstance(data, dict):
        print(f"ERROR: invalid payload: {payload_path}", file=sys.stderr)
        return 2

    picks_root = data.get("picks") or {}
    active = picks_root.get("active") if isinstance(picks_root, dict) else []
    if not isinstance(active, list):
        active = []

    counts = count_categories(active)
    commod_syms = commodity_symbols(active)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "payload_path": str(payload_path),
        "payload_generated_at": data.get("generated_at"),
        "active_total_unfiltered": len(active),
        "active_by_category_visible": counts,
        "commodity_symbols_in_payload": commod_syms,
        "strict_mode": os.environ.get("STRICT_PICK_CLASS_COUNTS", ""),
    }

    ma_path = Path(args.multi_asset)
    if ma_path.exists():
        report["mirror_compare"] = compare_mirror(active, ma_path)
    else:
        report["mirror_compare"] = {"skipped": True, "reason": "file not found", "path": str(ma_path)}

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("Non-crypto pick class audit")
    print(f"  Payload: {payload_path}")
    print(f"  Generated at (payload): {data.get('generated_at')}")
    print(f"  Active picks (total in payload): {len(active)}")
    print("  Visible counts (after blocked-system filter, may double-count multi-category):")
    for k, v in counts.items():
        print(f"    {k}: {v}")
    if commod_syms:
        print(f"  Commodity symbols: {', '.join(commod_syms)}")
    mc = report.get("mirror_compare") or {}
    if mc.get("only_in_mirror") or mc.get("only_in_payload"):
        print("  Mirror vs payload commodity symbol diff:")
        print(f"    only_in_mirror: {mc.get('only_in_mirror')}")
        print(f"    only_in_payload: {mc.get('only_in_payload')}")
    print(f"  Wrote: {OUT_JSON}")

    violations = check_strict(counts)
    if violations:
        for v in violations:
            print(f"STRICT VIOLATION: {v}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
