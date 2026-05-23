"""
Improvement Cycle — Consolidated quality-analysis runner.

Runs every 30 minutes (via GH Actions or locally) and produces a single
health-score report by orchestrating all quality sub-modules:

  1. check_active_picks  — score-PnL correlation, top gainers, anomalies
  2. decile_test          — score-WR stratification (Spearman)
  3. ic_weighted_selector — per-strategy Information Coefficients
  4. regime_flip_detector — current regime + confidence
  5. forward_test_portfolios — 8 portfolio PnLs
  6. GitHub Actions        — failed workflow detection
  7. feature_health        — feature population %

Output: alpha_engine/data/improvement_cycle_report.json (history capped at 500)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

# ── Windows UTF-8 fix ──────────────────────────────────────────────────────
if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / "alpha_engine"
DATA_DIR = ENGINE / "data"
REPORT_PATH = DATA_DIR / "improvement_cycle_report.json"
HISTORY_CAP = 500

# Ensure sys.path includes the repo root so sibling imports work
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ENGINE) not in sys.path:
    sys.path.insert(0, str(ENGINE))


# ── Helpers ────────────────────────────────────────────────────────────────
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path, default=None):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default if default is not None else {}


def _save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# ── Step runners ───────────────────────────────────────────────────────────

def step_check_active_picks() -> dict:
    """Step 1: Score-PnL correlation, top gainers, anomalies."""
    from alpha_engine.check_active_picks import run as cap_run
    result = cap_run()
    return result or {}


def step_decile_test() -> dict:
    """Step 2: Score-WR decile stratification."""
    from alpha_engine.decile_test import run as dt_run
    dt_run()  # saves to decile_test.json, returns None
    return _load_json(DATA_DIR / "decile_test.json", {})


def step_ic_weights() -> dict:
    """Step 3: Information Coefficient analysis."""
    from alpha_engine.ic_weighted_selector import run as ic_run
    result = ic_run()
    return result or {}


def step_regime() -> dict:
    """Step 4: Regime detection + confidence."""
    from alpha_engine.regime_flip_detector import (
        run as regime_run,
        get_regime_confidence,
        load_last_regime,
    )
    flipped = regime_run()
    regime = load_last_regime() or "UNKNOWN"
    confidence = get_regime_confidence(regime)
    return {
        "regime": regime,
        "flipped": bool(flipped),
        "confidence": confidence,
    }


def step_forward_portfolios() -> dict:
    """Step 5: Update all 8 forward-test portfolios."""
    from alpha_engine.forward_test_portfolios import run as ftp_run
    state = ftp_run()
    if not state or not isinstance(state, dict):
        return {}
    # Extract summary per portfolio
    summary = {}
    for name, portfolio in state.items():
        if not isinstance(portfolio, dict):
            continue
        summary[name] = {
            "equity": portfolio.get("equity", 10000),
            "pnl_pct": round(
                (portfolio.get("equity", 10000) / 10000 - 1) * 100, 2
            ),
            "open_positions": len(portfolio.get("open_positions", [])),
            "closed_count": len(portfolio.get("closed_positions", [])),
        }
    return summary


def step_github_actions() -> dict:
    """Step 6: Check for failed GitHub Actions workflows."""
    try:
        result = subprocess.run(
            ["gh", "run", "list", "--branch", "main", "--limit", "20",
             "--json", "name,status,conclusion,createdAt"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return {"error": f"gh cli failed: {result.stderr[:200]}"}

        runs = json.loads(result.stdout) if result.stdout.strip() else []
        failed = [
            {"name": r.get("name"), "created": r.get("createdAt")}
            for r in runs
            if r.get("conclusion") == "failure"
        ]
        return {
            "total_checked": len(runs),
            "failed_count": len(failed),
            "failed_runs": failed[:5],  # cap detail
        }
    except FileNotFoundError:
        return {"error": "gh CLI not found"}
    except Exception as e:
        return {"error": str(e)[:200]}


def step_feature_health() -> dict:
    """Step 7: Feature population / health."""
    from alpha_engine.feature_health import generate_health_report
    report = generate_health_report()
    return report or {}


# ── Health Score Calculator ────────────────────────────────────────────────

def compute_health_score(metrics: dict) -> tuple[int, dict]:
    """
    Compute 0-100 health score from sub-metrics.

    Returns (score, breakdown) where breakdown explains each component.
    """
    breakdown = {}
    score = 0

    # 1. Score-PnL Spearman > 0.10  → +20
    cap = metrics.get("check_active_picks", {})
    spearman = (
        cap.get("score_pnl_correlation", {}).get("spearman_r")
        or cap.get("summary", {}).get("score_pnl_spearman", 0)
        or 0
    )
    pts = 20 if spearman > 0.10 else int(max(0, spearman / 0.10 * 20))
    breakdown["score_pnl_spearman"] = {
        "value": round(spearman, 4), "threshold": ">0.10",
        "points": pts, "max": 20,
    }
    score += pts

    # 2. Decile monotonicity (D10 WR > D1 WR)  → +15
    decile = metrics.get("decile_test", {})
    overall = decile.get("overall", {})
    deciles = overall.get("deciles", [])
    d1_wr = deciles[0].get("win_rate", 0) if len(deciles) >= 1 else 0
    d10_wr = deciles[-1].get("win_rate", 0) if len(deciles) >= 1 else 0
    monotonic = d10_wr > d1_wr
    pts = 15 if monotonic and (d10_wr - d1_wr) > 5 else (8 if monotonic else 0)
    breakdown["decile_monotonicity"] = {
        "d1_wr": round(d1_wr, 2), "d10_wr": round(d10_wr, 2),
        "monotonic": monotonic, "points": pts, "max": 15,
    }
    score += pts

    # 3. Top trader WR > 60%  → +15
    top_wr = cap.get("summary", {}).get("top_trader_wr", 0) or 0
    # Also try top_gainers section
    if not top_wr:
        tg = cap.get("top_gainers", {})
        top_wr = tg.get("top_trader_wr", 0) or 0
    pts = 15 if top_wr > 60 else int(max(0, top_wr / 60 * 15))
    breakdown["top_trader_wr"] = {
        "value": round(top_wr, 2), "threshold": ">60%",
        "points": pts, "max": 15,
    }
    score += pts

    # 4. Regime confidence > 0.7  → +10
    regime_data = metrics.get("regime", {})
    conf = regime_data.get("confidence", {})
    # Use the max of long_conf and short_conf as overall confidence
    regime_conf = max(
        conf.get("long_conf", 0),
        conf.get("short_conf", 0),
        conf.get("confidence", 0),
    ) if isinstance(conf, dict) else 0
    pts = 10 if regime_conf > 0.7 else int(max(0, regime_conf / 0.7 * 10))
    breakdown["regime_confidence"] = {
        "regime": regime_data.get("regime", "UNKNOWN"),
        "confidence": round(regime_conf, 3),
        "threshold": ">0.7", "points": pts, "max": 10,
    }
    score += pts

    # 5. Forward portfolios net positive  → +15
    ftp = metrics.get("forward_portfolios", {})
    if ftp and not ftp.get("error"):
        positive = sum(1 for v in ftp.values()
                       if isinstance(v, dict) and v.get("pnl_pct", 0) > 0)
        total_p = max(1, len([v for v in ftp.values() if isinstance(v, dict)]))
        pct_positive = positive / total_p
        pts = 15 if pct_positive > 0.5 else int(pct_positive / 0.5 * 15)
    else:
        pts = 0
        positive, total_p, pct_positive = 0, 0, 0
    breakdown["forward_portfolios_positive"] = {
        "positive": positive, "total": total_p,
        "pct_positive": round(pct_positive, 2) if total_p else 0,
        "points": pts, "max": 15,
    }
    score += pts

    # 6. No GH Actions failures  → +10
    gha = metrics.get("github_actions", {})
    failed_count = gha.get("failed_count", 0)
    if gha.get("error"):
        pts = 5  # can't check, give half credit
    else:
        pts = 10 if failed_count == 0 else max(0, 10 - failed_count * 2)
    breakdown["github_actions"] = {
        "failed_count": failed_count,
        "points": pts, "max": 10,
    }
    score += pts

    # 7. Feature population > 30%  → +15
    fh = metrics.get("feature_health", {})
    health_score = fh.get("health_score", 0)
    if isinstance(health_score, (int, float)):
        pop_pct = health_score * 100 if health_score <= 1 else health_score
    else:
        pop_pct = 0
    pts = 15 if pop_pct > 30 else int(max(0, pop_pct / 30 * 15))
    breakdown["feature_population"] = {
        "value_pct": round(pop_pct, 1), "threshold": ">30%",
        "points": pts, "max": 15,
    }
    score += pts

    return min(score, 100), breakdown


# ── Trend Detection ────────────────────────────────────────────────────────

def compute_trend(current_score: int, history: list[dict]) -> str:
    """Compare current score to recent history to determine trend."""
    if len(history) < 3:
        return "insufficient_data"

    recent = history[-5:]  # last 5 entries
    recent_scores = [e.get("health_score", 0) for e in recent]
    avg_recent = sum(recent_scores) / len(recent_scores) if recent_scores else 0

    if current_score > avg_recent + 3:
        return "improving"
    elif current_score < avg_recent - 3:
        return "declining"
    return "stable"


# ── Actionable Summary ────────────────────────────────────────────────────

def generate_summary(health_score: int, breakdown: dict, trend: str) -> list[str]:
    """Generate actionable bullet points."""
    lines = []

    if trend == "improving":
        lines.append("[+] System health is IMPROVING (score trending up)")
    elif trend == "declining":
        lines.append("[!] System health is DECLINING (score trending down)")
    elif trend == "stable":
        lines.append("[=] System health is STABLE")

    # Highlight weak areas (< 50% of max)
    weak = []
    strong = []
    for key, info in breakdown.items():
        pct = info["points"] / info["max"] if info["max"] > 0 else 0
        if pct < 0.5:
            weak.append((key, info))
        elif pct >= 0.8:
            strong.append((key, info))

    if strong:
        names = ", ".join(k for k, _ in strong)
        lines.append(f"[+] Strong: {names}")

    if weak:
        for key, info in weak:
            lines.append(
                f"[!] Needs attention: {key} — "
                f"{info['points']}/{info['max']} pts"
            )

    # Specific advice
    sp = breakdown.get("score_pnl_spearman", {})
    if sp.get("points", 0) < 10:
        lines.append(
            f"    -> Score-PnL Spearman={sp.get('value', 0):.4f}, "
            f"target >0.10. Review scoring weights."
        )

    dm = breakdown.get("decile_monotonicity", {})
    if not dm.get("monotonic", True):
        lines.append(
            "    -> D10 WR <= D1 WR: score is NOT separating winners. "
            "Run ic_weighted_selector to find anti-predictive components."
        )

    gha = breakdown.get("github_actions", {})
    if gha.get("failed_count", 0) > 0:
        lines.append(
            f"    -> {gha['failed_count']} failed GH Actions. "
            f"Run: gh run list --branch main --status failure"
        )

    fp = breakdown.get("feature_population", {})
    if fp.get("points", 0) < 8:
        lines.append(
            f"    -> Feature population at {fp.get('value_pct', 0):.0f}%. "
            f"Run backfill_features.py to improve."
        )

    return lines


# ── Main Runner ────────────────────────────────────────────────────────────

def run() -> dict:
    """Execute all quality-analysis modules and produce consolidated report."""
    print("=" * 70)
    print(f"  IMPROVEMENT CYCLE  |  {_now_iso()}")
    print("=" * 70)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    metrics = {}
    errors = {}

    # Define steps with names
    steps = [
        ("check_active_picks", step_check_active_picks),
        ("decile_test", step_decile_test),
        ("ic_weights", step_ic_weights),
        ("regime", step_regime),
        ("forward_portfolios", step_forward_portfolios),
        ("github_actions", step_github_actions),
        ("feature_health", step_feature_health),
    ]

    for name, func in steps:
        print(f"\n{'─'*60}")
        print(f"  Step: {name}")
        print(f"{'─'*60}")
        try:
            metrics[name] = func()
            print(f"  -> {name}: OK")
        except Exception as e:
            tb = traceback.format_exc()
            print(f"  -> {name}: FAILED — {e}")
            errors[name] = {"error": str(e), "traceback": tb[-500:]}
            metrics[name] = {"error": str(e)}

    # ── Compute health score ──
    print(f"\n{'='*70}")
    print("  HEALTH SCORE COMPUTATION")
    print(f"{'='*70}")

    health_score, breakdown = compute_health_score(metrics)
    print(f"\n  HEALTH SCORE: {health_score}/100")
    for key, info in breakdown.items():
        print(f"    {key}: {info['points']}/{info['max']} pts")

    # ── Load history + compute trend ──
    existing = _load_json(REPORT_PATH, {})
    history = existing.get("history", [])
    trend = compute_trend(health_score, history)

    # ── Actionable summary ──
    print(f"\n{'='*70}")
    print("  ACTIONABLE SUMMARY")
    print(f"{'='*70}")
    summary_lines = generate_summary(health_score, breakdown, trend)
    for line in summary_lines:
        print(f"  {line}")
    print()

    # ── Build report ──
    report_entry = {
        "timestamp": _now_iso(),
        "health_score": health_score,
        "trend": trend,
        "breakdown": breakdown,
        "errors": errors if errors else None,
        "summary": summary_lines,
    }

    # Append to history (capped)
    history.append(report_entry)
    if len(history) > HISTORY_CAP:
        history = history[-HISTORY_CAP:]

    # Full report with latest + history
    full_report = {
        "latest": report_entry,
        "history": history,
        "metrics_snapshot": {
            k: _slim_metrics(v) for k, v in metrics.items()
        },
    }

    _save_json(REPORT_PATH, full_report)
    print(f"  Report saved to: {REPORT_PATH}")
    print(f"  History entries: {len(history)}")
    print(f"\n{'='*70}")
    print("  IMPROVEMENT CYCLE COMPLETE")
    print(f"{'='*70}\n")

    return full_report


def _slim_metrics(data: dict) -> dict:
    """Keep metrics snapshot small — strip large nested structures."""
    if not isinstance(data, dict):
        return data
    # For forward portfolios, keep only summary
    slimmed = {}
    for k, v in data.items():
        if isinstance(v, (str, int, float, bool, type(None))):
            slimmed[k] = v
        elif isinstance(v, dict) and len(json.dumps(v, default=str)) < 2000:
            slimmed[k] = v
        elif isinstance(v, list) and len(v) < 20:
            slimmed[k] = v
        else:
            slimmed[k] = f"<{type(v).__name__}, len={len(v) if hasattr(v, '__len__') else '?'}>"
    return slimmed


# ── Entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    run()
