#!/usr/bin/env python3
"""Crypto Paper Pilot — SHADOW->LIVE forward tracker for mega_mutation CRYPTO.

EDGE-HUNT VERDICT 2026-05-18 — the per-class candidate trade hunt
(reports/PER_CLASS_CANDIDATE_TRADES_2026-05-18.md,
reports/MAGIC_FILTER_HUNT_2026-05-18.md) found exactly ONE in-sample-profitable
non-artifact CRYPTO cohort: strategy `mega_mutation` (n=72, PF 2.19, WR 56.9%,
total +110.4% on the canonical deduped policy-clean ledger). n is too small for
an edge_stability_harness verdict (~1 walk-forward window). The honest next
step is to PAPER-TRACK it forward — the forward win-rate over the next ~8-10
weeks IS the real test. If `mega_mutation` holds PF>1.5 across >=5 walk-forward
windows it becomes the first real edge; if it sign-flips it joins the kill log.

This script clones the proven COT paper pilot
(alpha_engine/strategies/cot_paper_pilot.py) but for CRYPTO + `mega_mutation`.
The COT-specific CFTC release-week dedup logic is dropped (crypto picks are
not weekly-report re-emissions).

## Architecture

1. SEED (one-time): on first run, if the status JSON does not yet exist, seed
   the open-pick ledger from the historical `mega_mutation` CRYPTO cohort in
   `genome/data/closed_picks.json` — the same source pf_registry.json aggregates
   (deduped to n=72). Each seed pick carries symbol, direction, entry_price, tp,
   sl, entry_ts and starts status=OPEN (the FORWARD result is what we want, so
   we re-track from entry rather than trusting the historical close).
2. RESOLVE (every run): for each OPEN pick, fetch the live crypto price via the
   project API-failover chain (alpha_engine/api_failover.py — Binance mirrors ->
   Bybit -> CoinGecko -> KuCoin -> CryptoCompare). Mark WON if TP touched, LOST
   if SL touched, EXPIRED (resolved at last price) if max-hold elapsed.
3. AGGREGATE: rolling WR / PF / equity curve over the resolved (closed) picks,
   plus a SHADOW->LIVE graduation gate. Graduation here means ONLY
   "forward-confirmed" — it NEVER authorises real capital.

Output: audit_dashboard/data/crypto_mega_mutation_paper_pilot.json — consumed by
audit_dashboard/crypto_paper_pilot.html. Same status-JSON shape as the COT
pilot so the viewer pattern is reusable.

## Graduation gate (paper-only — never real capital)

  n_resolved < MIN_TRADES                 -> INSUFFICIENT_DATA
  PF >= 1.5 AND WR >= 50% AND n >= MIN     -> FORWARD_CONFIRMED  (paper graduate)
  PF in [1.0, 1.5)                         -> HOLDING            (keep tracking)
  PF < 1.0                                 -> FORWARD_FAILED     (sign-flip -> kill log)

Usage:
    python alpha_engine/strategies/crypto_paper_pilot.py             # default
    python alpha_engine/strategies/crypto_paper_pilot.py --dry-run   # no JSON write
    python alpha_engine/strategies/crypto_paper_pilot.py --reseed    # rebuild ledger
    python alpha_engine/strategies/crypto_paper_pilot.py --offline   # skip live fetch

NFA — paper pilot only. No real-money sizing, ever. Graduation == forward-
confirmed in paper, nothing more.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

# --- API failover (project API Failover Rule: 3+ fallback chain) ------------
# Binance mirrors -> Bybit -> CoinGecko -> KuCoin -> CryptoCompare.
try:
    from alpha_engine.api_failover import fetch_price as _failover_fetch_price
except Exception:  # pragma: no cover - direct-run / path fallback
    try:
        from api_failover import fetch_price as _failover_fetch_price  # type: ignore
    except Exception:
        _failover_fetch_price = None  # offline-only mode

# --- pilot parameters -------------------------------------------------------
STRATEGY_NAME = "mega_mutation"
ASSET_CLASS = "CRYPTO"
SEED_SOURCE = "genome/data/closed_picks.json"
DEFAULT_OUT = "audit_dashboard/data/crypto_mega_mutation_paper_pilot.json"

# Max holding period before an unresolved pick is force-closed at last price.
MAX_HOLD_DAYS = 21

# Graduation thresholds (paper-only — "forward-confirmed", never real capital).
MIN_TRADES_FOR_GATE = 20      # below this -> INSUFFICIENT_DATA
GRAD_PF_FLOOR = 1.5           # PF >= this for FORWARD_CONFIRMED
GRAD_WR_FLOOR = 50.0          # WR%% >= this for FORWARD_CONFIRMED

# In-sample reference cohort (pf_registry.json::by_asset_class_strategy_policy_clean_net,
# strategy=mega_mutation / CRYPTO — the figure the forward result is judged against).
INSAMPLE = {
    "n": 72, "pf": 2.19, "wr_pct": 56.94, "total_pnl_pct": 110.39,
    "source": "reports/PER_CLASS_CANDIDATE_TRADES_2026-05-18.md",
}

REFS = [
    "reports/PER_CLASS_CANDIDATE_TRADES_2026-05-18.md",
    "reports/MAGIC_FILTER_HUNT_2026-05-18.md",
]


# ---------------------------------------------------------------------------
# Timestamp helpers
# ---------------------------------------------------------------------------
def _parse_dt(value) -> datetime | None:
    """Parse a pick timestamp into an aware UTC datetime, or None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    s = str(value).strip()
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:len(fmt) + 2], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _entry_ts(row: dict) -> str:
    """Pick the canonical entry timestamp from a raw seed row."""
    for k in ("entry_date", "entry_time", "timestamp", "generated_at",
              "created_at", "closed_at"):
        v = row.get(k)
        if v:
            return str(v)
    return ""


