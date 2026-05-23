"""verify_ctf_cot_pf.py — A5 COMMODITY PF verification.

Throwaway read-only analysis: recompute multi_asset_cot / CT=F PF+WR raw vs deduped.
De-dup rule: picks sharing (symbol, direction, entry_date, entry_price rounded to 2dp)
are COT re-emissions of the same signal; keep one.
"""
import json
from collections import defaultdict


def load_picks():
    picks = []
    for path in ("alpha_engine/data/closed_picks.json",
                 "alpha_engine/data/closed_picks_fast.json"):
        try:
            d = json.load(open(path))
        except FileNotFoundError:
            continue
        rows = d if isinstance(d, list) else d.get("picks", d.get("closed", []))
        for r in rows:
            r["_src_file"] = path
        picks.extend(rows)
    return picks


def is_ctf_cot(p):
    sysname = (p.get("source_system") or "") .lower()
    sym = (p.get("symbol") or "")
    return sysname == "multi_asset_cot" and "CT=F" in sym


def pf_wr(rows):
    gp = gl = 0.0
    wins = losses = flat = 0
    for r in rows:
        pnl = r.get("pnl_pct")
        if pnl is None:
            continue
        pnl = float(pnl)
        # normalize: some rows store fraction (-0.0327), some percent
        if abs(pnl) < 1.5:  # treat as fraction -> percent
            pnl *= 100.0
        if pnl > 0:
            gp += pnl
            wins += 1
        elif pnl < 0:
            gl += -pnl
            losses += 1
        else:
            flat += 1
    n = wins + losses + flat
    pf = (gp / gl) if gl > 0 else float("inf")
    wr = (wins / (wins + losses) * 100.0) if (wins + losses) else 0.0
    return dict(n=n, wins=wins, losses=losses, flat=flat,
                gross_profit=round(gp, 2), gross_loss=round(gl, 2),
                pf=round(pf, 2) if gl > 0 else None, wr=round(wr, 1))


def dedup(rows):
    seen = {}
    for r in rows:
        ep = r.get("entry_price")
        try:
            epk = round(float(ep), 2)
        except (TypeError, ValueError):
            epk = ep
        key = (r.get("symbol"), r.get("direction") or r.get("signal_type"),
               r.get("entry_date"), epk)
        # prefer a row that has a non-null pnl_pct
        if key not in seen:
            seen[key] = r
        else:
            if seen[key].get("pnl_pct") is None and r.get("pnl_pct") is not None:
                seen[key] = r
    return list(seen.values())


def main():
    picks = load_picks()
    ctf = [p for p in picks if is_ctf_cot(p)]
    print(f"# total closed picks loaded: {len(picks)}")
    print(f"# multi_asset_cot CT=F picks (raw): {len(ctf)}")

    raw = pf_wr(ctf)
    deduped_rows = dedup(ctf)
    ded = pf_wr(deduped_rows)

    print("\n## RAW")
    print(json.dumps(raw, indent=1))
    print("\n## DEDUPED")
    print(f"# deduped count: {len(deduped_rows)}  (removed {len(ctf)-len(deduped_rows)})")
    print(json.dumps(ded, indent=1))

    # duplicate key histogram
    groups = defaultdict(list)
    for r in ctf:
        ep = r.get("entry_price")
        try:
            epk = round(float(ep), 2)
        except (TypeError, ValueError):
            epk = ep
        key = (r.get("symbol"), r.get("direction") or r.get("signal_type"),
               r.get("entry_date"), epk)
        groups[key].append(r)
    dup_groups = {k: len(v) for k, v in groups.items() if len(v) > 1}
    print(f"\n# duplicate groups (>1 emission): {len(dup_groups)}")
    for k, c in sorted(dup_groups.items(), key=lambda x: -x[1])[:10]:
        print(f"   {k} -> {c} copies")

    # pnl_pct scale sanity
    sample = [p.get("pnl_pct") for p in ctf if p.get("pnl_pct") is not None][:8]
    print(f"\n# sample raw pnl_pct values: {sample}")


if __name__ == "__main__":
    main()
