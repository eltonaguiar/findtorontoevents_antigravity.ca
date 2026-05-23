# Zombie-Kill Protocol — 2026-04-28

**Status:** kill applied (additive to `BLOCKED_SOURCE_SYSTEMS`).
**Branch:** `fix/kill-zombie-strategies-2026-04-28`.
**Goal alignment:** #1 (audit-page performance across asset classes).

Two source_systems are added to
`audit_trail/quality_gates.py::BLOCKED_SOURCE_SYSTEMS` (and synced to
`audit_dashboard/template.html::BLOCKED_SYSTEMS`) after running the
mandatory mutation three-axis autopsy from
`docs/MUTATION_THREE_AXIS_PROTOCOL.md` and
`docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`.

## Sources

### `copy_trader_highscore`

**Live aggregate** (`audit_dashboard/data/dashboard_data.json` `systems[]`):

| metric | value |
|--------|-------|
| resolved_picks | 234 |
| closed_picks | 373 |
| win_rate | 31.6% |
| avg_pnl_pct | -0.34% |
| total_pnl_pct | -78.41% |
| profit_factor | 0.74 |
| max_drawdown | 106.5% |
| last_signal_at | 2026-04-19 (dormant) |
| status | monitoring |

**Three-axis autopsy** (`audit_exports/closed_copy_trader_highscore.csv`,
n=283 from `audit_trail/data/universal_resolved_picks.json`):

```bash
python tools/mutation_analysis.py \
  --csv audit_exports/closed_copy_trader_highscore.csv \
  --min-trades 5 --dir-spread 5 --tf-spread 5 --sym-spread 10 \
  -o reports/mutation_analysis_copy_trader_highscore_2026_04_28.txt \
  --matrix-csv reports/mutation_matrix_copy_trader_highscore_2026_04_28.csv
```

| axis | finding | mutation save? |
|------|---------|----------------|
| direction | `hs_lb_None`: SHORT 32.4% WR on **n=253** vs LONG 80% on **n=5** | NO — LONG side n<30 statistical floor |
| symbol | 6 symbols at 100% WR (FETUSDT n=7; ZECUSDT, DASHUSDT, POPCATUSDT, AXSUSDT, KASUSDT all n=5) | NO — placeholder-stat artifact (5 identical +3.50% TP_HIT rows each, same pattern as `feedback_clone_hl_placeholder_stats.md`) |
| timeframe | no flips above 5pp threshold | NO |

**Per-strategy direction breakdown (n=283):**

```
strategy                       dir        n wins     WR   avg_pnl       sum
hs_lb_None                     SHORT    253   82  32.4%   -0.272%   -68.82%
hs_Auros_66M                   LONG      11    2  18.2%   -0.485%    -5.34%
hs_PensionFund_24M             LONG       9    4  44.4%   +1.043%    +9.39%
hs_lb_None                     LONG       5    4  80.0%   +2.200%   +11.00%
hs_ABC_41M                     LONG       2    0   0.0%   -1.000%    -2.00%
hs_whale_433roi                SHORT      2    0   0.0%   -0.905%    -1.81%
hs_whale_13M_new               SHORT      1    1 100.0%   +2.500%    +2.50%
```

No axis shows PF>1.2 with n>=30. Even unioning all LONG rows across all
`hs_*` strategies (27 trades total, 10 wins, 37% WR, sum +12.05%) the
sample is below the statistical floor and the WR is below break-even after
costs. **Verdict: kill.**

### `goldmine_stocks`

**Live aggregate:**

| metric | value |
|--------|-------|
| active_picks | 80 (still emitting) |
| closed_picks | 434 |
| resolved_picks | 24 |
| wins / losses | 3 / 21 |
| win_rate | 12.5% |
| avg_pnl_pct | -2.93% |
| total_pnl_pct | -70.37% |
| profit_factor | 0.03 |
| max_drawdown | 70.37% |
| last_signal_at | 2026-04-27 (active) |

**Three-axis autopsy** (`audit_exports/closed_goldmine_stocks.csv`,
n=24 from `audit_dashboard/data/dashboard_data.json::picks.recent_closed`):

| axis | finding | mutation save? |
|------|---------|----------------|
| direction | 24/24 LONG, no SHORT data | NOT TESTABLE (no inverse) |
| symbol | every symbol with n>=2 is 0% WR (JNJ 0/5, ABBV 0/3, XOM 0/3, MRK 0/2, CVX 0/2) | NO — only n=1 wins (MS, PLD) |
| strategy | `goldmine_6x_consensus` 0/17, `goldmine_5x_consensus` 3/5 (60% WR but sum -0.31% net flat), `goldmine_7x_consensus` 0/1, `goldmine_1x_consensus` 0/1 | NO — `5x` n<30 floor |

**By-strategy breakdown:**

```
strategy                         n wins     WR      sum     avg
goldmine_6x_consensus           17    0   0.0%  -58.71%  -3.45%
goldmine_5x_consensus            5    3  60.0%   -0.31%  -0.06%
goldmine_7x_consensus            1    0   0.0%   -5.59%  -5.59%
goldmine_1x_consensus            1    0   0.0%   -5.77%  -5.77%
```

**By-symbol breakdown:**

```
JNJ  n=5 wins=0 WR=  0.0% sum=-21.90%
ABBV n=3 wins=0 WR=  0.0% sum= -8.86%
XOM  n=3 wins=0 WR=  0.0% sum=-15.30%
MRK  n=2 wins=0 WR=  0.0% sum= -6.15%
GS   n=2 wins=1 WR= 50.0% sum= -1.64%   (still net negative)
CVX  n=2 wins=0 WR=  0.0% sum= -6.99%
[1-pick rows omitted]
```

