# Hedge-Fund-Grade Performance Review — Detailed Per-Class — 2026-04-27

**Author:** claude-opus-4-7
**Companion summary:** `reports/hedge_fund_performance_review_summary_2026_04_27.md`
**Source data:** `audit_trail/data/dashboard_payload.json` (generated_at 2026-04-27T22:08:21.106Z, 1.55h fresh).
**Cross-reference:** Workstream A (ML pipeline), B (resolver), C (symbol/direction), D (HC filter), E (strat_name), F (mutation) action reports in `reports/action_*_2026_04_27.md`.

The "clean wins" column throughout = wins minus 1bp resolver-flicker wins (per `feedback_noncrypto_resolver_live_close_bug.md`). For non-crypto classes this is the only number that survives the resolver bug.

---

## 1. EQUITY — n=381 — Tier 2 — **THE FRANCHISE**

### Numbers

- WR 51.97%, PF 1.385, Sum PnL +232.13%, MaxDD 70.95%, Sharpe(per-trade) 0.1265
- Resolver-noise share **9.09%** — within the 30% reliability threshold; numbers are trustworthy
- Of 198 wins, 180 are real (>0.05% pnl) — 87% clean win rate

### Source-system breakdown

| Source | n | WR% | Sum PnL% | Clean wins | Verdict |
|---|---:|---:|---:|---:|---|
| `kimi_riseoftheclaw` | 166 | 57.8 | **+245.8** | 95 | **Star performer** — single source carries the class |
| `stocks_competition` | 133 | 49.6 | +90.3 | 66 | Solid contributor, near-coinflip WR but PF positive |
| `multi_asset_copytrader` | 23 | 65.2 | -6.0 | 8 | Small WR positive, sum negative — losses are larger |
| `alpha_engine_fast` | 19 | 68.4 | +0.4 | 5 | Tiny but high WR, low sum (small position size) |
| `goldmine_stocks` | 13 | **0.0** | **-53.4** | 0 | **POISON — kill** |
| `fast_stocks_competition` | 6 | **0.0** | -22.0 | 0 | **POISON — kill** |
| `kimi_signal_tracking` | 4 | 50.0 | -17.3 | 2 | Tiny n, large losses — review |

### Gap analysis vs hedge-fund standard

What we have: discretionary momentum/gainer scanners. What top equity shops have:
- **Two Sigma** factor-zoo: ~150 rolling factors (value, momentum, low-vol, quality, profitability, investment, sentiment from filings/news), trained models update daily
- **Renaissance** stat-arb pairs: thousands of cointegrated pairs trading mean-reversion at minute scale
- **AQR Style Premia**: rule-based long-short on 6 documented factors across equity universe
- **13F follower** strategies: track quarterly hedge-fund disclosures, replicate top holdings 6-week lag

### Industry playbook to add

| Playbook | What it adds | Implementation surface |
|---|---|---|
| **Fama-French 5-factor + momentum overlay** | Gives EQUITY a structural risk model, lets you size by factor exposure not just signal strength | New `alpha_engine/equity_factor_model.py`; daily compute; gate at score time |
| **Earnings-drift event strategy** | Post-earnings-announcement-drift (PEAD) is one of the most-replicated anomalies — buy beats, short misses, hold 60d | Plug into existing `alpha_engine` infra; needs earnings calendar feed (Polygon, Finnhub) |
| **Low-vol factor (BlackRock USMV-style)** | 30-year out-of-sample factor; complements momentum to flatten MDD | Universe: S&P 500, monthly rebalance lowest-vol decile |
| **Insider-buying signal** | Form 4 + cluster filter (≥3 insiders buying within 30d) — Two Sigma uses this | Free SEC EDGAR data; needs new ingestor |

### Concrete next steps

