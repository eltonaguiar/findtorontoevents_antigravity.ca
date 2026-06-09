# Phase B step 1 — Wire `load_db_edge_forward()` into `QuantScorer.score()` (2026-06-09)

## What was wrong

`tools/picks_now_professional.py::QuantScorer.score()` was scoring the W_DB_EDGE
10-pt block from `load_db_edge()` — the **all-time** at_pick_outcomes WR.
That overlay is contaminated by:

1. **77.8% backfill labels** (resolver_version LIKE 'backfill%') — same data, two
   resolvers, two different PFs (0.51 vs 2.15). The `load_db_edge()` already
   quarantines these; the contamination that remains is the **staleness** of the
   non-backfill rows.
2. **Stale strategies** that haven't emitted fresh picks in 60-180 days but
   still carry their old WR into the scoring. A strategy that was 70% WR in
   2026-02 contributes the same 70% to a 2026-06 pick's score as a strategy
   that was 70% WR last week. Anti-predictive in a moving market.
3. **No TP/SL quality check** — picks would show 8%/4% TP/SL on a 0.5% ATR
   symbol (unreachable TP) or 1% SL on a 12% ATR symbol (stopped out instantly).
   Per the 2026-06-08 quant audit: 78.9% of SL hits came from too-tight SLs;
   94% of signals EXPIRED before hitting either TP or SL.

## What changed (7 patches in one commit on `tools/picks_now_professional.py`)

1. **`QuantScorer.score()` signature** — added `db_edge_forward: dict | None = None`
   parameter so the scorer can consume the new overlay without breaking the
   legacy `db_edge` callers.
2. **Forward-edge extraction** — added `dbf_wr`, `dbf_n_w`, `dbf_avg_pnl`,
   `dbf_staleness`, `dbf_active` (= `n_weighted >= 10`), `dbf_n_raw_60d` from
   the forward overlay. `dbf_active` is the gate that prevents tiny-decayed
   ghost-strategies from triggering the W_DB_EDGE bonus.
3. **W_DB_EDGE block (10 pts)** — replaced the contaminated `db_n >= 20` check
   with a forward-weighted check that requires `dbf_active` (= n_weighted >= 10).
   WR > 55% gives the full 10 pts; WR > 45% gives 4 pts. Both now also fire
   a `DB_FWD_WR=…% n_w=…` signal so the page can surface the source.
4. **Staleness penalty** — `>14d` since most-recent resolution knocks the
   W_DB_EDGE bonus down 50%; `>28d` knocks it down 25%. A symbol that was
   great 3 months ago gets ~zero credit. A `STALE(dbf_age=Nd)` signal is
   appended so the page can show the decay.
5. **Negative-expectancy guard** — was `db_n >= 20 and db_avg_pnl < 0`;
   now `dbf_active and dbf_avg_pnl < 0` (i.e. requires the forward overlay to
   confirm a meaningful effective sample AND negative avg PnL). Demotes
   STRONG_BUY/BUY to WATCH.
6. **`tp_sl_quality_score`** (NEW FIELD, 0–100) — ATR-relative:
   - **TP sweet spot**: 2-4 ATRs (best at 3 ATRs); linear penalty outside
     that band; hard zero if TP > 6 ATRs (unreachable).
   - **SL sweet spot**: 1-2 ATRs (best at 1.5 ATRs); linear penalty outside
     that band; hard zero if SL < 1 ATR (too tight → 78.9% of historical
     SL hits came from this).
   - Score is the average of the two sub-scores; `None` when BUY/STRONG_BUY
     didn't fire (so we don't penalize non-actionable picks).
7. **`main()`** — calls `load_db_edge_forward(decay_half_life_days=14, max_age_days=60)`
   and passes it into every `scorer.score()` call. Both legacy `db_edge` and
   the new `db_edge_forward` are loaded so callers that read the old fields
   don't break.

## New fields in the picks_now.json output (per pick)

| Field | Type | Meaning |
|---|---|---|
| `dbf_active` | bool | `n_weighted >= 10` (effective sample size) |
| `dbf_wr` | float | Decay-weighted WR (0-100) over 60d window |
| `dbf_n_weighted` | float | Sum of decay weights (effective sample size) |
| `dbf_n_raw_60d` | int | Raw row count in the 60d window |
| `dbf_avg_pnl` | float | Decay-weighted avg PnL (decimal) |
| `dbf_staleness_days` | float | Days since most-recent resolution |
| `tp_sl_quality_score` | float\|null | ATR-relative TP/SL achievability (0-100) |

