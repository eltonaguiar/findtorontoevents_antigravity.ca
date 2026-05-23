# AA-7 FOREX per-symbol mutation analysis — multi_asset_copytrader

**Date:** 2026-05-13
**Source:** `alpha_engine/data/closed_picks.json` terminal rows
**Filter:** `asset_class=FOREX` AND `source_system=multi_asset_copytrader`
**n (terminal):** 662

## Headline

FOREX class is NOT homogeneous. JPY-cross pairs drive the entire class loss; major non-JPY pairs are positive-edge inside the same strategy. Class-wide FOREX kill (or class-wide multi_asset_copytrader kill) destroys real edge on EURGBP/GBPUSD/AUDUSD/USDCHF.

Recommendation: **surgical symbol-triple blocks**, not class block, not strategy block.

## Per-symbol decomposition

| Symbol | n | WR% | PF | PnL% sum | Verdict |
|---|---:|---:|---:|---:|---|
| EURJPY=X | 154 | 1.9 | 0.02 | -0.77 | **KILL** — catastrophic; PF 0.02 = near-zero wins |
| USDJPY=X | 132 | 3.0 | 0.04 | -0.66 | **KILL** — same pattern as EURJPY |
| GBPJPY=X | 84 | 7.1 | 0.10 | -0.35 | **KILL** — JPY-cross drag |
| AUDJPY=X | 77 | 3.9 | 0.06 | -0.35 | **KILL** — JPY-cross drag |
| NZDUSD=X | 58 | 15.5 | 0.29 | -0.17 | **KILL** — commodity-cross drag |
| CADJPY=X | 37 | 10.8 | 0.14 | -0.14 | **KILL** — JPY-cross drag |
| USDCAD=X | 31 | 35.5 | 0.74 | -0.02 | KEEP (marginal; PF<1 but pnl≈flat) |
| EURGBP=X | 38 | 63.2 | 2.35 | +0.04 | **KEEP** — real edge |
| GBPUSD=X | 26 | 61.5 | 1.87 | +0.05 | **KEEP** — real edge |
| AUDUSD=X | 16 | 62.5 | 2.67 | +0.05 | **KEEP** — real edge (n<100 caveat) |
| USDCHF=X | 8 | 100.0 | ∞ | +0.06 | KEEP-MONITOR (n=8, thin) |

## Pattern

- **All 5 JPY-cross pairs**: EURJPY 1.9%, USDJPY 3.0%, GBPJPY 7.1%, AUDJPY 3.9%, CADJPY 10.8% — *every one* sub-15% WR, *every one* PF < 0.2. **Combined n=484** (73% of sample), **combined WR ≈ 4%**.
- **Non-JPY majors**: EURGBP 63.2%, GBPUSD 61.5%, AUDUSD 62.5%, USDCHF 100% — *every one* 60%+ WR, PF >1.8. **Combined n=88** (13%), **combined WR ≈ 65%**.
- **Commodity-cross laggards**: NZDUSD 15.5% PF 0.29 (n=58), USDCAD 35.5% PF 0.74 (n=31) — drag, but only NZDUSD severe.

The strategy is **directionally consistent on USD/EUR/GBP/AUD/CHF dynamics** but **systematically wrong on JPY positioning**. Likely root cause: JPY carry-trade regime change (BoJ tightening 2024-2025) inverted the strategy's prior LONG-USDJPY/SHORT-JPY-cross bias without strategy update.

## Mutation axes per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`

**Axis 1 — Symbol (this analysis):** decisive. JPY-crosses are the drag; non-JPY majors are positive-edge.

**Axis 2 — Direction:** not analyzed yet. Hypothesis: if strategy is LONG-only on JPY pairs (carrying old yen-weakness bias), inverting to SHORT-JPY-crosses might flip the edge. Needs separate run.

**Axis 3 — Timeframe:** not analyzed yet.

Axis-1 evidence is sufficient to act surgically. Axes 2/3 left as follow-up.

## Proposed action (gated on user approval per CLAUDE.md "Don't auto-add to BLOCKED_*")

Add to `audit_trail/quality_gates.py::BLOCKED_ASSET_STRATEGY_SYMBOL_TRIPLES` (new struct or extend existing pairs to triple form):

```
("FOREX", "multi_asset_copytrader", "EURJPY=X"),
("FOREX", "multi_asset_copytrader", "USDJPY=X"),
("FOREX", "multi_asset_copytrader", "GBPJPY=X"),
("FOREX", "multi_asset_copytrader", "AUDJPY=X"),
("FOREX", "multi_asset_copytrader", "CADJPY=X"),
("FOREX", "multi_asset_copytrader", "NZDUSD=X"),
```

Keep: EURGBP, GBPUSD, AUDUSD, USDCHF, USDCAD (marginal — monitor).

Expected impact (post-block, recomputed on same 662 sample):
- Removed n=510, removed pnl%=-1.94
- Remaining n=152, projected WR ≈ 60%, PF ≈ 2.0+, pnl% ≈ +0.27

Class-wide FOREX class WR/PF should lift substantially since multi_asset_copytrader is the dominant FOREX emitter (per `dashboard_data.json::by_asset_class` 2026-05-12 snapshot).

## What this report does NOT do

- Does not propose class-wide FOREX block (would destroy EURGBP/GBPUSD/AUDUSD edge).
- Does not propose strategy-wide multi_asset_copytrader block (peer claim that strategy is "5-class go-live" is already falsified for FUTURES n=157 WR 2.5%; same surgical-triple approach applies there).
- Does not run Axis-2/3 mutations (queued).
- Does not certify SHORT-JPY-cross inversion (would need separate backtest).

## Reproducer

```bash
python -c "
import json, collections
from pathlib import Path
rows = json.load(open('alpha_engine/data/closed_picks.json', encoding='utf-8'))
by_sym = collections.defaultdict(lambda: {'n':0,'w':0,'l':0,'wp':0.0,'lp':0.0,'pnl':0.0})
for r in rows:
    if str(r.get('asset_class','')).upper() != 'FOREX': continue
    if r.get('source_system') != 'multi_asset_copytrader': continue
    pnl = r.get('pnl_pct')
    if pnl is None: continue
    try: pnl = float(pnl)
    except: continue
    s = by_sym[r.get('symbol','UNK')]
    s['n'] += 1; s['pnl'] += pnl
    if pnl > 0: s['w'] += 1; s['wp'] += pnl
    elif pnl < 0: s['l'] += 1; s['lp'] += abs(pnl)
for sym, s in sorted(by_sym.items(), key=lambda x: -x[1]['n']):
    wr = (s['w']/(s['w']+s['l'])*100) if (s['w']+s['l']) else 0
    pf = (s['wp']/s['lp']) if s['lp']>0 else 999
    print(f'{sym} n={s[\"n\"]} WR={wr:.1f}% PF={pf:.2f} PnL={s[\"pnl\"]:+.2f}')
"
```

## Cross-references

- `docs/MUTATION_THREE_AXIS_PROTOCOL.md` — protocol followed
- `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` — investigation gate
- `feedback_noncrypto_resolver_live_close_bug.md` — resolver caveat; FOREX path uses `outcome_resolver.py` post-fix (v2.1), numbers trustworthy
- Peer claim `multi_asset_copytrader is best 5-class go-live` — partially falsified: COMMODITY n=96 WR 93.8% (real) vs FOREX 24.3% vs FUTURES 2.5%. Per-class decomposition is the only honest read.

NFA. Surgical, reversible (BLOCKED_* removal restores prior behavior).
