# multi_asset_cot — Slippage-Eats-Edge Analysis — 2026-05-13

**Trigger:** P0-D verifier ran 2026-05-13T02:55Z. Verdict in [reports/multi_asset_cot_db_verify_2026_05_13.md](reports/multi_asset_cot_db_verify_2026_05_13.md): **REAL** — PF 21.86 / WR 94.1% / n=102. **But the verifier did not apply slippage, and the gross numbers hide the real economic verdict.**

## Per-trade pnl is microscopic

Top-5 winning trades from the verifier output:

| rank | gross pnl |
|---|---|
| 1 | +7.18 bp |
| 2 | +6.19 bp |
| 3 | +6.18 bp |
| 4 | +6.18 bp |
| 5 | +6.18 bp |

The biggest winning trade in n=102 is **+7.18 basis points**. DeepSeek's prediction from session 1e0e line 2609 nails it: "microscopic per-trade pnl — only profitable at futures-contract scale."

## After slippage every "win" becomes a "loss"

Per [reports/implementation_plan_v2_2026-05-13.md](reports/implementation_plan_v2_2026-05-13.md) P0.5-2 spec, COMMODITY round-trip slippage = **12 bp**. So:

| metric | gross | net (post 12bp r/t) |
|---|---|---|
| top win | +7.18 bp | **−4.82 bp** |
| avg top-5 win | +6.38 bp | **−5.62 bp** |
| ⇒ net PF | 21.86 | **likely < 1.0** |

The data-integrity verdict (REAL) is correct. The economic verdict at retail scale is "edge does not survive realistic friction."

## Per-symbol: 96 of 102 trades are CT=F

- CT=F: 96 picks, PF 26.96, WR 94.8%
- ZW=F: 5 picks, PF ∞ (all wins), WR 100%
- KC=F: 1 pick, PF 0, WR 0%

This is a **single-symbol concentration risk** at 94% — exactly what P0.5-4 concentration controls flag against.

## What this means

1. **CT=F paper-pilot graduation gate now has 3 requirements** (was 2):
   - Lag-corrected WR ≥ 75% (PR #941)
   - DSR ≥ 0.85
   - **NEW:** Net WR ≥ 50% after P0.5-2 slippage applied
2. **P0.5-2 slippage model is now load-bearing** for the COMMODITY graduation decision. Plan-reviewer swarm flagged "P0-D should jump P0.5-2" — confirmed: P0.5-2 must ship next, not later
3. **New gate proposed:** `MIN_NET_PNL_BPS_BY_CLASS` in `quality_gates.py` — reject any strategy whose expected net pnl per trade < per-class spread floor. CT=F at retail scale would fail this.

## What survives

- The "edge is real" framing is **correct gross**
- COMMODITY class-level T1 candidacy (PF 3.94 / WR 67.8% / n=425) survives — `multi_asset_cot` is only one contributor
- Keep `multi_asset_cot` emitting at **0% sizing** for surveillance / paper-pilot. Kill-question is sizing-eligibility, not emission-eligibility.

## Per-trade min-pnl gate spec (proposed)

```python
MIN_NET_PNL_BPS_BY_CLASS = {
    "CRYPTO": 25,    # ~3x typical 8bp spread
    "EQUITY": 15,    # ~3x typical 5bp spread
    "ETF":    12,    # ~3x 4bp
    "COMMODITY": 36, # ~3x 12bp (futures spreads)
    "FOREX":  3,     # ~3x 1bp
    "BOND":   18,    # ~3x 6bp
}
```

Gate: reject if `(avg_win * win_rate - avg_loss * (1-win_rate)) * 100 < MIN_NET_PNL_BPS_BY_CLASS[asset_class]`.

CT=F current: `(6.4 * 0.94 - 3 * 0.06) * 100 = 583 bp expectancy` but on a 4.7bp average win that's already net of nothing — the gate needs to operate on **net** pnl (after slippage), not gross. After 12bp r/t: `(−5.62 * 0.94 - 15 * 0.06) * 100 = −618 bp expectancy`. Fails.
