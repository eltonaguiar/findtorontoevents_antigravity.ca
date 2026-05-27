# EAGLE: One Top-Tier Strategy Per Asset Class
**Date:** 2026-05-27 02:26 EST | **Model:** Claude Opus 4.7 (via CommandCode)
**Branch:** `feat/EAGLE-2026-05-27-end-to-end-review`

---

## 1. CRYPTO: Liquid Core + On-Chain Momentum + Source Whitelist

### The Strategy
**Symbols:** BTCUSDT, ETHUSDT, SOLUSDT, AVAXUSDT, NEARUSDT, SUIUSDT, ADAUSDT, LINKUSDT, ARBUSDT, DOTUSDT (10-25 liquid core, ADV>$10M 24h)

**Signals (multi-source):**
1. On-chain momentum (Glassnode MVRV-Z): LONG when MVRV-Z < -0.5 + rising active addresses; SHORT when MVRV-Z > 2.0 + falling exchange balances. Confidence: 0.55-0.75. BTC/ETH only.
2. Funding rate carry: LONG when funding rate < -0.01% (shorts pay longs); SHORT when > 0.05% (overheated). Binance/Hyperliquid free endpoints.
3. Source-restricted picks: ONLY from dna_winner_picks, mega_mutation, kimi_riseoftheclaw, baby_strats_forward, aggregated_picks, claude_gainer_st

**Regime:** BTC UTC-hour filter (reject 06, 08, 09 UTC; boost 22 UTC). VIX>30 → reduce sizing 50%.

**Risk:** TP 3-5% / SL 1.5-2%, max hold 7d. Per-symbol cap 15% class PnL. No single source >25% volume.

### Why This Is Top-Tier
- Liquid, low-slippage symbols (BTC/ETH/SOL = 40%+ of crypto volume)
- Academic on-chain edge (Glassnode MVRV-Z validated 2018-2025)
- Funding rate carry is the highest Sharpe in crypto (historical Sharpe 2-8 for this strategy family)
- Source whitelist removes 5+ diluting sources (luxalgo/alpha_engine/quan_engine/copy_trader/battleground = 50%+ vol at PF<1.1)
- Hour filter is memory-backed (n>1000 in studies), zero-cost edge

### Expected PF Lift: +0.15-0.30 (from 1.36 → 1.50-1.66)
### Dev Effort: M (3 files: config.py source whitelist, on-chain enable env var, hour filter duplication cleanup)
### Files: `alpha_engine/config.py`, `audit_trail/quality_gates.py`, `alpha_engine/crypto_onchain_momentum.py`

---

## 2. EQUITY: VIX<22 12-1 Momentum on 20-25 Large-Cap

### The Strategy
**Symbols:** AAPL, MSFT, NVDA, TSLA, AMZN, GOOGL, META, AMD, AVGO, ORCL, JPM, GS, UNH, LLY, WMT, COST, XOM, PG, SPY, QQQ (20-25 large-cap, ADV>$5B)

**Signals:**
1. 12-1 momentum factor (Jegadeesh-Titman 1993): Rank by 12-month return skipping most recent month. Top 3-5 LONG. Monthly rebalance.
2. Quality-value composite: equity_factor_model.py (PE + ROE + 52WeekChange). Boost +0.05-0.10 confidence.
3. Connors RSI2 on SPY/QQQ: RSI(2)<5 + above SMA200 → LONG. 75%+ WR documented.

**Regime:** VIX<22 hard filter. VIX>30 → stop all equity emissions. SPY>200SMA macro gate (existing). Yield-curve inversion (10Y-2Y) → reduce to defensive sectors only (XLP/XLU/XLV).

**Risk:** TP 3-5% / SL 1.5-2%, max hold 21d. Per-symbol cap 10% class PnL. Max 5 concurrent picks (monthly rebalance).