The legacy `db_n`, `db_wr`, `db_avg_pnl` are still in the output for
back-compat with `picks-now.html` consumers.

## Why these defaults

- **`decay_half_life_days=14`** — a strategy that fired two weeks ago is
  half as relevant as one that fired today; four weeks ago is one-quarter.
  This matches the natural cadence of crypto/forex strategy regimes.
- **`max_age_days=60`** — beyond 60d, the decay weight drops to ~0.16, so
  the data still gets included (no arbitrary cutoff bias) but contributes
  almost nothing. A pure cutoff would have created selection bias.
- **`n_weighted >= 10`** as the activation threshold — corresponds roughly
  to "10 effectively-recent picks" of evidence. Below that, the W_DB_EDGE
  bonus stays at zero to prevent a single lucky week from dominating.
- **TP sweet spot 2-4 ATRs, best 3** — institutional momentum/mean-reversion
  standard (see Kaufman, *Trading Systems and Methods*). 1 ATR is too tight
  to be tradable; 6 ATRs almost never fills inside the resolver horizon.
- **SL sweet spot 1-2 ATRs, best 1.5** — the canonical 1.5× ATR stop used
  by most CTAs. Below 1 ATR ≈ noise; above 2 ATRs you're giving back too
  much of the expected value.

## How to verify

```bash
cd /home/eaguiar2015/findtorontoevents_antigravity.ca

# 1. Compile-check
python3 -m py_compile tools/picks_now_professional.py && echo "COMPILE OK"

# 2. Smoke-test the new forward overlay without doing a full re-scan
python3 -c "
import sys; sys.path.insert(0, '.')
from tools.picks_now_professional import load_db_edge_forward, QuantScorer
dbf = load_db_edge_forward(decay_half_life_days=14, max_age_days=60)
print(f'forward overlay: {len(dbf)} symbols')
for sym in list(dbf.keys())[:5]:
    r = dbf[sym]
    print(f'  {sym:10s} dbf_wr={r[\"wr\"]:5.1f}%  n_w={r[\"n_weighted\"]:5.2f}  '
          f'staleness={r[\"staleness_days\"]:4.1f}d  avg_pnl={r[\"avg_pnl\"]:+.3f}')
"

# 3. (Optional) Re-run a full picks-now refresh and check the new fields
#    in the JSON: dbf_active, dbf_wr, tp_sl_quality_score, etc.
python3 tools/picks_now_professional.py
python3 -c "
import json
d = json.load(open('audit_dashboard/data/picks_now.json'))
for p in d['picks'][:3]:
    print(f\"{p['symbol']:8s} score={p['score']:5.1f} {p['direction']:11s}  \"
          f\"dbf_active={p.get('dbf_active')}  dbf_wr={p.get('dbf_wr', 0):.0f}%  \"
          f\"tpsl_q={p.get('tp_sl_quality_score')}\")
"
```

## What's next (Phase B step 2)

- `tools/picks_now_forward_tracker.py` — emit-history table + bucketed
  forward WR for the live "now" picks, to actually close the
  forward-validation loop (G4 gate).
- `tools/picks_now_reliability_panel.py` — P1/P2/P3/P5 pillars (P4 is
  already live via this patch's G1 filter).
- Re-run the per-asset-class clean-cohort screen on the now-clean data; the
  wire-up of G2 should make 0/9 → 0/9 still (no new edge created), but
  individual picks on the page should now be more accurately scored.

## Honest caveats

- The forward overlay is **strictly a measurement fix**, not a new edge
  source. It does NOT add real-money picks; it just makes the existing
  ones more honestly scored. The 0/9 money-ready verdict is unchanged.
- This patch does NOT change `picks-now.html` rendering — the new fields
  are present in the JSON but not yet shown on the page. That's a
  separate `picks-now.html` UI update.
- The "legacy" `db_n` / `db_wr` fields are kept in the output for one
  release cycle to give the page renderers time to migrate; a follow-up
  patch will likely deprecate them.