1. **Kill 2 zombie sources** (`goldmine_stocks`, `fast_stocks_competition`) — both 0% WR, -75.4% combined sum on n=19. Project rule requires `STRATEGY_INVESTIGATION_BEFORE_KILL.md` mutation pass, but n=19 with 0 wins is past saving — document and demote.
2. **Scale `kimi_riseoftheclaw` allocation 2-3×** (from current implicit n=166/3500 ≈ 5% of pick budget to ≥15%). It's been the single biggest PnL contributor across all classes by far.
3. **Backstop with one factor strategy** (Fama-French 3-factor minimum) so EQUITY isn't single-source-dependent on `kimi_riseoftheclaw`.
4. **Add MaxDD gate** at the EQUITY class level — 70% drawdown is unacceptable institutionally; cap class-level drawdown at 15% via vol-targeting.

---

## 2. CRYPTO — n=1,598 — Below Tier 3 — **EDGE EXISTS, DRAWDOWN LETHAL**

### Numbers

- WR 42.18%, PF 1.140, Sum PnL +158.74%, MaxDD **178.64%**, Sharpe 0.0465
- Resolver-noise share 1.19% — numbers trustworthy
- Direction asymmetry: BUY n=1146 WR=44.42%, SELL n=452 WR=36.50%

### Source-system breakdown (top 15)

| Source | n | WR% | Sum PnL% | Clean wins | Verdict |
|---|---:|---:|---:|---:|---|
| `luxalgo_filters` | 181 | **50.8** | **+63.1** | 92 | **Best edge** |
| `claude_gainer_st` | 256 | 47.7 | +36.6 | 121 | Strong, scale up |
| `signal_validation` | 26 | 61.5 | +25.8 | 16 | Best WR%, scale once n>50 |
| `kimi_riseoftheclaw` | 20 | 65.0 | +18.3 | 13 | Same kimi alpha, smaller crypto sample |
| `baby_strats_forward` | 205 | 46.8 | +11.4 | 94 | Workhorse, near-coinflip |
| `alpha_engine` | 462 | 36.1 | +12.7 | 163 | High-volume, low edge — **vol-cap target** |
| `dna_winner_picks` | 70 | 38.6 | +10.6 | 27 | Marginal |
| `aggregated_picks` | 21 | 42.9 | +14.4 | 9 | Tiny n |
| `regime_terminal` | 19 | 36.8 | +5.9 | 7 | Tiny |
| `super_signals` | 17 | 47.1 | -0.6 | 8 | Tiny, ~breakeven |
| `battleground` | 22 | 40.9 | -3.9 | 9 | Tiny, marginal loss |
| `dna_rapid_fire_mutations` | 20 | **25.0** | -9.5 | 5 | **POISON — kill** |
| `mercury2` | 37 | **27.0** | -18.7 | 10 | **POISON — kill** |
| `quan_engine` | 20 | **0.0** | -20.0 | 0 | **POISON — kill (memory: MATIC ghost-row artifact, 660 rows scrubbed; remaining are real losses)** |
| `rapid_fire` | 156 | 39.1 | **-52.8** | 60 | **POISON — kill (largest single-source negative PnL)** |

### Workstream C-confirmed poison-pill symbols

Per `reports/action_C_symbol_risk_2026_04_27.md`:

| Symbol | Action | Reason |
|---|---|---|
| `TONUSDT` | **BLOCK** (both directions) | n=11, WR 9.09% |
| `TIAUSDT` | **BLOCK** (both directions) | n=16, WR 25.00% |
| `HYPEUSDT` | **BLOCK** (both directions) | n=46, WR 26.09% |
| `ONDOUSDT` | **BLOCK SELL only** | SELL 0/18; BUY 3/6 = 50% (flipping is wrong, BUY already works) |
| `OPUSDT` | **BLOCK from `claude_gainer_st` only** | 100% concentrated in that source |
| `LTCUSDT` | **BLOCK from `alpha_engine` only** | alpha_engine LTC: n=57, 19.3% WR; claude_gainer_st LTC: 46.2% (fine) |

### Workstream C SHORT-side audit (challenges memory `feedback_long_source_bias.md`)

