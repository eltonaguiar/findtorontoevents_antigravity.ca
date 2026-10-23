# Other Entry Conditions — Systematic Investigation (2026-10-22)

## What I did

Ran the sanctioned exploratory edge-miner [`tools/mine_entry_condition_cells.py`](tools/mine_entry_condition_cells.py) (systematic (class × direction × RSI-band × session) cell enumeration + vol-regime axis, BH-FDR screen, symbol-bootstrap CI-LB robustness gate) on the honest deduped intrabar cohort, **plus** a new extension [`tools/mine_entry_condition_cells_extended.py`](tools/mine_entry_condition_cells_extended.py) covering the **unmined axes**: F1 trend-alignment, F2 24-bar momentum, and day-of-week.

- miner: cohort=3,525 / stamped=3,406 / 85 cells tested / BH-FDR rejected 71 / **6 robust candidates**
- extended: 71 cells tested / BH-FDR rejected 57 / **7 robust candidates**

## An other entry condition that wins: CRYPTO SHORT @ RSI 30-50

The single biggest discovery is a **different RSI band** than what we currently track. Our tracker only watches **RSI 50-70 SHORT** — which is a net loser over the full cohort (net PF 0.951). Mining the full RSI space flips the picture:

| Cell | n | WR% | Net PF | bootstrap CI-LB(5%) | ex-top3 net PF | Both BTC regimes | FDR pass |
|---|---|---|---|---|---|---|---|
| `CRYPTO\|SHORT\|RSI30-50` | 125 | 60.8 | **2.163** | 1.688 | 1.544 | Y | Y |
| `CRYPTO\|SHORT\|RSI30-50\|WITH` (F2 momentum WITH) | 102 | 61.8 | **2.475** | 1.707 | 1.733 | Y | Y |
| `CRYPTO\|SHORT\|RSI30-50\|VOLLOW` | 77 | 61.0 | 2.378 | 1.657 | 1.568 | Y | — |
| `CRYPTO\|SHORT\|RSI30-50\|EU` | 44 | 68.2 | 1.746 | 1.177 | 1.129 | Y | Y |
| `CRYPTO\|SHORT\|RSI30-50\|VOLHIGH` | 48 | 60.4 | 1.881 | 1.248 | 1.279 | Y | — |
| `CRYPTO\|SHORT\|RSI30-50\|ASIA` | 52 | 51.9 | 2.087 | 1.302 | 1.075 | Y | — |
| `CRYPTO\|SHORT\|F2WITH` (momentum, no RSI) | 207 | 58.0 | 2.023 | 1.834 | 1.776 | Y | Y |
| `CRYPTO\|SHORT\|F1ALIGNED` (trend-aligned) | 198 | 55.6 | 1.755 | 1.620 | 1.480 | Y | — |
| `CRYPTO\|SHORT\|RSI50-70\|WITH` | 89 | 51.7 | 1.596 | 1.383 | 1.182 | Y | — |
| `CRYPTO\|SHORT\|DOWTue` | 88 | 51.1 | 1.492 | 1.085 | 1.067 | Y | — |
| `CRYPTO\|SHORT\|DOWMon` | 139 | 51.1 | 1.332 | 1.172 | 1.133 | Y | — |

**All figures are net-of-cost** (16bp CRYPTO round-trip). All pass the robust gate (`net PF ≥ 1.2 AND n ≥ 40 AND symbol-bootstrap CI-LB ≥ 1.0 AND wins in both BTC-up and BTC-down months`). The core family is **broadly diversified (28–31 symbols)** — low single-symbol concentration, unlike the equity cells.

### Reading
- **Direction is the edge gate**: `CRYPTO SHORT` is broadly positive across RSI bands; `CRYPTO LONG` is broadly negative (e.g. LONG RSI50-70 net PF 0.693, LONG F1ALIGNED 0.754).
- **The RSI band matters a lot**: SHORT **30-50** (net PF 2.163) is >2× stronger than SHORT **50-70** (0.951). Momentum/trend confirmation (F2 WITH, F1 ALIGNED) and the very SHORT band are additive.
- **The equity high-netPF cells are concentration artifacts**: `EQUITY|LONG|F2WITH` (net PF 5.115) and `EQUITY|LONG|RSI50-70` (4.045) look huge but have bootstrap CI-LB ≈ 0 and only 8–16 symbols → single-name/frozen-exit artifacts, not robust. Ignore.

## Updated the forward tracker

Added both new monitor conditions to [`tools/stamp_entry_conditions.py`](tools/stamp_entry_conditions.py) `CONDITIONS` so they accrue forward n on every run (read-only measurement lane, never a sizing input):
- `crypto_short_rsi3050`
- `crypto_short_rsi3050_f2with`

## Risk / promotion status

- All of the above are **exploratory survivors** — they need a fresh forward pre-registration + single-hypothesis gate (`n ≥ 80 fwd, net-PF CI-LB > 1.15, time-split, concentration < 35%`) before any sizing. This is exactly the discipline in `mine_entry_condition_cells.py`'s caveat.
- The core `CRYPTO|SHORT|RSI30-50` cell already has **n=125** (> the 80 fwd gate) with **bootstrap CI-LB 1.688** (> 1.15) — it is the strongest candidate found so far, but the exploratory cohort is retrospective; it must accrue a **fresh forward** sample before promotion.
- Crypto tail risk (no CVaR/Omega measured) and SHORT borrow/perps execution still apply — Phase-3 is still not built.

## Recommendation

Prioritize forward-monitoring **`CRYPTO SHORT RSI 30-50`** (with the F2-with variant as the highest-WR slice). If it holds its bootstrap CI-LB > 1.15 over a fresh n≥80 forward window, it becomes the first candidate to actually pass the Phase-2 promotion bar — stronger than everything on the current dashboard.

## Files
- `tools/mine_entry_condition_cells.py` (existing miner, ran)
- `tools/mine_entry_condition_cells_extended.py` (new F1/F2/DOW axis miner, added)
- `tools/stamp_entry_conditions.py` (added `crypto_short_rsi3050`, `crypto_short_rsi3050_f2with` monitor conditions)
- outputs: `/tmp/mined_cells.json`, `/tmp/mined_cells_ext.json` (exploratory, not committed)

*Not financial advice. Research/educational only. Past performance does not guarantee future results.*
