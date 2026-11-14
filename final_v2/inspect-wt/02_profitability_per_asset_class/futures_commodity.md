# FUTURES / COMMODITY — how to get profitable (deepAI)

## My measured truth (live, 2026-11-14)
- Active: FUTURES 22 picks (**95.5% zombie** — highest of any class; repriced n=4, all flat),
  effectively dead. My audit found **zero closed futures ever** (finpredict-v3 confirms:
  date-only timestamps, class sits in `BLOCKED_ASSET_CLASSES`).
- **The commodity feed is counterfeit:** 44/44 rows labeled `=F` futures are actually **crypto
  proxies** (RNDR/ARB/XLM/DOT standing in for silver/oil) — so every "commodity" pick ever
  priced was priced off crypto. My own per-class quick-wins doc flagged this in session 1.
- V1 cells: commodity sources PF 0.36–0.81 (`silver_fade` 0.36 worst) — anti-skill on fake data.

## What peers propose
- **CTA time-series momentum** across liquid futures (ES, NQ, CL, GC, ZN), vol-targeted,
  realistic Sharpe **0.5–1.0** (finpredict roadmap) — the canonical managed-futures premium.
- Commodity **carry + momentum**, Sharpe ~0.3–0.7, only with a real feed (same source).
- **Veto: do NOT unblock the class without a real futures feed** (finpredict + my session-1
  recommendation — I endorse the veto).

## My plan
1. **Hard veto stands:** no futures/commodity picks, no backtest claims, no unblocking —
   until `canonical_asset_class=FUTURES` labeling is fixed and a **real GC=F/SI=F/CL=F/ES=F`
   feed** with staleness guard replaces the crypto proxies. (Proposed in my
   `fixspec_garbage_price_ingest_guard` + per-class quick wins.)
2. **After a real feed exists:** run **one** vol-targeted CTA trend sleeve (50d+200d blend)
   across 5–10 liquid futures, pre-registered, excess-of-benchmark paired bootstrap.
   Do not resurrect the 0.36–0.81 PF signal zoo — it was measured on counterfeit prices and
   its numbers are meaningless either way.
3. **Label honestly in the interim:** dashboard should show `NOT_BUILT / DATA_COUNTERFEIT`
   for commodity, not green PASS (my `fixspec_surface_disagreement_banner` covers the pattern).

**Tradable today: NO — and nothing about today's data is even measurable.** The honest path is
short: real feed → one CTA sleeve → forward gates. Realistic end-state Sharpe 0.5–1.0.
