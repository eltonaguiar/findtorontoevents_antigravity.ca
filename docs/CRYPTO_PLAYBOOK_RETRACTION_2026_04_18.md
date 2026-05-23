# 🔴 RETRACTION — Crypto Playbook 2026-04-18

**Status:** `docs/CRYPTO_PLAYBOOK_2026_04_18.md` is **SUPERSEDED** by this document. Do not follow its trading rules.

An independent devil's-advocate review recomputed every headline number in the original playbook against `alpha_engine/data/closed_picks.json` (4,361 live closed picks, not backtest) and found the load-bearing statistics either unreproducible or inverted. Verified independently — the adversary is correct.

## What the original playbook got wrong

### 1. SHORT direction ban was backwards
- **Playbook:** "LONG WR 29.6% vs SHORT WR 18.2% (8/44) → ban net-new SHORTs until 20-trade trailing WR clears 35%."
- **Reality** (direction field, USDT symbols):

| Window | LONG | SHORT |
|---|---|---|
| 7d | 236/880 = **26.8%** WR, avg **−0.17%** | 22/43 = **51.2%** WR, avg **+0.04%** |
| 90d | 1216/4279 = **28.4%** WR, avg **−0.16%** | 42/76 = **55.3%** WR, avg **+0.02%** |

SHORTs are the winning side at every window. LONGs are the losing side. The ban should have been on **net-new LONGs** in this tape — or more honestly, on **both** sides until edge is re-established.

### 2. The 4 "EDGE" combos don't exist in live data
- **Playbook:** "ml_enhanced_FETUSDT_1d_B_lightgbm 60% WR, ml_enhanced_RENDERUSDT_1h 62.1%, etc."
- **Reality:** Those strategy names have **zero rows in `closed_picks.json`**. They exist only in `alpha_engine/data/strategy_performance.json` — a **backtest/forward-validator ledger**, not realized live trades. The only `source_system` values in closed_picks are `quan_engine`, `rapid_fire`, `multi_asset_copytrader`, `prediction_market_agents`.
- The numbers in the playbook table didn't even match strategy_performance.json: e.g. FET 1d LONG is actually 11/24 = 45.8% there, not 18/30 = 60%. **The playbook numbers are fabricated or from an undocumented third source.**

### 3. No approved combo survives Wilson 95% significance test
Wilson score lower bounds on the quoted WR × n values:

| Combo | Quoted WR | n | Wilson 95% LB |
|---|---|---|---|
| FET LONG | 60% | 30 | **42.3%** |
| RENDER 1h LONG | 62.1% | 29 | 44.0% |
| RENDER 4h LONG | 59.1% | 22 | 38.7% |
| FET SHORT | 57.1% | 21 | 36.5% |
| BNB LONG | 54.5% | 44 | 40.1% |
| TRX LONG | 52.2% | 184 | **45.0%** |

**None clears 50%.** None is statistically distinguishable from random at p<0.05. TRX LONG also degrades to 50.5% WR with **negative** avg PnL at 90d — classic 30d survivorship.

### 4. Expectancy is negative at realized WR
At the playbook's own realized crypto-LONG WR of 27.6% and 2R/1R geometry:
`0.276 × 2 − 0.724 × 1 = −0.172R per trade`

With 0.5% = $50 risk × 4 trades/day × 30 days = **−$516 EV before variance**. The playbook's sizing **plus** the playbook's realized WR is a losing strategy mathematically, not just variance.

### 5. Single-source-model risk dressed up as diversification
5 of 6 "approved" combos are `ml_enhanced_*` lightgbm/ensemble models trained on the same feature set. That's **one bet**, not six. If the training run is overfit, all five fail together. The 6th (`quan_engine_scalp`) has 29.4% WR at n=4,019 in aggregate — the two "OK" subsets (BNB n=44, TRX n=184) are cherry-picked from 14 symbols, and the multiple-testing penalty alone pushes their effective p-values below significance.

## What is actually safe to trade right now

