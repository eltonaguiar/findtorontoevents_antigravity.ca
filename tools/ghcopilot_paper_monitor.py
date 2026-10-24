#!/usr/bin/env python3
"""Frozen, prospective-only research pilot. Never places orders or writes to MySQL."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
from pathlib import Path
import random
import re
import ssl
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from ftplib import FTP_TLS
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CLASSES = ("CRYPTO", "EQUITY", "ETF", "BOND", "FOREX", "COMMODITY", "FUTURES")
COST_PP = {c: (0.30 if c == "CRYPTO" else 0.10) for c in CLASSES}
STATE = ROOT / "audit_dashboard/data/ghcopilot_paper.json"
FOOTER = """
<nav id="ghcopilot-paper-footer" aria-label="Independent paper experiments"
 style="padding:20px;text-align:center;border-top:1px solid #334155;background:#101827;color:#e2e8f0">
 <strong>Independent paper experiments (not money-ready)</strong><br>
 <a href="/audit/ghcopilot_paper.html" style="color:#67e8f9">GHCOPILOT - Copilot SDK in VS Code: multi-class paper + random controls</a>
 &nbsp;|&nbsp; <a href="/audit/paper_pilot.html" style="color:#c4b5fd">Existing COT pilot</a>
 &nbsp;|&nbsp; <a href="/audit/crypto_paper_pilot.html" style="color:#c4b5fd">Existing crypto pilot</a>
