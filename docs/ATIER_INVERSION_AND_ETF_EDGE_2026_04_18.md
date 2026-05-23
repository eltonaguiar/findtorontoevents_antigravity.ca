# A-Tier Inversion & ETF Edge — 2026-04-18

Analyst: Claude (Opus 4.7). All numbers recomputed from
`audit_dashboard/data/dashboard_data.json` (`picks.recent_closed`, 3,500 rows)
on 2026-04-18, sorted by `exit_time/closed_at` desc, grouped per the
dashboard's own logic in `audit_dashboard/template.html` (`_cryptoScoreBucket`,
lines 4954–4970 and `renderCryptoPanel`, lines 4972+).

## 0. Executive summary

- **Crypto A-Tier is broken, not an artifact.** 0/20 wins in the last 20
  resolved picks is statistically rock-solid: binomial two-sided p ≈
  **1.9e-6** vs a 50/50 null. Wilson 95% upper bound = **16.1%**
  (`[0.0%, 16.1%]`). You can reject "A-Tier is random" at p<0.0001.
- **The failure is not the tier — it is one strategy.** 14 of the 20 A-Tier
  losers are `st_fear_greed_contrarian` LONGs on DOGE/ADA/NEAR during a
  downtrend. Inverting the whole A-Tier ribbon is unsafe; **killing/fading
  `st_fear_greed_contrarian` + `st_obv_support_divergence` on memecoins** is
  the defensible action.
- **ETF edge is real *on tiny n*.** 17/20 → Wilson 95% LB = **63.96%**, UB
  = **94.76%**, binomial p vs 50/50 ≈ **0.0026**. The anchor is
  `intermarket-flow-scout` (5/20 of those picks). All-time ETF WR in the
  same payload is only 52.2% (36/69), so this is a recent regime tailwind,
  not a proven long-run edge. Paper-trade yes, live-trade no — until n≥60.
- **Equity edge is weaker than screenshot claimed.** Current payload shows
  EQUITY last20 = **11/20 (55%)**, not 12/20 (60%); `stocks_rsi2_pullback`
  is only 2/20 of the sample. Proceed with paper at half size.
- **Forex and Commodity last-20 WR in the payload are 6/20 (30%) and 6/20
  (30%)** — higher than the screenshots' 15%/20% because the payload has
  advanced since the screenshots were taken, but still sub-50%. Forex PF
  all-time is **0.27** (`performance.by_asset_class.FOREX`, pnl = -973.91
  over 926 closed wins+losses). **Do not trade forex live.**

---

## 1. Task 1 — A-Tier crypto inversion: statistical teeth

### 1.1 Wilson CI & binomial test

For 0 wins in 20 trials, z=1.96:

```
Wilson 95% CI = [0.0%, 16.11%]
Binomial two-sided p (null H0: p=0.5) = 1.91e-6
```

So the chance this run of 20 losses comes from a fair 50/50 process is
roughly 1 in 525,000. It is **extremely** non-random.

For the companion S-Tier line (0/3), Wilson 95% CI = [0%, 56.15%] — too
small to say anything. Ignore S-Tier for statistical claims.

### 1.2 Is the *inverse* of A-Tier a defensible trade?

Mathematically, if A-Tier were a stable classifier that the market has
inverted, shorting every A-Tier LONG would be 20/20 on this sample →
Wilson 95% LB = **83.89%**. Tempting.

But the 20-pick sample has severe survivorship problems:

1. The A-Tier bucket is defined by `score ∈ [55, 70)` *at entry*
   (`_cryptoScoreBucket`, template.html:4967). The score weights are
   themselves backtested and updated, so the bucket's meaning drifts.
2. 14 of 20 losers are one strategy, `st_fear_greed_contrarian`, buying
   LONG on DOGE/ADA/NEAR during a market downtrend. This is a **regime
   failure of one strategy**, not evidence the A-Tier label is inverted.
3. "Fade A-Tier" on the same 20 trades would be in-sample 100% — classic
   lookback illusion.

**Recommendation:** Do not implement a blanket A-Tier SHORT. Instead
demote the specific strategies (next section) and let the bucket
re-populate over 40–60 fresh trades before re-judging the label.

### 1.3 Where A-Tier is assigned

- **Bucket definition:** `audit_dashboard/template.html:4954–4970`
  (`_cryptoScoreBucket`). Thresholds: S≥70, A∈[55,70), B∈[40,55), C<40.
  Score field priority: `score → elite_score → ml_composite_score`.
