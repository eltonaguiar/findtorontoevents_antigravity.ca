# H-012 — Delta-Neutral Crypto Funding-Rate Arbitrage (Option 3)

_Generated 2026-11-22T08:50:38.576122+00:00_  
Research sidecar — `tools/funding_arb_research.py`. NOT wired to any production pick/score path.

## What this strategy is

Delta-neutral funding-rate arbitrage: hold spot, short the perp (or flip when funding is negative), collect the contractual 8h funding cash flow. ZERO directional view. This is **structure alpha** — paid to carry, not paid to predict. It is **NOT** H-006 (kill #6, which traded funding as a directional price signal).

## Data

- Universe: BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT, ADAUSDT, AVAXUSDT, LINKUSDT, DOGEUSDT, LTCUSDT (10 liquid perps)
- History: 2.0 years of real 8h funding-rate history
- Source: binance/bybit/okx (paginated, failover chain Binance fapi -> Bybit v5 -> OKX)
- Funding cycles modelled: 21,900 (578 held, 21,322 flat-skipped)

## Cost model (harsh, realistic retail)

- Taker fee perp: 5.0 bp/fill  |  spot: 10.0 bp/fill
- Slippage (half-spread): 1.5 bp/fill, 4 fills per round trip
- Borrow on short leg: 6.0%/yr
- Re-hedge drag: 0.3 bp/cycle
- Round-trip entry+exit cost amortised over 30 cycles (~10 days hold)
- Per-cycle running cost: 2.05 bp

## Gate (a) — cost survival

- Gross funding collected (sum |rate|): 1.452289
- Net carry after all costs: 0.073291
- **Survival: 5.05% of gross** (threshold >= 60.0%)
- Gate (a): FAIL

## Gate (b) — edge-stability harness

- Score field: `funding_z`  |  windows scored: 7  |  strong: 7 (7+ / 0-)
- per-window eff (new->old):  n/a  n/a  n/a  n/a  n/a  n/a  n/a  n/a  n/a  n/a  n/a  n/a  n/a  n/a  n/a  n/a  n/a  n/a  n/a  n/a +3.75  n/a  n/a  n/a  n/a +3.95  n/a  n/a  n/a +3.26  n/a  n/a  n/a  n/a  n/a  n/a  n/a  n/a  n/a  n/a  n/a  n/a +3.36 +3.26 +3.69  n/a  n/a  n/a  n/a  n/a  n/a +1.55
- sign: +  |  admissible: True
- ADMISSIBLE — stable same-sign separation
- Gate (b): PASS

## Verdict

**KILL — funding-rate arbitrage does NOT clear the acceptance gates**

Overall: KILL

### Per-symbol

| symbol | funding rows | gross funding | net carry | cycles held |
|--------|-------------:|--------------:|----------:|------------:|
| BTCUSDT | 2,190 | 0.120182 | 0.00167 | 20 |
| ETHUSDT | 2,190 | 0.121735 | 0.002301 | 32 |
| SOLUSDT | 2,190 | 0.162742 | 0.01712 | 78 |
| BNBUSDT | 2,190 | 0.087351 | 0.012473 | 109 |
| XRPUSDT | 2,190 | 0.148657 | 0.004442 | 43 |
| ADAUSDT | 2,190 | 0.178038 | 0.005998 | 66 |
| AVAXUSDT | 2,190 | 0.185345 | 0.011861 | 121 |
| LINKUSDT | 2,190 | 0.160302 | 0.006012 | 44 |
| DOGEUSDT | 2,190 | 0.143857 | 0.006114 | 34 |
| LTCUSDT | 2,190 | 0.144081 | 0.005299 | 31 |

---

## Honest conclusion

Funding-rate arbitrage **does not clear the acceptance gates** — this is a clean kill (#8). Cost model eats too much of the gross funding. A positive gross funding number that does not survive costs+harness is not an edge.

Pre-registered H-012, `reports/hypothesis_registry.json` (M-107). Research/sidecar only — no production wiring.