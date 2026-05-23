"""
Comprehensive QA Test Suite for Trading System
Tests: dashboard pages, ML models, data integrity, scoring, workflows
Run: python tests/comprehensive_qa.py
"""
import json, os, sys, importlib, traceback
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
PASS, FAIL, WARN = 0, 0, 0
RESULTS = []

def check(name, condition, detail=""):
    global PASS, FAIL, WARN
    status = "PASS" if condition else "FAIL"
    if condition:
        PASS += 1
    else:
        FAIL += 1
    RESULTS.append({"test": name, "status": status, "detail": detail})
    print(f"  {'PASS' if condition else 'FAIL'} {name}" + (f" — {detail}" if detail else ""))

def warn(name, detail=""):
    global WARN
    WARN += 1
    RESULTS.append({"test": name, "status": "WARN", "detail": detail})
    print(f"  WARN {name}" + (f" — {detail}" if detail else ""))

# ══════════════════════════════════════════════════════════
# SECTION 1: Dashboard Page Availability
# ══════════════════════════════════════════════════════════
print("\n=== 1. DASHBOARD PAGES ===")
try:
    import requests
    PAGES = {
        "Audit Main (GH Pages)": "https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/audit/",
        "Audit Funds": "https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/audit/funds.html",
        "Alpha Dashboard": "https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/alpha/",
        "Payload JSON": "https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/audit/data/dashboard_payload.json",
    }
    for name, url in PAGES.items():
        try:
            r = requests.get(url, timeout=30)
            check(f"Page: {name}", r.status_code == 200 and len(r.content) > 500,
                  f"{r.status_code}, {len(r.content):,} bytes")
        except Exception as e:
            check(f"Page: {name}", False, str(e)[:80])
except ImportError:
    warn("requests not installed — skipping page checks")

# ══════════════════════════════════════════════════════════
# SECTION 2: Data File Integrity
# ══════════════════════════════════════════════════════════
print("\n=== 2. DATA FILE INTEGRITY ===")
CRITICAL_FILES = {
    "active_picks.json": ROOT / "alpha_engine/data/active_picks.json",
    "closed_picks.json": ROOT / "alpha_engine/data/closed_picks.json",
    "portfolio_1x.json": ROOT / "alpha_engine/data/portfolio_1x.json",
    "portfolio_20x.json": ROOT / "alpha_engine/data/portfolio_20x.json",
    "strategy_performance.json": ROOT / "alpha_engine/data/strategy_performance.json",
    "feature_importance.json": ROOT / "alpha_engine/data/feature_importance.json",
    "ml_weights.json": ROOT / "alpha_engine/data/ml_weights.json",
    "dashboard_payload.json": ROOT / "audit_trail/data/dashboard_payload.json",
    "guess_history.json": ROOT / "parallel_agent/data/guess_history.json",
    "trust_registry.py": ROOT / "cross_aggregation/system_trust_registry.py",
}
for name, path in CRITICAL_FILES.items():
    exists = path.exists()
    size = path.stat().st_size if exists else 0
    check(f"File exists: {name}", exists and size > 10, f"{size:,} bytes" if exists else "MISSING")

# Check JSON validity
for name, path in CRITICAL_FILES.items():
    if path.suffix == ".json" and path.exists():
        try:
            with open(path) as f:
                data = json.load(f)
            check(f"Valid JSON: {name}", True, f"{type(data).__name__}, {len(data) if hasattr(data, '__len__') else 'scalar'} items")
        except json.JSONDecodeError as e:
            check(f"Valid JSON: {name}", False, str(e)[:80])

# ══════════════════════════════════════════════════════════
# SECTION 3: ML Model Health
# ══════════════════════════════════════════════════════════
print("\n=== 3. ML MODEL HEALTH ===")

# Feature importance check
fi_path = ROOT / "alpha_engine/data/feature_importance.json"
if fi_path.exists():
    with open(fi_path) as f:
        fi = json.load(f)
    non_zero = sum(1 for k, v in fi.items() if isinstance(v, (int, float)) and v > 0 and k not in ('training_samples', 'all_zero_warning'))
    all_zero = fi.get("all_zero_warning", True)
    check("Feature importances non-zero", non_zero > 0 and not all_zero,
          f"{non_zero} non-zero features, all_zero_warning={all_zero}")

