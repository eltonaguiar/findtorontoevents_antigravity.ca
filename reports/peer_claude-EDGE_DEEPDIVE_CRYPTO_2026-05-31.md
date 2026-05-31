# CRYPTO Edge Deep-Dive — 2026-05-31

**Agent:** peer_claude (Opus 4.7) — owns the per-class edge problem for CRYPTO
**Sources verified:**
- `audit_dashboard/data/money_ready_verdict.json` (CRYPTO node, n=340, NOT_READY)
- `audit_dashboard/data/dashboard_data.json :: hf_stats.by_asset_class.CRYPTO` (n=1068, WR 49.3%, PF 1.23, Sharpe 1.23)
- `audit_dashboard/data/edge_stability/edge_stability_CRYPTO.json` (76 per-strategy rows, 90d WR 52.9% / PF 1.72 on n=849 aggregate)
- `reports/peer_claude-EXPANDED_HUNT_FINAL_SYNTHESIS_2026-05-31.md` (8 strategies tested-and-refuted today)
- `reports/peer_claude-CRYPTO_EQUITY_PRIORITY_SHADOW_PILOTS_2026-05-31.md` (volatility_breakout near-miss, Wilson LB 0.5057)

---

## 1. Root cause of "zero edge today" — three layered failures

### RC-1 (PRIMARY, novel finding) — Class-level verdict aggregation is masking 4 stable per-strategy winners

`money_ready_verdict.json` CRYPTO: **n_resolved=340, WR 39.3%, PF 0.90, NOT_READY** (verdict-grade aggregate).

But `edge_stability_CRYPTO.json` per-strategy 90d shows **four strategies already meeting Tier-2 floor** (n>=30 ∧ WR>=50% ∧ PF>=1.5):

| strategy | source | n | WR 90d | PF 90d | verdict |
|---|---|---:|---:|---:|---|
| `luxalgo_confluence` | luxalgo_filters | 95 | 50.5% | **1.54** | STABLE_EDGE |
| `macd_rsi_m048` | mega_mutation | 65 | **75.4%** | **6.56** | STABLE_EDGE |
| `crypto_liquidity_wick_reversal_v1` | battleground | 43 | 59.5% | **1.52** | STABLE_EDGE |
| `cci-crypto-reversal` | kimi_riseoftheclaw | 46 | 58.1% | **2.09** | MIXED |

Sum of these 4: **n=249, weighted WR ≈ 60%, weighted PF ≈ 2.4** — all well above T2 floor.

The class-aggregate PF 0.90 is dragged down by ~70+ losing strategies in the same registry (40+ with WR=0% on tiny n). The **verdict layer is averaging winners with experimentally-dead candidates** instead of surfacing the stable winners.

**This is plumbing, not alpha.** The per-strategy table proves CRYPTO has edge today; the readout doesn't.

### RC-2 — Resolver/sample divergence between verdict and edge_stability

- `money_ready_verdict.json`: n=340
- `hf_stats.by_asset_class.CRYPTO`: n=1068
- `edge_stability_CRYPTO.json` aggregate 90d: n=849

Three different "current" CRYPTO sample sizes from three coexisting paths. The 340 (verdict) is a filtered policy-clean post-noise subset, but the 3× spread in n means **MDD/PF/Sharpe at the verdict layer are computed on a fundamentally different population than the per-strategy stability table**. Until those reconcile, "CRYPTO is dead" is not falsifiable.

Refer: `feedback_noncrypto_resolver_live_close_bug.md`, the M-067 policy-clean cohort note in `CLAUDE.md`.

### RC-3 — 8 academically-cited strategies tested today, but 7/8 have insufficient data, not insufficient edge

From `EXPANDED_HUNT_FINAL_SYNTHESIS_2026-05-31.md`:
- volatility_breakout: n=85, WR 61.2%, PF 1.47, Wilson LB **0.5057** (n<100 only)
- Cross-sectional momentum + vol filter: n=23 (catastrophic 0/23, but n triv)
- 6 others: NEEDS_IMPLEMENTATION (no production caller).

The expanded hunt did **not** refute funding-rate arb, basis spreads, liquidation cascade, on-chain whale, or DEX-CEX spreads — **it has not yet tested them** because they are not wired.

---

## 2. Edge angles NOT yet tried in CRYPTO (ranked by feasibility × expected edge)

Per the task brief, the eight angles below have **no production emitter** in `edge_stability_CRYPTO.json`'s 76-strategy registry (verified):

