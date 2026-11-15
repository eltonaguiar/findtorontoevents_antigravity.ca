# Strategy Shortlist & 10-Step Quantitative Evaluation (`STRATEGY_SHORTLIST.md`)

**Run ID:** `2026-11-15_0725_inspect-wt` | **Seed:** `42` | **Evaluated Trials:** `9` pre-registered strategies across `8` asset classes (`N_repo = 646` historical trials)  
**Reproducible Code & Config:** [run_proof_suite.py](file:///e:/findtorontoevents_antigravity.ca/WIRED_IN/2026-11-15_0725_inspect-wt/experiments/run_proof_suite.py), [experiment_configs.json](file:///e:/findtorontoevents_antigravity.ca/WIRED_IN/2026-11-15_0725_inspect-wt/experiments/experiment_configs.json), [experiment_results.json](file:///e:/findtorontoevents_antigravity.ca/WIRED_IN/2026-11-15_0725_inspect-wt/experiments/experiment_results.json)

> **HONEST PROFITABILITY VERDICT (`PROVEN = 0 / 9`):** Under the non-negotiable 10-step Proof Standard (`WFO`, `DSR >= 0.95 at N=646`, `Holm p < 0.05`, `Block MC`, `2x Cost Safety`, `CAD After-Tax > 0`, `Excess CI != 0`, `Majority Regimes`, `Shuffle Control p < 0.05`, `Tracker`, `Seed=42`), **zero active or systematic strategies pass all 10 gates**. Passive buy-and-hold (`SPY_BH` CAGR `+12.82%`, Sharpe `0.747`; `60/40 SPY/AGG` CAGR `+7.31%`, Sharpe `0.538`, MaxDD `-21.03%`) outperformed every systematic rotation sleeve on raw risk-adjusted Sharpe over `2013-01..2026-10`. Two low-turnover monthly sleeves (`M1`, `E1`) qualify as **`PROMISING (NEAR-MISS)`** (`7/10` gates) for shadow forward tracking, while `CM1` exhibits genuine trend-timing skill (`Shuffle p = 0.0050`, `t = 2.20`, `7/10` gates) but failed pre-registered in-sample WFO (`IS Sharpe = -0.403` during the `2013-2019` commodity bear). All short-term `/audit` pick cohorts (`C1`, `FX1`, `S1`, `MA1`) and `B1` are **`REJECT`**.

---

## 1. Master Comparison Table (Ranked by Gates Passed, Then Sharpe)

| Rank | ID | Asset Class | Strategy Summary & Timeframe | Verdict | Gates (/10) | CAGR Net (Gross Cum / Net Cum) | CAD Tax (TFSA / CG / Ord) | Sharpe / Sortino / Calmar | MaxDD / MaxRec |
|---:|---|---|---|---|---:|---|---|---|---|
| 1 | `M1` | Mutual Funds | 12-1 Dual-Mom + InvVol + 12% VT, `0.15%` MER, Monthly NAV (>=30d hold) | **PROMISING (NEAR-MISS)** | **7/10** | `+7.49%` (`+174.9%` / `+170.0%`) | `+7.49%` / `+5.57%` / `+3.59%` | `0.450` / `0.708` / `0.308` | `-24.36%` / `40m` |
| 2 | `E1` | ETFs | 12-1 Dual-Mom + InvVol + 12% VT, `10 bps` RT, Monthly (21d rebalance) | **PROMISING (NEAR-MISS)** | **7/10** | `+7.31%` (`+174.9%` / `+163.9%`) | `+7.31%` / `+5.44%` / `+3.51%` | `0.436` / `0.684` / `0.300` | `-24.40%` / `40m` |
| 3 | `CM1` | Commodities | GLD/DBC 12-1 Dual-Mom + 12% VT, `20 bps` RT, Monthly | **REJECT** *(IS Bear anomaly)* | **7/10** | `+9.08%` (`+238.8%` / `+230.3%`) | `+9.08%` / `+6.80%` / `+4.42%` | `0.593` / `1.005` / `0.483` | `-18.81%` / `37m` |
| 4 | `MA2` | Multi-Asset (Sleeves) | Inverse-Vol Risk Parity (`E1+B1+CM1+Def`), Monthly (`153m`) | **REJECT** | **7/10** | `+3.99%` (`+68.2%` / `+64.6%`) | `+3.99%` / `+2.95%` / `+1.89%` | `0.269` / `0.445` / `0.317` | `-12.57%` / `36m` |
| 5 | `MA1` | Multi-Asset (`/audit`) | Variant-C Top-6 Selector (`train_n>=20, PF>1.3`, `179d`, `n=237`) | **REJECT** | **5/10** | `+10.50%` (`+9.92%` / `+7.35%`) | `+10.50%` / `+7.66%` / `+4.84%` | `0.754` / `1.223` / `1.582` | `-6.63%` / `69d` |
| 6 | `S1` | Stocks (`/audit`) | Active EQUITY Cohort (`1-14d` swing, `10 bps` extra, `193d`, `n=737`) | **REJECT** *(OOS collapse)* | **5/10** | `+25.94%` (`+28.31%` / `+19.32%`) | `+25.94%` / `+18.86%` / `+11.88%` | `0.927` / `1.454` / `1.351` | `-19.21%` / `143d` |
| 7 | `B1` | Bonds | TLT/IEF/AGG 12-1 Dual-Mom + 10% VT, `10 bps` RT, Monthly | **REJECT** | **5/10** | `+0.74%` (`+12.2%` / `+10.7%`) | `+0.74%` / `+0.44%` / `+0.13%` | `-0.203` / `-0.291` / `0.038` | `-19.53%` / `75m` |
| 8 | `FX1` | Forex (`/audit`) | Clean FX Cohort (`n=158`, `8 bps` spread+swap; `19` EURUSDT & `10` zero stripped) | **REJECT** *(Hard Disable)* | **3/10** | `-1.04%` (`+0.87%` / `-0.35%`) | `N/A (No TFSA)` / `-1.04%` / `-1.04%` | `-1.965` / `-2.624` / `-0.879` | `-1.18%` / `65d` |
| 9 | `C1` | Crypto | BTCUSDT 1h Donchian(48) + EMA(24/168) + 2x/4x ATR, `20 bps` RT + funding (`84d`, `n=16`) | **REJECT** *(Kill / Quarantine)* | **3/10** | `-24.93%` (`-3.32%` / `-6.39%`) | `-24.93%` / `-24.93%` / `-24.93%` | `-2.580` / `-3.726` / `-2.542` | `-9.81%` / `77d` |

---

## 2. Full Phase 5 Statistical, Risk & Distribution Metrics

| ID | Ann Vol | Beta / Treynor / IR | Win Rate / PF / Expectancy | AvgW / AvgL / Payoff / LossStreak | Skew / ExKurt / AC1 / TailR | VaR95 / CVaR95 | Breakeven Cost (Safety Margin) |
|---|---:|---|---|---|---|---|---|
| `M1` | `12.27%` | `0.790` / `0.070` / `+0.063` | `57.58%` / `1.631` / `+0.666%` | `+2.99%` / `-2.49%` / `1.202` / `5` | `-0.020` / `0.562` / `-0.025` / `1.343` | `-5.06%` / `-6.82%` | `243.6 bps` (`16.24x` of `15 bps`) |
| `E1` | `12.27%` | `0.790` / `0.068` / `+0.047` | `57.58%` / `1.613` / `+0.652%` | `+2.98%` / `-2.51%` / `1.189` / `5` | `-0.022` / `0.549` / `-0.024` / `1.334` | `-5.10%` / `-6.84%` | `246.4 bps` (`24.64x` of `10 bps`) |
| `CM1` | `11.68%` | `0.429` / `0.161` / `+0.176` | `70.30%` / `1.991` / `+0.783%` | `+2.24%` / `-2.66%` / `0.841` / `4` | `+0.225` / `1.398` / `+0.156` / `1.534` | `-4.32%` / `-6.42%` | `>=400.0 bps` (`>=20.00x` of `20 bps`) |
| `MA2` | `6.03%` | `0.165` / `0.099` / `-0.308` | `59.48%` / `1.832` / `+0.341%` | `+1.26%` / `-1.01%` / `1.248` / `5` | `+0.823` / `4.932` / `+0.014` / `1.431` | `-2.15%` / `-3.36%` | `>=400.0 bps` (`40.00x` of `10 bps`) |
| `MA1` | `10.71%` | `n/a` / `n/a` / `n/a` | `46.84%` / `1.194` / `+0.316%` | `+4.16%` / `-3.07%` / `1.355` / `14` | `+0.719` / `2.707` / `-0.076` / `1.282` | `-1.06%` / `-1.44%` | `41.5 bps` (`4.15x` of `10 bps`) |
| `S1` | `25.78%` | `n/a` / `n/a` / `n/a` | `46.68%` / `1.104` / `+0.223%` | `+5.09%` / `-4.04%` / `1.261` / `14` | `+0.422` / `2.241` / `+0.125` / `1.070` | `-2.64%` / `-3.36%` | `32.5 bps` (`3.25x` of `10 bps`) |
| `B1` | `7.26%` | `0.699` / `-0.021` / `+0.283` | `79.39%` / `1.165` / `+0.083%` | `+0.74%` / `-2.45%` / `0.302` / `5` | `+0.774` / `6.943` / `+0.099` / `0.877` | `-3.24%` / `-4.87%` | `85.6 bps` (`8.56x` of `10 bps`) |
| `FX1` | `1.78%` | `n/a` / `n/a` / `n/a` | `43.67%` / `0.872` / `-0.039%` | `+0.61%` / `-0.54%` / `1.125` / `13` | `+0.199` / `5.950` / `-0.005` / `1.209` | `-0.13%` / `-0.25%` | `4.2 bps` (`0.53x` of `8 bps`) |
| `C1` | `11.80%` | `0.042` / `n/a` / `+1.387` | `25.00%` / `0.537` / `-0.401%` | `+1.87%` / `-1.16%` / `1.612` / `5` | `+2.320` / `19.681` / `-0.211` / `0.003` | `-1.26%` / `-1.52%` | `0.0 bps` (`0.00x` of `20 bps`) |

*Note on `Sterling` ratio and recovery time:* `M1` Sterling `0.977` (worst trough recovery `30m`), `E1` `0.926` (`30m`), `CM1` `1.405` (`18m`), `MA2` `0.866` (`8m`), `MA1` `4.506` (`46d`), `S1` `3.054` (`6d`), `B1` `0.070` (`24m`), `FX1` `-1.693` (`18d`), `C1` `-4.968` (`6d`).

---

## 3. Phase 4 Proof Standard Gate Matrix (10-Step Verification)

| ID | 1:Temporal | 2:WFO (`IS -> OOS` SR / WFE / Folds+ / Grid+) | 3:DSR (`N=9 / N=646`, Holm, WRC) | 4:MC Block / IID (`+%, p5`) | 5:Friction & CAD Tax | 6:Sig (`t, p`, Boot CI95) | 7:Regimes (`Bull/Bear/Side/HiV/LoV`) | 8:Shuffle Null (`p`) | 9:Tracker | 10:Repro |
|---|---|---|---|---|---|---|---|---|---|---|
| `M1` | **PASS** | **PASS** (`0.20 -> 0.71`, `3.50`, `75%`, `100%`) | **FAIL** (`0.472 / 0.029`, `0.778`, `0.767`) | **PASS** (`93.5% / -5.9%`, IID `93.5%`) | **PASS** (`+5.57%` CG, `16.2x`) | **FAIL** (`1.67, 0.097`, `[-0.07,+1.00]%`) | **PASS** (`4/5 +`; only Sideways `-3.2%`) | **FAIL** (`0.655`) | **PASS** | **PASS** |
| `E1` | **PASS** | **PASS** (`0.18 -> 0.70`, `3.83`, `75%`, `100%`) | **FAIL** (`0.452 / 0.026`, `0.778`, `0.782`) | **PASS** (`91.6% / -10.6%`, IID `92.1%`) | **PASS** (`+5.44%` CG, `24.6x`) | **FAIL** (`1.62, 0.108`, `[-0.09,+0.99]%`) | **PASS** (`4/5 +`; only Sideways `-3.6%`) | **FAIL** (`0.655`) | **PASS** | **PASS** |
| `CM1` | **PASS** | **FAIL** (`-0.40 -> +1.25`, `WFE=0`, `50%`, `100%`) | **FAIL** (`0.678 / 0.083`, `0.265`, `0.327`) | **PASS** (`96.2% / +5.2%`, IID `97.7%`) | **PASS** (`+6.80%` CG, `20.0x`) | **FAIL** (`2.20, 0.029`, `[-0.02,+1.20]%`) | **PASS** (`4/5 +`; only Sideways `-5.1%`) | **PASS** (`0.005`) | **PASS** | **PASS** |
| `MA2` | **PASS** | **PASS** (`0.21 -> 0.37`, `1.78`, `50%`, `n/a`) | **FAIL** (`0.233 / 0.006`, `1.000`, `0.977`) | **PASS** (`79.9% / -14.2%`, IID `80.0%`) | **PASS** (`+2.95%` CG, `40.0x`) | **FAIL** (`0.96, 0.338`, `[-0.16,+0.41]%`) | **PASS** (`4/5 +`; only Sideways `-0.7%`) | **FAIL** (`0.065`) | **PASS** | **PASS** |
| `MA1` | **PASS** | **FAIL** (`-0.12 -> +1.66`, `WFE=0`, `75%`) | **FAIL** (`0.112 / 0.001`, `1.000`, `n/a`) | **FAIL** (`74.0% / -8.0%`, IID `72.4%`) | **PASS** (`+4.84%` Ord, `4.2x`) | **FAIL** (`0.64, 0.526`, `[-0.06,+0.13]%`) | **PASS** (`4/5 +`; Bull `-7.4%`) | **FAIL** (`0.055`) | **PASS** | **PASS** |
| `S1` | **PASS** | **FAIL** (`+2.43 -> -0.69`, `WFE=-0.29`, `25%`) | **FAIL** (`0.135 / 0.001`, `1.000`, `n/a`) | **FAIL** (`72.5% / -22.2%`, IID `75.5%`) | **PASS** (`+18.86%` CG, `3.3x`) | **FAIL** (`0.81, 0.418`, `[-0.15,+0.36]%`) | **PASS** (`4/5 +`; HiVol `-46.2%`) | **FAIL** (`0.210`) | **PASS** | **PASS** |
| `B1` | **PASS** | **FAIL** (`-0.10 -> -0.39`, `WFE=0`, `25%`, `0%`) | **FAIL** (`0.008 / 0.000`, `1.000`, `0.998`) | **FAIL** (`20.4% / -52.1%`, IID `17.3%`) | **PASS** (`+0.13%` Ord, `8.6x`) | **FAIL** (`-0.75, 0.453`, `[-0.48,+0.25]%`) | **PASS** (`3/5 +`; Side `-0.6%, LoV -0.6%`) | **FAIL** (`0.165`) | **PASS** | **PASS** |
| `FX1` | **PASS** | **FAIL** (`-4.14 -> -0.64`, `WFE=0`, `25%`) | **FAIL** (`0.010 / 0.000`, `1.000`, `n/a`) | **FAIL** (`12.8% / -2.7%`, IID `13.0%`) | **FAIL** (`-1.04%` Ord, `0.53x`) | **FAIL** (`-1.14, 0.260`, `[-0.04,+0.01]%`) | **FAIL** (`1/5 +`; only HiVol `+1.9%`) | **FAIL** (`0.880`) | **PASS** | **PASS** |
| `C1` | **PASS** | **FAIL** (`-4.99 -> -0.79`, `WFE=0`, `25%`, `0%`) | **FAIL** (`0.018 / 0.001`, `1.000`, `n/a`) | **FAIL** (`5.2% / -12.7%`, IID `9.9%`) | **FAIL** (`-24.93%` Ord, `0.00x`) | **FAIL** (`-1.24, 0.219`, `[-0.17,+0.02]%`) | **FAIL** (`1/5 +`; only Bull `+10.5%`) | **FAIL** (`0.535`) | **PASS** | **PASS** |

---

## 4. Benchmark Comparison, Canadian Fee Drag & Empirical Sub-Audits

### 4.1 Passive Benchmarks (`experiment_results.json`)
| Benchmark | Span | Net CAGR | Non-Reg CG CAGR | Ann Vol | Sharpe | Sortino | Calmar | MaxDD | Interpretation vs. Active Trials |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| `SPY_BH` | `166m` | `+12.82%` | `+9.47%` | `14.28%` | `0.747` | `1.166` | `0.517` | `-24.80%` | Beats EVERY sleeve (`M1/E1/CM1/MA2/B1`) on CAGR & Sharpe |
| `60_40_SPY_AGG` | `166m` | `+7.31%` | `+5.38%` | `9.39%` | `0.538` | `0.800` | `0.348` | `-21.03%` | Matches `E1` CAGR (`+7.31%`) with *lower* Vol (`9.4%` vs `12.3%`) & MaxDD |
| `GLD_BH` | `166m` | `+5.85%` | `+4.25%` | `16.18%` | `0.279` | `0.438` | `0.157` | `-37.38%` | `CM1` beats `GLD_BH` (`+9.08%`, `-18.8%` DD vs `-37.4%`) via trend exit |
| `DBC_BH` | `166m` | `+1.39%` | `+1.04%` | `17.15%` | `0.022` | `0.031` | `0.022` | `-61.71%` | Broad commodity passive holding destroyed wealth post-2013 |
| `AGG_BH` | `166m` | `-1.02%` | `-1.14%` | `4.73%` | `-0.716` | `-0.861` | `-0.045` | `-22.79%` | `B1` (`+0.74%`) avoided bond losses but still trailed `2.5%` T-bills |
| `TLT_BH` | `166m` | `-2.80%` | `-3.27%` | `13.17%` | `-0.338` | `-0.457` | `-0.051` | `-54.51%` | Long duration suffered `-54.5%` rate-hike crash |
| `BTCUSDT_3mo_BH` | `84d` | `-70.73%` | `-70.73%` | `57.53%` | `-1.888` | `-2.516` | `-2.019` | `-35.03%` | `C1` cut crash vol (`11.8%` vs `57.5%`), yet lost `-6.39%` cum after fees |

### 4.2 Canadian Mutual Fund MER Erosion (`M1` Sensitivity)
- **Low-Cost Index Class (`0.15%/yr`):** CAGR `+7.49%` (`+5.57%` Taxable CG), Sharpe `0.450`.
- **Mid-Fee Class (`0.50%/yr`):** CAGR `+7.17%` (`+5.33%` Taxable CG), Sharpe `0.425`.
- **Typical Canadian Retail Active MER (`1.80%/yr`):** CAGR drops to **`+5.95%`** (`+4.42%` Taxable CG), Sharpe **`0.332`**—losing **`1.54%/yr`** compounded and underperforming a passive `60/40` ETF portfolio cleanly.

### 4.3 Live `/audit` Diagnostics & OKX Crypto Funding Audit
- **OKX 8-Hour Funding (`data/funding_rate_archive/`, `51` days / `154` prints each):** `XRPUSDT` `+0.363 bps/8h` (`3.97%` gross -> `2.54%` net after `20 bps` RT entry/exit), `BNBUSDT` `+0.353 bps` (`3.87%` -> `2.44%` net), `ETHUSDT` `+0.312 bps` (`3.42%` -> `1.99%` net), **`BTCUSDT` `+0.158 bps` (`1.72%` gross -> `+0.29%/yr` net)**, `SOLUSDT` `+0.093 bps` (`1.02%` gross -> **`-0.41%/yr` net**). Delta-neutral funding yields **underperform Canadian risk-free cash (`2.5%`)** over calm/bear windows once exchange fees apply.
- **Live `/audit` `CRYPTO` Cohort (`n=1,966`):** Gross expectancy `-0.3509%/trade`, Net after `20 bps` = **`-0.5509%/trade`**, `WR = 39.27%`, `PF = 0.716`.
- **Live `/audit` `FOREX` Cohort:** Raw `n=187` averaged **`-0.155%` gross** (polluted by `19` synthetic `EURUSDT` crypto trades and `10` zero-PnL zombies). Clean `n=158` averaged `+0.0412%` gross (`+4.12 bps`), turning **`-0.0388%` (`-3.88 bps`) net** at realistic `8 bps` spread+swap (`breakeven = 4.2 bps`, `0.53x` margin of safety). Note Canadian ITA s.146.2 prohibits leveraged spot/CFD FX inside TFSA accounts.

---

## 5. Actionable Verdict Summary (Shortlist vs. Immediate Retirement)
1. **Do NOT claim any live `/audit` strategy is "proven profitable" today (`0/9` pass).** Deploy capital in real money strictly via low-fee passive Canadian ETF/index core (`SPY` / `60-40` or asset-allocation ETFs like `VEQT/VGRO/VBAL` inside TFSA/RRSP) rather than active pick generators.
2. **Pre-Register for Shadow Forward Tracking Only (`PROOF_PROTOCOL.md`):** `E1` / `M1` (`7/10` gates; zero-commission/D-series/TFSA only; monthly cadence eliminates intraday fee bleed) plus diagnostic watchlists on `CM1` (`Shuffle p=0.0050`, requiring longer secular cycle OOS) and `MA1` (`Variant C`, `n=237`, needing `>=500` clean OOS trades).
3. **Hard-Kill / Quarantine Immediately:** `FX1` (`FOREX_HARD_DISABLE=1`), `C1` intraday/ML crypto emitters (`1,966` live picks losing `-0.55%/trade`), `S1` (`/audit` active `EQUITY` collapsing to `OOS Sharpe -0.694`), and `B1` short-window bond rotation.
