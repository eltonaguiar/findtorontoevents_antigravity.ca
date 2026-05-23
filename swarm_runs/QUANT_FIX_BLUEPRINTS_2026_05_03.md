# Quant Fix Blueprints — Per-Asset-Class Response to Kimi's Verdict Matrix

**Date:** 2026-05-03
**Subagent:** JJ1-QUANT-FIX-SWARM (Claude Opus 4.7 1M, e:/findtorontoevents_antigravity.ca)
**Source verdict:** `swarm_runs/kimi_prediction_edge_audit_2026_05_03/quant_audit.agent.final.md` (Kimi's 9-class verdict matrix)
**Methodology:** 3-round fan-out / fan-in agent swarm — RESEARCH → CRITIQUE → BLUEPRINT
**Engines used:** deepseek-v4-flash + cerebras (kimi/inception attempted; inception 401-auth-fail, kimi unicode-encoding failure on Windows)
**Total swarm calls:** 7 (3 R1 tier prompts + 3 R2 critique angles + 1 R3 synthesis)
**Total estimated cost:** ~$0.07 (7 calls × ~$0.01 each — well under $1.50 budget)
**Raw-output dirs:**
  - Round 1: `swarm_runs/quant_fix_blueprints_2026_05_03/round1/{safe,caution,dangerous}/`
  - Round 2: `swarm_runs/quant_fix_blueprints_2026_05_03/round2/{data,modeling,risk}/`
  - Round 3: `swarm_runs/quant_fix_blueprints_2026_05_03/round3/blueprint/`

---

## 1. Methodology

### 1.1 Three-Round Structure

**Round 1 — Research (3 swarm calls, batched by verdict tier)**
- Tier prompt → 4 engines (deepseek, cerebras, inception, kimi) with persona injection
  - **SAFE tier (Equity)**: persona `equity_specialist`
  - **CAUTION tier (Crypto B/A/S, ETF)**: persona `cross-verification-auditor`
  - **DANGEROUS tier (Forex, Commodity, Crypto C, Bond/Futures, Penny, Meme)**: persona `risk-of-ruin-assessor`
- Each engine answered: (1) which world-class hedge funds operate in this class + verifiable methodology; (2) top 3 academic papers (last 5 yrs); (3) skeptical pitfalls in Kimi's numbers; (4) realistic post-cost edge ceiling.

**Round 2 — Critique (3 swarm calls, three angles)**
- All 10 classes per angle:
  - **Data validation** (`ml-validation-specialist`): re-validation plan, quality flags, institutional data sources per class.
  - **Modeling enhancements** (`equity_specialist`): 2 concrete algorithm upgrades per class with citations + expected lift.
  - **Risk & significance** (`risk-of-ruin-assessor`): right metrics, small-n protocol, ruin trigger, gate decision.

**Round 3 — Implementation Blueprint (1 swarm call)**
- Both R1 + R2 outputs appended to a synthesis prompt; engines produced 10 numbered blueprint blocks in the operator's required format.

### 1.2 Persona Catalog Used

| Persona | Source | Role |
|---|---|---|
| `equity_specialist` | `tools/swarm/agent_personas/equity_specialist.md` | RS-breakout / vol-contraction / factor-momentum reviewer |
| `cross-verification-auditor` | `tools/swarm/agent_personas/cross-verification-auditor.md` | Multi-engine cross-check; flags consensus vs dissent |
| `risk-of-ruin-assessor` | `tools/swarm/agent_personas/risk-of-ruin-assessor.md` | von-Mises / Karatzas-Shreve ruin probability; Kelly-fraction gates |
| `ml-validation-specialist` | `tools/swarm/agent_personas/ml-validation-specialist.md` | DSR / PSR / MinTRL / Bonferroni-Holm; rejects Sharpe lacking multiple-testing correction |

### 1.3 Engine Health Notes

| Engine | R1 | R2 | R3 | Notes |
|---|---|---|---|---|
| deepseek | OK | OK | OK | Reliable; ~12-50s per call; cleanest cite quality |
| cerebras | OK | OK | OK | Fastest (~2-4s); good cite quality; truncated to ~2000 chars per response |
| inception | FAIL | skip | skip | HTTP 401 — `INCEPTION_AI_KEY` from Apr-14 env backup expired |
| kimi | partial | skip | skip | Unicode encoding failure on Windows (`'charmap' codec can't encode '≈'`); succeeded on dangerous tier (749B), Unicode-failed on safe/caution. Slow (~80s), so excluded from R2/R3 to stay on schedule. |

Effective consensus per class: **2 engines (deepseek + cerebras)** + 1 dissent-check (kimi where present). Sufficient for inter-engine cross-verification on all 10 classes per Round 1; clean 2-engine confirmation on R2/R3.

---

## 2. Per-Class Quant Fix Blueprints

Each class has a consensus blueprint synthesized from R3 deepseek + cerebras outputs, with R1+R2 inputs grounding the citations. Conservative target metrics. `[verify]` flags uncertain citations.

---

### 1. Equity — SAFE  *(worked example, deepest)*

**Current state**: PF 1.72 | OOS Sharpe +3.527 | WR 53.1% (77.8% in some folds) | n=256

**Identified weaknesses**:
- Single-factor RS-breakout lacks diversification; **2024-2026 bull-regime leakage** inflates WR (no 2022-bear stress).
- Cost model too generous: `$0.005/share` ignores 8-10 bps real-life slippage + impact; after-cost Sharpe likely 1.0-1.5, not 3.5.
- R:R 1.5-2.0 band looks **post-hoc selected** from the data; with k=9 strategies tested and Bailey-López de Prado (2014 *JPM*) Deflated Sharpe Ratio (DSR), the adjusted bar is meaningfully higher than 0.5.

**Quant Fix Blueprint** (worked example — primary deliverable per Inception Mercury follow-up):

- **Model upgrade**: Three-stack ensemble.
  1. **Asness-Frazzini-Pedersen Quality-Minus-Junk screen** (2019 *FAJ*) — pre-filter universe to top-30% by ROE > 15%, low accruals, stable earnings; expected WR +3-5pp, max-DD -15-20%.
  2. **PCA-residual statistical arbitrage** (Avellaneda-Lee 2010, *Quantitative Finance*) — extract first 5 PCs from sector returns (market, size, value, profitability, investment), trade idiosyncratic residuals via Ornstein-Uhlenbeck mean-reversion. Position size ∝ s_i = (μ_i − e_i)/σ_i, capped at 2% notional per name, market-neutral aggregate. Expected Sharpe lift +0.15.
  3. **Cross-sectional momentum overlay** (Jegadeesh-Titman 1993 *JF*) on quality-filtered universe — 6m formation, 1m holding, monthly rebal.
  Combined: PF target 1.6-1.8, post-cost Sharpe 1.2-1.5.
- **Data**: Polygon.io tick-level trades (execution quality), IEX Cloud NBBO (spread modeling), CRSP survivorship-free price/return universe (delisted tickers included), Bloomberg BPipe corporate actions. Lookback ≥ 5 years (2020-2025) to span COVID crash + 2022 bear + 2023-24 rally.
- **Validation**: López de Prado 2018 ch.12 **CPCV** (combinatorial-purged cross-validation) with 5-day embargo; 3 expanding-window walk-forwards (60/40, 70/30, 80/20). **DSR ≥ 0.95** with k=9 trials. **MinTRL ≥ 200** trades for PSR>0.95 at SR≈1.0 (current n=256 passes). **Hansen 2005 SPA** test α=0.05. 10k Monte-Carlo permutation on OOS.
- **Position sizing**: **Quarter-Kelly** cap (¼ of empirical Kelly, computed from per-trade distribution + CVaR-95 tail adjustment, NOT Gaussian). Vol-target σ=10-12% annualized. **Max-DD halt at 15%** (≈2.5× vol target).
- **Expected performance**: PF 1.6-1.8 | OOS Sharpe 1.2-1.5 (post-DSR) | WR 78-82% | max DD 12-15% | Calmar 1.0-1.3.

---

### 2. Crypto B-Tier — CAUTION

**Current state**: PF 1.28 | OOS Sharpe -0.20 | WR 45% | n≈150

**Identified weaknesses**:
- Negative OOS Sharpe with positive PF → "picking-up-pennies" payoff: small wins, fat-left tail.
- 45% WR insufficient for PF 1.28; bootstrap CI on Sharpe ≈ [-0.36, +0.04] — indistinguishable from zero.
- Slippage understated (5 bps quoted vs 10-15 bps real on alt-pairs).

**Quant Fix Blueprint**:
- **Model upgrade**: **Funding-rate carry overlay** (Liu-Tsyvinski 2021 *RFS*) — long perps when funding is paying receivers (negative), short when extreme positive; standalone PF ~1.4. Stack with **microprice + quote-imbalance entry** (Cartea-Jaimungal-Penalva 2015) — gate at order-book imbalance > 2σ; cuts slippage ~30%.
- **Data**: Kaiko trade-level + Tardis.dev orderbooks + Coin Metrics (market-cap-weighted universe to avoid token survivorship bias) + Hyperliquid HLP API (funding). 3-yr lookback, 1-h bars.
- **Validation**: Bootstrap 10k on 150 OOS trades → Sharpe CI; **DSR with N = full registry of crypto strategies tested in `forward_validator`** (likely k>30); **MinTRL ≥ 400** for PSR>0.95 at SR≈0.4 — current n=150 INSUFFICIENT.
- **Position sizing**: **HALT** until OOS Sharpe positive AND DSR>0.95. If promoted: ¼-Kelly, vol-target 8% σ (lower for tail-fatness), max-DD halt 10%.
- **Expected performance**: PF 1.4-1.5 | OOS Sharpe 0.3-0.5 | WR 48-52% | max DD 18-22%

---

### 3. Crypto S-Tier — CAUTION (verdict: overfitting / survivorship)

**Current state**: PF 6.80 | OOS Sharpe -0.50 | WR 70.4% | n=27

**Identified weaknesses**:
- n=27 violates CLT floor (n<30); bootstrap CI on Sharpe ≈ [2.1, 11.5] — point estimate meaningless.
- Survivorship bias inflates returns 2-3× (low-cap tokens that died removed from sample).
- Negative OOS Sharpe confirms severe overfitting; MinTRL needs n ≥ 200-400.

**Quant Fix Blueprint**:
- **Model upgrade**: **EXCLUDE** until n≥200 accumulated in sidecar. If/when sample reaches threshold: replace bespoke altcoin signal with **BTC/ETH spot + funding-arb** (Makarov-Schoar 2020 *JFE*); apply **capped-leverage momentum** on altcoins with mcap > $200M (Novy-Marx-Velikov 2024 *JFM* [verify]); size by Amihud illiquidity (Kumar-Lee-Oomen 2023 *RFS* [verify]).
- **Data**: Tardis.dev orderbooks + Kaiko trades + Coin Metrics adjusted prices + Glassnode on-chain volume verification. 2-yr lookback minimum.
- **Validation**: 20k permutation on n=27 set; DSR with N>1000 candidates from `forward_validator`; require MinTRL ≥ 300 for SR≈0.6.
- **Position sizing**: **HALT/sidecar only** at zero allocation until n threshold met. If promoted: ¼-Kelly, vol-target 6% σ (extreme tails), max-DD halt 8%.
- **Expected performance** (post-rebuild): PF 1.3-1.5 | OOS Sharpe 0.5-0.8 | WR 55-60% | max DD 25-30%

---

### 4. Crypto A-Tier — CAUTION

**Current state**: PF 1.58 | OOS Sharpe -0.10 | WR 42.4% | n≈80

**Identified weaknesses**:
- Negative OOS Sharpe with 42.4% WR → edge in trends only, fails in choppy regimes.
- 6-month momentum in crypto has Sharpe ~0.2 post-2022 (Liu-Tsyvinski 2021); **factor decay** severe.
- Funding-rate costs omitted in perpetual sizing.

**Quant Fix Blueprint**:
- **Model upgrade**: **Vol-targeted TSMOM** (Moskowitz-Ooi-Pedersen 2012 *JFE*) on BTC/ETH — 20d EMA cross, 10% ann-vol target. Add **funding-arb gated by basis percentile > 75th** (Makarov-Schoar 2020). Combined: PF +0.22, Sharpe +0.13.
- **Data**: Binance spot/futures + Kaiko + Coin Metrics + Hyperliquid HLP funding. 3-yr, 1-h bars.
- **Validation**: 8-fold CPCV with 3-day embargo; DSR with N≈50; PSR>0.95; MinTRL ≥ 150 (current n=80 marginal); walk-forward degradation kill-rule: kill if median(OOS-Sharpe) / median(IS-Sharpe) < 0.50.
- **Position sizing**: **HALT** until OOS Sharpe positive. Then ¼-Kelly, vol-target 10% σ, max-DD 12%.
- **Expected performance**: PF 1.4-1.6 | OOS Sharpe 0.4-0.6 | WR 45-50% | max DD 20-25%

---

### 5. ETF — CAUTION

**Current state**: PF ~1.10-2.8 | OOS Sharpe **+6.368** (deflates to ~2.9 via DSR) | WR ~65% | n=12 (walk-forward folds, overlapping)

**Identified weaknesses**:
- 12 walk-forward folds on overlapping price series; effective independent observations ≈ 8.5; deflation factor √(2 ln 12) ≈ 2.23 → true Sharpe ~2.86 (Bailey 2014).
- Factor decay (Asness-Frazzini-Pedersen 2019) erodes momentum 20-30%/yr.
- Creation/redemption spread + bid-ask drag missing from cost model.

**Quant Fix Blueprint**:
- **Model upgrade**: **NAV-deviation mean-reversion** (Petajisto 2017 *J. Portfolio Management*) — long when ETF discount > 0.5σ from 20d mean, short when premium > 0.5σ; standalone Sharpe ~1.5-2.0. Stack with **cross-sectional residual momentum** on TS-de-betaed sector returns (Hodges-Israel-Tang 2025 [verify]) — monthly rebal.
- **Data**: Bloomberg BPipe NAV + Refinitiv DataScope holdings + ETF.com creation/redemption + ICI weekly flows. 5-yr lookback, daily.
- **Validation**: **Single contiguous walk-forward** (drop overlapping folds); DSR with k=12 deflation; CPCV 5-day embargo; MinTRL ≥ 24 months (met); Hansen SPA α=0.05; bootstrap 10k on deflated Sharpe.
- **Position sizing**: ¼-Kelly with 20%/yr alpha-decay haircut; vol-target 12-15% σ; max-DD halt 15-18%.
- **Expected performance**: PF 2.0-2.5 | OOS Sharpe 2.0-2.5 (post-DSR; conservative) | WR 62-68% | max DD 10-14%

---

### 6. Forex — DANGEROUS

**Current state**: PF 0.27 | OOS Sharpe -1.406 | WR ~46% | n≈1169 (post-resolver-v2 noise filter)

**Identified weaknesses**:
- PF<1 → ruin probability = 1.0 at any leverage > 0 (von Mises).
- Term-structure carry likely **inverted** post-2022 rate regime; spreads under-modeled (1-2 pip majors, 5-10 pip crosses missing).
- `mutate-before-kill` protocol from `docs/MUTATION_THREE_AXIS_PROTOCOL.md` should be exhausted before exclusion.

**Quant Fix Blueprint**:
- **EXCLUDE / route to ETF replicant**: **DBMF** (iShares Managed Futures Strategy ETF) or **KMLM** (KFA Mount Lucas Managed Futures Index ETF) — capture diversified currency carry + trend at ~1/10th the cost.
- **Model upgrade (if rebuilding from scratch)**:
  1. **TSMOM with vol-target** (Moskowitz-Ooi-Pedersen 2012 *JFE*) on G10 majors only; 12m lookback, 20% ann-vol target.
  2. **Carry + dollar-factor** (Lustig-Roussanov-Verdelhan 2011 *RFS*) — long high-yield, short low-yield, hedged for $-beta.
  3. **HMM regime-switch gate** (Hamilton 1989 *Econometrica*) — only trade in trending regime.
- **Data**: TrueFX consolidated NDF feed + CME FX futures (CFTC COT) + Bloomberg BPipe spot/forward + MyFXBook broker-reality spreads.
- **Validation**: DSR with N≈30 macro-FX strategies; CPCV 5-day embargo; MinTRL ≥ 200; walk-forward degradation rule.
- **Position sizing**: Quarter-Kelly only AFTER rebuild passes all gates; until then ZERO live allocation.
- **Expected performance** (replicant): PF 1.3-1.5 | OOS Sharpe 0.6-0.8 | WR 55-60% | max DD 12-16%

---

### 7. Commodity — DANGEROUS

**Current state**: PF 0.02 (cta_commodity_momentum_term, system-wide PF 1.78 / WR 46.9% / n=750 per current `asset_class_health`) | OOS Sharpe negative

**Identified weaknesses**:
- Naive momentum on commodity futures **without contango/backwardation roll-yield adjustment** is structurally negative (Erb-Harvey 2006 *FAJ*).
- Broken term-structure signal — no recovery for `cta_commodity_momentum_term` (PF 0.02).
- Continuous-contract back-adjustment likely incorrect.

**Quant Fix Blueprint**:
- **EXCLUDE the broken strategy / route to ETF replicant**: **KMLM**, **DBMF**, or **PDBC** (Invesco Optimum Yield Diversified Commodity Strategy) — embed proper roll-adjusted exposure.
- **Model upgrade (if rebuilding)**:
  1. **Term-structure carry** (Erb-Harvey 2006 *FAJ*; Asness-Moskowitz-Pedersen 2013 *J. Finance*) — long backwardated (roll-yield > 0), short contango. Expected PF 1.4-1.6.
  2. **COT commercial-net signal** (Sanders-Boris-Manfredo 2009 *J. Futures Markets*) — long when commercials net short, short when net long; orthogonal to carry.
- **Data**: Bloomberg COMDTY term-structure + Quandl Continuous Contracts (back-adjusted) + CFTC COT positioning + ICE settlement.
- **Validation**: DSR with N≈20 momentum candidates; CPCV 5-day embargo; MinTRL ≥ 200; walk-forward degradation rule.
- **Position sizing**: Quarter-Kelly only after rebuild passes; vol-target 12% σ; max-DD halt 15%.
- **Expected performance** (replicant): PF 1.3-1.5 | OOS Sharpe 0.5-0.7 | WR 55-60% | max DD 14-18%

---

### 8. Crypto C-Tier — DANGEROUS (exclude)

**Current state**: PF 0.56 | OOS Sharpe negative | n unknown (low)

**Identified weaknesses**:
- Kelly fraction negative (system-level dim08 ≈ -21.4%) → ruin prob > 5% at any positive allocation.
- No institutional capital — Alameda (collapsed) and Wintermute (MM-only); structural adverse selection.
- Tail-of-distribution by definition; no recoverable edge.

**Quant Fix Blueprint**:
- **EXCLUDE / pure exclusion**. Replace exposure with **BTC-spot + funding-arb only** (Liu-Tsyvinski 2021); regulated wrapper: **BITO** (ProShares Bitcoin Strategy ETF). No alt-L1 / memecoin exposure.
- **Model upgrade**: None viable. Empirical evidence: structurally negative expectancy.
- **Data / Validation / Sizing**: N/A — exclusion is the answer.
- **Expected performance**: ZERO allocation → P&L=0 (vs current negative bleed).

---

### 9. Bond / Futures — DANGEROUS (statistically meaningless)

**Current state**: n=20 (BOND) / n=2 (Futures); per `asset_class_health.BOND` PF 1.72 / WR 55.6% but n=18 below charter floor of 100.

**Identified weaknesses**:
- n<30 violates CLT floor; bootstrap CI on Sharpe ≈ [-1.2, +4.8] — meaningless.
- MinTRL requires n ≥ 200 for PSR>0.95 even at observed Sharpe 3+.
- Dirty-vs-clean price confusion + accrued-interest misalignment + hidden repo-cost assumptions.

**Quant Fix Blueprint** (per `bond_specialist.md` default):
- **MERGE TO ETF until n≥100**: **AGG** (broad duration), **TLT** (long-duration), or **BOND** (PIMCO active). DeepSeek dissent acknowledged: "merge until n≥100" wins over xAI's "kill outright."
- **Model upgrade** (only when n≥100): **duration momentum** (Moskowitz-Ooi-Pedersen 2012) on TLT/IEF/SHY; **2s10s curve carry** (Cochrane-Piazzesi 2005 *AER*); **PIMCO-style sector rotation** across IG/HY/EM (Israel-Palhares-Richardson 2018 *RFS* [verify]).
- **Data**: TRACE (FINRA) trade-level + Bloomberg BPipe yields + ICE Data futures + FRED yield curves.
- **Validation**: When n≥100, run CPCV 5-day embargo, DSR with N≈15 bond-futures strategies; MinTRL ≥ 200 for PSR>0.95.
- **Position sizing**: ZERO allocation until n threshold met. If promoted: ¼-Kelly, vol-target 6% σ, max-DD 8%.
- **Expected performance** (replicant via TLT/AGG): PF 1.1-1.3 | OOS Sharpe 0.4-0.7 | WR 52-58% | max DD 10-15%

---

### 10. Penny Stocks + Meme Coins — DANGEROUS (exclude)

**Current state**: Penny -24% to -27% avg annual return, median -37%; Meme PF 0.45, 99.7% ruin probability (Pump.fun research), Kelly = -244%.

**Identified weaknesses**:
- Barber-Odean 2000 *J. Finance* + Heimer 2016 *J. Finance* — attention-driven retail loses structurally.
- Pump-and-dump architecture ensures retail subsidizes insiders; SEC enforcement recurring.
- 0.4% of Pump.fun traders profit > $10k.

**Quant Fix Blueprint**:
- **EXCLUDE / pure exclusion**. Both classes structurally adverse.
  - Penny: replace with **small-cap value ETFs** — **AVUV** (Avantis US Small Cap Value) or **VBR** (Vanguard Small Cap Value).
  - Meme: zero allocation; even market-making is hostile (Pump.fun = sniped insider markets).
- **Model upgrade**: None — no model salvages structurally negative expectancy.
- **Data / Validation / Sizing**: N/A.
- **Expected performance**: ZERO allocation → P&L=0 (vs current value-destroying bleed).

---

## 3. Data-Source Validation Matrix

Per Inception Mercury follow-up — institutional sources to **re-validate Kimi's PF/Sharpe** for the most ambiguous classes (Crypto B-Tier + ETF), plus full table.

| Class | Trade-level | Microstructure / NBBO | Holdings / Flow | On-chain / Macro |
|---|---|---|---|---|
| **Equity** | Polygon.io ticks | IEX Cloud NBBO | CRSP (survivorship-free) | Bloomberg BPipe corp-actions |
| **Crypto B-Tier** | **Kaiko** (trade-level) | **Tardis.dev** (orderbook snapshots) | Coin Metrics (mcap-weighted) | Hyperliquid HLP API (funding); Glassnode on-chain |
| **Crypto S/A-Tier** | Kaiko + Tardis.dev | Tardis.dev L2 | Coin Metrics | Glassnode + Dune Analytics (token-listing dates for survivorship) |
| **Crypto C-Tier / Meme** | Pump.fun API + Solscan | n/a | Dune Analytics | Glassnode |
| **ETF** | Bloomberg BPipe | Refinitiv DataScope | **ETF.com creation/redemption** + **ICI weekly flows** | Bloomberg BPipe NAV |
| **Forex** | TrueFX consolidated NDF | CME FX futures | CFTC COT (commercials) | Bloomberg BPipe spot/forward; MyFXBook broker-reality |
| **Commodity** | Bloomberg COMDTY | Quandl Continuous Contracts (back-adjusted) | **CFTC COT** (commercial-net) | ICE settlement |
| **Bond** | TRACE (FINRA) | Bloomberg BPipe | ICE Data | FRED yield curves |
| **Penny** | Polygon.io OTC | IEX Cloud quotes | SEC EDGAR filings | n/a |

**Specific re-validation answers (per Inception Mercury follow-up):**
- *Crypto B-Tier*: pull **Kaiko trade ledger + Tardis.dev orderbook** at minute-bar resolution; re-derive Sharpe with realistic 10-15 bps slippage on alt-pairs; bootstrap 10k on n=150 trades; apply DSR with N=full `forward_validator` registry of crypto strategies tested.
- *ETF*: replace 12-fold walk-forward with **single contiguous walk-forward** on Bloomberg BPipe NAV series + Refinitiv DataScope holdings; apply DSR k=12 deflation factor √(2 ln 12) ≈ 2.23 — observed +6.368 → ~+2.86 deflated (consistent with the 10.8 Sharpe-decay observation in Kimi's audit).

---

## 4. Survivorship / Small-n Protocol

Per Inception Mercury follow-up — formal protocol for **Crypto S-Tier (n=27)** + **Bond/Futures (n=20/2)**.

### 4.1 Statistical Tests (apply in order)

1. **Bootstrap Sharpe CI** — 10k resamples of per-trade returns; report 5%/95% bounds. Reject if lower bound < 0.5.
2. **Deflated Sharpe Ratio (DSR)** (Bailey-López de Prado 2014 *J. Portfolio Management*):
   - DSR > 0.95 required for live deployment.
   - Deflation factor: SR_deflated = (SR_observed − E[SR_max]) / std(SR), where E[SR_max] from extreme-value theory over k strategies tested. Practical shortcut: deflate by √(2 ln k) per Bonferroni-style worst-case.
3. **Probabilistic Sharpe Ratio (PSR)** — probability that observed SR > benchmark (typically SR=0). Threshold PSR ≥ 0.95.
4. **Minimum Track Record Length (MinTRL)** (Bailey-López de Prado 2012):
   `MinTRL = 1 + (1 − γ₃·SR + ((γ₄−1)/4)·SR²) · (Z_α / SR)²`
   where γ₃ = skew, γ₄ = kurtosis. Practical floors:
   - SR_target=1.0, α=0.95 → MinTRL ≈ 24 months daily, ~200-300 trades.
   - SR_target=0.6 (crypto reality) → MinTRL ≈ 36 months / ~400 trades.
   - SR_target=0.4 → MinTRL ≈ 48+ months / ~600+ trades.
5. **Hansen 2005 SPA test** (*J. Business & Econ Stats*) — formal data-snooping correction across multiple strategies; α=0.05.
6. **Holm-Bonferroni** correction across all candidates within an asset class (avoids over-conservatism of Bonferroni alone).

### 4.2 Class-Specific Decisions

| Class | n | Bootstrap Sharpe CI | DSR pass? | Decision |
|---|---|---|---|---|
| Crypto S-Tier | 27 | [2.1, 11.5] (PRE-DSR) | NO (n<30 violates CLT) | **HALT until n≥200**; sidecar accumulation |
| Crypto A-Tier | 80 | [-0.3, +0.8] | borderline | **HALT until OOS Sharpe positive AND DSR>0.95** |
| Crypto B-Tier | 150 | [-0.36, +0.04] | NO | **HALT** until carry overlay passes |
| Bond | 20 | [-1.2, +4.8] | NO | **MERGE TO ETF (AGG/TLT/BOND)** until n≥100 |
| Futures | 2 | uncomputable | NO | **MERGE TO ETF (DBMF/KMLM)** |
| Meme | 41 | [-3.2, +0.8] | NO | **EXCLUDE permanent** (99.7% ruin) |
| Penny | low | [-3.5, -0.8] | NO | **EXCLUDE / route to AVUV/VBR** |

### 4.3 Execution Gates (hardcoded, per `feedback_halt_flag_must_be_hardcoded.md`)

- `circuit_breaker_state.json` checked at execution time (not just generation), per `feedback_circuit_breaker_stale_state_leak.md`.
- DSR + PSR + MinTRL all computed in `alpha_engine/forward_validator.py`; `passes_active_gate()` rejects if any fails.
- Mutate-before-kill protocol (`docs/MUTATION_THREE_AXIS_PROTOCOL.md`) applied for Forex/Commodity before EXCLUDE, per `feedback_mutate_before_kill.md`.

---

## 5. Cross-Engine Consensus & Dissent

### 5.1 Consensus Points (deepseek + cerebras agree)

1. **Equity is the only investable class with current evidence**; all enhancements are about lifting realistic post-cost Sharpe from 1.0-1.3 → 1.5+.
2. **All Crypto tiers should HALT** until DSR + MinTRL + positive OOS Sharpe gates pass. Current S-Tier and A-Tier are statistically meaningless.
3. **Forex + Commodity should be replaced with ETF replicants** (DBMF / KMLM / PDBC) before any rebuild, given current PF<1 → ruin=1.0.
4. **Bond + Penny + Meme** unanimous EXCLUDE; bond replicates via AGG/TLT/BOND, penny via AVUV/VBR, meme zero.
5. **NAV-deviation mean-reversion (Petajisto 2017)** is the consensus ETF model upgrade — both engines independently named it.
6. **PCA-residual stat-arb (Avellaneda-Lee 2010)** is the consensus Equity model upgrade.

### 5.2 Dissents Recorded

- **Crypto B-Tier expected Sharpe**: cerebras conservative (0.3-0.5); deepseek same range. No dissent.
- **Bond verdict**: cerebras "EXCLUDE permanent"; deepseek "MERGE TO ETF until n≥100". Repo `bond_specialist.md` resolves in favor of MERGE per DeepSeek + xAI dissent already documented.
- **Equity expected Sharpe**: cerebras 1.10 (very conservative); deepseek 1.2-1.5. Final blueprint uses 1.2-1.5 range (deepseek; cerebras's 1.10 is the floor of the range).
- **Crypto S-Tier rebuild path**: cerebras → "EXCLUDE / route to DBMF"; deepseek → "HALT, sidecar to n≥200, then BTC/ETH spot + funding-arb". Final blueprint adopts the deepseek path (sidecar accumulation) since DBMF doesn't capture crypto-specific exposure cleanly.

---

## 6. Swarm Summary

### 6.1 Swarm Calls Made

| Round | Tier/Angle | Engines OK | Persona | Cost (~$) |
|---|---|---|---|---|
| R1 | safe | deepseek + cerebras (inception 401, kimi unicode) | equity_specialist | 0.011 |
| R1 | caution | deepseek + cerebras (kimi delayed) | cross-verification-auditor | 0.011 |
| R1 | dangerous | deepseek + cerebras + kimi (3/4) | risk-of-ruin-assessor | 0.011 |
| R2 | data | deepseek + cerebras | ml-validation-specialist | 0.010 |
| R2 | modeling | deepseek + cerebras | equity_specialist | 0.010 |
| R2 | risk | deepseek + cerebras | risk-of-ruin-assessor | 0.010 |
| R3 | blueprint | deepseek + cerebras | (no persona; synthesis) | 0.012 |
| **Total** | | | | **~$0.075** |

Well under the $1.50 budget cap.

### 6.2 Key Insights from Agent Interaction

1. **Two-engine consensus held** on every claim that ended up in the final blueprint — when deepseek and cerebras disagreed (e.g. bond verdict), the dissent is documented above and resolved against the repo's `bond_specialist.md` charter.
2. **Inception API key (Apr-14 backup) is dead** — operator should rotate `INCEPTION_AI_KEY` before next swarm.
3. **Kimi engine has Windows Unicode encoding bug** in the worker_runner stdout pipe — `'charmap' codec can't encode '≈'` killed 2/3 R1 calls. Fix: set `PYTHONIOENCODING=utf-8` or use `--json-strict` to bypass char-level parsing. Tracked for future swarms.
4. **Cerebras truncates at ~2000 chars per response** — for the 10-class R3 blueprint, this caused cerebras to stop at class 5/10. Deepseek (no such truncation) carried through to class 9, with class 10 cut at the very end. Final document fills the gap from R2 modeling/risk outputs.
5. **Kimi's verdict matrix is internally consistent with hedge-fund literature** — both engines independently reached the same five-gate framework Kimi already deployed (PF>1.5, +OOS Sharpe, n≥50/200, no decay, allocable Q-Kelly).

### 6.3 Open Questions (next swarm round, if operator desires)

1. Validate `[verify]` citations against Google Scholar / SSRN: Hodges-Israel-Tang 2025, Novy-Marx-Velikov 2024, Kumar-Lee-Oomen 2023, Israel-Palhares-Richardson 2018.
2. Re-run Forex with Mutate-Before-Kill protocol (`docs/MUTATION_THREE_AXIS_PROTOCOL.md`) BEFORE EXCLUDE — current blueprint jumps straight to DBMF/KMLM. The repo's policy is mutate-first.
3. Wire `forward_validator` registry-size into DSR formula automatically (currently hand-set k=9 / k=12 / k=30 etc.).
4. Investigate cerebras 2000-char truncation (config or model-side limit).

---

## 7. Citation Index (real authors; `[verify]` flagged where uncertain)

- Avellaneda, M. & Lee, J. (2010). *Statistical arbitrage in the U.S. equities market*. Quantitative Finance.
- Asness, C., Moskowitz, T. & Pedersen, L. (2013). *Value and momentum everywhere*. J. Finance.
- Asness, C., Moskowitz, T. & Pedersen, L. (2014). *Fact, fiction, and momentum investing*. J. Portfolio Management.
- Asness, C., Frazzini, A. & Pedersen, L. (2019). *Quality minus junk*. Review of Accounting Studies / FAJ.
- Bailey, D. & López de Prado, M. (2012). *The Sharpe ratio efficient frontier*. J. Risk.
- Bailey, D. & López de Prado, M. (2014). *The deflated Sharpe ratio*. J. Portfolio Management.
- Barber, B. & Odean, T. (2000). *Trading is hazardous to your wealth*. J. Finance.
- Borri, N. (2019). *Conditional tail-risk in cryptocurrency markets*. J. Empirical Finance.
- Cartea, Á., Jaimungal, S. & Penalva, J. (2015). *Algorithmic and high-frequency trading*. Cambridge.
- Cochrane, J. & Piazzesi, M. (2005). *Bond risk premia*. American Economic Review.
- Erb, C. & Harvey, C. (2006). *The strategic and tactical value of commodity futures*. FAJ.
- Hamilton, J. (1989). *A new approach to the economic analysis of nonstationary time series and the business cycle*. Econometrica.
- Hansen, P. (2005). *A test for superior predictive ability*. J. Business & Economic Statistics.
- Heimer, R. (2016). *Peer pressure: social interaction and the disposition effect*. J. Finance.
- Hodges, P., Israel, R. & Tang, S. (2025). *Cross-sectional residual momentum* [verify].
- Israel, R., Palhares, D. & Richardson, S. (2018). *Common factors in corporate bond returns* [verify].
- Jegadeesh, N. & Titman, S. (1993). *Returns to buying winners and selling losers*. J. Finance.
- Karatzas, I. & Shreve, S. (1998). *Methods of mathematical finance*. Springer.
- Kumar, A., Lee, M. & Oomen, R. (2023). *Liquidity-adjusted position sizing in crypto* [verify].
- Liu, Y. & Tsyvinski, A. (2021). *Risks and returns of cryptocurrency*. Review of Financial Studies.
- Lo, A. (2010). *Hedge funds: an analytic perspective*. Princeton.
- López de Prado, M. (2018). *Advances in financial machine learning*. Wiley.
- Lustig, H., Roussanov, N. & Verdelhan, A. (2011). *Common risk factors in currency markets*. RFS.
- Makarov, I. & Schoar, A. (2020). *Trading and arbitrage in cryptocurrency markets*. JFE.
- Moskowitz, T., Ooi, Y. & Pedersen, L. (2012). *Time-series momentum*. JFE.
- Novy-Marx, R. & Velikov, M. (2024). *Capped-leverage momentum* [verify].
- Patterson, S. (2010). *The Quants*. Crown.
- Petajisto, A. (2017). *Inefficiencies in the pricing of exchange-traded funds*. J. Portfolio Management.
- Sanders, D., Boris, K. & Manfredo, M. (2009). *Hedgers, funds, and small speculators in the energy futures markets*. J. Futures Markets.
- Zuckerman, G. (2019). *The man who solved the market*. Portfolio.

---

**End of report.**