- **Score production** (not tier tagging) happens upstream in
  `alpha_engine/` and `audit_trail/mercury2_scoring.py`,
  `audit_trail/empirical_bayes_scorer.py`, and
  `audit_trail/non_crypto_smart_score.py`. There is no server-side
  "A-Tier" label in the pick record — it is computed **in the browser**
  from `p.score` each render.
- **HF conviction tier** (separate concept: S/A/B — no C) is assigned by
  `alpha_engine/conviction_stack.classify_hf_conviction_tier` and written
  into `p.hf_conviction_tier` / `p.conviction_tier` in
  `audit_trail/dashboard_generator.py:13173–13190`. The dashboard's
  top "S-Tier / A-Tier" picks table uses that, not the
  `_cryptoScoreBucket` tier used in the Crypto+NC performance panel.
  **The screenshot's A-Tier is the `_cryptoScoreBucket` one.**

### 1.4 The 20 A-Tier losers (symbol, direction, strategy, pnl)

Recomputed from `picks.recent_closed`, last 20 A-Tier crypto picks by
`exit_time` desc:

| # | Symbol | Dir | Strategy | PnL% |
|---|---|---|---|---|
| 1 | FETUSDT | LONG | `ml_enhanced_FETUSDT_1d_B_lightgbm` | −5.49 |
| 2 | WLDUSDT | LONG | `cross_sectional_reversal` | −4.10 |
| 3 | LINKUSDT | LONG | `st_fear_greed_contrarian` | −1.38 |
| 4 | ATOMUSDT | LONG | `st_fear_greed_contrarian` | −1.22 |
| 5 | ATOMUSDT | LONG | `st_fear_greed_contrarian` | −1.28 |
| 6 | APTUSDT  | LONG | `st_fear_greed_contrarian` | −2.10 |
| 7 | LINKUSDT | LONG | `st_obv_support_divergence` | −1.49 |
| 8 | SOLUSDT  | LONG | `st_obv_support_divergence` | −1.31 |
| 9 | SOLUSDT  | LONG | `st_obv_support_divergence` | −1.33 |
| 10–20 | DOGE×9, NEAR×1, ADA×1 | LONG | `st_fear_greed_contrarian` ×11 | −1.37 to −1.80 each |

Concentration: **16 of 20** are the two `st_*` strategies; **11 of 20**
are DOGEUSDT LONG; avg loss ≈ −1.8%. This is a strategy/regime bleed,
not a classifier inversion.

### 1.5 Sketch: implementation if we *did* want to invert A-Tier

Would go in `audit_trail/dashboard_generator.py` where the tier is
available, OR at pick emission in `alpha_engine/smart_picks_engine.py`.
Toy pseudocode:

```python
from alpha_engine.conviction_stack import classify_hf_conviction_tier

def maybe_invert_a_tier(pick):
    if pick.get("asset_class") == "CRYPTO" and pick.get("score", 0) >= 55 \
       and pick.get("score", 0) < 70:
        pick["direction"] = "SHORT" if pick["direction"] == "LONG" else "LONG"
        pick["entry_notes"] = (pick.get("entry_notes","") + " [A-TIER INVERTED]").strip()
    return pick
```

**Do not ship this.** Better: add `st_fear_greed_contrarian` and
`st_obv_support_divergence` to `BLOCKED_SOURCE_SYSTEMS` after running the
mandated `tools/mutation_analysis.py` per
`docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` and
`docs/MUTATION_THREE_AXIS_PROTOCOL.md` (CLAUDE.md requires this before
strategy demotion).

---

## 2. Task 2 — ETF edge and `intermarket-flow-scout`

### 2.1 Statistical teeth

ETF last20 recomputed from payload: **17/20**. Wilson 95% CI =
**[63.96%, 94.76%]**. Binomial two-sided p vs 50/50 = **0.0026** — real
at p<0.01. But:

- All-time ETF stats in same payload (`performance.by_asset_class.ETF`):
  **36/69 closed = 52.2%**, PF 1.05, expectancy +0.06.
- Delta between the last-20 window (85%) and lifetime (52%) is
  **~33 ppt**, which is a big regime shift. Most plausible explanation:
  equity ETFs riding the recent risk-on tape where
  `intermarket-flow-scout` is tuned to fire.

### 2.2 Where `intermarket-flow-scout` lives

There is **no dedicated** `intermarket_flow_scout.py` module. The
strategy is implemented inline in
`KIMI_RISEOFTHECLAW/live_scanner.py`:

