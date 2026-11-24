"""audit3_evidence.py — audit3 P1 evidence registry.

Purpose
-------
`audit3_tribunal.py` scores the *live closed-pick ledger*. That is only one
source of evidence about whether a strategy works. The repo already holds
hundreds of backtests (JSON files) and three MySQL tables of results, none of
which the tribunal could see.

This module builds the missing link: one registry where every piece of
backtest evidence is represented with

  * the numbers the source actually reported (n, win rate, PF, Sharpe, MDD),
  * a **provenance record** (file path + sha256, or table + row id) so a
    number can always be traced back,
  * an **asset class derived from the symbol**, not trusted from the column,
  * a note about what is missing (trade log? costs? out-of-sample window?).

It deliberately does NOT re-score anything. Prior backtests are *evidence*, not
timing-null-validated cells; the tribunal decides verdicts, this registry only
makes the evidence visible and traceable. Where a source ships a trade log we
recompute WR / PF / mean PnL and store it under ``recomputed`` so the stated
numbers can be checked for disagreement.

Doctrine: innocent until proven guilty. An old backtest with a losing record is
not deleted -- it is registered, tagged with its provenance, and left for the
tribunal to weigh with the sample and multiplicity it deserves.

Known defects this module fixes
-------------------------------
``bt_backtest_runs.asset_class`` tags every one of its 285 rows ``CRYPTO``,
including ``NZDUSD=X``. Class is therefore derived from ``symbol`` and any
disagreement is reported in ``class_mismatches`` instead of being silently
believed.

Hypothesis statuses in ``reports/hypothesis_registry.json`` use 28 spellings for
what should be ~10 states (``FORWARD_OBSERVATION`` / ``FORWARD_SHADOW`` /
``forward-shadow`` / ``REGISTERED-UNTESTED`` / ``PRE-REGISTERED`` ...). The
registry normalises them to a canonical enum and keeps the raw spelling, so the
tracker can finally count something.

Usage
-----
  python3 alpha_engine/audit3_evidence.py \\
      --out audit_dashboard/data/audit3_evidence.json            # JSON + DB
  python3 alpha_engine/audit3_evidence.py --no-db --out /tmp/e.json   # offline

Exit codes: 0 registry written; 2 nothing usable was found.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

MODULE_PATH = Path(__file__).resolve()
REPO_ROOT = MODULE_PATH.parent.parent
if str(REPO_ROOT) not in sys.path:  # direct invocation: python3 alpha_engine/...
    sys.path.insert(0, str(REPO_ROOT))

SCHEMA = "audit3.evidence.v1"
MAX_FILE_MB = 24
TRADE_CAP = 5000

# ───────────────────────────────────────────────────────────── asset class ──
ETF_SYMBOLS = {
    "SPY", "QQQ", "IWM", "DIA", "VTI", "VOO", "VEA", "VWO", "EFA", "EEM",
    "TLT", "IEF", "SHY", "BND", "AGG", "HYG", "LQD", "TIP", "MUB",
    "GLD", "SLV", "USO", "UNG", "DBC", "DBA", "XLE", "XLF", "XLK", "XLV",
    "XLI", "XLY", "XLP", "XLU", "XLB", "XLRE", "XLC", "SMH", "SOXX", "ARKK",
    "IBB", "XBI", "KRE", "ITB", "GDX", "GDXJ", "UNP", "VYM", "SCHD",
}
INDEX_FUTURES = {"ES=F", "NQ=F", "YM=F", "RTY=F", "MBT=F", "MET=F"}
CRYPTO_BASES = {
    "BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "AVAX", "LINK", "DOT",
    "MATIC", "LTC", "BCH", "TRX", "ATOM", "NEAR", "APT", "ARB", "OP", "SUI",
    "SEI", "TIA", "INJ", "PEPE", "SHIB", "BONK", "WIF", "FET", "RNDR",
    "GRT", "FIL", "ALGO", "EOS", "XLM", "HBAR", "VET", "AAVE", "UNI", "MKR",
    "CRV", "SNX", "COMP", "SAND", "MANA", "AXS", "GALA", "IMX", "STX",
    "RUNE", "THETA", "FTM", "EGLD", "FLOW", "KAVA", "ZIL", "ENS", "BNB",
    "USDC", "USDT", "AR", "JUP", "PYTH", "ONDO", "ENA", "WLD", "TAO",
}
QUOTE_SUFFIXES = ("USDT", "USDC", "BUSD", "FDUSD", "TUSD", "USDP", "PERP")
CLASSES = ("CRYPTO", "EQUITY", "ETF", "FOREX", "COMMODITY", "FUTURES",
           "BOND", "PENNY_STOCK", "MEMECOIN", "UNKNOWN")


def _norm_symbol(symbol: Any) -> str:
    if symbol is None:
        return ""
    return str(symbol).strip().upper()


def derive_asset_class(symbol: Any, claimed: Any = None) -> str:
    """Derive the asset class from the symbol, falling back to the claim.

    Symbol rules win because they are checkable; ``bt_backtest_runs`` labels all
    285 of its rows CRYPTO, so a trusted column would hide the defect.
    """
    sym = _norm_symbol(symbol)
    claim = _norm_symbol(claimed)
    if not sym:
        return claim if claim in CLASSES else "UNKNOWN"
    if sym.endswith("=X"):
        return "FOREX"
    if sym.endswith("=F"):
        return "FUTURES" if sym in INDEX_FUTURES else "COMMODITY"
    compact = re.sub(r"[/\-_.:]", "", sym)
    if (compact.endswith(QUOTE_SUFFIXES) or sym.endswith("-USD")
            or compact in CRYPTO_BASES):
        return "CRYPTO"
    if sym in ETF_SYMBOLS:
        # An ETF is a wrapper, not an exposure. A row that claims EQUITY/BOND/
        # COMMODITY and uses SPY/TLT/GLD as its proxy keeps its economic class;
        # otherwise every index-proxy backtest would be misfiled as ETF and the
        # BOND/EQUITY counts would silently empty out.
        return claim if claim in ("EQUITY", "BOND", "COMMODITY") else "ETF"
    if claim in ("PENNY_STOCK", "MEMECOIN", "BOND"):
        # Price/liquidity is not in the row, so the claim is the only evidence
        # available; it is recorded as claimed==derived rather than contested.
        return claim
    if compact.isalpha() and 1 <= len(compact) <= 5:
        return "EQUITY"
    return claim if claim in CLASSES else "UNKNOWN"


def class_is_mismatch(claimed: Any, derived: str) -> bool:
    claim = _norm_symbol(claimed)
    return bool(claim) and claim != "UNKNOWN" and claim in CLASSES and claim != derived


# ─────────────────────────────────────────────────────── hypothesis statuses ──
CANONICAL_STATUSES = (
    "PRE_REGISTERED",
    "REGISTERED_UNTESTED",
    "FORWARD_OBSERVING",
    "FORWARD_SHADOW",
    "PAPER_PILOT",
    "SHADOW_BUILDING",
    "TESTED_PASS",
    "TESTED_WEAK",
    "REFUTED",
    "DATA_GAP",
    "BLOCKED",
    "CLOSED",
    "UNKNOWN",
)

STATUS_MAP = {
    "PRE_REGISTERED": "PRE_REGISTERED",
    "PRE-REGISTERED": "PRE_REGISTERED",
    "REGISTERED": "PRE_REGISTERED",
    "REGISTERED-UNTESTED": "REGISTERED_UNTESTED",
    "REGISTERED_UNTESTED": "REGISTERED_UNTESTED",
    "UNTESTED": "REGISTERED_UNTESTED",
    "UNTESTED_DATA_GAP": "REGISTERED_UNTESTED",
    "FORWARD_OBSERVATION": "FORWARD_OBSERVING",
    "FORWARD_ACCRUING": "FORWARD_OBSERVING",
    "FORWARD_SHADOW": "FORWARD_SHADOW",
    "FORWARD-SHADOW": "FORWARD_SHADOW",
    "SHADOW_IMPLEMENTATION": "SHADOW_BUILDING",
    "SHADOW_LIVE": "SHADOW_BUILDING",
    "PAPER_PILOT": "PAPER_PILOT",
    "PAPER": "PAPER_PILOT",
    "TESTED_PASS": "TESTED_PASS",
    "SUPPORTED": "TESTED_PASS",
    "TESTED_PASS_BACKTEST_FORWARD_PENDING": "TESTED_PASS",
    "TESTED_WEAK": "TESTED_WEAK",
    "NULL_RESULT": "TESTED_WEAK",
    "KILLED": "REFUTED",
    "TESTED_KILL": "REFUTED",
    "REJECTED": "REFUTED",
    "HARNESS_REJECTED": "REFUTED",
    "FAILED_ARCHIVED": "REFUTED",
    "REFUTED": "REFUTED",
    "DATA_GAP": "DATA_GAP",
    "REGISTERED_BLOCKED_ON_DATA": "BLOCKED",
    "CONTROL_FAILED_PENDING_CLEAN_ENTRY": "BLOCKED",
    "CLOSED": "CLOSED",
    "NULL": "UNKNOWN",
    "NONE": "UNKNOWN",
    "": "UNKNOWN",
}

_PREFIX_RULES = (
    ("REJECT", "REFUTED"),
    ("PRE_REGISTER", "PRE_REGISTERED"),
    ("PRE-REGISTER", "PRE_REGISTERED"),
    ("FORWARD", "FORWARD_OBSERVING"),
    ("UNTESTED", "REGISTERED_UNTESTED"),
    ("TESTED_PASS", "TESTED_PASS"),
    ("TESTED_WEAK", "TESTED_WEAK"),
    ("SHADOW", "FORWARD_SHADOW"),
    ("BLOCK", "BLOCKED"),
    ("DATA_GAP", "DATA_GAP"),
)


def normalize_hypothesis_status(raw: Any) -> tuple[str, bool]:
    """Return (canonical_status, matched_exactly).

    ``matched_exactly`` is False when a prefix rule or the UNKNOWN fallback was
    used, so the registry can list the spellings a human should clean up.
    """
    key = str(raw).strip().upper().replace(" ", "_")
    if key in STATUS_MAP:
        return STATUS_MAP[key], True
    for prefix, status in _PREFIX_RULES:
        if key.startswith(prefix):
            return status, False
    return "UNKNOWN", False


# ─────────────────────────────────────────────────────────── stats aliases ──
ALIASES = {
    "n": ("n", "n_trades", "n_closed", "total_trades", "trade_count", "trades_count"),
    "wr": ("wr", "wr_pct", "win_rate", "win_rate_pct", "wr_net"),
    "pf": ("pf", "pf_net", "profit_factor", "pf_gross"),
    "avg_net_bp": ("avg_net_bp", "avg_bp", "avg_net_bps", "avg_bp_net",
                   "avg_net_bp_per_trade"),
    "total_net_pct": ("total_net_pct", "sum_net_pct", "sum_net", "total_return_pct"),
    "sharpe": ("sharpe", "sharpe_ratio", "sharpe_annualized"),
    "mdd_pct": ("max_drawdown_pct", "max_drawdown", "mdd", "mdd_pct"),
    "trial_count": ("trial_count_N", "n_trials", "trials"),
}
PNL_KEYS = ("pnl_pct", "net_pct", "return_pct", "pnl_percent", "pct", "pnl")


def _num(value: Any) -> float | None:
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if out != out or out in (float("inf"), float("-inf")):
        return None
    return out


def _ratio(value: Any) -> float | None:
    """Normalise a win rate that may be 0-1 or 0-100."""
    v = _num(value)
    if v is None:
        return None
    return round(v / 100.0, 6) if v > 1.5 else v


def _pct(value: Any) -> float | None:
    """Normalise a drawdown that may be a ratio or already a percent."""
    v = _num(value)
    if v is None:
        return None
    if 0 < v <= 1.5:
        return round(v * 100.0, 4)
    return round(v, 4)


def stats_from_obj(obj: Any) -> dict[str, Any] | None:
    """Pick the reported metrics out of one dict, normalising units."""
    if not isinstance(obj, dict):
        return None
    out: dict[str, Any] = {}
    for field, names in ALIASES.items():
        for name in names:
            if name in obj:
                val = obj[name]
                if field == "wr":
                    val = _ratio(val)
                elif field == "mdd_pct":
                    val = _pct(val)
                elif field == "n":
                    val = int(val) if _num(val) is not None else None
                elif field == "trial_count":
                    val = int(val) if _num(val) is not None else None
                else:
                    val = _num(val)
                if val is not None:
                    out[field] = val
                    break
    if out.get("n") is None:
        return None
    return out


def find_stats(node: Any, max_depth: int = 3) -> tuple[dict[str, Any] | None, str]:
    """Breadth-first search for the most complete stats dict under ``node``."""
    best: tuple[int, int, dict[str, Any] | None, str] = (0, 99, None, "")
    queue: list[tuple[Any, int, str]] = [(node, 0, "")]
    seen = 0
    while queue and seen < 400:
        cur, depth, path = queue.pop(0)
        seen += 1
        if depth > max_depth:
            continue
        if isinstance(cur, dict):
            stats = stats_from_obj(cur)
            if stats:
                score = len(stats)
                if score > best[0] or (score == best[0] and depth < best[1]):
                    best = (score, depth, stats, path)
            for key, val in cur.items():
                if isinstance(val, (dict, list)):
                    queue.append((val, depth + 1, f"{path}.{key}" if path else str(key)))
        elif isinstance(cur, list):
            for idx, val in enumerate(cur[:8]):
                if isinstance(val, dict):
                    queue.append((val, depth + 1, f"{path}[{idx}]"))
    return best[2], best[3]


def extract_trade_pnls(node: Any, cap: int = TRADE_CAP) -> tuple[list[float], str]:
    """Return (pnls, field) from a trade-log list, if one is present."""
    if not isinstance(node, dict):
        return [], ""
    for container in ("trades", "trade_log", "trade_log_json", "closed_trades"):
        rows = node.get(container)
        if isinstance(rows, str):
            try:
                rows = json.loads(rows)
            except ValueError:
                continue
        if not isinstance(rows, list) or len(rows) < 10:
            continue
        for field in PNL_KEYS:
            vals = [v for v in (_num(r.get(field)) for r in rows[:cap] if isinstance(r, dict))
                    if v is not None]
            if len(vals) >= max(10, int(0.8 * min(len(rows), cap))):
                if field == "pnl" and abs(sorted(vals)[len(vals) // 2]) > 50:
                    continue  # looks like USD, not percent
                return vals, field
    return [], ""


def recompute(pnls: list[float]) -> dict[str, Any]:
    """Recompute WR / PF / mean from a raw trade log (gross, costs unknown)."""
    n = len(pnls)
    wins = sum(1 for v in pnls if v > 0)
    gross = sum(v for v in pnls if v > 0)
    loss = -sum(v for v in pnls if v < 0)
    return {
        "n": n,
        "wr": round(wins / n, 6) if n else None,
        "pf": round(gross / loss, 4) if loss > 1e-12 else None,
        "mean_pnl_pct": round(sum(pnls) / n, 4) if n else None,
        "cost_basis": "unknown/absent in source — not a net figure",
    }


# ──────────────────────────────────────────────────────────────── ingestion ──
CLASS_TOKENS = (
    ("CRYPTO", "CRYPTO"), ("EQUITY", "EQUITY"), ("ETF", "ETF"), ("BOND", "BOND"),
    ("FOREX", "FOREX"), ("FX", "FOREX"), ("COMMODITY", "COMMODITY"),
    ("FUTURES", "FUTURES"), ("MEMECOIN", "MEMECOIN"), ("MEME", "MEMECOIN"),
    ("PENNY", "PENNY_STOCK"), ("CHEAP", "PENNY_STOCK"), ("IPO", "EQUITY"),
)
# Last-resort name hints: a backtest named btc_utc_hour_backtest is crypto even
# when the payload never states a class. Word boundaries stop "AR" matching
# "carry" and "SOL" matching "solution".
CRYPTO_NAME_TOKENS = ("BTC", "ETH", "USDT", "COIN", "ALTCOIN")


def class_from_filename(name: str) -> str | None:
    upper = name.upper()
    for token, cls in CLASS_TOKENS:
        if re.search(rf"(^|[^A-Z]){token}([^A-Z]|$)", upper):
            return cls
    for token in CRYPTO_NAME_TOKENS:
        if re.search(rf"(^|[^A-Z]){token}([^A-Z]|$)", upper):
            return "CRYPTO"
    return None


def _evidence_id(*parts: Any) -> str:
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _record(*, surface: str, strategy: Any, symbol: Any, claimed: Any,
            stats: dict[str, Any], provenance: dict[str, Any],
            generated_at: Any = None, source_verdict: Any = None,
            split_half_pass: Any = None, trade_pnls: list[float] | None = None,
            pnl_field: str = "", notes: list[str] | None = None) -> dict[str, Any]:
    derived = derive_asset_class(symbol, claimed)
    if derived == "UNKNOWN":
        # No symbol, no column: the strategy name is the last checkable hint
        # (e.g. "BOND-01 ...", "crypto_eu_us...").
        derived = class_from_filename(str(strategy or "")) or "UNKNOWN"
    rec: dict[str, Any] = {
        "evidence_id": _evidence_id(surface, strategy, symbol,
                                    provenance.get("path") or provenance.get("table"),
                                    provenance.get("row_id")),
        "surface": surface,
        "strategy": str(strategy) if strategy else "(unnamed)",
        "symbol": _norm_symbol(symbol) or None,
        "asset_class_derived": derived,
        "asset_class_claimed": _norm_symbol(claimed) or None,
        "class_mismatch": class_is_mismatch(claimed, derived),
        "n": stats.get("n"),
        "wr": stats.get("wr"),
        "pf": stats.get("pf"),
        "avg_net_bp": stats.get("avg_net_bp"),
        "total_net_pct": stats.get("total_net_pct"),
        "sharpe": stats.get("sharpe"),
        "mdd_pct": stats.get("mdd_pct"),
        "trial_count_N": stats.get("trial_count"),
        "source_verdict": source_verdict if isinstance(source_verdict, (str, bool)) else None,
        "split_half_pass": split_half_pass if isinstance(split_half_pass, bool) else None,
        "recomputed": None,
        "provenance": provenance,
        "generated_at": str(generated_at) if generated_at else None,
        "notes": notes or [],
    }
    if trade_pnls:
        rec["recomputed"] = {**recompute(trade_pnls), "pnl_field": pnl_field}
    return rec


def _iter_bundles(data: Any) -> tuple[list[tuple[str | None, Any]], bool]:
    """Split a payload into (strategy_name, node) pairs, plus a single? flag."""
    if isinstance(data, list):
        return [(None, item) for item in data if isinstance(item, dict)], False
    if not isinstance(data, dict):
        return [], True
    if isinstance(data.get("strategies"), list):
        return [(s.get("name") or s.get("strategy"), s)
                for s in data["strategies"] if isinstance(s, dict)], False
    candidates = []
    for key, val in data.items():
        if not isinstance(val, dict):
            continue
        if any(k in val for k in ("results", "overall", "main", "stats", "metrics")):
            candidates.append((key, val))
    if len(candidates) >= 2:
        return candidates, False
    return [], True


def ingest_json(path: Path, root: Path = REPO_ROOT) -> list[dict[str, Any]]:
    """Ingest one backtest JSON into evidence records. Never raises."""
    try:
        if path.stat().st_size > MAX_FILE_MB * 1024 * 1024:
            return []
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return []
    try:
        rel = str(path.relative_to(root))
    except ValueError:
        rel = str(path)
    digest = _sha256_file(path)
    bundles, single = _iter_bundles(data)
    if single:
        bundles = [(data.get("strategy") if isinstance(data, dict) else None, data)]

    common_generated = None
    common_trials = None
    if isinstance(data, dict):  # some payloads are a bare list of results
        common_generated = (data.get("generated_at") or data.get("generated")
                            or data.get("generated_utc") or data.get("run_at")
                            or data.get("run_date"))
        common_trials = data.get("trial_count_N")
    file_class = None
    if isinstance(data, dict):
        file_class = data.get("asset_class")
    file_class = file_class or class_from_filename(path.stem)

    records: list[dict[str, Any]] = []
    for name, node in bundles:
        if not isinstance(node, dict):
            continue
        stats, _ = find_stats(node)
        if not stats:
            continue
        if common_trials is not None and stats.get("trial_count") is None:
            stats["trial_count"] = common_trials
        strategy = name or node.get("strategy") or node.get("archetype") or path.stem
        config = node.get("config") if isinstance(node.get("config"), dict) else {}
        symbols = config.get("symbols") or node.get("symbols") or node.get("universe")
        symbol = node.get("symbol")
        if not symbol and isinstance(symbols, (list, tuple)) and symbols:
            symbol = symbols[0]
        declared = file_class
        for key in ("asset_class", "assetclass", "instrument_type", "market"):
            if isinstance(node.get(key), str) and node[key].strip():
                declared = node[key]
                break
        nested = node.get("data")
        if isinstance(nested, dict) and isinstance(nested.get("asset_class"), str):
            declared = nested["asset_class"]
        if isinstance(config.get("asset_class"), str):
            declared = config["asset_class"]
        pnls, pnl_field = extract_trade_pnls(node)
        verdict = node.get("verdict")
        if isinstance(verdict, dict):
            verdict = verdict.get("status") or verdict.get("verdict") or verdict.get("pass")
        split = node.get("r1_time_split") or node.get("r1_split") or node.get("r1_timesplit")
        split_pass = None
        if isinstance(split, dict):
            split_pass = split.get("pass")
        notes = []
        if declared is None:
            notes.append("asset class inferred from filename/symbol only")
        if not pnls:
            notes.append("no trade log shipped — stated metrics only, not re-scored")
        records.append(_record(
            surface="backtest_json",
            strategy=strategy, symbol=symbol, claimed=declared, stats=stats,
            provenance={"kind": "file", "path": rel, "sha256": digest},
            generated_at=common_generated, source_verdict=verdict,
            split_half_pass=split_pass, trade_pnls=pnls, pnl_field=pnl_field,
            notes=notes,
        ))
    return records


def default_json_sources(root: Path = REPO_ROOT) -> list[Path]:
    patterns = [
        "reports/strategy_bt_*.json",
        "reports/backtest_path_forward*.json",
        "reports/*backtest*.json",
        "audit_dashboard/data/*backtest*.json",
        "audit_dashboard/data/backtest*.json",
        "copy_trader_intel/data/*backtest*.json",
        "baby_strategies/*backtest*.json",
    ]
    found: dict[str, Path] = {}
    for pattern in patterns:
        for hit in glob.glob(str(root / pattern)):
            p = Path(hit)
            if p.is_file() and p.suffix.lower() == ".json":
                found[str(p)] = p
    return sorted(found.values(), key=lambda p: str(p))


# ─────────────────────────────────────────────────────────────────── mysql ──
def _env(*names: str, default: str = "") -> str:
    for name in names:
        val = os.environ.get(name)
        if val:
            return val
    return default


def backtests_conn() -> Any:
    import pymysql  # local import: offline runs must not need the driver

    return pymysql.connect(
        host=_env("DB_HOST_BACKTESTS", "DB_BACKTESTS_HOST", "DB_HOST", default="mysql.50webs.com"),
        user=_env("DB_USER_BACKTESTS", "DB_BACKTESTS_USER", default="ejaguiar1_backtests"),
        password=_env("DB_PASS_BACKTESTS", "DB_BACKTESTS_PASSWORD", "MYSQL_PASSWORD"),
        database=_env("DB_NAME_BACKTESTS", "DB_BACKTESTS_NAME", default="ejaguiar1_backtests"),
        port=int(_env("DB_PORT_BACKTESTS", "DB_BACKTESTS_PORT", default="3306")),
        connect_timeout=20,
        read_timeout=60,
    )


DB_TABLES = {
    "bt_backtest_runs": {
        "strategy": "strategy", "symbol": "symbol", "claimed": "asset_class",
        "id": "id", "generated": "imported_at",
        "extra": ("source_db", "source_table"),
    },
    "at_large_backtest_results": {
        "strategy": "archetype", "symbol": "symbol", "claimed": None,
        "id": "id", "generated": "created_at",
        "extra": ("params_json", "avg_hold_bars", "slippage_pct", "commission_pct"),
    },
    "at_incubator_backtest_results": {
        "strategy": "archetype", "symbol": "symbol", "claimed": None,
        "id": "id", "generated": "created_at",
        "extra": ("params_json", "avg_hold_bars", "slippage_pct", "commission_pct"),
    },
}


def ingest_db(conn: Any, max_rows: int = 5000) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Read the three backtest result tables read-only, one query each."""
    api = conn.cursor()
    records: list[dict[str, Any]] = []
    tables: dict[str, Any] = {}
    for table, spec in DB_TABLES.items():
        try:
            api.execute(f"SHOW COLUMNS FROM {table}")
            cols = {row[0] for row in api.fetchall()}
            wanted = ["id", "strategy", "symbol", "asset_class", "total_trades", "wins",
                      "losses", "win_rate", "profit_factor", "total_return", "sharpe",
                      "max_drawdown", "created_at", "imported_at", "source_db",
                      "source_table", "avg_trade_pnl", "avg_hold_bars", "slippage_pct",
                      "commission_pct", "params_json"]
            select = [c for c in wanted if c in cols]
            api.execute(f"SELECT {', '.join(select)} FROM {table} LIMIT {int(max_rows)}")
            rows = api.fetchall()
            names = [d[0] for d in api.description]
        except Exception as exc:  # table missing / no permission: keep going
            tables[table] = {"error": str(exc)[:200], "rows": 0}
            continue
        added = 0
        for row in rows:
            raw = dict(zip(names, row))
            stats = stats_from_obj({
                **raw,
                "n": raw.get("total_trades"),
                "wr": raw.get("win_rate"),
                "pf": raw.get("profit_factor"),
                "mdd_pct": raw.get("max_drawdown"),
                "total_net_pct": raw.get("total_return"),
            })
            if not stats:
                continue
            extra = {k: (str(raw.get(k))[:300] if raw.get(k) is not None else None)
                     for k in spec["extra"] if k in raw}
            records.append(_record(
                surface=f"db:{table}",
                strategy=raw.get(spec["strategy"]), symbol=raw.get(spec["symbol"]),
                claimed=raw.get(spec["claimed"]) if spec["claimed"] else None,
                stats=stats,
                provenance={"kind": "table", "table": table, "row_id": raw.get("id"),
                            "column_class": raw.get("asset_class")},
                generated_at=raw.get(spec["generated"]),
                notes=[f"db row; extra={json.dumps(extra, sort_keys=True)[:200]}"]
                if extra else ["db row; stated metrics only"],
            ))
            added += 1
        tables[table] = {"rows": added, "columns_seen": len(cols)}
    return records, tables


