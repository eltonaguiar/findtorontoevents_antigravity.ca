# TV Paper Trade Justifications — 2026-05-11 22:29 EST

7 trades placed across 2 paper accounts. Per-trade rationale below.

Operator: Claude Opus 4.7 (caveman mode), skill `tv-paper-trade`.

---

## zerounderscore account ($91,658 balance, 10:1 leverage)

### 1. BINANCE:ONDOUSDT — LONG 8,000 @ 0.4357

- **Source:** `trio_bot` strategy via `alpha_engine/data/active_picks.json`
- **Confidence:** 0.78 — **sweet-spot** (skill: 0.75-0.79 = 87.4% WR tier, highest WR bucket)
- **R:R declared:** 1.67; recomputed TP/SL: SL 0.4171 (1× ATR ~4%), TP 0.4693 (2× ATR ~8%) → R:R 2.0
- **Sizing:** 8,000 units = $3,486 notional = 3.8% of balance = $349 margin (0.38%)
- **Why this side:** ONDO is in real-world-asset rotation theme; recent technicals showed accumulation off range lows. trio_bot strategy passes elite=100 in current picks. JSON entry was stale ($0.2606 vs live $0.4345) so recomputed entry to live and TP/SL via portfolio ATR rule.
- **Why this size:** Default zerounderscore sizing is 2-5%. Picked 4% target → 3.8% actual after rounding to clean 8,000 units. Diversified across 4 picks → total exposure ~15% notional, under the diversified-portfolio cap.
- **Risk:** trio_bot has fewer total trades than ml_strategy_reviver → less statistical confidence. Stale JSON entry indicates pick generation pipeline lagged the rebound.

### 2. BINANCE:APTUSDT — LONG 3,300 @ 1.112

- **Source:** `ml_strategy_reviver`
- **Confidence:** 0.75 — sweet-spot
- **R:R declared:** 2.33; recomputed via ATR: SL 1.066, TP 1.199 → R:R 1.96
- **Sizing:** 3,300 units = $3,666 notional = 4.0% balance = $367 margin
- **Why this side:** APT had been basing in $1.05-1.15 range with declining sell volume; ml_strategy_reviver flagged for revival. Conservative LONG with tight 4% SL.
- **Why this size:** 4% default. R:R declared 2.33 marginally above 2.0 floor → standard size; no upsize because revival strategies have historical drift risk.
- **Risk:** ml_strategy_reviver as a class has mixed forward performance per memory. BNBUSDT BUY from same strategy was a known 0% WR drain — excluded from this slate but flag the class-level risk.

### 3. BINANCE:ARBUSDT — LONG 26,000 @ 0.1394

- **Source:** `ml_strategy_reviver`
- **Confidence:** 0.75 — sweet-spot
- **R:R declared:** 2.50 (highest in sweet-spot set); recomputed: SL 0.1335, TP 0.1502 → R:R 1.93
- **Sizing:** 26,000 units = $3,622 notional = 4.0% balance = $362 margin
- **Why this side:** ARB at $0.13-$0.14 is near absolute lows; Layer-2 rotation thesis; oversold momentum reversion candidate. Sweet-spot conf + best declared R:R in slate.
- **Why this size:** 4% default, despite best R:R among slate. Did not upsize — preserves diversification, avoids over-weighting any single strategy.
- **Risk:** Layer-2s have been broadly weak; ARB is a deep-drawdown bounce attempt, not trend-following.

### 4. BINANCE:ADAUSDT — SHORT 13,000 @ 0.2785

- **Source:** `ml_strategy_reviver_inverse` (inverse-signal model: flips a presumed losing LONG into a SHORT)
- **Confidence:** 0.75 — sweet-spot
- **R:R declared:** 1.25; recomputed: SL 0.2894 (+4%), TP 0.2560 (-8%) → R:R 2.0
- **Sizing:** 13,000 units = $3,620 notional = 4.0% balance = $362 margin
- **Why this side:** Inverse-strategy SHORT provides directional diversification — slate already has 3 LONGs. Memory: "SHORT outperforms LONG in BEAR regime". BTC topping in $79-84k range supports broader risk-off bias.
- **Why this size:** Same 4% as LONGs — keeps inverse-strategy weight matched, doesn't over-trust the inversion edge.
- **Risk:** Inverse strategies invert a losing source signal — if the source flips to winning, the inverse becomes losing. ADA could surprise to the upside on ETF/regulatory headlines.

---

## HIGHFWWRABV55_SCOREABOVE50_V4 account ($1,022 balance) — SKIPPED

- **Why skipped:** Gate (fwd_WR≥55 + PF≥1.5 + n≥20) returned 8 eligible strategies → cross-ref to current `active_picks` produced 3 unique futures picks (NG1!/CT1!/ZW1! from `multi_asset_cot`). All 3 require $1,459-$2,177 margin per contract. V4 has only $865.87 available → ALL blocked.
- **Why not loosen the gate:** Loosening to per-pick elite_score≥50 returned 50 picks, 48 from `copy_trader_intel` with stale entries (BTC pick $70k vs live $81k). Only 2 non-stale (LINK BUY ml_strategy_reviver + ATOM LONG ml_crypto_predictor); neither source passes the top-8 strategy gate. Forcing trades on stale entries or single-strategy concentration is worse than skipping.
- **Additional concern:** `multi_asset_cot` 87.4% WR is likely inflated by the non-crypto resolver bug (`outcome_resolver.py:384-405` closes at yfinance spot with 1bp WIN threshold — memory `feedback_noncrypto_resolver_live_close_bug`). Real WR may be much lower; placing concentrated futures bet on this strategy without addressing the resolver bug = poor expected value.