# ---------------------------------------------------------------------------
# Seeding — one-time, from the historical mega_mutation CRYPTO cohort
# ---------------------------------------------------------------------------
def _dedup_key(row: dict) -> tuple:
    """Mirror pf_registry.json dedup key so we seed exactly the n=72 cohort:
    (strategy, symbol, direction, trade_date, entry_price~2p)."""
    return (
        STRATEGY_NAME,
        row.get("symbol"),
        row.get("direction"),
        _entry_ts(row)[:10],
        round(float(row.get("entry_price") or 0.0), 2),
    )


def seed_picks() -> list[dict]:
    """Build the seed open-pick ledger from genome/data/closed_picks.json.

    Selects source_system == 'mega_mutation' CRYPTO rows, deduplicates with the
    pf_registry key (reproduces the canonical n=72 cohort), and emits each pick
    in OPEN state so its FORWARD outcome is tracked fresh.
    """
    src = ROOT / SEED_SOURCE
    raw = json.loads(src.read_text(encoding="utf-8"))
    rows = raw if isinstance(raw, list) else raw.get("picks", raw.get("closed_picks", []))

    cohort = [
        r for r in rows
        if isinstance(r, dict)
        and str(r.get("source_system")) == STRATEGY_NAME
        and str(r.get("asset_class", "CRYPTO")).upper() == ASSET_CLASS
    ]

    seen: dict[tuple, dict] = {}
    for r in cohort:
        key = _dedup_key(r)
        if key not in seen:
            seen[key] = r

    picks = []
    for i, r in enumerate(sorted(seen.values(), key=lambda x: _entry_ts(x))):
        entry = float(r.get("entry_price") or 0.0)
        tp = r.get("take_profit")
        sl = r.get("stop_loss")
        picks.append({
            "pick_id": f"mm-{i:03d}",
            "symbol": r.get("symbol"),
            "direction": (r.get("direction") or "LONG").upper(),
            "entry_price": entry,
            "take_profit": float(tp) if tp not in (None, "") else None,
            "stop_loss": float(sl) if sl not in (None, "") else None,
            "entry_ts": _entry_ts(r),
            "mutation_name": r.get("mutation_name") or r.get("strategy"),
            # FORWARD tracking starts fresh — status begins OPEN regardless of
            # the historical close. The forward result is the real verdict.
            "status": "OPEN",
            "exit_price": None,
            "exit_ts": None,
            "exit_reason": None,
            "pnl_pct": None,
            "seeded_from_historical_status": r.get("status"),
        })
    return picks


# ---------------------------------------------------------------------------
# Resolution — mark OPEN picks WON / LOST / EXPIRED against live price
# ---------------------------------------------------------------------------
def _fetch_live_price(symbol: str, offline: bool) -> float | None:
    """Live crypto price via the API-failover chain. None when unavailable."""
    if offline or _failover_fetch_price is None:
        return None
    try:
        return _failover_fetch_price(symbol)
    except Exception as exc:  # pragma: no cover
        print(f"  price fetch failed for {symbol}: {exc}", file=sys.stderr)
        return None


def _pnl_pct(direction: str, entry: float, exit_px: float) -> float:
    if entry <= 0:
        return 0.0
    raw = (exit_px - entry) / entry * 100.0
    return raw if direction == "LONG" else -raw