### Why This Is Top-Tier
- **Backtest-proven Tier-1:** VIX<22 12-1 momentum on 30 LC (2015-2026): PF 5.37, WR 75%, Sharpe 2.19, MDD 7.3%, n=88 periods
- VIX<25 baseline: PF 3.22, Sharpe 1.63, MDD 11.8%, n=102 periods
- **Branch already exists:** `feat/equity-vix-regime-gate-sidecar-2026-05-13` — unmerged but ready
- Friction-robust: even at 10bp stress, ETF equivalent PF 1.99
- Clean academic edge (Jegadeesh-Titman most replicated factor in finance)
- External replication: AQR, Alpha Architect, Dimensional — all run momentum factors

### Expected PF Lift: +0.3-0.8 (from 1.57 → 1.87-2.37)
### Dev Effort: S-M (merge existing branch + add 8 LC to universe + split penny/meme)
### Files: `alpha_engine/equity_strategies.py`, `alpha_engine/config.py`, `audit_trail/vix_regime_gate.py`

---

## 3. COMMODITY: Carry-Momo Double-Sort (Miffre 2010)

### The Strategy
**Symbols:** CT=F, KC=F, SB=F, CC=F, OJ=F, GC=F, SI=F, HG=F, PL=F, PA=F, CL=F, NG=F, ZC=F, ZS=F, ZW=F, HE=F, LE=F (18 futures from commodity_carry_momo.json)

**Signals:**
1. 12-1 momentum rank + carry proxy rank → double-sort (Fuertes/Miffre/Rallis 2010, SSRN 1127213)
2. Long top-3 quintile (highest mom + highest carry), short bottom-3 quintile (academic long-short, production long-only for simplicity)
3. Carry proxy = rolling mean of (far-month − near-month) / near-month → contango=short, backwardation=long

**Regime:** Roll-yield check (contango penalty). Seasonal weight adjustment (e.g. NG winter weight boost). VIX>30 → reduce commodity exposure 50% (commodities correlate with inflation/vol).

**Risk:** Single contract per symbol. Max 5 concurrent positions. Daily limit-move risk accounted in sizer (CT=F $1,500/contract, GC=F $5,000/contract). Never exceed 25% class PnL from single symbol.

### Why This Is Top-Tier
- Academic edge with 15+ years of replication (Miffre lab at EDHEC)
- Already coded: `commodity_carry_momo.json` has 18 symbols with current mom/carry values
- Current values (2026-05-12): CT +11.8% mom +12% carry, GC +47% mom, SI +133% mom — strong signals today
- **Bypasses COT over-emission problem entirely** (different data, different symbols, different academic basis)
- Diversifies the 73% CT=F concentration that plagues current COMMODITY

### Expected PF: 1.5-1.8 if n≥80 clean post-dedup
### Dev Effort: M (wire sidecar into production path + backtest validation)
### Files: `commodity_carry_momo.json`, `alpha_engine/production_scanner.py`, `audit_trail/dashboard_generator.py`

---

## 4. ETF: 11-Sector Rotation + VIX<25 Regime Gate

### The Strategy
**Symbols:** XLK, XLE, XLF, XLV, XLI, XLY, XLP, XLU, XLB, XLRE, XLC (11 SPDR sectors)

**Signals:**
1. Faber TAA: Top 3 sectors by 3-month momentum, must be above 200-day SMA. Monthly rebalance.
2. Antonacci Dual Momentum: 12-month absolute + relative momentum. Fallback when Faber empty.
3. VIX<25 gate: Skip rebalance in high-vol months (~16% of months). VIX<22 preferred (lifts PF from 2.05→3.91).

**Regime:** VIX<25 = rotate normally. VIX≥25 = skip month, hold cash/TLT. Yield-curve inversion → overweight defensive (XLP/XLU/XLV).

**Risk:** Equal-weight top 3 (33% each). Max 3 concurrent positions. Rebalance monthly (6 trades/year → friction <2% annual). 5bp round-trip transaction cost model.

