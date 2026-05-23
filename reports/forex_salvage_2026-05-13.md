# FOREX Salvage Plan — Mutate-Before-Kill

**Date:** 2026-05-13
**Source:** `audit_dashboard/data/dashboard_data.json` (systems block + asset_class_health.FOREX)
**Protocol:** `docs/MUTATION_THREE_AXIS_PROTOCOL.md` + `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`
**Class state:** status=stressed, sizing_allowed=false, PF 0.63, WR 41.4%, resolved_n=432 (live `by_asset_class.FOREX`); legacy headline PF 0.29 / n=1339 reflects pre-resolver-v2 raw rows.

---

## 1. Discover — top-3 FOREX drag systems

| System (`system.name`)   | `closed_picks` | `profit_factor` | `win_rate` | gross_loss | Notes |
|--------------------------|---------------:|----------------:|-----------:|-----------:|-------|
| `multi_asset`            | 225            | 0.32            | 44.4%      | -233.5     | Biggest PF drag; FOREX+COMMODITY only; total pnl -159.4% |
| `alpha_engine_fast`      | 299 (FOREX subset of 12.4k total) | 0.62 | 43.2% | -336.3 | Multi-class; FOREX is one of six; flagged in `feedback_circuit_breaker_stale_state_leak` history |
| `multi_asset_scanner`    | 111            | 0.71            | 13.0%      | -11.9      | 13% WR = symptom of LONG-bias on red DXY days; small gross loss but catastrophic WR |

These three account for ~94% of FOREX gross loss. `regime_terminal` (PF 1.12, n=64) is borderline-positive — leave alone. `alpha_engine` core (PF 1.61, n=12,442 across classes), `rapid_fire` (PF 1.73), `kimi_riseoftheclaw` (PF 1.38), `stocks_competition` (PF 1.31) are not drags.

---

## 2. Mutate — 3-axis rules

### 2.1 `multi_asset` (PF 0.32 → target ≥1.4)
- **Axis 1 (timeframe):** raise hold horizon from intraday-spot to **4H bar-close** entries; require signal candle to close before fill (kills tick-noise resolver leak per `feedback_noncrypto_resolver_live_close_bug`).
- **Axis 2 (regime):** skip when `DXY_4h_ATR_pct > 1.5×20d_mean` OR economic-calendar `event_impact == HIGH` within ±90 min (NFP, CPI, FOMC, ECB, BoE, BoC). Also skip 22:00-02:00 UTC (Asia thin book).
- **Axis 3 (instrument):** focus on **EURUSD, GBPUSD, AUDUSD, USDJPY**; **AVOID** USDCAD, NZDUSD, USDCHF, exotics (where prior closed-trade subset shows WR <35%).
- **Signal rule:**
  ```python
  if tf != "4H": reject
  if dxy_atr_pct > 1.5 * dxy_atr_pct_20d_mean: reject
  if economic_event_impact_within(minutes=90) == "HIGH": reject
  if hour_utc in range(22,24) or hour_utc < 2: reject
  if symbol not in {"EURUSD","GBPUSD","AUDUSD","USDJPY"}: reject
  ```

### 2.2 `alpha_engine_fast` (FOREX subset PF 0.62 → target ≥1.4)
- **Axis 1:** drop M5/M15 FOREX picks entirely; allow **1H + 4H only**. The "fast" suffix has been the noise source on FOREX (already locked alpha_engine_fast once per `circuit_breaker_stale_state_leak`).
- **Axis 2:** require **DXY-confluence**: LONG USD-base pairs only when DXY 4H EMA20 > EMA50; SHORT USD-base pairs only when DXY 4H EMA20 < EMA50. Skip the first 15 min of London (07:00 UTC) and NY (12:30 UTC) opens — fade-the-spike protection.
- **Axis 3:** rotate **out of carry pairs** (USDJPY, USDMXN, USDZAR) during BoJ/EM-CB weeks; rotate **into** EURUSD + GBPUSD as the liquidity core.
- **Signal rule:**
  ```python
  if tf in {"M5","M15"}: reject
  base, quote = parse_pair(symbol)
  dxy_trend = ema20_4h > ema50_4h
  if side == "LONG"  and base == "USD" and not dxy_trend: reject
  if side == "SHORT" and base == "USD" and dxy_trend:     reject
  if minutes_since(open_utc=7*60)  < 15: reject
  if minutes_since(open_utc=12*60+30) < 15: reject
  ```