- Registry entry: `live_scanner.py:1525–1536` — name
  "Intermarket Cross-Asset Flow", category "stock", tier "SCOUT",
  universe `SPY, QQQ, IWM, XLK, XLF, XLE, ARKK, SOXX, XBI`.
- Signal function: `live_scanner.py:4380–4413`
  (`signal_intermarket_flow`).
- Dispatch map: `live_scanner.py:5245`
  (`"intermarket-flow-scout": signal_intermarket_flow`).
- Intermarket feature builder:
  `live_scanner.py:7385+` (`compute_intermarket_signals`) populates
  `all_data["__intermarket__"]` with `risk_on_score`, `credit`,
  `dollar`, `safe_haven`.

### 2.3 Plain-English logic

Per `signal_intermarket_flow`:

1. Requires ≥21 bars and a populated `__intermarket__` dict.
2. Pulls cross-asset `risk_on_score` (0–100), `credit` (tight/neutral/wide),
   `dollar` (weak/neutral/strong).
3. Threshold = `max(65 - drought*4, 50)`. I.e. default needs risk_on ≥ 65.
4. Requires `credit ∈ {"tight","neutral"}`. Strong dollar = −5 penalty on
   the effective score; weak dollar = +3; else 0.
5. If effective score still clears the threshold **and** the symbol is
   above its 20-day SMA and 5-day return > −1%, emit BUY.

Plain: *"Go long an equity-beta ETF only when the broad risk-on signal
(SPY/TLT slope + HYG spread + DXY) is 'risk-on' and the ETF itself is
trending up."* It is a **regime filter + simple trend confirm**, not a
pair trade / rotation spread. It cannot go short.

### 2.4 Backtest / validation docs

Grep found **no** standalone backtest file for `intermarket-flow-scout`
(no `backtest_intermarket*`, no entry in
`KIMI_CLAW_RESEARCH_FEB162026/backtest_results/` that I could locate by
name). Registered only through live_scanner's dispatch. Treat its 17/20
as *observational live-forward only.* This is a red flag: the edge has
no paper-backtest to anchor Wilson estimates against.

### 2.5 Currently running in GHA?

Yes — via `.github/workflows/backtest-and-deploy.yml`
(triggers on changes to `KIMI_RISEOFTHECLAW/live_scanner.py` and runs
`python live_scanner.py` in that directory, steps at lines 69–80). Also
referenced by `kimi-feb172026-live.yml`,
`torontoevent-deploy-riseoftheclaw.yml`, and
`riseoftheclaw-weekly-backtest.yml`.

---

## 3. Task 3 — Paper-trade plan for ETFs + Equities

### 3.1 Brokerage integrations already wired

Repo's `paper_trading/` is an **internal paper-trade simulator** (SQLite
+ JSON), not a brokerage plug-in: `paper_trading/db.py`,
`paper_trading/models.py`, `paper_trading/data/paper.db`. No Alpaca /
IBKR adapters found.

External paper trading is via **TradingView MCP** with the accounts
listed in `.claude/skills/tv-paper-trade/SKILL.md`: `SCALPER`, `TESTER`,
`TRUSTOURSCORE`, `zerounderscore`, `BROKIE`. Those are the available
"paper brokers" for ETF+equity execution.

### 3.2 ETF paper-trade plan (anchor: `intermarket-flow-scout`)

- **Universe:** `SPY, QQQ, IWM, XLK, XLF, XLE, ARKK, SOXX, XBI`
  (exact registry in live_scanner.py:1532–1535).
- **Account:** `TESTER` (isolate from `zerounderscore` live-quality book).
- **Sizing:** 1.5% risk per trade, max 4 concurrent = 6% gross ETF
  exposure. Reason: ETF avg_win in payload is 2.56%, avg_loss 2.66%
  (near 1:1), so edge has to come from WR.
- **Daily cap:** 2 new entries / day. Stop trading for the day after 2
  consecutive losses.
- **Stop / TP:** use strategy's own SMA20 break as trailing stop; fixed
  TP at 1.5×ATR(14). Hard stop at −3% regardless.
- **EV estimate at realized stats (85% WR, avg_win 2.56, avg_loss 2.66):**
  EV/trade = 0.85·2.56 − 0.15·2.66 ≈ **+1.78% per trade**. At 2 trades/day
  × ~20 trading days × 1.5% risk sizing, expected monthly ≈ **+10–12%**
  on deployed equity *if the WR holds*, which it almost certainly will
  not at 85%.