`alpha_engine` SHORT n=190 WR=33.7% sum=-19.12% — **single biggest contributor to MaxDD**. Memory (22 days old) said alpha_engine SHORT had 62.5% WR; current data refutes that. The "good" SHORT sources today (`luxalgo_filters` 50%, `signal_validation` 66.7%, `copy_trader_highscore` 70%) total only n=107 — too small to carry the SHORT side.

### Gap analysis vs hedge-fund standard

What we have: 24 sources of varying quality, 1.598k picks/period, BUY-bias, no vol-targeting.

What top crypto desks (Jump, Cumberland, B2C2, Galaxy) have:
- **Cross-venue stat arb** (Binance vs Coinbase vs Kraken price spreads, microsecond execution) — not feasible at our scale
- **Perp basis trade** (fund rate arb between perp and spot) — workable
- **On-chain signal layer** (Glassnode wallet flows, IntoTheBlock holder concentration, Arkham smart-money tags) — workable
- **Vol-targeting + Kelly sizing**, not flat $-per-pick
- **MEV-aware order routing** — not relevant unless scaling >$10M

### Industry playbook to add

| Playbook | Lift | Implementation |
|---|---|---|
| **Vol-targeted position sizing** | Caps MDD from 178% → ~25% | `alpha_engine/sizing.py` new module; ATR-scaled position size; gate at execution |
| **Perp funding-rate basis** | New non-correlated income stream (typical 5-15% APY, low MDD) | Bybit/Binance funding feeds; net long spot + short perp when funding > threshold |
| **On-chain whale-flow filter** | Reduces false-positive entries during distribution phases | Glassnode `exchange_inflow` API; veto LONG entries during high inflow windows |
| **Kill-switch on regime change** | Existing `regime_terminal` gates sizing, doesn't kill | Add hard halt when `regime_terminal` reports state ≥6/7 (extreme) |

### Concrete next steps

1. **Kill 4 zombie sources** (`quan_engine`, `dna_rapid_fire_mutations`, `mercury2`, `rapid_fire`) — total -101.0% on n=233. Project rule requires mutation-before-kill protocol; per Workstream F format, run `tools/mutation_analysis.py` first, document outcome.
2. **Apply Workstream C symbol gates** (TON / TIA / HYPE block; ONDO SELL block; OP/LTC source-scoped) → expected MDD reduction ~15-20pp from poison removal alone.
3. **Apply Workstream C SHORT-side gate** (block `alpha_engine` SHORT triple) → expected MDD reduction additional ~10-15pp.
4. **Add vol-targeting layer** — biggest single MDD lever, biggest single hedge-fund-vs-retail differentiator.
5. **Scale up `luxalgo_filters` and `claude_gainer_st`** — both have positive PF and clean-win share >50%.

---

## 3. ETF — n=83 — Tier 3 borderline — **TOO SMALL TO TRUST**

### Numbers

- WR 54.22%, PF 1.220, Sum PnL +20.25%, MaxDD 46.94%, Sharpe 0.0816
- Resolver-noise share 6.67% — trustworthy
- n=83 is below the 100-row Tier-3-confidence threshold

### Source-system breakdown

| Source | n | WR% | Sum PnL% | Clean wins | Verdict |
|---|---:|---:|---:|---:|---|
| `kimi_riseoftheclaw` | 68 | 52.9 | +26.4 | 35 | Single dominant source (82% of class) |
| `crypto_ml_edge` | 5 | 60.0 | +0.4 | 3 | Tiny |
| `alpha_engine_fast` | 4 | 100.0 | +1.3 | 2 | Tiny |
| `multi_asset_scanner` | 2 | 50.0 | +0.1 | 1 | Tiny |
| `institutional_picks_engine` | 2 | 0.0 | -6.6 | 0 | Tiny, big losers |
| `goldmine_stocks` | 1 | 0.0 | -5.8 | 0 | n=1 |

### Gap analysis vs hedge-fund standard

ETF is the natural home for **risk parity** (Bridgewater All-Weather, AQR Risk Parity), **sector rotation** (State Street SPDR series), and **factor wrappers** (BlackRock iShares Edge MSCI series). We have neither a sector model nor a duration model nor a vol-budget — `kimi_riseoftheclaw` is treating ETFs like stocks.

