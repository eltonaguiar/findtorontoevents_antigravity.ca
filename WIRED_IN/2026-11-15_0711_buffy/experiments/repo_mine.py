"""Layer A/B repository mining: static signature scan + semantic extraction.

Run from the repo root:
    python3 WIRED_IN/<ws>/experiments/repo_mine.py WIRED_IN/<ws>

Writes <ws>/harvested_ideas/00_inventory.csv and prints aggregate counts.
Deterministic; no network; skips .git, node_modules and worktree copies.
"""
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict

ROOT = os.getcwd()
OUT = sys.argv[1] if len(sys.argv) > 1 else "."
SKIP_DIRS = {".git", "node_modules", ".worktrees", "__pycache__", ".venv", "venv",
             ".mypy_cache", ".pytest_cache", "dist", "build", "WIRED_IN", "archive",
             "final_v4", "backups", ".claude", ".agents", ".local", "coinglass_strategies"}
EXTS = {".py", ".md", ".pine", ".js", ".ts", ".json", ".txt", ".yml", ".yaml"}
MAX_BYTES = 200_000
MAX_FILES = 25_000

PATTERNS = {
    "ML:tree-ensemble": r"random[_ ]?forest|xgboost|lightgbm|catboost|gradient.?boosting",
    "ML:deep": r"keras|tensorflow|pytorch|torch\.|lstm|transformer|gru\b",
    "ML:classical": r"\bsvm\b|\bpca\b|kmeans|clustering|isolation.?forest",
    "ML:state-space": r"\bhmm\b|hmmlearn|kalman|bayesian|particle.?filter",
    "ML:timeseries": r"\barima\b|sarima|prophet|\barch\b|garch|cointegrat",
    "ML:rl": r"reinforcement|q.?learning|policy.?gradient|\bppo\b|\bdqn\b",
    "BT:framework": r"vectorbt|zipline|backtrader|quantconnect|backtesting\.py",
    "BT:walkforward": r"walk.?forward|\bwfo\b|walkforward",
    "BT:cv": r"cross.?validation|purged|combinatorial|\bcpcv\b|embargo",
    "BT:sweep": r"grid.?search|param.?sweep|optuna|hyperopt|parameters? ?space",
    "STAT:dsr": r"deflated.?sharpe|\bdsr\b|probabilistic.?sharpe|\bpsr\b",
    "STAT:pbo": r"\bpbo\b|probability.?of.?backtest|\bcscv\b",
    "STAT:reality-check": r"white.?s.?reality|reality.?check|\bspa\b|hansen",
    "STAT:bootstrap": r"bootstrap|monte.?carlo|permutation|resampl",
    "STAT:multiple-testing": r"bonferroni|holm|benjamini|\bfdr\b|false.?discovery",
    "STAT:significance": r"t.?stat|p.?value|wilson|confidence.?interval|significan",
    "RISK:sizing": r"kelly|position.?siz|vol.?target|risk.?parity",
    "RISK:stops": r"stop.?loss|take.?profit|trailing.?stop|\batr\b",
    "RISK:drawdown": r"max.?(drawdown|dd)|calmar|sterling|sortino",
    "EXEC:costs": r"slippage|commission|spread|funding.?rate|borrow|fee.?bps",
    "EXEC:paper": r"paper.?trad|simulate|dry.?run|forward.?test",
    "EXEC:live": r"live.?trad|order.?submit|api.?key|ccxt|binance|hyperliquid",
    "DATA:market": r"yfinance|ccxt|alpha.?vantage|polygon|ohlcv|adj.?close|resample",
    "DATA:alt": r"on.?chain|funding.?rate|\bcot\b|open.?interest|sentiment",
    "REGIME": r"regime|hmm.?state|volatility.?regime|sideways",
}
CLS = [
    ("CRYPTO", r"crypto|btc|eth\b|usdt|altcoin|coinglass|binance"),
    ("EQUITY", r"equit|stock|spy|nasdaq|s&p|penny"),
    ("ETF", r"\betf\b|sector.?rotation"),
    ("FOREX", r"forex|\bfx\b|eurusd|currency.?pair"),
    ("BOND", r"\bbond\b|treasury|yield.?curve|duration|2s10s"),
    ("COMMODITY", r"commodit|gold|wti|brent|inventory"),
    ("MULTI", r"multi.?asset|rotat|basket|portfolio"),
]
TF = [(r"\b1m\b|\b1min", "1m"), (r"\b5m\b", "5m"), (r"\b15m\b", "15m"),
      (r"\b1h\b|hourly", "1h"), (r"\b4h\b", "4h"), (r"daily|\b1d\b", "1d"),
      (r"weekly|\b1w\b", "1w"), (r"intraday|scalp", "intraday")]


