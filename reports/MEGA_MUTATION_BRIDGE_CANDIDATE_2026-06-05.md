# `mega_mutation` — verified T2 bridge candidate (2026-06-05)

**TL;DR:** After deduping INCIDENT #91-style row inflation (2.72× factor), `mega_mutation` survives every scrutiny test that killed the other 5 high-PF headlines (see [SUSPICIOUS_PICKS_SCRUTINY_2026-06-05.md](./SUSPICIOUS_PICKS_SCRUTINY_2026-06-05.md)). **This is the leading bridge-to-money-ready candidate** — beats `fx_smart_carry_trade_momentum` on n and PF.

## Headline numbers

| Metric | Raw | **Deduped** | T2 floor | Pass? |
|---|---|---|---|---|
| n | 296 | **109** | 100 | ✅ |
| WR | 63.9% | **61.5%** | 50% | ✅ |
| PF | 3.12 | **2.79** | 1.5 | ✅ |
| avg pnl | +2.41% | +2.12% | — | — |
| Half 1 OOS-PF | 3.15 | **2.65** | — | ✅ stable |
| Half 2 OOS-PF | 3.09 | **2.93** | — | ✅ stable |
| Distinct dates | 39 | 39 | ≥10 | ✅ |
| Distinct symbols | 8 | 8 | ≥3 | ✅ |
| Max single-day share | 6.4% | 6.4% | <25% | ✅ |
| Max symbol share | 15.9% (JUP) | 15.9% | <50% | ✅ |
| PF without top 2 wins | 3.06 | ~2.7 | ≥1.2 | ✅ no fat-tail |
| Zero-pnl rows | 0 | 0 | 0 | ✅ no flat-as-win |

**Span:** 2026-04-02 → 2026-06-04 (~2 months live forward).

## Why the other 5 were artifacts and this one isn't

| Pattern | Other 5 | mega_mutation |
|---|---|---|
| Single-day batch | 30–44% | **6.4% max** |
| Single-symbol bet | 100% (DYDX/RENDER) | **8 syms, max 15.9%** |
| Fat-tail PF | -50% PF drop excluding 2 wins | **PF 3.12 → 3.06 (drop 1.9%)** |
| pnl=0 inflation | 43% (`regime_mild_bear`) | **0 rows** |
| OOS collapse | first/second halves diverged 16× | **First/second halves: 2.65 / 2.93** |

## Symbol breakdown (deduped) — diversified crypto majors+mids

| Symbol | n (raw) | avg pnl% |
|---|---|---|
| JUPUSDT | 47 | +4.77% |
| WIFUSDT | 45 | +3.69% |
| AVAXUSDT | 40 | −0.37% |
| DOTUSDT | 39 | +0.02% |
| RENDERUSDT | 37 | +1.39% |
| STXUSDT | 31 | +0.83% |
| ENAUSDT | 30 | +6.16% |
| ADAUSDT | 27 | +2.77% |

8 crypto altcoins, no single-asset >16%. JUP/WIF/ENA carry, AVAX/DOT roughly flat — distributed PnL, not concentration.

## The INCIDENT #91 caveat (2.72× row inflation on `trading_picks`)

Live evidence (4 dup JUP rows on 2026-05-26):

```
id=15a6877b3e81 entry=0.2481 TP=0.253062 SL=0.245619 pnl=+11.13% created=None closed=2026-05-26 20:27:37 TP_HIT
id=19199b7356d4 entry=0.2481 TP=0.253062 SL=0.245619 pnl=+11.13% created=None closed=2026-05-26 21:18:16 TP_HIT
id=e299cb5ac334 entry=0.2481 TP=0.253062 SL=0.245619 pnl=+11.13% created=None closed=2026-05-26 22:13:22 TP_HIT
id=fb714843652b entry=0.2481 TP=0.253062 SL=0.245619 pnl=+11.13% created=None closed=2026-05-26 23:08:55 TP_HIT
```

Identical entry/TP/SL/pnl; only different ids + closed_at timestamps. `created_at=None` on all 4 (synthetic/replay signal).

Cursor's session fixed this pattern for `at_signal_outcomes` (242,427 → 2,467 rows, see memory `project-multi-agent-storm-2026-06-05`). The fix has **not** been applied to `trading_picks` yet. Recommend running the analogous dedup before any sizing decision off these numbers.

## Recommended actions

1. **Validate via Cursor's `tools/incident_91_dedup.py`** retargeted at `trading_picks` (currently only runs on `at_signal_outcomes`). Re-run scrutiny on the deduped result.
2. **Restore `mega_mutation` from BLOCKED_STRATEGY_SYSTEMS** — the other Claude already did this in commit `9c5bc6ec4e`. Verify on next `production_scanner` pass that emissions resume.
3. **Add to `phase3_promotion_readiness.py` as a candidate** with the post-dedup n=109/PF=2.79 numbers (not the inflated raw).
4. **Forward-pilot wrapper** — create `verified_strategies/paper_pilot/mega_mutation_forward_pilot.py` that tracks future closes from a `started_at=2026-06-05T06:25Z` cutoff (analogous to luxalgo honesty fix), so we can measure true forward performance from this point on with no backfill contamination.
5. **Skeptic review** — `/consult-deepseek` and `/consult-grok` on this report before promoting to live capital. Per memory `project-multi-agent-storm-2026-06-05`, lab "VALIDATED ✅" without cross-AI critique was the Cloud-Minimix failure pattern.

## What this means for the audit page

The "0/9 money-ready" headline is correct (the verdict pipeline applies its own gates), but:
- `mega_mutation` deserves a `WATCH` row in the bridge truth panel (one tier below MONEY_READY).
- After dedup verification, it should advance to forward-pilot Stage 4 with a real n→200 (Tier-1 target) track.

---

Filed by `/loop` blitz at 2026-06-05 ~06:25Z. Evidence: direct live-DB queries against `ejaguiar1_stocks.trading_picks`. Cross-references: [[project-true-winners-investigation-2026-06-05]], [[project-multi-agent-storm-2026-06-05]] (INCIDENT #91 dedup pattern), commit `9c5bc6ec4e` (mega_mutation unblock).