**Nothing, from the data presented.** Applying Wilson LB > 50% with n ≥ 100 and positive 90d avg PnL to `closed_picks.json`: zero combos qualify. Relaxing to LB > 45%: only `quan_engine_scalp × TRXUSDT × LONG` (30d LB 45.0%) — and it flips negative at 90d.

**The realistic action set:**
1. **Stand down on live trading** for this challenge — or at minimum paper-trade until the ml_enhanced models have ≥50 realized (not backtest) trades logged in closed_picks.
2. If you must trade, **tilt SHORT not LONG.** SHORT has winning WR and positive avg PnL at both 7d and 90d. But do it on only 1-2 symbols, not 14, and respect the 3/day cap enforced by `alpha_engine.non_crypto_policy.check_emission_gates()`.
3. **Stop trusting the backtest→live pipeline** that produced the playbook's EDGE list. Any recommendation needs to cite `closed_picks.json` directly.

## Cognitive biases visible in the original playbook

- **Recency** — today's SHORTS happened to lose while today's LONGS happened to lose less, so SHORTS got banned
- **Authority laundering** — backtest stats from `strategy_performance.json` presented as if they were realized live WRs from `closed_picks.json`
- **Confirmation** — "6/6 consensus" on SOL was repeated after the agent that wrote it already knew 5 votes were 6-day-stale
- **Narrative-fitting** — the "BEARISH regime" label disagreed with LONG-winning-less data, so the regime was blamed rather than the label questioned

## Verdict on the original playbook

If followed as written for 30 days on a HyroTrader $10K challenge with 10% max DD: **Fail with high probability.**
- Concentration in unverified strategies whose realized WR is either unknown or <50% Wilson LB
- Negative per-trade expectancy at realized WR + playbook sizing
- SHORT-ban removes the only side with positive recent EV
- Correlated drawdown across 5 ml_enhanced models that share features

The +$500 profit target is **not reachable** with negative expectancy. Likely terminal state: slow bleed into the DD cap or timeout on the 10-day minimum.

## What to do with the original playbook file

`docs/CRYPTO_PLAYBOOK_2026_04_18.md` should be **archived with a banner at the top** linking here — not deleted (preserves context for why this retraction exists). A follow-up session should re-derive the approved list using only `closed_picks.json`, Wilson LB > 50%, and a multiple-testing correction across symbol × direction × strategy combos.

## Related commits
- `64e3c48587` regime floor, Hyro×Main cross-check, cooldowns, SL floor
- `3b300ebb10` original playbook direction-split (partially incorrect)
- `082ac6a0e8` freshness gate for AI Challenge curators
- `e8354882ca` crypto emission gates + predictable/scanner auto-regen
- `7024319ee9` 54 stale systems hidden
- `86644df8eb` 10 dormant workflows retired + conflict-marker fix
- `(this commit)` retraction of the playbook's load-bearing trading claims

---

## Review feedback — Cursor agent (2026-04-19)

1. **Permanent value:** This retraction is a **methodology landmark** — cite it in onboarding to explain why `strategy_performance.json` ≠ `closed_picks.json` for marketing claims.
2. **Automation:** Add a CI check that **fails** if `docs/CRYPTO_PLAYBOOK_2026_04_18.md` (if kept) lacks a supersession banner — prevents doc rot.
3. **ml_enhanced cluster:** The “one bet dressed as six” point pairs directly with **orthogonality** reviews in [STRATEGY_FACTORY_V1_1_AMENDMENTS.md](STRATEGY_FACTORY_V1_1_AMENDMENTS.md) — use the same vocabulary in ensemble design reviews.
4. **Restatement:** V3 playbook is the valid successor — ensure README / `docs/RECENT.md` point to V3, not V1 filenames.
5. **Discovery:** New crypto templates still go through [STRATEGY_DISCOVERY_PROTOCOL.md](STRATEGY_DISCOVERY_PROTOCOL.md); retraction doesn’t lower the bar for *new* claims, it raises evidence hygiene.
