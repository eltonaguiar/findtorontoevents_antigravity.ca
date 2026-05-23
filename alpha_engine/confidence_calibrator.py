"""Per-asset-class confidence calibration via isotonic regression.

Background
----------
Memory note: "confidence inverts on ETF/CRYPTO" — i.e. high confidence picks
have *lower* realised win-rate than low-confidence picks for those classes.
This is a calibration problem, not a model problem: the score's *ranking* may
be informative but its *level* doesn't map to true P(win).

Confirmed inversion (n=3,497 closed picks, audit_dashboard/data/dashboard_data.json):
    CRYPTO  n=1514  high_conf(>=0.70)_WR=38.2%  low_conf_WR=44.7%   INVERTED
    ETF     n=  86  high_conf_WR=75.0%          low_conf_WR=51.4%   partial
    EQUITY  n= 282  high_conf_WR=62.5%          low_conf_WR=51.2%   normal
    FOREX/COMMODITY                                                  normal

Strategy
--------
Fit an isotonic regression per asset class mapping raw confidence -> realised
P(win). Apply during pick scoring. Off by default until A/B-validated.

Wiring
------
Fit (offline, daily): `python -m alpha_engine.confidence_calibrator fit`
Apply (production):    `from alpha_engine.confidence_calibrator import calibrate`
                       behind env flag `CONFIDENCE_CALIBRATION_ENABLED=1`.
Persisted calibrators: alpha_engine/data/confidence_calibrators.json

Wire-Up Rule status: WIRED. Caller is alpha_engine/smart_picks_engine.py
in `_compute_ml_composite()` (default-off env flag).

Known limitations (cross-AI review 2026-05-02)
----------------------------------------------
1. **Training-label contamination by the resolver bug.** The closed-pick
   labels (`pnl_pct > 0`) used for fitting are produced by
   `alpha_engine/outcome_resolver.py`, which currently uses a 0.1bp WIN
   threshold (`PNL_WIN_THRESHOLD = 0.00001` legacy alias) and re-closes
   non-crypto picks at live yfinance spot every run. ~63-67% of FOREX /
   COMMODITY "wins" are 1bp resolver flicker. The CRYPTO inversion the
   calibrator detects is plausibly real (CRYPTO has its own resolver
   path), but FOREX / COMMODITY / EQUITY calibrators are partially
   regressing on resolver noise. Re-fit after the resolver fix lands
   (GH Actions cloud agent Theme B / `reports/action_B_resolver_2026_04_27.md`).

2. **Trust-tier interaction.** `smart_picks_engine._compute_ml_composite`
   applies `tier_penalty = 0.3` for SANDBOX/UNTRUSTED/UNPROVEN/DEMOTED
   tiers AFTER calibration. Calibration is per-class, tier penalty is
   per-strategy — they are orthogonal and stack multiplicatively. This
   is intended (calibration produces an honest P(win), tier penalty
   layers a "we don't trust this strategy yet" discount), but document
   the interaction here so future agents don't mistake it for a bug.

3. **Drift over time.** Calibrators are stale the moment they're fit.
   Re-fit cadence should be at least daily (GH Actions step; not yet
   wired). Consider Beta-Bernoulli online updating in v2.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

LOG = logging.getLogger("confidence_calibrator")

REPO_ROOT = Path(__file__).resolve().parents[1]
CAL_PATH = REPO_ROOT / "alpha_engine" / "data" / "confidence_calibrators.json"
PICKS_PATH = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"

# Asset classes we calibrate. Lower-cased on read; UNKNOWN/missing classes
# pass through uncalibrated (no-op).
_CLASSES = ("CRYPTO", "ETF", "EQUITY", "FOREX", "COMMODITY", "BOND")
_MIN_FIT_N = 30  # don't fit a calibrator on fewer than 30 closed picks
_FLAG_ENV = "CONFIDENCE_CALIBRATION_ENABLED"

_CACHE: dict[str, dict[str, list[float]]] | None = None


def _enabled() -> bool:
    return os.environ.get(_FLAG_ENV, "0").strip().lower() in ("1", "true", "yes")


def _isotonic_fit(x: list[float], y: list[float]) -> dict[str, list[float]]:
    """Fit isotonic regression, return as serialisable knot points.

    sklearn's IsotonicRegression isn't trivially JSON-serialisable, so we
    store (sorted x_thresholds, y_predictions) for stepwise interpolation
    at apply time. This avoids a sklearn dependency at apply time too —
    only fit needs sklearn.
    """
    from sklearn.isotonic import IsotonicRegression  # local import: fit-only
    cal = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0, increasing="auto")
    cal.fit(x, y)
    # Build a uniform-grid lookup so apply is dependency-free.
    grid = [round(i * 0.01, 2) for i in range(0, 101)]
    pred = [float(p) for p in cal.predict(grid)]
    return {"grid": grid, "pred": pred}


def _apply_isotonic(table: dict[str, list[float]], x: float) -> float:
    """Interpolate a single calibration. table = {grid, pred}."""
    grid = table["grid"]
    pred = table["pred"]
    if x <= grid[0]:
        return pred[0]
    if x >= grid[-1]:
        return pred[-1]
    # Linear interpolation between adjacent grid points
    lo, hi = 0, len(grid) - 1
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if grid[mid] <= x:
            lo = mid
        else:
            hi = mid
    g0, g1 = grid[lo], grid[hi]
    p0, p1 = pred[lo], pred[hi]
    if g1 == g0:
        return p0
    return p0 + (p1 - p0) * (x - g0) / (g1 - g0)


def _load_cache() -> dict[str, dict[str, list[float]]]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if not CAL_PATH.exists():
        _CACHE = {}
        return _CACHE
    try:
        with CAL_PATH.open("r", encoding="utf-8") as f:
            _CACHE = json.load(f).get("calibrators", {})
    except Exception as exc:
        LOG.warning("confidence_calibrator: cache load failed: %s", exc)
        _CACHE = {}
    return _CACHE


def reset_cache() -> None:
    global _CACHE
    _CACHE = None


def calibrate(pick: dict[str, Any]) -> dict[str, Any]:
    """Mutate pick with a calibrated confidence value.

    No-op when:
      - env flag CONFIDENCE_CALIBRATION_ENABLED is unset/0/false
      - no calibrator exists for the pick's asset_class
      - confidence field missing or non-numeric

    Stores the original under `confidence_raw` for audit traceability.
    """
    if not _enabled():
        return pick
    raw = pick.get("confidence")
    if raw is None:
        return pick
    try:
        raw_f = float(raw)
    except (TypeError, ValueError):
        return pick
    klass = (pick.get("asset_class") or pick.get("category") or "").strip().upper()
    if not klass:
        return pick
    table = _load_cache().get(klass)
    if not table:
        return pick
    cal = _apply_isotonic(table, max(0.0, min(1.0, raw_f)))
    if "confidence_raw" not in pick:
        pick["confidence_raw"] = raw_f
    pick["confidence"] = float(cal)
    pick["confidence_calibrated"] = True
    return pick


def fit_from_picks(picks: list[dict]) -> dict[str, Any]:
    """Fit per-class calibrators from closed picks. Return the artifact dict."""
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

    calibrators: dict[str, dict[str, list[float]]] = {}
    diagnostics: dict[str, dict[str, Any]] = {}
    for klass, samples in by_class.items():
        n = len(samples)
        if n < _MIN_FIT_N:
            diagnostics[klass] = {"n": n, "fitted": False, "reason": "n<min_fit_n"}
            continue
        x = [s[0] for s in samples]
        y = [s[1] for s in samples]
        wr_overall = sum(y) / n
        # Spearman-style sign: high vs low confidence WR
        hi = [s for s in samples if s[0] >= 0.70]
        lo = [s for s in samples if s[0] < 0.70]
        hi_wr = (sum(s[1] for s in hi) / len(hi)) if hi else None
        lo_wr = (sum(s[1] for s in lo) / len(lo)) if lo else None
        try:
            calibrators[klass] = _isotonic_fit(x, y)
        except Exception as exc:
            diagnostics[klass] = {"n": n, "fitted": False, "reason": f"fit_error:{exc!r}"}
            continue
        diagnostics[klass] = {
            "n": n,
            "fitted": True,
            "wr_overall": round(wr_overall, 4),
            "wr_high_conf_ge_0_70": round(hi_wr, 4) if hi_wr is not None else None,
            "wr_low_conf_lt_0_70": round(lo_wr, 4) if lo_wr is not None else None,
            "inverted": (hi_wr is not None and lo_wr is not None and hi_wr < lo_wr),
        }

    from datetime import datetime, timezone
    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "min_fit_n": _MIN_FIT_N,
        "diagnostics": diagnostics,
        "calibrators": calibrators,
    }


def _cmd_fit(picks_path: Path | None = None) -> int:
    path = picks_path or PICKS_PATH
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    picks = data.get("picks", {}).get("recent_closed", [])
    artifact = fit_from_picks(picks)
    CAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CAL_PATH.open("w", encoding="utf-8") as f:
        json.dump(artifact, f, indent=2)
    print(f"Fitted calibrators written to {CAL_PATH}")
    for klass, diag in artifact["diagnostics"].items():
        if diag["fitted"]:
            inv = "INVERTED" if diag["inverted"] else "normal   "
            print(f"  {klass:<10} n={diag['n']:>5} {inv} "
                  f"high={diag['wr_high_conf_ge_0_70']} low={diag['wr_low_conf_lt_0_70']}")
        else:
            print(f"  {klass:<10} n={diag['n']:>5} skipped ({diag['reason']})")
    reset_cache()
    return 0


def _cmd_apply_demo() -> int:
    """Sanity check — apply calibration to a few synthetic picks."""
    os.environ[_FLAG_ENV] = "1"
    reset_cache()
    for klass in _CLASSES:
        for raw in (0.30, 0.50, 0.70, 0.90):
            p = {"asset_class": klass, "confidence": raw}
            calibrate(p)
            cal = p.get("confidence")
            tag = "CAL" if p.get("confidence_calibrated") else " - "
            print(f"  {klass:<10} raw={raw:.2f} -> {cal:.3f} [{tag}]")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        print("\nCommands:\n  fit    Fit per-class calibrators from closed picks\n"
              "  apply  Demo apply on synthetic picks (sets env flag)")
        return 0
    cmd = argv[0]
    if cmd == "fit":
        return _cmd_fit()
    if cmd == "apply":
        return _cmd_apply_demo()
    print(f"unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
