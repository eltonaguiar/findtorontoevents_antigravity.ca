"""Deep Asset Class Edge Analysis — run from project root."""
import json, sys, os, statistics
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from audit_trail.asset_classification import classify_asset


def compute_wr(picks):
    valid = [p for p in picks if p.get("_pnl") is not None]
    if not valid:
        return {"n": 0, "wr": None, "avg_pnl": None, "pf": None, "cum_pnl": None}
    wins = [p for p in valid if p["_pnl"] > 0]
    losses = [p for p in valid if p["_pnl"] <= 0]
    total = sum(p["_pnl"] for p in valid)
    gw = sum(p["_pnl"] for p in wins) if wins else 0
    gl = abs(sum(p["_pnl"] for p in losses)) if losses else 0.0001
    wr = len(wins) / len(valid) * 100 if valid else 0
    pf = gw / gl if gl > 0 else 999
    return {
        "n": len(valid),
        "wr": round(wr, 1),
        "avg_pnl": round(total / len(valid), 4),
        "pf": round(pf, 2),
        "cum_pnl": round(total, 2),
    }


def main():
    # ── Load ALL pick data ──────────────────────────────────────────────
    all_picks = []
    seen_ids = set()
    data_files = [
        "alpha_engine/data/closed_picks.json",
        "audit_trail/data/universal_resolved_picks.json",
        "multi_asset/data/multi_asset_closed.json",
        "multi_asset/data/institutional_closed.json",
        "battleground/data/closed_picks.json",
    ]

    for fp in data_files:
        if not os.path.exists(fp):
            continue
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            continue
        for p in data:
            pid = p.get("id", "")
            if pid and pid in seen_ids:
                continue
            if pid:
                seen_ids.add(pid)
            # Classify
            sym = p.get("symbol", "")
            raw_ac = str(p.get("asset_class", "") or "").upper()
            if raw_ac and raw_ac not in ("", "UNKNOWN", "NONE"):
                p["_ac"] = raw_ac
            else:
                p["_ac"] = classify_asset(sym).value
            # PnL
            pnl = p.get("pnl_pct")
            if pnl is None:
                pnl = p.get("realized_pnl_pct")
            try:
                p["_pnl"] = float(pnl) if pnl is not None else None
            except (TypeError, ValueError):
                p["_pnl"] = None
            # Confidence
            conf = p.get("confidence")
            try:
                p["_conf"] = float(conf) if conf is not None else None
            except (TypeError, ValueError):
                p["_conf"] = None
            # Score
            score = p.get("score") or p.get("elite_score") or p.get("ml_composite_score")
            try:
                p["_score"] = float(score) if score is not None else None
            except (TypeError, ValueError):
                p["_score"] = None
            # Sort timestamp
            ts = (
                p.get("closed_at")
                or p.get("resolved_at")
                or p.get("exit_time")
                or p.get("created_at")
                or p.get("timestamp")
                or ""
            )
            p["_ts"] = str(ts)
            p["_strategy"] = p.get("strategy", "unknown")
            p["_direction"] = str(p.get("direction", "")).upper()
            p["_exit_reason"] = str(p.get("exit_reason", "")).upper()
            all_picks.append(p)

    all_picks.sort(key=lambda p: p["_ts"], reverse=True)
    print(f"Total unique picks loaded: {len(all_picks)}")

    # Asset class counts
    ac_counts = defaultdict(int)
    for p in all_picks:
        ac_counts[p["_ac"]] += 1
    print("\n=== Re-Classified Asset Class Distribution ===")
    for ac, cnt in sorted(ac_counts.items(), key=lambda x: -x[1]):
        print(f"  {ac}: {cnt}")

    # ── SECTION 1: Win rates by asset class at different windows ────────
    print("\n" + "=" * 80)
    print("SECTION 1: WIN RATE BY ASSET CLASS AT DIFFERENT WINDOWS")
    print("=" * 80)

    TARGET = ["CRYPTO", "EQUITY", "FOREX", "COMMODITY", "BOND", "ETF", "FUTURES", "MEME"]
    WINDOWS = [20, 100, 200, None]

    for window in WINDOWS:
        w_label = f"last_{window}" if window else "ALL"
        print(f"\n--- Window: {w_label} ---")
        for ac in TARGET:
            ac_picks = [p for p in all_picks if p["_ac"] == ac]
            if window:
                ac_picks = ac_picks[:window]
            stats = compute_wr(ac_picks)
            if stats["n"] > 0:
                n = stats["n"]
                wr = stats["wr"]
                ap = stats["avg_pnl"]
                pf = stats["pf"]
                cp = stats["cum_pnl"]
                print(f"  {ac:12s}: n={n:4d}  WR={wr:5.1f}%  AvgPnL={ap:+.4f}%  PF={pf:.2f}  CumPnL={cp:+.2f}%")
            else:
                count = len([p for p in all_picks if p["_ac"] == ac])
                print(f"  {ac:12s}: NO PnL DATA (total picks: {count})")

    # ── SECTION 2: Verify claimed numbers ───────────────────────────────
    print("\n" + "=" * 80)
    print("SECTION 2: VERIFICATION OF CLAIMED WIN RATES (last 20 per class)")
    print("=" * 80)

    claimed = {"EQUITY": 65.0, "FOREX": 5.0, "COMMODITY": 15.0, "BOND": 47.1, "ETF": 85.0}
    for ac, cwr in claimed.items():
        ac_picks = [p for p in all_picks if p["_ac"] == ac][:20]
        stats = compute_wr(ac_picks)
        if stats["n"] == 0:
            total_count = len([p for p in all_picks if p["_ac"] == ac])
            print(f"  {ac:12s}: NO PnL DATA (total picks: {total_count})")
        else:
            match = "MATCH" if abs(stats["wr"] - cwr) < 5 else "MISMATCH"
            print(f"  {ac:12s}: Claimed={cwr:5.1f}%  Actual={stats['wr']:5.1f}%  {match}  (n={stats['n']})")

    # ── SECTION 3: Edge by strategy per asset class ────────────────────
    print("\n" + "=" * 80)
    print("SECTION 3: EDGE BY STRATEGY (min 3 picks with PnL)")
    print("=" * 80)

    for ac in TARGET:
        ac_picks = [p for p in all_picks if p["_ac"] == ac and p["_pnl"] is not None]
        if not ac_picks:
            continue
        strat_map = defaultdict(list)
        for p in ac_picks:
            strat_map[p["_strategy"]].append(p)
        print(f"\n  === {ac} (n={len(ac_picks)}) ===")
        strat_stats = []
        for strat, picks in strat_map.items():
            stats = compute_wr(picks)
            if stats["n"] >= 3:
                strat_stats.append((strat, stats))
        strat_stats.sort(key=lambda x: x[1]["cum_pnl"], reverse=True)
        for strat, stats in strat_stats[:5]:
            print(f"    + {strat:35s}: n={stats['n']:4d}  WR={stats['wr']:5.1f}%  PF={stats['pf']:.2f}  CumPnL={stats['cum_pnl']:+.2f}%")
        if len(strat_stats) > 5:
            print("    --- Worst ---")
            for strat, stats in strat_stats[-3:]:
                print(f"    - {strat:35s}: n={stats['n']:4d}  WR={stats['wr']:5.1f}%  PF={stats['pf']:.2f}  CumPnL={stats['cum_pnl']:+.2f}%")

    # ── SECTION 4: Filter-based edge ────────────────────────────────────
    print("\n" + "=" * 80)
    print("SECTION 4: FILTER-BASED EDGE")
    print("=" * 80)

    # 4a: Confidence tier (CRYPTO)
    print("\n  --- Confidence Tier (CRYPTO only) ---")
    crypto_conf = [p for p in all_picks if p["_ac"] == "CRYPTO" and p["_conf"] is not None and p["_pnl"] is not None]
    for label, lo, hi in [("0.00-0.55", 0, 0.55), ("0.55-0.65", 0.55, 0.65), ("0.65-0.75", 0.65, 0.75), ("0.75-0.85", 0.75, 0.85), ("0.85+", 0.85, 1.01)]:
        bp = [p for p in crypto_conf if lo <= p["_conf"] < hi]
        stats = compute_wr(bp)
        if stats["n"] > 0:
            print(f"    conf {label:10s}: n={stats['n']:4d}  WR={stats['wr']:5.1f}%  AvgPnL={stats['avg_pnl']:+.4f}%  PF={stats['pf']:.2f}")

    # 4b: Score tier (CRYPTO)
    print("\n  --- Score Tier (CRYPTO only) ---")
    crypto_score = [p for p in all_picks if p["_ac"] == "CRYPTO" and p["_score"] is not None and p["_pnl"] is not None]
    for label, lo, hi in [("0-40", 0, 40), ("40-55", 40, 55), ("55-70", 55, 70), ("70-85", 70, 85), ("85+", 85, 101)]:
        bp = [p for p in crypto_score if lo <= p["_score"] < hi]
        stats = compute_wr(bp)
        if stats["n"] > 0:
            print(f"    score {label:6s}: n={stats['n']:4d}  WR={stats['wr']:5.1f}%  AvgPnL={stats['avg_pnl']:+.4f}%  PF={stats['pf']:.2f}")

    # 4c: Exit reason
    print("\n  --- Exit Reason (ALL picks) ---")
    er_map = defaultdict(list)
    for p in all_picks:
        if p["_pnl"] is not None:
            er = p["_exit_reason"] or "NONE"
            er_map[er].append(p)
    for er in sorted(er_map.keys()):
        stats = compute_wr(er_map[er])
        if stats["n"] > 0:
            print(f"    {er:15s}: n={stats['n']:4d}  WR={stats['wr']:5.1f}%  AvgPnL={stats['avg_pnl']:+.4f}%  PF={stats['pf']:.2f}")

    # 4d: Direction
    print("\n  --- Direction (ALL picks) ---")
    dir_map = defaultdict(list)
    for p in all_picks:
        if p["_pnl"] is not None:
            dir_map[p["_direction"]].append(p)
    for d in sorted(dir_map.keys()):
        stats = compute_wr(dir_map[d])
        if stats["n"] > 0:
            print(f"    {d:8s}: n={stats['n']:4d}  WR={stats['wr']:5.1f}%  AvgPnL={stats['avg_pnl']:+.4f}%  PF={stats['pf']:.2f}")

    # 4e: Combined edge filter
    print("\n  --- Combined Edge Filters ---")
    combos = [
        ("CRYPTO+score>=70+!deadzone", lambda p: p["_ac"]=="CRYPTO" and p["_score"] is not None and p["_score"]>=70 and p["_conf"] is not None and not (0.65<=p["_conf"]<0.75)),
        ("CRYPTO+score>=85", lambda p: p["_ac"]=="CRYPTO" and p["_score"] is not None and p["_score"]>=85),
        ("CRYPTO+conf>=0.75+score>=55", lambda p: p["_ac"]=="CRYPTO" and p["_conf"] is not None and p["_conf"]>=0.75 and p["_score"] is not None and p["_score"]>=55),
        ("CRYPTO+BUY+score>=70", lambda p: p["_ac"]=="CRYPTO" and p["_direction"]=="BUY" and p["_score"] is not None and p["_score"]>=70),
        ("CRYPTO+SHORT+score>=70", lambda p: p["_ac"]=="CRYPTO" and p["_direction"]=="SHORT" and p["_score"] is not None and p["_score"]>=70),
    ]
    for label, pred in combos:
        picks = [p for p in all_picks if p["_pnl"] is not None and pred(p)]
        stats = compute_wr(picks)
        if stats["n"] > 0:
            print(f"    {label:35s}: n={stats['n']:4d}  WR={stats['wr']:5.1f}%  PF={stats['pf']:.2f}  CumPnL={stats['cum_pnl']:+.2f}%")

    # ── SECTION 5: Non-crypto deep dive ─────────────────────────────────
    print("\n" + "=" * 80)
    print("SECTION 5: NON-CRYPTO DEEP DIVE")
    print("=" * 80)

    for ac in ["FOREX", "COMMODITY", "EQUITY", "ETF", "BOND"]:
        ac_picks = [p for p in all_picks if p["_ac"] == ac]
        if not ac_picks:
            print(f"\n  {ac}: NO DATA AT ALL")
            continue
        ac_pnl = [p for p in ac_picks if p["_pnl"] is not None]
        stats = compute_wr(ac_picks)
        print(f"\n  === {ac} (total={len(ac_picks)}, with PnL={stats['n']}) ===")
        if stats["n"] == 0:
            print("    NO PnL DATA — cannot compute win rate")
            continue
        print(f"    WR={stats['wr']}%  AvgPnL={stats['avg_pnl']}%  PF={stats['pf']}")
        if stats["n"] < 30:
            print("    *** SMALL SAMPLE — not statistically significant ***")

        # Symbol breakdown
        sym_map = defaultdict(list)
        for p in ac_pnl:
            sym_map[p.get("symbol", "?")].append(p)
        print(f"    Symbols ({len(sym_map)}):")
        for sym, picks in sorted(sym_map.items(), key=lambda x: -len(x[1]))[:8]:
            ss = compute_wr(picks)
            print(f"      {sym:15s}: n={ss['n']:3d}  WR={ss['wr']:5.1f}%  AvgPnL={ss['avg_pnl']:+.4f}%")

        # TP/SL analysis
        tp = sum(1 for p in ac_pnl if p["_exit_reason"] in ("TP", "TP_HIT"))
        sl = sum(1 for p in ac_pnl if p["_exit_reason"] in ("SL", "SL_HIT"))
        te = sum(1 for p in ac_pnl if "TIME" in p["_exit_reason"])
        print(f"    Exits: TP={tp} SL={sl} TIME={te}")

        # TP/SL distance
        tp_dists, sl_dists = [], []
        for p in ac_pnl:
            try:
                entry = float(p.get("entry_price", 0))
                tp_val = float(p.get("take_profit", 0))
                sl_val = float(p.get("stop_loss", 0))
                d = p["_direction"]
                if entry > 0 and tp_val > 0:
                    if d == "BUY":
                        tp_dists.append((tp_val - entry) / entry * 100)
                        sl_dists.append((entry - sl_val) / entry * 100)
                    else:
                        tp_dists.append((entry - tp_val) / entry * 100)
                        sl_dists.append((sl_val - entry) / entry * 100)
            except (TypeError, ValueError, ZeroDivisionError):
                pass
        if tp_dists and sl_dists:
            avg_tp = statistics.mean(tp_dists)
            avg_sl = statistics.mean(sl_dists)
            ratio = avg_tp / avg_sl if avg_sl > 0 else 0
            assessment = "TOO TIGHT" if ratio < 1.5 else "REASONABLE"
            print(f"    Avg TP dist: {avg_tp:.3f}%  Avg SL dist: {avg_sl:.3f}%  Ratio: {ratio:.2f} ({assessment})")

    # ── SECTION 6: CRYPTO extended windows ──────────────────────────────
    print("\n" + "=" * 80)
    print("SECTION 6: CRYPTO EDGE PERSISTENCE (does the edge hold at scale?)")
    print("=" * 80)

    crypto_all = [p for p in all_picks if p["_ac"] == "CRYPTO" and p["_pnl"] is not None]
    for window in [20, 50, 100, 200, 500, 1000, None]:
        subset = crypto_all[:window] if window else crypto_all
        stats = compute_wr(subset)
        w_label = f"last_{window}" if window else f"ALL({stats['n']})"
        print(f"  {w_label:12s}: n={stats['n']:4d}  WR={stats['wr']:5.1f}%  AvgPnL={stats['avg_pnl']:+.4f}%  PF={stats['pf']:.2f}  CumPnL={stats['cum_pnl']:+.2f}%")


if __name__ == "__main__":
    main()