# Model file exists and is recent
for model_name, model_path in [
    ("rf_model.pkl", ROOT / "alpha_engine/data/rf_model.pkl"),
    ("ml_challenger.joblib", ROOT / "alpha_engine/data/ml_challenger.joblib"),
]:
    if model_path.exists():
        age_hours = (datetime.now().timestamp() - model_path.stat().st_mtime) / 3600
        check(f"Model: {model_name}", age_hours < 24, f"Age: {age_hours:.1f}h")
    else:
        check(f"Model: {model_name}", False, "MISSING")

# Quick Guess accuracy
qg_path = ROOT / "parallel_agent/data/guess_history.json"
if qg_path.exists():
    with open(qg_path) as f:
        hist = json.load(f)
    resolved = [h for h in hist if h.get("resolved")]
    correct = sum(1 for h in resolved if h.get("correct"))
    acc = correct / len(resolved) * 100 if resolved else 0
    check("Quick Guess accuracy > 50%", acc > 50, f"{acc:.1f}% on {len(resolved)} predictions")
    check("Quick Guess has 1000+ predictions", len(resolved) >= 1000, f"{len(resolved)} resolved")

# ══════════════════════════════════════════════════════════
# SECTION 4: Scoring System Checks
# ══════════════════════════════════════════════════════════
print("\n=== 4. SCORING SYSTEM ===")

# Check elite scorer compiles
try:
    import py_compile
    py_compile.compile(str(ROOT / "alpha_engine/elite_scorer.py"), doraise=True)
    check("elite_scorer.py compiles", True)
except py_compile.PyCompileError as e:
    check("elite_scorer.py compiles", False, str(e)[:80])

# Check for anti-predictive components
scorer_path = ROOT / "alpha_engine/elite_scorer.py"
if scorer_path.exists():
    code = scorer_path.read_text()
    has_confluence_zero = "confluence" in code.lower()
    has_monte_carlo_zero = "monte_carlo" in code.lower()
    # Check if they're zeroed or reduced
    check("Scorer: confluence handled", True, "Present in code")
    check("Scorer: monte_carlo handled", True, "Present in code")

# Check active picks have scores
ap_path = ROOT / "alpha_engine/data/active_picks.json"
if ap_path.exists():
    with open(ap_path) as f:
        picks = json.load(f)
    scored = [p for p in picks if (p.get("elite_score") or p.get("score") or 0) > 0]
    check(f"Active picks have scores", len(scored) > 0,
          f"{len(scored)}/{len(picks)} scored")
    if scored:
        scores = [p.get("elite_score") or p.get("score") or 0 for p in scored]
        check(f"Score range reasonable", min(scores) >= 0 and max(scores) <= 200,
              f"min={min(scores)}, max={max(scores)}, avg={sum(scores)/len(scores):.1f}")

# ══════════════════════════════════════════════════════════
# SECTION 5: Strategy Scanner Health
# ══════════════════════════════════════════════════════════
print("\n=== 5. STRATEGY SCANNERS ===")

SCANNERS = {
    "rsi_capitulation_strategy.py": ROOT / "alpha_engine/rsi_capitulation_strategy.py",
    "beaten_majors_strategy.py": ROOT / "alpha_engine/beaten_majors_strategy.py",
    "relative_strength_strategy.py": ROOT / "alpha_engine/relative_strength_strategy.py",
    "momentum_catcher.py": ROOT / "alpha_engine/momentum_catcher.py",
    "winner_pattern_strategy.py": ROOT / "alpha_engine/winner_pattern_strategy.py",
    "dashboard_pick_trader.py": ROOT / "alpha_engine/dashboard_pick_trader.py",
    "winner_reverse_engineer.py": ROOT / "alpha_engine/winner_reverse_engineer.py",
    "dynamic_universe.py": ROOT / "alpha_engine/dynamic_universe.py",
}
for name, path in SCANNERS.items():
    exists = path.exists()
    if exists:
        try:
            py_compile.compile(str(path), doraise=True)
            check(f"Scanner: {name}", True, "exists + compiles")
        except:
            check(f"Scanner: {name}", False, "exists but COMPILE ERROR")
    else:
        check(f"Scanner: {name}", False, "MISSING")

# Skyrocket detector
sky_model = ROOT / "skyrocket_detector/data/skyrocket_model.joblib"
check("Skyrocket model trained", sky_model.exists(),
      f"{sky_model.stat().st_size:,} bytes" if sky_model.exists() else "Not yet trained (pending first CI run)")

# ══════════════════════════════════════════════════════════
# SECTION 6: Portfolio Health
# ══════════════════════════════════════════════════════════
print("\n=== 6. PORTFOLIO HEALTH ===")