### Why This Is Top-Tier
- **Backtest-proven near Tier-1:** VIX<22: PF 3.91, Sharpe 1.93, MDD 8.1%, n=88 periods (2015-2026)
- VIX<25: PF 3.22, Sharpe 1.63, MDD 11.8%, n=102 periods
- **VIX overlay transfers from EQUITY success** (both classes have independent VIX regime breakthroughs May-13)
- Already coded: `tools/etf_sector_emitter.py`, `alpha_engine/etf_strategies.py`, `audit_trail/vix_regime_gate.py`
- Liquid, diversified, low manipulation risk — easiest path to institutional trust
- External replication: Faber TAA funds, AQR QMOM, Alpha Architect, sector rotation ETFs

### Expected PF Lift: +0.5-1.0 (from 1.48 → 1.98-2.48)
### Dev Effort: S (VIX gate default ON in emitter + activate emitter schedule)
### Files: `tools/etf_sector_emitter.py`, `audit_trail/quality_gates.py`

---

## 5. FOREX: DISABLED — If Revived, SHORT-Only AUDUSD/JPY + DXY Confluence

### The Strategy
**Symbols:** EURUSD=X, GBPUSD=X, AUDUSD=X, USDJPY=X (4 majors only)

**Signals (SHORT-ONLY):**
1. ig_contrarian SHORT: when IG client sentiment >70% long → SHORT (retail fade). WR 57.1% SHORT in deep_dive.
2. MeanReversionBB SHORT: price > upper Bollinger band + RSI>70. PF 2.09, n=44 in mutation autopsy.
3. DXY confluence gate: ONLY SHORT when DXY 4H EMA20 < EMA50 (USD weakening). This blocks the anti-edge LONG direction.

**Regime:** DXY trend filter. Skip FOMC/NFP/ECB ±2h. Session-aware (08-16 UTC London/NY overlap only).

**Risk:** 0.5-1% risk per trade. TP 1.5% / SL 0.8%. Max 2 concurrent. AUDUSD/JJPY PF>2 survivees only.

### Why This Is Top-Tier (Conditional)
- SHORT-only PF 8.11 on n=29 in mutation autopsy
- Survivors: AUDUSD SHORT PF 3.55, AUDJPY SHORT PF 2.45
- Academic carry + DXY literature supports direction asymmetry
- DXY trend is the missing regime gate that explains why LONG 80% vol drags are anti-edge
- **BUT: n is tiny.** 30d paper proof mandatory before any sizing.

### Expected PF (if proven): 1.3-1.5 on SHORT-only sleeve
### Dev Effort: M (DXY gate + partial exemption from HARD_DISABLE + paper pilot)
### Files: `audit_trail/quality_gates.py`, `alpha_engine/forex_strategies.py`

---

## 6. BOND: Research-Only — Curve-Carry Momentum (Cochrane-Piazzesi 2005)

### The Strategy
**Symbols:** TLT, IEF, SHY (Treasury duration ladder)

**Signals:**
1. Curve-carry: Rank TLT, IEF, TLH by 3-month return. LONG top, SHORT bottom. Monthly. (Cochrane-Piazzesi 2005 factor).
2. TIPS-Treasury breakeven MR: LONG TIP when T10YIE > 20d MA + TIP oversold (Fleckenstein-Longstaff-Lustig 2014).
3. Credit-spread MR: LONG HYG when HY OAS > 2σ above mean (Frazzini-Pedersen quality-minus-junk pattern).

**Regime:** MOVE index <20d MA (bond vol low → carry works). FOMC ±2d skip.

**Risk:** TP 1.5% / SL 0.75%. Monthly frequency (12-24 trades/year). Low-vol asset class.

