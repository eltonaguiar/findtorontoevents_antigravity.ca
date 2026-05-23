#!/usr/bin/env python3
"""
Hedge-Fund Level Pick Quality Validator
=========================================
Validates active picks against EMPIRICALLY CALIBRATED institutional thresholds.

Thresholds derived from 4,005 closed picks (alpha_engine + STOCKS combined):

  WHAT ACTUALLY PREDICTS WIN RATE:
  ┌─────────────────────────────┬──────┬──────────┐
  │ Signal                      │  WR  │  n picks │
  ├─────────────────────────────┼──────┼──────────┤
  │ Confidence 0.80-0.90        │  77% │   83     │  ← STRONGEST SIGNAL
  │ Confidence 0.70-0.80        │  36% │  193     │
  │ Confidence 0.60-0.70        │  22% │ 1952     │  ← danger zone
  │ RR 1.0-1.5                  │  56% │  176     │  ← tighter TP hits
  │ RR 1.5-2.0                  │  44% │  131     │
  │ RR 2.0-2.5                  │  25% │  532     │  ← TP too far, never hit
  │ Elite 40-60                 │  37% │  152     │
  │ Elite 20-40                 │   8% │  202     │  ← anti-predictive!
  │ Elite < 20                  │  27% │  135     │
  └─────────────────────────────┴──────┴──────────┘

  KEY INSIGHT: RR 2.0+ has LOWER WR than RR 1.0-1.5 because TP targets are
  too ambitious — they rarely get hit before SL triggers. High RR sounds
  rigorous but destroys edge in practice.

  HIGH CONVICTION BUTTON: passes picks with hf_conviction_tier S/A/B, which
  requires 4-of-5 data-driven criteria (conf≥0.8, elite≥60, ml≥0.85, rr≥1.2, mc_verified).

Usage:
    python audit_trail/hf_pick_validator.py [--file alpha_engine/data/active_picks.json]
    python audit_trail/hf_pick_validator.py --all     # validate all pick files
    python audit_trail/hf_pick_validator.py --report  # write JSON report

Stdlib only (no numpy/pandas). Safe to import in any step.
"""

from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

_REPO = Path(__file__).resolve().parent.parent

if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

# ---------------------------------------------------------------------------
# DATA-CALIBRATED Thresholds (from 4,005 real closed picks)
# ---------------------------------------------------------------------------

# HF tier: picks the dashboard "High Conviction" button should show
HF_MIN_CONFIDENCE = 0.75    # 0.80 bucket = 77% WR; 0.75 is minimum viable
HF_MIN_ELITE      = 50      # Calibrated: elite 40-60 → 37% WR (acceptable)
HF_MIN_EMPIRICAL_WR = 0.40  # 40% empirical WR from Bayes-shrunk strategy history
HF_MIN_RR         = 1.1     # Data shows RR 1-1.5 → 56% WR; 1.1 is the floor
HF_MAX_RR         = 2.5     # RR > 2.5 has 31% WR — TP too ambitious
HF_MAX_FRESHNESS_H  = 48    # Reject stale picks (> 48h)
HF_MAX_SYMBOL_CONCENTRATION = 3  # Max simultaneous picks per symbol

# Active tier: minimum survivability (not blocked, not obviously wrong)
ACTIVE_MIN_CONFIDENCE = 0.55
ACTIVE_MIN_RR         = 0.8   # Positive risk/reward floor
ACTIVE_MIN_ELITE      = 30

# Danger zone: confidence 0.6-0.7 has only 22% WR — flag for review
CONFIDENCE_DANGER_LOW  = 0.60
CONFIDENCE_DANGER_HIGH = 0.70

# Strategies that are hard-blocked
_BLOCKED_STRATEGIES = frozenset({
    "claude_gainer_ml", "claude_gainer_ml_perf",
    "yahoo_analyst_consensus",
    "community_london_breakout_v2_forex",
    "forex_logistic_direction",
    "futures_ema_stack_momentum",  # 0/4=0% WR, 7 zombie picks — killed 2026-04-02
    "ema_stack_momentum",            # bare variant (multi_asset/scanner.py), 21.4% WR n=14 — killed
})

