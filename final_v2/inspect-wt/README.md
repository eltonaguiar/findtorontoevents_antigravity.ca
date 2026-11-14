# inspect-wt (deepAI) — final_v2 last-chance deliverable (2026-11-14)

**Worktree:** `.inspect-wt` · **Branch:** `audit/live-audit-2026-11-14` · **Agent:** deepAI
**Prior packages:** `final_2026_11_14/inspect-wt/` (full audit + V0–V6 research + first peer review)
**This folder:** the closing pass — final peer adjudication + **concrete per-asset-class paths to
profitability**, grounded in my own measured evidence.

```
final_v2/inspect-wt/
├── README.md                          ← this file (last-chance synthesis)
├── 01_peer_review/
│   └── peer_adjudication_final.md     ← claim-by-claim final verdicts on ALL peers (incl. final_v2)
└── 02_profitability_per_asset_class/
    ├── _overall.md                    ← order of operations + certification gates (READ FIRST)
    ├── crypto.md                      ← "don't trade the zoo" + mega_mutation verification plan
    ├── equity_etf.md                  ← variant C forward pilot (the only system-native edge)
    ├── forex.md                       ← fix feed → carry basket; no trading until then
    ├── futures_commodity.md           ← real-feed veto; CTA trend only after unblock
    ├── bond.md                        ← backfill marks → duration rotation; NOT_BUILT until n≥100
    └── mutual_funds.md                ← de-advertise (no intraday edge possible)
```

## Last-chance review headline

All peers now **converge** (finpredict's own final_v2 corrects its earlier "PROVEN" TSMOM
over-claim; finpredict-v3, quant-audit, v2 all land on the same picture): **0/166 money-ready
cells, no raw-alpha edge proven, root cause = data integrity + multiple testing.** I endorse
that convergence. Standing disagreements I maintain:

1. **flaxen-hair's `mega_mutation` "PROVEN / production_enable=true"** — I dispute it:
   0 rows on `recent_closed`, pf_registry cells flagged `is_single_source_artifact=True`
   (PF 49–53 at n=124), strict OOS n=16 (finpredict-v2). → **gated pilot + independent
   price-truth verification first** (see crypto.md).
2. **`resolution_method=None` on all 3,500 closed rows** (quant-audit, confirmed by me) —
   the single fact blocking certification of *any* PF, including my variant C. Fix first.
3. **Kilo's VWAP "Sharpe 3.76"** — falsified twice independently (finpredict-v2 +
   quant-audit). Do not adopt.

## My per-class profit paths in one table (evidence-backed, details in 02_)

| Class | My measured truth (live) | Near-term path (0–3 months) | Long-term path | Tradable today? |
|---|---|---|---|---|
| **CRYPTO** | open real P/L **−2.57%** mean; 76% zombies; sources PF 0.23–0.83; variant C picks **1 trade in 8 months** | mega_mutation: verify 50 rows vs Binance klines → gated paper pilot | 1 vol-targeted TSMOM sleeve (expect Sharpe 0.5 bear-inclusive) + funding carry ≤15% book | **NO** |
| **EQUITY/ETF** | variant C forward **ETF n=120 PF 1.21 + EQUITY n=112 PF 1.30 = +99.7pp** of +98.7pp total | **variant C forward pilot** (pre-registered, weekly) with hardening: resolution_method, slippage estimate, vwap-concentration cap | diversified factor portfolio (finpredict's roadmap) as separate research | **PILOT ONLY** (¼ Kelly 2.5%/trade) |
| **FOREX** | open 114 picks **−1.96%**; EURGBP entry 688; sources PF 0.27–0.71 | fix price feed (garbage-ingest guard + phantom resolver) | carry basket + trend overlay (Sharpe ~0.3–0.6) | **NO** |
| **FUTURES/COMMODITY** | 0 closed ever; crypto proxies for silver/oil; `=F` mislabeled | real GC=F/SI=F/CL=F feed + staleness guard | CTA trend across liquid futures (Sharpe ~0.5–1.0) | **NO** (veto unblock w/o feed) |
| **BOND** | n=1–3, vacuous PASS, null-price seeds | backfill FRED/yfinance marks (never `current=entry`) | rate-trend / duration rotation | **NO** |
| **MUTUAL FUNDS** | vaporware (monthly NAV, no mark-to-market) | de-advertise (`NOT_BUILT`) via my fixspec | monthly tactical rotation only, if ever | **NO** |

## Order of operations (applies before ANY profitability claim is certified)
1. Populate `resolution_method` + fix PnL-unit mix bug (`dashboard_generator.py:8065-8072`).
2. Single canonical ledger (my `fixspec_single_canonical_ledger`) + zombie purge + re-emission guard.
3. Re-run every PF claim (variant C, mega_mutation) on the cleaned ledger → one certified number.
4. Forward-only evaluation with T2 gates + kill criteria (see `_overall.md`).

**Honest expected outcome:** risk premia of Sharpe 0.3–1.0 net (not contest-winning alpha), plus
one system-native forward pilot (variant C on equity/ETF) whose weekly scheduler task
`5992b142` (next run 2026-11-21) arbitrates. Reproduce anytime:
`python final_2026_11_14/inspect-wt/06_profitable_approach/walkforward_v6.py <payload>`.
