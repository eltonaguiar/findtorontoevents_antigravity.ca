"""PCG-5: Portfolio Construction Gate stack (shadow-mode Phase 1).

5 exec-time REJECT gates. See `DAILY_IDEAS.MD` 2026-05-12 entry for spec.

Phase 1 = SHADOW: log decisions to `audit_dashboard/data/pcg5_log.json`,
return verdict but DO NOT actually block. Caller decides whether to honor.

Phase 2 = ENFORCE: switch by setting env `PCG5_ENFORCE=1`. Default OFF.

Usage:
    from audit_trail.portfolio_gates import evaluate_pick

    verdict = evaluate_pick({
        "pick_id": "test-1",
        "account": "theswarm",
        "symbol": "NASDAQ:NVDA",
        "direction": "SHORT",
        "asset_class": "EQUITY",
        "size_usd": 4000,
    })
    # verdict: {"action": "APPROVE"|"REJECT"|"NET",
    #          "gate_results": [...], "reasons": [...]}
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "audit_dashboard" / "data"
PCG5_LOG_PATH = DATA_DIR / "pcg5_log.json"

PCG5_ENFORCE = os.environ.get("PCG5_ENFORCE", "0") == "1"

# Asset classes where Gate 1 applies (EQUITY-style, regime-directional)
GATE1_EQUITY_CLASSES = {"EQUITY", "ETF", "INDEX_STOCK"}

# Catalysts that override Gate 1 (allow equity-short in BULL with thesis)
GATE1_BEAR_CATALYSTS = {"earnings_miss", "downgrade", "fraud", "dilution",
                        "guidance_cut", "regulatory_block"}

# Gate 3 thresholds
GATE3_WARN_PCT = 50.0
GATE3_REJECT_PCT = 70.0

# Gate 4 thresholds
GATE4_PROFIT_LOCK_PCT = 3.0
# M-019: Portfolio MDD hard-cap per Charter §7 (Tier 2 MDD ≤ 20%).
# If total unrealized PnL of all_positions is < -GATE4_MDD_LIMIT_PCT, halt new entries.
# Kill-switch: PORTFOLIO_MDD_GATE_ENABLED=0. Default ON.
GATE4_MDD_LIMIT_PCT = 20.0

# Gate 5 correlation thresholds
GATE5_DEMOTE_CORR = 0.35
GATE5_REVERT_CORR = 0.20

# Canonical symbol map for Gate 2 (treat as same instrument)
CANONICAL_SYMBOL = {
    "BTC-USD": "BTC", "BTCUSDT": "BTC", "BTCUSDC.P": "BTC",
    "COINBASE:BTCUSDC.P": "BTC", "BINANCE:BTCUSDT": "BTC",
    "ETH-USD": "ETH", "ETHUSDT": "ETH", "ETHUSDC.P": "ETH",
    "COINBASE:ETHUSDC.P": "ETH", "BINANCE:ETHUSDT": "ETH",
    "ADA-USD": "ADA", "ADAUSDT": "ADA", "BINANCE:ADAUSDT": "ADA",
    "DOGE-USD": "DOGE", "DOGEUSDT": "DOGE", "DOGEUSDC.P": "DOGE",
    "BINANCE:DOGEUSDT": "DOGE", "COINBASE:DOGEUSDC.P": "DOGE",
    "SOL-USD": "SOL", "SOLUSDT": "SOL", "SOLUSDC.P": "SOL",
    "COINBASE:SOLUSDC.P": "SOL", "BINANCE:SOLUSDT": "SOL",
}


def canonical(symbol: str) -> str:
    if symbol in CANONICAL_SYMBOL:
        return CANONICAL_SYMBOL[symbol]
    if ":" in symbol:
        return symbol.split(":", 1)[1]
    return symbol


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _load_regime() -> str:
    """Read regime from STOCKSUNIFY2 or dashboard_data."""
    # STOCKSUNIFY2 current.json (preferred)
    sf2 = _load_json(REPO_ROOT / "alpha_engine" / "data" / "stocksunify2_current.json", {})
    if sf2 and "regime" in sf2:
        return sf2["regime"].get("status", "UNKNOWN").upper()
    d = _load_json(DATA_DIR / "dashboard_data.json", {})
    return d.get("performance", {}).get("regime", "UNKNOWN").upper()


def _load_concentration() -> dict:
    """Read asset_class_concentration from dashboard_data.json."""
    d = _load_json(DATA_DIR / "dashboard_data.json", {})
    return d.get("performance", {}).get("asset_class_concentration", {})


def _load_correlation() -> dict:
    """Read correlation_regime.json."""
    return _load_json(DATA_DIR / "correlation_regime.json", {})


def _spy_corr_per_class(corr_data: dict) -> dict[str, float]:
    """Extract current 30d corr vs EQUITY/SPY for each class."""
    if not corr_data:
        return {}
    classes = corr_data.get("classes_resolved", [])
    matrix = corr_data.get("current_correlation_matrix", [])
    if not classes or not matrix:
        return {}
    try:
        eq_idx = classes.index("EQUITY")
    except ValueError:
        return {}
    out = {}
    for i, c in enumerate(classes):
        if i == eq_idx:
            continue
        if i < len(matrix) and eq_idx < len(matrix[i]):
            out[c] = matrix[i][eq_idx]
    return out


def gate1_regime(pick: dict, regime: str | None = None) -> dict:
    """REGIME_DIRECTIONAL_GATE — reject equity-short in BULL (or LONG in BEAR)."""
    if regime is None:
        regime = _load_regime()
    cls = pick.get("asset_class", "")
    direction = pick.get("direction", "")
    catalyst = pick.get("thesis_catalyst", "")
    if cls not in GATE1_EQUITY_CLASSES:
        return {"gate": "1_regime", "verdict": "APPROVE", "reason": f"class={cls} not regime-gated"}
    if regime in {"BULL", "BULLISH"} and direction == "SHORT":
        if catalyst in GATE1_BEAR_CATALYSTS:
            return {"gate": "1_regime", "verdict": "APPROVE",
                    "reason": f"BULL+EQUITY+SHORT allowed (catalyst={catalyst})"}
        return {"gate": "1_regime", "verdict": "REJECT",
                "reason": f"BULL regime + EQUITY SHORT without bear catalyst"}
    if regime in {"BEAR", "BEARISH"} and direction == "LONG":
        if catalyst in GATE1_BEAR_CATALYSTS:
            return {"gate": "1_regime", "verdict": "APPROVE",
                    "reason": f"BEAR+EQUITY+LONG allowed (catalyst={catalyst})"}
        return {"gate": "1_regime", "verdict": "REJECT",
                "reason": f"BEAR regime + EQUITY LONG without bull catalyst"}
    return {"gate": "1_regime", "verdict": "APPROVE", "reason": f"regime={regime} dir={direction} OK"}


def gate2_cross_account(pick: dict, all_positions: list[dict]) -> dict:
    """CROSS_ACCOUNT_NET_POSITION — block offsetting / duplicate positions."""
    sym = canonical(pick.get("symbol", ""))
    direction = pick.get("direction", "")
    account = pick.get("account", "")
    for pos in all_positions:
        pos_sym = canonical(pos.get("symbol", ""))
        if pos_sym != sym:
            continue
        pos_dir = pos.get("direction", "")
        pos_acct = pos.get("account", "")
        if pos_acct == account and pos_dir == direction:
            return {"gate": "2_cross_account", "verdict": "REJECT",
                    "reason": f"duplicate {sym} {direction} same account {account}"}
        if pos_dir != direction:
            return {"gate": "2_cross_account", "verdict": "NET",
                    "reason": f"{sym} {pos_dir} on {pos_acct} offsets new {direction} on {account}"}
    return {"gate": "2_cross_account", "verdict": "APPROVE",
            "reason": f"no conflicts for {sym}"}


def gate3_concentration(pick: dict, concentration: dict | None = None) -> dict:
    """CONCENTRATION_REJECT — block adding to >50% top-share symbol in class."""
    if concentration is None:
        concentration = _load_concentration()
    cls = pick.get("asset_class", "")
    sym = canonical(pick.get("symbol", ""))
    cls_data = concentration.get(cls, {})
    if not isinstance(cls_data, dict):
        return {"gate": "3_concentration", "verdict": "APPROVE",
                "reason": f"no concentration data for class={cls}"}
    top_sym = canonical(cls_data.get("top_symbol", ""))
    share = float(cls_data.get("top_share_pct", 0))
    if not top_sym or top_sym != sym:
        return {"gate": "3_concentration", "verdict": "APPROVE",
                "reason": f"not the top symbol in {cls} (top={top_sym} share={share}%)"}
    if share >= GATE3_REJECT_PCT:
        return {"gate": "3_concentration", "verdict": "REJECT",
                "reason": f"{cls} class is {share}% {top_sym} (>= {GATE3_REJECT_PCT}%); rotate to class-cousin"}
    if share >= GATE3_WARN_PCT:
        return {"gate": "3_concentration", "verdict": "REJECT",
                "reason": f"{cls} class is {share}% {top_sym} ({GATE3_WARN_PCT}-{GATE3_REJECT_PCT}%); rotate to class-cousin"}
    return {"gate": "3_concentration", "verdict": "APPROVE",
            "reason": f"{cls} {top_sym} share {share}% below {GATE3_WARN_PCT}%"}


def gate4_profit_lock(pick: dict, all_positions: list[dict]) -> dict:
    """PROFIT_LOCK_SCAN — block new picks on account with unlocked >+3% positions.

    M-019: Also enforces Charter §7 Portfolio MDD hard-cap (≤ -20% total unrealized PnL
    across all positions). Kill-switch: PORTFOLIO_MDD_GATE_ENABLED=0.
    """
    account = pick.get("account", "")

    # M-019: Portfolio MDD hard-cap — Charter §7 Tier 2 (MDD ≤ 20%)
    _mdd_gate_on = os.environ.get("PORTFOLIO_MDD_GATE_ENABLED", "1") not in (
        "0", "false", "FALSE", "False"
    )
    if _mdd_gate_on and all_positions:
        _account_positions = [p for p in all_positions if p.get("account") == account]
        if _account_positions:
            _total_unrealized = sum(
                float(p.get("unrealized_pnl_pct") or 0) for p in _account_positions
            )
            _avg_unrealized = _total_unrealized / len(_account_positions)
            if _avg_unrealized < -GATE4_MDD_LIMIT_PCT:
                return {
                    "gate": "4_mdd_hard_cap",
                    "verdict": "REJECT",
                    "reason": (
                        f"M-019: portfolio MDD breached Charter §7 limit — "
                        f"avg_unrealized={_avg_unrealized:.1f}% < -{GATE4_MDD_LIMIT_PCT:.0f}% "
                        f"(n={len(_account_positions)} positions)"
                    ),
                }

    unlocked_winners = []
    for pos in all_positions:
        if pos.get("account") != account:
            continue
        pnl_pct = float(pos.get("unrealized_pnl_pct", 0))
        if pnl_pct < GATE4_PROFIT_LOCK_PCT:
            continue
        sl_at_be = pos.get("sl_at_breakeven", False)
        partial_taken = pos.get("partial_close_done", False)
        trailing = pos.get("trailing_stop_armed", False)
        if not (sl_at_be or partial_taken or trailing):
            unlocked_winners.append(
                f"{pos.get('symbol')} +{pnl_pct:.1f}% (no lock)"
            )
    if unlocked_winners:
        return {"gate": "4_profit_lock", "verdict": "REJECT",
                "reason": f"account {account} has unlocked winners: {unlocked_winners}"}
    return {"gate": "4_profit_lock", "verdict": "APPROVE",
            "reason": f"all account {account} winners locked"}


def gate5_correlation_demote(pick: dict, corr_data: dict | None = None) -> dict:
    """CROSS_CLASS_CORRELATION_DEMOTE — flag risk_on_beta status (no reject, sizing hint)."""
    if corr_data is None:
        corr_data = _load_correlation()
    cls = pick.get("asset_class", "")
    corr_by_class = _spy_corr_per_class(corr_data)
    # Map asset class to correlation_regime class name
    cls_map = {
        "COMMODITY": "COMMODITY_GOLD",
        "FUTURES": "FUTURES_COT",
        "BOND": "BOND",
        "CRYPTO": "CRYPTO",
        "ETF": "ETF_SMALLCAP",
        "FOREX": "FOREX_USD",
    }
    corr_cls = cls_map.get(cls, cls)
    corr = corr_by_class.get(corr_cls)
    if corr is None:
        return {"gate": "5_correlation", "verdict": "APPROVE",
                "reason": f"no corr data for class={cls}"}
    if abs(corr) >= GATE5_DEMOTE_CORR:
        return {"gate": "5_correlation", "verdict": "DEMOTE",
                "reason": f"{cls} corr-to-SPY = {corr:.2f} (>= {GATE5_DEMOTE_CORR}); "
                           f"sizing_role=risk_on_beta, halve size",
                "sizing_adjustment": 0.5}
    return {"gate": "5_correlation", "verdict": "APPROVE",
            "reason": f"{cls} corr-to-SPY = {corr:.2f} < {GATE5_DEMOTE_CORR}; diversifier intact"}


def evaluate_pick(pick: dict, all_positions: list[dict] | None = None) -> dict:
    """Run all 5 gates, return aggregated verdict + per-gate results.

    Shadow mode (default): returns verdict but caller is free to ignore.
    Enforce mode (PCG5_ENFORCE=1): caller is expected to honor REJECT.
    """
    if all_positions is None:
        all_positions = []
    results = [
        gate1_regime(pick),
        gate2_cross_account(pick, all_positions),
        gate3_concentration(pick),
        gate4_profit_lock(pick, all_positions),
        gate5_correlation_demote(pick),
    ]
    rejects = [r for r in results if r["verdict"] == "REJECT"]
    nets = [r for r in results if r["verdict"] == "NET"]
    demotes = [r for r in results if r["verdict"] == "DEMOTE"]
    if rejects:
        action = "REJECT"
    elif nets:
        action = "NET"
    elif demotes:
        action = "APPROVE_HALF"
    else:
        action = "APPROVE"
    verdict = {
        "pick_id": pick.get("pick_id", ""),
        "symbol": pick.get("symbol", ""),
        "account": pick.get("account", ""),
        "direction": pick.get("direction", ""),
        "action": action,
        "enforce_mode": PCG5_ENFORCE,
        "gate_results": results,
        "reasons": [r["reason"] for r in (rejects or nets or demotes or results)],
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }
    _append_log(verdict)
    return verdict


def _append_log(verdict: dict) -> None:
    """Append verdict to pcg5_log.json. Keeps last 1000 entries and caps at 5MB."""
    existing = _load_json(PCG5_LOG_PATH, [])
    # Support both list (legacy portfolio_gates format) and dict (pcg5_gates format)
    if isinstance(existing, dict):
        entries = existing.get("entries", [])
    elif isinstance(existing, list):
        entries = existing
    else:
        entries = []
    entries.append(verdict)
    # Rotate: keep last 1000 entries
    entries = entries[-1000:]
    out = {"shadow_mode": not PCG5_ENFORCE, "entries": entries}
    PCG5_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(out, indent=2, default=str)
    # Cap at 5MB — drop oldest half if over limit
    if len(serialized.encode("utf-8")) > 5 * 1024 * 1024:
        entries = entries[len(entries) // 2:]
        out["entries"] = entries
        serialized = json.dumps(out, indent=2, default=str)
    tmp = PCG5_LOG_PATH.with_suffix(PCG5_LOG_PATH.suffix + ".tmp")
    tmp.write_text(serialized, encoding="utf-8")
    os.replace(tmp, PCG5_LOG_PATH)


def evaluate_portfolio_gates(picks: list, context: dict | None = None) -> dict:
    """Batch-evaluate all 5 PCG gates across a list of picks.

    Shadow mode (PCG5_ENFORCE=0, default): logs verdicts but never filters.
    Enforce mode (PCG5_ENFORCE=1): caller should honor 'would_reject' list.

    Args:
        picks: list of pick dicts (same schema as active_picks.json)
        context: optional dict with keys:
            - 'all_positions': list of current open positions for gate2/gate4
            - 'regime': str override (skips file read)
            - 'concentration': dict override (skips file read)
            - 'corr_data': dict override (skips file read)

    Returns:
        {
            "gate_results": [list of per-pick verdict dicts],
            "would_reject": [list of pick symbols that failed at least one gate],
            "shadow_mode": True/False,
            "evaluated_at": ISO timestamp,
            "n_picks": int,
            "n_would_reject": int,
        }
    """
    if context is None:
        context = {}
    all_positions = context.get("all_positions", picks)  # use picks as positions if not provided
    regime = context.get("regime", None)
    concentration = context.get("concentration", None)
    corr_data = context.get("corr_data", None)

    # Pre-load shared data once (avoid repeated file reads per pick)
    if regime is None:
        regime = _load_regime()
    if concentration is None:
        concentration = _load_concentration()
    if corr_data is None:
        corr_data = _load_correlation()

    gate_results = []
    would_reject = []

    for pick in picks:
        try:
            results = [
                gate1_regime(pick, regime=regime),
                gate2_cross_account(pick, all_positions),
                gate3_concentration(pick, concentration=concentration),
                gate4_profit_lock(pick, all_positions),
                gate5_correlation_demote(pick, corr_data=corr_data),
            ]
            rejects = [r for r in results if r["verdict"] == "REJECT"]
            nets = [r for r in results if r["verdict"] == "NET"]
            demotes = [r for r in results if r["verdict"] == "DEMOTE"]
            if rejects:
                action = "REJECT"
            elif nets:
                action = "NET"
            elif demotes:
                action = "APPROVE_HALF"
            else:
                action = "APPROVE"
            verdict = {
                "pick_id": pick.get("pick_id", pick.get("id", "")),
                "symbol": pick.get("symbol", ""),
                "account": pick.get("account", ""),
                "direction": pick.get("direction", ""),
                "action": action,
                "enforce_mode": PCG5_ENFORCE,
                "shadow_mode": not PCG5_ENFORCE,
                "gate_results": results,
                "reasons": [r["reason"] for r in (rejects or nets or demotes or results[:1])],
                "evaluated_at": datetime.now(timezone.utc).isoformat(),
            }
            gate_results.append(verdict)
            if action == "REJECT":
                would_reject.append(pick.get("symbol", pick.get("pick_id", "")))
        except Exception as _e:
            # Fail-open: never let a gate error crash the caller
            gate_results.append({
                "pick_id": pick.get("pick_id", pick.get("id", "")),
                "symbol": pick.get("symbol", ""),
                "action": "APPROVE",
                "error": str(_e),
                "shadow_mode": True,
            })

    summary = {
        "gate_results": gate_results,
        "would_reject": would_reject,
        "shadow_mode": not PCG5_ENFORCE,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "n_picks": len(picks),
        "n_would_reject": len(would_reject),
    }
    # Log the batch summary as a single entry (avoid flooding the log with per-pick rows)
    _append_log({
        "type": "batch_summary",
        "n_picks": len(picks),
        "n_would_reject": len(would_reject),
        "would_reject_symbols": would_reject[:20],  # cap to avoid huge log entries
        "shadow_mode": not PCG5_ENFORCE,
        "evaluated_at": summary["evaluated_at"],
    })
    return summary


if __name__ == "__main__":
    # Smoke test
    test_pick = {
        "pick_id": "smoke-1",
        "account": "theswarm",
        "symbol": "NASDAQ:NVDA",
        "direction": "SHORT",
        "asset_class": "EQUITY",
    }
    v = evaluate_pick(test_pick, all_positions=[])
    print(json.dumps(v, indent=2))