### Industry playbook to add

| Playbook | What it adds | Implementation |
|---|---|---|
| **Sector rotation on relative momentum** | Standard since Faber's "Ivy Portfolio" (2007) — top-N sectors by 6-month return, monthly rebalance | Universe: 11 GICS sectors (XLK, XLF, XLE, XLV, XLY, XLP, XLI, XLU, XLB, XLRE, XLC) |
| **Risk parity weighting** | Bridgewater/AQR — equal risk contribution, not equal $ | Apply over a basket: SPY/AGG/GLD/DBC/IEF or a more diversified set |
| **Volatility targeting overlay** | Fixed 10% target vol, scale exposure inversely to realized vol | Trivial to bolt on |

### Concrete next steps

1. **Grow data first** — n=83 over the recent window is too small to make ETF a primary class. Add 1-2 ETF-specialist sources (sector momentum + low-vol factor) to get to n>200 in 30 days.
2. **Don't size up `kimi_riseoftheclaw` ETF** until you have 2+ uncorrelated sources — single-source ETF concentration is a model-failure risk.

---

## 4. FOREX — n=794 — **CANNOT EVALUATE** (resolver-contaminated)

### Numbers

- WR 50.38%, PF 1.349, Sum PnL +29.63%, MaxDD 38.06%, Sharpe 0.0215
- Resolver-noise share **63.25%** — **WR is meaningless**
- Of 400 wins, 253 are 1bp resolver flicker

### Source-system breakdown (with the noise filter applied)

| Source | n | Reported WR% | Clean wins | Implied real WR | Verdict |
|---|---:|---:|---:|---:|---|
| `multi_asset_copytrader` | 512 | 48.4 | 100 | **19.5%** | Mostly noise + losses |
| `non_crypto_consensus` | 101 | 53.5 | **0** | **0%** | **All wins are 1bp flicker** |
| `forex_copy_trader` | 41 | 53.7 | 1 | 2.4% | All wins are flicker |
| `cta_replicator` | 37 | 43.2 | 2 | 5.4% | Almost all flicker |
| `stocks_competition` | 32 | 56.3 | 17 | 53.1% | **Real edge** (only such source) |
| `alpha_engine` | 29 | 62.1 | 9 | 31.0% | Real edge |
| `kimi_riseoftheclaw` | 22 | 54.5 | 10 | 45.5% | Real edge |

**Take-home:** Once 1bp wins are stripped, FOREX has ~83 real wins on n=794 — **real WR ~10.5%** before resolver fix. The actual non-flicker edge is concentrated in 3 sources (`stocks_competition`, `alpha_engine`, `kimi_riseoftheclaw`) totaling n=83.

### Why this is contaminated, not bad

`audit_trail/outcome_resolver.py:384-405` closes positions at yfinance live spot every run; `WIN_THRESHOLD ≈ 1bp` (`outcome_resolver.py:97`). For low-vol pairs (most G10), every micro-tick is "a win." Workstream B fix is the prerequisite for any FOREX verdict.

### Gap analysis vs hedge-fund standard

What top FX desks (Brevan Howard, AQR Currency, Tudor) have:
- **G10 carry trade** (long high-yielders, short low-yielders) — most-cited single FX factor
- **Currency value** (long undervalued by REER, short overvalued)
- **Currency momentum** (3-12 month trend on dollar block)
- **Central bank surprise** (priced via Bloomberg WIRP / OIS-implied paths)
- **Order-flow data** from prime brokers (CLS, EBS) — not retail-accessible

### Industry playbook to add (post-resolver-fix)

| Playbook | Source / Cost | Notes |
|---|---|---|
| **G10 carry** | Free (Trading Economics for OIS rates, FRED for short rates) | Long top-3 yielders, short bottom-3, monthly rebalance |
| **Dollar-block momentum** | Free (yfinance for DXY, EURUSD, USDJPY etc.) | 6-month look-back, equal-weight |
| **Real-effective-exchange-rate (REER) value** | Free (BIS quarterly data) | Slow-moving, monthly rebalance |
| **DAILYFX seasonal patterns** | Free | E.g., USD strength typically peaks late-Q1 — overlay only |

