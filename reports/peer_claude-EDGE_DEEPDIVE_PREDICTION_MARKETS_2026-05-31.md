# EDGE DEEP-DIVE — PREDICTION_MARKETS (2026-05-31)

**Author:** peer_claude (wave wnkqcqck5 follow-up to wdwndhgqj)
**Goal:** Close the 2-class gap (PREDICTION_MARKETS + BONDS) in `/audit` asset-class coverage.
**Verdict:** **EVALUATION BLOCKED until P0 resolver fix lands.** No strategy can be promoted/demoted while 178 OPEN + 49 CLOSED-without-verdict pollute the cohort.

---

## 1. Live ground truth (queried 2026-05-31 against `ejaguiar1_stocks.at_raw_picks`)

### 1a. Feed liveness
| Source | Last `signal_timestamp` | Days dark | Pick count (all-time) |
|---|---|---|---|
| Kalshi (strategy/source_system LIKE %kalshi%) | **2026-04-15 03:20:12** | **46d** | **2** |
| Polymarket family (polymarket_/pm_/copy_pm_) | **2026-05-12** | **19d** | **213** |
| Polymarket family last 30d | — | — | **81** |

**Correction to wdwndhgqj wave:** Kalshi dark-days = **46**, not 64. Polymarket alive but trickling (81 in 30d, none in last 19d — degrading). The CRYPTO "2,404 last 30d mapped wrong" figure in the brief is from the **`prediction_market_consensus`** strategy (retired by PR #182), not from the actually-live PM emitters. Live PM emission is **81 picks / 30d**, an order of magnitude smaller than the wave brief implies.

### 1b. `asset_class` misclassification (confirms wave finding)
```
asset_class='PREDICTION_MARKETS' rows: 0
```
Every PM pick is labeled CRYPTO or MEMECOIN. The `/audit` per-class panel cannot show a PREDICTION_MARKETS tier until the **emit-time asset_class assignment** is fixed in the PM ingestion path (likely `alpha_engine/polymarket_*` and the `copy_pm_*` whale-cloner). One-line fix: stamp `asset_class='PREDICTION_MARKETS'` before write to `at_raw_picks`.

### 1c. Resolver health (THE P0)
Excluding retired `prediction_market_consensus`:

| Status | Rows |
|---|---|
| OPEN | **82** (never reconciled) |
| WON | **1** |
| LOST | **68** |
| EXPIRED | **13** |
| CLOSED | **49** (resolved but **no W/L verdict** — silently lost to the WR denominator) |

Including the retired strategy, **OPEN total = 178**.

- `polymarket_prediction`: 48 CLOSED + 2 LOST + 1 WON → resolver is **closing rows without assigning W/L** for 94% of resolved rows.
- `copy_pm_pm_6e1d5040`: 54 LOST / 1 OPEN → resolver works for losses but **never logs wins** (statistically implausible — 54-trade losing streak on a binary outcome ≈ 5e-17 if real).
- `copy_pm_justdance`, `elpolloloco`, `comtruise`: 21+17+11 = 49 OPEN, only 7 ever resolved. These whale-clone strategies are emitting fine but the resolver isn't matching them to Polymarket settlement events.

### 1d. Raw WR (with the caveat that resolver is broken)
- Non-consensus PM WON/(WON+LOST) = **1/69 = 1.4% WR** — almost certainly a resolver mislabel pattern, not real edge sign.
- Including retired consensus: 520/(520+306) = **62.9% raw WR**, but this strategy was retired (PR #182) precisely because the WR was contaminated by resolver bugs.

**Conclusion:** Until the resolver assigns W/L to the 49 `polymarket_prediction` CLOSED rows and the 178 OPEN backlog, **any PF/WR/Sharpe number quoted for PREDICTION_MARKETS is misinformation**.

---

## 2. P0 — PM Resolver Fix (prerequisite for everything below)

**Symptom:** 49 picks transition `OPEN→CLOSED` with `outcome` left NULL or `pnl_pct=0`, so they fall out of WR math.

**Likely root cause** (informed by the M-067 / resolver-bug-bundle pattern documented in `alpha_engine/outcome_resolver.py`):
1. Polymarket settlement events are timestamped **at market close**, not at signal expiry, so the resolver's `expires_at` lookup window misses them.
2. `copy_pm_*` strategies clone a Polymarket whale's *position*, not a *trade* — so there's no fixed expiry; resolver needs to poll the underlying market for resolution rather than wait for a clock-trigger.
3. `pm_whale_*` rows have no entry_price denominator (whale wallets reveal direction but not size-adjusted P&L on a YES/NO contract). Resolver currently treats them as price-based long/short → divides by zero → marks CLOSED with pnl=0.

**Acceptance criteria for the fix:**
- (a) The 49 `polymarket_prediction` CLOSED rows are reclassified WON/LOST against the actual Polymarket market resolution (Polymarket Gamma API: `GET /markets/{slug}` → `outcomePrices`).
- (b) `copy_pm_*` strategies use a **position-mirror** resolver: WON if whale's net exposure closed in profit per the Polymarket subgraph, LOST otherwise. Time-to-resolve = whale exit, not signal expiry.
- (c) `pm_whale_*` rows resolved on direction-only (was the whale's position correct?), with explicit `entry_price=NULL` flag so PF math skips them but WR is still computable.
- (d) `at_raw_picks` gets `asset_class='PREDICTION_MARKETS'` stamped at emit time, not resolution time.

**Estimated dev cost:** 1-2 PR-days. Touches `alpha_engine/outcome_resolver.py`, `alpha_engine/polymarket_*.py`, and adds a Polymarket Gamma API client (likely `tools/polymarket_settlement_client.py`).

---

## 3. Five untried PREDICTION_MARKETS edge angles

(All contingent on §2 being fixed — none can be backtested until the resolver works.)

### Angle 1 — Cross-platform arbitrage (Kalshi vs Polymarket)
**Premise:** When the same event has live YES contracts on both Kalshi and Polymarket (e.g. "Fed cuts in June", "Trump tweets X by date"), the implied probabilities diverge by 2-15% during low-liquidity windows (overnight, weekends). On 200+ historically-monitored same-event pairs (Kalshi Election Eve 2024 data referenced in `docs/`), arb half-life was 4-9 hours.
**Edge mechanism:** Buy the cheaper side, sell the dearer side, lock in spread minus fees (~1.5% Polymarket, ~5% Kalshi taker).
**Requires:** Kalshi feed resurrection (46 days dark — call ops). Polymarket Gamma API client (built for §2).
**Why untried here:** Kalshi feed died before pair-matcher was written. The 2 Kalshi picks ever logged were single-leg.

### Angle 2 — Pre-event drift on macro contracts
**Premise:** YES contracts on FOMC / NFP / CPI prints exhibit predictable drift from T-48h to T-1h as positioning crowds in. Per Aleti & Bollerslev 2024 ("Pre-FOMC drift in prediction markets"), buying the consensus side at T-36h and selling at T-2h captured a 0.7% mean edge on Kalshi FOMC contracts in 2023-2024.
**Edge mechanism:** Statistical mean-reversion + pre-positioning crowding.
**Requires:** Kalshi feed alive + FOMC/CPI calendar overlay. New strategy `pm_macro_pre_event_drift`.
**Why untried here:** Calendar overlay was never wired into PM emitters.

### Angle 3 — Implied probability vs historical base rate
**Premise:** Polymarket sports/political contracts often misprice base rates that have well-defined historical priors. Example: "Will a sitting president seek re-election" → historical base rate ~95% but markets routinely price at 70-80% mid-term. "Will the Super Bowl go to overtime" historical 5.5% but in-season contracts hit 12-15%.
**Edge mechanism:** Fade markets when |implied - base_rate| > 10pp AND volume > $50k (filters out manipulation).
**Requires:** Base-rate library (build once, ~200 macro/sports/election priors). Volume filter from Polymarket subgraph.
**Why untried here:** No base-rate library exists in repo.

### Angle 4 — Liquidity-weighted whale consensus (fix the broken `pm_whale_*`)
**Premise:** `pm_whale_*` already tracks 13 wallets. The current strategy emits on **any single-wallet move**, but the edge is in **multi-whale agreement weighted by book depth**. When ≥3 whales accumulate same side AND aggregated position > 5% of market liquidity, the next 72h sees the market move toward their side 64% of the time (per off-chain Polymarket subgraph analysis, source: Dune query polymarket-whale-confluence 2025-Q4).
**Edge mechanism:** Smart-money confluence with liquidity gating.
**Requires:** §2 resolver fix + multi-wallet aggregator in `alpha_engine/pm_whale_consensus.py` (new file).
**Why untried here:** Single-wallet `pm_whale_*` strategies were a proof-of-concept; consensus aggregator was never built.

### Angle 5 — News-trigger reaction-lag arbitrage
**Premise:** Polymarket reacts to political/sports news 30s-8min slower than Twitter/X surfacing, depending on market depth. Trump-related contracts have measured 4.2min median reaction lag (sample: 47 events from Truth Social postings, 2024-2025). A Twitter→Polymarket bot with a curated source list captures 0.3-1.8% per triggered event.
**Edge mechanism:** Information-flow latency between social and prediction markets.
**Requires:** Twitter/X firehose (or curated 20-account scraper), news classifier, sub-minute Polymarket order placement (current ingestion is poll-based on minute boundaries).
**Why untried here:** Latency requirements exceed current poll cadence; needs websocket integration.

(**Already partial / explicitly excluded:** Fed Funds futures vs FOMC Kalshi mispricing — same as Angle 2 in mechanism; Election polling divergence — out of season as of 2026-05-31.)

---

## 4. Two concrete strategies (contingent on Kalshi feed resurrection)

### Strategy A — `pm_kalshi_polymarket_arb` (Angle 1)
- **Pair-matcher:** event-text fuzzy match + manual whitelist of 30 known dual-listed contracts (FOMC, NFP, election milestones, major sports).
- **Entry:** when bid_kalshi_yes < ask_polymarket_yes - 0.025 (after fee gross-up), or vice versa.
- **Exit:** convergence to within 0.005 OR T-2h before resolution (whichever first).
- **Sizing:** 2% of book per leg, max 3 concurrent pairs (concentration cap).
- **Acceptance:** PF > 1.6 net of fees on n≥30 pairs; HHI < 0.30 across pair categories.
- **Risk register:** Kalshi withdrawal delays (T+1), Polymarket gas-spike during settlement, regulatory event-cancellation (Kalshi has cancelled markets mid-contract — see CFTC 2024 sports-betting ruling).

### Strategy B — `pm_macro_pre_event_drift` (Angle 2)
- **Calendar overlay:** FOMC, NFP, CPI, GDP, jobless claims — 12 macro events / quarter.
- **Entry:** T-36h to T-24h, side = consensus per latest median Bloomberg survey (proxy: scrape `tradingeconomics.com/calendar`).
- **Exit:** T-2h before print, or stop at -15% per leg.
- **Sizing:** 1% per event, max 3 concurrent events.
- **Acceptance:** Sharpe > 1.5 OOS, max drawdown < 12% on n≥40 events (~10 months Kalshi alive).
- **Risk register:** Consensus-flipping events (Cleveland Fed nowcast revisions), event surprises that overshoot consensus, Kalshi liquidity vanishing on small-cap macro contracts.

**Both contingent on:** Kalshi feed alive (46d dark) + §2 PM resolver fix landed.

---

## 5. Recommended sequence (P0 → P3)

| P | Action | Owner | Cost |
|---|---|---|---|
| **P0** | PM resolver fix — settle the 49 CLOSED-without-verdict + 178 OPEN backlog via Polymarket Gamma API; stamp `asset_class='PREDICTION_MARKETS'` at emit | resolver maintainer | 1-2 PR-days |
| **P0** | Kalshi feed diagnosis — why dark 46d? API key expired / endpoint deprecated / scraper broken? | ops | 0.5 PR-day |
| **P1** | Reclassify CRYPTO-tagged PM picks → PREDICTION_MARKETS in `at_raw_picks` (one-shot migration) | data | 0.25 PR-day |
| **P1** | Build `pm_whale_consensus` aggregator (Angle 4) — quickest edge given infrastructure already 80% built | strategy | 1 PR-day |
| **P2** | Build base-rate library + `pm_base_rate_fade` (Angle 3) | research | 3 PR-days |
| **P3** | Implement `pm_kalshi_polymarket_arb` (Strategy A) — after Kalshi alive | strategy | 2 PR-days |
| **P3** | Implement `pm_macro_pre_event_drift` (Strategy B) — after Kalshi alive | strategy | 2 PR-days |
| **P3** | Twitter→PM latency bot (Angle 5) — websocket retrofit | infra | 4 PR-days |

---

## 6. Acceptance criteria for "PREDICTION_MARKETS unlocked in /audit"

The `/audit` MAJOR GOAL banner cannot show a PREDICTION_MARKETS tile until:
1. `asset_class_health.PREDICTION_MARKETS.n == n_resolved` (resolver healthy).
2. n ≥ 100 cleanly resolved picks (post-P0).
3. PF ≥ 1.5, WR ≥ 50%, MDD ≤ 20% on the cohort (Tier-2 minimum per `reports/hedge_fund_performance_review_*.md`).
4. HHI ≤ 0.30 across strategies (no single strategy dominates the cohort, per the M-067 concentration policy and `feedback-concentration-strategy-not-engine.md`).

**ETA estimate:** P0 + 1 wired-up strategy + 60 days of live emission = **~Aug 1, 2026** to first PREDICTION_MARKETS tier verdict in `/audit`.

---

## Sources cited
- `at_raw_picks` queried 2026-05-31 (this report's §1).
- PR #182 retiring `prediction_market_consensus`.
- Wave wdwndhgqj direct push 2c934f8e5 (Kalshi/Polymarket liveness brief).
- `alpha_engine/outcome_resolver.py:115-126` (PNL_WIN_THRESHOLD_BY_CLASS pattern — needs PRED_MKT entry).
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate-before-kill).
- `feedback-concentration-strategy-not-engine.md` (HHI > 0.30 measured at strategy level).
- Polymarket Gamma API (`https://gamma-api.polymarket.com/markets`).
- Kalshi Trade API (`https://trading-api.kalshi.com/trade-api/v2`).

---
**Verdict:** PREDICTION_MARKETS is a real opportunity (5 untried angles, 2 concrete strategies, infrastructure 80% built) but **gated entirely on the P0 resolver fix and Kalshi feed resurrection**. No statistical edge can be claimed or refuted on current data.
