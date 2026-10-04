#!/usr/bin/env python3
# B5: Forward-Track Cell Selector (2026-06-24)
#
# Buckets audit pick-funnel sample into granular cells (asset_class \u00d7 strategy_base
# \u00d7 timeframe), applies forward-track filters (intrabar n\u226530, WR>50%, PF>1.0), ranks
# survivors by score = wr * pf * sqrt(n) and emits:
#
#   1. Canonical report     : reports/forward_track_candidates_<UTC>.json
#   2. Dashboard payload    : audit_dashboard/data/forward_track_candidates.json
#   3. Paper-trading module : paper_trading/strategies/forward_track_<cohort>_<UTC>.py
#                             (only when --emit-strategy and \u22651 cell passes)
#
# Usage:
#   python tools/select_forward_track_candidates.py
#   python tools/select_forward_track_candidates.py --min-n 20 --top-k 50
#   python tools/select_forward_track_candidates.py --cell-mode tier_a --min-n 15
#   python tools/select_forward_track_candidates.py --no-emit-strategy
from __future__ import annotations
import argparse, json, math, os, re, sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

TOOL_VERSION  = "b5-1.0.0"
TOOL_CREATED  = "2026-06-24"
INTRABAR_EXIT_REASONS = {"TP_HIT", "SL_HIT"}

# Recognised bars, in priority order (longest first)
TF_RE = re.compile(r"_(15m|30m|1h|2h|4h|6h|8h|12h|1d|1w)(?:_|\b|$)")

# Hand-curated default TF assignment for strategies whose name has no explicit bar.
# Operators: edit this map freely; UNKNOWN means 'do not auto-track this cell'.
DEFAULT_TF_MAP: Dict[str, str] = {
    "luxalgo_confluence":              "4h",
    "stocks_rsi2_pullback":            "1d",
    "stocks_rsi2_pullback_wide":       "1d",
    "futures_momentum":                "1d",
    "futures_connors_rsi2":            "1d",
    "futures_volume_breakout":         "1d",
    "rsi_vwap_contrarian":             "4h",
    "ema_momentum_volume":             "4h",
    "st_atr_vol_breakout":             "4h",
    "regime_strong_bull":              "1d",
    "regime_mild_bear":                "1d",
    "disposition_effect_contrarian":   "1d",
    "macd_crossover":                  "4h",
    "cvd_divergence":                  "4h",
    "hma_turtle":                      "4h",
    "ml_enhanced_BTCUSDT":             "1d",
    "ml_enhanced_ETHUSDT":             "1d",
    "ml_enhanced_SOLUSDT":             "1d",
    "cta_commodity_momentum_term":     "1d",
    "cta_cross_asset_tsmom":           "1d",
    "cta_donchian_55":                 "1d",
    "commodity_rsi_divergence":        "1d",
    "cot_positioning":                 "1w",
    "cftc_cot_commercial_signal":      "1w",
    "cg_whale_divergence":             "4h",
    "exchange_netflow":                "4h",
    "defi_tvl_momentum":               "1d",
    "fear_greed_contrarian":           "1d",
    "funding_rate_carry":              "4h",
    "clone_hl_copy_whale_13M_new":     "4h",
    "community_ema_9_21_rsi_crypto":   "4h",
    "cointegration_pairs":             "1d",
    "proven_futures_term_structure_proxy":"1d",
    "non_crypto_consensus":            "1d",
    "clone_hl_copy_pm_pm_":            "4h",
    "clone_hl_copy_pm_pm_6e1d5040":    "4h",
    "prediction_market_consensus":  "n/a",  # PM is not bar-based
    # Prefix rules (B5 coverage extension 2026-06-24 round-2):
    #   ml_enhanced_<SYMBOL>  bare-symbol variants from pick_funnel (~50 of them)
    #                          -> default to 1d swing when TF not in name
    "ml_enhanced_":                 "1d",
}

PF_CAP = 99.0   # cap infinite PF (wins=1, losses=0)


def extract_tf(strategy: str) -> str:
    """Extract TF from a strategy name. Returns UNKNOWN if not found."""
    if not strategy:
        return "UNKNOWN"
    m = TF_RE.search(strategy)
    if m:
        return m.group(1)
    if strategy in DEFAULT_TF_MAP:
        return DEFAULT_TF_MAP[strategy]
    for prefix, tf in DEFAULT_TF_MAP.items():
        if strategy.startswith(prefix):
            return tf
    return "UNKNOWN"