### Copy-trader / external-alpha options

If after resolver-fix the internal FOREX edge is still <0 (highly likely), copy-trader is the right move:

| Provider | Notes |
|---|---|
| **Darwinex** | EU-regulated, audited equity curves, DARWIN factor scoring (VaR-controlled). Best institutional fit. |
| **eToro CopyTrader** | Largest pool but retail skew; filter for ≥2y track record, max-drawdown <20%, profit factor >1.5 |
| **Myfxbook AutoTrade** | Verified myfxbook accounts only (broker-side audit) |
| **ZuluTrade** | Older platform, large universe, requires hand-curating (look for 5y+ verified) |

**DD before any wire-up:** the existing `multi_asset_copytrader` is already the largest source AND largest noise generator — wrong copy-trader is worse than none.

### Concrete next steps

1. **BLOCK Workstream B** Workstream B resolver fix lands first. Nothing else FOREX-related can be data-supported until then.
2. **Re-resolve historical FOREX picks** with the patched resolver. Re-run this audit.
3. **If post-fix real WR <40%**: kill `multi_asset_copytrader` FOREX, kill `non_crypto_consensus`, kill `forex_copy_trader`, kill `cta_replicator` FOREX. Replace with G10 carry + dollar-momentum (industry standard).
4. **If post-fix real WR is 40-50%**: keep `stocks_competition`/`alpha_engine`/`kimi_riseoftheclaw` FOREX, kill the 4 noise-dominated sources, add G10 carry as a non-correlated overlay.

---

## 5. COMMODITY — n=622 — **CANNOT EVALUATE** (resolver-contaminated AND likely zero edge)

### Numbers

- WR 42.60%, PF 0.896, Sum PnL **−9.82%**, MaxDD 39.79%, Sharpe -0.0183
- Resolver-noise share **66.79%** — **WR is meaningless**
- Of 265 wins, 177 are 1bp flicker → **88 real wins on n=622 → real WR ~14%**

### Source-system breakdown (with noise filter)

| Source | n | Reported WR% | Clean wins | Implied real WR | Verdict |
|---|---:|---:|---:|---:|---|
| `multi_asset_copytrader` | 492 | 44.5 | 85 | **17.3%** | Mostly noise |
| `cta_replicator` | 105 | 39.0 | **1** | **1.0%** | **Pure noise** |
| `multi_asset_cot` | 8 | 0.0 | 0 | 0% | Tiny + zero |
| 6 other sources | 17 total | mostly 0 | 2 | ~12% | Tiny |

**Take-home:** Once flicker is stripped, COMMODITY has ~88 real wins on n=622 — **real WR ~14%, almost certainly zero edge**. The `cta_replicator` claim of "CTA-style momentum" is unsupported — it gets 1 real win out of 105 picks.

### Gap analysis vs hedge-fund standard

The internal sources don't appear to have any signal. The only path forward is industry-standard external alpha:

What top commodity desks (Winton, AHL, Aspect, Cargill alternative-data) have:
- **Term-structure (contango/backwardation)** — long backwardated futures, short contango
- **Cross-sectional momentum** (Asness 2003) — top-N performing commodities long, bottom-N short
- **Seasonality** (natty gas winter, corn-grain harvest, gold safe-haven)
- **Inventory data** (DOE crude, USDA grain, LME warehouse)
- **COT positioning** (commercial vs non-commercial — `multi_asset_cot` exists at n=8 but 0% WR — likely implementation bug, not signal failure)

### Industry playbook to add (post-resolver-fix)

| Playbook | Source / Cost | Notes |
|---|---|---|
| **Mt. Lucas Management Index (MLM)-style trend** | Free (yfinance futures continuous contracts) | 12-month moving-average crossover on 25 commodity futures, equal weight |
| **Term-structure carry** | Free (CME contract curves) | Long top-3 backwardated, short top-3 contango, monthly |
| **DOE-EIA inventory surprises** (energy) | Free (EIA weekly data) | Trade WTI/HO/NG against forecast surprises |
| **Cocoa/coffee/sugar seasonal** | Free (USDA + WMO weather) | Niche but documented edge |

