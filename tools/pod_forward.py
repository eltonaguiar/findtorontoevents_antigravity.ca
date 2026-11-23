"""Forward observation recorder for the H-201 pod — the 77-day clock.

`pod_status.py` reports GATE STATE and never advances `n_days`, because nothing in the repo
recorded forward observations. The pod spec answers "how many days?" and "what kills it?" but
the journal stayed at `n_days=0` forever, which means the pod could be run daily until the
heat death of the universe and still never produce a verdict. This tool closes that gap.

What it does, and what it deliberately will not do:

  * Records REAL forward observations only — prices that exist, from the session after the
    signal close, filled at the next open, per the spec's execution block. It never invents a
    row for a day that did not trade.
  * Rebuilds the path deterministically from an anchor month-end, so re-running it is
    idempotent and the rows are reproducible rather than stateful.
  * Applies the spec's KILL rule symmetrically and its SUCCESS rule asymmetrically, because
    the survivorship bias established in item 16 moves in one direction: a contaminated
    universe can inflate a pass, so a pass is not admissible evidence. A KILL is.

Consequence, stated up front: the pod spec requires a point-in-time universe of at least 22
names. The harness fallback (`UNIVERSES["EQUITY"]`) is 10 mega-caps, which the spec bars outright,
so this tool now reads the audited point-in-time artifact at
`reports/pit_equity_universe_20261122.json` (44 names, 61 monthly rebalance dates, no date below
the 22-name floor).

That artifact is NOT delisting-aware -- its own status is PARTIAL_NON_DELISTING_AWARE with the
residual bias pointing UPWARD. It clears the count bar but cannot launder the survivorship
problem, so a universe drawn from it caps the verdict at CANDIDATE_SURVIVORSHIP_FLAGGED. A clean
PASS needs a delisting-aware source (CRSP/Norgate/Polygon), which this repo does not have.

Because the universe is chosen at the anchor, switching it mid-clock would silently change the
basket under an unchanged `n_days` -- the same class of defect as a status that ignores its own
stats. The clock therefore refuses a differing universe unless `--switch-universe` is passed,
which archives the running rows and restarts the anchor so the change is visible in history.

Usage
  python3 tools/pod_forward.py --dry-run     # compute rows, print, write nothing
  python3 tools/pod_forward.py               # append new forward rows
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from per_class_edge_harness import (  # noqa: E402
    UNIVERSES, block_bootstrap, fetch, matched_vol_block,
)

POD_DIR = ROOT / "reports" / "pods"
FWD_DIR = POD_DIR / "forward"
POD_ID = "POD-EQUITY-H201-XSMOM-6M"
PIT_ARTIFACT = ROOT / "reports" / "pit_equity_universe_20261122.json"
LOOKBACK = 126
TOP_K = 3
SLIP_BP = 10.0
COMM_BP = 1.0
COST_PER_SIDE_BP = SLIP_BP + COMM_BP


def load_spec(pod_id: str = POD_ID) -> dict:
    for p in sorted(POD_DIR.glob("pod_*.json")):
        spec = json.loads(p.read_text())
        if spec.get("pod_id") == pod_id:
            return spec
    raise SystemExit(f"pod spec not found for {pod_id}")


def read_universe(path: str | Path | None = PIT_ARTIFACT) -> tuple[list[str], dict]:
    """Names from the audited PIT artifact, else the harness list, plus what that universe is."""
    p = Path(path) if path else None
    if p and p.exists():
        a = json.loads(p.read_text())
        names = [str(s) for s in (a.get("universe") or [])]
        if names and a.get("passes_count_bar"):
            surv = a.get("survivorship") or {}
            guide = a.get("verdict_guidance") or {}
            return names, {
                "source": f"PIT_ARTIFACT:{p.name}",
                "survivorship_status": surv.get("status"),
                "survivorship_direction": surv.get("direction_of_residual_bias"),
                "label": guide.get("recommended_label"),
                "n_names": len(names),
            }
    return list(UNIVERSES["EQUITY"]), {
        "source": "HARNESS_FALLBACK_UNIVERSES_EQUITY",
        "survivorship_status": None,
        "survivorship_direction": None,
        "label": None,
        "n_names": len(UNIVERSES["EQUITY"]),
    }


def load_closes(names: list[str]) -> pd.DataFrame:
    data = {s: fetch(s) for s in names}
    data = {s: d for s, d in data.items() if d is not None and len(d) > 200}
    if not data:
        raise SystemExit("no price history available for the selected universe")
    return pd.concat({s: d["close"] for s, d in data.items()}, axis=1).dropna(how="all")


def load_opens(names: list[str]) -> pd.DataFrame:
    data = {s: fetch(s) for s in names}
    data = {s: d for s, d in data.items() if d is not None and "open" in d.columns}
    if not data:
        raise SystemExit("no open prices available for the selected universe")
    return pd.concat({s: d["open"] for s, d in data.items()}, axis=1).dropna(how="all")


def completed_month_end(idx: pd.DatetimeIndex, as_of: pd.Timestamp) -> pd.Timestamp:
    """Last session of a COMPLETED month at or before `as_of` (signal close, not entry)."""
    first_of_current = as_of.normalize().replace(day=1)
    prior = idx[idx < first_of_current]
    if len(prior) == 0:
        raise SystemExit("no completed month in the price history")
    return prior[-1]


def basket_on(closes: pd.DataFrame, date: pd.Timestamp, lookback: int = LOOKBACK,
              top_k: int = TOP_K) -> list[str]:
    """Top-k 6-month total return as of `date`'s close — data available at that close only."""
    mom = closes.pct_change(lookback, fill_method=None).loc[date].dropna()
    if len(mom) < top_k:
        raise SystemExit(f"universe too thin on {date.date()} ({len(mom)} names)")
    return list(mom.nlargest(top_k).index)