# Strategies with proven edge in closed-book (auto bonus)
_PROVEN_STRATEGIES = frozenset({
    "crypto_rsi_whaleconfirmed_v1", "funding_momentum",
    "crypto_keltner_compression_expansion",
    "crypto_vwap_deviation_reversion_vol",
    "multi_period_rsi_confluence", "drawdown_recovery_rsi",
    "ml_enhanced_FETUSDT_1d_B_lightgbm",      # 85% WR in closed picks
    "ml_enhanced_BNBUSDT_15m_B_lightgbm",     # 89% WR in closed picks
    "ml_enhanced_RENDERUSDT_1h_D_ensemble_stack",  # 72% WR in closed picks
})

# ---------------------------------------------------------------------------
# Empirical Bayes win prob (inline — no external dep)
# ---------------------------------------------------------------------------

def _load_closed_for_eb() -> list:
    """Load closed picks from the largest available source."""
    sources = [
        _REPO / "alpha_engine" / "data" / "closed_picks.json",
        _REPO / "STOCKS" / "competition" / "forward_picks.json",
    ]
    merged = []
    terminal = {"WON", "LOST", "CLOSED", "EXPIRED"}
    seen = set()
    for path in sources:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_bytes())
            if isinstance(data, dict):
                data = data.get("picks", [])
            for p in data:
                if not isinstance(p, dict):
                    continue
                if str(p.get("status", "")).upper() not in terminal:
                    continue
                pid = str(p.get("id", id(p)))
                if pid not in seen:
                    seen.add(pid)
                    merged.append(p)
        except Exception:
            continue
    return merged


def _is_won(p: dict) -> bool:
    status = str(p.get("status", "")).upper()
    if status == "WON":
        return True
    if status in ("LOST", "EXPIRED"):
        return False
    exit_r = str(p.get("exit_reason", "")).upper()
    if "TP" in exit_r:
        return True
    if "SL" in exit_r:
        return False
    pnl = p.get("pnl_pct")
    return float(pnl) > 0 if pnl is not None else False


_EB_CACHE: dict | None = None


def _get_strategy_wr(strategy: str, closed: list) -> tuple[float, int]:
    """Return (win_rate, n_trades) for a strategy from closed trade history."""
    global _EB_CACHE
    if _EB_CACHE is None:
        _EB_CACHE = {}
        strat_wins: dict[str, int] = defaultdict(int)
        strat_total: dict[str, int] = defaultdict(int)
        for p in closed:
            s = p.get("strategy") or p.get("algorithm") or ""
            if s:
                strat_total[s] += 1
                if _is_won(p):
                    strat_wins[s] += 1
        global_won = sum(strat_wins.values())
        global_tot = sum(strat_total.values())
        _EB_CACHE["_global_wr"] = global_won / global_tot if global_tot > 0 else 0.35
        for s, n in strat_total.items():
            _EB_CACHE[s] = (strat_wins[s] / n, n)

    global_wr = _EB_CACHE.get("_global_wr", 0.35)
    if strategy not in _EB_CACHE:
        return (global_wr, 0)
    return _EB_CACHE[strategy]


def empirical_win_prob(strategy: str, closed: list, prior_strength: int = 20) -> float:
    """Beta-Binomial shrinkage of strategy WR toward global prior."""
    global_wr = _EB_CACHE.get("_global_wr", 0.35) if _EB_CACHE else 0.35
    strat_wr, n = _get_strategy_wr(strategy, closed)
    shrunk = (n * strat_wr + prior_strength * global_wr) / (n + prior_strength)
    return round(max(0.05, min(0.95, shrunk)), 3)


# ---------------------------------------------------------------------------
# Pick age helper
# ---------------------------------------------------------------------------

