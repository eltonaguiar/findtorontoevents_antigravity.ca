# Per-asset-class analysis

**Source:** live payload `picks.recent_closed`, n=3,500, closed 2026-02-21T07:08Z → 2026-11-14T18:56Z,
142 distinct symbols. Reproduce with `04_verification/per_class_stats.py`.

**Scope caveat:** this is a 9-month window capped at 3,500 rows, not the full ledger. The payload's
own full-ledger aggregate (`performance.by_asset_class`) reports CRYPTO 4,945 closed at PF 0.91 and
FOREX 82 closed at PF 0.48 — same sign, similar magnitude. The conclusion does not depend on the window.

## 1. Headline statistics

| Class | n | WR | PF | mean | median | total | t | sign-test p | top-5 share of gross profit |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| CRYPTO | 1,966 | 39.3% | 0.768 | −0.426 | −1.282 | −837.8 | −4.84 | <0.001 | 2.6% |
| EQUITY | 738 | 47.0% | 1.154 | +0.323 | −0.726 | +238.3 | 1.52 | 0.122 | 6.0% |
| ETF | 567 | 44.3% | 1.036 | +0.040 | −0.730 | +22.9 | 0.34 | 0.007 | 7.7% |
| FOREX | 187 | 39.0% | 0.634 | −0.155 | −0.274 | −29.0 | −2.29 | 0.024 | 22.4% |
| BOND | 35 | 37.1% | 0.586 | −0.221 | −0.753 | −7.7 | −1.47 | 0.176 | 56.4% |
| COMMODITY | 7 | 42.9% | 0.604 | −0.598 | −1.167 | −4.2 | −0.53 | 1.000 | 100% |
| **ALL** | 3,500 | 41.7% | 0.895 | −0.176 | −0.938 | −617.5 | −2.53 | <0.001 | 2.0% |

Notes that change how these read:

- **Median is negative in every class including the two that make money.** The typical trade loses;
  the total is positive only because wins are larger. That is a real property of trend-following
  equity picks, not an error, but it means drawdown sequencing will feel worse than the total implies.
- **ETF's win rate is significantly *below* 50%** (p=0.007) yet PF > 1. Fee structure, not skill:
  avg win 2.64 vs avg loss 2.02.
- **BOND and COMMODITY are noise, not evidence.** In BOND the top 5 winners are 56% of gross profit;
  in COMMODITY 100% (n=7). Neither can support a conclusion in either direction.
- **Concentration is not the problem for the big classes** (CRYPTO top-5 = 2.6%). The loss is broad
  and systematic, not one bad trade.

## 2. Split-half stability (by `closed_at`)

| Class | 1st half PF | 2nd half PF | direction |
|---|---:|---:|---|
| CRYPTO | 0.952 | 0.608 | decay |
| EQUITY | 1.342 | 0.977 | decay to breakeven |
| ETF | 1.090 | 0.971 | decay to breakeven |
| FOREX | 0.931 | 0.507 | decay |

**No class improves.** EQUITY and ETF were mildly profitable in the first half and fell to breakeven
in the second — consistent with a regime change, a cost increase, or decay of an initially-selected
strategy set. Any claim of a stable per-class edge has to explain this.

## 3. Exit mix drives PF, which is why PF comparisons across classes mislead

`exit_reason` is mechanically tied to outcome, so class PF is largely a function of *how trades were
closed*, not how good the entries were:

| Exit | n | WR | mean | total |
|---|---:|---:|---:|---:|
| TP_HIT | 873 | 99.9% | +4.001 | **+3,493.1** |
| SL_HIT | 1,468 | 1.0% | −2.974 | **−4,366.4** |
| TIME_EXIT | 517 | 60.7% | +0.467 | +241.2 |
| FORCE_CLOSED | 615 | 40.5% | +0.019 | +11.9 |
| UNKNOWN / EXPIRED | 27 | — | — | +2.6 |

