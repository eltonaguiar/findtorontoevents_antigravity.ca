# PLAN_INSIGHTS — FABLE — June 12 2026, 11:37 PM EDT

**Headline: a genuine money-ready-grade FOREX candidate exists at the STRATEGY level — `non_crypto_consensus` (PF 2.02, holds out-of-sample). It has been invisible because the class-aggregate (pf_registry FOREX PF 0.55) is dragged down by losing sibling sources.**

Reproduce everything here: `DB_PASS_STOCKS=... python3 tools/validate_forex_consensus_edge.py --category forex --min-n 60`

---

## 1. The winner

| Source / strategy | n (deduped, clean) | PF | IS-half PF | OOS-half PF | decisive WR | WR 95% CI | PF − top winner | top symbol | active days |
|---|---|---|---|---|---|---|---|---|---|
| **non_crypto_consensus** | **303** | **2.02** | **2.01** | **2.03** | **63.3%** (81W/47L) | **[55%, 71%]** | **1.97** | EURJPY=X 14% | **46** |

Why this clears the bar where everything else has failed:

- **Tier-1 on Profit Factor (≥2.0), Tier-2 on Win-Rate (≥50%) and n (≥100).** Per `docs/PERFORMANCE_CHARTER.md`.
- **Survives the time-split** that has killed every prior false winner: IS-half PF 2.01, OOS-half PF 2.03 — essentially identical. Not a 6-day snapshot — **46 active trading days over a ~50-day span**.
- **Outlier-robust.** PF with the single largest winner removed is still 1.97; winsorized at ±2% it's still 1.96. The wins are realistic 0.2–0.3% FX moves; **zero >2% rows** (so it is NOT the JPY pip-vs-percent corruption that has faked FOREX edges before).
- **Direction-signs clean:** 0/200 sampled rows had a pnl sign that disagreed with `(exit−entry)·direction` (rules out the sign-flip contamination quarantined elsewhere).
- **Contamination-filtered:** excludes hold < 60 min (same-stamp + "time-travel" backfill rows). The per-symbol-day dedup had already removed the batch 0-hour dupes — applying the explicit filter changed n by 1 (304→303), confirming the edge is not artifact-carried.
- **Mechanism is sound:** `non_crypto_consensus` only emits when ≥2 independent systems agree on symbol+direction. Consensus-filtering is a legitimate, non-overfit edge source.

The decisive-WR framing matters: of 303 deduped picks, 177 are TIME_EXIT near-flat (|pnl| < 5bp) and excluded from WR; of the **127 that moved decisively, 63% are wins** (binomial p ≈ 0.006 vs coin-flip).

## 2. Why it was hidden — reconciliation with "FOREX FAILS"

`pf_registry` / `money_ready_verdict` report FOREX at **PF 0.55 — FAIL**. That is the **class aggregate**, which sums every FOREX source including net-losing ones. The edge lives in **one source**, not the class. This is the `[[feedback-concentration-strategy-not-engine]]` lesson in the other direction: **measure edge at the strategy level, not the asset-class level.** A failing class can contain a winning strategy, and averaging them together buries it.

Three measurement disciplines were required to see it, all of which the aggregate view skips:
1. **Dedup per (strategy, symbol, day)** — FOREX raw was 15,084 rows → **1,853 deduped (88% were batch duplicates).** Un-deduped numbers are meaningless.
2. **5bp percent win-threshold** — without it, near-flat TIME_EXIT picks count as "wins" and inflate WR.
3. **Contamination filter** (hold ≥ 60 min) — drops resolver/backfill artifacts.

## 3. Ranked FOREX shortlist (contamination-clean, deduped, n≥60)

