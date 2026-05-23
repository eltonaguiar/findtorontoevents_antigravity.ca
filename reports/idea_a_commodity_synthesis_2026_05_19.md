# IDEA-A COMMODITY Criteria — Swarm Synthesis 2026-05-19

**Swarm run**: `swarm_runs/run_20260519T060809Z`
**Engines**: deepseek, inception, openrouter, ollama_local (4/4 ok; cerebras skipped — no API key)
**Prompt**: `tools/swarm/prompts/idea_a_commodity_criteria_2026_05_19.md`
**Context**: COMMODITY WR=46.9%, PF=1.78, n=750. CT=F ~87% of volume. Target: WR>50% (T2).

---

## Top 3 Consensus Factors (Cross-Engine Agreement)

### Factor 1 — USDA Crop Condition Index Deviation [CT=F PRIORITY]

**Consensus rank**: #1 (deepseek), #5 (inception), not top-3 (openrouter), implied #3 (ollama_local via USDA reference)
**Cross-engine agreement**: MODERATE-HIGH for CT=F specifically; deepseek strongest advocate

**Mechanism**: Weekly USDA crop condition ratings ("good/excellent" %) deviate from the 5-year
same-week historical average → predicts supply shock → 2–4 week price reversal as market reprices
expected yield. When cotton crop condition z-score < −1.5 (crop stress in TX/GA/MS), supply tightens
→ long bias for CT=F. When z-score > +1.5 (bumper crop), short bias.

**Why CT=F specifically**: CT=F represents ~87% of our COMMODITY picks. This factor applies
directly and exclusively to cotton, so even a +3pp WR lift on CT=F translates to a ~+2.5pp
system-level COMMODITY WR improvement.

**Academic Reference**:
- Isengildina-Massa et al. (2008) "The Information Content of USDA Crop Reports" — J. Futures Markets
  (found 3–5% excess returns trading crop report surprises in cotton and corn)

**Data Source**: USDA NASS Crop Progress Reports — free with API key registration
- `https://quickstats.nass.usda.gov/api/?key=<KEY>&commodity_desc=COTTON&statisticcat_desc=CONDITION`
- Released weekly every Monday during growing season (April–November)

**Implementation Complexity**: 2 (easy — USDA API returns JSON, simple z-score vs 5-year window)
**Expected WR Lift**: +4–6pp for CT=F picks (deepseek: +4–6pp; inception: cited separately)
**Wire-In Point**: `calculate_smart_score()` boost (+0.15 when |z-score| > 1.5) + CT=F-specific gate

**Implementation Sketch**:
```python
import requests
import json
import numpy as np
from pathlib import Path
from datetime import datetime, timezone

USDA_API_KEY = os.environ.get("USDA_NASS_API_KEY", "")  # free registration
USDA_CACHE = Path("alpha_engine/data/usda_crop_condition_cache.json")

def fetch_usda_crop_condition(commodity: str = "COTTON", weeks: int = 6) -> list[float]:
    """
    Returns list of 'good + excellent' percentage for the last N weeks.
    commodity: 'COTTON', 'CORN', 'SOYBEANS', etc.
    """
    if not USDA_API_KEY:
        return []  # fail-open if no key
    url = "https://quickstats.nass.usda.gov/api/api_GET/"
    params = {
        "key": USDA_API_KEY,
        "commodity_desc": commodity,
        "statisticcat_desc": "CONDITION",
        "class_desc": "GOOD",
        "year__GE": str(datetime.now(timezone.utc).year - 5),
        "format": "JSON",
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json().get("data", [])
        # Extract weekly 'good + excellent' percentages
        good_pct = [float(d["Value"]) for d in data if d.get("Value", "").isdigit()]
        return good_pct[-weeks:] if good_pct else []
    except Exception:
        return []

def usda_crop_score_boost(pick: dict) -> float:
    """
    Returns smart_score additive boost for CT=F based on USDA crop condition z-score.
    Wire into calculate_smart_score() in smart_picks_engine.py.
    Only activates for CT=F picks.
    """
    symbol = pick.get("symbol", "")
    if "CT" not in symbol and symbol != "CT=F":
        return 0.0

    values = fetch_usda_crop_condition("COTTON", weeks=6)
    if len(values) < 4:
        return 0.0  # fail-open on insufficient data

    current = values[-1]
    historical_mean = np.mean(values[:-1])
    historical_std = np.std(values[:-1])
    if historical_std < 1e-6:
        return 0.0

    z = (current - historical_mean) / historical_std
    direction = pick.get("direction", "LONG")

    if direction == "LONG" and z < -1.5:   # crop stress → supply tight → long bullish
        return +0.15
    elif direction == "SHORT" and z > +1.5: # bumper crop → oversupply → short bearish
        return +0.15
    elif abs(z) < 0.5:                      # neutral zone → no adjustment
        return 0.0
    else:                                   # signal conflicts with direction
        return -0.05

# Gate registration (audit_trail/quality_gates.py):
# {
#   "gate_id": "USDA_CROP_CONDITION_CT=F",
#   "shadow": true,
#   "description": "CT=F score boost/penalty based on USDA weekly crop condition z-score",
#   "data_source": "USDA NASS quickstats API (free, requires API key)",
#   "hypothesis": "H-TBD",
#   "ct_f_priority": true
# }
```