### 2.3 `multi_asset_scanner` (WR 13% → target ≥45%)
The 13% WR with only 111 trades is the textbook `feedback_long_source_bias` artifact: LONG-only on a 6-month strong-DXY regime.
- **Axis 1:** lift to **1D bar-close** entries (it is a scanner, not a scalper).
- **Axis 2:** require **2-of-3 regime confluence**: (a) DXY 1D below 20d-EMA, (b) US10Y yield 5d-change ≤ 0, (c) VIX < 22. Otherwise force the inverse side.
- **Axis 3:** focus on **EUR, GBP, AUD majors vs USD only**; drop CHF/JPY/CAD/NZD pairs and ALL crosses.
- **Signal rule:**
  ```python
  if tf != "1D": reject
  votes = sum([dxy_below_ema20, us10y_5d_change <= 0, vix < 22])
  if votes < 2 and side == "LONG": side = "SHORT"; tag="inverted"
  if symbol not in {"EURUSD","GBPUSD","AUDUSD"}: reject
  ```

---

## 3. Three paper-trade picks for 2026-05-13 US-session open (~07:00 EDT / 11:00 UTC)

Account $100,000, 1.5% notional risk = **$1,500 max loss per trade**. Live refs are last-known mids from prior session; **operator must re-pull quote at fill** and shift entry by ≤ 5 pips.

| # | Symbol  | Side  | Entry (ref) | SL      | TP      | Risk pips | Lot (1.5% risk) | R:R  | Mutation | Conviction |
|---|---------|-------|------------:|--------:|--------:|----------:|----------------:|-----:|----------|------------|
| 1 | EURUSD  | LONG  | 1.08450     | 1.08100 | 1.09200 | 35        | 0.43 lot ($1,500/350)| 1:2.14 | `multi_asset` 4H + DXY-confluence (DXY below 20d-EMA) | **PILOT — highest** |
| 2 | GBPUSD  | LONG  | 1.26800     | 1.26350 | 1.27700 | 45        | 0.33 lot ($1,500/450)| 1:2.00 | `alpha_engine_fast` 1H + DXY-confluence, London-open +15 min | Medium |
| 3 | AUDUSD  | SHORT | 0.66200     | 0.66550 | 0.65500 | 35        | 0.43 lot ($1,500/350)| 1:2.00 | `multi_asset_scanner` inverted (votes=1, side flipped per axis-2) | Lower (inverted-LONG-bias play) |

**Why #1 is pilot:** EURUSD is the deepest book, the mutation hits all three axes cleanly, and `multi_asset` is the largest drag — biggest expected lift if the mutation prints.

**Exec notes:**
- Use TradingView paper account `TESTER` or `SCALPER` per `.claude/skills/tv-paper-trade/SKILL.md`; **mandatory TP/SL toggles ON** (`feedback_tv_protect_position_tp_toggle`).
- Tag each pick with `meta.mutation_id = "forex_salvage_2026_05_13"` so the resolver can group them.
- Spread ≤ 1.2 pips at fill, else skip.

---

## 4. Acceptance criteria — does mutation beat kill?

**Window:** next 50 closed mutation-tagged FOREX trades, or 30 calendar days, whichever first.

| Metric                                  | Pass (keep mutation)   | Fail (proceed to kill) |
|-----------------------------------------|------------------------|------------------------|
| Profit Factor (mutation cohort)         | ≥ 1.40                 | < 1.10                 |
| Win Rate                                | ≥ 48%                  | < 42%                  |
| Max Drawdown (peak-to-trough $)         | ≤ 12%                  | > 18%                  |
| Avg R:R realized                        | ≥ 1.30                 | < 1.00                 |
| Per-mutation contribution to FOREX PF   | Lifts class PF ≥ +0.50 vs Apr baseline 0.63 | No measurable lift |

**Hard kill-switch:** if any single mutation cohort posts MDD > 20% before n=20, halt that cohort and rotate the surviving 2 forward. Reviews at n=20 (early read), n=50 (verdict), n=100 (stable-tier promotion / FOREX `sizing_allowed=true` candidate).

**Reproducer:**
```
python tools/mutation_analysis.py --tag forex_salvage_2026_05_13 --class FOREX --min-n 20
```
