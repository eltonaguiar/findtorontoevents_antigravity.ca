"""Conservative, deterministic scorecard for the dashboard's *bounded* closed slice.

Run: python3 tools/audit_scorecard.py --input dashboard_data.json --output verdicts.json

``pf``/``pf_2x_cost`` and their entry-day bootstrap are explicitly hypothetical
cost scenarios, not claims of actual executable performance. Portfolio returns
and drawdown require a separately audited daily MTM/sizing ledger and remain
null here. Static peer claims, ``audit_evidence``, and reported PnL do not certify
any gate. This reader cannot establish leakage, market-path nulls or forward
immutability from closed rows, so it deliberately cannot manufacture promotion.
"""

import argparse
import hashlib
import json
import math
import random
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


RULES_PATH = Path(__file__).resolve().parents[1] / "audit" / "gates.json"
CLASSES = {"CRYPTO", "EQUITY", "ETF", "FOREX", "BOND", "COMMODITY",
           "FUTURES", "MUTUAL_FUND", "OPTIONS", "PENSION", "MEME", "PENNY"}
ALIASES = {"STOCK": "EQUITY", "STOCKS": "EQUITY", "FX": "FOREX",
           "COMMODITIES": "COMMODITY", "BONDS": "BOND",
           "MUTUAL FUND": "MUTUAL_FUND", "ETFS": "ETF"}


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return value if math.isfinite(value) else None


def _time(value):
    if not isinstance(value, str) or len(value.strip()) <= 10:
        return None
    try:
        result = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        if result.tzinfo is None:
            return None
        return result.astimezone(timezone.utc)
    except ValueError:
        return None


def _iso(value):
    return value.isoformat().replace("+00:00", "Z") if value else None


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def _class(row):
    value = str(row.get("asset_class") or "UNKNOWN").strip().upper()
    return ALIASES.get(value, value)


def _identity(row, index):
    return str(row.get("id") or row.get("pick_id") or f"row:{index}")


def _first_time(row, fields):
    # Date-only entry_time is not an execution timestamp. A timestamp fallback
    # is accepted as the dashboard's signal/entry proxy, not proof of L1.
    for field in fields:
        result = _time(row.get(field))
        if result is not None:
            return result
    return None


def _pf(values):
    gain = math.fsum(v for v in values if v > 0)
    loss = -math.fsum(v for v in values if v < 0)
    return gain / loss if loss else None


def _bootstrap(rows, cost, rules):
    if not rows or cost is None:
        return [None, None], None
    clusters = defaultdict(lambda: [0.0, 0.0])
    for row in rows:
        value = row["gross"] - cost
        day = row["entry"].date().isoformat()
        clusters[day][0 if value > 0 else 1] += abs(value)
    days = [clusters[key] for key in sorted(clusters)]
    rng = random.Random(rules["bootstrap"]["seed"])
    samples = rules["bootstrap"]["samples"]
    # Undefined zero-loss replicates are +infinity for interval ordering, but
    # are serialized as null, never a made-up PF=999 or silently discarded.
    results = []
    undefined = 0
    for _ in range(samples):
        gain = loss = 0.0
        for _ in days:
            selected = days[rng.randrange(len(days))]
            gain += selected[0]
            loss += selected[1]
        if loss == 0:
            results.append(math.inf)
            undefined += 1
        else:
            results.append(gain / loss)
    results.sort()

    def endpoint(p):
        value = results[int((samples - 1) * p)]
        return value if math.isfinite(value) else None

    return [endpoint(0.025), endpoint(0.975)], undefined / samples


def _genuine_flat(row):
    """Require distinct execution fill identifiers, not just a boolean claim."""
    reason = str(row.get("exit_reason") or "").upper()
    return (reason in {"BREAKEVEN", "BREAK_EVEN", "GENUINE_FLAT"}
            and bool(row.get("entry_fill_id")) and bool(row.get("exit_fill_id"))
            and row["entry_fill_id"] != row["exit_fill_id"]
            and str(row.get("status") or "").upper() != "F")


def _crypto_symbol(symbol):
    # Only explicit exchange stablecoin pairs or a bounded canonical USD list.
    # XAU-USD and other legitimate USD-priced noncrypto instruments are not
    # inferred to be crypto merely because they use a USD suffix.
    return bool(re.fullmatch(r"[A-Z0-9]{2,15}(USDT|USDC|BUSD)", symbol)
                or symbol in {"BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD",
                              "XRP-USD", "ADA-USD", "AVAX-USD", "LTC-USD",
                              "BCH-USD", "DOT-USD", "LINK-USD"})


