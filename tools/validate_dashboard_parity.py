#!/usr/bin/env python3
"""
Closed-book dashboard parity: Python `classify_hf_conviction_tier` vs JS `passesHighConvictionPick`.

Closed rows usually **do not** store `hf_conviction_tier`, so comparing raw JSON to the full
JS function makes tier short-circuit look "missing". This tool reports:

1. **Heuristic parity** — `classify_hf_conviction_tier` vs `passes_high_conviction_heuristics_only`
   (JS body without S/A/B short-circuit). Shows how often ML/bypass tiers lack a dashboard heuristic match.

2. **Stamped parity** — merge computed `hf_conviction_tier` onto the pick, then run full JS mirror
   (simulates live payload after `attach_hf_conviction_tiers_to_picks`). Should match `tier in S/A/B`
   vs "would HC button light up" for tiered rows; remaining gaps are heuristic-only passes without tier.

3. **Alias map sync** — checks that STRATEGY_TRACK_ALIASES (alpha_engine/config.py) and
   LEADERBOARD_STRATEGY_ALIASES (audit_dashboard/template.html) have identical entries so split
   track records are resolved consistently in both the Python backend and JS dashboard.

Usage:
  python tools/validate_dashboard_parity.py
  python tools/validate_dashboard_parity.py --json-out audit_trail/data/dashboard_hc_parity.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_TOOLS = Path(__file__).resolve().parent
for _p in (_REPO, _TOOLS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from alpha_engine.conviction_stack import classify_hf_conviction_tier, load_conviction_tiers_config

from dashboard_hc_rules import (
    passes_high_conviction_heuristics_only,
    passes_high_conviction_pick,
    passes_high_conviction_with_stamped_tier,
)


def _check_alias_map_sync() -> dict:
    """
    Compare STRATEGY_TRACK_ALIASES (Python, alpha_engine/config.py) with
    LEADERBOARD_STRATEGY_ALIASES (JS, audit_dashboard/template.html).

    Both dicts must have the same keys and values so split track records are
    resolved identically by the backend and the dashboard JS.

    Returns a report dict with 'ok', 'py_only', 'js_only', 'value_mismatch'.
    """
    # ── Load Python aliases ──
    try:
        from alpha_engine.config import STRATEGY_TRACK_ALIASES as py_aliases
    except ImportError:
        py_aliases = {}

    # ── Extract JS aliases from template.html via regex ──
    template_path = _REPO / "audit_dashboard" / "template.html"
    js_aliases: dict[str, str] = {}
    if template_path.exists():
        html = template_path.read_text(encoding="utf-8", errors="replace")
        # Match the block:  const LEADERBOARD_STRATEGY_ALIASES = { ... };
        block_match = re.search(
            r"const LEADERBOARD_STRATEGY_ALIASES\s*=\s*\{([^}]+)\};",
            html,
            re.DOTALL,
        )
        if block_match:
            block = block_match.group(1)
            # Match key: 'value' or key: "value" lines (skip comments)
            for m in re.finditer(
                r"""^\s*([\w]+)\s*:\s*['"]([^'"]+)['"]\s*,?\s*(?://.*)?$""",
                block,
                re.MULTILINE,
            ):
                js_aliases[m.group(1)] = m.group(2)

    py_keys = set(py_aliases.keys())
    js_keys = set(js_aliases.keys())
    py_only = sorted(py_keys - js_keys)
    js_only = sorted(js_keys - py_keys)
    value_mismatch = sorted(
        k for k in py_keys & js_keys if py_aliases[k] != js_aliases[k]
    )
    ok = not py_only and not js_only and not value_mismatch
    return {
        "ok": ok,
        "py_alias_count": len(py_aliases),
        "js_alias_count": len(js_aliases),
        "py_only": py_only,
        "js_only": js_only,
        "value_mismatch": value_mismatch,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--closed-path",
        type=Path,
        default=_REPO / "alpha_engine" / "data" / "closed_picks.json",
    )
    ap.add_argument("--json-out", type=Path, default=None)
    ap.add_argument("--max-examples", type=int, default=25)
    args = ap.parse_args()

    if not args.closed_path.is_file():
        print("Missing %s" % args.closed_path, file=sys.stderr)
        return 1

    data = json.loads(args.closed_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        print("Expected JSON array", file=sys.stderr)
        return 1

    cfg = load_conviction_tiers_config()

    # --- A) Raw JSON (no tier field): full JS mirror — informational only ---
    raw_both = raw_py_only = raw_js_only = raw_neither = 0

    # --- B) Heuristic-only vs classifier tier ---
    h_both = h_py_only = h_js_only = h_neither = 0
    h_py_examples: list[dict] = []
    h_js_examples: list[dict] = []

    # --- C) Stamped tier + full JS ---
    s_agree = s_disagree = 0
    s_examples: list[dict] = []

    for pick in data:
        if not isinstance(pick, dict):
            continue
        tier, reasons = classify_hf_conviction_tier(pick, cfg)
        py_tier = tier in ("S", "A", "B")

        js_raw = passes_high_conviction_pick(pick)
        if js_raw and py_tier:
            raw_both += 1
        elif not js_raw and not py_tier:
            raw_neither += 1
        elif py_tier and not js_raw:
            raw_py_only += 1
        else:
            raw_js_only += 1

        js_h = passes_high_conviction_heuristics_only(pick)
        if js_h and py_tier:
            h_both += 1
        elif not js_h and not py_tier:
            h_neither += 1
        elif py_tier and not js_h:
            h_py_only += 1
            if len(h_py_examples) < args.max_examples:
                h_py_examples.append(
                    {
                        "symbol": pick.get("symbol"),
                        "asset_class": pick.get("asset_class"),
                        "tier": tier,
                        "strategy": (pick.get("strategy") or "")[:48],
                    }
                )
        else:
            h_js_only += 1
            if len(h_js_examples) < args.max_examples:
                h_js_examples.append(
                    {
                        "symbol": pick.get("symbol"),
                        "asset_class": pick.get("asset_class"),
                        "tier": tier,
                        "strategy": (pick.get("strategy") or "")[:48],
                    }
                )

        js_stamp = passes_high_conviction_with_stamped_tier(pick, tier, reasons)
        if py_tier == js_stamp:
            s_agree += 1
        else:
            s_disagree += 1
            if len(s_examples) < args.max_examples:
                s_examples.append(
                    {
                        "symbol": pick.get("symbol"),
                        "tier": tier,
                        "py_tier": py_tier,
                        "js_stamped": js_stamp,
                    }
                )

    n = raw_both + raw_py_only + raw_js_only + raw_neither
    report = {
        "source": str(args.closed_path),
        "total_picks": n,
        "raw_json_full_js_mirror": {
            "note": "Most closed rows lack hf_conviction_tier; JS tier short-circuit rarely fires.",
            "both_pass": raw_both,
            "both_fail": raw_neither,
            "python_tier_js_false": raw_py_only,
            "js_pass_no_tier": raw_js_only,
        },
        "heuristic_vs_classifier_tier": {
            "description": "Classifier tier vs JS rules without S/A/B short-circuit",
            "both_heuristic_and_tier": h_both,
            "neither": h_neither,
            "tier_only_no_heuristic": h_py_only,
            "heuristic_only_no_tier": h_js_only,
            "examples_tier_only": h_py_examples,
            "examples_heuristic_only": h_js_examples,
        },
        "stamped_tier_full_js": {
            "description": "After stamping hf_conviction_tier from classifier; should match py_tier flag",
            "agree": s_agree,
            "disagree": s_disagree,
            "examples_disagree": s_examples,
        },
    }

    print("=== Dashboard HC parity (closed picks) ===")
    print("  Total picks: %s" % n)
    print()
    print("  [A] Raw JSON + full JS (informational — tier field usually absent on closes):")
    print("      tier+JS both: %s | neither: %s | tier only: %s | JS only: %s" % (raw_both, raw_neither, raw_py_only, raw_js_only))
    print()
    print("  [B] Classifier tier vs JS heuristics only (no S/A/B short-circuit):")
    print("      tier+heuristic: %s | neither: %s | tier only: %s | heuristic only: %s" % (h_both, h_neither, h_py_only, h_js_only))
    if h_py_examples:
        print("      Examples tier from Python, no dashboard heuristic (up to 5):")
        for m in h_py_examples[:5]:
            print("       ", m)
    if h_js_examples:
        print("      Examples heuristic pass, classifier no tier (up to 5):")
        for m in h_js_examples[:5]:
            print("       ", m)
    print()
    print("  [C] Stamped hf_conviction_tier + full JS (simulates live payload):")
    print("      agree: %s  disagree: %s" % (s_agree, s_disagree))
    if s_examples:
        print("      (Disagree examples — investigate):")
        for m in s_examples[:5]:
            print("       ", m)

    # ── [D] Alias map sync check ──
    alias_sync = _check_alias_map_sync()
    report["alias_map_sync"] = alias_sync

    print()
    print("  [D] STRATEGY_TRACK_ALIASES (Python config.py) vs LEADERBOARD_STRATEGY_ALIASES (template.html):")
    if alias_sync["ok"]:
        print("      OK — %d aliases in sync" % alias_sync["py_alias_count"])
    else:
        if alias_sync["py_only"]:
            print("      Python-only (missing from JS): %s" % alias_sync["py_only"])
        if alias_sync["js_only"]:
            print("      JS-only (missing from Python): %s" % alias_sync["js_only"])
        if alias_sync["value_mismatch"]:
            print("      Value mismatch (same key, different canonical): %s" % alias_sync["value_mismatch"])
        print("      ACTION REQUIRED: update audit_dashboard/template.html or alpha_engine/config.py")

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print()
        print("Wrote %s" % args.json_out)

    return 1 if not alias_sync["ok"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
