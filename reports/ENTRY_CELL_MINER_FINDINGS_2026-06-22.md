# Systematic Entry-Cell Edge Miner — Findings (2026-06-22)

**Tool:** `tools/mine_entry_condition_cells.py` (read-only, exploratory). Reuses the validated
honest-intrabar `fetch_cohort`/`fetch_bars`/`features`/`stats` from `stamp_entry_conditions.py`
(no re-implementation). Enumerates every `(class × dir × RSI-band × session)` cell + roll-ups,
ranks by net_PF, BH-FDR q=0.10 on the per-cell two-sided binomial p (WR vs 0.5).

**Run:** cohort=1251, stamped=1207, cells_tested=18, BH-rejected=15. Raw: `reports/entry_cell_scan_2026-06-22.json`.

## Why this matters
`crypto_rsi5070_us` (net PF ~1.34) is a *winning pocket inside a losing class* (CRYPTO overall
intrabar PF ~0.79). This miner finds all such pockets at once instead of hand-guessing one
predicate at a time — the systematic path to a second/third honest edge.

## Top cells by net_PF (n≥30)

| cell | n | WR% | PF | netPF | binom_p | FDR | read |
|------|---|-----|-----|-------|---------|-----|------|
| **CRYPTO\|SHORT\|RSI50-70** | 45 | 57.8 | 1.69 | **1.52** | 0.30 | no | **top candidate, underpowered** |
| CRYPTO\|SHORT\|ASIA | 35 | 48.6 | 1.59 | 1.38 | 0.87 | no | R:R-driven, not significant |
| CRYPTO\|LONG\|RSI50-70\|US | 99 | 40.4 | 1.15 | 1.02 | 0.056 | yes | the rsi5070 LONG lead (thin on this window) |
| CRYPTO\|LONG\|RSI30-50\|US | 136 | 32.4 | 0.85 | 0.74 | <0.001 | yes | **avoid** |
| CRYPTO\|LONG\|RSI50-70\|ASIA | 168 | 28.0 | 0.63 | 0.56 | <0.001 | yes | **avoid** (LONG outside US is a loser) |
| CRYPTO\|LONG\|ASIA / EU / RSI<30 / RSI>70 | 45–424 | 22–35 | <0.73 | <0.66 | <0.001 | yes | **avoid filters** |

## Honest verdict
1. **rsi5070-LONG remains the lead** — still the only FDR-passing LONG pocket with net_PF>1, but
   thin (1.02–1.34 depending on window). No change to its forward gate (n≥150, CI-LB>1.15).
2. **NEW candidate: `CRYPTO|SHORT|RSI50-70` (net PF 1.52, n=45).** The SHORT side of the same RSI
   band screens *higher* than the LONG lead. BUT **underpowered** — WR 57.8% at n=45 gives binom_p
   0.30 (not distinguishable from noise); the 1.52 leans on R:R asymmetry. This is a **forward-track
   candidate, not a winner.** Next step: forward-register it (shadow lane, mirroring the rsi5070-LONG
   tagger) to accrue n; it needs n≥80 fwd + net-PF CI-LB>1.15 + time-split before any sizing claim.
3. **Confirmed avoid-filters** (FDR-significant losers): CRYPTO LONG outside the US-session RSI50-70
   pocket — RSI30-50, RSI<30, RSI>70, and ASIA/EU sessions — all net_PF<0.75. Not taking these is
   itself portfolio-positive.

## Caveats (binding)
- Cells overlap (roll-ups reuse picks) → FDR here is a **screen**, not a clean independent test.
- A surfaced cell must pass a **fresh single-hypothesis forward gate** before promotion.
- Direction asymmetry (SHORT>LONG) may be **regime-specific** (choppy/down window) — verify it
  persists across a time-split before believing it.