def _clean(raw, rules):
    prepared, exclusions = [], []
    ids, keys = set(), set()
    batch = Counter()
    for row in raw:
        if isinstance(row, dict):
            close = _first_time(row, ("closed_at", "exit_time", "resolved_at"))
            if close:
                batch[close.replace(microsecond=0)] += 1

    def exclude(row, index, reason):
        exclusions.append({"identity": _identity(row, index),
                           "asset_class": _class(row), "reason": reason,
                           "_strategy": str(row.get("strategy") or row.get("source_system") or "UNKNOWN"),
                           "_source_system": str(row.get("source_system") or "UNKNOWN"),
                           "_direction": str(row.get("direction") or "").upper()})

    for index, original in enumerate(raw):
        row = original if isinstance(original, dict) else {}
        asset = _class(row)
        strategy = str(row.get("strategy") or row.get("source_system") or "UNKNOWN")
        source_system = str(row.get("source_system") or "UNKNOWN")
        direction = str(row.get("direction") or "").upper()
        direction = {"BUY": "LONG", "SELL": "SHORT"}.get(direction, direction)
        symbol = str(row.get("symbol") or "").strip().upper()
        entry_px, exit_px = _number(row.get("entry_price")), _number(row.get("exit_price"))
        reported = _number(row.get("pnl_pct"))
        entry = _first_time(row, ("entry_time", "entry_ts", "timestamp", "created_at"))
        close = _first_time(row, ("closed_at", "exit_time", "resolved_at"))
        created = _time(row.get("created_at"))
        reason = None
        if entry_px is None:
            reason = "missing_entry_price"
        elif exit_px is None:
            reason = "missing_exit_price"
        elif exit_px == 0:
            reason = "zero_exit_price"
        elif abs(entry_px) >= 999999 or abs(exit_px) >= 999999:
            reason = "sentinel_price"
        elif reported is not None and abs(reported) >= 999999:
            reason = "sentinel_pnl"
        elif entry_px <= 0 or exit_px < 0:
            reason = "invalid_price"
        elif entry_px == exit_px and not _genuine_flat(row):
            reason = "placeholder_flat"
        elif entry is None:
            reason = "missing_entry_timestamp"
        elif close is None:
            reason = "missing_close_timestamp"
        elif close < entry or (created and created > entry):
            reason = "nonmonotonic_timestamp"
        elif (close - entry).total_seconds() < rules["minimum_hold_seconds"]:
            reason = "hold_under_2_minutes"
        elif direction not in {"LONG", "SHORT"}:
            reason = "invalid_direction"
        elif not symbol:
            reason = "missing_symbol"
        elif asset not in CLASSES:
            reason = "unknown_asset_class"
        elif _crypto_symbol(symbol) and asset not in {"CRYPTO", "MEME"}:
            reason = "wrong_asset_class"
        elif symbol.endswith("=X") and asset != "FOREX":
            reason = "wrong_asset_class"
        elif symbol.endswith("=F") and asset not in {"FUTURES", "COMMODITY", "BOND"}:
            reason = "wrong_asset_class"
        elif batch[close.replace(microsecond=0)] >= rules["batch_close_second_threshold"]:
            reason = "batch_close_second"
        ident = row.get("id") or row.get("pick_id")
        key = (source_system, strategy, symbol, direction, entry.replace(second=0, microsecond=0) if entry else None)
        if reason is None and ident and str(ident) in ids:
            reason = "duplicate_id"
        if reason is None and key in keys:
            reason = "duplicate_signal_minute"
        if reason:
            exclude(row, index, reason)
            continue
        if ident:
            ids.add(str(ident))
        keys.add(key)
        gross = (exit_px - entry_px) / entry_px * 100
        if direction == "SHORT":
            gross = -gross
        prepared.append({"identity": _identity(row, index), "index": index,
                         "asset_class": asset, "strategy": strategy,
                         "source_system": source_system,
                         "direction": direction, "symbol": symbol,
                         "entry": entry, "close": close, "gross": gross,
                         "inconsistent": reported is not None and abs(gross - reported) > 0.01})
    active = {}
    clean = []
    for row in sorted(prepared, key=lambda r: (r["entry"], r["close"], r["identity"])):
        # Long and short signals share the same strategy symbol book.
        key = (row["source_system"], row["strategy"], row["symbol"])
        if key in active and row["entry"] < active[key]:
            exclude(raw[row["index"]], row["index"], "same_symbol_overlap")
        else:
            active[key] = row["close"]
            clean.append(row)
    return clean, exclusions


