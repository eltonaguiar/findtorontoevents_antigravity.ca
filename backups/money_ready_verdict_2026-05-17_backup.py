"""
M-061: Unified money_ready_verdict() — wires DSR + PBO/CSCV + SPA into one per-class verdict.

Returns a per-asset-class readiness dict:
    {
        "COMMODITY": {
            "dsr_ok": True,
            "pbo_ok": True,
            "spa_ok": True,
            "n_ok": True,
            "n_resolved": 750,
            "verdict": "MONEY_READY",   # MONEY_READY | WATCH | NOT_READY | INSUFFICIENT_DATA
            "details": {...}
        },
        ...
    }

Verdicts:
    MONEY_READY     — all applicable gates pass (n_ok + at least dsr_ok or spa_ok)
    WATCH           — enough data, mixed signals (e.g. n_ok but pbo failed)
    NOT_READY       — enough data, edge not confirmed
    INSUFFICIENT_DATA — too few resolved picks for statistical testing

Usage:
    python alpha_engine/money_ready_verdict.py               # print report
    python alpha_engine/money_ready_verdict.py --json        # JSON output
    python alpha_engine/money_ready_verdict.py --class COMMODITY
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).parent.parent
# Ensure repo root and alpha_engine dir are importable regardless of how this file is invoked
import sys as _sys
for _p in [str(REPO_ROOT), str(Path(__file__).parent)]:
    if _p not in _sys.path:
        _sys.path.insert(0, _p)
CLOSED_PATH = REPO_ROOT / "alpha_engine/data/closed_picks.json"
DASHBOARD_PATH = REPO_ROOT / "audit_dashboard/data/dashboard_data.json"
GATES_PATH = REPO_ROOT / "audit_trail/quality_gates.py"

# Tier-2 floors per PERFORMANCE_CHARTER.md
MIN_N_CLASS = 50          # minimum resolved picks for a class verdict
MIN_WR = 0.50             # win-rate floor (generic)
MIN_PF = 1.5              # profit-factor floor
DSR_THRESHOLD = 0.95      # DSR probability threshold
PBO_THRESHOLD = 0.55      # PBO ≤ threshold means edge likely real (low overfit prob)
# PBO/CSCV requires ≥5 strategies to have meaningful overfit detection power
# (Bailey et al., 2016 — with <5 strategies the stat is essentially random)
MIN_STRATEGIES_FOR_PBO = 5
SPA_ALPHA = 0.10          # family-wise alpha for SPA (looser than per-strategy 0.05)
MIN_N_STRATEGY = 20       # minimum per-strategy picks for SPA inclusion

# Asset-class-specific WR floors (swarm Q1 recommendation 2026-05-17).
# EQUITY institutional benchmarks accept 52% as viable (lower WR compensated by PF≥1.5+).
# All other classes default to MIN_WR=50%.
MIN_WR_BY_CLASS: dict[str, float] = {
    "EQUITY": 0.52,
}


# ---------------------------------------------------------------------------
# Data loading (shared with whites_reality_check.py, deflated_sharpe.py)
# ---------------------------------------------------------------------------

def _load_blocked() -> set[str]:
    blocked: set[str] = set()
    if not GATES_PATH.exists():
        return blocked
    text = GATES_PATH.read_text(encoding="utf-8", errors="replace")
    in_block = False
    for line in text.splitlines():
        s = line.strip()
        if ("BLOCKED_SOURCE_SYSTEMS" in s or "BLOCKED_STRATEGIES" in s) and "=" in s:
            in_block = True
        elif in_block:
            if s.startswith("}"):
                in_block = False
                continue
            if s.startswith('"') or s.startswith("'"):
                name = s.split('"')[1] if '"' in s else s.split("'")[1]
                if name:
                    blocked.add(name)
    return blocked


def _load_picks() -> list[dict]:
    if not CLOSED_PATH.exists():
        return []
    return json.loads(CLOSED_PATH.read_text())


def _load_dashboard_health() -> dict[str, dict]:
    """Load asset_class_health from dashboard_data.json for fallback n/wr/pf."""
    if not DASHBOARD_PATH.exists():
        return {}
    try:
        dd = json.loads(DASHBOARD_PATH.read_text())
        return dd.get("performance", {}).get("asset_class_health", {})
    except Exception:
        return {}


def _resolved(picks: list[dict]) -> list[dict]:
    return [p for p in picks if str(p.get("status", "")).upper() in ("WON", "LOST")]


# ---------------------------------------------------------------------------
# Per-class aggregation
# ---------------------------------------------------------------------------

def _class_stats(picks: list[dict]) -> dict[str, dict]:
    blocked = _load_blocked()
    by_class: dict[str, list[dict]] = defaultdict(list)
    for p in _resolved(picks):
        strat = p.get("strategy") or p.get("source_system") or ""
        if strat in blocked:
            continue
        ac = str(p.get("asset_class") or "UNKNOWN").upper()
        by_class[ac].append(p)

    stats: dict[str, dict] = {}
    for ac, ps in by_class.items():
        n = len(ps)
        wins = sum(1 for p in ps if str(p.get("status", "")).upper() == "WON")
        wr = wins / n if n else 0.0
        gross_win = sum(float(p.get("pnl_pct") or 0) for p in ps if str(p.get("status", "")).upper() == "WON")
        gross_loss = abs(sum(float(p.get("pnl_pct") or 0) for p in ps if str(p.get("status", "")).upper() == "LOST"))
        pf = gross_win / gross_loss if gross_loss > 0 else float("inf")
        returns = [float(p.get("pnl_pct") or 0) for p in ps]
        stats[ac] = {
            "n": n,
            "wr": round(wr, 4),
            "pf": round(pf, 4),
            "returns": returns,
            "picks": ps,
        }
    return stats


# ---------------------------------------------------------------------------
# DSR gate (per-class aggregate — treat all class picks as one strategy)
# ---------------------------------------------------------------------------

def _dsr_gate(returns: list[float]) -> dict[str, Any]:
    try:
        try:
            from alpha_engine.deflated_sharpe import returns_stats, sharpe_variance, deflated_sharpe_ratio
        except ImportError:
            from deflated_sharpe import returns_stats, sharpe_variance, deflated_sharpe_ratio
    except ImportError:
        return {"ok": None, "note": "deflated_sharpe not importable", "dsr_score": None}

    arr = np.array(returns, dtype=float)
    if len(arr) < 10:
        return {"ok": None, "note": f"n={len(arr)} too small for DSR", "dsr_score": None}

    mu, sd = arr.mean(), arr.std()
    if sd == 0:
        return {"ok": False, "note": "zero variance returns", "dsr_score": 0.0}

    sr = mu / sd * np.sqrt(252)  # annualised daily SR approximation
    stats = returns_stats(list(returns))
    horizon = len(arr)
    sr_var = sharpe_variance(sr, horizon, stats["skewness"], stats["kurtosis"])
    # nb_trials=1 — we're testing the class aggregate, not a selected-best strategy
    dsr = deflated_sharpe_ratio(
        estimated_sharpe=sr,
        sr_variance=sr_var,
        nb_trials=1,
        backtest_horizon=horizon,
        skew=stats["skewness"],
        kurtosis=stats["kurtosis"],
    )
    return {"ok": dsr >= DSR_THRESHOLD, "dsr_score": round(dsr, 4), "note": ""}


# ---------------------------------------------------------------------------
# PBO gate (per-class aggregate: build strategy columns from top strategies)
# ---------------------------------------------------------------------------

def _pbo_gate(picks: list[dict]) -> dict[str, Any]:
    try:
        from tools.pbo_cscv import compute_pbo
    except ImportError:
        try:
            sys.path.insert(0, str(REPO_ROOT / "tools"))
            from pbo_cscv import compute_pbo
        except ImportError:
            return {"ok": None, "note": "pbo_cscv not importable", "pbo": None}

    blocked = _load_blocked()
    by_strat: dict[str, list[float]] = defaultdict(list)
    for p in picks:
        strat = p.get("strategy") or p.get("source_system") or ""
        if not strat or strat in blocked:
            continue
        try:
            by_strat[strat].append(float(p.get("pnl_pct") or 0))
        except (TypeError, ValueError):
            pass

    eligible = {k: v for k, v in by_strat.items() if len(v) >= MIN_N_STRATEGY}
    if len(eligible) < 2:
        return {"ok": None, "note": f"need ≥2 strategies with n≥{MIN_N_STRATEGY}, got {len(eligible)}", "pbo": None}
    # PBO/CSCV has near-zero power with <MIN_STRATEGIES_FOR_PBO strategies
    if len(eligible) < MIN_STRATEGIES_FOR_PBO:
        return {
            "ok": None,
            "note": f"n_strategies={len(eligible)} < {MIN_STRATEGIES_FOR_PBO} — PBO statistically unreliable (N/A)",
            "pbo": None,
            "n_strategies": len(eligible),
        }

    T_max = max(len(v) for v in eligible.values())
    rng = np.random.default_rng(42)
    mat = np.zeros((T_max, len(eligible)))
    for j, (_, rets) in enumerate(eligible.items()):
        r = np.array(rets, dtype=float)
        if len(r) < T_max:
            idx = rng.integers(0, len(r), size=T_max)
            r = r[idx]
        mat[:, j] = r

    result = compute_pbo(mat)
    pbo = result.get("pbo")
    ok = (pbo is not None) and (pbo <= PBO_THRESHOLD)
    return {"ok": ok, "pbo": round(pbo, 4) if pbo is not None else None, "n_strategies": len(eligible), "note": result.get("note", "")}


# ---------------------------------------------------------------------------
# SPA gate (family-wise — delegates to whites_spa_test)
# ---------------------------------------------------------------------------

def _spa_gate(picks: list[dict]) -> dict[str, Any]:
    try:
        tools_dir = str(REPO_ROOT / "tools")
        if tools_dir not in sys.path:
            sys.path.insert(0, tools_dir)
        from whites_reality_check import whites_spa_test
    except ImportError:
        return {"ok": None, "note": "whites_reality_check not importable", "spa_p": None}

    blocked = _load_blocked()
    by_strat: dict[str, list[float]] = defaultdict(list)
    for p in picks:
        strat = p.get("strategy") or p.get("source_system") or ""
        if not strat or strat in blocked:
            continue
        try:
            by_strat[strat].append(float(p.get("pnl_pct") or 0))
        except (TypeError, ValueError):
            pass

    eligible = {k: v for k, v in by_strat.items() if len(v) >= MIN_N_STRATEGY}
    if not eligible:
        return {"ok": None, "note": f"no strategies with n≥{MIN_N_STRATEGY}", "spa_p": None, "n_spa_pass": 0}

    result = whites_spa_test(eligible, n_boot=500, alpha=SPA_ALPHA)
    spa_p = result.get("family_p_spa")
    ok = (spa_p is not None) and (spa_p <= SPA_ALPHA)
    return {
        "ok": ok,
        "spa_p": round(spa_p, 4) if spa_p is not None else None,
        "n_spa_pass": result.get("n_spa_pass", 0),
        "n_strategies_tested": result.get("n_strategies", 0),
        "note": "",
    }


# ---------------------------------------------------------------------------
# Verdict logic
# ---------------------------------------------------------------------------

def _verdict(n: int, wr: float, pf: float, dsr: dict, pbo: dict, spa: dict, asset_class: str = "") -> str:
    n_ok = n >= MIN_N_CLASS
    if not n_ok:
        return "INSUFFICIENT_DATA"

    wr_floor = MIN_WR_BY_CLASS.get(asset_class.upper(), MIN_WR)
    wr_ok = wr >= wr_floor
    pf_ok = pf >= MIN_PF

    dsr_ok = dsr.get("ok") is True
    pbo_ok = pbo.get("ok") is True
    spa_ok = spa.get("ok") is True

    if wr_ok and pf_ok and (dsr_ok or spa_ok) and (pbo_ok or spa_ok):
        return "MONEY_READY"
    elif wr_ok or pf_ok:
        return "WATCH"
    else:
        return "NOT_READY"


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def money_ready_verdict(asset_class: str | None = None, n_boot: int = 500) -> dict[str, dict]:
    """Return per-class readiness verdict dict.

    When closed_picks.json has <MIN_N_CLASS picks for an asset class, the n/wr/pf
    from dashboard_data.json::asset_class_health is used as a fallback for display.
    Statistical tests (DSR/PBO/SPA) still require actual pick-level data and will
    show N/A when the closed_picks sample is too small.
    """
    picks = _load_picks()
    class_stats = _class_stats(picks)
    dash_health = _load_dashboard_health()

    # Include any classes in dashboard health that have no closed_picks data at all
    for ac_dash, health in dash_health.items():
        ac_up = ac_dash.upper()
        if ac_up not in class_stats:
            class_stats[ac_up] = {
                "n": health.get("n", 0),
                "wr": health.get("wr") or 0.0,
                "pf": health.get("pf") or 0.0,
                "returns": [],
                "picks": [],
                "_source": "dashboard_fallback",
            }

    results: dict[str, dict] = {}
    for ac, stats in class_stats.items():
        if asset_class and ac != asset_class.upper():
            continue

        n = stats["n"]
        wr = stats["wr"]
        pf = stats["pf"]
        returns = stats["returns"]
        ac_picks = stats["picks"]
        data_source = stats.get("_source", "closed_picks")

        # Dashboard fallback: if closed_picks n < MIN_N_CLASS but dashboard has more data,
        # use ALL dashboard n/wr/pf for verdict display (statistical tests still need pick data)
        if n < MIN_N_CLASS and ac in dash_health:
            h = dash_health[ac]
            dash_n = h.get("n", 0)
            if dash_n > n:
                n = dash_n
                # dashboard stores wr as percentage (53.3) in win_rate/wr_pct, or fraction in wr
                raw_wr = h.get("win_rate") or h.get("wr_pct") or h.get("wr") or 0
                wr = float(raw_wr) / 100 if float(raw_wr or 0) > 1 else float(raw_wr or 0)
                pf = float(h.get("pf") or h.get("profit_factor") or 0)
                data_source = "dashboard_fallback"

        dsr = _dsr_gate(returns)
        pbo = _pbo_gate(ac_picks)
        spa = _spa_gate(ac_picks)
        verdict = _verdict(n, wr, pf, dsr, pbo, spa, asset_class=ac)
        wr_floor = MIN_WR_BY_CLASS.get(ac.upper(), MIN_WR)

        results[ac] = {
            "n_resolved": n,
            "wr": round(wr, 4),
            "pf": round(pf, 4) if pf != float("inf") else None,
            "n_ok": n >= MIN_N_CLASS,
            "wr_ok": wr >= wr_floor,
            "pf_ok": pf >= MIN_PF,
            "dsr_ok": dsr.get("ok"),
            "dsr_score": dsr.get("dsr_score"),
            "pbo_ok": pbo.get("ok"),
            "pbo": pbo.get("pbo"),
            "spa_ok": spa.get("ok"),
            "spa_p": spa.get("spa_p"),
            "n_spa_pass": spa.get("n_spa_pass", 0),
            "verdict": verdict,
            "data_source": data_source,
            "details": {"dsr": dsr, "pbo": pbo, "spa": spa},
        }

    return results


def print_report(results: dict[str, dict]) -> None:
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print(f"# Money-Ready Verdict — {today}\n")
    print(f"{'Class':<12} {'n':>6} {'WR':>7} {'PF':>7} {'DSR':>6} {'PBO':>6} {'SPA':>6} {'Verdict':<18}")
    print("-" * 76)

    order = ["EQUITY", "COMMODITY", "CRYPTO", "ETF", "FOREX", "BOND", "FUTURES"]
    for ac in order + [k for k in results if k not in order]:
        if ac not in results:
            continue
        r = results[ac]
        dsr_str = "PASS" if r["dsr_ok"] is True else ("FAIL" if r["dsr_ok"] is False else "N/A")
        pbo_str = "PASS" if r["pbo_ok"] is True else ("FAIL" if r["pbo_ok"] is False else "N/A")
        spa_str = "PASS" if r["spa_ok"] is True else ("FAIL" if r["spa_ok"] is False else "N/A")
        pf_val = r["pf"]
        pf_str = f"{pf_val:7.2f}" if pf_val is not None else "    inf"
        src_tag = " [DASH]" if r.get("data_source") == "dashboard_fallback" else ""
        print(f"{ac:<12} {r['n_resolved']:>6} {r['wr']:>7.1%} {pf_str} {dsr_str:>6} {pbo_str:>6} {spa_str:>6} {r['verdict']:<18}{src_tag}")

    print("\n## Gate Thresholds")
    print(f"- n_ok: ≥{MIN_N_CLASS} resolved picks")
    print(f"- wr_ok: ≥{MIN_WR:.0%}")
    print(f"- pf_ok: ≥{MIN_PF}")
    print(f"- DSR: probability ≥{DSR_THRESHOLD}")
    print(f"- PBO: overfit probability ≤{PBO_THRESHOLD}")
    print(f"- SPA: family-wise p ≤{SPA_ALPHA} (α={SPA_ALPHA})")

    money_ready = [ac for ac, r in results.items() if r["verdict"] == "MONEY_READY"]
    watch = [ac for ac, r in results.items() if r["verdict"] == "WATCH"]
    print(f"\n**MONEY_READY:** {', '.join(money_ready) or 'none'}")
    print(f"**WATCH:** {', '.join(watch) or 'none'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="M-061: Unified money_ready_verdict()")
    parser.add_argument("--class", dest="asset_class", help="Filter to one asset class")
    parser.add_argument("--json", dest="as_json", action="store_true")
    args = parser.parse_args()

    results = money_ready_verdict(asset_class=args.asset_class)
    if args.as_json:
        print(json.dumps(results, indent=2))
    else:
        print_report(results)


if __name__ == "__main__":
    main()
