# Paper Trade Session — 2026-05-11

**Operator:** Claude Opus 4.7 (caveman mode)
**Skill:** `tv-paper-trade`
**Accounts touched:** `zerounderscore`, `HIGHFWWRABV55_SCOREABOVE50_V4` (SKIPPED), `The Leap Crypto`
**Goal:** Place top picks across portfolios + swarm-vet The Leap restricted-symbol slate

---

## Outcome

7 paper trades placed across 2 accounts. 1 account (V4) skipped with documented reason.

| Account | Trades | Notional | Margin used | Bal |
|---|---|---|---|---|
| zerounderscore | 4 | $14,387 | $1,439 | $91,658 |
| The Leap Crypto | 3 | $9,055 | $905 | $100,070 |
| V4 | 0 (SKIPPED) | — | — | $1,022 |

---

## zerounderscore — 4 positions

Source: `alpha_engine/data/active_picks.json` filtered by sweet-spot conf 0.75-0.79, fresh-ish, sane R:R, excluded cycle-7 wreck symbols (BTCUSDT/SUIUSDT/OPUSDT/AVAX), forex (PF 0.27 sub-floor per CLAUDE.md), and BNBUSDT (0% WR drain per memory).

TP/SL recomputed via portfolio rule (1x ATR SL / 2x TP, ~4% daily ATR) — JSON entries were 50%+ stale (ONDO pick entry 0.2606 vs live $0.4345).

| Symbol | Side | Qty | Entry (filled) | TP | SL | Notional | Margin | Source strategy | Conf |
|---|---|---|---|---|---|---|---|---|---|
| BINANCE:ONDOUSDT | Long | 8,000 | 0.4357 | 0.4693 | 0.4171 | $3,486 | $349 | trio_bot | 0.78 |
| BINANCE:APTUSDT | Long | 3,300 | 1.112 | 1.199 | 1.066 | $3,666 | $367 | ml_strategy_reviver | 0.75 |
| BINANCE:ARBUSDT | Long | 26,000 | 0.1394 | 0.1502 | 0.1335 | $3,622 | $362 | ml_strategy_reviver | 0.75 |
| BINANCE:ADAUSDT | Short | 13,000 | 0.2785 | 0.2560 | 0.2894 | $3,620 | $362 | ml_strategy_reviver_inverse | 0.75 |

Sizing: ~4% notional each → ~1.57% margin per trade at 10:1 leverage. Total exposure 15.7% notional / 1.57% margin. Diversified 3L + 1S.

Side-sanity verified before each execute:
- LONG: TP > entry > SL
- SHORT (ADA): SL > entry > TP

