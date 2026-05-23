# H-012 — Delta-Neutral Crypto Funding-Rate Arbitrage (Option 3)

_Generated 2026-05-18T03:45:38.219061+00:00_  
Research sidecar — `tools/funding_arb_research.py`. NOT wired to any production pick/score path.

## What this strategy is

Delta-neutral funding-rate arbitrage: hold spot, short the perp (or flip when funding is negative), collect the contractual 8h funding cash flow. ZERO directional view. This is **structure alpha** — paid to carry, not paid to predict. It is **NOT** H-006 (kill #6, which traded funding as a directional price signal).

## Data

- Universe: BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT, ADAUSDT, AVAXUSDT, LINKUSDT, DOGEUSDT, LTCUSDT (10 liquid perps)
- History: 2.0 years of real 8h funding-rate history
- Source: binance/bybit/okx (paginated, failover chain Binance fapi -> Bybit v5 -> OKX)
- Funding cycles modelled: 21,900 (740 held, 21,160 flat-skipped)

## Cost model (harsh, realistic retail)

- Taker fee perp: 5.0 bp/fill  |  spot: 10.0 bp/fill
- Slippage (half-spread): 1.5 bp/fill, 4 fills per round trip
- Borrow on short leg: 6.0%/yr
- Re-hedge drag: 0.3 bp/cycle
- Round-trip entry+exit cost amortised over 30 cycles (~10 days hold)
- Per-cycle running cost: 2.05 bp

## Gate (a) — cost survival

- Gross funding collected (sum |rate|): 1.589784
- Net carry after all costs: 0.090803
- **Survival: 5.71% of gross** (threshold >= 60.0%)
- Gate (a): FAIL

## Gate (b) — edge-stability harness

- Score field: `funding_z`  |  windows scored: 13  |  strong: 13 (13+ / 0-)
- per-window eff (new->old):  n/a  n/a  n/a  n/a  n/a  n/a  n/a +3.51  n/a  n/a  n/a  n/a +3.77  n/a  n/a +2.53  n/a  n/a  n/a  n/a  n/a  n/a  n/a  n/a  n/a  n/a  n/a  n/a +3.50 +3.13 +3.80 +3.80  n/a  n/a  n/a  n/a  n/a +1.83 +1.69 +2.10  n/a  n/a  n/a  n/a  n/a  n/a +3.86  n/a  n/a  n/a +3.02 +3.27  n/a
- sign: +  |  admissible: True
- ADMISSIBLE — stable same-sign separation
- Gate (b): PASS

## Verdict

**KILL — funding-rate arbitrage does NOT clear the acceptance gates**

Overall: KILL

### Per-symbol

| symbol | funding rows | gross funding | net carry | cycles held |
|--------|-------------:|--------------:|----------:|------------:|
| BTCUSDT | 2,190 | 0.131844 | 0.002878 | 30 |
| ETHUSDT | 2,190 | 0.141384 | 0.003798 | 43 |
| SOLUSDT | 2,190 | 0.174413 | 0.018568 | 94 |
| BNBUSDT | 2,190 | 0.086381 | 0.014629 | 128 |
| XRPUSDT | 2,190 | 0.167669 | 0.006473 | 62 |
| ADAUSDT | 2,190 | 0.184711 | 0.006695 | 68 |
| AVAXUSDT | 2,190 | 0.207306 | 0.01603 | 161 |
| LINKUSDT | 2,190 | 0.176826 | 0.007493 | 59 |
| DOGEUSDT | 2,190 | 0.160238 | 0.008149 | 55 |
| LTCUSDT | 2,190 | 0.159011 | 0.00609 | 40 |

---

## Honest conclusion

Funding-rate arbitrage **does not clear the acceptance gates** — this is a clean kill (#8). Cost model eats too much of the gross funding. A positive gross funding number that does not survive costs+harness is not an edge.

Pre-registered H-012, `reports/hypothesis_registry.json` (M-107). Research/sidecar only — no production wiring.