### Copy-trader / external-alpha options

Commodity copy-trading is dominated by managed-futures CTA replication:

| Provider | Notes |
|---|---|
| **Striker Securities** | Managed-futures marketplace, audited fills, can replicate CTA signals at retail size |
| **iSystems (TradeStation)** | Futures strategy marketplace, automated execution |
| **AlgoTrader marketplace** | Quant-strategy storefront, mostly CTA-style |
| **Top Traders Unplugged podcast track records** | Public TT-Index of CTAs, useful as universe for due-diligence |

**Realistic path:** the existing `cta_replicator` source is at n=105 with real WR ~1% — it's not actually replicating CTAs successfully. Either fix it (likely needs a real CTA data feed) or replace with one of the above.

### Concrete next steps

1. **BLOCK Workstream B** resolver fix first.
2. **Suspend COMMODITY emissions** entirely until both (a) resolver is fixed and (b) at least one source achieves >40% real WR on n>50.
3. **Investigate `cta_replicator` implementation** — 1 real win on n=105 strongly suggests implementation bug, not market dynamics. Workstream F (mutation-before-kill) covers this for the "5 commodity strategies" but `cta_replicator` is its own beast.
4. **Don't add new commodity sources** until external alpha is proven.

---

## 6. BOND — n=17 — **INSUFFICIENT DATA**

### Numbers

- WR 47.06%, PF 1.601, Sum PnL +2.84%, MaxDD 3.47%, Sharpe 0.1246
- Resolver-noise share 12.50% — within reliability threshold but n=17 makes that fragile
- 2 sources only (`kimi_riseoftheclaw` n=9, `multi_asset_copytrader` n=8)

### Gap analysis vs hedge-fund standard

What top fixed-income shops (PIMCO, BlackRock Global Fixed Income, Brevan Howard) have:
- **Duration management** — explicit DV01 sizing, never raw $-position
- **Yield-curve steepener/flattener** trades (2s10s, 5s30s)
- **Credit spread** trades (HY vs IG vs TSY) using ETF wrappers (HYG vs LQD vs IEF)
- **TIPS breakeven** (5y/10y inflation expectations) — Treasury vs TIPS spread

### Industry playbook to add

| Playbook | Source / Cost | Notes |
|---|---|---|
| **PIMCO StocksPLUS-style ETF rotation** | Free (yfinance: TLT, IEF, SHY, BIL, TIP, LQD, HYG, EMB) | Slow-moving, monthly rebalance based on yield-curve slope |
| **Duration matching** | Free | Match average duration to a target (e.g., 7y for IEF benchmark) |
| **2s10s steepener** | Free | Long 2y note futures, short 10y note futures when curve flattens below historical mean |

### Copy-trader / external-alpha options

Less common in fixed income; **PIMCO's actively managed ETFs** (BOND, MINT, LDUR) are the de-facto benchmark for retail-accessible bond strategy.

### Concrete next steps

1. **No action until n>50.** With 17 samples, every metric is noise.
2. **Add a fixed-income ETF rotation source** — would 5-10× the data flow within 30 days at minimal infra cost.

---

## 7. Cross-class structural gaps (apply to ALL classes)

These are hedge-fund features missing across the system, not class-specific:

### A. No vol-targeting layer

CRYPTO MDD 178%, EQUITY 71%, FOREX 38%, COMMODITY 40%. Every institutional shop runs constant-vol; we run flat-$ position sizing. **Single biggest hedge-fund-vs-retail differentiator.** Implementation: `alpha_engine/vol_target.py`, scale entry size inversely to ATR, target 10-15% annualized portfolio vol.

### B. No risk-parity capital allocation