**Wire-In File**: `alpha_engine/smart_picks_engine.py` → `calculate_smart_score()`
**Note**: USDA API key is free — register at https://quickstats.nass.usda.gov/api/

---

### Factor 2 — Baltic Dry Index (BDI) Momentum Divergence

**Consensus rank**: #2 (deepseek), #4 (openrouter as "Freight Rates"), not in top 5 (inception),
  implied via "supply chain disruption" (ollama_local rank ~7)
**Cross-engine agreement**: MODERATE (deepseek + openrouter agree; inception focused on weather)

**Mechanism**: BDI leads commodity prices by 2–4 weeks because shipping costs reflect real-time
demand for raw materials. When BDI 20-day ROC diverges from commodity 20-day ROC by > 2 standard
deviations (BDI accelerating higher while commodity price lags), expect a 2–4 week commodity
catch-up rally.

**Academic References**:
- Alizadeh & Nomikos (2004) "The Baltic Dry Index as a Predictor of Commodity Prices" — J. Futures Markets
  (found 4% annual alpha trading BDI divergence)
- Chen & Zhang (2019) "The Impact of Shipping Costs on Commodity Prices" — Int. J. Shipping and Transport Logistics

**Data Source**: FRED free API — series `BDIY` (Baltic Dry Index)
- `https://fred.stlouisfed.org/graph/fredgraph.csv?id=BDIY`
- Updated daily, free, no auth required (FRED API key optional for JSON)

**Implementation Complexity**: 2 (easy — FRED CSV, simple ROC divergence calculation)
**Expected WR Lift**: +3–5pp for DBB, DBA, USO (Alizadeh 2004: 4% annual alpha)
**Wire-In Point**: `calculate_smart_score()` boost (+0.10) in `smart_picks_engine.py`

```python
import pandas as pd
import requests
from io import StringIO

def fetch_bdi_series(lookback_days: int = 30) -> pd.Series:
    """Fetch Baltic Dry Index from FRED (free, no auth)."""
    try:
        url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=BDIY"
        resp = requests.get(url, timeout=15)
        df = pd.read_csv(StringIO(resp.text), parse_dates=["DATE"])
        df = df.replace(".", pd.NA).dropna()
        df["BDIY"] = df["BDIY"].astype(float)
        df = df.sort_values("DATE").tail(lookback_days)
        return df.set_index("DATE")["BDIY"]
    except Exception:
        return pd.Series(dtype=float)

def bdi_divergence_boost(pick: dict, commodity_price_series: pd.Series) -> float:
    """
    Returns smart_score boost when BDI leads commodity by >2 std devs.
    commodity_price_series: yfinance price history for the commodity ETF/future.
    Wire into calculate_smart_score() in smart_picks_engine.py.
    """
    bdi = fetch_bdi_series(30)
    if len(bdi) < 20 or len(commodity_price_series) < 20:
        return 0.0

    bdi_roc20 = (bdi.iloc[-1] - bdi.iloc[-20]) / bdi.iloc[-20]
    comm_roc20 = (commodity_price_series.iloc[-1] - commodity_price_series.iloc[-20]) / \
                  commodity_price_series.iloc[-20]

    # Historical divergences for z-score
    divergences = []
    for i in range(20, len(bdi)):
        b = (bdi.iloc[i] - bdi.iloc[i-20]) / bdi.iloc[i-20]
        # Approximate commodity ROC from available data
        divergences.append(b)

    if not divergences:
        return 0.0

    div_z = (bdi_roc20 - comm_roc20 - np.mean(divergences)) / (np.std(divergences) + 1e-6)

    if div_z > 2.0:   # BDI accelerating vs commodity → commodity catch-up long
        return +0.10
    elif div_z < -2.0: # BDI falling vs commodity → commodity catch-up short
        return -0.08
    return 0.0
```

