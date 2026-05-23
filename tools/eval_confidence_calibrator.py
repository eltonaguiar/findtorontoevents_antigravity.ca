"""Evaluate confidence-calibrator quality (A6).

For each asset class with a fitted calibrator, compute Spearman rank
correlation between confidence and realised outcome (win=1/loss=0) on the
closed picks, for BOTH raw and calibrated confidence. Acceptance bar:
calibrated rho >= 0.15 AND calibrated rho > raw rho.

Usage:
  python -m tools.eval_confidence_calibrator        # in-sample (uses committed calibrators.json)
  python -m tools.eval_confidence_calibrator --oos  # out-of-sample 70/30 time split
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from alpha_engine.confidence_calibrator import (
    CAL_PATH,
    PICKS_PATH,
    _CLASSES,
    _apply_isotonic,
    fit_from_picks,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _spearman(x: list[float], y: list[float]) -> float | None:
    """Spearman rho with average ranks for ties. Returns None if degenerate."""
    n = len(x)
    if n < 3:
        return None

    def _rank(vals: list[float]) -> list[float]:
        order = sorted(range(n), key=lambda i: vals[i])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and vals[order[j + 1]] == vals[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                ranks[order[k]] = avg
            i = j + 1
        return ranks

    rx, ry = _rank(x), _rank(y)
    mx = sum(rx) / n
    my = sum(ry) / n
    cov = sum((rx[i] - mx) * (ry[i] - my) for i in range(n))
    vx = sum((rx[i] - mx) ** 2 for i in range(n))
    vy = sum((ry[i] - my) ** 2 for i in range(n))
    if vx <= 0 or vy <= 0:
        return None
    return cov / (vx ** 0.5 * vy ** 0.5)


def _samples(picks: list[dict]) -> dict[str, list[tuple[float, int]]]:
    by_class: dict[str, list[tuple[float, int]]] = {k: [] for k in _CLASSES}
    for p in picks:
        c = p.get("confidence")
        pnl = p.get("pnl_pct")
        klass = (p.get("asset_class") or p.get("category") or "").strip().upper()
        if c is None or pnl is None or klass not in by_class:
            continue
        try:
            c_f = float(c)
            pnl_f = float(pnl)
        except (TypeError, ValueError):
            continue
        by_class[klass].append((max(0.0, min(1.0, c_f)), 1 if pnl_f > 0 else 0))
    return by_class


def main() -> int:
    oos = "--oos" in sys.argv[1:]
    data = json.load(PICKS_PATH.open("r", encoding="utf-8"))
    picks = data.get("picks", {}).get("recent_closed", [])

    if oos:
        # Time-ordered 70/30 split: fit on oldest 70%, eval on newest 30%.
        usable = [p for p in picks
                  if p.get("confidence") is not None and p.get("pnl_pct") is not None]
        usable.sort(key=lambda p: p.get("closed_at") or p.get("timestamp") or "")
        cut = int(len(usable) * 0.7)
        train, test = usable[:cut], usable[cut:]
        artifact = fit_from_picks(train)
        calibrators = artifact.get("calibrators", {})
        min_n = artifact.get("min_fit_n", 30)
        by_class = _samples(test)
        print(f"OUT-OF-SAMPLE: fit on oldest {len(train)}, eval on newest {len(test)}")
    else:
        artifact = json.load(CAL_PATH.open("r", encoding="utf-8"))
        calibrators = artifact.get("calibrators", {})
        min_n = artifact.get("min_fit_n", 30)
        by_class = _samples(picks)

    return _report(by_class, calibrators, min_n)


def _report(by_class, calibrators, min_n) -> int:
    results = {}
    for klass, samples in by_class.items():
        n = len(samples)
        raw_x = [s[0] for s in samples]
        y = [s[1] for s in samples]
        raw_rho = _spearman(raw_x, y) if n >= 3 else None
        table = calibrators.get(klass)
        cal_rho = None
        if table:
            cal_x = [_apply_isotonic(table, s[0]) for s in samples]
            cal_rho = _spearman(cal_x, y)
        # Verdict
        if not table or n < min_n:
            verdict = "INSUFFICIENT-N"
        elif cal_rho is not None and cal_rho >= 0.15 and (raw_rho is None or cal_rho > raw_rho):
            verdict = "ENABLE"
        else:
            verdict = "KEEP-OFF"
        results[klass] = {
            "n": n,
            "raw_rho": raw_rho,
            "cal_rho": cal_rho,
            "has_calibrator": bool(table),
            "verdict": verdict,
        }

    print(f"{'CLASS':<11}{'n':>7}{'raw_rho':>12}{'cal_rho':>12}  verdict")
    for klass, r in results.items():
        rr = f"{r['raw_rho']:+.4f}" if r["raw_rho"] is not None else "  n/a "
        cr = f"{r['cal_rho']:+.4f}" if r["cal_rho"] is not None else "  n/a "
        print(f"{klass:<11}{r['n']:>7}{rr:>12}{cr:>12}  {r['verdict']}")

    out = REPO_ROOT / "reports" / "_confidence_calibrator_eval.json"
    json.dump(results, out.open("w", encoding="utf-8"), indent=2)
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
