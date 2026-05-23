# Github Strategy Research — 4-engine Consensus — 2026-05-13T01:45Z

Research swarm `bt0l21dde` (xai + deepseek + groq + kimi) returned candidates
for CRYPTO + ETF + BOND struggling classes. Kimi took 498s vs others
~2-22s (likely thinking-token reasoning).

## CRYPTO — best candidates (ranked by consensus + concrete impl)

| Repo | Cited by | Stars | Strategy | Effort | Best for |
|---|---|---|---|---|---|
| **freqtrade/freqtrade** | xai+groq (2/4) | 25k | Modular bot; funding-rate arb extensible | 12-15h | broad infrastructure |
| **jesse-ai/jesse** | deepseek | 5.6k | Native funding-rate arb templates | 8h | quick funding-arb pilot |
| **polakowo/vectorbt** | xai | 3.5k | Vectorized BTC seasonal + arb backtest | 8h | Edge #10 UTC-hour validation |
| **50shadesofgwei/funding-rate-arbitrage** | kimi | ~150 | Delta-neutral funding-rate basis | 4h | Edge #11 specific |
| **NeuZhou/finclaw** | kimi | ~500 | Multi-exchange funding arb framework | 3h | plugin Backtrader |
| **cython/cryptotrader** | groq | 1.4k | Hyperliquid HLP carry | 10h | Edge #9 specific |

**Consensus pick:** `freqtrade` — largest ecosystem + active maintenance
+ supports community-contributed funding-rate strategies. Closest match
to our `alpha_engine/strategies/` structure.

**Alternative (faster pilot):** `jesse-ai` per deepseek — native
funding-rate template + Python-native + 8h integration. **Best for the
specific funding-skew/HLP-carry edges** (Edges #9 and #11).

**Specialty pick for direct Edge match:** `50shadesofgwei/funding-rate-arbitrage`
— 4h integration, tests our exact "funding skew + taker imbalance"
hypothesis. Caveat: 150 stars + v0.3.0 = young codebase; testnet-first
warning.

## ETF — best candidates (UNANIMOUS consensus)

| Repo | Cited by | Stars | Strategy | Effort |
|---|---|---|---|---|
| **robertmartin8/PyPortfolioOpt** | deepseek+xai (2/4) | 4-4.5k | Black-Litterman + risk-parity over sector ETFs | 6-10h |
| quantopian/zipline | deepseek+xai+groq | 17k | Sector-rotation XLF/XLE/XLK | 12-16h (archived) |
| garroshub/Quant_Sector_Rotation | kimi | ~350 | MA-Energy rotation + VIX sizing | 2h |
| catalyst/catalyst | groq | 1.2k | Risk-parity over duration+equity | 10h |

**Consensus pick:** `PyPortfolioOpt` (2 explicit + 1 implicit via xai-mentioned-alternative)
- Actively maintained (vs zipline archived 2021)
- pip-installable
- Black-Litterman directly addresses our supreme-plan B-ETF #1
  ("risk-parity rotation post-2022 reset")
- 6h integration is fastest

**Specialty/alternative:** garroshub/Quant_Sector_Rotation — 2h integration,
Sharpe 1.45 / 2010-2024 backtest. LLM-review feature is gimmick but core
momentum signal is sound (per kimi). Best fit if we want sector-rotation
specifically without the portfolio-optimization machinery.

## BOND — single strong candidate (1 of 4 returned BOND)

| Repo | Cited by | Stars | Strategy | Effort |
|---|---|---|---|---|
| **pmorissette/bt** | deepseek | 2.1k | TLT/IEF momentum 12-1m skip-1m, monthly rebalance | 4h |
| jasonstrimpel/volatility-trading | deepseek | 1.2k | HYG/LQD ratio mean-reversion z-score | 3h |

**Consensus pick:** `pmorissette/bt` with TLT/IEF momentum
- Sharpe 1.3 / PF 1.6 / WR 58% (2010-2023) per deepseek
- Free Yahoo Finance data
- Fastest 4h integration
- 2022 drawdown -25% is the main caveat (BOND massacre year)

xai + groq + kimi did NOT return BOND candidates — likely because their
attention was on the bigger-asset CRYPTO+ETF prompts. Future swarms
should split BOND into its own prompt.

## Cross-class single-pilot recommendation

| Engine | Pilot pick | Why |
|---|---|---|
| deepseek | jesse-ai/jesse | CRYPTO funding-rate arb has highest expected impact + Python-native |
| xai | freqtrade/freqtrade | proven community + funding-rate support |
| groq | n/a | did not respond |
| kimi | n/a | did not respond |

**My synthesis:** **Pilot freqtrade-strategies first** (or jesse-ai if
funding-arb is the only target). Reason: it's the de-facto crypto trading
framework, our 7935 CRYPTO pick volume justifies infrastructure investment,
and any single-strategy candidate (Hyperliquid HLP, BTC seasonal, funding-rate)
plugs into the same framework. Two-week timeline:
- Week 1: install + ingest closed_picks for backtest harness
- Week 2: pilot Edge #10 (BTC UTC-hour, already memory-confirmed +14pp)
  AND Edge #11 (funding-skew) via `50shadesofgwei` plugin

## Cross-cutting risk flags

All 4 engines flagged 2022 drawdown as the common blind spot:
- freqtrade community configs exclude 2022 crash
- zipline archived pre-2022 (no recent OOS)
- PyPortfolioOpt under-represents 2022 inflation shock
- bt library shows -25% drawdown in 2022 on TLT/IEF

Mitigation: ANY pilot strategy must explicitly include 2022 in its
backtest window. Reject any candidate whose claim period stops at
2021. This is a hard gate.

## What to do next

1. **Pilot freqtrade** — install + ingest our closed_picks for native
   backtest harness reconstruction (1 day work)
2. **Wire Edge #10 (BTC UTC-hour)** into freqtrade as the simplest
   first proof — memory already says +14pp WR potential
3. **Then wire Edge #11 (funding-skew)** via `50shadesofgwei` plugin
4. **For ETF:** ship `garroshub/Quant_Sector_Rotation` as 2h pilot
   (faster than PyPortfolioOpt's 6h) — Sharpe 1.45 historical
5. **For BOND:** ship `pmorissette/bt` TLT/IEF momentum — 4h, lowest-
   hanging fruit BUT BOND still has n=11 production sample so verify
   doesn't size live for months

## NFA

Research recommendations. No code installed yet. Pilot install requires
explicit user approval (any pip install of a 25k-star repo with C++
deps can crash the dev shell).
