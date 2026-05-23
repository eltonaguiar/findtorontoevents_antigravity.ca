#!/usr/bin/env python3
"""
Consensus Pick Builder
=======================
Scans all copy trader picks across intel/clones/highscore sources,
finds where 2+ independent traders agree on the same symbol+direction,
and creates consensus picks with boosted confidence and score.

These picks get saved as data/consensus_active_picks.json and are
picked up by dashboard_generator.py as source 'copy_trader_consensus'.

The more traders that agree, the higher the confidence multiplier.
"""
import json, sys, os, hashlib
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(__file__).resolve().parent / "data"
ALPHA_DATA = ROOT / "alpha_engine" / "data"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from alpha_engine.feed_hygiene import sanitize_active_picks
except ImportError:
    sanitize_active_picks = lambda picks, label="": picks  # graceful fallback
try:
    from audit_trail.quality_gates import passes_active_gate
except ImportError:
    passes_active_gate = lambda pick: True  # graceful fallback
PAYLOAD_PATH = ROOT / "audit_trail" / "data" / "dashboard_payload.json"

NOW = datetime.now(timezone.utc)
NOW_ISO = NOW.isoformat()
OPEN_STATUSES = {"", "OPEN", "ACTIVE", "LIVE", "PENDING"}
CT_MAX_AGE_HOURS = 24


def load_json(path):
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str, ensure_ascii=False)


def safe_float(v, default=0.0):
    try:
        return float(v or default)
    except (ValueError, TypeError):
        return default


def normalize_trader_identity(strategy="", trader_label=""):
    """Map clone/highscore/copy variants back to one underlying trader identity."""
    raw = str(trader_label or strategy or "").strip()
    lower = raw.lower()
    for prefix in ("clone_hl_copy_", "copy_hl_", "hs_"):
        if lower.startswith(prefix):
            raw = raw[len(prefix):]
            break
    return " ".join(raw.strip().lower().split())


def pick_id(symbol, direction):
    raw = "consensus_{}_{}_{:.0f}".format(symbol, direction, NOW.timestamp())
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def normalize_symbol(symbol=""):
    return str(symbol or "").upper().replace("/", "").replace("-", "").replace("_", "").strip()


def normalize_direction(direction="LONG"):
    text = str(direction or "LONG").upper().strip()
    if text in ("SELL", "SHORT"):
        return "SHORT"
    if text in ("BUY", "LONG"):
        return "LONG"
    return "LONG"


def normalize_confidence(value):
    conf = safe_float(value, 0.0)
    if conf <= 0:
        return 0.0
    return round(min(conf, 1.0) if conf <= 1.0 else min(conf / 100.0, 1.0), 4)


def get_pick_timestamp(pick):
    for key in ("timestamp", "detected_at", "generated_at", "entry_date", "entryDate", "created_at", "scan_time"):
        value = pick.get(key)
        if value:
            return str(value)
    return ""


def parse_timestamp(ts_str):
    if not ts_str:
        return None
    try:
        ts = str(ts_str).strip()
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        if " " in ts and "T" not in ts:
            ts = ts.replace(" ", "T")
            if "+" not in ts and "-" not in ts[10:]:
                ts += "+00:00"
        if "+" not in ts and "-" not in ts[10:] and len(ts) >= 19:
            ts += "+00:00"
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def logical_pick_key(pick):
    raw_id = pick.get("id")
    source = pick.get("source_system") or pick.get("_ct_source") or ""
    if raw_id not in (None, ""):
        return ("id", source, str(raw_id))
    ts = get_pick_timestamp(pick)
    ts_key = ts[:19] if ts else ""
    return (
        "fallback",
        source,
        normalize_symbol(pick.get("symbol", "")),
        normalize_direction(pick.get("direction", "LONG")),
        str(pick.get("strategy", "") or ""),
        round(safe_float(pick.get("entry_price"), 0.0), 8),
        ts_key,
    )


def normalize_source_pick(raw, src_name):
    if not isinstance(raw, dict):
        return None
    pick = dict(raw)
    pick["_ct_source"] = pick.get("_ct_source") or src_name
    pick["source_system"] = pick.get("source_system") or src_name
    pick["asset_class"] = pick.get("asset_class") or "CRYPTO"
    pick["category"] = pick.get("category") or "crypto"
    pick["status"] = str(pick.get("status") or "OPEN").upper().strip()
    pick["direction"] = normalize_direction(pick.get("direction", pick.get("signal_type", "LONG")))
    if not pick.get("take_profit"):
        pick["take_profit"] = pick.get("target_price") or pick.get("targetPrice") or pick.get("tp")
    if not pick.get("stop_loss"):
        pick["stop_loss"] = pick.get("stop_price") or pick.get("stopPrice") or pick.get("sl")
    ts = get_pick_timestamp(pick)
    if ts and not pick.get("timestamp"):
        pick["timestamp"] = ts
    pick["confidence"] = normalize_confidence(pick.get("confidence", pick.get("score", 0)))
    return pick


