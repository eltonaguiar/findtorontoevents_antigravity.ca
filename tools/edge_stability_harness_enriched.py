#!/usr/bin/env python3
"""Edge-stability harness — enriched-ledger extension (Fork 1, research only).

Thin wrapper that runs the SAME walk-forward gate as
`tools/edge_stability_harness.py` but against the feature-backfilled sidecar
`alpha_engine/data/closed_picks_enriched.json` (produced by
`tools/backfill_pick_features.py`).

It exists to honestly verdict the two candidate score families that the
original harness could not test because the ledger lacked their inputs
(`reports/EDGE_VERDICT_2026-05-18.md`):

  * qlib factors      — qlib_vol_ratio, qlib_pv_corr30, qlib_realized_vol30
  * regime-conditioned — regime_score (numeric proxy of regime_at_entry)

Admissibility logic, EFF_MIN, MIN_WINDOW_N, MIN_STABLE_WINDOWS, window
bucketing and `_window_eff` are imported unchanged from the canonical harness
so the verdict is produced by the exact same gate. Nothing here ranks or gates
production picks.

    python tools/edge_stability_harness_enriched.py [--json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENRICHED = ROOT / "alpha_engine" / "data" / "closed_picks_enriched.json"

sys.path.insert(0, str(Path(__file__).resolve().parent))
import edge_stability_harness as H  # noqa: E402  the canonical gate

# Candidate fields the backfill added. regime_score is the numeric proxy the
# harness needs; regime_at_entry is the categorical label it derives from.
CANDIDATE_FIELDS = ("qlib_vol_ratio", "qlib_pv_corr30", "qlib_realized_vol30",
                    "regime_score")


def _load_enriched() -> list[dict]:
    d = json.loads(ENRICHED.read_text(encoding="utf-8"))
    picks = d.get("picks", d if isinstance(d, list) else [])
    return [p for p in picks if isinstance(p, dict)]


def evaluate_enriched(field: str, window_days: int = 14) -> dict:
    """Walk-forward verdict for one field, scored on the enriched sidecar.

    Reuses H._windows / H._window_eff / H.MIN_WINDOW_N etc. verbatim; only the
    data source differs (enriched sidecar instead of closed_picks.json).
    """
    wins = [w for w in H._windows(_load_enriched(), window_days)
            if len(w) >= H.MIN_WINDOW_N]
    effs = []
    for i, w in enumerate(wins):
        # how many picks in this window actually carry the candidate field
        have = sum(1 for p in w if H._num(p.get(field)) is not None)
        effs.append({"window": i, "n": len(w), "n_with_field": have,
                     "eff": H._window_eff(w, field)})
    scored = [r for r in effs if r["eff"] is not None]
    strong = [r for r in scored if abs(r["eff"]) >= H.EFF_MIN]
    pos = [r for r in strong if r["eff"] > 0]
    neg = [r for r in strong if r["eff"] < 0]
    same_sign = pos if len(pos) >= len(neg) else neg
    admissible = (len(same_sign) >= H.MIN_STABLE_WINDOWS
                  and len(same_sign) == len(strong))
    sign = "+" if (admissible and same_sign and same_sign[0]["eff"] > 0) else \
           ("-" if (admissible and same_sign) else "mixed")
    return {
        "field": field,
        "windows_scored": len(scored),
        "windows_strong": len(strong),
        "strong_positive": len(pos),
        "strong_negative": len(neg),
        "per_window_eff": effs,
        "sign": sign,
        "admissible": admissible,
        "reason": (
            "ADMISSIBLE — stable same-sign separation"
            if admissible else
            f"REJECTED — strong in {len(strong)} windows but signs split "
            f"({len(pos)}+/{len(neg)}-); needs {H.MIN_STABLE_WINDOWS} same-sign"
            if (pos and neg) else
            f"REJECTED — only {len(strong)}/{len(scored)} windows reach "
            f"eff>={H.EFF_MIN}"
        ),
    }


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--window-days", type=int, default=14)
    ap.add_argument("--json", dest="as_json", action="store_true")
    args = ap.parse_args()

    results = [evaluate_enriched(f, args.window_days) for f in CANDIDATE_FIELDS]
    if args.as_json:
        print(json.dumps(results, indent=2))
        return 0

    print(f"# Edge-Stability Harness (ENRICHED) — {args.window_days}-day "
          f"walk-forward")
    print(f"# source: alpha_engine/data/closed_picks_enriched.json")
    print(f"# admissible iff |eff|>={H.EFF_MIN} same-sign in "
          f">={H.MIN_STABLE_WINDOWS} windows\n")
    for r in results:
        effs = " ".join(
            (f"{e['eff']:+.2f}" if e["eff"] is not None else "  n/a")
            for e in r["per_window_eff"])
        flag = "ADMISSIBLE" if r["admissible"] else "REJECTED"
        print(f"{r['field']:<22} [{flag:^10}] effs(new->old): {effs}")
        print(f"{'':<22}  {r['reason']}")
    adm = [r["field"] for r in results if r["admissible"]]
    print(f"\nADMISSIBLE candidates: {adm or 'NONE'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