| Rank | Source / strategy | n | PF | IS / OOS | decisive WR | verdict |
|---|---|---|---|---|---|---|
| 1 | **non_crypto_consensus** | 303 | **2.02** | 2.01 / 2.03 | 63% | **LEAD — T1-PF / T2 — forward-pilot now** |
| 2 | myfxbook_retail_contrarian | 262 | 1.74 | 1.32 / 2.89 | 56% | T2, HOLDS — secondary pilot |
| 3 | ig_contrarian_sentiment | 379 | 1.26 | 1.28 / 1.25 | 55% | T3 but most STABLE (IS≈OOS), biggest n |
| — | forex_rsi2_mean_reversion | 292 | 1.60 | **1.03** / 3.50 | 57% | REJECTED — IS-half collapses; edge is one-sided in time (prior memory flag refuted) |
| — | cta_cross_asset_tsmom | 89 | 1.54 | 1.70 / 1.46 | 59% | HOLDS but n<100 (developing) |
| — | fx_smart_carry_trade_momentum | 84 | 1.32 | **0.14** / 6.70 | 31% | REJECTED — IS-half is a loser; all edge in OOS tail |

**Note:** the prior session memory flagged `forex_rsi2` (daily) as "the lead (70%/2.44)". The rigorous contamination-clean + time-split test **refutes** that — its early-half PF is 1.03 (a coin-flip), so its apparent edge is concentrated in one time window, not durable. `non_crypto_consensus` is the real lead.

## 4. Other classes (this pass — FOREX/EQUITY/ETF only; CRYPTO/COMMODITY are a peer's lane)

- **EQUITY:** no clean Tier-2. Best is `stocks_rsi2_pullback` (n=307, PF 1.30, IS 1.18 / OOS 1.41 — HOLDS but marginal T3). `stocks_ema_golden_cross` looks great (PF 2.24) but **collapses OOS** (IS 4.09 / OOS 0.92) — classic overfit, do not size.
- **ETF:** no Tier-2 at n≥100. `etf_sector_momentum` (PF 2.24, IS 2.64 / OOS 1.98) is promising but n=40 → "developing", not promotable yet.

## 5. Honest caveats (do not over-claim)

1. **Daily first-touch resolver, not intrabar.** Non-crypto picks did **not** get the intrabar OHLC replay (only ~19 of 19,211 non-crypto rows have `intrabar_status`). The universal_v2 daily first-touch is conservative (SL-first) and trustworthy per `[[project-resolver-keyspace-gap-2026-06-09]]`, but a true intrabar replay would be the gold standard and is the recommended next hardening step.
2. **Recent cohort.** The 303 picks span ~50 days in 2026 — strong, but a **forward pilot** is still required to confirm the edge persists on un-seen days (this is the whole point of the Stage 3 bridge).
3. **Single class, single source.** Concentration/diversification risk; this is a pilot candidate, not a portfolio.

## 6. Recommended action (the bridge, per `docs/MONEY_READY_MASTER_LOOP_2026-06.md`)

1. **Do NOT blanket-block the FOREX class.** Any class-level FOREX down-sizing must **exempt `source_system=non_crypto_consensus`** — it is the strongest money-ready candidate the project has. (Broadcast P0 to peers via /dropchat-multipc.)
2. **Promote `non_crypto_consensus` (FOREX) to Stage 3 — WATCH / forward-paper pilot** at 0.1–0.5% notional, drawdown-halted, accrue forward n→100. Secondary pilot: `myfxbook_retail_contrarian`.
3. **Harden:** run the intrabar replay on these FOREX sources to confirm PF survives first-touch SL ordering before any real sizing (Stage 4 gate).
4. **Re-run this audit weekly** via `tools/validate_forex_consensus_edge.py` to watch IS/OOS stability as forward n grows.

## 7. Artifacts

- `tools/validate_forex_consensus_edge.py` — read-only reproducer (creds from env / `dbpasses.txt`, never hardcoded).
- Source table: `ejaguiar1_stocks.trading_picks` (50,905 rows; FOREX resolved 2026+ = 15,126 raw, 1,853 deduped).