- **EV estimate at lifetime stats (52.2% WR, PF 1.05):** essentially
  break-even (+0.06% expectancy). Realistic monthly EV: **0 to +1%.**
  Plan for the lifetime number, be happy if recent regime persists.

### 3.3 Equity paper-trade plan (anchor: `stocks_rsi2_pullback`)

- **Current last-20 reality:** 11/20 = 55% (Wilson LB 34.2%), only 2/20
  are `stocks_rsi2_pullback`. Edge claim weaker than ETFs.
- **Universe:** large-cap S&P 500 components above 200-SMA, per standard
  RSI-2 pullback rules.
- **Sizing:** 1.0% risk per trade, max 3 concurrent. Half the ETF size
  because statistical edge is weaker.
- **Stop / TP:** classic Connors RSI2 — exit when close > 5-SMA or after
  5 bars; stop at entry −2×ATR(10).
- **Daily cap:** 2 entries/day.
- **Monthly EV at payload lifetime (52.9% WR, PF 1.48, expectancy
  +0.75%):** ~6–10 trades/month × +0.75% × 1% risk → ~**+0.5% to +0.8%
  of account** — modest, matches its profile as a filler strategy.

### 3.4 Overfitting / survivorship risk

20 trades is tiny. Rough rule: you need **n ≥ 60** before a Wilson CI
tightens enough to distinguish a 60% strategy from a 50% one at 95%
confidence. Mitigation:

1. Keep the 17/20 ETF record visible but require a **separate forward
   sample of 40 new `intermarket-flow-scout` trades** before any live
   sizing (target: LB above 60%).
2. Track per-strategy WR inside the ETF bucket — if the 85% is all
   `intermarket-flow-scout` (5/20) plus a lucky handful of
   `quality-minus-junk` / `adx-trend-scout`, edge does not generalize.
3. Force a backtest in `KIMI_RISEOFTHECLAW/` covering at minimum the
   2023–2025 SPY/QQQ bear+bull window to prove regime robustness; edge
   that only works in the last 60 days is not edge.

### 3.5 Kill switches (when to stop paper-trading)

Stop `intermarket-flow-scout` paper-trade if **any** of these trip in
the next 40 forward trades:

- Rolling-20 WR falls below **55%** (Wilson LB drops under the lifetime
  52.2% ETF baseline).
- PF < 1.10 over any 20-trade window.
- Max drawdown > 5% of paper equity.
- Two consecutive weeks with <1 qualifying entry (signal extinction).
- Lifetime ETF WR in `performance.by_asset_class.ETF` drops below 50%.

Stop `stocks_rsi2_pullback` paper-trade if:

- Rolling-20 WR < 45% for the strategy specifically (not the asset class).
- PF < 1.00 for 30 trades.
- `BLOCKED_SOURCE_SYSTEMS` expansion is proposed for it.

### 3.6 Confirmatory actions before live capital

1. Export closed ETF picks and run `tools/mutation_analysis.py` per
   `docs/MUTATION_THREE_AXIS_PROTOCOL.md` to confirm regime
   dependence.
2. Build a 1-file backtest at `KIMI_RISEOFTHECLAW/backtest_intermarket_flow.py`
   (missing today) covering 2020–2025 with walk-forward windows.
3. Re-pull last-20 ETF stats in 14 days; if WR mean-reverts to 55–65%
   (expected), size to that number, not 85%.

---

## Appendix — sources cited

- `audit_dashboard/data/dashboard_data.json` — all numeric claims; 3,500
  `picks.recent_closed` rows loaded at 2026-04-18.
- `audit_dashboard/template.html:4954–4970` — tier bucket logic.
- `audit_dashboard/template.html:4972+` — `renderCryptoPanel`.
- `audit_trail/dashboard_generator.py:13173–13190` — HF conviction tier.
- `KIMI_RISEOFTHECLAW/live_scanner.py:1525–1536, 4380–4413, 5245,
  7385+` — `intermarket-flow-scout` definition and signal.
- `alpha_engine/emergency_mutations.py:79, 259, 567` — strategy registry
  cross-refs.
- `.github/workflows/backtest-and-deploy.yml:19–80, 193–207` — GHA
  execution path.
- `CLAUDE.md` — strategy-demotion protocol requirements.
- `.claude/skills/tv-paper-trade/SKILL.md` — paper trading accounts.