---

## The Leap Crypto account ($100,070 balance, 10:1 leverage, restricted to 5 Coinbase USDC perps)

Slate built by background `general-purpose` agent. Brief asked for 5-symbol slate w/ force-diversification + SKIP rather than pad. Swarm returned 3 trades + 2 skips.

### 5. COINBASE:BTCUSDC.P — SHORT 0.05 @ 81,189.8

- **Source:** Swarm agent (highest-conviction trade in returned slate)
- **Side rationale:** BTC failed at $84k twice in the $79-84k range = textbook distribution at range high. Project memory rule: "LONG bias in BEAR/topping regime = 25% WR" → range-midpoint SHORT with stop above range high is correct posture.
- **Levels:** SL 83,900 (above range high), TP 76,800 (range low + buffer). R:R = 1.69
- **Sizing:** 0.05 BTC = $4,059 notional = 4.0% of balance = $406 margin
- **Why this size:** Anchor trade in the slate. Largest position by design — highest conviction, longest-validated thesis (range-bound is the cleanest BTC technical right now).
- **Risk:** A daily close above $84,000 invalidates the thesis; SL placement above $83,900 will trigger on a breakout attempt — acceptable.

### 6. COINBASE:ETHUSDC.P — SHORT 1.3 @ 2,313.25

- **Source:** Swarm agent, **but levels recomputed locally** — swarm assumed ETH ~$3,150 (off by 27% from live $2,312). Used portfolio ATR rule instead.
- **Side rationale:** ETH/BTC ratio has been bleeding; ETH underperformed every BTC bounce in current range. Correlated confirm to the BTC SHORT — sized smaller to avoid double-counting one macro bet.
- **Levels (locally recomputed):** SL 2,428 (~+5%, 1× daily ATR), TP 2,092 (~-9.5%, 2× ATR). R:R = 1.92
- **Sizing:** 1.3 ETH = $3,007 notional = 3.0% of balance = $301 margin
- **Why this size:** Per swarm, 3% (smaller than BTC) because correlation-confirm trades shouldn't be sized equal to anchor — controls macro concentration.
- **Risk:** ETH could decouple upward if a spot-ETF flow event hits during the BTC range; ETH/BTC ratio reversal would hurt this trade specifically.

### 7. COINBASE:DOGEUSDC.P — LONG 18,000 @ 0.11069

- **Source:** Swarm agent (the deliberate counter-position to balance the 2 SHORTs)
- **Side rationale:** Alt-beta diversifier. DOGE typically front-runs retail risk-on bounces from BTC range lows. If BTC breaks DOWN, this LONG underperforms but the 2 SHORTs anchor the slate. If BTC breaks UP instead, DOGE LONG limits the slate's pure-downside exposure. Memory rule: avoid 5/5 same-direction (LONG in BEAR = 25% WR; SHORT in BULL also costly). Mix forces robustness.
- **Levels:** SL 0.10453 (-5.5%, 1× ATR), TP 0.12056 (+9%, ~1.6× ATR). R:R = 1.64
- **Sizing:** 18,000 DOGE = $1,991 notional = 2.0% of balance = $199 margin (smallest in slate)
- **Why this size:** Minimum 2%. Confidence not highest in slate; size reflects "diversifier, not conviction trade".
- **Risk:** DOGE is memecoin-volatile; can spike on Musk tweets unrelated to charts. Stop placement at -5.5% is wider than ARB/ONDO LONG stops to account for that. Worst case is BTC breaks down AND DOGE falls harder than SL — the BTC/ETH SHORTs would still cover.

### Swarm SKIPs

- **SOLUSDC.P — SKIP:** No clean trigger from supplied context; Coinbase SOLUSDC.P perp book thinner than BTC/ETH equivalents. Memory: don't pad slate just to fill 5 picks.
- **XRPUSDC.P — SKIP:** Driven by legal/ETF headlines, not technicals. Pure news-flow lottery. Skip per swarm's risk-aware default.

---

## Slate-level rationale

- **Total notional placed:** $23,442 across 7 trades / 2 accounts.
- **Total margin used:** $2,345 (heavily diversified, no account >2% margin utilization).
- **Net direction:** 4 LONG + 3 SHORT (vs 5/5 LONG default per the LONG-bias memory)
- **Cross-account hedging:** zerounderscore is mostly LONG-side crypto (3L 1S). The Leap is SHORT-leaning (2S 1L). Combined, slate is approximately direction-neutral on the BTC complex.
- **No cycle-7-wreck symbols:** SUIUSDT/OPUSDT/BTCUSDT-LONG/AVAX explicitly excluded from zerounderscore slate.
- **No clone_hl_copy:** quarantined per memory `feedback_clone_hl_placeholder_stats`.

## Audit checklist (all passed)

- [x] Account verified per trade via DOM read (`span.accountName-dm1wtgNn`)
- [x] Live entry quoted via TV legend (not stale JSON entry)
- [x] Side-sanity gate pre-execute (LONG: TP>E>SL ; SHORT: SL>E>TP)
- [x] TP/SL toggles enabled before execute (no silent-drop per memory `reference_tv_protect_position_tp_toggle`)
- [x] Post-fill TP/SL audit on each position row — no `VIOLATION:` triggered
- [x] No position opened with $0 SL or $0 TP
- [x] V4 skip documented in lieu of forced fills

---

Generated at 2026-05-11 22:29 EST (UTC-5).