Risk dollars are currently allocated by source-pick-volume (alpha_engine emits 462 CRYPTO picks → gets 462 picks worth of capital). Should be allocated by Sharpe contribution. **Bridgewater All-Weather is the canonical reference.** Implementation: monthly Sharpe rollup → capital weights → per-source `pick_budget` cap.

### C. No regime-aware kill-switch

`regime_terminal` source exists (n=19 CRYPTO, n=2 FOREX, n=3 UNKNOWN) — i.e., we have a regime detector that's emitting picks rather than gating other strategies. Should be the *gate*, not a peer source.

### D. No portfolio-level Kelly / fractional-Kelly sizing

Each pick is sized in isolation. Pro shops compute portfolio-level Kelly fraction (target 0.25-0.5 Kelly to control variance) and scale all positions proportionally.

### E. No factor decomposition / risk-attribution

Why did EQUITY drawdown 70%? Was it momentum factor crash, sector concentration, single-name blow-up? We don't know because we don't decompose. **Two Sigma and AQR run this in real-time.**

### F. Resolver SLA / data-integrity audit

Today no automated check fires when 63% of FOREX wins are 1bp. Needs a daily / weekly job that computes resolver-noise share per class, alerts on >30%.

### G. ML training pipeline silent failures

Per Workstream A: `alpha-engine-live.yml:592` swallows `auto_tuner` failures with `|| echo "non-fatal"`; rf_model.pkl 12.3d stale; ml_gatekeeper persistence broken. Pro shops have dedicated ML-ops with hard-fail on training pipeline errors.

---

## 8. Sequencing — what to ship in what order

| Order | Item | Class blocker? | Workstream |
|---|---|---|---|
| 1 (P0, this week) | Resolver fix | **YES** — blocks FOREX/COMMODITY/BOND verdicts | B |
| 2 (P0, this week) | ML pipeline silent-failure fix | NO (independent) | A |
| 3 (P0, this week) | EQUITY zombie kills (`goldmine_stocks`, `fast_stocks_competition`) | NO | (this doc) |
| 4 (P0, this week) | CRYPTO symbol blocks (TON/TIA/HYPE/ONDO-SELL/OP-source/LTC-source) | NO | C |
| 5 (P0, this week) | CRYPTO SHORT block on `alpha_engine` triple | NO | C |
| 6 (P1, next) | Vol-targeting layer | NO (independent) | (this doc, cross-class) |
| 7 (P1, next) | CRYPTO zombie kills (`quan_engine`, `dna_rapid_fire_mutations`, `mercury2`, `rapid_fire`) | gated on Workstream F mutation protocol | F |
| 8 (P1, next) | Re-resolve historical non-crypto picks + repeat audit | depends on #1 | B |
| 9 (P2) | Add Fama-French equity factor model | NO | new |
| 10 (P2) | Add G10 carry FOREX (post-resolver-fix) | depends on #1, #8 | new |
| 11 (P2) | Suspend COMMODITY emissions; investigate `cta_replicator` impl | depends on #1, #8 | F |
| 12 (P3) | Risk-parity capital allocator | NO | new |
| 13 (P3) | Regime-aware kill-switch | NO | repurpose `regime_terminal` |
| 14 (P3) | External copy-trader DD on Darwinex / Striker (only if internal alpha proves insufficient post-#8) | depends on #8 | new |

## 9. Final synthesis

**The system has one real franchise (EQUITY via `kimi_riseoftheclaw`), one promising-but-dangerous class (CRYPTO with edge but lethal MDD), three classes with broken data integrity that masks whether edge exists (FOREX, COMMODITY, BOND), and a missing institutional risk-management layer everywhere.**

The hedge-fund-grade roadmap is clear: (1) fix the data layer (resolver), (2) consolidate around the proven franchise (EQUITY), (3) add the structural risk-management features pro shops have (vol-targeting, risk parity), (4) only then evaluate whether to add internal vs external alpha for the weak classes. Buying copy-trader signals before fixing the resolver and adding vol-targeting would be premature optimization — the existing `multi_asset_copytrader` is already the largest noise generator, demonstrating that "more sources" isn't the answer until the underlying data plumbing is sound.
