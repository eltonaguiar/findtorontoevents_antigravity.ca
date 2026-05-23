"""Score-band edge diagnostic for crypto LONG picks.

Verifies whether high-score crypto LONG picks exhibit the claimed edge
(PF >= 3.0 at score >= 65) on the current closed-picks ledger. This is a
gate for shipping the score-based promotion mechanism in curation:
  - TIER_S:  score >= 65   (claimed PF 4.47 on 186 trades, ~60.8% WR)
  - TIER_A:  50 <= score < 65  (claimed PF 1.83 on 1,011 trades, ~52.4% WR)
  - TIER_B:  everything else

Buckets by elite_score (the most-populated score field in the live
ledger) and reports n, WR, PF, expectancy, Wilson 95% CI, gross_win,
gross_loss per bucket.

Exit code:
  0 if bucket [65+] has Wilson 95% CI lower bound >= 0.50 (edge verified)
  2 otherwise (edge NOT confirmed — do NOT ship promotion gate)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import defaultdict

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
)
from tools.data_integrity._common import (  # noqa: E402
    CLOSED_PICKS,
    classify_asset,
    ensure_out_dir as _di_ensure_out_dir,
    is_ghost_row,
    load_json_list,
)

CALIBRATION_OUT_DIR = os.path.join(os.path.dirname(__file__), "out")

SCORE_FIELD_CANDIDATES = ("score", "final_score", "elite_score", "smart_score")
LONG_DIRECTIONS = {"LONG", "BUY"}

BUCKETS: list[tuple[str, float, float]] = [
    ("<50", float("-inf"), 50.0),
    ("[50,65)", 50.0, 65.0),
    ("[65,80)", 65.0, 80.0),
    ("[80,100]", 80.0, float("inf")),
]


def ensure_out_dir() -> str:
    os.makedirs(CALIBRATION_OUT_DIR, exist_ok=True)
    # also ensure data_integrity out dir exists for symmetry
    try:
        _di_ensure_out_dir()
    except Exception:
        pass
    return CALIBRATION_OUT_DIR


def wilson_ci(wins: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    """Return (point_wr, ci_lo, ci_hi) using Wilson score interval."""
    if n == 0:
        return 0.0, 0.0, 0.0
    p = wins / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)) / denom
    return p, max(0.0, centre - half), min(1.0, centre + half)


def pick_direction(p: dict) -> str:
    for k in ("direction", "signal_type", "side"):
        v = p.get(k)
        if v:
            return str(v).upper().strip()
    return ""


def pick_is_crypto(p: dict) -> bool:
    return classify_asset(p) == "CRYPTO"


def pick_is_long(p: dict) -> bool:
    return pick_direction(p) in LONG_DIRECTIONS


def best_score_field(rows: list[dict]) -> str:
    """Return the score field with the most non-null values."""
    counts = {f: 0 for f in SCORE_FIELD_CANDIDATES}
    for r in rows:
        for f in SCORE_FIELD_CANDIDATES:
            if r.get(f) is not None:
                counts[f] += 1
    # Prefer the highest count; stable tie-break by list order
    best = max(SCORE_FIELD_CANDIDATES, key=lambda f: (counts[f], -SCORE_FIELD_CANDIDATES.index(f)))
    return best if counts[best] > 0 else SCORE_FIELD_CANDIDATES[0]


def get_pnl(p: dict) -> float | None:
    v = p.get("pnl_pct")
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        return None


def bucket_for_score(score: float) -> str | None:
    for name, lo, hi in BUCKETS:
        if lo <= score < hi:
            return name
    # [80,100] upper inclusive via inf already
    return None


def build_bands(
    rows: list[dict], score_field: str
) -> dict[str, dict]:
    bands: dict[str, list[float]] = defaultdict(list)
    skipped_no_score = 0
    skipped_no_pnl = 0
    total_crypto_long = 0

    for r in rows:
        if is_ghost_row(r):
            continue
        if not pick_is_crypto(r):
            continue
        if not pick_is_long(r):
            continue
        total_crypto_long += 1
        s = r.get(score_field)
        if s is None:
            skipped_no_score += 1
            continue
        try:
            s = float(s)
        except Exception:
            skipped_no_score += 1
            continue
        pnl = get_pnl(r)
        if pnl is None:
            skipped_no_pnl += 1
            continue
        name = bucket_for_score(s)
        if name is None:
            continue
        bands[name].append(pnl)

    results: dict[str, dict] = {}
    for name, _lo, _hi in BUCKETS:
        pnls = bands.get(name, [])
        n = len(pnls)
        wins = sum(1 for p in pnls if p > 0)
        gross_win = float(sum(p for p in pnls if p > 0))
        gross_loss = float(sum(-p for p in pnls if p <= 0))
        pf = (gross_win / gross_loss) if gross_loss > 0 else (float("inf") if gross_win > 0 else 0.0)
        expectancy = (sum(pnls) / n) if n else 0.0
        wr, ci_lo, ci_hi = wilson_ci(wins, n)
        results[name] = {
            "bucket": name,
            "n": n,
            "wins": wins,
            "losses": n - wins,
            "wr": wr,
            "wr_ci_lo": ci_lo,
            "wr_ci_hi": ci_hi,
            "pf": pf if math.isfinite(pf) else None,
            "pf_is_inf": not math.isfinite(pf),
            "expectancy_pct": expectancy,
            "gross_win_pct": gross_win,
            "gross_loss_pct": gross_loss,
        }
    results["_meta"] = {
        "total_crypto_long_rows": total_crypto_long,
        "skipped_no_score": skipped_no_score,
        "skipped_no_pnl": skipped_no_pnl,
        "score_field": score_field,
    }
    return results


def print_table(results: dict[str, dict]) -> None:
    print("=" * 98)
    print("CRYPTO LONG SCORE-BAND EDGE REPORT")
    print("=" * 98)
    meta = results.get("_meta", {})
    print(
        f"score_field={meta.get('score_field')}  "
        f"crypto_long_rows={meta.get('total_crypto_long_rows')}  "
        f"skipped_no_score={meta.get('skipped_no_score')}  "
        f"skipped_no_pnl={meta.get('skipped_no_pnl')}"
    )
    print("-" * 98)
    header = (
        f"{'BUCKET':10s} {'n':>6s} {'wins':>5s} {'WR':>7s} "
        f"{'CI_lo':>7s} {'CI_hi':>7s} {'PF':>8s} {'exp%':>8s} "
        f"{'gw%':>9s} {'gl%':>9s}"
    )
    print(header)
    print("-" * 98)
    for name, _lo, _hi in BUCKETS:
        r = results.get(name)
        if not r:
            continue
        pf = r["pf"]
        pf_s = "inf" if r["pf_is_inf"] else (f"{pf:.2f}" if pf is not None else "-")
        print(
            f"{name:10s} {r['n']:6d} {r['wins']:5d} "
            f"{r['wr']*100:6.2f}% {r['wr_ci_lo']*100:6.2f}% {r['wr_ci_hi']*100:6.2f}% "
            f"{pf_s:>8s} {r['expectancy_pct']:7.3f}% "
            f"{r['gross_win_pct']:8.2f}% {r['gross_loss_pct']:8.2f}%"
        )
    print("-" * 98)


def edge_verified(results: dict[str, dict]) -> bool:
    """High-score crypto LONG edge is verified iff the combined [65+]
    bucket has Wilson 95% CI lower bound >= 0.50 with n >= 30."""
    b1 = results.get("[65,80)", {"n": 0, "wins": 0})
    b2 = results.get("[80,100]", {"n": 0, "wins": 0})
    n = int(b1.get("n", 0)) + int(b2.get("n", 0))
    wins = int(b1.get("wins", 0)) + int(b2.get("wins", 0))
    if n < 30:
        return False
    _, ci_lo, _ = wilson_ci(wins, n)
    return ci_lo >= 0.50


def run(closed_path: str = CLOSED_PICKS) -> tuple[int, dict]:
    rows = load_json_list(closed_path)
    score_field = best_score_field(rows)
    results = build_bands(rows, score_field)
    print_table(results)

    out_dir = ensure_out_dir()
    out_path = os.path.join(out_dir, "score_band_edge.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nwrote {out_path}")

    verified = edge_verified(results)
    b1 = results.get("[65,80)", {})
    b2 = results.get("[80,100]", {})
    n_hi = int(b1.get("n", 0)) + int(b2.get("n", 0))
    wins_hi = int(b1.get("wins", 0)) + int(b2.get("wins", 0))
    _, ci_lo, ci_hi = wilson_ci(wins_hi, n_hi)
    print(
        f"\nCOMBINED [65+] bucket: n={n_hi} wins={wins_hi} "
        f"Wilson 95% CI = [{ci_lo*100:.2f}%, {ci_hi*100:.2f}%]"
    )
    if verified:
        print("VERIFIED: Wilson CI lower bound >= 50%. Promotion gate is safe to ship.")
        return 0, results
    print(
        "NOT VERIFIED: Wilson CI lower bound < 50% (or n < 30). "
        "Do NOT ship the promotion gate based on this ledger."
    )
    return 2, results


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--closed", default=CLOSED_PICKS)
    args = ap.parse_args(argv)
    code, _ = run(args.closed)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