</nav>
"""


def utc(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if not isinstance(value, datetime):
        raise ValueError("Missing/invalid timestamp")
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def number(value):
    if value is None:
        raise ValueError("Missing numeric value")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Nonfinite numeric value")
    return result


def source_key(value):
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def bh_adjust(values):
    n = len(values)
    result = [1.0] * n
    bound = 1.0
    for rank, idx in reversed(list(enumerate(sorted(range(n), key=values.__getitem__), 1))):
        bound = min(bound, values[idx] * n / rank)
        result[idx] = bound
    return result


def summarize(rows):
    from scipy.stats import binomtest

    pnls = [number(r["net_pct"]) for r in rows]
    gains = sum(max(x, 0) for x in pnls)
    losses = -sum(min(x, 0) for x in pnls)
    days = defaultdict(list)
    for row, pnl in zip(rows, pnls):
        days[utc(row["entry_at"]).date().isoformat()].append(pnl)
    groups = list(days.values())
    samples = []
    rng = random.Random(42)
    if len(groups) >= 2:
        for _ in range(2000):
            draw = [rng.choice(groups) for _ in groups]
            samples.append(sum(map(sum, draw)) / sum(map(len, draw)))
        samples.sort()
    ordered = sorted(rows, key=lambda r: utc(r["entry_at"]))
    half = len(ordered) // 2
    half_means = [
        sum(number(r["net_pct"]) for r in part) / len(part) if part else None
        for part in (ordered[:half], ordered[half:])
    ]
    return {
        "n": len(pnls), "entry_days": len(days),
        "span_days": (max(map(utc, days)) - min(map(utc, days))).days if days else 0,
        "win_rate": sum(x > 0 for x in pnls) / len(pnls) if pnls else None,
        "net_mean_pct": sum(pnls) / len(pnls) if pnls else None,
        "net_pf": gains / losses if losses else None,
        "no_losses": bool(pnls) and losses == 0,
        "day_bootstrap_ci95": [samples[50], samples[1950]] if samples else None,
        "coinflip_p": float(binomtest(sum(x > 0 for x in pnls), len(pnls), .5,
                                    alternative="greater").pvalue) if pnls else 1.0,
        "half_net_means_pct": half_means,
    }


def geometry(row):
    entry, tp, sl = (number(row[k]) for k in ("entry_price", "take_profit", "stop_loss"))
    direction = row["direction"]
    if entry <= 0 or tp <= 0 or sl <= 0 or direction not in ("LONG", "SHORT"):
        raise ValueError("Invalid geometry")
    if not (sl < entry < tp if direction == "LONG" else tp < entry < sl):
        raise ValueError("Invalid geometry")
    distances = abs(tp - entry) / entry, abs(sl - entry) / entry
    if max(distances) > .30 or min(distances) < .0001:
        raise ValueError("Invalid geometry")
    return distances


def screen_candidates(rows, now):
    grouped = defaultdict(list)
    seen = set()
    rejected = Counter()
    duplicates = 0
    for row in rows:
        try:
            cls = row["asset_class"]
            if row.get("intrabar_ambiguous"):
                raise ValueError("ambiguous_history")
            if row["strategy"] == "vt_equity_two_day_rsi_reversal":
                raise ValueError("known_historical_reemission")
            if cls not in CLASSES or not row["strategy"] or not row["source_system"]:
                raise ValueError("Missing strategy/source/class")
            stamp = utc(row["opened_at"])
            pnl = number(row["intrabar_pnl_pct"])
            geometry(row)
            if not now - timedelta(days=120) <= stamp <= now or abs(pnl) > 30:
                raise ValueError("Out-of-window/outlier")
            key = (cls, source_key(row["source_system"]), row["strategy"])
            identity = key + (row["symbol"], row["direction"], stamp)
            if identity in seen:
                duplicates += 1
                continue
            seen.add(identity)
            grouped[key].append({"net_pct": pnl - COST_PP[cls],
                                 "entry_at": stamp.isoformat()})
        except (ValueError, KeyError, TypeError) as exc:
            rejected[str(exc)] += 1
    groups = []
    for (cls, source, strategy), values in sorted(grouped.items()):
        stats = summarize(values)
        groups.append({"asset_class": cls, "source": source, "strategy": strategy,
                       "cost_pp": COST_PP[cls], **stats})
    adjusted = bh_adjust([g["coinflip_p"] for g in groups])
    for group, q in zip(groups, adjusted):
        ci = group["day_bootstrap_ci95"]
        group["coinflip_q"] = q
        group["historical_gate_pass"] = bool(
            group["n"] >= 100 and group["entry_days"] >= 30 and group["span_days"] >= 90
            and q <= .05 and ci and ci[0] > 0 and (group["net_pf"] or 0) >= 1.5
            and all(v is not None and v > 0 for v in group["half_net_means_pct"]))
    candidates = {}
    for cls in CLASSES:
        eligible = [g for g in groups if g["asset_class"] == cls
                    and g["n"] >= 20 and g["entry_days"] >= 10
                    and g["net_mean_pct"] > 0 and (g["net_pf"] or 0) > 1]
        eligible.sort(key=lambda g: (
            g["historical_gate_pass"], (g["day_bootstrap_ci95"] or [-100])[0],
            g["n"]), reverse=True)
        candidates[cls] = eligible[0] if eligible else None
    return {"groups": groups, "candidates": candidates,
            "duplicate_rows": duplicates, "excluded_rows": dict(rejected),
            "screened_at": now.isoformat(), "tested_groups": len(groups)}


def admit_signals(state, rows, now):
    seen = set(state["seen"])
    counts = Counter(state["rejections"])
    for row in rows:
        cls = row["asset_class"]
        candidate = state["candidates"].get(cls)
        if not candidate or (source_key(row["source_system"]), row["strategy"]) != (
                candidate["source"], candidate["strategy"]):
            continue
        ident = hashlib.sha256(("ghcopilot-v1:" + str(row["id"])).encode()).hexdigest()[:24]
        if ident in seen:
            continue
        seen.add(ident)
        try:
            stamp, recorded = utc(row["signal_timestamp"]), utc(row["recorded_at"])
            if recorded < utc(state["locked_at"]) or stamp < utc(state["locked_at"]):
                raise ValueError("before_lock")
            if stamp > now + timedelta(minutes=5) or recorded > now + timedelta(minutes=5):
                raise ValueError("future_signal")
            if now - stamp > timedelta(hours=2):
                raise ValueError("stale_signal")
            if row["status"] != "OPEN":
                raise ValueError("not_open")
            if any(row.get(k) for k in ("was_stale", "was_banned", "was_demoted")):
                raise ValueError("policy_flag")
            try:
                tp_distance, sl_distance = geometry(row)
            except (ValueError, KeyError, TypeError) as exc:
                raise ValueError("invalid_geometry") from exc
            busy = [t for t in state["trades"] if t["status"] not in ("CLOSED", "CANCELLED")]
            if any(t["asset_class"] == cls or t["symbol"] == row["symbol"] for t in busy):
                raise ValueError("exposure_cap")
            if not re.fullmatch(r"[A-Za-z0-9=.^_-]{1,30}", row["symbol"]):
                raise ValueError("invalid_symbol")
            state["trades"].append({
                "id": ident, "asset_class": cls, "source": candidate["source"],
                "strategy": candidate["strategy"], "symbol": row["symbol"],
                "direction": row["direction"], "observed_at": now.isoformat(),
                "signal_at": stamp.isoformat(), "status": "PENDING_ENTRY",
                "tp_distance": tp_distance, "sl_distance": sl_distance,
                "notional_usd": 1000, "cost_pp": COST_PP[cls],
                "control_direction": "LONG" if int(ident, 16) % 2 else "SHORT",
            })
        except (ValueError, KeyError, TypeError) as exc:
            counts[str(exc)] += 1
    state["seen"] = sorted(seen)
    state["rejections"] = dict(counts)


def validate_bars(bars):
    seen = set()
    for bar in bars:
        stamp = utc(bar["time"])
        o, h, l, c = (number(bar[k]) for k in ("open", "high", "low", "close"))
        if stamp in seen or min(o, h, l, c) <= 0 or not l <= min(o, c) <= max(o, c) <= h:
            raise ValueError("Invalid/duplicate market candle")
        seen.add(stamp)
    return sorted(bars, key=lambda b: utc(b["time"]))


def resolve_leg(leg, bars, now, cls):
    entry_time, expiry = utc(leg["entry_at"]), utc(leg["expires_at"])
    previous = None
    for bar in validate_bars(bars):
        stamp = utc(bar["time"])
        end = stamp + timedelta(hours=1)
        if stamp < entry_time or end > now:
            continue
        if previous is None and stamp != entry_time:
            raise ValueError("missing entry candle")
        if previous is not None and stamp - previous > timedelta(hours=1):
            raise ValueError("missing market candle or unverified session closure")
        previous = stamp
        is_long = leg["direction"] == "LONG"
        o, h, l = (number(bar[k]) for k in ("open", "high", "low"))
        sl, tp = leg["sl"], leg["tp"]
        if (o <= sl if is_long else o >= sl):
            price, reason = o, "GAP_SL"
        elif (o >= tp if is_long else o <= tp):
            price, reason = tp, "GAP_TP"
        elif stamp >= expiry:
            price, reason = o, "TIME_EXIT"
        elif (l <= sl if is_long else h >= sl):
            price, reason = sl, "SL_HIT"
        elif (h >= tp if is_long else l <= tp):
            price, reason = tp, "TP_HIT"
        elif end == expiry:
            price, reason = number(bar["close"]), "TIME_EXIT"
        else:
            continue
        gross = (price / leg["entry"] - 1) * (100 if is_long else -100)
        return {"exit": price, "exit_at": (stamp if reason.startswith("GAP") or stamp >= expiry
                                          else end).isoformat(),
                "gross_pct": gross, "reason": reason}
    return None


def advance_trade(trade, bars, now):
    bars = validate_bars(bars)
    if trade["status"] == "PENDING_ENTRY":
        ready = [b for b in bars if utc(b["time"]) >= utc(trade["observed_at"])
                 and utc(b["time"]) + timedelta(hours=1) <= now]
        if not ready:
            if now - utc(trade["observed_at"]) > timedelta(days=7):
                trade.update(status="CANCELLED", error="No tradable entry within seven days")
            return
        first = ready[0]
        if utc(first["time"]) - utc(trade["observed_at"]) > timedelta(hours=1):
            raise ValueError("missing next-entry market candle or unverified session closure")
        trade["entry_at"], trade["entry"] = first["time"], number(first["open"])
        trade["expires_at"] = (utc(first["time"]) + timedelta(hours=48)).isoformat()
        trade["status"] = "OPEN"
    for label, direction in (("strategy_result", trade["direction"]),
                             ("control_result", trade["control_direction"])):
        if label in trade:
            continue
        sign = 1 if direction == "LONG" else -1
        leg = {**trade, "direction": direction,
               "tp": trade["entry"] * (1 + sign * trade["tp_distance"]),
               "sl": trade["entry"] * (1 - sign * trade["sl_distance"])}
        result = resolve_leg(leg, bars, now, trade["asset_class"])
        if result:
            result["net_pct"] = result["gross_pct"] - trade["cost_pp"]
            result["net_usd"] = result["net_pct"] * trade["notional_usd"] / 100
            trade[label] = result
    if "strategy_result" in trade and "control_result" in trade:
        trade["status"] = "CLOSED"
    trade.pop("error", None)
    completed = [b for b in bars if utc(b["time"]) + timedelta(hours=1) <= now]
    if completed and trade["status"] == "OPEN":
        latest = completed[-1]
        trade["mark_at"] = (utc(latest["time"]) + timedelta(hours=1)).isoformat()
        trade["mark_price"] = number(latest["close"])


def market_bars(symbol, start, now):
    import requests

    ticker = symbol[:-4] + "-USD" if symbol.endswith("USDT") else symbol
    errors = []
    for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        try:
            response = requests.get(
                f"https://{host}/v8/finance/chart/{quote(ticker, safe='')}",
                params={"period1": int((start - timedelta(hours=2)).timestamp()),
                        "period2": int(now.timestamp()), "interval": "1h"},
                headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
            response.raise_for_status()
            chart = response.json()["chart"]
            if chart.get("error") or not chart.get("result"):
                raise ValueError("Market provider has no chart")
            data = chart["result"][0]
            quotes = data["indicators"]["quote"][0]
            bars = []
            for i, stamp in enumerate(data.get("timestamp", [])):
                values = {k: quotes[k][i] for k in ("open", "high", "low", "close")}
                if any(v is None for v in values.values()):
                    continue
                bars.append({"time": datetime.fromtimestamp(stamp, timezone.utc).isoformat(),
                             **values})
            if not bars:
                raise ValueError("No usable hourly bars")
            return validate_bars(bars)
        except (requests.RequestException, ValueError, KeyError, IndexError) as exc:
            errors.append(f"{host}: {type(exc).__name__}")
    raise ValueError("Market data unavailable; " + "; ".join(errors))


def read_db(screen=False, locked_at=None):
    import pymysql
    from tools.db_env import get_stocks_creds

    connection = pymysql.connect(**get_stocks_creds(), cursorclass=pymysql.cursors.DictCursor)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SET SESSION TRANSACTION READ ONLY")
            if screen:
                cursor.execute("""
                    SELECT id,symbol,source_system,strategy,asset_class,direction,
                           entry_price,take_profit,stop_loss,opened_at,intrabar_pnl_pct,
                           intrabar_ambiguous
                    FROM at_signal_outcomes
                    WHERE opened_at >= UTC_TIMESTAMP() - INTERVAL 120 DAY
                      AND intrabar_status IN ('TP_HIT','SL_HIT','TIME_EXIT')
                      AND intrabar_pnl_pct IS NOT NULL
                    ORDER BY opened_at,id""")
            else:
                cursor.execute("""
                    SELECT id,symbol,source_system,strategy,asset_class,direction,
                           entry_price,take_profit,stop_loss,signal_timestamp,recorded_at,
                           status,was_stale,was_banned,was_demoted
                    FROM at_raw_picks WHERE recorded_at >= %s
                      AND recorded_at >= UTC_TIMESTAMP() - INTERVAL 2 HOUR
                    ORDER BY recorded_at,id""", (utc(locked_at).replace(tzinfo=None),))
            return cursor.fetchall()
    finally:
        connection.close()


def database_quality():
    import pymysql
    from tools.db_env import get_stocks_creds

    connection = pymysql.connect(**get_stocks_creds(), cursorclass=pymysql.cursors.DictCursor)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SET SESSION TRANSACTION READ ONLY")
            cursor.execute("""
                SELECT asset_class,COUNT(*) n,
                  SUM(recorded_at>=UTC_TIMESTAMP()-INTERVAL 24 HOUR) recorded_24h,
                  MAX(recorded_at) latest_recorded,MAX(signal_timestamp) latest_signal,
                  SUM(signal_timestamp IS NULL) missing_signal,
                  SUM(status IN ('WON','LOST','CLOSED','EXPIRED')) closed_n,
                  SUM(status IN ('WON','LOST','CLOSED','EXPIRED') AND pnl_pct IS NULL) missing_closed_pnl,
                  SUM(status IN ('WON','LOST','CLOSED','EXPIRED') AND pnl_pct=0) zero_closed_pnl,
                  SUM(ABS(pnl_pct)>30) extreme_pnl
                FROM at_raw_picks GROUP BY asset_class""")
            raw = cursor.fetchall()
            cursor.execute("""
                SELECT asset_class,COUNT(*) n,MAX(opened_at) latest_signal,
                  SUM(intrabar_pnl_pct IS NOT NULL) replay_n,
                  SUM(intrabar_pnl_pct IS NULL) no_replay,
                  SUM(intrabar_ambiguous=1) ambiguous
                FROM at_signal_outcomes GROUP BY asset_class""")
            outcomes = cursor.fetchall()
        # Explicit typed projection: no raw payloads or credential material.
        def project(rows):
            return [{k: (v.isoformat() + "Z" if isinstance(v, datetime)
                         else v if isinstance(v, (str, type(None))) else int(v))
                     for k, v in row.items()} for row in rows]
        return {"raw_classes": project(raw), "outcome_classes": project(outcomes),
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "scope": "Cumulative ledgers; zero is diagnostic, not assumed invalid. Ambiguous replay is not independently certified."}
    finally:
        connection.close()


def report(state):
    groups = {}
    for cls in CLASSES:
        closed = [t for t in state["trades"] if t["asset_class"] == cls and t["status"] == "CLOSED"]
        rows = [{**t["strategy_result"], "entry_at": t["entry_at"]} for t in closed]
        stats = summarize(rows)
        # Pairwise random-direction controls follow their own exit path.
        diffs = [{"net_pct": t["strategy_result"]["net_pct"] - t["control_result"]["net_pct"],
                  "entry_at": t["entry_at"]} for t in closed]
        stats["paired_control"] = summarize(diffs)
        stats["net_usd"] = sum(t["strategy_result"]["net_usd"] for t in closed)
        stats["control_net_usd"] = sum(t["control_result"]["net_usd"] for t in closed)
        stats["active"] = sum(t["asset_class"] == cls and t["status"] in ("OPEN", "PENDING_ENTRY")
                              for t in state["trades"])
        groups[cls] = stats
    qvals = bh_adjust([groups[c]["coinflip_p"] for c in CLASSES])
    for cls, q in zip(CLASSES, qvals):
        stats = groups[cls]
        ci, paired = stats["day_bootstrap_ci95"], stats["paired_control"]["day_bootstrap_ci95"]
        stats["coinflip_q"] = q
        stats["verdict"] = "PAPER_EVIDENCE_PASS" if (
            stats["n"] >= 100 and stats["entry_days"] >= 30 and stats["span_days"] >= 90
            and q <= .05 and ci and ci[0] > 0 and paired and paired[0] > 0
            and (stats["net_pf"] or 0) >= 1.5
            and all(v is not None and v > 0 for v in stats["half_net_means_pct"])
        ) else ("COLLECTING" if state["candidates"].get(cls) else "NO_QUALIFYING_CANDIDATE")
    state["summary"] = groups
    realized = []
    for trade in state["trades"]:
        if trade["status"] == "CLOSED":
            realized.append((max(trade["strategy_result"]["exit_at"],
                                 trade["control_result"]["exit_at"]),
                             trade["strategy_result"]["net_usd"]))
    equity = peak = 10000.0
    mdd = 0.0
    for _, pnl in sorted(realized):
        equity += pnl
        peak = max(peak, equity)
        mdd = max(mdd, (peak - equity) / peak * 100)
    state["portfolio"] = {"initial_usd": 10000, "realized_equity_usd": equity,
                          "realized_drawdown_pct": mdd,
                          "note": "Realized paired trades only; not daily mark-to-market drawdown."}


def save_state(path, state):
    content = json.dumps(state, indent=2, allow_nan=False) + "\n"
    temporary = path.with_suffix(".tmp")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary.write_text(content)
    temporary.replace(path)


def lock_digest(state):
    material = {"candidates": state["candidates"], "locked_at": state["locked_at"],
                "protocol": state["protocol"], "cost_pp": COST_PP,
                "horizon_hours": 48, "notional_usd": 1000,
                "entry": "first completed next-hour open",
                "gaps": "unverified session closure blocks resolution"}
    return hashlib.sha256(json.dumps(material, sort_keys=True,
                                     allow_nan=False).encode()).hexdigest()


def deploy(path, link_footer=False):
    targets = [(ROOT / "audit_dashboard/audit_scorecard.js", "/audit/audit_scorecard.js"),
               (ROOT / "audit_dashboard/ghcopilot_paper.html", "/audit/ghcopilot_paper.html"),
               (path, "/audit/data/ghcopilot_paper.json")]
    with FTP_TLS(os.environ.get("FTP_SERVER", "ftps2.50webs.com"),
                 context=ssl.create_default_context(), timeout=60) as ftp:
        ftp.login(os.environ["FTP_USER"], os.environ["FTP_PASS"])
        ftp.prot_p()
        for local, remote in targets:
            ftp.storbinary("STOR /findtorontoevents.ca" + remote, io.BytesIO(local.read_bytes()))
            print("Uploaded", remote)
        if link_footer:
            original = io.BytesIO()
            ftp.retrbinary("RETR /findtorontoevents.ca/audit/index.html", original.write)
            content = original.getvalue()
            if b'id="ghcopilot-paper-footer"' not in content:
                marker = content.lower().rfind(b"</body>")
                if marker < 0:
                    raise ValueError("Live audit body boundary not found; refusing footer edit")
                content = content[:marker] + FOOTER.encode() + content[marker:]
                ftp.storbinary("STOR /findtorontoevents.ca/audit/index.html", io.BytesIO(content))
                print("Inserted footer without regenerating audit HTML")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initialize", action="store_true")
    parser.add_argument("--screen-only", action="store_true")
    parser.add_argument("--state", type=Path, default=STATE)
    parser.add_argument("--deploy", action="store_true")
    parser.add_argument("--link-footer", action="store_true")
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    if args.screen_only:
        print(json.dumps(screen_candidates(read_db(screen=True), now), indent=2, allow_nan=False))
        return
    if args.initialize:
        if args.state.exists():
            raise ValueError("State already exists; refusing to reset prospective ledger")
        screen = screen_candidates(read_db(screen=True), now)
        state = {"schema_version": 1, "protocol": "ghcopilot-paper-v1",
                 "agent": "GHCOPILOT - AI assistant using Copilot SDK in VS Code",
                 "model": "Underlying model ID not exposed by this runtime",
                 "locked_at": now.isoformat(), "screen": screen,
                 "candidates": screen["candidates"], "trades": [], "seen": [],
                 "rejections": {}, "errors": [], "cost_pp": COST_PP,
                 "policy": "One $1000 position per class/symbol; no leverage; 48h horizon; next-bar open; conservative stops; no historical fills."}
    else:
        state = json.loads(args.state.read_text())
        if state.get("schema_version") != 1:
            raise ValueError("Unsupported state version; refusing automatic migration/reset")
        if state.get("lock_digest") != lock_digest(state):
            raise ValueError("Frozen candidates/protocol changed; refusing ledger update")
    if args.initialize:
        state["lock_digest"] = lock_digest(state)
    state["errors"] = []
    admit_signals(state, read_db(locked_at=state["locked_at"]), now)
    # Persist the first-observed timestamp even if a later provider request fails.
    save_state(args.state, state)
    for trade in state["trades"]:
        if trade["status"] in ("CLOSED", "CANCELLED"):
            continue
        try:
            bars = market_bars(trade["symbol"], utc(trade["observed_at"]), now)
            advance_trade(trade, bars, now)
        except ValueError as exc:
            trade["error"] = str(exc)
            state["errors"].append({"trade": trade["id"], "error": str(exc)})
    state["updated_at"] = now.isoformat()
    state["database_quality"] = database_quality()
    state["revision"] = os.environ.get("GITHUB_SHA", "local-initialization")
    report(state)
    save_state(args.state, state)
    print(json.dumps({"candidates": {c: v["strategy"] if v else None
                                   for c, v in state["candidates"].items()},
                      "observations": len(state["trades"]), "errors": state["errors"]}))
    if args.deploy:
        deploy(args.state, args.link_footer)
    elif args.link_footer:
        raise ValueError("--link-footer requires --deploy")
    if state["errors"]:
        raise SystemExit("Market data errors persisted; inspect public monitor")


if __name__ == "__main__":
    main()
