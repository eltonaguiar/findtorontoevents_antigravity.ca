# Regime-Change Detection + Kill Switches — Grok-4 Deep Dive (2026-05-31)

**Model:** grok-4-latest (xAI API)
**Context:** 24-strategy paper-pilot, 8 asset classes, emission starts 13:30 UTC 2026-06-01
**Asked by:** session wnkqcqck5 / 24-strategy harness prep

## 3-Line Operator Summary

1. **Kill triggers (any 2 = KILL, any 1 = PAUSE 3d):** VIX>35 or ΔVIX_1d>+8, 20d/60d RV ratio >1.8 or <0.6, 20d pairwise corr <0.15 or >0.75, bid-ask spread z-score >+3.5, strategy 5d DD <-3.5σ.
2. **Asset-class kill map is non-uniform:** trend/CTA dies in chop (RV ratio >1.8), carry dies in corr-collapse, crypto kills everything-except-basis on VIX>40.
3. **Lookbacks tiered:** 5-20d fast filter (VIX/spreads/PnL), 60d RV vs 252d baseline for regime, 20d rolling correlation (Diebold-Yilmaz). Re-entry requires 5d all-clear.

---

## Distilled Bullet Spec (wire into docs/PAPER_PILOT_HARNESS.md)

### Macro Regime Kill Signals (5)
- **VIX:** level > 35 OR Δ1d > +8
- **Correlation:** 20d avg pairwise corr < 0.15 (breakdown) OR > 0.75 (flight-to-quality)
- **Vol regime switch:** 20d RV / 60d RV > 1.8 (vol expansion) OR < 0.6 (vol crush)
- **Liquidity shock:** median bid-ask spread z-score > +3.5 (cross-asset)
- **Strategy DD:** 5d cumulative return < -3.5σ of 252d history (per-strategy)

### Per-Asset-Class Kill Map
| Asset Class | Kill Rule |
|---|---|
| EQUITY / ETF | kill trend/momentum on corr collapse OR vol switch; kill short-vol on VIX spike |
| FUTURES / COMMODITY | kill CTAs on RV ratio > 1.8 (chop regime) |
| FOREX | kill carry on liquidity z > 3 OR corr > 0.75 |
| CRYPTO | kill everything except basis arb on VIX > 40 OR RV switch |
| BOND / PREDICTION_MARKETS | kill directional on DD trigger only |

### Lookback Windows
- **Fast filter:** 5-20d (VIX, spreads, PnL)
- **Regime filter:** 60d RV vs 252d baseline (avoids >80% false alarms vs 20d)
- **Correlation:** 20d rolling (Diebold-Yilmaz 2012 spillover robustness)

### Pause-vs-Kill Decision Tree
```
severity = count of triggered signals
if severity == 1 and persists < 2 days  -> PAUSE 3 trading days
elif severity >= 2 OR signal persists > 3 days -> KILL (manual re-enable)
elif strategy DD < -4σ -> immediate KILL
Re-entry: requires 5 consecutive days with all triggers cleared
```

## Python Pseudo-code (paste into harness)

```python
# daily at T-1 close
def regime_kill(asset_class, strat_type, data):
    vix, dvix = data['VIX'], data['dVIX']
    rv_ratio = data['RV_20'] / data['RV_60']
    corr = data['pairwise_corr_20']
    liq_z = data['spread_z_20']
    strat_dd = data['strat_5d_z']

    kills = []
    if vix > 35 or dvix > 8:
        kills.append('VIX')
    if rv_ratio > 1.8 or rv_ratio < 0.6:
        kills.append('VOL_REGIME')
    if (asset_class in ['EQUITY', 'FOREX'] and corr < 0.15) or corr > 0.75:
        kills.append('CORR')
    if liq_z > 3.5:
        kills.append('LIQ')
    if strat_dd < -3.5:
        kills.append('DD')

    if len(kills) >= 2 or 'DD' in kills:
        return 'KILL'
    elif len(kills) == 1:
        return 'PAUSE_3D'
    return 'OK'
```

## Citations
- **Ang & Bekaert (2002)** "Regime Switches in Interest Rates" — two-state Markov evidence for vol/corr jumps.
- **Diebold & Yilmaz (2012)** "Better to Give than to Receive: Forecast-Based Measurement of Volatility Spillovers" — correlation breakdown / spillover timing.
- **Hamilton (1989)** Markov-switching autoregressive model — baseline for RV regime detection.
- **Cont (2001)** "Empirical properties of asset returns: stylized facts and statistical issues" — liquidity and vol clustering thresholds.

---

## Raw Grok-4 Response

**Regime Signals (KILL triggers)**
1. VIX level + jump: VIX > 35 or ΔVIX_1d > +8 (Ang-Bekaert 2002 regime-switch evidence).
2. Cross-asset correlation collapse: 20-day avg pairwise corr < 0.15 (equity/credit/FX) or > 0.75 (flight-to-quality).
3. Realized vol regime switch: 20d RV / 60d RV > 1.8 or < 0.6 (HMM two-state vol model).
4. Liquidity shock: median bid-ask spread z-score > +3.5 across asset class.
5. Strategy P&L drawdown: 5d cumulative return < -3.5σ of 252d history (strategy-specific).

**Asset-class × Strategy kill map**
- EQUITY / ETF: kill trend/momentum on corr collapse or vol switch; kill short-vol on VIX spike.
- FUTURES / COMMODITY: kill CTAs on RV ratio > 1.8 (choppy regime).
- FOREX: kill carry on liquidity z > 3 or corr > 0.75.
- CRYPTO: kill everything except basis arb on VIX > 40 or RV switch.
- BOND / PREDICTION_MARKETS: kill directional on drawdown trigger only.

**Lookback windows**
- Fast filter: 5-20d (VIX, spreads, P&L).
- Regime filter: 60d RV vs 252d baseline (avoids >80% false alarms vs 20d).
- Correlation: 20d rolling (Diebold-Yilmaz 2012 spillover robustness).

**Pause-vs-Kill tree**
```
if severity == 1 (single signal, <2d): PAUSE 3 trading days
elif severity >= 2 or signal persists >3d: KILL (manual re-enable only)
elif strategy DD < -4σ: immediate KILL
```
Re-entry requires 5d confirmation that all triggers cleared.

**Citations**
- Ang & Bekaert (2002) "Regime Switches in Interest Rates" - two-state Markov evidence for vol/corr jumps.
- Diebold & Yilmaz (2012) "Better to Give than to Receive" - spillover/corr breakdown timing.
- Hamilton (1989) Markov-switching autoregressive model - baseline for RV regime detection.
- Cont (2001) "Empirical properties of asset returns" - liquidity and vol clustering thresholds.