def _gate(gates, name, status, reason, value=None):
    gates[name].update(status=status, reason=reason)
    if value is not None:
        gates[name]["value"] = value


def _stat(rows, asset, strategy, direction, excluded, source, rules, endpoint_health,
          source_system="ALL"):
    gates = {key: {"name": name, "status": "N/A",
                   "reason": "Independent evidence unavailable in closed-row snapshot"}
             for key, name in rules["gates"].items()}
    n = len(rows)
    reasons = dict(sorted(Counter(r["reason"] for r in excluded).items()))
    cost = rules["scenario_round_trip_pct"].get(asset)
    gross = [row["gross"] for row in rows]
    net = [v - cost for v in gross] if cost is not None else []
    pf = _pf(net) if net else None
    ci, undefined_mass = _bootstrap(rows, cost, rules)
    wins = sum(v > 0 for v in net) if cost is not None else None
    losses = sum(v < 0 for v in net) if cost is not None else None
    top_share = max(Counter(r["symbol"] for r in rows).values(), default=0) / n if n else None
    thresholds = rules["thresholds"]
    declared_match = source["total_known"] and source["total_closed_n"] == source["input_closed_n"]
    _gate(gates, "D5", "PASS", "Every excluded row has an identity, class and reason")
    if n:
        _gate(gates, "D1", "N/A", "Retained prices are sentinel-free; ordered source-feed jump audit unavailable")
        _gate(gates, "D3", "N/A", "Retained timestamps ordered; creation/execution provenance unavailable; entry can be signal proxy")
        _gate(gates, "R3", "PASS", "Returns recomputed from prices; SHORT=(entry-exit)/entry")
        _gate(gates, "R4", "PASS", "One concurrent position per strategy/symbol after quarantine")
        _gate(gates, "R5", "PASS", "Retained IDs and strategy/symbol/direction/entry-minute keys unique")
        _gate(gates, "R7", "PASS", "Zero/sentinel exits and unproven flat placeholders quarantined")
        minute_counts = Counter(row["close"].replace(second=0, microsecond=0) for row in rows)
        dates = len({row["close"].date() for row in rows})
        artifact_pass = max(minute_counts.values()) <= 3 and sum(v > 0 for v in gross) <= 2 * dates
        _gate(gates, "R6", "PASS" if artifact_pass else "FAIL",
              "Retained close-minute count <=3 and wins <=2x distinct close dates")
        _gate(gates, "S1", "N/A",
              "Retained nonoverlapping rows are not independently certified trials; same-day correlation unverified", n)
        if n >= 20 and cost is not None:
            _gate(gates, "S4", "PASS" if wins / n * 100 >= thresholds["win_rate_pct"] else "FAIL",
                  "Scenario-net win rate; actual net costs unavailable", wins / n * 100)
        if top_share > thresholds["top_symbol_share"]:
            _gate(gates, "S11", "FAIL", "Top symbol exceeds 30% of retained trades", top_share)
    _gate(gates, "R8", "N/A" if declared_match else ("FAIL" if source["total_known"] else "N/A"),
          "Snapshot equals declared total, but independent DB reconciliation is unavailable" if declared_match
          else "Bounded/missing history; do not claim a complete ledger")
    # Invalid source rows remain visible as hard failures, even after removal.
    hard_reasons = {
        "D1": {"sentinel_price", "sentinel_pnl", "invalid_price", "zero_exit_price", "missing_entry_price", "missing_exit_price"},
        "D3": {"missing_entry_timestamp", "missing_close_timestamp", "nonmonotonic_timestamp"},
        "R4": {"same_symbol_overlap"}, "R5": {"duplicate_id", "duplicate_signal_minute"},
        "R6": {"batch_close_second"}, "R7": {"placeholder_flat", "hold_under_2_minutes"},
    }
    for gate, failures in hard_reasons.items():
        found = sorted(failures.intersection(reasons))
        if found:
            _gate(gates, gate, "FAIL", "Quarantined source defects: " + ", ".join(found))
    if "wrong_asset_class" in reasons or "unknown_asset_class" in reasons:
        _gate(gates, "D1", "FAIL", "Source class mapping invalid")

    score = sum(5 for key, value in gates.items() if key.startswith("S") and value["status"] == "PASS")
    score += sum(8.75 for key, value in gates.items() if key.startswith("F") and value["status"] == "PASS")
    hard_pass = all(v["status"] == "PASS" for k, v in gates.items() if k[0] in "DLR")
    label = "FAIL"
    # These explicit conditions are intentionally unreachable from static
    # closed rows alone: missing independent evidence is never a PASS.
    candidate = (hard_pass and thresholds["candidate_min_score"] <= score < thresholds["candidate_max_score_exclusive"]
                 and pf is not None and pf >= thresholds["candidate_pf"]
                 and ci[0] is not None and ci[0] > thresholds["candidate_ci_lower_exclusive"]
                 and all(gates[g]["status"] == "PASS" for g in ("S2", "S3", "S6", "F1", "F2")))
    if candidate:
        label = "CANDIDATE"
    first = min((r["close"] for r in rows), default=None)
    last = max((r["close"] for r in rows), default=None)
    limitations = (
        "Recent closed snapshot only. PF/CI are hypothetical cost scenarios, not verified net results. "
        "Sum of trade returns is NOT a portfolio return. Portfolio compounding/MDD unverified: "
        "missing dated daily MTM equity, concurrent positions and sizing. "
        "No independent market paths, trial matrix, sealed forward ledger or operator sign-off; no promotion."
    )
    if cost is None:
        limitations += " No defensible universal percentage cost scenario for this class."
    warning = ((cost is not None and n >= 50 and wins / n >= .9)
               or (n > 0 and math.fsum(gross) / n > 5))
    health = "OK" if rows or excluded else "EMPTY"
    endpoint = endpoint_health.get(asset, {})
    endpoint_status = endpoint.get("health") if isinstance(endpoint, dict) else endpoint
    if endpoint_status in {"BROKEN", "EMPTY", "STALE"}:
        health = endpoint_status
    elif health == "OK" and source["snapshot_age_days"] is not None and source["snapshot_age_days"] > 7:
        health = "STALE"
    recent = sorted(rows, key=lambda r: (r["close"], r["identity"]), reverse=True)[:5]
    return {
        "asset_class": asset, "strategy": strategy, "direction": direction,
        "source_system": source_system,
        "label": label, "score": score, "n": n, "wins": wins, "losses": losses,
        "win_rate": wins / n * 100 if n >= 20 and cost is not None else None,
        "wins_basis": "price_derived_scenario_net" if cost is not None else "UNKNOWN_ACTUAL_COSTS",
        "pf": pf, "pf_ci95": ci, "pf_bootstrap_undefined_mass": undefined_mass,
        "pf_2x_cost": _pf([v - 2 * cost for v in gross]) if cost is not None and n else None,
        "cost_scenario_pct": cost, "cost_status": "UNVERIFIED_SCENARIO",
        "cost_scenario_note": rules["scenario_notes"].get(asset, rules["scenario_notes"]["OTHER"]),
        "compound_return_pct": None, "compound_unverified_reason": "Missing audited daily MTM equity and sizing ledger",
        "sum_trade_pct": math.fsum(gross) if n else None, "mdd_pct": None,
        "distinct_close_days": len({r["close"].date() for r in rows}),
        "top_symbol_share": top_share, "forward_status": "UNVERIFIED",
        "health": health,
        "health_note": ("Endpoint failure reported by sanitized endpoint_health input" if health == "BROKEN"
                        else "Snapshot update age only; close activity is not proof of feed freshness"),
        "excluded_n": len(excluded), "exclusion_reasons": reasons,
        "first_close": _iso(first), "last_close": _iso(last),
        "gates": gates, "warning": warning, "limitations": limitations,
        "recent5": [{"symbol": r["symbol"], "closed_at": _iso(r["close"]),
                     "net_pct": r["gross"] - cost if cost is not None else None} for r in recent],
        "inconsistent": False,
        "pnl_disagreement_n": sum(r["inconsistent"] for r in rows),
    }