# ───────────────────────────────────────────────────────────────── registry ──
def load_hypotheses(root: Path = REPO_ROOT) -> dict[str, Any]:
    path = root / "reports/hypothesis_registry.json"
    out: dict[str, Any] = {
        "registry_path": "reports/hypothesis_registry.json",
        "available": False, "total": 0,
        "canonical_counts": {}, "raw_counts": {}, "unmapped": [],
        "canonical_enum": list(CANONICAL_STATUSES),
        "rule": "M-107: pre-register before any backtest; a strategy with no "
                "registered hypothesis cannot be promoted past CANDIDATE.",
    }
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as exc:
        out["error"] = str(exc)[:200]
        return out
    hyps = data.get("hypotheses") or []
    out["available"] = True
    out["total"] = len(hyps)
    unmapped: dict[str, int] = {}
    for h in hyps:
        raw = h.get("status")
        canonical, exact = normalize_hypothesis_status(raw)
        out["canonical_counts"][canonical] = out["canonical_counts"].get(canonical, 0) + 1
        raw_key = str(raw)
        out["raw_counts"][raw_key] = out["raw_counts"].get(raw_key, 0) + 1
        if not exact:
            unmapped[raw_key] = unmapped.get(raw_key, 0) + 1
    out["unmapped"] = [{"raw": k, "count": v,
                        "canonical": normalize_hypothesis_status(k)[0]}
                       for k, v in sorted(unmapped.items(), key=lambda kv: -kv[1])]
    out["n_raw_spellings"] = len(out["raw_counts"])
    out["n_canonical"] = len(out["canonical_counts"])
    return out