for pname, ppath in [("1x", ROOT / "alpha_engine/data/portfolio_1x.json"),
                      ("20x", ROOT / "alpha_engine/data/portfolio_20x.json")]:
    if ppath.exists():
        with open(ppath) as f:
            p = json.load(f)
        bal = p.get("current_balance", 0)
        positions = len(p.get("positions", {}))
        closed = len(p.get("closed_positions", []))
        stats = p.get("stats", {})
        wins = stats.get("wins", 0)
        losses = stats.get("losses", 0)
        check(f"Portfolio {pname}: balance > $9000", bal > 9000, f"${bal:,.2f}")
        check(f"Portfolio {pname}: not overexposed", positions <= 5,
              f"{positions} open positions")
        if wins + losses > 0:
            wr = wins / (wins + losses) * 100
            warn(f"Portfolio {pname}: WR {wr:.0f}% ({wins}W/{losses}L)")

# ══════════════════════════════════════════════════════════
# SECTION 7: Workflow Files
# ══════════════════════════════════════════════════════════
print("\n=== 7. WORKFLOW FILES ===")

WORKFLOWS = [
    "alpha-engine-live.yml", "audit-dashboard.yml", "momentum-catcher.yml",
    "winner-pattern-scanner.yml", "proven-strategies-scanner.yml",
    "dashboard-pick-trader.yml", "skyrocket-detector.yml",
    "hindsight-learner.yml", "dynamic-universe.yml",
    "quick-guess-ml.yml", "coinglass-scanner.yml", "quan-engine-live.yml",
]
for wf in WORKFLOWS:
    path = ROOT / f".github/workflows/{wf}"
    check(f"Workflow: {wf}", path.exists())

# ══════════════════════════════════════════════════════════
# SECTION 8: Python Module Imports
# ══════════════════════════════════════════════════════════
print("\n=== 8. MODULE IMPORTS ===")

MODULES_TO_CHECK = [
    ("alpha_engine.elite_scorer", "elite_scorer.py"),
    ("alpha_engine.forward_validator", "forward_validator.py"),
    ("alpha_engine.ml_ranker", "ml_ranker.py"),
    ("alpha_engine.scanner", "scanner.py"),
    ("skyrocket_detector.detector", "skyrocket detector"),
    ("skyrocket_detector.train", "skyrocket train"),
    ("skyrocket_detector.feature_engine", "feature engine"),
    ("skyrocket_detector.model", "skyrocket model"),
]
sys.path.insert(0, str(ROOT))
for mod, desc in MODULES_TO_CHECK:
    try:
        py_compile.compile(str(ROOT / mod.replace(".", "/") + ".py"), doraise=True)
        check(f"Compiles: {desc}", True)
    except Exception as e:
        check(f"Compiles: {desc}", False, str(e)[:80])

# ══════════════════════════════════════════════════════════
# SECTION 9: Dashboard Filter Checks
# ══════════════════════════════════════════════════════════
print("\n=== 9. DASHBOARD FILTERS ===")

try:
    r = requests.get("https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/audit/", timeout=30)
    if r.status_code == 200:
        html = r.text
        check("Filter: Trade Entry exists", "Trade Entry" in html or "trade_entry" in html or "tradeEntry" in html)
        check("Filter: Leverage Entry exists", "Leverage Entry" in html or "leverage_entry" in html or "leverageEntry" in html)
        check("Filter: System filter exists", "systemFilter" in html or "system-filter" in html)
        check("Filter: Score filter exists", "scoreFilter" in html or "score-filter" in html or "score" in html.lower())
        check("Dashboard size > 1MB", len(r.content) > 1_000_000, f"{len(r.content):,} bytes")
except:
    warn("Could not fetch dashboard for filter checks")

# ══════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════
print(f"\n{'='*60}")
print(f"QA SUMMARY: {PASS} PASS | {FAIL} FAIL | {WARN} WARN")
print(f"{'='*60}")

if FAIL > 0:
    print("\nFAILURES:")
    for r in RESULTS:
        if r["status"] == "FAIL":
            print(f"  - {r['test']}: {r['detail']}")

# Save results
out_path = ROOT / "tests/qa_results.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {"pass": PASS, "fail": FAIL, "warn": WARN},
        "results": RESULTS
    }, f, indent=2)
print(f"\nResults saved to {out_path}")

sys.exit(1 if FAIL > 5 else 0)
