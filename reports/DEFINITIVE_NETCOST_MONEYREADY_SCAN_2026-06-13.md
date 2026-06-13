# Definitive net-cost money-ready scan — ONE survivor

**Author:** claude-fable · 2026-06-13 ~07:18Z · **Method:** for every `(strategy, category)` in `trading_picks` with ≥80 deduped (symbol-day) resolved picks (2026+), subtract a per-class realistic round-trip cost from each trade's `pnl_pct` (FX majors 2bp / JPY 6bp, crypto 10bp taker, commodity/futures 3bp, equity/etf 3bp; pnl_pct is percent → 1bp = 0.01), then compute net PF + cluster-bootstrap **PF CI-LB** (`tools/pf_ci_lower.py`, symbol-day clusters) + n_eff + IS/OOS net split + concentration.

**Gate (all four required):** net CI-LB > 1.15 · n_eff ≥ 80 · OOS net PF ≥ 1.0 · top-symbol concentration < 35%.

## Result: 1 survivor of ~19 strategies tested

**`non_crypto_consensus / COMMODITY`** — net CI-LB **1.75** @ n_eff 136 · gross PF 2.69 → **net PF 2.58** · IS/OOS net **5.73 / 1.44** · conc 19%. **The first strategy to clear the full net-of-cost promotion gate this session.**

### Ranked table (top 15 by net CI-LB)

| strategy / category | n | gross PF | net PF | **net CI-LB** | IS net | OOS net | conc% |
|---|--:|--:|--:|--:|--:|--:|--:|
| **non_crypto_consensus / commodity** | 136 | 2.69 | 2.58 | **1.75 ✓** | 5.73 | 1.44 | 19 |
| cta_commodity_momentum_term / commodity | 252 | 1.64 | 1.57 | 1.14 | 1.98 | 1.30 | 24 |
| (unnamed) / crypto | 217 | 2.09 | 1.98 | 1.13 | 1.78 | 3.59 | 7 |
| luxalgo_confluence / crypto | 1116 | 1.15 | 1.06 | 0.95 | 1.20 | 0.96 | 7 |
| stocks_rsi2_pullback / equity | 313 | 1.32 | 1.24 | 0.91 | 1.06 | 1.41 | 7 |
| prediction_market_consensus / crypto | 375 | 1.23 | 0.77 | 0.51 | 0.61 | 0.99 | 17 |
| **non_crypto_consensus / forex** | 304 | 1.79 | 0.62 | 0.48 | 0.72 | 0.52 | 12 |
| myfxbook_retail_contrarian / forex | 282 | 1.37 | 0.52 | 0.38 | 0.57 | 0.47 | 14 |
| forex_rsi2_mean_reversion / forex | 359 | 1.55 | 0.50 | 0.37 | 0.44 | 0.58 | 11 |
| futures_momentum / commodity | 321 | 0.39 | 0.37 | 0.26 | 0.48 | 0.24 | 17 |

## Key insight: cost-amplitude, not signal, is the gate
The same `non_crypto_consensus` source **survives on COMMODITY but dies on FOREX**. Commodity winners are large enough that 3bp barely dents PF (2.69→2.58); FX winners are tiny (0.2–0.3%) so 2bp+ erases the edge (1.79→0.62). Low-amplitude edges are not deployable regardless of statistical strength. This is why the net-cost gate is essential — it killed FOREX consensus, futures_momentum (mirage), forex_rsi2, and luxalgo crypto, while passing exactly one.

## Caveats before any sizing (NOT money-ready yet — forward-pilot first)
1. **IS/OOS decay (5.73 → 1.44):** the edge is weakening over time. The net CI-LB 1.75 is dominated by the strong IS half; the forward-relevant strength is **OOS net ~1.44**, not the 2.58 headline. Real, but watch the decay — this goes to a forward pilot to confirm OOS strength holds, NOT a sized position on the headline.
2. **COMMODITY is the peer's lane** (per project convention). This finding should be handed to / coordinated with the peer who owns commodity, not unilaterally actioned.
3. **Cost assumption (3bp commodity round-trip):** reasonable for liquid futures but instrument-specific; validate the actual cost for the symbols traded (the memory's prior CT=F concentration note is relevant — conc here is 19%, acceptable, but confirm the symbol mix).
4. **Daily resolver** (not intrabar first-touch) — same caveat as the FOREX pilot.

## Recommendation
- **non_crypto_consensus / COMMODITY is the project's first net-of-cost-surviving candidate.** Promote it to a **forward pilot** (read-only sidecar, like PR #592 for FOREX), gating acceptance on net CI-LB holding >1.15 on the *forward* (post-today) window — to confirm the OOS 1.44 isn't decaying toward 1.0.
- Hand to the COMMODITY-lane peer; do not size on the IS-inflated headline.
- **North-star update:** not "0 money-ready" anymore — there is **1 qualified candidate** (commodity consensus), pending forward confirmation of the decay. Everything else fails net of cost.

## Reproduce
`tools/pf_ci_lower.py` over deduped `trading_picks` per `(strategy,category)`, `net = pnl_pct − per_class_cost`, gate as above. DB via `tools/db_env.get_stocks_creds()`.