def _pick_age_hours(pick: dict) -> Optional[float]:
    for field in ("timestamp", "entry_date", "entry_time", "opened_at", "created_at", "generated_at"):
        raw = pick.get(field)
        if not raw:
            continue
        try:
            ts_str = str(raw).replace("Z", "+00:00").replace(" EST", "")
            if "T" not in ts_str and " " in ts_str:
                ts_str = ts_str.replace(" ", "T")
            dt = datetime.fromisoformat(ts_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
            return round(age, 1)
        except Exception:
            continue
    return None


# ---------------------------------------------------------------------------
# Core validator
# ---------------------------------------------------------------------------

class PickResult:
    """Result of validating a single pick."""

    __slots__ = ("pick", "passes_hf", "passes_active", "fails", "score", "empirical_wr", "age_h")

    def __init__(self, pick, passes_hf, passes_active, fails, score, empirical_wr, age_h):
        self.pick = pick
        self.passes_hf = passes_hf
        self.passes_active = passes_active
        self.fails = fails
        self.score = score
        self.empirical_wr = empirical_wr
        self.age_h = age_h

    def to_dict(self) -> dict:
        sym = self.pick.get("symbol") or self.pick.get("ticker", "?")
        return {
            "symbol": sym,
            "strategy": self.pick.get("strategy") or self.pick.get("algorithm", "?"),
            "direction": self.pick.get("direction", "?"),
            "risk_reward": self.pick.get("risk_reward"),
            "confidence": self.pick.get("confidence"),
            "elite_score": self.pick.get("elite_score"),
            "empirical_wr": self.empirical_wr,
            "age_hours": self.age_h,
            "hf_quality_score": self.score,
            "passes_hf": self.passes_hf,
            "passes_active": self.passes_active,
            "fail_reasons": self.fails,
        }


def validate_pick(pick: dict, closed: list, symbol_counts: dict | None = None) -> PickResult:
    """Validate a single pick against HF and active-tier standards.

    Uses data-calibrated thresholds from 4,005 closed picks:
      - conf >= 0.75 (0.8+ bucket → 77% WR)
      - RR 1.1-2.5 (1-1.5 zone → 56% WR; >2.5 falls to 31%)
      - empirical WR >= 40% from Bayesian shrinkage

    Returns a PickResult with:
      - passes_hf: True if pick meets hedge-fund tier (High Conviction eligible)
      - passes_active: True if pick meets minimum survivability standards
      - fails: list of failure reason codes
      - score: 0-100 quality score (higher = better)
    """
    fails_hf = []
    fails_active = []

    strategy = pick.get("strategy") or pick.get("algorithm") or ""
    rr = float(pick.get("risk_reward") or 0)
    # STOCKS forward_picks use tp_pct/sl_pct — derive RR from those if risk_reward missing
    if rr == 0:
        tp_pct = float(pick.get("tp_pct") or pick.get("tp") or 0)
        sl_pct = float(pick.get("sl_pct") or pick.get("sl") or 0)
        if tp_pct > 0 and sl_pct > 0:
            rr = round(tp_pct / sl_pct, 3)
    conf = float(pick.get("confidence") or pick.get("score") or 0)
    # STOCKS forward_picks use score (0-1 range) as confidence proxy
    if conf > 1.0:
        conf = conf / 100.0  # normalize if in 0-100 range
    elite = float(pick.get("elite_score") or pick.get("ml_composite_score") or 0)
    ml_score = float(pick.get("ml_score") or 0)
    age_h = _pick_age_hours(pick)
    emp_wr = empirical_win_prob(strategy, closed)
    conviction = pick.get("hf_conviction_tier") or pick.get("conviction_tier") or ""

    # --- Conviction tier bypass: S/A/B tiers already passed 4-of-5 quality criteria ---
    # bypass_hf prevents any further HF gates from failing these picks
    bypass_hf = conviction in ("S", "A", "B")

    # --- Hard block ---
    if strategy in _BLOCKED_STRATEGIES:
        fails_hf.append("blocked_strategy")
        fails_active.append("blocked_strategy")

    # Skip remaining HF checks for conviction-bypassed picks
    if not bypass_hf:
        # --- R:R checks (data-calibrated: RR 1.0-1.5 zone = 56% WR) ---
        if rr < HF_MIN_RR:
            fails_hf.append(f"rr_{rr:.2f}_lt_{HF_MIN_RR}")
        if rr > HF_MAX_RR:
            fails_hf.append(f"rr_{rr:.1f}_gt_{HF_MAX_RR}_tp_too_ambitious")

        # --- Confidence (critical: 0.6-0.7 danger zone = 22% WR) ---
        if conf < HF_MIN_CONFIDENCE:
            fails_hf.append(f"conf_{conf:.2f}_lt_{HF_MIN_CONFIDENCE}")
        elif CONFIDENCE_DANGER_LOW <= conf < CONFIDENCE_DANGER_HIGH:
            fails_hf.append(f"conf_danger_zone_{conf:.2f}")

        # --- Elite score (0 = field missing, treat as neutral not penalized) ---
        if elite > 0 and elite < HF_MIN_ELITE:
            fails_hf.append(f"elite_{elite:.0f}_lt_{HF_MIN_ELITE}")

        # --- Empirical WR ---
        if emp_wr < HF_MIN_EMPIRICAL_WR:
            fails_hf.append(f"emp_wr_{emp_wr:.2f}_lt_{HF_MIN_EMPIRICAL_WR}")

        # --- Freshness ---
        if age_h is not None and age_h > HF_MAX_FRESHNESS_H:
            fails_hf.append(f"stale_{age_h:.0f}h_gt_{HF_MAX_FRESHNESS_H}h")

        # --- Concentration ---
        sym = pick.get("symbol") or pick.get("ticker", "")
        if symbol_counts and sym and symbol_counts.get(sym, 0) > HF_MAX_SYMBOL_CONCENTRATION:
            fails_hf.append(f"concentration_{symbol_counts[sym]}_picks_for_{sym}")

    # Active tier: minimum survivability checks (not bypassed by conviction tier)
    if rr < ACTIVE_MIN_RR:
        fails_active.append(f"rr_{rr:.2f}_lt_{ACTIVE_MIN_RR}")
    if conf < ACTIVE_MIN_CONFIDENCE:
        fails_active.append(f"conf_{conf:.2f}_lt_{ACTIVE_MIN_CONFIDENCE}")
    if elite > 0 and elite < ACTIVE_MIN_ELITE:
        fails_active.append(f"elite_{elite:.0f}_lt_{ACTIVE_MIN_ELITE}")

    # --- HF quality score (0-100), calibrated to actual data ---
    # Weights derived from observed WR buckets:
    #   Confidence 0.80+ → 77% WR  → highest weight (30 pts)
    #   Empirical WR     → direct   → high weight (25 pts)
    #   Elite score      → moderate → medium weight (20 pts)
    #   R:R in sweet spot → 56% WR → 15 pts
    #   ML score / freshness → 10 pts
    score = 0.0
    # Confidence scoring (calibrated to WR buckets)
    if conf >= 0.80:
        score += 30
    elif conf >= 0.70:
        score += 18
    elif conf >= 0.60:
        score += 5   # Danger zone — low bonus
    # Empirical WR
    score += emp_wr * 25
    # Elite score
    if elite >= 60:
        score += 20
    elif elite >= 40:
        score += 12
    elif elite >= 20:
        score += 5
    # R:R in sweet spot (1.1-2.5 is the data-calibrated zone)
    if HF_MIN_RR <= rr <= HF_MAX_RR:
        # Bonus for being in the 1.1-1.5 sweet spot
        score += 15 if rr <= 1.5 else 10
    # ML score
    if ml_score >= 0.85:
        score += 7
    elif ml_score >= 0.70:
        score += 3
    # Proven strategy bonus
    if strategy in _PROVEN_STRATEGIES:
        score += 8
    # High conviction tier bonus (already passed 4-of-5 criteria)
    if conviction in ("S", "A"):
        score += 10
    elif conviction == "B":
        score += 5
    # Fresh signal
    if age_h is not None and age_h < 4:
        score += 5
    score = round(min(100, max(0, score)), 1)

    passes_active = len(fails_active) == 0
    passes_hf = len(fails_hf) == 0

    return PickResult(pick, passes_hf, passes_active, fails_hf, score, emp_wr, age_h)


# ---------------------------------------------------------------------------
# Batch validator + report
# ---------------------------------------------------------------------------

def validate_picks(picks: list, source_name: str = "unknown") -> dict:
    """Validate a list of picks and return a quality report."""
    closed = _load_closed_for_eb()
    # Pre-compute strategy WR cache
    _get_strategy_wr("__warm", closed)  # warms _EB_CACHE

    # Symbol concentration count
    symbol_counts: dict[str, int] = Counter(
        (p.get("symbol") or p.get("ticker", "")) for p in picks
    )

    results = [validate_pick(p, closed, symbol_counts) for p in picks]

    hf_pass  = [r for r in results if r.passes_hf]
    act_pass = [r for r in results if r.passes_active]
    hf_fail  = [r for r in results if not r.passes_hf]

    # Fail reason histogram
    fail_hist: dict[str, int] = Counter()
    for r in hf_fail:
        for f in r.fails:
            # Normalise to category
            cat = f.split("_")[0] if "_" in f else f
            fail_hist[cat] += 1

    # Score distribution
    scores = [r.score for r in results]
    avg_score = sum(scores) / len(scores) if scores else 0
    scores_sorted = sorted(scores)

    def pct(n, d):
        return round(n / d * 100, 1) if d > 0 else 0

    report = {
        "source": source_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_picks": len(picks),
        "closed_trades_used": len(closed),
        "summary": {
            "hf_tier_pass": len(hf_pass),
            "hf_tier_pct": pct(len(hf_pass), len(picks)),
            "active_tier_pass": len(act_pass),
            "active_tier_pct": pct(len(act_pass), len(picks)),
            "avg_quality_score": round(avg_score, 1),
            "median_quality_score": scores_sorted[len(scores_sorted) // 2] if scores_sorted else 0,
        },
        "thresholds": {
            "hf_min_rr": HF_MIN_RR,
            "hf_min_confidence": HF_MIN_CONFIDENCE,
            "hf_min_elite_score": HF_MIN_ELITE,
            "hf_min_empirical_wr": HF_MIN_EMPIRICAL_WR,
            "hf_max_freshness_h": HF_MAX_FRESHNESS_H,
            "active_min_rr": ACTIVE_MIN_RR,
            "active_min_confidence": ACTIVE_MIN_CONFIDENCE,
        },
        "fail_histogram": dict(fail_hist.most_common()),
        "hf_picks": [r.to_dict() for r in sorted(hf_pass, key=lambda r: -r.score)],
        "active_only_picks": [r.to_dict() for r in sorted(act_pass, key=lambda r: -r.score)
                              if not r.passes_hf],
        "rejected_picks": [r.to_dict() for r in sorted(hf_fail, key=lambda r: -r.score)],
    }
    return report


def validate_file(path: Path) -> dict:
    """Validate all picks in a single file."""
    try:
        data = json.loads(path.read_bytes())
    except Exception as e:
        return {"source": str(path), "error": str(e)}

    if isinstance(data, dict):
        picks = data.get("picks", [])
        if not picks:
            # Try common alternate keys
            for k in ("smart_picks", "active_picks", "results"):
                if k in data:
                    picks = data[k]
                    break
    else:
        picks = data if isinstance(data, list) else []

    picks = [p for p in picks if isinstance(p, dict)]
    if not picks:
        return {"source": str(path), "total_picks": 0, "note": "empty or no pick dicts"}

    return validate_picks(picks, source_name=path.name)


def _print_report(report: dict) -> None:
    """Pretty-print a validation report to stdout."""
    src = report.get("source", "?")
    total = report.get("total_picks", 0)
    if total == 0:
        print(f"  {src}: no picks to validate")
        return
    s = report.get("summary", {})
    print(f"\n{'='*65}")
    print(f"  {src}  ({total} picks)")
    print(f"{'='*65}")
    print(f"  ✅ HF-tier  pass: {s.get('hf_tier_pass'):>3} / {total}  ({s.get('hf_tier_pct')}%)")
    print(f"  ⚠️  Active  pass: {s.get('active_tier_pass'):>3} / {total}  ({s.get('active_tier_pct')}%)")
    print(f"  📊 Avg quality score: {s.get('avg_quality_score')} / 100")

    fh = report.get("fail_histogram", {})
    if fh:
        print(f"\n  TOP FAIL REASONS:")
        for reason, count in list(fh.items())[:5]:
            bar = "█" * min(count, 20)
            print(f"    {reason:<30} {count:>3}x  {bar}")

    hf_picks = report.get("hf_picks", [])
    if hf_picks:
        print(f"\n  HF-TIER PICKS ({len(hf_picks)}):")
        for p in hf_picks[:8]:
            print(f"    {p['symbol']:<12} {p['direction']:<5} "
                  f"RR={p['risk_reward'] or '?':<5} "
                  f"conf={p['confidence'] or '?':<5} "
                  f"elite={p['elite_score'] or '?':<5} "
                  f"emp_wr={p['empirical_wr']:.0%}  "
                  f"score={p['hf_quality_score']}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

DEFAULT_PICK_FILES = [
    _REPO / "alpha_engine" / "data" / "active_picks.json",
    _REPO / "alpha_engine" / "data" / "smart_picks.json",
    _REPO / "audit_dashboard" / "data" / "ai_challenge_antigravity_active_picks.json",
    _REPO / "STOCKS" / "competition" / "forward_picks.json",
]

REPORT_OUTPUT = _REPO / "audit_trail" / "data" / "hf_quality_report.json"


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    all_mode = "--all" in argv
    report_mode = "--report" in argv

    # Choose files to validate
    if all_mode:
        files = DEFAULT_PICK_FILES
    elif argv and not argv[0].startswith("-"):
        files = [Path(argv[0])]
    else:
        files = [_REPO / "alpha_engine" / "data" / "active_picks.json"]

    print("╔══════════════════════════════════════════════════════════════╗")
    print("║      HEDGE-FUND PICK QUALITY VALIDATOR                       ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print(f"║  HF thresholds:  RR≥{HF_MIN_RR}  Conf≥{HF_MIN_CONFIDENCE}  Elite≥{HF_MIN_ELITE}  EmpWR≥{HF_MIN_EMPIRICAL_WR:.0%}  ║")
    print("╚══════════════════════════════════════════════════════════════╝")

    all_reports = []
    for path in files:
        if not path.exists():
            print(f"  SKIP (not found): {path.name}")
            continue
        report = validate_file(path)
        _print_report(report)
        all_reports.append(report)

    # Combined summary
    if len(all_reports) > 1:
        total_picks = sum(r.get("total_picks", 0) for r in all_reports)
        total_hf = sum(r.get("summary", {}).get("hf_tier_pass", 0) for r in all_reports)
        total_active = sum(r.get("summary", {}).get("active_tier_pass", 0) for r in all_reports)
        print(f"\n{'='*65}")
        print(f"  COMBINED: {total_picks} picks across {len(all_reports)} files")
        pct_hf = total_hf / total_picks * 100 if total_picks else 0
        pct_ac = total_active / total_picks * 100 if total_picks else 0
        print(f"  HF-tier:  {total_hf}/{total_picks} ({pct_hf:.1f}%)")
        print(f"  Active:   {total_active}/{total_picks} ({pct_ac:.1f}%)")
        grade = "🏆 HEDGE-FUND READY" if pct_hf >= 40 else "⚠️  NEEDS IMPROVEMENT" if pct_hf >= 20 else "❌ BELOW STANDARD"
        print(f"  Grade:    {grade}")

    if report_mode and all_reports:
        REPORT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        combined = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "files_validated": len(all_reports),
            "reports": all_reports,
        }
        REPORT_OUTPUT.write_text(json.dumps(combined, indent=2, default=str))
        print(f"\n  Report saved: {REPORT_OUTPUT}")

    # Exit 0 unless nothing passed HF tier
    if all_reports:
        total_hf = sum(r.get("summary", {}).get("hf_tier_pass", 0) for r in all_reports)
        return 0 if total_hf > 0 else 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