def resolve_picks(picks: list[dict], offline: bool, now: datetime) -> dict:
    """Resolve every OPEN pick against the live price. Mutates picks in place.

    Returns a counter dict {resolved, still_open, no_price}.
    """
    counter = {"resolved": 0, "still_open": 0, "no_price": 0}
    for p in picks:
        if p.get("status") != "OPEN":
            continue
        symbol = p.get("symbol")
        entry = float(p.get("entry_price") or 0.0)
        direction = p.get("direction", "LONG")
        tp = p.get("take_profit")
        sl = p.get("stop_loss")
        entry_dt = _parse_dt(p.get("entry_ts"))

        price = _fetch_live_price(symbol, offline)
        if price is None or price <= 0:
            counter["no_price"] += 1
            counter["still_open"] += 1
            continue

        hit_tp = tp is not None and (
            (direction == "LONG" and price >= tp) or
            (direction == "SHORT" and price <= tp)
        )
        hit_sl = sl is not None and (
            (direction == "LONG" and price <= sl) or
            (direction == "SHORT" and price >= sl)
        )
        expired = entry_dt is not None and (now - entry_dt) >= timedelta(days=MAX_HOLD_DAYS)

        if hit_tp:
            p["status"], p["exit_reason"] = "WON", "TP_HIT"
            p["exit_price"] = float(tp)
        elif hit_sl:
            p["status"], p["exit_reason"] = "LOST", "SL_HIT"
            p["exit_price"] = float(sl)
        elif expired:
            exit_px = price
            p["exit_price"] = exit_px
            pnl = _pnl_pct(direction, entry, exit_px)
            p["status"] = "WON" if pnl > 0 else "LOST"
            p["exit_reason"] = "MAX_HOLD"
        else:
            p["last_price"] = price
            counter["still_open"] += 1
            continue

        p["exit_ts"] = now.isoformat()
        p["pnl_pct"] = round(_pnl_pct(direction, entry, float(p["exit_price"])), 4)
        counter["resolved"] += 1
    return counter


# ---------------------------------------------------------------------------
# Aggregation — rolling WR / PF / equity curve
# ---------------------------------------------------------------------------
def compute_stats(picks: list[dict]) -> dict:
    """Rolling WR / PF / cumulative-pnl equity curve over resolved picks."""
    closed = [p for p in picks
              if p.get("status") in ("WON", "LOST") and p.get("pnl_pct") is not None]
    closed.sort(key=lambda p: p.get("exit_ts") or "")

    trades = []
    cum = 0.0
    gross_profit = 0.0
    gross_loss = 0.0
    n_wins = n_losses = 0
    for p in closed:
        pnl = float(p["pnl_pct"])
        cum += pnl
        if pnl > 0:
            gross_profit += pnl
            n_wins += 1
        else:
            gross_loss += -pnl
            n_losses += 1
        trades.append({
            "pick_id": p.get("pick_id"),
            "symbol": p.get("symbol"),
            "direction": p.get("direction"),
            "status": p.get("status"),
            "exit_reason": p.get("exit_reason"),
            "entry_price": p.get("entry_price"),
            "exit_price": p.get("exit_price"),
            "pnl_pct": round(pnl, 4),
            "cum_pnl_pct": round(cum, 4),
            "entry_ts": p.get("entry_ts"),
            "exit_ts": p.get("exit_ts"),
        })

    n_total = len(closed)
    wr = (n_wins * 100.0 / n_total) if n_total else 0.0
    pf = (gross_profit / gross_loss) if gross_loss > 0 else (
        None if gross_profit == 0 else float("inf"))
    avg = (cum / n_total) if n_total else 0.0

    return {
        "n_total": n_total,
        "n_wins": n_wins,
        "n_losses": n_losses,
        "n_open": sum(1 for p in picks if p.get("status") == "OPEN"),
        "wr_pct": round(wr, 2),
        "profit_factor": round(pf, 4) if isinstance(pf, float) and pf != float("inf") else pf,
        "gross_profit_pct": round(gross_profit, 4),
        "gross_loss_pct": round(gross_loss, 4),
        "cum_pnl_pct": round(cum, 4),
        "avg_pnl_per_trade_pct": round(avg, 4),
        "trades": trades,
    }


def graduation_gate_verdict(stats: dict) -> dict:
    """SHADOW->LIVE gate. Graduation == forward-confirmed in PAPER only.

    This NEVER authorises real capital — it only states the forward result
    has replicated the in-sample edge.
    """
    n = stats["n_total"]
    pf = stats["profit_factor"]
    wr = stats["wr_pct"]
    if n < MIN_TRADES_FOR_GATE:
        return {
            "verdict": "INSUFFICIENT_DATA",
            "detail": f"need {MIN_TRADES_FOR_GATE}+ forward-resolved trades, have {n}",
            "forward_confirmed": False,
        }
    if pf is None:
        return {
            "verdict": "INSUFFICIENT_DATA",
            "detail": "profit factor undefined (no losses yet)",
            "forward_confirmed": False,
        }
    pf_v = float(pf)
    if pf_v < 1.0:
        return {
            "verdict": "FORWARD_FAILED",
            "detail": f"PF {pf_v:.2f} < 1.0 — in-sample edge sign-flipped forward; "
                      f"candidate -> kill log",
            "forward_confirmed": False,
        }
    if pf_v >= GRAD_PF_FLOOR and wr >= GRAD_WR_FLOOR:
        return {
            "verdict": "FORWARD_CONFIRMED",
            "detail": f"PF {pf_v:.2f} >= {GRAD_PF_FLOOR} and WR {wr:.1f}% >= "
                      f"{GRAD_WR_FLOOR}% on n={n} — forward-confirmed (PAPER only, "
                      f"no real capital)",
            "forward_confirmed": True,
        }
    return {
        "verdict": "HOLDING",
        "detail": f"PF {pf_v:.2f} in [1.0, {GRAD_PF_FLOOR}) — profitable but below "
                  f"the forward-confirm floor; keep tracking",
        "forward_confirmed": False,
    }


