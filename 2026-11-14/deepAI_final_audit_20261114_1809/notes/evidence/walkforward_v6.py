"""Walk-forward proof for PROFITABLE_APPROACH_v1.md (variant C).

Run from the repo root (or any dir containing the payload):
  python walkforward_v6.py dashboard_payload.json

Procedure (pre-specified, selection sees ONLY prior months):
  each month M: group training trades by strategy (>=20 trades),
  rank by PF, take top-6 with PF>1.3, evaluate on month M.
Null: same structure but 6 randomly drawn candidate strategies/month.
Outputs: monthly table, aggregate n/WR/PF/sum, randomization p (800 draws).
"""
import json, sys, math, random
from collections import defaultdict


def pf(v):
    gp = sum(x for x in v if x > 0)
    gl = abs(sum(x for x in v if x < 0))
    return gp / gl if gl else (float('inf') if gp > 0 else 0.0)


def main(path):
    d = json.load(open(path, encoding='utf-8'))
    rows = [p for p in d['picks']['recent_closed'] if isinstance(p.get('pnl_pct'), (int, float))]

    def cdate(p):
        return str(p.get('closed_at') or p.get('exit_date') or '9999')[:10]

    months = sorted({cdate(p)[:7] for p in rows})

    def forward(pick_fn):
        fwd = []
        for m in months:
            if m <= '2026-03':
                continue
            train = [p for p in rows if cdate(p)[:7] < m]
            test = [p for p in rows if cdate(p)[:7] == m]
            if len(train) < 150 or len(test) < 5:
                continue
            agg = defaultdict(list)
            for p in train:
                agg[str(p.get('strategy'))].append(p['pnl_pct'])
            picks = pick_fn(agg)
            fwd += [p for p in test if str(p.get('strategy')) in picks]
        return fwd

    def variant_c(agg):
        rank = sorted([(k, v) for k, v in agg.items() if len(v) >= 20],
                      key=lambda kv: -pf(kv[1]))
        return [k for k, v in rank[:6] if pf(v) > 1.3]

    fwd = forward(variant_c)
    v = [p['pnl_pct'] for p in fwd]
    w = sum(1 for x in v if x > 0)
    n = len(v)
    z = (w / n - 0.5) / math.sqrt(0.25 / n)
    print(f"VARIANT C walk-forward: n={n} WR={100*w/n:.1f}% PF={pf(v):.2f} "
          f"sum={sum(v):+.1f}pp z={z:+.2f}")

    random.seed(31)
    ge = tr = 0
    obs = pf(v)
    for _ in range(800):
        def random_pick(agg, _s=random):
            cands = [k for k, x in agg.items() if len(x) >= 20]
            if len(cands) < 6:
                return []
            return _s.sample(cands, 6)
        rf = [p['pnl_pct'] for p in forward(random_pick)]
        if len(rf) >= 30:
            tr += 1
            if pf(rf) >= obs:
                ge += 1
    print(f"randomization null: {ge}/{tr} = p={ge/tr:.4f}")


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'dashboard_payload.json')