def strategy_base(strategy: str) -> str:
    """Strip the TF suffix from a strategy name to get its base form.
    Examples:
      ml_enhanced_RENDERUSDT_4h_D    -> ml_enhanced_RENDERUSDT_D
      ml_enhanced_RENDERUSDT         -> ml_enhanced_RENDERUSDT
      cta_donchian_55                -> cta_donchian_55
    """
    if not strategy:
        return strategy
    return TF_RE.sub("_", strategy, count=1).rstrip("_")


def load_pick_funnel(source_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Load pick_funnel_90d.json.

    When `source_path` is None, falls back to a list of candidate locations.
    When an explicit `source_path` is supplied it is treated as authoritative:
    if it doesn't exist the function raises FileNotFoundError WITHOUT falling
    back (B5 round-2: makes "raise on missing path" tests deterministic).
    """
    fallback_candidates = [
        Path("audit_dashboard/data/pick_funnel_90d.json"),
        Path("..") / "audit_dashboard" / "data" / "pick_funnel_90d.json",
        Path("/home/eaguiar2015/findtorontoevents_antigravity.ca/audit_dashboard/data/pick_funnel_90d.json"),
    ]
    candidates: List[Path] = (
        [source_path] if source_path is not None else fallback_candidates
    )
    tried: List[str] = []
    last_err = None
    for c in candidates:
        tried.append(str(c))
        try:
            if not c.exists():
                continue
            with c.open() as fh:
                blob = json.load(fh)
        except (json.JSONDecodeError, OSError) as e:
            last_err = e
            continue
        rows = blob.get("picks_sample")
        if rows is None and isinstance(blob, list):
            rows = blob
        if not isinstance(rows, list) or not rows:
            raise FileNotFoundError(
                f"{c} exists but contains an empty picks_sample list"
            )
        return rows
    raise FileNotFoundError(
        "pick_funnel_90d.json not located. Tried: " + ", ".join(tried)
        + (f" (last err: {last_err})" if last_err else "")
    )


def bucket_rows(
    rows: List[Dict[str, Any]],
    cell_mode: str = "tier_b",
) -> Dict[Tuple, Dict[str, Any]]:
    """Group rows by cell_key and compute per-cell aggregates.

    cell_mode:
      tier_a = (asset_class, strategy_base, symbol, timeframe)
      tier_b = (asset_class, strategy_base, timeframe)   [DEFAULT]
    """
    buckets: Dict[Tuple, Dict[str, Any]] = defaultdict(lambda: {"rows_buf": []})

    for r in rows:
        s = r.get("strategy") or "?"
        sb = strategy_base(s)
        tf = extract_tf(s)
        ac = (r.get("asset_class") or "UNKNOWN").upper()
        sym = r.get("symbol") or "?"
        key = (ac, sb, sym, tf) if cell_mode == "tier_a" else (ac, sb, tf)
        buckets[key]["rows_buf"].append({
            "pick_id": r.get("pick_id"),
            "pnl": r.get("pnl_pct"),
            "exit_reason": r.get("exit_reason") or "",
            "closed_at": r.get("closed_at"),
            "status": r.get("status") or "",
            "symbol": sym,
            "source_system": r.get("source_system"),
            "strategy": s,
        })

    out: Dict[Tuple, Dict[str, Any]] = {}
    for key, b in buckets.items():
        wins = losses = time_exits = unresolved = 0
        sum_win = sum_loss = 0.0
        symbol_set: set = set()
        source_set: set = set()
        pick_ids: List[str] = []
        last_seen: Optional[str] = None
        total_pnl_sum = 0.0
        total_pnl_n   = 0
        for row in b["rows_buf"]:
            pnl = row["pnl"]; er = row["exit_reason"]; sym = row["symbol"]
            rid = row["pick_id"]; close = row["closed_at"]; st = row["status"]
            # only count intrabar-resolved rows in wr/pf numerator
            if er in INTRABAR_EXIT_REASONS:
                if pnl is None:
                    unresolved += 1
                else:
                    pf_val = float(pnl)
                    total_pnl_sum += pf_val; total_pnl_n += 1
                    if pf_val > 0:
                        wins += 1; sum_win += pf_val
                    else:
                        losses += 1; sum_loss += abs(pf_val)
            elif er == "TIME_EXIT":
                time_exits += 1
                if pnl is not None:
                    total_pnl_sum += float(pnl); total_pnl_n += 1
            else:
                # absent/active/etc \u2014 unresolved
                unresolved += 1
            if sym and sym != "?":
                symbol_set.add(sym)
            if row["source_system"]:
                source_set.add(row["source_system"])
            if rid:
                pick_ids.append(str(rid))
            if close:
                last_seen = close if not last_seen else max(last_seen, close)

        n_intrabar = wins + losses
        wr = (wins / n_intrabar) if n_intrabar else 0.0
        pf = (sum_win / sum_loss) if sum_loss > 0 else (PF_CAP if wins > 0 else 0.0)
        avg_pnl = (total_pnl_sum / total_pnl_n) if total_pnl_n else 0.0
        # composite score: wr * pf * sqrt(n_intrabar); UNKNOWN cells get score=0
        if tf == "UNKNOWN":
            score = 0.0
        else:
            score = wr * pf * math.sqrt(n_intrabar) if n_intrabar else 0.0

        if cell_mode == "tier_a":
            ac_k, sb_k, sym_k, tf_k = key
        else:
            ac_k, sb_k, tf_k = key; sym_k = ""

        out[key] = {
            "cell_key":              list(key),
            "cell_mode":             cell_mode,
            "asset_class":           ac_k,
            "strategy_base":         sb_k,
            "symbol":                sym_k,
            "timeframe":             tf_k,
            "n_total":               len(b["rows_buf"]),
            "n_intrabar":            n_intrabar,
            "wins":                  wins,
            "losses":                losses,
            "time_exits":            time_exits,
            "unresolved":            unresolved,
            "sum_win_pnl":           round(sum_win, 6),
            "sum_loss_abs_pnl":      round(sum_loss, 6),
            "wr":                    round(wr, 6),
            "pf":                    round(pf, 6),
            "avg_pnl":               round(avg_pnl, 6),
            "score":                 round(score, 6),
            "symbols":               sorted(symbol_set),
            "source_systems":        sorted(source_set),
            "last_seen":             last_seen,
            "pick_ids_sample":       pick_ids[:50],  # size cap
        }
    return out


def filter_and_rank(
    cells: Dict[Tuple, Dict[str, Any]],
    min_n: int,
    min_wr: float,
    min_pf: float,
    top_k: int,
) -> List[Dict[str, Any]]:
    """Filter cells by min thresholds, rank by score, return top-k."""
    survivors: List[Dict[str, Any]] = []
    for c in cells.values():
        if c["timeframe"] == "UNKNOWN":
            continue
        if c["n_intrabar"] < min_n:
            continue
        if c["wr"] < min_wr:
            continue
        if c["pf"] < min_pf:
            continue
        survivors.append(c)
    def _ls_key(ls: Optional[str]) -> int:
        """Convert ISO date (closed_at) to int for DESC tiebreaker via negation.

        Empty / malformed dates sort LAST (treated as 0).
        """
        if not ls:
            return 0
        try:
            return int(ls[:10].replace("-", ""))
        except Exception:
            return 0

    survivors.sort(
        key=lambda c: (
            -c["score"],
            -c["pf"],
            -c["n_intrabar"],
            -_ls_key(c["last_seen"]),  # DESC of date via negation; newer wins
        ),
    )
    return survivors[:top_k]


def emit_strategy_module(
    survivors: List[Dict[str, Any]],
    cohort_tag: str,
    utc_stamp: str,
) -> str:
    """Generate a paper_trading module skeleton from the top-ranked cells.

    Emits ONE class per top cell so operators can run each independently.
    Skeleton ONLY \u2014 generate_signals proxies to a placeholder; real wiring is
    downstream work (B5 followups).
    """
    # symbol union + TF union
    all_symbols: set = set()
    tf_dist: Dict[str, int] = defaultdict(int)
    asset_classes: set = set()
    for c in survivors:
        for s in c["symbols"]:
            all_symbols.add(s)
        tf_dist[c["timeframe"]] += 1
        asset_classes.add(c["asset_class"])
    primary_tf = max(tf_dist, key=tf_dist.get) if tf_dist else "1h"

    safe_cohort = re.sub(r"[^A-Za-z0-9_]", "_", cohort_tag or "auto")[:32] or "auto"
    class_lines: List[str] = []
    for c in survivors[:10]:   # cap to 10 classes per module
        class_name = "FwdTrack_" + re.sub(r"[^A-Za-z0-9_]", "_", c["strategy_base"])[:48].rstrip("_") + ("_" + c["timeframe"] if c["timeframe"] else "")
        sym_literal = repr(sorted(c["symbols"]))
        class_lines.append(f'''
class {class_name}(BaseStrategy):
    """Auto-generated forward-track class for cell {c["cell_key"]}.

    Stats (intrabar): n={c["n_intrabar"]}  wr={c["wr"]}  pf={c["pf"]}  score={c["score"]}
    Asset class: {c["asset_class"]}  Timeframe: {c["timeframe"]}  Strategy base: {c["strategy_base"]}
    Last seen: {c["last_seen"]}
    """
    name = "{c["strategy_base"]}_{c["timeframe"]}_fwdtrack"
    display_name = "Fwd-Track {c["strategy_base"]} {c["timeframe"]}"
    source = "Forward-Track Cohort {safe_cohort} (B5 auto)"
    category = "{c["asset_class"].lower()}"
    portfolio_type = "technical"
    symbols = {sym_literal}

    def fetch_data(self, symbol=None):
        return self.fetch_klines(symbol, interval="{c["timeframe"]}", limit=250)

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        # Placeholder \u2014 B5 followup wires the original strategy_cls.generate_signals()
        return []
''')

    sym_union_lit = repr(sorted(all_symbols))
    primary_tf_lit = repr(primary_tf)
    module = f'''"""
Auto-generated by `tools/select_forward_track_candidates.py` on {utc_stamp}.
Cohort tag : {safe_cohort}
Top cells  : {len(survivors)}
Asset mix  : {sorted(asset_classes)}
Primary TF : {primary_tf}
Symbol union : {len(all_symbols)} unique symbols across the cohort

This is a SKELETON. Replace `generate_picks()` with a real alpha_engine proxy
against the corresponding strategy_base to enable live signal production.
"""
from typing import List
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick

# Cohort identity
COHORT_TAG = "{safe_cohort}"
GENERATED_AT = "{utc_stamp}"
GENERATOR_VERSION = "{TOOL_VERSION}"

# A flat symbol union captured across ALL top cells
COHORT_SYMBOLS = {sym_union_lit}
COHORT_PRIMARY_TF = {primary_tf_lit}
''' + '\n\n\n# === per-cell classes ===\n' + '\n'.join(class_lines)

    return module


def main() -> int:
    ap = argparse.ArgumentParser(description="Forward-Track Cell Selector (B5)")
    ap.add_argument("--source-path", default="", help="Path to pick_funnel_90d.json (default: auto-discover)")
    ap.add_argument("--min-n", type=int,   default=30,  help="Minimum intrabar n to qualify a cell")
    ap.add_argument("--min-wr", type=float, default=0.50, help="Minimum win-rate")
    ap.add_argument("--min-pf", type=float, default=1.0,  help="Minimum profit factor")
    ap.add_argument("--top-k", type=int,   default=25, help="Emit at most K top cells")
    ap.add_argument("--cell-mode", choices=("tier_a", "tier_b"), default="tier_b",
                    help="tier_a=(ass,strat,sym,tf) ; tier_b=(ass,strat,tf) [FALLBACK when full cells too sparse]")
    ap.add_argument("--cohort-tag", default="auto", help="Cohort id embedded in emitted module path")
    ap.add_argument("--out-report",    default="", help="Override canonical report path")
    ap.add_argument("--out-dashboard", default="", help="Override dashboard payload path")
    ap.add_argument("--out-strategy",  default="", help="Override emitted strategy module path")
    ap.add_argument("--emit-strategy",  action="store_true", default=True,  help="Emit forward_track_<cohort>.py module on success")
    ap.add_argument("--no-emit-strategy", dest="emit_strategy", action="store_false",
                    help="Disable paper-trading module emission (report + dashboard only)")
    ap.add_argument("--reports-dir",  default="reports", help="Reports dir for canonical report")
    ap.add_argument("--dry-run", action="store_true", help="Compute + filter but write nothing")
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    src = Path(args.source_path) if args.source_path else None
    if src is None:
        print(f"[B5] source: auto-discover (no --source-path supplied)", file=sys.stderr)
    else:
        print(f"[B5] source: {src} (explicit --source-path)", file=sys.stderr)
    rows = load_pick_funnel(src)
    print(f"[B5] source: {src}  rows: {len(rows)}", file=sys.stderr)

    cells = bucket_rows(rows, cell_mode=args.cell_mode)
    print(f"[B5] cells: {len(cells)} ({args.cell_mode})", file=sys.stderr)

    survivors = filter_and_rank(cells, args.min_n, args.min_wr, args.min_pf, args.top_k)
    print(f"[B5] survivors: {len(survivors)}  (min_n={args.min_n} min_wr={args.min_wr} min_pf={args.min_pf})", file=sys.stderr)

    utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_cohort = re.sub(r"[^A-Za-z0-9_]", "_", args.cohort_tag or "auto")[:32] or "auto"

    # 1) canonical report
    payload = {
        "tool_version":  TOOL_VERSION,
        "tool_created":  TOOL_CREATED,
        "generated_at":  utc,
        "source":        "audit_dashboard/data/pick_funnel_90d.json",
        "cell_mode":     args.cell_mode,
        "filters":       {"min_n": args.min_n, "min_wr": args.min_wr, "min_pf": args.min_pf, "top_k": args.top_k},
        "counts": {
            "rows": len(rows),
            "cells": len(cells),
            "raw_survivors": sum(1 for c in cells.values() if c["n_intrabar"] >= args.min_n and c["timeframe"] != "UNKNOWN"),
            "cohort_survivors": len(survivors),
        },
        "cells":     [c for c in cells.values()],   # all observed cells, sorted by score desc
        "cohort":    survivors,                      # filter-passing cells, rank-ordered
    }
    payload["cells"].sort(key=lambda c: -c["score"])

    if args.dry_run:
        print(json.dumps({"cohort_count": len(survivors), "cohort": [c["cell_key"] for c in survivors]}, indent=2)[:1500])
        return 0 if survivors else 1

    # write canonical report
    report_dir = repo_root / args.reports_dir
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = Path(args.out_report) if args.out_report else (report_dir / f"forward_track_candidates_{utc}.json")
    with report_path.open("w") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1, default=str)
    print(f"[B5] wrote report: {report_path}", file=sys.stderr)

    # write dashboard payload (always overwrites \u2014 last-writer-wins by utc stamp)
    dash_path = Path(args.out_dashboard) if args.out_dashboard else (repo_root / "audit_dashboard" / "data" / "forward_track_candidates.json")
    dash_path.parent.mkdir(parents=True, exist_ok=True)
    with dash_path.open("w") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1, default=str)
    print(f"[B5] wrote dashboard: {dash_path}", file=sys.stderr)

    # 3) emit paper-trading module
    if args.emit_strategy and survivors:
        module_src = emit_strategy_module(survivors, safe_cohort, utc)
        strat_path = Path(args.out_strategy) if args.out_strategy else (
            repo_root / "paper_trading" / "strategies" / f"forward_track_{safe_cohort}_{utc}.py"
        )
        strat_path.parent.mkdir(parents=True, exist_ok=True)
        with strat_path.open("w") as fh:
            fh.write(module_src)
        print(f"[B5] wrote strategy module: {strat_path}", file=sys.stderr)

    # summary
    if survivors:
        print(json.dumps({
            "ok": True,
            "cohort_count": len(survivors),
            "top_5": [
                {"cell_key": c["cell_key"], "n": c["n_intrabar"], "wr": c["wr"], "pf": c["pf"], "score": c["score"]}
                for c in survivors[:5]
            ],
        }, indent=2))
        return 0
    else:
        print(json.dumps({"ok": False, "reason": "no cells passed filters", "min_n": args.min_n, "min_wr": args.min_wr, "min_pf": args.min_pf, "cell_mode": args.cell_mode}, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