def build_path(closes: pd.DataFrame, opens: pd.DataFrame, anchor: pd.Timestamp,
               spec: dict) -> tuple[pd.DataFrame, list[dict]]:
    """Deterministic forward path from `anchor` (the first recorded signal month-end)."""
    idx = closes.index
    rebal_signal_dates = [d for d in idx if d >= anchor and
                          (d.month != idx[idx.get_loc(d) - 1].month if idx.get_loc(d) > 0 else False)]
    if anchor not in rebal_signal_dates:
        rebal_signal_dates = [anchor] + rebal_signal_dates

    holdings: dict[str, float] = {}
    entry_px: dict[str, float] = {}
    trades = 0
    rows, events = [], []
    pending: list[str] | None = basket_on(closes, anchor)
    events.append({"type": "signal", "date": str(anchor.date()), "basket": pending})

    rf = fetch("^IRX")
    rf_daily = ((rf["close"] / 100.0) / 252.0).reindex(idx).ffill().fillna(0.0) if rf is not None \
        else pd.Series(0.0, index=idx)

    for d in idx[idx > anchor]:
        # fill at today's open whatever was signalled at a prior close
        if pending is not None:
            # charge the entry side ONCE per name, from the basket being bought. The first
            # version summed over `holdings`, which is empty at the first entry, so the very
            # first trade was booked at zero cost -- the one cost that is certain.
            cost = COST_PER_SIDE_BP * len(pending)
            holdings, entry_px = {}, {}
            for n in pending:
                if n in opens.columns and pd.notna(opens.loc[d].get(n)):
                    entry_px[n] = float(opens.loc[d][n])
                    holdings[n] = 1.0
            if not holdings:
                continue
            trades += len(holdings)
            rows.append({"date": str(d.date()),
                         "port_ret": -cost / 1e4 / len(holdings),
                         "event": "entry", "basket": list(holdings)})
            events.append({"type": "entry", "date": str(d.date()), "basket": list(holdings),
                           "trade_size": len(holdings), "cost_bps_per_name": cost})
            pending = None
            prev_close = {n: entry_px[n] for n in holdings}
            continue

        # mark to market from the previous close (entry day: from the entry price)
        rets = {}
        for n in holdings:
            px = closes.loc[d].get(n) if n in closes.columns else np.nan
            if pd.notna(px):
                rets[n] = float(px) / prev_close[n] - 1.0
                prev_close[n] = float(px)
            else:
                rets[n] = 0.0     # delisted/halted: marked at last trade, NOT refilled
        port = float(np.mean(list(rets.values()))) if rets else 0.0
        rows.append({"date": str(d.date()), "port_ret": port, "event": "mark"})

        if d in rebal_signal_dates:
            pending = basket_on(closes, d)
            events.append({"type": "signal", "date": str(d.date()), "basket": pending})

    df = pd.DataFrame(rows)
    if len(df):
        df["rf"] = rf_daily.reindex(pd.to_datetime(df["date"])).to_numpy()
        df["excess"] = df["port_ret"] - df["rf"]
        df["n_days"] = np.arange(1, len(df) + 1)
        df["n_trades"] = trades
    return df, events