The class-level differences are largely exit-mix differences — e.g. EQUITY's TIME_EXIT bucket is
n=220, WR 61.4%, **PF 1.988**, and ETF's is n=147, WR 63.9%, **PF 3.062**. Time-based exits are the
best-behaved bucket in both classes; the stop-loss bucket is where classes die.

**Implication:** PF measured on this ledger cannot rank strategies across classes. Rank on R-multiples.

## 4. R-multiples — the honest per-class measure

Planned risk = |entry − stop| / entry. R = realized pnl ÷ planned risk.

| Class | planned risk (med) | planned R:R (med) | mean R | avg loss (R) | % trades worse than −1R | % trades ≥ +1R |
|---|---:|---:|---:|---:|---:|---:|
| CRYPTO | 1.50% | 1.69 | **−0.266** | **−1.74** | 55.4% | 33.9% |
| EQUITY | 5.00% | 1.60 | +0.046 | −0.84 | 14.8% | 18.0% |
| ETF | 3.00% | 1.67 | +0.016 | −0.69 | 9.5% | 14.6% |
| FOREX | 1.00% | 1.50 | −0.024 | −0.67 | 13.4% | 13.4% |
| BOND | 1.50% | 1.67 | −0.146 | −0.60 | 5.7% | 2.9% |

CRYPTO is the outlier in a way that names the problem precisely: **55.4% of crypto trades lose more
than the risk the system declared,** and the average loss is −1.74R. Every other class keeps losses
inside the declared risk (avg −0.6 to −0.8R). Crypto is also the only class with an average planned
risk under 1.5% — tight stops in a volatile asset, which is exactly where detection latency costs the
most.

## 5. Stop-fill verification (the mechanism)

| Class | stopped trades | exit == stop | exit ≠ stop | mean planned | mean realized | mean overshoot |
|---|---:|---:|---:|---:|---:|---:|
| CRYPTO | 773 | 70 | **703** | 1.919% | 2.990% | **+1.071pp** |
| EQUITY | 304 | 0 | 304 | 4.984% | 4.551% | −0.433pp |
| ETF | 262 | 1 | 261 | 2.953% | 2.260% | −0.694pp |
| FOREX | 104 | 36 | 68 | 1.096% | 0.751% | −0.344pp |

For crypto's mismatched rows, `pnl_pct` matches `exit_price` in 633 cases and `stop_loss` in 140,
and **neither in zero** cases. So the pnl arithmetic is correct; the fill price is genuinely beyond
the stop. Median price gap 0.324%, p90 4.43% — a long tail of badly-priced exits, consistent with
detection-on-poll rather than a resting order at the exchange.

EQUITY, ETF and FOREX overshoot *negatively* (they exit inside the stop), so this is a crypto-specific
execution defect, not a universal one.

## 6. Timeframe

| Class | Timeframe | n | WR | PF | total |
|---|---|---:|---:|---:|---:|
| CRYPTO | INTRADAY | 1,684 | 40.2% | 0.801 | −590.8 |
| CRYPTO | SWING | 243 | 28.4% | 0.457 | **−328.6** |
| CRYPTO | POSITION | 33 | 69.7% | **3.180** | **+74.4** |
| EQUITY | INTRADAY | 731 | 47.1% | 1.155 | +239.8 |
| ETF | INTRADAY | 557 | 44.5% | 1.050 | +31.3 |
| FOREX | INTRADAY | 117 | 43.6% | 1.028 | +0.9 |
| FOREX | SWING | 67 | 32.8% | 0.383 | −29.7 |

Two things worth testing further, both undersampled: CRYPTO SWING is the worst bucket in the entire
ledger (PF 0.457) and should be switched off immediately; CRYPTO POSITION is the only positive crypto
bucket (n=33, PF 3.18) and is too small to believe but large enough to justify a forward test.

Everything else is INTRADAY — meaning the system's stated horizons and its actual holding periods
have collapsed into one bucket, which is itself a finding: `trade_timeframe` is not discriminating.