def build_registry(records: Iterable[dict[str, Any]], sources: list[dict[str, Any]],
                   db_info: dict[str, Any], root: Path = REPO_ROOT) -> dict[str, Any]:
    recs: dict[str, dict[str, Any]] = {}
    for rec in records:
        recs.setdefault(rec["evidence_id"], rec)
    ordered = sorted(recs.values(),
                     key=lambda r: (-(r.get("n") or 0), r["surface"], r["strategy"]))

    by_surface: dict[str, int] = {}
    by_class: dict[str, int] = {}
    claimed_counts: dict[str, int] = {}
    strategies: dict[str, int] = {}
    mismatches: list[dict[str, Any]] = []
    retestable = 0
    with_trials = 0
    total_trades = 0
    for r in ordered:
        by_surface[r["surface"]] = by_surface.get(r["surface"], 0) + 1
        by_class[r["asset_class_derived"]] = by_class.get(r["asset_class_derived"], 0) + 1
        if r["asset_class_claimed"]:
            claimed_counts[r["asset_class_claimed"]] = claimed_counts.get(r["asset_class_claimed"], 0) + 1
        strategies[r["strategy"]] = 1
        if r["class_mismatch"]:
            mismatches.append({"strategy": r["strategy"], "symbol": r["symbol"],
                               "claimed": r["asset_class_claimed"],
                               "derived": r["asset_class_derived"],
                               "n": r["n"], "surface": r["surface"]})
        if r.get("recomputed"):
            retestable += 1
        if r.get("trial_count_N"):
            with_trials += 1
        total_trades += int(r.get("n") or 0)

    hyps = load_hypotheses(root)
    known_gaps = [
        "bt_backtest_trades holds ~32.7M rows and is NOT scanned here; full scans "
        "time out. Pre-aggregate by (strategy, symbol, class, month) first.",
        "Prior backtests are evidence, not verdicts: without a trade log or a "
        "timing-null price series they cannot be re-scored by the tribunal.",
        "Costs are only trusted when the source states them; recomputed numbers "
        "are gross and labelled cost_basis=unknown.",
        "RECOVERY_PROTOCOL.MD does not exist in this repo (referenced only from "
        "WIRED_IN prompts and .kilo worktrees).",
        "Forward/live rows remain the only inputs to the kill tribunal; this "
        "registry never promotes anything on its own.",
    ]
    return {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "module": "alpha_engine/audit3_evidence.py",
        "doctrine": {
            "name": "innocent-until-proven-guilty",
            "rule": "Prior evidence is registered, never deleted. A losing "
                    "backtest and a missing backtest are different things; only "
                    "the tribunal may retire a cell, and only on proven harm.",
        },
        "summary": {
            "n_records": len(ordered),
            "by_surface": dict(sorted(by_surface.items(), key=lambda kv: -kv[1])),
            "by_class_derived": dict(sorted(by_class.items(), key=lambda kv: -kv[1])),
            "by_class_claimed": dict(sorted(claimed_counts.items(), key=lambda kv: -kv[1])),
            "n_class_mismatches": len(mismatches),
            "n_strategies": len(strategies),
            "n_retestable_with_trade_log": retestable,
            "n_with_trial_count": with_trials,
            "total_trades_covered": total_trades,
            "n_sources": len(sources),
        },
        "class_mismatches": mismatches[:40],
        "sources": sources,
        "records": ordered,
        "hypotheses": hyps,
        "db": db_info,
        "known_gaps": known_gaps,
    }