def is_open_like_pick(pick):
    status = str(pick.get("status") or "").upper().strip()
    if status not in OPEN_STATUSES:
        return False
    if any(pick.get(key) for key in ("closed_at", "resolved_at", "exit_time", "close_time")):
        return False
    pnl = pick.get("pnl_pct")
    if pnl not in (None, ""):
        try:
            if abs(float(pnl)) >= 0.01:
                return False
        except (ValueError, TypeError):
            pass
    return True


def is_recent_copy_pick(pick):
    dt = parse_timestamp(get_pick_timestamp(pick))
    if not dt:
        return False
    age_hours = (NOW - dt).total_seconds() / 3600
    return age_hours <= CT_MAX_AGE_HOURS


def run():
    print("=" * 70)
    print("  CONSENSUS PICK BUILDER")
    print("  " + NOW.strftime("%Y-%m-%d %H:%M UTC"))
    print("=" * 70)

    # ── Load all CT source files ──
    sources = [
        ("copy_trader_intel", DATA_DIR / "active_picks.json"),
        ("copy_trader_highscore", DATA_DIR / "highscore_active_picks.json"),
        ("copy_trader_clones", DATA_DIR / "clone_active_picks.json"),
        ("copy_trader_variations", DATA_DIR / "variation_active_picks.json"),
    ]

    all_ct_picks = {}
    source_counts = defaultdict(int)
    rejected_closed = 0
    rejected_stale = 0
    rejected_quality = 0
    deduped_dups = 0
    for src_name, path in sources:
        data = load_json(path)
        if not data:
            continue
        picks = data if isinstance(data, list) else data.get("picks", data.get("active_picks", []))
        for p in picks:
            pick = normalize_source_pick(p, src_name)
            if not pick:
                continue
            source_counts[src_name] += 1
            if not is_open_like_pick(pick):
                rejected_closed += 1
                continue
            if not is_recent_copy_pick(pick):
                rejected_stale += 1
                continue
            if not passes_active_gate(pick):
                rejected_quality += 1
                continue
            key = logical_pick_key(pick)
            existing = all_ct_picks.get(key)
            if existing:
                deduped_dups += 1
                if pick.get("confidence", 0) > existing.get("confidence", 0):
                    all_ct_picks[key] = pick
            else:
                all_ct_picks[key] = pick

    # Also check dashboard payload for additional CT picks
    payload = load_json(PAYLOAD_PATH)
    if payload:
        active = payload.get("picks", {}).get("active", [])
        for p in active:
            src = (p.get("source_system", "") or "").lower()
            if src == "copy_trader_consensus":
                continue
            if "copy_trader" in src and p.get("_ct_source") is None:
                pick = normalize_source_pick(p, src)
                if not pick or not is_open_like_pick(pick) or not is_recent_copy_pick(pick) or not passes_active_gate(pick):
                    continue
                key = logical_pick_key(pick)
                existing = all_ct_picks.get(key)
                if existing:
                    deduped_dups += 1
                    if pick.get("confidence", 0) > existing.get("confidence", 0):
                        all_ct_picks[key] = pick
                else:
                    all_ct_picks[key] = pick

    all_ct_picks = list(all_ct_picks.values())
    print("  Loaded {} quality-gated open copy trader picks".format(len(all_ct_picks)))
    if source_counts:
        print("  Source rows read: {}".format(", ".join(f"{src}={count}" for src, count in sorted(source_counts.items()))))
    if rejected_closed or rejected_stale or rejected_quality or deduped_dups:
        print("  Filtered rows: closed_or_resolved={}, stale_or_untimestamped={}, quality_gate={}, deduped={}".format(
            rejected_closed, rejected_stale, rejected_quality, deduped_dups))

    # ── Group by (normalized symbol, direction) ──
    groups = defaultdict(lambda: {"traders": set(), "picks": [], "strategies": set(), "timestamps": []})

    for p in all_ct_picks:
        symbol = normalize_symbol(p.get("symbol", ""))
        if not symbol:
            continue
        direction = normalize_direction(p.get("direction", "LONG"))
        key = (symbol, direction)

        trader = normalize_trader_identity(
            p.get("strategy", p.get("_ct_source", "unknown")),
            p.get("trader_label", ""),
        )
        if not trader:
            trader = normalize_trader_identity(p.get("_ct_source", "unknown"))
        groups[key]["traders"].add(trader)
        groups[key]["picks"].append(p)
        groups[key]["strategies"].add(p.get("_ct_source", "unknown"))
        ts = get_pick_timestamp(p)
        if ts:
            groups[key]["timestamps"].append(ts)

    # ── Build consensus picks where 2+ independent traders agree ──
    consensus_picks = []
    stats = {"total_groups": len(groups), "consensus_2": 0, "consensus_3": 0, "consensus_4": 0, "consensus_5plus": 0}

    for (symbol, direction), data in sorted(groups.items(), key=lambda x: -len(x[1]["traders"])):
        num_traders = len(data["traders"])
        if num_traders < 2:
            continue

        if num_traders >= 5:
            stats["consensus_5plus"] += 1
        elif num_traders >= 4:
            stats["consensus_4"] += 1
        elif num_traders >= 3:
            stats["consensus_3"] += 1
        else:
            stats["consensus_2"] += 1

        # Confidence scales with consensus count
        # 2 traders = 0.70, 3 = 0.80, 4 = 0.88, 5+ = 0.95
        base_conf = min(0.95, 0.60 + num_traders * 0.07)

        # Aggregate entry prices
        entries = [safe_float(p.get("entry_price")) for p in data["picks"] if safe_float(p.get("entry_price")) > 0]
        avg_entry = sum(entries) / len(entries) if entries else 0

        # Aggregate TP/SL from underlying picks
        tps = [safe_float(p.get("take_profit")) for p in data["picks"] if safe_float(p.get("take_profit")) > 0]
        sls = [safe_float(p.get("stop_loss")) for p in data["picks"] if safe_float(p.get("stop_loss")) > 0]
        avg_tp = sum(tps) / len(tps) if tps else None
        avg_sl = sum(sls) / len(sls) if sls else None

        # Best entry date (most recent)
        dates = []
        for p in data["picks"]:
            for key in ["entry_date", "detected_at"]:
                val = p.get(key)
                if val:
                    dates.append(str(val))
                    break

        cpick = {
            "id": pick_id(symbol, direction),
            "strategy": "ct_consensus_{}_{}".format(symbol.lower(), direction.lower()),
            "symbol": symbol,
            "category": "crypto",
            "asset_class": "CRYPTO",
            "signal_type": "CONSENSUS",
            "direction": direction,
            "entry_price": round(avg_entry, 8) if avg_entry else None,
            "entry_date": max(dates) if dates else NOW_ISO,
            "timestamp": max(data["timestamps"]) if data["timestamps"] else NOW_ISO,
            "detected_at": NOW_ISO,
            "take_profit": round(avg_tp, 8) if avg_tp else None,
            "stop_loss": round(avg_sl, 8) if avg_sl else None,
            "confidence": round(base_conf, 4),
            "ml_score": None,
            "status": "OPEN",
            "source_system": "copy_trader_consensus",
            "consensus_count": num_traders,
            "agreeing_traders": sorted(data["traders"]),
            "agreeing_sources": sorted(data["strategies"]),
            "reason": "{} independent copy traders agree on {} {}".format(
                num_traders, symbol, direction),
        }
        consensus_picks.append(cpick)

    # Sort by consensus count (highest first)
    consensus_picks.sort(key=lambda x: -x["consensus_count"])

    # ── Save ──
    consensus_picks = sanitize_active_picks(consensus_picks, "copy_trader_consensus")
    output = {
        "generated_at": NOW_ISO,
        "total_consensus_picks": len(consensus_picks),
        "stats": stats,
        "picks": consensus_picks,
    }
    save_json(DATA_DIR / "consensus_active_picks.json", output)

    # ── Print summary ──
    print("\n  CONSENSUS RESULTS:")
    print("  Total groups: {}".format(stats["total_groups"]))
    print("  5+ traders agree: {}".format(stats["consensus_5plus"]))
    print("  4 traders agree: {}".format(stats["consensus_4"]))
    print("  3 traders agree: {}".format(stats["consensus_3"]))
    print("  2 traders agree: {}".format(stats["consensus_2"]))
    print("  Total consensus picks: {}".format(len(consensus_picks)))

    print("\n  TOP CONSENSUS PICKS:")
    for cp in consensus_picks[:15]:
        print("    {} {}: {} traders, conf={:.2f}, traders={}".format(
            cp["symbol"], cp["direction"],
            cp["consensus_count"], cp["confidence"],
            cp["agreeing_traders"][:3]))

    print("\n  [OK] Saved to data/consensus_active_picks.json")
    return output


if __name__ == "__main__":
    run()
