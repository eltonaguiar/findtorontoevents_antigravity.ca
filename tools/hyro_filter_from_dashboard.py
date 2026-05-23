#!/usr/bin/env python3
"""
hyro_filter_from_dashboard.py
Reads dashboard_data.json (URL or local), filters picks to Hyro-safe USDT perps,
applies prop firm gates, scores them, calculates position sizes, writes hyrotrader_picks.json.

Preserves challenge / playbook / account_snapshot from the existing hyrotrader_picks.json
when present so audit/hyrotrader/index.html keeps working. If challenge/playbook are missing,
fills from tools/hyrotrader_merge_defaults.json.

Usage:
  python tools/hyro_filter_from_dashboard.py
  python tools/hyro_filter_from_dashboard.py --local audit_dashboard/data/dashboard_data.json
  python tools/hyro_filter_from_dashboard.py --account 5000 --daily-used 0 --overall-used 141
  python tools/hyro_filter_from_dashboard.py --equity 4929.34 --day-start-equity 5000 --cumulative-pnl -70.66 --high-water 5070.3
  python tools/hyro_filter_from_dashboard.py --save
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

WORKSPACE = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = WORKSPACE / "audit_dashboard" / "data" / "hyrotrader_picks.json"
DEFAULT_DASHBOARD_LOCAL = WORKSPACE / "audit_dashboard" / "data" / "dashboard_data.json"
DEFAULT_JOURNAL = WORKSPACE / "audit_dashboard" / "data" / "hyrotrader_journal.json"
MERGE_DEFAULTS_JSON = Path(__file__).resolve().parent / "hyrotrader_merge_defaults.json"

# 2026-04-11: mirror of alpha_engine/smart_picks_engine._apply_winrate_filter.
# Hyrotrader picks should get the same label normalization + confidence gate
# + blacklist treatment as the smart_picks pool. Config lives in
# alpha_engine/data/winrate_filter_config.json.
_WINRATE_CFG_PATH = WORKSPACE / "alpha_engine" / "data" / "winrate_filter_config.json"
_WINRATE_FILTER_MODE = os.environ.get("WINRATE_FILTER_MODE", "shadow").lower()


def _load_winrate_cfg() -> dict:
    try:
        return json.loads(_WINRATE_CFG_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


_HYRO_WINRATE_CFG = _load_winrate_cfg()


def _to_float_safe(v, default: float = 0.0) -> float:
    try:
        return float(v) if v is not None else default
    except (TypeError, ValueError):
        return default


def _apply_hyro_winrate_filter(picks: list) -> tuple[list, dict]:
    """Mirror of smart_picks_engine._apply_winrate_filter for hyrotrader picks.

    Always applies BUY->LONG / SELL->SHORT normalization (data bug fix).
    In strict mode also rejects picks failing min_confidence, strategy
    blacklist, or symbol blacklist.
    """
    if not _HYRO_WINRATE_CFG:
        return picks, {"mode": "disabled", "reason": "no_config_file"}

    thresholds = _HYRO_WINRATE_CFG.get("thresholds", {}) or {}
    min_conf = float(thresholds.get("min_confidence", 0.0))
    strat_blacklist = set(_HYRO_WINRATE_CFG.get("strategy_blacklist", []) or [])
    symbol_blacklist = set(_HYRO_WINRATE_CFG.get("symbol_blacklist", []) or [])

    label_normalized = 0
    rejected_low_conf = 0
    rejected_blacklist = 0
    admitted: list = []

    for p in picks:
        direction_raw = str(p.get("direction") or p.get("side") or "").upper()
        if direction_raw == "BUY":
            p["direction"] = "LONG"
            label_normalized += 1
        elif direction_raw == "SELL":
            p["direction"] = "SHORT"
            label_normalized += 1

        # Hyrotrader picks use confidence_pct (0-100) not confidence (0-1).
        # Normalize: if confidence missing but confidence_pct present, divide by 100.
        raw_conf = p.get("confidence")
        if raw_conf is None and p.get("confidence_pct") is not None:
            try:
                raw_conf = float(p.get("confidence_pct")) / 100.0
            except (TypeError, ValueError):
                raw_conf = 0
        try:
            conf = float(raw_conf or 0)
        except (TypeError, ValueError):
            conf = 0.0

        strat = str(p.get("strategy") or p.get("source_system") or "").strip()
        # Hyrotrader uses symbol_hint; fall back to that if symbol is None.
        sym_raw = p.get("symbol") or p.get("symbol_hint") or ""
        sym = str(sym_raw).strip().upper()
        sym_bare = sym.split(":")[-1] if ":" in sym else sym

        if conf < min_conf:
            rejected_low_conf += 1
            if _WINRATE_FILTER_MODE != "strict":
                admitted.append(p)
            continue
        if strat in strat_blacklist:
            rejected_blacklist += 1
            if _WINRATE_FILTER_MODE != "strict":
                admitted.append(p)
            continue
        if sym_bare in symbol_blacklist:
            rejected_blacklist += 1
            if _WINRATE_FILTER_MODE != "strict":
                admitted.append(p)
            continue
        admitted.append(p)

    stats = {
        "mode": _WINRATE_FILTER_MODE,
        "min_confidence": min_conf,
        "strategy_blacklist_size": len(strat_blacklist),
        "symbol_blacklist_size": len(symbol_blacklist),
        "total_in": len(picks),
        "label_normalized": label_normalized,
        "would_reject_low_conf": rejected_low_conf,
        "would_reject_blacklist": rejected_blacklist,
        "admitted": len(admitted),
    }
    return admitted, stats

HYRO_DEFAULTS = {
    "account_size": 5000,
    "max_risk_pct": 3,
    "max_daily_loss_pct": 5,
    "max_overall_loss_pct": 10,
    "consistency_rule_pct": 40,
    "phase1_target_pct": 10,
    "phase2_target_pct": 5,
    "min_trading_days": 10,
    "recommended_risk_pct": 0.75,
    "min_rr": 1.5,             # raised from 1.2 — canonical data shows 1.6x win/loss ratio needed for edge
    "min_ml_score": 0.50,     # lowered from 0.55 — was filtering out some proven winners
    "min_confidence": 0.50,   # lowered from 0.55 — same reason
    "max_age_hours": 48,
}

BYBIT_USDT_SYMBOLS = {
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT",
    "MATICUSDT", "NEARUSDT", "ARBUSDT", "OPUSDT", "SUIUSDT",
    "APTUSDT", "PEPEUSDT", "WIFUSDT", "FILUSDT", "INJUSDT",
    "AAVEUSDT", "LTCUSDT", "ETCUSDT", "ATOMUSDT", "HBARUSDT",
    "ALGOUSDT", "SEIUSDT", "TONUSDT", "TIAUSDT", "SHIBUSDT",
    "APEUSDT", "STRKUSDT", "JTOUSDT", "ZKUSDT", "ZROUSDT",
    "RENDERUSDT", "FETUSDT", "WLDUSDT", "STXUSDT", "IMXUSDT",
    "RUNEUSDT", "GALAUSDT", "SANDUSDT", "MANAUSDT", "AXSUSDT",
    "CFXUSDT", "ORDIUSDT", "PENDLEUSDT", "BLURUSDT", "JUPUSDT",
    "PYTHUSDT", "DYMUSDT", "ALTUSDT", "METISUSDT", "MANTAUSDT",
}

DASHBOARD_URL = "https://findtorontoevents.ca/audit/data/dashboard_data.json"


def fetch_dashboard(source: str | None) -> dict:
    if source and os.path.isfile(source):
        with open(source, encoding="utf-8") as f:
            return json.load(f)

    if source and source.startswith("http"):
        url = source
    else:
        url = DASHBOARD_URL

    req = Request(url, headers={"User-Agent": "hyro-filter/1.0"})
    try:
        with urlopen(req, timeout=45) as resp:
            return json.loads(resp.read().decode())
    except URLError as e:
        print(f"ERROR: Failed to fetch {url}: {e}", file=sys.stderr)
        sys.exit(1)


def is_hyro_compatible(pick: dict) -> tuple[bool, str]:
    if pick.get("asset_class") != "CRYPTO":
        return False, "not CRYPTO"

    symbol = (pick.get("symbol") or "").upper()
    if not symbol.endswith("USDT"):
        return False, f"not USDT pair ({symbol})"

    if symbol not in BYBIT_USDT_SYMBOLS:
        return False, f"{symbol} not in Bybit USDT perp list"

    if not pick.get("entry_price") or not pick.get("stop_loss") or not pick.get("take_profit"):
        return False, "missing entry/SL/TP"

    if pick.get("paper_trade"):
        return False, "paper trade"

    rr = pick.get("rr_ratio") or 0
    if rr < HYRO_DEFAULTS["min_rr"]:
        return False, f"R:R {rr:.2f} < {HYRO_DEFAULTS['min_rr']}"

    ml = pick.get("ml_score", 0) or 0
    if ml < HYRO_DEFAULTS["min_ml_score"]:
        return False, f"ml_score {ml:.3f} < {HYRO_DEFAULTS['min_ml_score']}"

    conf = pick.get("confidence", 0) or 0
    if conf < HYRO_DEFAULTS["min_confidence"]:
        return False, f"confidence {conf:.3f} < {HYRO_DEFAULTS['min_confidence']}"

    age = pick.get("age_hours")
    if age is None:
        age = 999
    if age > HYRO_DEFAULTS["max_age_hours"]:
        return False, f"age {age:.1f}h > {HYRO_DEFAULTS['max_age_hours']}h"

    # Sim 2026-04-10: BTC-short stopped out against 8 correct LONG calls
    # Hedge SHORTs on BTC/ETH are redundant in strong uptrends — skip them
    _direction = (pick.get("direction") or "").upper()
    _regime = str(pick.get("regime", "")).lower()
    if (_direction == "SHORT"
            and symbol in ("BTCUSDT", "ETHUSDT")
            and _regime in ("strong_uptrend", "uptrend", "bull")):
        return False, f"SHORT on {symbol} blocked in {_regime} regime (2026-04-10 sim)"

    # ── Compound edge filter (2026-04-14) ──
    # Verified on dashboard_data.json: trust>=3 AND score>=50 AND LONG lifts
    # crypto PF from 1.57 → 3.09 (58.6% WR, 307 picks, CI lower bound 53%).
    # Stable across all time windows (Q2-Q4). This is the single highest-leverage
    # quality gate available — doubles the profit factor.
    _trust = float(pick.get("trust_score") or 0)
    _score = float(pick.get("score") or 0)

    if _trust < 3:
        return False, f"trust_score {_trust:.0f} < 3 (compound edge filter)"

    if _score < 50:
        return False, f"score {_score:.0f} < 50 (compound edge filter)"

    if _direction == "SHORT":
        # SHORT crypto picks have PF=1.08 vs LONG PF=1.57 on definitive exits.
        # For prop challenge safety, require higher bar for shorts.
        if _trust < 5 or _score < 60:
            return False, f"SHORT requires trust>=5 AND score>=60 (got trust={_trust:.0f}, score={_score:.0f})"

    return True, "passed"


def calc_position_size(pick: dict, account_size: float, risk_pct: float) -> dict | None:
    entry = pick.get("entry_price", 0)
    sl = pick.get("stop_loss", 0)

    if not entry or not sl or entry == sl:
        return None

    risk_amount = account_size * (risk_pct / 100)
    price_risk = abs(entry - sl)

    if price_risk == 0:
        return None

    size = risk_amount / price_risk
    position_value = size * entry

    return {
        "risk_amount_usdt": round(risk_amount, 2),
        "price_risk": round(price_risk, 6),
        "size": round(size, 6),
        "position_value_usdt": round(position_value, 2),
    }


def calc_hyro_score(pick: dict) -> float:
    ml = (pick.get("ml_score") or 0) * 100
    conf = (pick.get("confidence") or 0) * 100
    rr = pick.get("rr_ratio") or 1.0
    rr_score = min(100, max(0, (rr - 1.0) * 60))

    regime = pick.get("regime", "neutral")
    direction = pick.get("direction", "LONG")
    if (direction == "LONG" and regime == "bull") or (direction == "SHORT" and regime == "bear"):
        regime_score = 100
    elif regime == "neutral":
        regime_score = 50
    else:
        regime_score = 0

    fwd_wr = pick.get("forward_wr") or 0
    if fwd_wr > 1:
        fwd_wr = fwd_wr / 100
    fwd_score = min(100, fwd_wr * 150)

    safety = pick.get("safety_score") or 50
    if safety <= 1:
        safety = safety * 100
    safety = min(100, safety)

    raw = (
        ml * 0.33
        + conf * 0.27
        + rr_score * 0.15
        + regime_score * 0.10
        + fwd_score * 0.10
        + safety * 0.05
    )

    return round(min(100, max(0, raw)), 1)


def check_daily_consistency(pick: dict, account_size: float, daily_profit_so_far: float = 0) -> tuple[bool, float]:
    phase1_max_daily = (
        account_size
        * HYRO_DEFAULTS["phase1_target_pct"]
        / 100
        * HYRO_DEFAULTS["consistency_rule_pct"]
        / 100
    )

    entry = pick.get("entry_price", 0)
    tp = pick.get("take_profit", 0)

    if not entry or not tp:
        return True, 0.0

    pos = calc_position_size(pick, account_size, HYRO_DEFAULTS["recommended_risk_pct"])
    if not pos:
        return True, 0.0

    size = pos["size"]
    potential_profit = abs(tp - entry) * size

    remaining_daily_cap = phase1_max_daily - daily_profit_so_far

    if potential_profit > remaining_daily_cap:
        return False, round(potential_profit, 2)

    return True, round(potential_profit, 2)


def filter_and_score(dashboard_data: dict, args: argparse.Namespace) -> tuple[list, list, int]:
    picks = dashboard_data.get("picks", {}).get("active", [])
    scanned = len(picks)

    account_size = args.account
    daily_used = args.daily_used
    overall_used = args.overall_used

    max_risk_usdt = account_size * HYRO_DEFAULTS["max_risk_pct"] / 100
    daily_remaining = account_size * HYRO_DEFAULTS["max_daily_loss_pct"] / 100 - daily_used
    overall_remaining = account_size * HYRO_DEFAULTS["max_overall_loss_pct"] / 100 - overall_used

    results: list[dict] = []
    rejected: list[dict] = []

    for pick in picks:
        compatible, reason = is_hyro_compatible(pick)
        if not compatible:
            rejected.append({"symbol": pick.get("symbol"), "reason": reason})
            continue

        pos_conservative = calc_position_size(pick, account_size, HYRO_DEFAULTS["recommended_risk_pct"])
        pos_max = calc_position_size(pick, account_size, HYRO_DEFAULTS["max_risk_pct"])

        if not pos_conservative or not pos_max:
            rejected.append({"symbol": pick.get("symbol"), "reason": "could not calc position"})
            continue

        if pos_max["position_value_usdt"] > account_size * 5:
            rejected.append(
                {
                    "symbol": pick.get("symbol"),
                    "reason": f"position too large: ${pos_max['position_value_usdt']:.0f}",
                }
            )
            continue

        if pos_max["risk_amount_usdt"] > max_risk_usdt + 0.01:
            rejected.append(
                {"symbol": pick.get("symbol"), "reason": "max risk slot exceeds Hyro 3% at this SL distance"}
            )
            continue

        consistency_ok, potential_profit = check_daily_consistency(pick, account_size)
        hyro_score = calc_hyro_score(pick)

        results.append(
            {
                "symbol": pick["symbol"],
                "direction": pick["direction"],
                "entry_price": pick["entry_price"],
                "stop_loss": pick["stop_loss"],
                "take_profit": pick["take_profit"],
                "rr_ratio": pick.get("rr_ratio"),
                "ml_score": pick.get("ml_score"),
                "confidence": pick.get("confidence"),
                "elite_score": pick.get("elite_score"),
                "regime": pick.get("regime"),
                "strategy": pick.get("strategy"),
                "system": pick.get("system"),
                "forward_wr": pick.get("forward_wr"),
                "forward_trades": pick.get("forward_trades"),
                "age_hours": pick.get("age_hours"),
                "tp_remaining_pct": pick.get("tp_remaining_pct"),
                "hyro_score": hyro_score,
                "position_conservative": pos_conservative,
                "position_max": pos_max,
                "max_risk_usdt": round(max_risk_usdt, 2),
                "daily_drawdown_remaining": round(daily_remaining, 2),
                "overall_drawdown_remaining": round(overall_remaining, 2),
                "consistency_ok": consistency_ok,
                "potential_profit_at_tp": potential_profit,
                "consistency_cap_phase1": round(
                    account_size
                    * HYRO_DEFAULTS["phase1_target_pct"]
                    / 100
                    * HYRO_DEFAULTS["consistency_rule_pct"]
                    / 100,
                    2,
                ),
                "source_pick_id": pick.get("id"),
            }
        )

    results.sort(key=lambda x: x["hyro_score"], reverse=True)
    return results, rejected, scanned


def load_merge_base(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def load_journal(path: Path | None = None) -> dict:
    path = path or DEFAULT_JOURNAL
    if not path.is_file():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _existing_pick_index(merge_base: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for pick in merge_base.get("picks", []) or []:
        pick_id = pick.get("id")
        if isinstance(pick_id, str) and pick_id:
            out[pick_id] = pick
    return out


def _symbol_dir_key(symbol: str | None, direction: str | None) -> str:
    return f"{(symbol or '').upper()}|{(direction or '').upper()}"


def _existing_pick_symbol_dir_index(merge_base: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for pick in merge_base.get("picks", []) or []:
        key = _symbol_dir_key(pick.get("symbol_hint") or pick.get("symbol"), pick.get("direction"))
        if key != "|":
            out[key] = pick
    return out


def _journal_pick_index(journal: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for trade in journal.get("trades", []) or []:
        pick_id = trade.get("pick_id")
        if isinstance(pick_id, str) and pick_id:
            out[pick_id] = trade
    return out


def _journal_pick_symbol_dir_index(journal: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for trade in journal.get("trades", []) or []:
        key = _symbol_dir_key(trade.get("symbol"), trade.get("direction"))
        if key != "|":
            out[key] = trade
    return out


def _apply_execution_state(pick_out: dict, existing_pick: dict | None, journal_trade: dict | None) -> None:
    existing_pick = existing_pick or {}
    journal_trade = journal_trade or {}
    if journal_trade:
        pick_out["symbol_hint"] = journal_trade.get("symbol") or pick_out.get("symbol_hint")
        pick_out["entry_price"] = journal_trade.get("entry_price")
        pick_out["stop_loss"] = journal_trade.get("stop_loss")
        pick_out["take_profit"] = journal_trade.get("take_profit")
        pick_out["opened_at"] = journal_trade.get("entry_time")
        pick_out["closed_at"] = journal_trade.get("closed_at")
        pick_out["pnl_pct"] = journal_trade.get("pnl_pct")
        pick_out["pnl_usdt"] = journal_trade.get("pnl_usdt")
        pick_out["exit_price"] = journal_trade.get("exit_price")
        pick_out["exit_reason"] = journal_trade.get("exit_reason")
        pick_out["position_size_usdt"] = journal_trade.get("position_size_usdt")
        pick_out["risk_amount_usdt"] = journal_trade.get("risk_amount_usdt")
        pick_out["sl_confirmed"] = journal_trade.get("stop_loss") is not None
        pick_out["status"] = "closed" if journal_trade.get("status") == "closed" else "open"
        return

    if existing_pick:
        for field in (
            "entry_price",
            "stop_loss",
            "take_profit",
            "opened_at",
            "closed_at",
            "pnl_pct",
            "pnl_usdt",
            "exit_price",
            "exit_reason",
            "position_size_usdt",
            "risk_amount_usdt",
        ):
            if existing_pick.get(field) is not None:
                pick_out[field] = existing_pick.get(field)
        if existing_pick.get("status") in {"open", "closed"}:
            pick_out["status"] = existing_pick.get("status")
        if existing_pick.get("sl_confirmed") is not None:
            pick_out["sl_confirmed"] = bool(existing_pick.get("sl_confirmed"))


def _derive_account_state_from_journal(journal: dict, snap: dict) -> dict:
    trades = journal.get("trades", []) or []
    closed = [t for t in trades if t.get("status") == "closed"]
    open_trades = [t for t in trades if t.get("status") == "open"]
    today_realized = sum(_to_float_safe(t.get("pnl_usdt")) for t in closed)
    today_unrealized = 0.0
    if "today_realized_pnl_usdt" not in snap:
        snap["today_realized_pnl_usdt"] = round(today_realized, 2)
    if "today_unrealized_pnl_usdt" not in snap:
        snap["today_unrealized_pnl_usdt"] = round(today_unrealized, 2)
    snap["journal_trade_count"] = len(trades)
    snap["journal_open_trade_count"] = len(open_trades)
    snap["journal_closed_trade_count"] = len(closed)
    if closed:
        wins = sum(1 for t in closed if _to_float_safe(t.get("pnl_usdt")) > 0)
        snap["journal_closed_win_rate_pct"] = round((wins / len(closed)) * 100.0, 1)
        snap["journal_realized_pnl_usdt"] = round(sum(_to_float_safe(t.get("pnl_usdt")) for t in closed), 2)
    return snap


def build_output(
    results: list,
    args: argparse.Namespace,
    merge_base: dict,
    dashboard_url: str,
    journal: dict,
) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    account_size = args.account
    daily_remaining = account_size * HYRO_DEFAULTS["max_daily_loss_pct"] / 100 - args.daily_used
    overall_remaining = account_size * HYRO_DEFAULTS["max_overall_loss_pct"] / 100 - args.overall_used

    picks_out: list[dict] = []
    existing_by_id = _existing_pick_index(merge_base)
    existing_by_symdir = _existing_pick_symbol_dir_index(merge_base)
    journal_by_id = _journal_pick_index(journal)
    journal_by_symdir = _journal_pick_symbol_dir_index(journal)
    for i, r in enumerate(results[:20]):
        # 2026-04-10 sim: take 50% off at ~1R to lock profit
        _entry = r.get("entry_price")
        _tp = r.get("take_profit")
        _dir = (r.get("direction") or "LONG").upper()
        if _entry is not None and _tp is not None:
            try:
                if _dir == "SHORT":
                    _partial_tp = round(float(_entry) - (float(_entry) - float(_tp)) * 0.45, 8)
                else:
                    _partial_tp = round(float(_entry) + (float(_tp) - float(_entry)) * 0.45, 8)
            except (TypeError, ValueError):
                _partial_tp = None
        else:
            _partial_tp = None

        pick_id = f"hyro-{now[:10]}-{r['symbol'].replace('USDT', '').lower()}"
        symdir = _symbol_dir_key(r["symbol"], r["direction"])
        existing_pick = existing_by_symdir.get(symdir) or existing_by_id.get(pick_id)
        journal_trade = journal_by_symdir.get(symdir) or journal_by_id.get(pick_id)
        if journal_trade and journal_trade.get("pick_id"):
            pick_id = journal_trade["pick_id"]
        elif existing_pick and existing_pick.get("id"):
            pick_id = existing_pick["id"]
        pick_out = {
                "id": pick_id,
                "rank": i + 1,
                "asset_class": "CRYPTO",
                "label": r["symbol"].replace("USDT", ""),
                "symbol_hint": r["symbol"],
                "direction": r["direction"],
                "confidence_pct": round((r.get("confidence") or 0) * 100, 1),
                "hyro_score": r["hyro_score"],
                "timeframe": "SWING",
                "thesis": (
                    f"Strategy: {r.get('strategy', '?')} | ml={r.get('ml_score', 0):.3f} | "
                    f"fwd={r.get('forward_wr', 0)} | regime={r.get('regime', '?')} | system={r.get('system', '?')}"
                ),
                "entry_price": r["entry_price"],
                "stop_loss": r["stop_loss"],
                "take_profit": r["take_profit"],
                "partial_tp": _partial_tp,  # 2026-04-10 sim: take 50% off at ~1R to lock profit
                "rr_ratio": r["rr_ratio"],
                "position_size_conservative": r["position_conservative"],
                "position_size_max": r["position_max"],
                "status": "planned",
                "opened_at": None,
                "closed_at": None,
                "pnl_pct": None,
                "sl_confirmed": False,
                "consistency_ok": r["consistency_ok"],
                "potential_profit_at_tp": r["potential_profit_at_tp"],
                "source_pick_id": r.get("source_pick_id"),
                "stop_plan": "Levels from dashboard — confirm on Hyro/chart before entry; SL on exchange within ~5 min.",
                "take_profit_plan": "Partial per playbook; watch trailing DD on unrealized highs.",
            }
        _apply_execution_state(pick_out, existing_pick, journal_trade)
        picks_out.append(pick_out)

    challenge = merge_base.get("challenge")
    if not isinstance(challenge, dict):
        challenge = {}

    playbook = merge_base.get("playbook")
    if not isinstance(playbook, dict):
        playbook = {}

    if not challenge or not playbook:
        defaults = load_merge_base(MERGE_DEFAULTS_JSON)
        if not challenge:
            c = defaults.get("challenge")
            if isinstance(c, dict) and c:
                challenge = c
        if not playbook:
            p = defaults.get("playbook")
            if isinstance(p, dict) and p:
                playbook = p

    snap: dict = {}
    if isinstance(merge_base.get("account_snapshot"), dict):
        snap = dict(merge_base["account_snapshot"])

    if args.equity is not None:
        snap["equity_usdt"] = args.equity
    if args.day_start_equity is not None:
        snap["day_start_equity_usdt"] = args.day_start_equity
    if args.cumulative_pnl is not None:
        snap["cumulative_pnl_usdt"] = args.cumulative_pnl
    if args.high_water is not None:
        snap["high_water_equity_usdt"] = args.high_water
    if args.trading_days is not None:
        snap["trading_days_logged"] = args.trading_days

    snap.setdefault("challenge_start_equity_usdt", account_size)
    snap["daily_drawdown_used_usdt"] = args.daily_used
    snap["daily_drawdown_remaining_usdt"] = round(daily_remaining, 2)
    snap["overall_drawdown_used_usdt"] = args.overall_used
    snap["overall_drawdown_remaining_usdt"] = round(overall_remaining, 2)
    snap["filter_last_run_utc"] = now
    snap = _derive_account_state_from_journal(journal, snap)

    out: dict = {
        "generated_at": now,
        "source": "hyro_filter_from_dashboard.py",
        "dashboard_url": dashboard_url,
        "challenge": challenge,
        "account_snapshot": snap,
        "playbook": playbook,
        "picks": picks_out,
    }
    return out


def print_summary(results: list, rejected: list, scanned: int, args: argparse.Namespace) -> None:
    print(f"\n{'=' * 60}")
    print("  HYRO FILTER RESULTS")
    print(f"{'=' * 60}")
    print(f"  Total active picks scanned:  {scanned}")
    print(f"  Passed Hyro gates:           {len(results)}")
    print(f"  Rejected:                    {len(rejected)}")
    print(f"  Account (reference):         ${args.account}")
    print(f"  Daily DD remaining:          ${args.account * 5 / 100 - args.daily_used:.2f}")
    print(f"  Overall DD remaining:        ${args.account * 10 / 100 - args.overall_used:.2f}")
    print(f"  Max risk per trade:          ${args.account * 3 / 100:.2f}")
    print(f"  Conservative risk per trade: ${args.account * 0.75 / 100:.2f}")
    print(f"{'=' * 60}\n")

    if not results:
        print("  No picks passed Hyro filters.")
        return

    print("  TOP PICKS (by Hyro score):\n")
    print(f"  {'#':<3} {'Symbol':<12} {'Dir':<6} {'Score':<6} {'ML':<6} {'Conf':<6} {'R:R':<5} {'Strategy'}")
    print(f"  {'-' * 3} {'-' * 12} {'-' * 6} {'-' * 6} {'-' * 6} {'-' * 6} {'-' * 5} {'-' * 30}")

    for i, r in enumerate(results[:15]):
        ml = f"{r.get('ml_score', 0):.3f}" if r.get("ml_score") else "—"
        conf = f"{r.get('confidence', 0):.2f}" if r.get("confidence") else "—"
        strat = (r.get("strategy") or "?")[:30]
        print(
            f"  {i + 1:<3} {r['symbol']:<12} {r['direction']:<6} {r['hyro_score']:<6} "
            f"{ml:<6} {conf:<6} {r.get('rr_ratio', 0):<5.1f} {strat}"
        )

    print("\n  Top pick detail:")
    top = results[0]
    print(f"  Symbol:     {top['symbol']} {top['direction']}")
    print(f"  Entry:      {top['entry_price']}")
    print(f"  Stop Loss:  {top['stop_loss']}")
    print(f"  Take Profit:{top['take_profit']}")
    print(f"  R:R:        {top.get('rr_ratio', '?')}")
    print(
        f"  Conservative size: {top['position_conservative']['size']} = "
        f"${top['position_conservative']['position_value_usdt']}"
    )
    print(f"  Risk if SL hit:   ${top['position_conservative']['risk_amount_usdt']}")
    print(f"  Profit if TP hit: ${top['potential_profit_at_tp']}")
    print(f"  Consistency OK:   {top['consistency_ok']}")

    if rejected:
        print("\n  REJECTED (sample):")
        for r in rejected[:12]:
            print(f"    {r['symbol']}: {r['reason']}")

    print()


def main() -> int:
    parser = argparse.ArgumentParser(description="HyroTrader filter for audit dashboard picks")
    parser.add_argument("--local", help="Path to local dashboard_data.json")
    parser.add_argument("--url", help="Override dashboard URL")
    parser.add_argument("--account", type=float, default=float(HYRO_DEFAULTS["account_size"]), help="Reference account size USDT")
    parser.add_argument("--daily-used", type=float, default=0, help="Daily drawdown already used (USDT)")
    parser.add_argument("--overall-used", type=float, default=0, help="Overall drawdown already used (USDT)")
    parser.add_argument("--trading-days", type=int, default=None, help="Trading days completed (Hyro UI)")
    parser.add_argument("--equity", type=float, default=None, help="Override account_snapshot.equity_usdt")
    parser.add_argument("--day-start-equity", type=float, default=None, help="Override account_snapshot.day_start_equity_usdt")
    parser.add_argument("--cumulative-pnl", type=float, default=None, help="Override account_snapshot.cumulative_pnl_usdt")
    parser.add_argument("--high-water", type=float, default=None, help="Override account_snapshot.high_water_equity_usdt")
    parser.add_argument("--save", action="store_true", help="Write hyrotrader_picks.json")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output path (default: audit_dashboard/data/hyrotrader_picks.json)",
    )
    parser.add_argument("--json-only", action="store_true", help="Only output JSON to stdout, no summary")
    parser.add_argument(
        "--no-merge-base",
        action="store_true",
        help="Do not merge challenge/playbook from existing output file (not recommended)",
    )
    args = parser.parse_args()

    source = args.local or args.url
    if not source and DEFAULT_DASHBOARD_LOCAL.is_file():
        source = str(DEFAULT_DASHBOARD_LOCAL)

    dashboard_url = args.url or (DASHBOARD_URL if not args.local else f"file:{args.local}")
    dashboard_data = fetch_dashboard(source)
    journal = load_journal()

    results, rejected, scanned = filter_and_score(dashboard_data, args)

    merge_path = Path(args.output)
    merge_base: dict = {}
    if not args.no_merge_base:
        merge_base = load_merge_base(merge_path)

    if not args.json_only:
        print_summary(results, rejected, scanned, args)

    out = build_output(results, args, merge_base, dashboard_url, journal)

    # 2026-04-11: apply winrate filter (label normalization + conf gate +
    # blacklists) to hyrotrader picks before writing. Shadow by default; flip
    # with WINRATE_FILTER_MODE=strict in the workflow/scheduler.
    if isinstance(out.get("picks"), list):
        out["picks"], wr_stats = _apply_hyro_winrate_filter(out["picks"])
        out["winrate_filter_stats"] = wr_stats
        if not args.json_only:
            print(
                f"  winrate_filter mode={wr_stats.get('mode')} "
                f"normalized={wr_stats.get('label_normalized', 0)} "
                f"would_reject_conf={wr_stats.get('would_reject_low_conf', 0)} "
                f"would_reject_blacklist={wr_stats.get('would_reject_blacklist', 0)} "
                f"admitted={wr_stats.get('admitted', 0)}/{wr_stats.get('total_in', 0)}"
            )

    # 2026-04-11: apply prop-challenge gate (5 HyroTrader rules).
    # Shadow mode by default; enable hard reject with PROP_CHALLENGE_GATE=strict.
    # The gate needs: challenge config + account_snapshot (already in `out`
    # after build_output merged them from the base file), plus today's
    # realized/unrealized pnl (best-effort from journal).
    if isinstance(out.get("picks"), list):
        try:
            from alpha_engine.prop_challenge_gate import prop_challenge_gate
            challenge_cfg = out.get("challenge") or merge_base.get("challenge", {})
            account_state = dict(out.get("account_snapshot") or merge_base.get("account_snapshot", {}))
            # Prefer journal-derived realized data when present; otherwise fall
            # back to the equity snapshot delta.
            eq = _to_float_safe(account_state.get("equity_usdt"), 5000.0)
            day_start = _to_float_safe(account_state.get("day_start_equity_usdt"), eq)
            if account_state.get("today_realized_pnl_usdt") is None:
                account_state["today_realized_pnl_usdt"] = eq - day_start
            if account_state.get("today_unrealized_pnl_usdt") is None:
                account_state["today_unrealized_pnl_usdt"] = 0.0
            gate_mode = os.environ.get("PROP_CHALLENGE_GATE", "shadow").lower()
            gate_result = prop_challenge_gate(
                out["picks"], challenge_cfg, account_state,
                conservative=True,
            )
            out["prop_challenge_gate_stats"] = gate_result.summary()
            out["prop_challenge_gate_rejected"] = gate_result.rejected
            if gate_mode == "strict":
                out["picks"] = gate_result.accepted
            if not args.json_only:
                s = gate_result.summary()
                print(
                    f"  prop_challenge_gate mode={gate_mode} "
                    f"accepted={s['accepted_count']} rejected={s['rejected_count']} "
                    f"breaches={s['breach_count']} "
                    f"by_reason={s['rejections_by_reason']}"
                )
        except (ImportError, Exception) as exc:
            if not args.json_only:
                print(f"  prop_challenge_gate skipped: {exc}")

    if args.json_only:
        print(json.dumps(out, indent=2))
        return 0

    if args.save:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"  Saved to {out_path}")
        print(f"  {len(out['picks'])} picks written (challenge/playbook merged from base unless --no-merge-base)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