# ---------------------------------------------------------------------------
# Ledger persistence
# ---------------------------------------------------------------------------
def load_or_seed(out_path: Path, reseed: bool) -> list[dict]:
    """Return the current open-pick ledger — seed it if missing or --reseed."""
    if not reseed and out_path.exists():
        try:
            prev = json.loads(out_path.read_text(encoding="utf-8"))
            picks = prev.get("picks")
            if isinstance(picks, list) and picks:
                return picks
        except Exception as exc:
            print(f"# existing ledger unreadable ({exc}); reseeding", file=sys.stderr)
    print(f"# seeding ledger from {SEED_SOURCE}", file=sys.stderr)
    return seed_picks()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", default=DEFAULT_OUT)
    p.add_argument("--dry-run", action="store_true",
                   help="compute + print payload, do not write JSON")
    p.add_argument("--reseed", action="store_true",
                   help="rebuild the ledger from the seed source (discards forward state)")
    p.add_argument("--offline", action="store_true",
                   help="skip live price fetch (seed/aggregate only)")
    args = p.parse_args()

    out_path = ROOT / args.out
    now = datetime.now(timezone.utc)

    print(f"# Crypto Paper Pilot — {STRATEGY_NAME} ({ASSET_CLASS})", file=sys.stderr)

    picks = load_or_seed(out_path, args.reseed)
    print(f"# ledger: {len(picks)} picks "
          f"({sum(1 for x in picks if x.get('status') == 'OPEN')} open)", file=sys.stderr)

    counter = resolve_picks(picks, args.offline, now)
    print(f"# resolved this run: {counter['resolved']}  still open: "
          f"{counter['still_open']}  no_price: {counter['no_price']}", file=sys.stderr)

    stats = compute_stats(picks)
    gate = graduation_gate_verdict(stats)

    payload = {
        "generated_at": now.isoformat(),
        "strategy_name": STRATEGY_NAME,
        "asset_class": ASSET_CLASS,
        "title": "Crypto Paper Pilot — mega_mutation",
        "pilot_kind": "forward-tracking SHADOW->LIVE paper pilot (no real capital)",
        "seed_source": SEED_SOURCE,
        "max_hold_days": MAX_HOLD_DAYS,
        "api_failover_chain": [
            "Binance mirrors (api, api1, api2, api3, data-api, binance.us)",
            "Bybit v5", "CoinGecko", "KuCoin", "CryptoCompare",
        ],
        "in_sample_reference": INSAMPLE,
        "refs": REFS,
        "evidence_source": (
            "forward paper-pilot ledger — mega_mutation CRYPTO cohort re-tracked "
            "from entry against live API-failover prices"
        ),
        "stats": stats,
        "graduation_gate": gate,
        "state_machine": {
            "current_state": "SHADOW",
            "next_state": "FORWARD_CONFIRMED" if gate["forward_confirmed"] else "SHADOW",
            "target_state": "FORWARD_CONFIRMED (paper) — NEVER real capital",
            "notes": [
                "in-sample n=72 PF 2.19 WR 56.9% — only ~1 walk-forward window, "
                "no harness verdict",
                "forward win-rate over the next ~8-10 weeks IS the real test",
                "graduation here means forward-confirmed in paper only",
            ],
        },
        "resolution_counter": counter,
        "picks": picks,
        "nfa": ("Paper pilot only. Forward-tracking research surface. NO real "
                "capital, ever — 'graduation' means forward-confirmed in paper."),
    }

    print(f"# n_resolved={stats['n_total']} WR={stats['wr_pct']}% "
          f"PF={stats['profit_factor']} cum_pnl={stats['cum_pnl_pct']}%  "
          f"gate={gate['verdict']}", file=sys.stderr)

    if args.dry_run:
        print(json.dumps(payload, indent=2, default=str))
        return

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"# wrote {out_path}  ({out_path.stat().st_size:,} bytes)", file=sys.stderr)


if __name__ == "__main__":
    main()
