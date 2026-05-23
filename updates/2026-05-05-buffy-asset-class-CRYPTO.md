# CRYPTO Asset Class Audit — Buffy
**Agent:** Buffy (Codebuff) | **Date:** 2026-05-05  
**Class Status:** WATCH (WR 44.2% | PF 1.26 | n=1,512 recent | +292.50% cum PnL)

---

## Health Summary

CRYPTO is the largest asset class by volume (1,512 recent trades) and generates +292.50% cumulative PnL — BUT this is carried by a handful of winning strategies while alpha_engine bleeds -51.64% alone.

## Top Winners

| Strategy | WR | n | Cum PnL | Verdict |
|----------|-----|---|---------|---------|
| luxalgo_filters | 53.6% | 179 | **+133.62%** | PROTECT |
| claude_gainer_st | 66.7% | 81 | **+37.22%** | UN-KILL (killed on stale data) |
| kimi_riseoftheclaw | 53.2% | 60 | **+36.49%** | PROTECT |
| st_fear_greed_contrarian | 87.7% | 138 | +? | PROTECT (missing PnL, fix pipeline) |

## Top Losers

| Strategy | WR | n | Cum PnL | Action |
|----------|-----|---|---------|--------|
| **alpha_engine** | 34.5% | 460 | **-51.64%** | **KILL** — replace with inverse_quan_engine_scalp (70% WR) |
| quan_engine | 17.6% | 68 | -21.76% | **INVERSE** — inverse already exists at 70% WR / PF 2.0 |
| dna_rapid_fire_mutations | 29.0% | 31 | -9.61% | **INVERSE** — 3/3 swarm unanimous |

## Specific Fixes

1. **Kill `alpha_engine`** — 524 total trades at 34.5% WR = statistically significant negative edge. Replace with `inverse_alpha_engine` or redirect to `inverse_quan_engine_scalp` (70% WR, PF 2.0, 1,643 trades)
2. **Un-kill `claude_gainer_st`** — 66.7% recent WR (81 trades) contradicts kill list's 26.5% WR claim. The kill list has stale data.
3. **Inverse mutate `dna_rapid_fire_mutations`** — unanimous swarm recommendation, strong precedent (12 inverse-validated strategies in winners_registry.json)
4. **Block TRXUSDT** — -10,064% PnL (103% of ALL negative crypto PnL). Already in BLOCKED_SYMBOLS in quality_gates.py — verify it's actually enforced.
5. **Block MATICUSDT** — 424 trades, 0% WR, -63.60% PnL. Delisted token generating phantom TIME_EXIT trades.

## Proven Inverse Pipeline (Already Exists!)

| Original | Inverse | WR | PF | n |
|----------|---------|-----|-----|---|
| quan_engine_scalp | inverse_quan_engine_scalp | 70.0% | 2.0 | 1,643 |
| claude_gainer_1h | inverse_claude_gainer_1h | 78.7% | 99.99 | 47 |
| winner_pattern_precursor | winner_pattern_precursor_inverse | 81.2% | 2.35 | 48 |

**Stop building new strategies. Start inverting existing losers.**