Post-fill TP/SL audit passed for all 4 (no `VIOLATION:` from skill's audit IIFE).

---

## HIGHFWWRABV55_SCOREABOVE50_V4 — SKIPPED

**Gate definition:** strategy-level fwd_WR >= 55% AND PF >= 1.5 AND n_closed >= 20.

Filter run against `audit_dashboard/data/dashboard_data.json::systems` produced 8 eligible strategies: `multi_asset_cot`, `aggregated_picks`, `ml_crypto_pred_v12`, `mega_mutation`, `claude_gainer`, `multi_asset_institutional`, `claude_gainer_st`, `rapid_fire`.

Cross-ref against current `active_picks.json` produced **3 unique picks**, all futures from `multi_asset_cot`:

| Symbol (TV) | Side | Entry | TP | SL | Required margin | V4 available |
|---|---|---|---|---|---|---|
| NYMEX:NG1! | LONG | 2.933 | 3.186 | 2.743 | $1,459.50 | $865.87 → BLOCKED |
| ICEUS:CT1! | SHORT | 86.51 | 82.72 | 89.36 | $2,177.50 | $865.87 → BLOCKED |
| CBOT:ZW1! | SHORT | 640.5 | 606.82 | 665.76 | (not tested, presumed similar) | BLOCKED |

Loosening to per-pick `elite_score >= 50` produced 50 picks — 48 from `copy_trader_intel` with stale entries (BTC pick $70k vs live $81k), 2 non-stale picks (LINK BUY ml_strategy_reviver + ATOM LONG ml_crypto_predictor) but neither source passes the top-8 gate.

**Decision: skip.** Better than forced trades on stale entries or concentrated single-strategy futures bet that won't fit margin.

Caveat: `multi_asset_cot` 87.4% WR likely inflated by non-crypto resolver bug (`feedback_noncrypto_resolver_live_close_bug` — outcome_resolver.py:384-405 closes at yfinance spot with 1bp threshold). Real WR may be much lower.

---

## The Leap Crypto — 3 positions (swarm-vetted)

Account restricted to 5 Coinbase USDC perps: BTCUSDC.P / ETHUSDC.P / SOLUSDC.P / DOGEUSDC.P / XRPUSDC.P.

Spawned `general-purpose` agent in background while V4 work proceeded. Brief: 5-symbol slate with side/SL/TP/size/justification, force diversification, skip if no edge.

**Swarm verdict:**

| Symbol | Side | Entry (swarm) | SL (swarm) | TP (swarm) | Size | Rationale |
|---|---|---|---|---|---|---|
| BTCUSDC.P | SHORT | 81,260 | 83,900 | 76,800 | 4% | Failed at 84k twice, range distribution; LONG bias in topping regime = 25% WR |
| ETHUSDC.P | SHORT | ~3,150 | 3,300 | 2,900 | 3% | ETH/BTC ratio bleeding, correlated confirm to BTC short |
| SOLUSDC.P | SKIP | — | — | — | 0% | No clean trigger; thin USDC.P book |
| DOGEUSDC.P | LONG | market | -5.5% | +9% | 2% | Alt-beta diversifier vs 2 shorts |
| XRPUSDC.P | SKIP | — | — | — | 0% | News-flow lottery, no setup |

**Live-price adjustment:** swarm's ETH levels assumed $3,150 base; ETH was actually $2,312 live (~27% off). Recomputed ETH via portfolio ATR rule (5% SL / 9.5% TP):
- ETH SHORT @ 2312, SL 2428, TP 2092

BTC and DOGE levels matched live state (within 0.1% of swarm's reference).

**Filled:**

| Symbol | Side | Qty | Entry | TP | SL | Notional | Margin |
|---|---|---|---|---|---|---|---|
| COINBASE:BTCUSDC.P | Short | 0.05 | 81,189.8 | 76,800 | 83,900 | $4,059 | $406 |
| COINBASE:ETHUSDC.P | Short | 1.3 | 2,313.25 | 2,092 | 2,428 | $3,007 | $301 |
| COINBASE:DOGEUSDC.P | Long | 18,000 | 0.11069 | 0.12056 | 0.10453 | $1,991 | $199 |

Total: $9,055 notional / $905 margin (0.9% of $100k). Net 2 SHORT + 1 LONG (DOGE is alt-beta counter).

Side-sanity verified pre-execute, post-fill TP/SL audit passed.

---

## Lessons / Caveman Notes

1. **`mcp__tradingview-desktop__quote_get` is buggy** — returns the current chart symbol's price regardless of the `symbol` arg. Workaround: `chart_set_symbol` first, then read legend via `ui_evaluate` on `div[data-name="legend-source-item"]`.

2. **Skill's account-switcher selector (`button.dropdownButton-dm1wtgNn`) opens symbol-search modal in some TV builds** — clicked button is the same class. Real account-switcher button was identified via `tv_ui_state` `other` array at position (192, 514) in the bottom Paper Trading panel. Account rows live as `div[class*="middle-RDCgMoEQ"]` inside the opened dropdown.

3. **Skill's Step-4 IIFE input-mapping (`visible[0..3]` = TP-ticks/TP-price/SL-ticks/SL-price) doesn't match current build.** Current layout: `[0]=qty, [1]=tp_chk, [2]=tp_price, [3]=sl_chk, [4]=sl_price`. Updated adapted IIFE used throughout.

4. **V4 paper account is a $1k account, not $100k.** Skill's portfolio table needs the actual balance per account, not assumed $K bucket.

5. **Pick entries in `active_picks.json` can be 50%+ stale** even when `created_at` says "9.7h ago" (e.g., BTC entry $81,662 when memory thought BTC was $104k — turned out BTC was actually $81,260). Always re-quote before trusting JSON TP/SL.

6. **Swarm output can have stale price baselines.** ETH swarm rec assumed $3,150 (off by ~27% from live $2,312). Always cross-check swarm levels against live before placing.

7. **No `VIOLATION:` audit triggered.** All 7 fills landed with TP/SL set correctly on the first attempt thanks to enabled toggles + native-setter dispatching `input` + `change` events.

---

## Files / refs

- Picks source: `alpha_engine/data/active_picks.json` (108 entries, 41 with timestamps)
- Strategy stats: `audit_dashboard/data/dashboard_data.json` `systems` block (131 strategies)
- Skill: `.claude/skills/tv-paper-trade/SKILL.md`
- Memory references applied:
  - `feedback_gate_at_execution_not_generation` (re-applied gate at exec time for V4)
  - `feedback_noncrypto_resolver_live_close_bug` (flagged multi_asset_cot WR inflation)
  - `feedback_clone_hl_placeholder_stats` (quarantine — no clone_hl_copy picks hit slate)
  - `feedback_tv_cdp_orchestrator_lessons_2026-05-09` (swarm-vet 3+ pick batches → applied to Leap)
  - `reference_tv_account_switching` (DOM-click flow, with build-drift adaptation)

## Open items

- PR #904 swarm review (paused before this session — still pending)
- Monitor 7 paper positions for fill quality + TP/SL hit rate
- Consider populating V4 with cheap-symbol picks once a non-stale, non-clone, gate-passing crypto/equity pick exists
