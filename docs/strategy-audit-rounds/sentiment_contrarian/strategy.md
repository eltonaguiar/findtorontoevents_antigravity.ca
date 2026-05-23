# sentiment_macro_contrarian — Strategy Spec

Status: opt-in sidecar (not yet wired into production scanner).
Module: `alpha_engine/sentiment_macro_contrarian.py`
Baseline: `st_fear_greed_contrarian` — PF 4.22 / WR 75% / n=96
(`reports/forward_edge_audit_2026-05-02.json`).

## Thesis

`st_fear_greed_contrarian` works because it buys CRYPTO during retail capitulation
(Alternative.me Fear/Greed Index < 25) while filtered to symbols above their
200-day SMA — i.e. capitulation in an uptrend. That filter is half the story.
The other half (which the original strategy does NOT control for) is the macro
regime: panic into a strong-USD/risk-off tape historically takes longer to mean-
revert and the SL hits more often. Panic into a weak-USD reflation regime
mean-reverts fast.

This strategy generalizes the contrarian signal to ALL asset classes and adds a
macro-alignment gate. If FRED data is unavailable, we degrade to a sentiment-only
signal at lower confidence (no hard fail).

## Entry rules

CRYPTO (BTC-USDT, ETH-USDT, SOL-USDT, etc.):
- BUY when `fear_greed_index < 25` (extreme fear) AND
- `regime.usd != "strong"` (DTWEXBGS 30d delta < 1.5%)

EQUITY (TIER1 of `alpha_engine/elite_scorer.py`: AAPL, MSFT, ...) and ETF (SPY, QQQ, IWM, ...):
- BUY when `VIXCLS > 25` (extreme fear) AND
- `regime.curve != "inverted"` (T10Y2Y spread > -0.05)
- SELL/SHORT when `VIXCLS < 12` (complacency) AND
- `regime.vol == "low"` AND
- `regime.curve == "inverted"` (late-cycle complacency setup)

## Exit rules

- CRYPTO: TP +5%, SL −3% (RR 1.67)
- EQUITY/ETF: TP ±4%, SL ±2.5% (RR 1.6)
- No time stop in v1; expected hold 5-15 trading days.

## Confidence model

```
sentiment-only fire (macro absent / unknown): 0.55-0.62
sentiment + macro alignment (BOTH hot):       0.65-0.78
+0.05 bonus when FGI < 15 (panic) or VIX > 35 (panic)
hard cap: 0.78
```

## Pseudocode

```
fgi   = load_fear_greed(kwargs, audit_dashboard/data/fear_greed_history.json)
macro = fred_macro_context.get_macro_context()  # cached 1h
for symbol, df in data.items():
    entry = df["Close"].iloc[-1]
    if is_crypto(symbol):
        if fgi < 25 and macro.regime.usd != "strong":
            emit BUY  CRYPTO  conf=0.70 if usd=="weak" else 0.58
    elif is_equity_or_etf(symbol):
        if vix > 25 and macro.regime.curve != "inverted":
            emit BUY  EQUITY|ETF  conf=0.70 if curve in ("flat","steep") else 0.58
        elif vix < 12 and macro.regime.vol == "low" and macro.regime.curve == "inverted":
            emit SELL EQUITY|ETF  conf=0.70 (always macro-aligned by definition)
```

## Expected WR justification

The CRYPTO branch inherits the `st_fear_greed_contrarian` n=96 / 75% WR baseline
and ADDS a USD-regime gate. If the gate is non-redundant — i.e. the historical
`fear_greed_contrarian` failures correlate with strong-USD periods — we expect
post-gate WR to land 75-82%. If the gate is fully redundant (all `fgi<25`
periods coincide with weak-USD), WR is unchanged at 75% but we trade FEWER
times (lower drawdown). Either is acceptable.

The EQUITY VIX-spike branch is academically supported (Whaley 2009 "Investor
Fear Gauge"; Black 1976; Bekaert-Hoerova 2014 on uncertainty vs risk-aversion
decomposition of VIX). Base-rate VIX>25-then-mean-revert WR over 1990-2024
SPX = ~62-68% at 4-week horizon. With curve-not-inverted gate (avoids the
2007-2008 / 2000-2002 / 1989-1990 pre-recession setups where VIX spiked
INTO bear markets) we target 65-72%.

The EQUITY complacency-short branch is the highest-conviction macro setup but
fires rarely. 1990-2024 SPX: VIX<12 + 2s10s inverted + low realized vol fired
~3 times pre-recession (1998, 2000, 2007, 2019). Hit rate ~75% but n is
intrinsically tiny.

## Risk register

- Macro snapshot stale: `fred_macro_context` caches 1h; `_safe_fetch` returns
  `[]` on FRED 5xx. Strategy degrades to sentiment-only (no kill).
- FGI feed dead: `audit_dashboard/data/fear_greed_history.json` and the
  Alternative.me URL both unreachable -> strategy emits 0 CRYPTO signals.
- TIER1 set drift: copied locally from `elite_scorer.py` to avoid import
  fragility. Re-sync in a follow-up PR if elite_scorer changes the lists.
- Symbol overlap with `st_fear_greed_contrarian`: until wired, no overlap.
  After wire-up, CRYPTO signals will deduplicate at the scanner consensus
  layer (same path as `crypto_fear_greed_contrarian`).

## Promotion criteria

- 4-week live forward-test n>=40
- WR >= 55% post-fees / post-slippage
- macro-aligned subset PF >= sentiment-only PF + 0.5 (justifies the gate)
- No single symbol >25% of trade volume (avoids `quan_engine_matic`-style
  concentration artifact, see `feedback_quan_engine_matic_positive_artifact.md`)