def build_verdicts(payload, as_of=None):
    """Return JSON-safe verdicts without modifying input or consulting the clock.

    Accepted dashboard input: ``picks.recent_closed`` (canonical) or top-level
    ``recent_closed``; declared history total: ``summary.total_closed_picks``.
    Naive/date-only timestamps are quarantined; ``timestamp`` is the legacy
    entry proxy when a precise ``entry_time`` is absent.

    Unknown evidence is N/A. No input boolean or peer-supplied gate verdict is
    accepted as proof. This version intentionally accepts no portfolio-evidence
    extension: adding one requires an independently audited sizing/MTM contract.
    """
    if not isinstance(payload, dict):
        raise ValueError("Dashboard payload must be an object")
    rules_bytes = RULES_PATH.read_bytes()
    rules = json.loads(rules_bytes)
    picks = payload.get("picks", {})
    raw = picks.get("recent_closed", []) if isinstance(picks, dict) else []
    if "recent_closed" in payload:
        raw = payload["recent_closed"]
    if not isinstance(raw, list):
        raise ValueError("recent_closed must be an array")
    generated = payload.get("generated_at")
    evaluation = as_of if as_of is not None else generated
    now = _time(evaluation)
    if as_of is not None and now is None:
        raise ValueError("--as-of requires an ISO-8601 timestamp with timezone")
    summary = payload.get("summary")
    total = summary.get("total_closed_picks") if isinstance(summary, dict) else None
    total_known = isinstance(total, int) and not isinstance(total, bool) and total >= len(raw)
    closes = [_first_time(r, ("closed_at", "exit_time", "resolved_at"))
              for r in raw if isinstance(r, dict)]
    closes = [t for t in closes if t]
    updated = _time(payload.get("updated_at")) or _time(payload.get("generated_at"))
    age_days = max(0, (now - updated).total_seconds() / 86400) if now and updated else None
    endpoint_health = payload.get("endpoint_health")
    if not isinstance(endpoint_health, dict):
        endpoint_health = {}
    source = {
        "first_close": _iso(min(closes)) if closes else None,
        "last_close": _iso(max(closes)) if closes else None,
        "input_closed_n": len(raw), "total_closed_n": total if total_known else None,
        "total_known": total_known,
        "generated_at": generated if _time(generated) else None,
        "snapshot_updated_at": _iso(updated), "snapshot_age_days": age_days,
        "scope": ("declared_total_match_unverified" if total_known and total == len(raw)
                  else "recent_closed_subset"),
    }
    clean, excluded = _clean(raw, rules)
    groups = defaultdict(list)
    for row in clean:
        groups[(row["asset_class"], row["source_system"], row["strategy"], row["direction"])].append(row)
    for row in excluded:
        groups.setdefault((row["asset_class"], row["_source_system"], row["_strategy"], row["_direction"]), [])
    strategies = []
    for (asset, system, strategy, direction), rows in sorted(groups.items()):
        rejected = [r for r in excluded if (r["asset_class"], r["_source_system"], r["_strategy"], r["_direction"])
                    == (asset, system, strategy, direction)]
        strategies.append(_stat(rows, asset, strategy, direction, rejected, source, rules, endpoint_health, system))
    assets = sorted(CLASSES | {r["asset_class"] for r in clean + excluded})
    classes = {}
    for asset in assets:
        classes[asset] = _stat([r for r in clean if r["asset_class"] == asset], asset,
                               "ALL", "ALL", [r for r in excluded if r["asset_class"] == asset],
                               source, rules, endpoint_health)
    classes["NON_CRYPTO"] = _stat(
        [r for r in clean if r["asset_class"] not in {"CRYPTO", "MEME"}],
        "NON_CRYPTO", "ALL", "ALL",
        [r for r in excluded if r["asset_class"] not in {"CRYPTO", "MEME"}],
        source, rules, endpoint_health)
    top = sorted([r for r in strategies if r["label"] in {"MONEY-READY", "CANDIDATE"}],
                 key=lambda r: (-r["score"], -(r["pf_ci95"][0] or 0),
                                r["asset_class"], r["source_system"], r["strategy"], r["direction"]))
    return {
        "schema_version": 1, "rules_hash": hashlib.sha256(rules_bytes).hexdigest(),
        "generated_at": generated if _time(generated) else None,
        "evaluated_at": evaluation if now else None, "source": source, "classes": classes,
        "strategies": strategies, "top_verified": top,
        "excluded": dict(sorted(Counter(r["reason"] for r in excluded).items())),
        "exclusions": [{k: v for k, v in r.items() if not k.startswith("_")} for r in excluded],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--as-of")
    args = parser.parse_args(argv)
    payload = json.loads(args.input.read_text())
    result = build_verdicts(payload, args.as_of)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(_canonical(result) + "\n")


if __name__ == "__main__":
    main()
