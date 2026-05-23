#!/usr/bin/env python3
"""Walk-forward edge-stability harness.

THE GATE. A scoring signal is admissible to the pick gate ONLY if its ability
to separate winners from losers is *stable across time* — not a one-window
fluke. Three independent autopsies (Claude, Grok, codebuff — 2026-05-17) all
found the same trap: `method_a_score` separates winners in the last 14 days
(eff 1.14) but inverts in the prior window (eff 0.42, wrong sign). In-sample
`eff` is worthless; only walk-forward stability counts.

For each score field this harness:
  1. buckets resolved picks into consecutive 14-day windows,
  2. per window computes the signed standardised gap
     eff = (mean_score|WON - mean_score|LOST) / pooled_sd,
  3. verdicts the score ADMISSIBLE iff |eff| >= EFF_MIN with the SAME sign in
     at least MIN_STABLE_WINDOWS qualifying windows.

A score that flips sign, or is sub-threshold, is noise — it must not rank or
gate picks. `is_admissible()` is importable as the gate other code should call
before trusting any score.

    python tools/edge_stability_harness.py [--all] [--field method_a_score]
                                           [--window-days 14] [--json]
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLOSED = ROOT / "alpha_engine" / "data" / "closed_picks.json"
PF_REGISTRY = ROOT / "audit_dashboard" / "data" / "pf_registry.json"

SCORE_FIELDS = ("confidence", "elite_score", "ml_score", "ml_composite_score",
                "method_a_score", "forward_wr", "risk_reward")

EFF_MIN = 0.30           # standardised gap below which a window carries no signal
MIN_WINDOW_N = 80        # a window with fewer resolved picks is not scored
MIN_STABLE_WINDOWS = 3   # qualifying windows that must agree (eff>=EFF_MIN, same sign)

# Confidence values >1.0 are a percent-as-integer encoding bug; exclude them so
# corrupted rows do not poison the scorer.
_CONFIDENCE_MAX = 1.0


def _load_one(path: Path) -> list[dict]:
    """Load picks from one closed_picks file; return [] on any error."""
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
        picks = d if isinstance(d, list) else d.get(
            "picks", d.get("closed", d.get("trades", [])))
        if not isinstance(picks, list):
            return []
        return [p for p in picks if isinstance(p, dict)]
    except Exception:
        return []


def _load() -> list[dict]:
    """Load resolved picks from all pf_registry source files (canonical view).

    Falls back to the single CLOSED file if pf_registry is absent.
    Confidence values >1.0 are stripped (percent-as-integer encoding bug).
    """
    all_picks: list[dict] = []
    if PF_REGISTRY.exists():
        try:
            reg = json.loads(PF_REGISTRY.read_text(encoding="utf-8"))
            for sf in reg.get("source_files", []):
                fpath = ROOT / sf["file"]
                if fpath.exists():
                    all_picks.extend(_load_one(fpath))
        except Exception:
            pass
    if not all_picks:
        all_picks = _load_one(CLOSED)

    # Strip corrupted confidence values (percent-as-integer: 15–78 observed)
    cleaned: list[dict] = []
    for p in all_picks:
        c = p.get("confidence")
        if c is not None:
            try:
                if float(c) > _CONFIDENCE_MAX:
                    p = dict(p)
                    del p["confidence"]
            except (TypeError, ValueError):
                pass
        cleaned.append(p)
    return cleaned


def _rdate(p: dict) -> str:
    return str(p.get("resolved_at") or p.get("exit_date") or p.get("timestamp") or "")[:10]


_RESOLVED_STATUSES = frozenset({"WON", "LOST", "CLOSED", "EXPIRED", "SL_HIT", "TP_HIT",
                                "SL_HIT_REPLAY", "TP_HIT_REPLAY", "RESOLVE_FAILED",
                                "RESOLVE_FAILED_BREAKEVEN", "RESOLVE_FAILED_MAX_RETRIES"})


def _won(p: dict):
    s = str(p.get("status") or "").upper()
    if s == "WON":
        return True
    if s in ("LOST", "SL_HIT", "SL_HIT_REPLAY"):
        return False
    # Exclude unresolved picks entirely (status="?", "OPEN", "ACTIVE", etc.)
    # so they don't pollute the WON/LOST ratio as phantom losses.
    if s and s not in _RESOLVED_STATUSES:
        return None
    v = p.get("pnl_pct")
    if v is None:
        return None  # no outcome data → exclude from analysis
    try:
        return float(v) > 0
    except (TypeError, ValueError):
        return None


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _regime(p: dict) -> str:
    """Market-regime label for a pick, or '' if untagged."""
    return str(p.get("regime") or p.get("market_regime") or "").strip()


def _windows(picks: list[dict], window_days: int) -> list[list[dict]]:
    """Bucket dated picks into consecutive windows, newest = window 0."""
    dated = [(p, _rdate(p)) for p in picks if _rdate(p)]
    if not dated:
        return []
    latest = date.fromisoformat(max(d for _, d in dated))
    buckets: dict[int, list[dict]] = {}
    for p, ds in dated:
        try:
            age = (latest - date.fromisoformat(ds)).days
        except ValueError:
            continue
        buckets.setdefault(age // window_days, []).append(p)
    return [buckets[k] for k in sorted(buckets)]


def _window_eff(window: list[dict], field: str):
    """Signed standardised gap for one score in one window, or None."""
    won = [v for v in (_num(p.get(field)) for p in window if _won(p) is True) if v is not None]
    lost = [v for v in (_num(p.get(field)) for p in window if _won(p) is False) if v is not None]
    if len(won) < 15 or len(lost) < 15:
        return None
    mw, ml = statistics.mean(won), statistics.mean(lost)
    sd = statistics.pstdev(won + lost) or 1e-9
    return round((mw - ml) / sd, 3)   # signed: + means winners score higher


def evaluate(field: str, window_days: int = 14) -> dict:
    """Walk-forward stability verdict for one score field."""
    wins = [w for w in _windows(_load(), window_days) if len(w) >= MIN_WINDOW_N]
    effs = []
    for i, w in enumerate(wins):
        e = _window_eff(w, field)
        effs.append({"window": i, "n": len(w), "eff": e})
    scored = [r for r in effs if r["eff"] is not None]
    strong = [r for r in scored if abs(r["eff"]) >= EFF_MIN]
    pos = [r for r in strong if r["eff"] > 0]
    neg = [r for r in strong if r["eff"] < 0]
    # admissible only if a single sign dominates with enough strong windows
    same_sign = pos if len(pos) >= len(neg) else neg
    admissible = len(same_sign) >= MIN_STABLE_WINDOWS and len(same_sign) == len(strong)
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
            f"({len(pos)}+/{len(neg)}-); needs {MIN_STABLE_WINDOWS} same-sign"
            if (pos and neg) else
            f"REJECTED — only {len(strong)}/{len(scored)} windows reach eff>={EFF_MIN}"
        ),
    }


def evaluate_by_regime(field: str, window_days: int = 14) -> dict:
    """Regime-conditional verdict.

    The plain `evaluate()` requires ONE global sign across all windows, so it
    structurally REJECTS a regime-dependent edge (positive in risk-on windows,
    negative in risk-off). Most real edge is regime-conditional. This stratifies
    resolved picks by their `regime` label and runs the same per-window
    stability test *inside each regime cohort*: the field is regime-admissible
    if it is same-sign stable across >= MIN_STABLE_WINDOWS windows within at
    least one regime.

    Returns verdict DATA_GAP when the ledger is not regime-tagged — the
    closed-pick ledger must first be backfilled with a `regime` field at each
    pick's resolve-date (regime_terminal HMM). Until then this is a no-op gate.
    """
    tagged = [(p, _regime(p)) for p in _load()]
    tagged = [(p, rg) for p, rg in tagged if rg]
    regimes = sorted({rg for _, rg in tagged})
    if len(regimes) < 2 or len(tagged) < MIN_WINDOW_N:
        return {
            "field": field,
            "mode": "regime",
            "verdict": "DATA_GAP",
            "regime_admissible": False,
            "regimes_found": regimes,
            "n_tagged": len(tagged),
            "per_regime": [],
            "reason": (
                f"DATA_GAP — only {len(tagged)} resolved picks carry a `regime` "
                f"label across {len(regimes)} regime(s). Backfill `regime` onto "
                f"closed_picks.json at resolve-date (regime_terminal HMM) before "
                f"regime-conditional admissibility can be evaluated."
            ),
        }
    per_regime = []
    for rg in regimes:
        cohort = [p for p, r in tagged if r == rg]
        wins = [w for w in _windows(cohort, window_days) if len(w) >= MIN_WINDOW_N]
        effs = [{"window": i, "n": len(w), "eff": _window_eff(w, field)}
                for i, w in enumerate(wins)]
        scored = [r for r in effs if r["eff"] is not None]
        strong = [r for r in scored if abs(r["eff"]) >= EFF_MIN]
        pos = [r for r in strong if r["eff"] > 0]
        neg = [r for r in strong if r["eff"] < 0]
        same_sign = pos if len(pos) >= len(neg) else neg
        adm = len(same_sign) >= MIN_STABLE_WINDOWS and len(same_sign) == len(strong)
        per_regime.append({
            "regime": rg,
            "n": len(cohort),
            "windows_scored": len(scored),
            "windows_strong": len(strong),
            "strong_positive": len(pos),
            "strong_negative": len(neg),
            "sign": ("+" if (adm and same_sign and same_sign[0]["eff"] > 0)
                     else "-" if (adm and same_sign) else "mixed"),
            "admissible": adm,
            "per_window_eff": effs,
        })
    winners = [r["regime"] for r in per_regime if r["admissible"]]
    return {
        "field": field,
        "mode": "regime",
        "verdict": "REGIME_ADMISSIBLE" if winners else "REJECTED",
        "regime_admissible": bool(winners),
        "admissible_regimes": winners,
        "regimes_found": regimes,
        "per_regime": per_regime,
        "reason": (
            f"REGIME-ADMISSIBLE within {winners} — stable same-sign separation "
            f"inside that regime cohort"
            if winners else
            f"REJECTED — no regime cohort ({len(regimes)} checked) shows stable "
            f"same-sign separation"
        ),
    }


def is_admissible(field: str, window_days: int = 14, regime: bool = False) -> bool:
    """Gate other code should call before trusting a score to rank/filter.

    regime=True uses regime-conditional admissibility (stable within at least
    one market regime). Default is the stricter global verdict — unchanged, so
    every existing caller is unaffected.
    """
    if regime:
        return evaluate_by_regime(field, window_days)["regime_admissible"]
    return evaluate(field, window_days)["admissible"]


def get_admissibility_badge(window_days: int = 14) -> dict[str, dict]:
    """Return a mapping of every score field → its harness admissibility verdict.

    Importable by dashboard generators, quality gates, or any code that needs
    to know which scores are harness-verified before ranking or gating picks.

    Example return:
        {
            "risk_reward": {"admissible": True,  "sign": "-", "windows_strong": 3, ...},
            "confidence":  {"admissible": False, "sign": "mixed", ...},
            ...
        }

    The 'admissible' bool is the single gate: if False, that score should NOT
    be used to rank picks, set thresholds, or drive conviction tiers.
    """
    badge: dict[str, dict] = {}
    for field in SCORE_FIELDS:
        result = evaluate(field, window_days)
        eff_trend = [
            e["eff"] for e in result["per_window_eff"]
            if e["eff"] is not None
        ]
        badge[field] = {
            "field": result["field"],
            "admissible": result["admissible"],
            "sign": result["sign"],
            "reason": result["reason"],
            "windows_scored": result["windows_scored"],
            "windows_strong": result["windows_strong"],
            "strong_positive": result["strong_positive"],
            "strong_negative": result["strong_negative"],
            "eff_trend": eff_trend,
        }
    return badge


def admissible_scores(window_days: int = 14) -> list[str]:
    """Convenience: return list of score field names that are harness-admissible.

    If empty, no existing score should gate picks — every candidate signal
    must clear this harness before it is trusted.
    """
    badge = get_admissibility_badge(window_days)
    return [k for k, v in badge.items() if v["admissible"]]


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--field", default=None)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--window-days", type=int, default=14)
    ap.add_argument("--json", dest="as_json", action="store_true")
    ap.add_argument("--regime", action="store_true",
                    help="regime-conditional admissibility (stratify by `regime`)")
    args = ap.parse_args()

    fields = [args.field] if args.field else list(SCORE_FIELDS)
    if args.regime:
        results = [evaluate_by_regime(f, args.window_days) for f in fields]
    else:
        results = [evaluate(f, args.window_days) for f in fields]

    if args.as_json:
        print(json.dumps(results, indent=2))
        return 0

    if args.regime:
        print(f"# Edge-Stability Harness — REGIME-CONDITIONAL — "
              f"{args.window_days}-day walk-forward\n")
        for r in results:
            print(f"{r['field']:<20} [{r['verdict']:^18}] {r['reason']}")
            for pr in r.get("per_regime", []):
                effs = " ".join(
                    (f"{e['eff']:+.2f}" if e["eff"] is not None else "  n/a")
                    for e in pr["per_window_eff"])
                tag = "ADMISSIBLE" if pr["admissible"] else "rejected"
                print(f"{'':<4}{pr['regime']:<16} n={pr['n']:<5} "
                      f"[{tag:^10}] effs: {effs}")
        adm = [r["field"] for r in results if r["regime_admissible"]]
        print(f"\nREGIME-ADMISSIBLE scores: {adm or 'NONE'}")
        return 0

    print(f"# Edge-Stability Harness — {args.window_days}-day walk-forward")
    print(f"# admissible iff |eff|>={EFF_MIN} same-sign in >={MIN_STABLE_WINDOWS} windows\n")
    for r in results:
        effs = " ".join(
            (f"{e['eff']:+.2f}" if e["eff"] is not None else "  n/a")
            for e in r["per_window_eff"])
        flag = "ADMISSIBLE" if r["admissible"] else "REJECTED"
        print(f"{r['field']:<20} [{flag:^10}] effs(new->old): {effs}")
        print(f"{'':<20}  {r['reason']}")
    adm = [r["field"] for r in results if r["admissible"]]
    print(f"\nADMISSIBLE scores: {adm or 'NONE'}")
    if not adm:
        print("=> No existing score may rank or gate picks. Every candidate "
              "signal must clear this harness before it is trusted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