def summarise(df: pd.DataFrame, spec: dict, closes: pd.DataFrame,
              n_names: int, uni_meta: dict | None = None) -> dict:
    uni_meta = uni_meta or {}
    minimum = spec.get("universe", {}).get("minimum_names", 22)
    universe_ok = bool(n_names >= minimum)
    # Count bar cleared, but the universe is still survivorship-flagged -> cap the good verdict.
    flagged = bool(universe_ok and uni_meta.get("survivorship_status") not in (None, "PASS"))
    uni_fields = {
        "universe_names": int(n_names),
        "universe_minimum_required": minimum,
        "universe_ok": universe_ok,
        "universe_source": uni_meta.get("source"),
        "universe_survivorship_status": uni_meta.get("survivorship_status"),
        "universe_survivorship_direction": uni_meta.get("survivorship_direction"),
        "universe_label": uni_meta.get("label"),
        "universe_block": None if universe_ok else "universe_below_minimum_names",
    }
    n = int(len(df))
    if n < 30:
        # A bootstrap CI on 15 days is a number with no content, and vol-matching on it is
        # worse. Report the running sum and say plainly that inference has not started.
        return {"n_days": n, "n_trades": int(df["n_trades"].iloc[-1]) if n else 0,
                "cum_excess_bps": round(float(df["excess"].sum() * 1e4), 3) if n else 0.0,
                "ci_lb_raw_bps": None, "ci_lb_volmatched_bps": None,
                **uni_fields,
                "universe_note": uni_meta.get("label") if flagged else None,
                "verdict": "NO_VERDICT_TOO_FEW_DAYS_FOR_INFERENCE"}
    x = df["excess"].to_numpy(dtype=float)
    lo, _hi = block_bootstrap(x)
    lo = float(lo)
    bench = ((fetch("SPY")["close"].pct_change()).reindex(
        pd.to_datetime(df["date"])).fillna(0.0).to_numpy())
    mvb = matched_vol_block(x, bench)
    gate = spec.get("size_gate", {})
    kill = spec.get("kill_rule", {})
    min_days = gate.get("no_verdict_before_n_days", 20)
    min_trades = gate.get("no_verdict_before_n_trades", 10)
    n_days, n_trades = int(len(df)), int(df["n_trades"].iloc[-1])

    verdict = "GATED"
    if n_days >= kill.get("trigger_day", 40) and lo <= 0:
        # A KILL is admissible even on a contaminated universe: survivorship inflates
        # returns, so failing to clear zero DESPITE the inflation is the real result.
        verdict = "REFUTED"
    elif n_days >= min_days and n_trades >= min_trades:
        if lo > 0 and mvb["matched_ci_lb_bps"] > 0:
            if not universe_ok:
                verdict = "UNSAFE_CANDIDATE"
            elif flagged:
                # Cleared the count bar; still not delisting-aware. Name the caveat in the
                # verdict instead of letting a clean-sounding label imply a clean universe.
                verdict = "CANDIDATE_SURVIVORSHIP_FLAGGED"
            else:
                verdict = "CANDIDATE_NEEDS_SECOND_UNIVERSE"
        else:
            verdict = "PENDING" if n_days < 77 else "NOT_PROVEN"
    return {
        "n_days": n_days, "n_trades": n_trades,
        "cum_excess_bps": round(float(np.sum(x) * 1e4), 3),
        "mean_excess_bps": round(1e4 * float(np.mean(x)), 3),
        "ci_lb_raw_bps": round(1e4 * lo, 3),
        "ci_lb_volmatched_bps": mvb["matched_ci_lb_bps"],
        "vol_matched_excess_bps": mvb["matched_excess_bps"],
        **uni_fields,
        "universe_note": uni_meta.get("label") if flagged else None,
        "verdict": verdict,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--anchor", default=None, help="YYYY-MM-DD signal month-end to anchor on")
    ap.add_argument("--universe", default=str(PIT_ARTIFACT),
                    help="point-in-time universe artifact (default: the audited PIT artifact)")
    ap.add_argument("--switch-universe", action="store_true",
                    help="archive the running clock and restart the anchor on a different universe")
    args = ap.parse_args()

    spec = load_spec()
    names, uni_meta = read_universe(args.universe)
    FWD_DIR.mkdir(parents=True, exist_ok=True)
    anchor_file = FWD_DIR / f"{POD_ID}_anchor.json"
    out_rows = FWD_DIR / f"{POD_ID}.jsonl"

    # A clock is a clock: its universe is fixed at the anchor. Swapping the basket while
    # keeping n_days would leave the running total describing two different portfolios.
    prior = json.loads(anchor_file.read_text()) if anchor_file.exists() else None
    if prior and prior.get("universe") and set(prior["universe"]) != set(names):
        if not args.switch_universe:
            raise SystemExit(
                f"REFUSING to change the clock's universe mid-run.\n"
                f"  pinned at anchor : {len(prior['universe'])} names "
                f"(set {prior.get('set_at', '?')})\n"
                f"  requested now    : {len(names)} names from {uni_meta['source']}\n"
                "Re-run with --switch-universe to archive the existing rows and restart the "
                "anchor on the new universe, or point --universe at the pinned set.")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        arch = FWD_DIR / f"archive_pre_switch_{stamp}"
        arch.mkdir(parents=True, exist_ok=True)
        for pth in (out_rows, anchor_file):
            if pth.exists():
                pth.rename(arch / pth.name)
        (arch / "switch.json").write_text(json.dumps({
            "switched_utc": stamp,
            "from_universe": prior["universe"],
            "from_anchor": prior.get("anchor"),
            "to_source": uni_meta["source"],
            "to_n_names": len(names),
            "to_survivorship_status": uni_meta.get("survivorship_status"),
            "why": "prior universe was below the spec's 22-name floor, so it could never "
                    "produce a verdict; clock restarted on the audited PIT artifact",
        }, indent=1))
        prior = None
        print(f"archived prior clock to {arch}")

    closes, opens = load_closes(names), load_opens(names)
    if args.anchor:
        anchor = pd.Timestamp(args.anchor)
    elif prior:
        anchor = pd.Timestamp(prior["anchor"])
    else:
        anchor = completed_month_end(closes.index, closes.index[-1])

    df, events = build_path(closes, opens, anchor, spec)
    summary = summarise(df, spec, closes, len(closes.columns), uni_meta)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    existing = set()
    if out_rows.exists():
        for line in out_rows.read_text().splitlines():
            if line.strip():
                try:
                    existing.add(json.loads(line).get("date"))
                except json.JSONDecodeError:
                    pass

    new = []
    for _, r in df.iterrows():
        if r["date"] in existing:
            continue
        new.append({"ts": today, "pod_id": POD_ID, "date": r["date"],
                    "port_ret_bps": round(1e4 * float(r["port_ret"]), 3),
                    "rf_bps": round(1e4 * float(r["rf"]), 3),
                    "excess_bps": round(1e4 * float(r["excess"]), 3),
                    "n_days": int(r["n_days"]), "n_trades": int(r["n_trades"]),
                    "event": r["event"], "universe_ok": summary["universe_ok"]})

    if not args.dry_run:
        anchor_file.write_text(json.dumps({"anchor": str(anchor.date()),
                                           "set_at": today,
                                           "universe": sorted(closes.columns)}, indent=1))
        with out_rows.open("a") as fh:
            for r in new:
                fh.write(json.dumps(r) + "\n")

    print(f"{POD_ID}  anchor signal {anchor.date()}  sessions recorded {len(df)}  "
          f"new {0 if args.dry_run else len(new)}")
    print(json.dumps({**summary, "events": events}, indent=1))
    if summary.get("universe_block"):
        print("\nVERDICT BARRED: the spec requires a point-in-time universe of at least "
              f"{summary['universe_minimum_required']} names; this run has "
              f"{summary['universe_names']}. A pass cannot be issued on a "
              "survivorship-contaminated universe. A KILL still can.")
    elif summary.get("universe_note"):
        print(f"\nUNIVERSE CAVEAT ({summary['universe_survivorship_status']}): a pass from this "
              "run is capped at CANDIDATE_SURVIVORSHIP_FLAGGED -- the count bar is met but the "
              "universe is not delisting-aware.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
