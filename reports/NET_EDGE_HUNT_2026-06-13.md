# Net-of-cost edge hunt — 2026-06-13 (loop iteration 3)

**Question:** after the FOREX winner failed the cost test (gross PF 3.13 → net 0.76), is there ANY net-positive edge in the live book? **Answer: barely — only one structurally-grounded candidate (`leveraged_etf_decay`), and it's marginal.**

## Method
Live `trading_picks`, 2026+, resolved, classes FOREX/EQUITY/ETF/BOND/INDEX (CRYPTO/COMMODITY = peer's lane). Dedup per (source, strategy, symbol, day). 5bp win-threshold. Per-class round-trip cost applied to every trade: FOREX majors 3bp / JPY 6bp, EQUITY/ETF/INDEX 4bp, BOND 3bp. Filter n≥50, net PF≥1.2.

## Result — only 3 of all non-crypto strategies clear net PF≥1.2 (n≥50)

| Class | Source / strategy | n | gross PF | **net PF** | decWR | avg winner | OOS net | verdict |
|---|---|---|---|---|---|---|---|---|
| ETF | `leveraged_etf_decay` | 69 | 1.30 | **1.24** | 58% | 1.64% | IS 1.30 / **OOS 1.16** | **lead net-positive candidate** |
| EQUITY | `stocks_ema_golden_cross` | 57 | 2.24 | 1.98 | 60% | 0.80% | IS 3.53 / **OOS 0.91** | ❌ OVERFIT (OOS collapses) |
| EQUITY | `smart_money_accumulation` | 76 | 1.46 | 1.37 | 38% | 2.04% | unstable (IS 0.29 / OOS 4.85 earlier) | ❌ unstable, low WR |

## The lead: `leveraged_etf_decay` (SHORT)

- **Mechanism is real and structural:** shorts leveraged INVERSE ETFs (JDST, SOXS, LABD) which suffer volatility decay (daily-rebalance drag) — a documented, persistent phenomenon, not a data fluke.
- **Survives cost** where FOREX didn't: avg winner ~1.6% vs FOREX ~0.2-0.3%, so a 4bp cost barely dents it (gross 1.30 → net 1.24).
- **OOS-stable net:** IS net 1.30 / OOS net 1.16 — holds, marginally.
- **Caveats:** n=69 (<100, "developing" not promotable); only 23 active days; **concentrated in 3 symbols** (JDST/SOXS/LABD ~33% each — high HHI). 100% SHORT.

## The principle (confirmed twice now)
**Only higher-amplitude edges survive transaction cost.** The FOREX consensus edge (huge gross PF, tiny winners) dies at retail cost; the leveraged-ETF-decay edge (modest gross PF, ~1.6% winners) survives. **Future winner-hunts should screen on net PF and average winner size, not gross PF.**

## Recommendation
- `leveraged_etf_decay` is a credible **Tier-3 net-positive candidate** worth a forward-paper pilot — but **expand the universe first** (add TQQQ/SQQQ, SOXL/SOXS, TZA, YANG, etc.) to break the 3-symbol concentration, since the decay mechanism applies to the whole leveraged-ETF universe. Then re-measure net PF on the broader set before piloting.
- Do NOT pilot at n=69 / 3-symbol concentration as-is.
- This does NOT change the FOREX verdict (still gross-only).

Reproduce: per-class net hunt in this session; cost model matches `tools/forex_long_pilot_tracker.py`.