def build(root: Path = REPO_ROOT, use_db: bool = True,
          json_paths: list[Path] | None = None,
          max_rows: int = 5000) -> dict[str, Any]:
    paths = json_paths if json_paths is not None else default_json_sources(root)
    records: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    for path in paths:
        got = ingest_json(path, root)
        if not got:
            continue
        records.extend(got)
        try:
            rel = str(path.relative_to(root))
        except ValueError:
            rel = str(path)
        sources.append({
            "path": rel,
            "bytes": path.stat().st_size,
            "sha256": got[0]["provenance"]["sha256"],
            "records": len(got),
        })

    db_info: dict[str, Any] = {"connected": False, "tables": {}}
    if use_db:
        try:
            conn = backtests_conn()
        except Exception as exc:
            db_info["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
        else:
            try:
                db_records, tables = ingest_db(conn, max_rows=max_rows)
                records.extend(db_records)
                db_info.update({"connected": True, "tables": tables,
                                "records": len(db_records)})
            except Exception as exc:
                db_info["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
    return build_registry(records, sources, db_info, root)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="audit3 evidence registry (P1)")
    ap.add_argument("--out", help="write registry JSON here (else stdout)")
    ap.add_argument("--no-db", action="store_true", help="skip MySQL ingestion")
    ap.add_argument("--max-rows", type=int, default=5000, help="row cap per table")
    ap.add_argument("--json", nargs="*", help="explicit JSON files to ingest")
    args = ap.parse_args(argv)
    paths = [Path(p) for p in args.json] if args.json else None
    reg = build(use_db=not args.no_db, json_paths=paths, max_rows=args.max_rows)
    if not reg["records"]:
        print("ERROR: no evidence records found", file=sys.stderr)
        return 2
    payload = json.dumps(reg, indent=1, allow_nan=False, default=str)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(payload + "\n")
        s = reg["summary"]
        print(f"wrote {args.out}: {s['n_records']} records, {s['n_strategies']} "
              f"strategies, {s['n_class_mismatches']} class mismatches, "
              f"db={'up' if reg['db'].get('connected') else 'down'}")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