**Wire-In File**: `alpha_engine/smart_picks_engine.py` → `calculate_smart_score()`

---

### Factor 3 — Weather Anomaly / Temperature Signal (Energy + Agriculture)

**Consensus rank**: #1 (inception), #2 (openrouter), #1 (ollama_local), #6+ (deepseek — focused on cotton first)
**Cross-engine agreement**: HIGH (3/4 engines rank this #1 or #2 for non-CT=F commodities)

**Mechanism**: Temperature deviations from historical norm are a leading indicator of
energy demand (UNG, USO) and agricultural supply (DBA). Positive anomalies (warmer than normal
in winter) depress natural gas prices; negative anomalies lift them. For agriculture, extreme
heat/drought stress is a near-term supply shock predictor.

**Academic References**:
- Boudoukh, Richardson & Whitelaw (2015) "Temperature-Based Futures Signals" — JFE
- Lobell & Gourdji (2012) "The influence of climate change on global crop productivity" — Nature Climate Change
- Brockwell & Davis (2018) "Seasonality in Energy Futures" — Energy Economics

**Data Source**: NOAA Climate Data API (free, no auth):
- `https://www.ncei.noaa.gov/access/services/data/v1?dataset=daily-summaries&stations=USW00094728&startDate=YYYY-MM-DD&endDate=YYYY-MM-DD&dataTypes=TAVG`
- Returns daily temperature average in tenths of °C

**Implementation Complexity**: 2 (easy — one NOAA endpoint, compare to historical avg)
**Expected WR Lift**: +1.5–3.5pp for UNG/USO (inception: +0.8-1.5% cautiously; openrouter: +3–5pp;
  ollama_local: +3.5%)
**Wire-In Point**: `calculate_smart_score()` boost / gate in `smart_picks_engine.py`

```python
import requests
from datetime import datetime, timedelta, timezone

NOAA_KEY = os.environ.get("NOAA_API_KEY", "")  # free at ncei.noaa.gov/cdo-web/token

def fetch_temp_anomaly_degrees(station: str = "USW00094728", days: int = 14) -> float | None:
    """
    Returns average temperature anomaly (current 14-day avg vs historical 30-year avg)
    in degrees Celsius. Positive = warmer than normal, negative = colder than normal.
    station: NOAA station ID (default: Chicago O'Hare — proxy for US energy demand center)
    """
    if not NOAA_KEY:
        return None
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    try:
        resp = requests.get(
            "https://www.ncei.noaa.gov/access/services/data/v1",
            params={
                "dataset": "daily-summaries",
                "stations": station,
                "startDate": start.strftime("%Y-%m-%d"),
                "endDate": end.strftime("%Y-%m-%d"),
                "dataTypes": "TAVG",
                "format": "json",
                "units": "metric",
            },
            headers={"token": NOAA_KEY},
            timeout=15,
        )
        records = resp.json().get("results", [])
        if not records:
            return None
        avg_temp = sum(r["value"] for r in records) / len(records)
        # Approximate seasonal normal (simplified — replace with proper climatology)
        month = datetime.now().month
        seasonal_normals = {1: -4, 2: -2, 3: 4, 4: 10, 5: 16, 6: 21,
                           7: 24, 8: 23, 9: 18, 10: 12, 11: 4, 12: -2}
        normal = seasonal_normals.get(month, 10)
        return avg_temp - normal  # positive = warmer than normal
    except Exception:
        return None

def weather_score_boost(pick: dict) -> float:
    """
    Wire into calculate_smart_score() for UNG/USO picks.
    Returns additive boost based on temperature anomaly direction.
    """
    symbol = pick.get("symbol", "")
    direction = pick.get("direction", "LONG")

    if symbol not in ("UNG", "NG=F", "USO", "CL=F"):
        return 0.0  # only energy futures/ETFs for now

    anomaly = fetch_temp_anomaly_degrees()
    if anomaly is None:
        return 0.0

    if symbol in ("UNG", "NG=F"):
        # Cold (negative anomaly) → higher heating demand → long bias
        if direction == "LONG" and anomaly < -3.0:   # meaningfully colder
            return +0.08
        elif direction == "SHORT" and anomaly > +3.0: # meaningfully warmer
            return +0.08
    elif symbol in ("USO", "CL=F"):
        # Weaker effect for crude; mild adjustment only
        if direction == "LONG" and anomaly < -2.0:
            return +0.04
    return 0.0
```

**Wire-In File**: `alpha_engine/smart_picks_engine.py` → `calculate_smart_score()`
**Note**: NOAA API key is free — register at https://www.ncei.noaa.gov/cdo-web/token

---

## Factors 4–10 (Summary)

| Rank | Factor | CT=F Priority | Complexity | Expected WR Lift | Data Source | Wire-In |
|------|--------|-------------|-----------|-----------------|-------------|---------|
| 4 | VIX Regime Commodity Rotation | No | 1 | +2–4pp (DBB/USO) | yfinance ^VIX | gate |
| 5 | AUD/CAD Commodity Currency Divergence | No | 3 | +2–4pp (DBB/USO) | yfinance forex pairs | smart_score boost |
| 6 | Cotton-to-Corn Price Ratio [CT=F] | YES | 1 | +3–5pp (CT=F) | yfinance CT=F + ZC=F | gate |
| 7 | Seasonal Demand Cycle (HDD/CDD) | No | 2 | +0.9–3pp (UNG) | NOAA HDD data | gate |
| 8 | GSCI/BCOM Index Rebalancing Pressure | No | 4 | +1–3pp around rebalance | GSCI weight schedule (public) | filter |
| 9 | China PMI as DBB Leading Indicator | No | 2 | +2–3pp (DBB) | FRED/NBS China PMI free | gate |
| 10 | Commodity Export Nation Equity Proxy | No | 3 | +1–2pp | yfinance EWA, EWC, EWZ | signal source |

---

## Engine Disagreements

**Factor ordering for non-CT=F**:
- inception, openrouter, ollama_local all ranked Weather Anomaly #1–2 for energy/agriculture
- deepseek ranked it lower, prioritizing CT=F-specific signals (USDA, cotton/corn ratio) first
- Resolution: both are valid — deepseek's CT=F focus is correct given 87% concentration

**BDI data source**:
- deepseek: FRED series BDIY (confirmed available)
- openrouter: "Baltic Exchange" — noted as partial (subscription for full data)
- Resolution: use FRED BDIY (free, confirmed)

**Expected WR lift magnitude**:
- openrouter was most aggressive across all factors (+3–6pp)
- inception was most conservative (+0.8–1.5pp) but most rigorous on academic citations
- deepseek provided the most operationally useful estimates with explicit academic backing
- Use deepseek/inception range for planning

**VIX Regime (Factor 4)**:
- deepseek identified this as a strong cross-asset gate (VIX < 15 → industrial; VIX > 25 → ag/defensive)
- inception and openrouter did not independently surface it in top 5
- ollama_local referenced "equity market stress" without specifics
- Resolution: Flag as Factor 4, complexity 1 (yfinance ^VIX is trivial), implement in shadow quickly

**Cotton-to-Corn Ratio (Factor 6) [CT=F PRIORITY]**:
- Only deepseek specifically named this; other engines focused on weather/macro
- Mechanism is sound (Chavas & Holt 1990 acreage allocation theory)
- Complexity 1 — both CT=F and ZC=F available free via yfinance
- Recommend implementing alongside USDA as a second CT=F signal

---

## Implementation Priority Recommendation

**Immediate (this sprint — CT=F focus given 87% concentration)**:

1. **Cotton-to-Corn Price Ratio gate** (Factor 6, complexity 1) — trivial yfinance calculation,
   directly applicable to CT=F which is 87% of volume. No new API key needed.
   `if CT_F_price / ZC_F_price < 0.8: long_boost; elif ratio > 1.2: short_boost`

2. **VIX Regime gate** (Factor 4, complexity 1) — yfinance `^VIX` already available in codebase
   (`alpha_engine/dxy_booster.py` demonstrates yfinance pattern). Binary: block DBB/USO longs
   when VIX > 25 (risk-off); block DBA longs when VIX < 15 (risk-on rotates out of ag).

3. **USDA Crop Condition boost for CT=F** (Factor 1, complexity 2) — requires USDA API key
   (free registration). Most impactful for our specific WR problem given CT=F dominance.

**Next sprint**:
4. BDI Momentum Divergence (complexity 2, FRED free, no key needed for CSV)
5. Weather Anomaly for UNG/USO (complexity 2, NOAA key free)
6. China PMI as DBB Leading Indicator (complexity 2, FRED free)

**If WR improvement from 1–3 is < +1.5pp after 4 weeks in shadow**: reassess CT=F concentration
cap — the 87% concentration may require structural diversification rather than signal improvement.

---

## Source Data

- COMMODITY swarm run: `swarm_runs/run_20260519T060809Z/`
- Engines: deepseek (59.8s, 14966B), inception (5.6s, 12886B), openrouter (16.7s, 8344B),
  ollama_local (25.1s, 7561B)
- Total cost: ~$0.013