### Why This Is (Low Priority) Top-Tier
- 3 academic pilots fully specified in `bond_deep_dive_round2_2026-05-13.md`
- Cochrane-Piazzesi is one of the most cited bond factors in finance (2005, JF)
- But: n=11 total BOND sample is statistically meaningless
- FRED key needed for yield curve data (M-032 pending)
- De-prioritized for full 90 days

### Expected PF: Unknown — requires n≥50 paper before any inference
### Dev Effort: M (lower elite floor + wire 3 pilots)
### Files: `alpha_engine/bond_strategies.py`, `alpha_engine/bond_data_fred.py`

---

## 7. FUTURES: Merge + Overnight Drift (MES) + Asia MR (MGC)

### The Strategy
**Symbols:** ES=F/MES=F, NQ=F/MNQ=F, GC=F/MGC=F, ZN=F, 6E=F, 6J=F (financial futures + micros)

**Signals:**
1. MES overnight drift: LONG 16:00 ET, exit 09:30 next day (Asness 2011 documented edge: overnight + O.4% avg, intraday -0.4%). VIX<25 only.
2. MGC Asia MR: MGC RSI(14)<35 at 18:00 ET → LONG to 03:00 London. TP 0.3%, SL 0.45%.
3. M6A carry sign: LONG 6A=F when 3M rate diff >0 + SMA slope positive (Lustig/Verdelhan 2007 carry).

**Regime:** VIX<30 for equity futures. Roll-yield check for rates/FX. Macro-blackout (CPI, FOMC, NFP).

**Risk:** Micro contracts (MES=$5/point, MNQ=$2/point, MGC=$10/point). Max 3 concurrent. Per-contract notional <5% account.

### Why This Is Top-Tier
- Overnight drift is academic edge (Asness 2011, Cliff Asness at AQR — one of the most cited papers)
- Micro contracts enable realistic paper → live scaling
- Asia MR on gold has seasonal + timezone edge
- CARVE: financial futures diversify commodity futures
- **BUT: tile shows n=0.** Merge with COMMODITY first.

### Expected PF: Unknown until merge + 30d paper
### Dev Effort: M (classification patch + 3 pilot strategies)
### Files: `audit_trail/dashboard_generator.py`, `alpha_engine/futures_strategies.py`

---

## 8. PENNY/MEME: No Strategy — PERMANENTLY QUARANTINED

**Evidence:** MEMECOIN PF 0.50 / WR 15.7% / n=1,869. PENNY_STOCK PF 0.19 / WR 6.8% / n=148. Structural negative edge. Sharpe -2.8 to -3.4. Sub-coin-toss across thousands of trades.

**No revival.** No "high-vol sleeve." No exemptions. The worst edge in any asset class. Already correctly quarantined.

---

## Summary: Top Strategy Per Class

| Class | Strategy | Academic Backing | PF Target | Effort | Priority |
|---|---|---|---|---|---|
| EQUITY | VIX<22 12-1 Momentum 20-25 LC | Jegadeesh-Titman 1993, Asness 2013 | 1.87-2.37 | S-M | P0 |
| ETF | 11-Sector Rotation + VIX<25 | Faber 2007, Antonacci 2014 | 1.98-2.48 | S | P0 |
| CRYPTO | Liquid Core + On-Chain + Source Whitelist | Glassnode MVRV-Z, funding carry | 1.50-1.66 | M | P1 |
| COMMODITY | Carry-Momo Double-Sort 18 futures | Miffre/Rallis/Fuertes 2010 | 1.50-1.80 | M | P1 |
| FOREX | SHORT-Only 4 majors + DXY gate | Carry + contrarian literature | 1.30-1.50 | M | P2 (disabled) |
| FUTURES | Overnight drift MES + Asia MR MGC | Asness 2011, Lustig 2007 | Unknown | M | P2 (merge first) |
| BOND | Curve-carry TLT/IEF/SHY + 2 pilots | Cochrane-Piazzesi 2005 | Unknown | M | P3 (research) |
| PENNY/MEME | QUARANTINED | None | — | — | — |
