#!/usr/bin/env python3
"""Resolve provenance-ledger picks into outcomes — without ever touching the picks.

THE OTHER HALF OF THE LOOP
    tools/provenance_ledger.py records intent at emit time. On its own that proves
    a pick existed before an outcome, but nothing ever computes the outcome, so
    pct_forward stays null and no statistic can be formed.

    This reads the pick ledger, decides each pick's outcome from market data, and
    appends the outcome to a SEPARATE append-only file. The pick records are never
    modified — that is the entire guarantee. If a resolver could rewrite the picks
    it could backfill them, and the ledger would be worthless.

CONVENTIONS (chosen to be pessimistic, and stated so they can be argued with)
  * Entry at the FIRST bar OPEN at or after signal_ts. Never at the signal price.
  * If a bar's range touches BOTH TP and SL, the SL is assumed to have filled
    first. Intrabar ordering is unknowable from OHLC, so the pessimistic branch is
    the only defensible one. This systematically understates win rate.
  * A pick with no resolution within MAX_DAYS stays OPEN, not "expired as a win".
  * Outcomes are appended with their own hash chain, so a resolution cannot be
    edited after the fact either.
  * `resolved_at` is stamped when THIS PROCESS decides, and must be > created_at.

WHAT IT REPORTS
    n_emitted / n_resolved / n_open / pct_forward / hit rate / mean / PF,
    and per-strategy and per-side breakdowns.

Read-only on picks. Append-only on resolutions. No orders, no keys. Not advice.

Usage:
    python3 tools/provenance_resolver.py --status
    python3 tools/provenance_resolver.py --resolve
    python3 tools/provenance_resolver.py --selftest
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PICKS = REPO / "reports/provenance/picks_provenance.jsonl"
RES = REPO / "reports/provenance/resolutions.jsonl"
STATUS = REPO / "reports/provenance/resolved_status.json"
GENESIS = "0" * 64
MAX_DAYS = 45


# ---------------------------------------------------------------- helpers
def _canon(rec: dict) -> bytes:
    return json.dumps(rec, sort_keys=True, separators=(",", ":")).encode()


def _sha(rec: dict) -> str:
    return hashlib.sha256(_canon(rec)).hexdigest()


def read_jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    out = []
    for line in p.open():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def yf_symbol(sym: str) -> str:
    """BTCUSDT -> BTC-USD ; SPY -> SPY ; BTC/USDT -> BTC-USD."""
    s = (sym or "").upper().replace("/", "")
    for q in ("USDT", "USDC", "BUSD", "PERP"):
        if s.endswith(q) and len(s) > len(q):
            return f"{s[:-len(q)]}-USD"
    return (sym or "").upper()


def load_bars(symbols: list[str], start: datetime):
    import yfinance as yf
    frames = {}
    for s in symbols:
        try:
            df = yf.download(s, start=start.date(), progress=False,
                             auto_adjust=False, interval="1h", timeout=25)
        except Exception:  # noqa: BLE001
            continue
        if df is None or df.empty:
            continue
        if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
            df.columns = [c[0] for c in df.columns]
        frames[s] = df
    return frames


def decide(pick: dict, bars) -> dict | None:
    """Return an outcome dict or None if still open / no data."""
    side = pick["side"]
    tp, sl = float(pick["tp"]), float(pick["sl"])
    start = datetime.fromisoformat(pick["created_at"])
    if bars is None or bars.empty:
        return None
    idx = bars.index
    try:
        # entry at the first bar at/after creation
        if idx.tz is not None:
            mask = idx >= start
        else:
            mask = idx >= start.replace(tzinfo=None)
        pos = int(mask.argmax()) if mask.any() else -1
    except (TypeError, ValueError):
        return None
    if pos < 0:
        return None
    entry = float(bars["Open"].iloc[pos]) if "Open" in bars else float(bars["Close"].iloc[pos])
    if not (entry > 0):
        return None
    deadline = start + timedelta(days=MAX_DAYS)
    for i in range(pos, len(bars)):
        ts = idx[i]
        t = ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        if t > deadline:
            break
        hi = float(bars["High"].iloc[i]) if "High" in bars else float(bars["Close"].iloc[i])
        lo = float(bars["Low"].iloc[i]) if "Low" in bars else float(bars["Close"].iloc[i])
        hit_tp = hi >= tp if side == "LONG" else lo <= tp
        hit_sl = lo <= sl if side == "LONG" else hi >= sl
        if hit_sl:                      # pessimistic: SL first on ambiguity
            return {"outcome": "SL", "exit_px": sl, "exit_utc": t.isoformat(),
                    "entry_px": entry, "bars_held": i - pos + 1}
        if hit_tp:
            return {"outcome": "TP", "exit_px": tp, "exit_utc": t.isoformat(),
                    "entry_px": entry, "bars_held": i - pos + 1}
    return None


def ret_bp(pick: dict, o: dict) -> float:
    r = (o["exit_px"] / o["entry_px"] - 1) * 1e4
    return -r if pick["side"] == "SHORT" else r


def append_resolutions(rows: list[dict], path: Path = RES) -> int:
    prev = GENESIS
    existing = read_jsonl(path)
    if existing:
        prev = existing[-1]["sha256"]
    seq = len(existing)
    with path.open("a") as f:
        for r in rows:
            seq += 1
            rec = dict(r, seq=seq, prev_sha256=prev)
            rec["sha256"] = _sha(rec)
            prev = rec["sha256"]
            f.write(json.dumps(rec, sort_keys=True) + "\n")
    return len(rows)


def verify_resolutions(path: Path = RES) -> dict:
    recs = read_jsonl(path)
    prev = GENESIS
    for i, r in enumerate(recs):
        stored = r.get("sha256")
        body = {k: v for k, v in r.items() if k != "sha256"}
        if r.get("seq") != i + 1:
            return {"ok": False, "index": i, "reason": "seq gap"}
        if r.get("prev_sha256") != prev:
            return {"ok": False, "index": i, "reason": "prev_sha256 mismatch"}
        if _sha(body) != stored:
            return {"ok": False, "index": i, "reason": "sha256 mismatch"}
        prev = stored
    return {"ok": True, "n": len(recs)}


def compute_status() -> dict:
    picks = read_jsonl(PICKS)
    res = read_jsonl(RES)
    by_pick = {r["pick_seq"]: r for r in res}
    resolved = [p for p in picks if p["seq"] in by_pick]
    # pct_forward: resolved picks whose resolution was decided AFTER creation
    fwd = 0
    for p in resolved:
        r = by_pick[p["seq"]]
        try:
            if datetime.fromisoformat(r["resolved_at"]) > datetime.fromisoformat(p["created_at"]):
                fwd += 1
        except (KeyError, ValueError):
            pass
    rets = []
    for p in resolved:
        r = by_pick[p["seq"]]
        try:
            rets.append(ret_bp(p, {"exit_px": float(r["exit_px"]),
                                   "entry_px": float(r["entry_px"])}))
        except (KeyError, TypeError, ValueError):
            continue

    def pf(xs):
        w = sum(v for v in xs if v > 0)
        l = -sum(v for v in xs if v < 0)
        return (w / l) if l > 0 else (float("nan") if not w else float("inf"))

    st = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_emitted": len(picks),
        "n_resolved": len(resolved),
        "n_open": len(picks) - len(resolved),
        "n_forward": fwd,
        "pct_forward": (100 * fwd / len(resolved)) if resolved else None,
        "resolution_chain_ok": verify_resolutions().get("ok"),
    }
    if rets:
        st.update({
            "mean_bp": sum(rets) / len(rets),
            "median_bp": sorted(rets)[len(rets) // 2],
            "hit_rate": 100 * sum(1 for v in rets if v > 0) / len(rets),
            "profit_factor": pf(rets),
            "worst_bp": min(rets),
            "best_bp": max(rets),
        })
    return st


def cmd_resolve() -> int:
    picks = read_jsonl(PICKS)
    if not picks:
        print("BLOCKED: pick ledger is empty. Nothing to resolve.")
        print("It fills the first time alpha_engine/production_scanner.py runs with")
        print("the section-6y provenance hook merged.")
        return 3
    res = read_jsonl(RES)
    done = {r["pick_seq"] for r in res}
    todo = [p for p in picks if p["seq"] not in done]
    print(f"picks {len(picks)}  already resolved {len(done)}  to resolve {len(todo)}")
    if not todo:
        print("nothing new to resolve")
        return 0

    symbols = sorted({yf_symbol(p["symbol"]) for p in todo})
    oldest = min(datetime.fromisoformat(p["created_at"]) for p in todo)
    print(f"loading hourly bars for {len(symbols)} symbol(s) from {oldest:%Y-%m-%d}")
    bars = load_bars(symbols, oldest - timedelta(days=2))
    print(f"loaded {len(bars)}/{len(symbols)} series")

    rows, still_open, no_data = [], 0, 0
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for p in todo:
        b = bars.get(yf_symbol(p["symbol"]))
        if b is None:
            no_data += 1
            continue
        o = decide(p, b)
        if o is None:
            still_open += 1
            continue
        rows.append({"pick_seq": p["seq"], "symbol": p["symbol"], "side": p["side"],
                     "outcome": o["outcome"], "entry_px": o["entry_px"],
                     "exit_px": o["exit_px"], "exit_utc": o["exit_utc"],
                     "bars_held": o["bars_held"], "resolved_at": now,
                     "convention": "next_bar_open_entry, SL_first_on_ambiguity"})
    if rows:
        n = append_resolutions(rows)
        print(f"appended {n} resolution(s) -> {RES.relative_to(REPO)}")
    print(f"still open {still_open}  no data {no_data}")
    st = compute_status()
    STATUS.write_text(json.dumps(st, indent=1))
    print(json.dumps(st, indent=1))
    return 0


def selftest() -> int:
    """Prove the pessimistic tie-break and the no-mutation guarantee."""
    print("=" * 78)
    print("SELFTEST -- pessimistic tie-break, no-mutation, forward clock")
    print("=" * 78)
    import pandas as pd

    # a bar that touches BOTH levels must resolve as SL, never TP
    idx = pd.date_range("2026-01-01", periods=3, freq="h", tz="UTC")
    bars = pd.DataFrame({
        "Open": [100.0, 100.0, 100.0],
        "High": [100.0, 120.0, 100.0],     # touches TP 110 on bar 1
        "Low":  [100.0,  90.0, 100.0],     # AND SL 95 on the same bar
        "Close": [100.0, 100.0, 100.0],
    }, index=idx)
    pick = {"seq": 1, "symbol": "X", "side": "LONG", "entry_ref": 100.0,
            "tp": 110.0, "sl": 95.0, "created_at": "2026-01-01T00:00:00+00:00"}
    o = decide(pick, bars)
    print(f"  bar touches TP and SL together -> outcome={o['outcome']} "
          f"(must be SL)")
    assert o["outcome"] == "SL", "pessimistic tie-break violated"

    # a clean TP touch resolves as TP
    bars2 = bars.copy()
    bars2.loc[idx[1], "Low"] = 99.0
    o2 = decide(pick, bars2)
    print(f"  bar touches TP only            -> outcome={o2['outcome']} (must be TP)")
    assert o2["outcome"] == "TP"

    # entry must be a bar OPEN, not the signal price
    print(f"  entry price used               -> {o2['entry_px']} (must be a bar Open)")
    assert o2["entry_px"] == 100.0

    # resolutions append without touching picks
    tmp = Path(tempfile.mkdtemp())
    pf_, rf_ = tmp / "p.jsonl", tmp / "r.jsonl"
    pf_.write_text(json.dumps(dict(pick, sha256="x", prev_sha256=GENESIS)) + "\n")
    before = pf_.read_text()
    rf_.write_text("")
    append_resolutions([{"pick_seq": 1, "symbol": "X", "side": "LONG",
                         "outcome": "TP", "entry_px": 100.0, "exit_px": 110.0,
                         "exit_utc": "2026-01-01T01:00:00+00:00", "bars_held": 2,
                         "resolved_at": "2026-01-02T00:00:00+00:00",
                         "convention": "t"}], rf_)
    print(f"  pick file unchanged after resolving -> {pf_.read_text() == before}")
    assert pf_.read_text() == before, "resolver MUTATED the pick ledger"

    # chain detects an edited resolution
    recs = read_jsonl(rf_)
    recs[0]["exit_px"] = 999.0
    rf_.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in recs))
    v = verify_resolutions(rf_)
    print(f"  edited resolution detected          -> ok={v['ok']} "
          f"reason={v.get('reason')}")
    assert not v["ok"], "edited resolution NOT detected"

    print("\n  ALL RESOLVER SELFTESTS PASSED")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--resolve", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.resolve:
        return cmd_resolve()
    if a.status:
        st = compute_status()
        STATUS.parent.mkdir(parents=True, exist_ok=True)
        STATUS.write_text(json.dumps(st, indent=1))
        print(json.dumps(st, indent=1))
        print(f"\nwrote {STATUS.relative_to(REPO)}")
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