def iter_files():
    seen = 0
    for d, dirs, fs in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS and not x.startswith(".git")]
        for f in fs:
            ext = os.path.splitext(f)[1].lower()
            if ext not in EXTS:
                continue
            p = os.path.join(d, f)
            try:
                if os.path.getsize(p) > MAX_BYTES:
                    continue
            except OSError:
                continue
            seen += 1
            if seen > MAX_FILES:
                return
            yield p, ext


rows, tech_files, cls_counts = [], defaultdict(set), Counter()
scanned = 0
for path, ext in iter_files():
    try:
        txt = open(path, encoding="utf-8", errors="ignore").read()
    except OSError:
        continue
    scanned += 1
    low = txt.lower()
    rel = os.path.relpath(path, ROOT)
    hits = [t for t, rx in PATTERNS.items() if re.search(rx, low)]
    if not hits:
        continue
    cls = next((c for c, rx in CLS if re.search(rx, rel.lower() + " " + low[:4000])), "")
    tf = next((v for rx, v in TF if re.search(rx, low[:6000])), "")
    fns = re.findall(r"^\s*(?:async\s+)?def\s+([A-Za-z_]\w+)", txt, re.M)[:4] if ext == ".py" else []
    fns += re.findall(r"^\s*class\s+([A-Za-z_]\w+)", txt, re.M)[:2]
    lang = {".py": "python", ".md": "markdown", ".pine": "pine", ".js": "javascript",
            ".ts": "typescript", ".json": "json", ".txt": "text",
            ".yml": "yaml", ".yaml": "yaml"}.get(ext, ext.lstrip("."))
    status = ("implemented" if ext == ".py" else
              "tested" if re.search(r"backtest|result|verdict", rel, re.I) else "documented")
    if re.search(r"abandon|reject|\bkill|retire|deprecat|falsif|exhaust",
                 rel + " " + low[:2000], re.I):
        status = "abandoned"
    rows.append({"file_path": rel, "language": lang, "technique detected": ";".join(hits),
                 "asset class": cls, "timeframe": tf,
                 "key functions": ";".join(fns)[:400], "status": status})
    for h in hits:
        tech_files[h].add(rel)
    cls_counts[cls or "UNSPECIFIED"] += 1

rows.sort(key=lambda r: (r["status"], r["file_path"]))
os.makedirs(os.path.join(OUT, "harvested_ideas"), exist_ok=True)
csv_path = os.path.join(OUT, "harvested_ideas", "00_inventory.csv")
with open(csv_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["file_path"])
    w.writeheader()
    w.writerows(rows)

print(f"scanned {scanned} files | flagged {len(rows)} | csv {csv_path}")
print("\ntechnique -> flagged files")
for t, s in sorted(tech_files.items(), key=lambda kv: -len(kv[1])):
    print(f"  {len(s):5d}  {t}")
print("\nasset class -> flagged files")
for c, n in cls_counts.most_common():
    print(f"  {n:5d}  {c}")
print("\nstatus -> files")
for k, n in Counter(r["status"] for r in rows).most_common():
    print(f"  {n:5d}  {k}")

if os.path.exists("requirements.txt"):
    req = [l.strip() for l in open("requirements.txt") if l.strip() and not l.startswith("#")]
    print(f"\nrequirements.txt: {len(req)} entries")
    print("  sample:", ", ".join(x.split("==")[0].split(">=")[0] for x in req[:18]))
if os.path.exists("package.json"):
    pj = json.load(open("package.json"))
    print(f"package.json: {len(pj.get('dependencies') or {})} deps, "
          f"{len(pj.get('devDependencies') or {})} devDeps")
