#!/usr/bin/env python3
"""
Layer A + Layer B Repository Miner & Dependency Triage
======================================================
Implements the two-layer repository mining ("code archaeology") protocol:
  - Layer A: Static regex archaeology across ML/models, Backtesting, Risk,
    Execution, and Data signatures, plus dependency manifest parsing.
  - Layer B: Semantic extraction (Python functions/classes, Pine declarations,
    Markdown strategy headings) -> harvested_ideas/00_inventory.csv.

Reproducible on any clean checkout of the repository (uses git ls-files when
available, falling back to pruned directory walk; skips transient worktrees,
node_modules, .git, and peer WIRED_IN/final_* dumps to prevent circularity).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

# Repo root preamble per AGENTS.md (works under direct python invocation)
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

OUT_DIR = Path(__file__).resolve().parent

SKIP_TOP_PREFIXES = (
    ".git/",
    "node_modules/",
    ".worktrees/",
    ".fix-wt/",
    ".inspect-wt/",
    "WIRED_IN/",
    "final_2026_11_14/",
    "final_v2/",
    "final_v3/",
    "final_v4/",
    "2026-11-14",
    "2026-11-15",
    "archive/",
    "favcreators/",
    "TORONTOEVENTS_ANTIGRAVITY/",
    "vr/",
    "logs/",
    "tmp/",
)

SCAN_EXTS = {".py", ".md", ".pine", ".js", ".ts", ".php", ".html"}

REGEX_LIB = {
    "ML_MODELS": re.compile(
        r"\b(random[ _.]forest|xgboost|lightgbm|keras|tensorflow|pytorch|lstm|transformer|"
        r"arima|sarima|prophet|hmm|kalman|bayesian|neural|gradient[ _.]boosting|clustering|pca|svm)\b",
        re.IGNORECASE,
    ),
    "BACKTESTING": re.compile(
        r"\b(backtest|vectorbt|zipline|backtrader|quantconnect|walk[ _.]forward|"
        r"cross[ _.]validation|train_test_split|in_sample|out_of_sample|param[ _.]sweep|grid[ _.]search)\b",
        re.IGNORECASE,
    ),
    "RISK": re.compile(
        r"\b(var|value[ _.]at[ _.]risk|max[ _.]drawdown|sharpe|sortino|calmar|sterling|"
        r"kelly|position[ _.]sizing|stop[ _.]loss|take[ _.]profit|tp|sl|atr|volatility|leverage)\b",
        re.IGNORECASE,
    ),
    "EXECUTION": re.compile(
        r"\b(paper[ _.]trade|simulate|live|execution|slippage|commission|spread|funding|tax)\b",
        re.IGNORECASE,
    ),
    "DATA": re.compile(
        r"\b(yfinance|ccxt|alpha[ _.]vantage|polygon|binance|ohlcv|resample|adj[ _.]close)\b",
        re.IGNORECASE,
    ),
}

PRIORITY_PATTERNS = (
    "money-maker",
    "money_maker",
    "testing_protocol",
    "recovery",
    "kimi",
    "alpha_engine",
    "audit_trail",
    "audit_dashboard",
    "updates/index.html",
    "ml_battleground",
    "ml_crypto_predictor",
    "copy_trader_intel",
    "prediction_market_agents",
    "baby_strategies",
    "genome",
    "quant_lab",
    "verified_strategies",
    "paper_trading",
    "plans/",
    "tools/",
)

# Pre-compiled Layer B extractors (avoid per-file compilation overhead)
RE_PY_DEF = re.compile(r"^(?:def|class)\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE)
RE_MD_HEAD = re.compile(r"^#{1,3}\s+(.+)$", re.MULTILINE)
RE_PINE_FN = re.compile(r"(?:^|\n)\s*([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)\s*=>")
RE_PINE_IN = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*input\.")
RE_JS_FN = re.compile(r"function\s+([A-Za-z_][A-Za-z0-9_]*)")

ASSET_PATTERNS = [
    ("CRYPTO", re.compile(r"\b(crypto|btc|eth|sol|binance|ccxt|funding[ _.]rate|perps?|usdt)\b")),
    ("EQUITY", re.compile(r"\b(equity|equities|stock|stocks|spy|qqq|pead|earnings|s&p|penny)\b")),
    ("FOREX", re.compile(r"\b(forex|fx|eurusd|usdjpy|gbpusd|pip|pips|cot|carry)\b")),
    ("BOND", re.compile(r"\b(bond|bonds|treasury|yield[ _.]curve|tlt|ief|agg|shy|duration|fixed[ _.]income)\b")),
    ("ETF", re.compile(r"\b(etf|etfs|xlk|efa|eem|vnq|gld|dbc|sgov|sector[ _.]rotation)\b")),
    ("MUTUAL_FUND", re.compile(r"\b(mutual[ _.]fund|nav|mer|expense[ _.]ratio|tfsa|rrsp|index[ _.]fund)\b")),
    ("COMMODITY_FUTURES", re.compile(r"\b(commodity|commodities|futures|gold|oil|cl|gc|ng|roll[ _.]yield|bcom)\b")),
    ("PREDICTION_MARKET", re.compile(r"\b(polymarket|kalshi|prediction[ _.]market)\b")),
]

TF_PATTERNS = [
    ("1m-15m", re.compile(r"\b(1m|5m|15m|scalp|intraday|minute)\b")),
    ("1h-4h", re.compile(r"\b(1h|4h|hourly|4-hour)\b")),
    ("daily", re.compile(r"\b(1d|daily|day|swing|200d|sma200|rsi\(2\))\b")),
    ("weekly-monthly", re.compile(r"\b(weekly|monthly|rebalance|12-1|quarterly|long-term)\b")),
]

ENTRY_PATTERNS = [
    (re.compile(r"\brsi\b"), "RSI"),
    (re.compile(r"bollinger|bb_"), "Bollinger"),
    (re.compile(r"donchian|breakout"), "Breakout"),
    (re.compile(r"momentum|12-1|\bsma\b|\bema\b|crossover"), "Trend/Momentum"),
    (re.compile(r"mean[ _.]reversion|vwap|pullback|wick"), "MeanReversion"),
    (re.compile(r"funding|carry|yield|\bcot\b"), "Carry/COT/Funding"),
    (re.compile(r"pead|earnings|insider|accrual"), "Fundamental/Event"),
    (re.compile(r"xgboost|random[ _.]forest|lightgbm|lstm|hmm|kelly|bayesian"), "ML/Stat"),
]

EXIT_PATTERNS = [
    (re.compile(r"take[ _.]profit|\btp\b"), "TP"),
    (re.compile(r"stop[ _.]loss|\bsl\b"), "SL"),
    (re.compile(r"time[ _.]exit|max[ _.]hold|expired"), "TimeExit"),
    (re.compile(r"rebalance|monthly|weekly"), "PeriodicRebal"),
    (re.compile(r"trailing|\batr\b"), "ATR/Trail"),
]

RISK_PATTERNS = [
    (re.compile(r"\bkelly\b"), "Kelly"),
    (re.compile(r"vol[ _.]target|inverse[ _.]vol"), "VolTargeting"),
    (re.compile(r"max[ _.]drawdown|\bmdd\b"), "MDD-Gate"),
    (re.compile(r"\bcvar\b|\bvar\b"), "VaR/CVaR"),
    (re.compile(r"\bdsr\b|deflated|\bpbo\b|\bspa\b|bonferroni"), "MultipleTestGate"),
    (re.compile(r"slippage|cost_gate|commission"), "CostModel"),
]

RE_TPSL = re.compile(r"(?:tp|sl|stop_loss|take_profit|tp_pct|sl_pct)\s*[=:]\s*([0-9.]+%?)")
RE_PF = re.compile(r"(?:pf|profit[ _.]factor)\s*[=:≈~]\s*([0-9.]+)")
RE_WR = re.compile(r"(?:wr|win[ _.]rate)\s*[=:≈~]\s*([0-9.]+%?)")
RE_SHARPE = re.compile(r"sharpe\s*[=:≈~]\s*(-?[0-9.]+)")


def list_repo_files(scan_root: Path) -> list[str]:
    try:
        res = subprocess.run(
            ["git", "-C", str(scan_root), "ls-files"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=20,
            check=True,
        )
        return [line.strip().replace("\\", "/") for line in res.stdout.splitlines() if line.strip()]
    except Exception:
        out = []
        skip_names = {p.rstrip("/") for p in SKIP_TOP_PREFIXES}
        for root, dirs, files in os.walk(scan_root):
            dirs[:] = sorted([d for d in dirs if d not in skip_names and not d.startswith("2026-11-")])
            for fn in files:
                rel = (Path(root) / fn).relative_to(scan_root).as_posix()
                out.append(rel)
        return out


def detect_language(ext: str) -> str:
    return {
        ".py": "Python",
        ".md": "Markdown",
        ".pine": "PineScript",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".php": "PHP",
        ".html": "HTML",
    }.get(ext, ext.lstrip("."))


def infer_asset_class(rel_path: str, text_lower: str) -> str:
    combined = f"{rel_path.lower()}\n{text_lower[:6000]}"
    classes = [label for label, pat in ASSET_PATTERNS if pat.search(combined)]
    if len(classes) >= 3 or "multi_asset" in combined or "allocation" in combined:
        return "MULTI_ASSET"
    return "|".join(classes) if classes else "MULTI_ASSET"


def infer_timeframe(text_lower: str) -> str:
    sample = text_lower[:8000]
    found = [tf for tf, pat in TF_PATTERNS if pat.search(sample)]
    return "|".join(found) if found else "unspecified"


def infer_status(rel_path: str, text_lower: str) -> str:
    p = rel_path.lower()
    if any(k in p for k in ("archive/", "deprecated", "old", "stub")):
        return "abandoned"
    if any(k in text_lower[:5000] for k in ("quarantine", "kill", "blacklist", "disabled", "failed", "not_ready")):
        return "tested/flagged"
    if p.endswith(".py") and any(k in p for k in ("alpha_engine/", "audit_trail/", "tools/", "copy_trader_intel/")):
        return "implemented"
    if p.endswith(".py") and any(k in p for k in ("incubator/", "ml_battleground/", "genome/", "baby_strategies/")):
        return "tested"
    if p.endswith(".pine"):
        return "implemented/tradingview"
    return "documented/tested"


def infer_logic_fields(tl: str) -> tuple[str, str, str, str, str, str]:
    sub = tl[:12000]
    entry_hits = [label for pat, label in ENTRY_PATTERNS if pat.search(sub)]
    entry_logic = "+".join(entry_hits[:4]) if entry_hits else "signal/rule"

    exit_hits = [label for pat, label in EXIT_PATTERNS if pat.search(sub)]
    exit_logic = "+".join(exit_hits[:4]) if exit_hits else "unspecified"

    tp_sl_m = RE_TPSL.findall(sub)
    tp_sl = ";".join(tp_sl_m[:4]) if tp_sl_m else ("ATR/param-based" if "atr" in sub else "unextracted")

    risk_hits = [label for pat, label in RISK_PATTERNS if pat.search(sub)]
    risk_mgmt = "+".join(risk_hits[:4]) if risk_hits else "basic/none"

    pf_m = RE_PF.search(sub)
    wr_m = RE_WR.search(sub)
    sharpe_m = RE_SHARPE.search(sub)
    obs_parts = []
    if pf_m:
        obs_parts.append(f"PF={pf_m.group(1)}")
    if wr_m:
        obs_parts.append(f"WR={wr_m.group(1)}")
    if sharpe_m:
        obs_parts.append(f"Sharpe={sharpe_m.group(1)}")
    result_observed = " ".join(obs_parts) if obs_parts else "see_audit_ledger"

    failure_modes = []
    if any(k in sub for k in ("overfit", "pbo", "snooping", "646", "285")):
        failure_modes.append("1:Overfit")
    if any(k in sub for k in ("lookahead", "look-ahead", "intrabar", "nominal")):
        failure_modes.append("2:LookAhead/Fill")
    if any(k in sub for k in ("slippage", "spread", "cost", "422%", "overshoot")):
        failure_modes.append("4:Friction/Cost")
    if any(k in sub for k in ("regime", "chop", "bull", "bear")):
        failure_modes.append("6:RegimeDep")
    if any(k in sub for k in ("zombie", "time_expired", "backfill", "0% p/l", "staleness")):
        failure_modes.append("7:ImplGap")
    if any(k in sub for k in ("insufficient_data", "low-n", "n<100", "small n")):
        failure_modes.append("8:SmallN")
    suspected_failure = "|".join(failure_modes[:3]) if failure_modes else "5:WeakSNR/Unverified"

    return entry_logic, exit_logic, tp_sl, risk_mgmt, result_observed, suspected_failure


def parse_dependencies(scan_root: Path, all_rel_files: list[str]) -> dict:
    manifests = {}
    all_pkgs = Counter()
    for rel in all_rel_files:
        if any(rel.startswith(p) for p in SKIP_TOP_PREFIXES):
            continue
        fn = os.path.basename(rel)
        if fn in ("pyproject.toml", "package.json") or (fn.startswith("requirements") and fn.endswith(".txt")):
            fpath = scan_root / rel
            if not fpath.is_file():
                continue
            try:
                raw = fpath.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            pkgs = []
            if fn.endswith(".txt"):
                for line in raw.splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("-"):
                        continue
                    pkg = re.split(r"[>=<!~\[;\s]", line, maxsplit=1)[0].strip().lower()
                    if pkg:
                        pkgs.append(pkg)
            elif fn == "package.json":
                try:
                    data = json.loads(raw)
                    for sec in ("dependencies", "devDependencies"):
                        for k in (data.get(sec) or {}):
                            pkgs.append(k.lower())
                except json.JSONDecodeError:
                    pass
            elif fn == "pyproject.toml":
                for m in re.findall(r'^\s*"([A-Za-z0-9_.-]+)', raw, re.MULTILINE):
                    pkgs.append(m.lower())
            manifests[rel] = sorted(set(pkgs))
            for p in set(pkgs):
                all_pkgs[p] += 1
    return {"manifests": manifests, "package_frequency": dict(all_pkgs.most_common())}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan-root", default="", help="Override repository root to scan")
    args = parser.parse_args()

    scan_root = Path(args.scan_root).resolve() if args.scan_root else REPO_ROOT
    all_rel_files = list_repo_files(scan_root)

    total_files_scanned = 0
    category_file_hits = Counter()
    keyword_hits = Counter()
    dir_counts = Counter()
    inventory_rows = []

    for rel in all_rel_files:
        if any(rel.startswith(p) for p in SKIP_TOP_PREFIXES):
            continue
        ext = os.path.splitext(rel)[1].lower()
        if ext not in SCAN_EXTS:
            continue
        if ext == ".html" and rel not in (
            "updates/index.html",
            "audit_dashboard/template.html",
            "simpleton_kimi_guide.html",
        ):
            continue

        fpath = scan_root / rel
        rel_low = rel.lower()
        is_priority = any(p in rel_low for p in PRIORITY_PATTERNS)
        read_cap = 80_000 if (is_priority and ext in (".md", ".pine", ".html")) else 24_000
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
                sample_text = fh.read(read_cap)
        except OSError:
            continue

        total_files_scanned += 1
        top_dir = rel.split("/")[0] if "/" in rel else "<root>"
        dir_counts[top_dir] += 1

        matched_cats = []
        matched_terms = []
        for cat, pat in REGEX_LIB.items():
            hits = pat.findall(sample_text)
            if hits:
                matched_cats.append(cat)
                category_file_hits[cat] += 1
                unique_hits = sorted({h.lower().strip() for h in hits})
                for uh in unique_hits:
                    keyword_hits[f"{cat}:{uh}"] += 1
                matched_terms.extend([f"{cat}:{u}" for u in unique_hits[:4]])

        if len(matched_cats) >= 2 or (is_priority and len(matched_cats) >= 1):
            lang = detect_language(ext)
            if lang == "Python":
                key_fns = RE_PY_DEF.findall(sample_text)[:8]
            elif lang == "PineScript":
                key_fns = [f"fn:{f}" for f in RE_PINE_FN.findall(sample_text)[:4]] + [
                    f"in:{i}" for i in RE_PINE_IN.findall(sample_text)[:4]
                ]
            elif lang == "Markdown":
                key_fns = [h.strip().replace(",", ";")[:60] for h in RE_MD_HEAD.findall(sample_text) if len(h.strip()) > 3][:6]
            else:
                key_fns = RE_JS_FN.findall(sample_text)[:6]

            sample_low = sample_text.lower()
            asset_class = infer_asset_class(rel, sample_low)
            tf = infer_timeframe(sample_low)
            status = infer_status(rel, sample_low)
            entry_l, exit_l, tp_sl, risk_m, res_obs, fail_m = infer_logic_fields(sample_low)

            inventory_rows.append({
                "file_path": rel,
                "language": lang,
                "technique_detected": ";".join(matched_terms[:10]),
                "asset_class": asset_class,
                "timeframe": tf,
                "key_functions": ";".join(key_fns[:8]) if key_fns else "module_level",
                "status": status,
                "entry_logic": entry_l,
                "exit_logic": exit_l,
                "tp_sl": tp_sl,
                "risk_mgmt": risk_m,
                "result_observed": res_obs,
                "suspected_failure_mode": fail_m,
            })

    csv_path = OUT_DIR / "00_inventory.csv"
    fieldnames = [
        "file_path",
        "language",
        "technique_detected",
        "asset_class",
        "timeframe",
        "key_functions",
        "status",
        "entry_logic",
        "exit_logic",
        "tp_sl",
        "risk_mgmt",
        "result_observed",
        "suspected_failure_mode",
    ]
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(inventory_rows)

    deps = parse_dependencies(scan_root, all_rel_files)
    (OUT_DIR / "dependencies_summary.json").write_text(
        json.dumps(deps, indent=2), encoding="utf-8"
    )

    stats = {
        "scan_root_name": scan_root.name,
        "total_tracked_files": len(all_rel_files),
        "total_files_scanned": total_files_scanned,
        "inventory_rows_written": len(inventory_rows),
        "category_file_hits": dict(category_file_hits),
        "top_40_keyword_hits": dict(keyword_hits.most_common(40)),
        "scanned_by_top_dir": dict(dir_counts.most_common(30)),
        "manifest_files_parsed": len(deps["manifests"]),
        "unique_packages_declared": len(deps["package_frequency"]),
    }
    (OUT_DIR / "layer_a_stats.json").write_text(
        json.dumps(stats, indent=2), encoding="utf-8"
    )

    print(f"Scan root: {scan_root.name} (tracked={len(all_rel_files)}, scanned={total_files_scanned})")
    print(f"Inventory rows written to {csv_path.name}: {len(inventory_rows)}")
    print(f"Category hits: {dict(category_file_hits)}")
    print(f"Manifests parsed: {len(deps['manifests'])}, unique packages: {len(deps['package_frequency'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