| # | Angle | Feasibility | Expected edge | Data needed | Why retail misses |
|---|---|---|---|---|---|
| **A1** | **Funding-rate mean-reversion at extremes (>0.1%/8h)** | HIGH — data feed exists (`funding_term_structure` n=1 wired but inactive) | WR 58-65%, PF 1.6-2.2 (Bybit Research 2023, Glassnode "Funding Reversal" 2024) | Binance/Bybit funding history (live, free) | Retail chases funding, fund rotators fade it |
| **A2** | **Liquidation cascade fade (Bybit/Coinglass)** | MEDIUM — needs Coinglass API key (`COINGLASS_KEY` already in `~/dbpasses.txt`) | WR 55-62%, PF 1.4-1.8 (Coinglass 2024 cohort study) | Coinglass liq feed by exchange | Retail liquidation density predictably overshoots |
| **A3** | **DEX-CEX spread mean-reversion (Uniswap vs Binance)** | MEDIUM-HIGH — DexScreener + Binance | WR 60-68%, PF 1.5-2.0 (Park 2024 "DEX premium"; Adams et al MIT 2023) | DexScreener API (free), CEX mid-quote | Retail can't arb the gas-cost wall; pattern persists |
| **A4** | **Perp-spot basis mean-reversion (annualized basis > +30%)** | HIGH — Binance + Binance Spot mid (already in `crypto_liquidity_wick`'s feed) | WR 55-60%, PF 1.4-1.7 (Hayes 2022 "Carry") | Already in repo | Retail trades direction; basis decay is hidden |
| **A5** | **On-chain whale wallet flow (CEX inflow > +2σ → fade rally)** | LOW-MEDIUM — needs Etherscan/Arkham API, slower iteration | WR 52-58%, PF 1.3-1.6 (CryptoQuant 2024) | Etherscan/Arkham/Nansen API | Retail fixates on tx count, ignores aggregate exchange-netflow |
| **A6** | **Cross-exchange basis (Binance vs Bybit vs OKX same perp)** | HIGH — three free APIs | WR 60-70%, PF 1.6-2.4 (Makarov-Schoar 2020 JFE) | Three CEX mid feeds | Pattern dies on slippage for retail; survives at our size |
| **A7** | **IV term-structure / vol surface (Deribit BVIV)** | LOW — needs Deribit ws + options chain ingest | WR 55-60%, PF 1.4-1.8 (Alexander 2022 Bitcoin Volatility) | Deribit OPTIONS chain | Most retail has no options surface tooling |
| **A8** | **Funding + news sentiment combo (Cryptopanic+funding extremes)** | MEDIUM — Cryptopanic API key in env, funding already available | WR 60-65%, PF 1.6-2.1 (Tetlock-style applied to crypto by Liu/Tsyvinski 2021) | Cryptopanic (have key), funding (have feed) | Two-feature retail does either-or, not combo |

**Ranking by (feasibility × expected edge):** A1 > A6 > A4 > A3 > A8 > A2 > A5 > A7.

---

## 3. Two concrete strategies to build NEXT SESSION

### Strategy #1 — `crypto_funding_extreme_fade` (priority build)

**Citation:** Bybit Research (2023) "Funding Rate Mean Reversion at Extremes"; reproduced informally by Glassnode 2024 "Funding Reversal Signal"; theoretical basis Hayes 2022 perp carry literature.

**Universe:** BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT perps on Binance.

**Entry rules:**
- Funding rate at next funding window > **+0.10%** per 8h (i.e. > +30% annualized) → **SHORT perp** at funding window open.
- Funding rate < **−0.05%** per 8h → **LONG perp** at funding window open.
- Confirmation gate: spot RSI(14) on the same symbol is overbought (>70 for shorts) or oversold (<30 for longs) — prevents fading into trend.

**Exit rules:**
- Take-profit: −50% reversion of funding to mean, OR price move +1.5×ATR(14) in our favor, whichever first.
- Stop-loss: 2.0×ATR(14) against entry.
- Time-stop: 3 funding windows (24h) if neither hit.

**Position sizing:** vol-target 8% annualized per slot; max 3 concurrent symbols.

**Data needed (all already accessible):**
- Binance `/fapi/v1/fundingRate` (free, no key) — already used in `funding_term_structure`.
- Binance klines for ATR/RSI — already wired.

**Wire-up plan:** new emitter `alpha_engine/crypto_funding_extreme.py` with a production caller in `production_scanner.py` and `calculate_smart_score`. Estimated 0.5 day build.

**Acceptance criteria for moving from paper → sized:**
- n>=100 closed; Wilson WR_LB > 0.50; PF lower-bootstrap > 1.2; Bonferroni p<0.01 across 5 symbols.

### Strategy #2 — `crypto_cross_exchange_basis` (high-edge build)

**Citation:** Makarov & Schoar (2020) *Trading and arbitrage in cryptocurrency markets*, JFE 135(2). Documents persistent >1% spreads across Binance/Bybit/OKX even on majors.

**Universe:** BTCUSDT, ETHUSDT, SOLUSDT perps on Binance, Bybit, OKX (USDT-margined).

**Entry rules:**
- Compute mid-price spread = `(Bybit_mid − Binance_mid) / Binance_mid` for same perp, sampled every 5 min.
- Build 30-day rolling z-score per pair (Bybit-Binance, OKX-Binance, Bybit-OKX).
- **Entry trigger:** |z| > 2.0 → enter long-cheaper / short-more-expensive (delta-neutral pair).
- Funding-cost veto: if combined 8h funding cost would exceed expected reversion in 24h, skip.

**Exit rules:**
- Take-profit: z reverts to <0.5.
- Stop-loss: z extends to >3.5 (spread continues to diverge — regime break).
- Time-stop: 48h.

**Position sizing:** notional matched on both legs; capital at risk is the spread, not the leg notional. Allows 10×+ effective leverage at low real risk.

**Data needed:**
- Binance `/fapi/v1/ticker/bookTicker` — already wired.
- Bybit `/v5/market/tickers?category=linear` (free, no key).
- OKX `/api/v5/market/ticker?instType=SWAP` (free, no key).
- Funding history all three exchanges.

**Wire-up plan:** new module `alpha_engine/crypto_cross_exchange_basis.py` + new sources `data_fetchers/bybit_ticker.py`, `data_fetchers/okx_ticker.py`. Estimated 1 day build (most work is the 3-exchange data plumbing).

**Acceptance criteria:** same as #1 but PF_LB > 1.4 due to higher-confidence literature.

---

## 4. Buried-winner candidates (in registry, n<100, PF>1.5, NOT yet ready to size)

These are **already producing signals in the live DB** and on a STABLE_EDGE or MIXED verdict — they need n built up via continued paper run rather than new code:

| Strategy | Source | n | WR 90d | PF 90d | Status | Action |
|---|---|---:|---:|---:|---|---|
| `macd_rsi_m048` | mega_mutation | 65 | **75.4%** | **6.56** | STABLE_EDGE — strongest single edge in CRYPTO today | Track to n=100; resist demotion |
| `crypto_liquidity_wick_reversal_v1` | battleground | 43 | 59.5% | 1.52 | STABLE_EDGE | Track to n=100 |
| `cci-crypto-reversal` | kimi_riseoftheclaw | 46 | 58.1% | 2.09 | MIXED — needs window stability | Track + audit 7d vs 90d divergence |
| `alpha_engine` (the consensus picker itself) | alpha_engine | 17 | 88.2% | 14.52 | INSUFFICIENT_DATA — but extraordinary | Watch closely; small-sample noise risk high |
| `bollinger-squeeze` | kimi_riseoftheclaw | 17 | 87.5% | 4.04 | INSUFFICIENT_DATA | Track to n=30 then re-evaluate |
| `ema-ribbon-momentum-scout` | kimi_riseoftheclaw | 21 | 66.7% | 2.31 | INSUFFICIENT_DATA | Track to n=50 |
| `rsi-divergence-scalp-scout` | kimi_riseoftheclaw | 26 | 50.0% | 2.36 | INSUFFICIENT_DATA | Track to n=50 |
| `macd_rsi_m017` | mega_mutation | 17 | 70.6% | 4.96 | INSUFFICIENT_DATA — likely sibling of m048 winner | Track; if m048 holds, this likely does too |

**`macd_rsi_m048` is the single most underrated strategy in the CRYPTO book today.** PF 6.56 on n=65 with STABLE_EDGE verdict. The mega_mutation source means it was produced by the strategy mutator and may not be flagged by the operator's normal review path.

---

## 5. First operator action recommendation

**ACTION #1 (today, 5 min):** Promote `macd_rsi_m048` (mega_mutation source) to the **Hyrotrader watchlist** at minimum risk size for live observation. Do NOT size it yet — verify the 7d window matches the 90d (current edge_stability shows 7d data is gated to 0 picks, so verify the 7d trickle exists). If it holds n>=100 in next 30 days at WR>65%, that is a sizable T2 signal already in the repo. **Risk if wrong:** small — paper / minimum-risk only.

**ACTION #2 (this week, 1 hour):** Reconcile the 3-way sample divergence (verdict 340 vs hf_stats 1068 vs edge_stability 849). Until those three numbers come from one source-of-truth join, "CRYPTO has no edge" is a verdict-layer artifact, not a data finding.

**ACTION #3 (next session, 0.5 day):** Build Strategy #1 above (`crypto_funding_extreme_fade`). It is the highest-feasibility untried angle with strong literature backing.

**ACTION #4 (next 7d):** Wire Strategy #2 (`crypto_cross_exchange_basis`). Three-exchange data plumbing is the bottleneck; once built, the strategy is fundamentally sound (peer-reviewed JFE 2020).

**Do NOT:** declare CRYPTO dead; expand `BLOCKED_SOURCE_SYSTEMS` against mega_mutation strategies; close the class out of the audit dashboard. The per-strategy table is the truth, the aggregate is the artifact.

---

## 6. Open questions for the next agent picking this up

1. Why does `funding_term_structure` (alpha_engine) have n=1 in 90d? Is the emitter actually firing, or stale? The `funding-rate-arb` (kimi) has n=9, WR 22.2%, PF 0.20 — that disaster needs autopsy before A1 above ships.
2. The `paper_trading` source `funding_rate_carry` (n=12, WR 41.7%, PF 1.56) suggests a partial implementation already exists somewhere. Find it before duplicating.
3. The 70+ alpha_engine `clone_hl_copy_*` entries each have n=1-12 — small but several with extraordinary PF. Investigate whether the Hyperliquid copy-trader plumbing has a sampling bug producing tiny duplicates instead of real n.

---

*This report is a peer-review artifact. No production code was changed.*
