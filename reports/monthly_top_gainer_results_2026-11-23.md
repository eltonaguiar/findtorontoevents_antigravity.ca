# H-239 / H-240 — monthly top gainers, run at the pre-registered bar

**Run:** 2026-11-23 · **Pre-registration:** `plans/2026-11-23-prereg-H-239-H-240-monthly-top-gainer.md`
(filed before any run) · **Tool:** `tools/monthly_top_gainer.py` · **Artifact:**
`reports/h239_h240_monthly_top_gainer_2026-11-23.json`

Both classes now **clear the observation bar** that was fixed in advance — ≥ 48 scored months and
≥ 15 names of breadth — so these are admissible verdicts, not data gaps.

## H-240 — EQUITY, 118-name frozen universe

| metric | value |
|---|---|
| scored monthly periods | **68** (bar 48) |
| breadth min / median | 115 / 118 |
| mean excess bp per month vs universe mean | **+67.61** |
| 95% CI (block 3, 4,000 resamples) | **[−30.76, +187.48]** |
| hit rate (book > universe) | 52.9% |
| mean rank-IC | **+0.0083** |
| gross / net annualised | 24.54% / 24.40% |
| cost survival (net ÷ gross) | 0.994 |
| **verdict** | **REFUTED** — CI includes zero |

## H-239 — CRYPTO, 38 USD pairs (of 44 requested; the rest returned no bars)

| metric | value |
|---|---|
| scored monthly periods | **69** (bar 48) |
| breadth min | 29 |
| mean excess bp per month | **+41.28** |
| 95% CI | **[−247.81, +361.74]** |
| hit rate | 60.9% |
| mean rank-IC | **+0.1431** |
| gross / net annualised | 44.04% / 40.67% |
| cost survival | 0.923 |
| name-periods rejected by the integrity guard | 12 |
| **verdict** | **REFUTED** — CI includes zero |

## What the two verdicts say together

1. **The horizon was never the problem.** Moving from daily (H-237) to weekly (H-238) to monthly cut
   cost drag to almost nothing — crypto keeps **92.3%** of gross at 20 bp, equity **99.4%** at 0.98 bp
   — and the excess still cannot be distinguished from zero. Every cost-based hope for this family is
   now closed off: the drag is gone and the edge still isn't there.
2. **Crypto shows weak information and no tradeable separation.** IC **+0.143** is the largest
   cross-sectional signal recorded anywhere in this sweep, and the top decile still has a CI spanning
   −248 to +362 bp per month. That combination means the ranking has some content but the *extreme*
   names it selects have dispersion so wide that a 3–4 name book cannot express it. Information ≠
   expression.
3. **Equity monthly is the cleanest null in the family** — IC 0.0083 is essentially zero-rank, on 68
   independent-ish months, with the whole cost question removed.

## A bug this run caught (and did not paper over)

The first pass produced a mean excess of **−19,783 bp/month**, which is arithmetically impossible for
a long-only book of close-to-close ratios (the floor is −100%). Cause: 12 bad price prints — split-like
jumps and stale quotes in the Yahoo crypto series. The guard now **rejects and counts** any name-period
outside (−95%, +500%) instead of silently winsorising: 12 rejected for crypto, 0 for equity, and the
count is in the artifact. Without the guard the crypto verdict would have been a fake, spectacular REFUTED.

## Limits, stated

- Both universes are **names liquid today**. A FAIL is therefore the strong direction (survivorship
  inflates long-only results); a PASS here would have needed the `WEAK_PASS` label. We got fails, so no
  label is needed.
- Crypto panel spans 2020-11-23 → 2026-11-23 (69 months); equity 2020-11-23 → 2026-11-20 (68).
- Thresholds, features, signs, benchmark and cost are exactly as registered; the only thing added after
  the fact is the integrity guard, which can only remove bad data, never change a sign.
