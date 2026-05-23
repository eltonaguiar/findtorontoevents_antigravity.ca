"""
Pick Provenance Index — tools/pick_provenance_index.py

Traces pick lineage from JSON source → emitter script → GitHub Action.
Outputs a compact JSON map (~50-200KB) that an agent swarm can load to
answer "where does this pick come from?" without reading the full codebase.

Usage:
    python tools/pick_provenance_index.py [--out reports/provenance_index.json] [--pretty]
    python tools/pick_provenance_index.py --pick LTCUSDT:ml_enhanced  # single-pick trace

Output schema:
    {
      "generated_at": "...",
      "pick_sources": {             # JSON files → picks count + sample
          "alpha_engine/data/active_picks.json": {...}
      },
      "source_systems": {           # source_system → emitter script + workflow + gate status
          "ml_strategy_reviver": {...}
      },
      "strategies": {               # strategy → asset_class + gate verdicts + WR/PF
          "ml_enhanced_LTCUSDT_4h_A_xgboost": {...}
      },
      "picks": [                    # per-pick provenance (active picks only)
          {"id": "...", "lineage": {...}}
      ],
      "gate_topology": {            # quality_gates.py BLOCKED/MONITORED lists
          "blocked_strategies": [...],
          "blocked_symbols": [...],
          "monitored_futures": [...]
      },
      "workflow_map": {             # source_system → GitHub Actions workflow
          "ml_strategy_reviver": ["ml-strategy-reviver", "alpha-engine-live"]
      }
    }
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent

# ── Pick source JSON files (ordered by priority) ───────────────────────────

PICK_SOURCE_FILES: dict[str, str] = {
    "alpha_engine/data/active_picks.json": "active",
    "alpha_engine/data/active_picks_fast.json": "active_fast",
    "alpha_engine/data/closed_picks.json": "closed",
    "alpha_engine/data/closed_picks_fast.json": "closed_fast",
    "alpha_engine/data/incubator_picks.json": "incubator",
    "alpha_engine/data/connors_rsi2_signals.json": "connors_rsi2",
    "alpha_engine/data/expired_picks_archive.json": "expired",
    "alpha_engine/data/gainer_capture_picks.json": "gainer_capture",
    "alpha_engine/data/dna_reviver_picks.json": "dna_reviver",
    "alpha_engine/data/maplestax_picks.json": "maplestax",
    "alpha_engine/data/ml_reviver_picks.json": "ml_reviver",
    "alpha_engine/data/mutation_picks.json": "mutation",
    "alpha_engine/data/momentum_tracker_picks.json": "momentum_tracker",
}

# ── Source system → emitter script + workflow (manually curated) ────────────

SOURCE_SYSTEM_MAP: dict[str, dict] = {
    "ml_crypto_predictor": {
        "emitter_script": "ml_crypto_predictor/fetch_and_populate_db.py",
        "workflows": ["enhanced-ml-crypto", "baby-strat-forward-paper"],
        "description": "ML crypto prediction models (XGBoost/LightGBM per symbol+timeframe)",
    },
    "ml_strategy_reviver": {
        "emitter_script": "alpha_engine/ml_strategy_reviver.py",
        "workflows": ["alpha-engine-live", "ml-strategy-reviver"],
        "description": "Revives low-performing strategies via ML signal boosting",
    },
    "ml_strategy_reviver_inverse": {
        "emitter_script": "alpha_engine/ml_strategy_reviver.py",
        "workflows": ["alpha-engine-live", "ml-strategy-reviver"],
        "description": "Inverse side of ml_strategy_reviver picks",
    },
    "multi_asset_copytrader": {
        "emitter_script": "copy_trader_intel/multi_asset_copytrader_scraper.py",
        "workflows": ["multi-asset-scanner"],
        "description": "Copies trades from top-ranked traders across all asset classes",
    },
    "cta_replicator": {
        "emitter_script": "alpha_engine/cta_replication_engine.py",
        "workflows": ["alpha-engine-live"],
        "description": "CTA (commodity trading advisor) strategy replication",
    },
    "combined_confidence_strategy": {
        "emitter_script": "alpha_engine/combined_confidence_strategy.py",
        "workflows": ["audit-dashboard"],
        "description": "Multi-signal confidence aggregation strategy",
    },
    "bond_scanner": {
        "emitter_script": "alpha_engine/bond_scanner.py",
        "workflows": ["alpha-engine-bond"],
        "description": "Bond yield signal scanner (Connors RSI2 on TLT/IEF/BND)",
    },
    "multi_asset_cot": {
        "emitter_script": "alpha_engine/multi_asset_cot_strategy.py",
        "workflows": ["alpha-engine-live"],
        "description": "COT (Commitment of Traders) signal-based strategy",
    },
    "prediction_market_agents": {
        "emitter_script": "alpha_engine/prediction_market_agents.py",
        "workflows": ["alpha-engine-live"],
        "description": "Prediction market consensus signals (Polymarket/Kalshi)",
    },
    "cta_commodity_ml_enhanced": {
        "emitter_script": "alpha_engine/cta_replication_engine.py",
        "workflows": ["alpha-engine-live"],
        "description": "ML-enhanced CTA replication for COMMODITY",
    },
    "futures_momentum": {
        "emitter_script": "alpha_engine/futures_momentum_strategy.py",
        "workflows": ["alpha-engine-fast"],
        "description": "Futures momentum strategy (MONITORED — zero-sizing)",
    },
}

# ── Gate topology extraction ─────────────────────────────────────────────────

def _extract_gate_topology() -> dict:
    """Read quality_gates.py and extract blocked/monitored lists."""
    qg_path = _REPO / "audit_trail" / "quality_gates.py"
    if not qg_path.exists():
        return {}

    content = qg_path.read_text(encoding="utf-8", errors="ignore")

    def _extract_list_after(marker: str, max_chars: int = 8000) -> list[str]:
        idx = content.find(marker)
        if idx < 0:
            return []
        chunk = content[idx : idx + max_chars]
        return re.findall(r'"([a-zA-Z0-9_\-\.]+)"', chunk)[:200]

    def _extract_dict_keys_after(marker: str, max_chars: int = 4000) -> list[str]:
        """Extract top-level string keys from a dict literal (key: { ... })."""
        idx = content.find(marker)
        if idx < 0:
            return []
        # Find opening brace of the dict
        brace_start = content.find("{", idx)
        if brace_start < 0:
            return []
        chunk = content[brace_start : brace_start + max_chars]
        # Keys at depth 1 are followed by ': {'
        return re.findall(r'^\s+"([a-zA-Z0-9_]+)"\s*:', chunk, re.MULTILINE)[:50]

    blocked_strategies = _extract_list_after("BLOCKED_ASSET_STRATEGY_PAIRS")
    blocked_source_systems = _extract_list_after("BLOCKED_SOURCE_SYSTEMS")
    blocked_symbols = _extract_list_after("BLOCKED_SYMBOLS")
    monitored_futures = _extract_dict_keys_after("MONITORED_FUTURES_STRATEGIES")

    # Find line numbers of key gate functions
    gate_lines: dict[str, int] = {}
    for fn in ["passes_active_gate", "passes_smart_gate", "tag_futures_monitor",
               "is_futures_monitored", "passes_direction_gate"]:
        m = re.search(rf"^def {fn}\(", content, re.MULTILINE)
        if m:
            gate_lines[fn] = content[: m.start()].count("\n") + 1

    return {
        "blocked_asset_strategy_pairs_sample": blocked_strategies[:50],
        "blocked_source_systems": blocked_source_systems[:30],
        "blocked_symbols": blocked_symbols[:50],
        "monitored_futures_strategies": monitored_futures[:20],
        "gate_function_lines": gate_lines,
        "quality_gates_path": "audit_trail/quality_gates.py",
        "quality_gates_lines": content.count("\n"),
    }

# ── Workflow map builder ──────────────────────────────────────────────────────

def _build_workflow_map() -> dict[str, list[str]]:
    """Scan .github/workflows for source_system mentions and script invocations."""
    wf_dir = _REPO / ".github" / "workflows"
    if not wf_dir.exists():
        return {}

    result: dict[str, list[str]] = {}

    for wf_file in sorted(wf_dir.glob("*.yml")):
        content = wf_file.read_text(encoding="utf-8", errors="ignore")
        wf_stem = wf_file.stem

        # Direct source_system= occurrences
        systems = re.findall(r'source_system[=:\s"\']+([a-z_][a-z0-9_]+)', content)
        for s in systems:
            if s not in ("source_system", "none", "str", "optional", "true", "false"):
                result.setdefault(s, [])
                if wf_stem not in result[s]:
                    result[s].append(wf_stem)

        # Script names that match known emitters
        for source, meta in SOURCE_SYSTEM_MAP.items():
            script_basename = Path(meta["emitter_script"]).stem
            if script_basename in content:
                result.setdefault(source, [])
                if wf_stem not in result[source]:
                    result[source].append(wf_stem)

    return result

# ── Pick source file reader ───────────────────────────────────────────────────

def _read_pick_file(rel_path: str) -> tuple[list[dict], dict]:
    """Read a pick source file; return (picks, summary)."""
    path = _REPO / rel_path
    if not path.exists():
        return [], {"exists": False}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [], {"exists": True, "error": str(exc)}

    if not isinstance(data, list):
        return [], {"exists": True, "format": "non-list", "keys": list(data.keys())[:5] if isinstance(data, dict) else []}

    picks = [p for p in data if isinstance(p, dict) and "symbol" in p]

    # Summarize by source_system + asset_class
    by_source: dict[str, int] = {}
    by_class: dict[str, int] = {}
    statuses: dict[str, int] = {}

    for p in picks:
        s = p.get("source_system") or "unknown"
        ac = p.get("asset_class") or p.get("category") or "unknown"
        st = p.get("status") or "unknown"
        by_source[s] = by_source.get(s, 0) + 1
        by_class[ac] = by_class.get(ac, 0) + 1
        statuses[st] = statuses.get(st, 0) + 1

    return picks, {
        "exists": True,
        "total": len(picks),
        "by_source_system": dict(sorted(by_source.items(), key=lambda x: -x[1])[:10]),
        "by_asset_class": dict(sorted(by_class.items(), key=lambda x: -x[1])),
        "by_status": statuses,
        "mtime": datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(),
    }

# ── Per-pick lineage tracer ───────────────────────────────────────────────────

def _trace_pick_lineage(pick: dict, workflow_map: dict, gate_topology: dict) -> dict:
    """Build a lineage record for a single pick."""
    source = pick.get("source_system") or "unknown"
    strategy = pick.get("strategy") or "unknown"
    symbol = pick.get("symbol") or "?"
    asset_class = pick.get("asset_class") or pick.get("category") or "unknown"

    meta = SOURCE_SYSTEM_MAP.get(source, {})
    workflows = workflow_map.get(source, meta.get("workflows", []))

    blocked_strats = gate_topology.get("blocked_asset_strategy_pairs_sample", [])
    blocked_sources = gate_topology.get("blocked_source_systems", [])
    blocked_syms = gate_topology.get("blocked_symbols", [])
    monitored = gate_topology.get("monitored_futures_strategies", [])

    gate_flags: list[str] = []
    if strategy in blocked_strats:
        gate_flags.append("BLOCKED_STRATEGY")
    if source in blocked_sources:
        gate_flags.append("BLOCKED_SOURCE")
    if symbol in blocked_syms:
        gate_flags.append("BLOCKED_SYMBOL")
    if source in monitored:
        gate_flags.append("FUTURES_MONITORED_ZERO_SIZING")

    lifecycle_id = pick.get("_pick_lifecycle_id", "")

    return {
        "id": pick.get("id") or f"{strategy}::{symbol}",
        "symbol": symbol,
        "strategy": strategy,
        "asset_class": asset_class,
        "direction": pick.get("direction") or pick.get("signal_type") or "?",
        "status": pick.get("status") or "UNKNOWN",
        "confidence": pick.get("confidence"),
        "elite_score": pick.get("elite_score"),
        "trust_label": pick.get("trust_label"),
        "created_at": pick.get("created_at") or pick.get("timestamp"),
        "lineage": {
            "source_system": source,
            "emitter_script": meta.get("emitter_script", f"alpha_engine/{source}.py"),
            "emitter_description": meta.get("description", ""),
            "github_actions": workflows[:3],
            "source_json": "alpha_engine/data/active_picks.json",
            "gate_path": "audit_trail/quality_gates.py::passes_active_gate()",
            "gate_flags": gate_flags,
            "lifecycle_id": lifecycle_id,
            "traceable_via_db": bool(lifecycle_id),
        },
    }

# ── Main builder ──────────────────────────────────────────────────────────────

def build_index(include_closed: bool = False) -> dict:
    gate_topology = _extract_gate_topology()
    workflow_map = _build_workflow_map()

    # Read all pick source files
    pick_sources: dict[str, dict] = {}
    all_active_picks: list[dict] = []

    for rel_path, label in PICK_SOURCE_FILES.items():
        picks, summary = _read_pick_file(rel_path)
        summary["label"] = label
        pick_sources[rel_path] = summary

        if label == "active":
            all_active_picks = picks
        elif label == "active_fast" and not all_active_picks:
            all_active_picks = picks

    # Build per-pick lineage for active picks only (closed too large)
    provenance_picks = [
        _trace_pick_lineage(p, workflow_map, gate_topology)
        for p in all_active_picks
    ]

    # Aggregate source system stats across active picks
    source_systems: dict[str, dict] = {}
    for p in all_active_picks:
        src = p.get("source_system") or "unknown"
        ac = p.get("asset_class") or "unknown"
        meta = SOURCE_SYSTEM_MAP.get(src, {})

        if src not in source_systems:
            source_systems[src] = {
                "emitter_script": meta.get("emitter_script", f"alpha_engine/{src}.py"),
                "description": meta.get("description", ""),
                "github_actions": workflow_map.get(src, meta.get("workflows", [])),
                "active_pick_count": 0,
                "asset_classes": {},
                "is_blocked": src in gate_topology.get("blocked_source_systems", []),
                "is_monitored_futures": src in gate_topology.get("monitored_futures_strategies", []),
            }

        source_systems[src]["active_pick_count"] += 1
        ac_counts = source_systems[src]["asset_classes"]
        ac_counts[ac] = ac_counts.get(ac, 0) + 1

    # Aggregate strategy stats
    strategies: dict[str, dict] = {}
    for p in all_active_picks:
        strat = p.get("strategy") or "unknown"
        ac = p.get("asset_class") or "unknown"
        conf = p.get("confidence") or 0
        elite = p.get("elite_score") or 0

        if strat not in strategies:
            strategies[strat] = {
                "asset_class": ac,
                "source_system": p.get("source_system") or "unknown",
                "active_count": 0,
                "avg_confidence": 0.0,
                "avg_elite_score": 0.0,
                "_conf_sum": 0.0,
                "_elite_sum": 0.0,
                "gate_blocked": strat in gate_topology.get("blocked_asset_strategy_pairs_sample", []),
            }

        strategies[strat]["active_count"] += 1
        strategies[strat]["_conf_sum"] += conf
        strategies[strat]["_elite_sum"] += elite

    for strat, data in strategies.items():
        n = data["active_count"]
        if n > 0:
            data["avg_confidence"] = round(data.pop("_conf_sum") / n, 3)
            data["avg_elite_score"] = round(data.pop("_elite_sum") / n, 1)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo": str(_REPO),
        "summary": {
            "active_picks": len(all_active_picks),
            "active_source_systems": len(source_systems),
            "active_strategies": len(strategies),
            "pick_files_indexed": len(pick_sources),
            "blocked_source_systems": len(gate_topology.get("blocked_source_systems", [])),
            "blocked_symbols": len(gate_topology.get("blocked_symbols", [])),
        },
        "pick_sources": pick_sources,
        "source_systems": source_systems,
        "strategies": dict(sorted(strategies.items(), key=lambda x: -x[1]["active_count"])[:100]),
        "picks": provenance_picks,
        "gate_topology": gate_topology,
        "workflow_map": {k: v for k, v in workflow_map.items() if v},
        "source_system_map": {k: {kk: vv for kk, vv in v.items() if kk != "workflows"}
                               for k, v in SOURCE_SYSTEM_MAP.items()},
    }


def trace_single_pick(symbol_strategy: str) -> dict | None:
    """Quick lineage trace for a single pick by 'symbol:strategy' or just 'symbol'."""
    active_path = _REPO / "alpha_engine" / "data" / "active_picks.json"
    if not active_path.exists():
        return None

    picks = json.loads(active_path.read_text(encoding="utf-8"))
    parts = symbol_strategy.split(":", 1)
    sym = parts[0].upper()
    strat_filter = parts[1] if len(parts) > 1 else ""

    matches = [
        p for p in picks
        if isinstance(p, dict)
        and p.get("symbol", "").upper() == sym
        and (not strat_filter or strat_filter in p.get("strategy", ""))
    ]

    if not matches:
        return None

    gate_topology = _extract_gate_topology()
    workflow_map = _build_workflow_map()

    return [_trace_pick_lineage(p, workflow_map, gate_topology) for p in matches]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build pick provenance index")
    parser.add_argument("--out", default="reports/provenance_index.json",
                        help="Output JSON path (default: reports/provenance_index.json)")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON (indent=2)")
    parser.add_argument("--pick", metavar="SYMBOL[:STRATEGY]",
                        help="Trace a single pick and print result")
    parser.add_argument("--summary", action="store_true", help="Print summary only, no file write")
    args = parser.parse_args()

    if args.pick:
        result = trace_single_pick(args.pick)
        if result is None:
            print(f"No active pick found for: {args.pick}")
            sys.exit(1)
        print(json.dumps(result, indent=2, default=str))
        return

    print("Building pick provenance index...")
    index = build_index()

    if args.summary:
        print(json.dumps(index["summary"], indent=2))
        print("\nSource systems:")
        for src, data in sorted(index["source_systems"].items(), key=lambda x: -x[1]["active_pick_count"]):
            flags = []
            if data["is_blocked"]:
                flags.append("BLOCKED")
            if data["is_monitored_futures"]:
                flags.append("MONITORED")
            flag_str = f" [{','.join(flags)}]" if flags else ""
            wfs = ",".join(data["github_actions"][:2]) or "unknown"
            print(f"  {src}{flag_str}: {data['active_pick_count']} picks → {wfs}")
        return

    out_path = _REPO / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    indent = 2 if args.pretty else None
    out_path.write_text(json.dumps(index, indent=indent, default=str), encoding="utf-8")

    kb = out_path.stat().st_size / 1024
    print(f"Provenance index written: {out_path} ({kb:.1f}KB)")
    print(f"  Active picks: {index['summary']['active_picks']}")
    print(f"  Source systems: {index['summary']['active_source_systems']}")
    print(f"  Strategies: {index['summary']['active_strategies']}")
    print(f"  Gate: quality_gates.py ({index['gate_topology'].get('quality_gates_lines', 0):,} lines)")


if __name__ == "__main__":
    main()