`goldmine_6x_consensus` is a deterministic-loser-style fast-path candidate
(0% WR on n=17, just shy of the n>=20 hard fast-path threshold from
`feedback/loss-driver` analysis). Combined with PF 0.03 across the whole
source and an active pick book of 80, this is a clear net-negative emitter.
**Verdict: kill.**

## Devil's-advocate self-critique

1. **`copy_trader_highscore` LONG side at 80% WR n=5 looks tempting — is it really artifact?**
   Yes. Inspection (`updates/.../...`) shows 4 of the 5 LONG wins on
   `hs_lb_None` are HYPEUSDT/BTCUSDT/RENDERUSDT TP_HIT at exactly +3.50%
   pnl — same constant-PnL placeholder pattern as the SHORT 100%-WR symbol
   clusters. Wilson 95% LB on 4/5 ≈ 28%, which is below break-even after
   2bp average cost and well below the 50% break-even target. Cannot
   promote.

2. **`goldmine_5x_consensus` shows 60% WR — should we keep that variant only?**
   No — n=5 (below the n>=30 floor; Wilson 95% LB ≈ 23%) and net sum
   -0.31% means the wins are tiny and the losses cancel them. The Mutation
   Quality Score from §5 of the protocol (winning_subset_n × WR / total_n)
   for this variant = (3 × 0.6) / 24 = 7.5%, well below the 10% rule of
   thumb the protocol uses to reject a "tiny" winning subset.

3. **Are we killing too aggressively given goldmine has 410 unresolved closed picks?**
   The 24 resolved picks are the only data we can act on; the 410
   unresolved ones cannot be reasoned about until the resolver runs (see
   `feedback_noncrypto_resolver_live_close_bug.md` — the equity resolver
   path may still be polluted). However:
     - 0/14, then 3/24 progression is monotonically bad in the resolver
       output. The added wins (3) over 10 new resolutions still leaves
       WR 30%, well below break-even.
     - With 80 active emissions/day at PF 0.03, leaving the strategy live
       would inject more low-quality picks into the active gate while we
       wait for the resolver fix. Block-now is risk-asymmetric.
     - If post-resolver-fix data shows redemption (PF>1, WR>40%, n>=50),
       the entry is reversible by deletion — comments in the kill diff
       record exactly which variant + axis to revisit.

4. **Cross-asset migration?**
   `copy_trader_highscore` is crypto-only by design (Hyperliquid
   leaderboard). `goldmine_stocks` is equity-only by design. Neither
   admits a cross-asset rescue.

## Wiring proof

* `audit_trail/quality_gates.py:933-963` — `BLOCKED_SOURCE_SYSTEMS` set
  with new entries.
* `audit_trail/quality_gates.py:4059` — `passes_active_gate` rejects any
  pick whose `source_system.lower()` is in `BLOCKED_SOURCE_SYSTEMS`.
* `audit_dashboard/template.html` `BLOCKED_SYSTEMS` Set — synced (dashboard
  visibility).
* `tests/test_zombie_kill_2026_04_28.py` — 5 assertions covering set
  membership, gate rejection, case-insensitive match, additivity, and
  negative control.

## Cross-reference

* GitHub Cloud agent (Sonnet 4.6) deep-dive convergent finding.
* RooCode + EQUITY-team commit `a30df0ac` cross-source convergence.
* Cursor commit `c720b66d6b` — "retire three persistent negative-EV
  strategies" (same protocol, strategy-axis variant).

## Reproducer

```bash
# Re-derive the closed-pick CSVs:
python - <<'PY'
import csv, json
from pathlib import Path

def write(rows, dest):
    fields = ['strategy','symbol','direction','timeframe','system','pnl%']
    with open(dest, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for r in rows: w.writerow(r)

data = json.loads(Path('audit_trail/data/universal_resolved_picks.json').read_text(encoding='utf-8'))
chs = []
for p in data:
    if isinstance(p, dict) and (p.get('source_system') or '') == 'copy_trader_highscore':
        chs.append({
            'strategy': p.get('strategy') or '',
            'symbol': p.get('symbol') or '',
            'direction': str(p.get('direction') or '').upper(),
            'timeframe': str(p.get('timeframe') or p.get('mode') or 'UNK'),
            'system': p.get('source_system') or 'copy_trader_highscore',
            'pnl%': str(p.get('pnl_pct') or 0),
        })
write(chs, 'audit_exports/closed_copy_trader_highscore.csv')

dash = json.loads(Path('audit_dashboard/data/dashboard_data.json').read_text(encoding='utf-8'))
gms = []
for p in (dash['picks'].get('recent_closed') or []):
    if isinstance(p, dict) and (p.get('source_system') or '') == 'goldmine_stocks':
        gms.append({
            'strategy': p.get('strategy') or '',
            'symbol': p.get('symbol') or '',
            'direction': str(p.get('direction') or '').upper(),
            'timeframe': str(p.get('timeframe') or p.get('mode') or 'UNK'),
            'system': p.get('source_system') or 'goldmine_stocks',
            'pnl%': str(p.get('pnl_pct') or 0),
        })
write(gms, 'audit_exports/closed_goldmine_stocks.csv')
PY

# Re-run the autopsy:
python tools/mutation_analysis.py --csv audit_exports/closed_copy_trader_highscore.csv \
  --min-trades 5 --dir-spread 5 --tf-spread 5 --sym-spread 10 \
  -o reports/mutation_analysis_copy_trader_highscore_2026_04_28.txt
python tools/mutation_analysis.py --csv audit_exports/closed_goldmine_stocks.csv \
  --min-trades 3 --dir-spread 5 --tf-spread 5 --sym-spread 10 \
  -o reports/mutation_analysis_goldmine_stocks_2026_04_28.txt

# Verify the kill:
python -m pytest tests/test_zombie_kill_2026_04_28.py -q
```
