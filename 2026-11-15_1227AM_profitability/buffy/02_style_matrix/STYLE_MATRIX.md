# 02 — Asset Class × Holding Period × Trading Style

**Date:** 2026-11-15 · **Author:** Buffy

Two questions: for each class, **which holding period can pay for its own costs**; and **which named
algorithms are actually documented** (contest-audited or peer-reviewed), as opposed to systems that
merely have a landing page.

---

## 1. The cost ladder that decides everything

Edge must exceed round-trip cost **at the horizon you trade**. This single table kills most retail styles.

| Style | Typical holding | Trades/yr | Round-trip cost (liquid) | Required gross edge/trade | Who can clear it |
|---|---|---|---|---|---|
| **Scalping** | seconds–minutes | 5,000–50,000 | 1–3 bps + spread | >3–5 bps | market makers, latency owners only |
| **Day trading** | minutes–hours | 500–2,000 | 3–8 bps | >8 bps | prop desks, some systematic |
| **Swing** | 2–20 days | 30–120 | 8–20 bps | >20 bps | retail systematic, **plausible** |
| **Position** | 1–6 months | 6–24 | 15–30 bps | >30 bps | retail systematic, plausible |
| **Long-term / allocation** | 3–20 years | 0.05–0.3 | 3–10 bps one-off + ER | risk premium | **anyone** — this is beta |

The repo's measured per-trade Sharpe (CRYPTO 0.005, ETF 0.014, EQUITY 0.054, FOREX 0.061) is **below the
day-trading and scalping columns** and above the swing/position columns. That is the whole argument
against intraday: the strategies are producing swing-sized edge while being executed intraday.

---

## 2. Class × style viability matrix

`✓` viable and measurable here · `~` plausible, untested · `✗` fails cost or structure · `?` no data

| Class | Scalp | Day | Swing | Position | Long-term | Why |
|---|---|---|---|---|---|---|
| **EQUITY** | ✗ | ✗ | **✓** | ✓ | ✓ (beta) | RSI-2 style reversion is a swing premium; intraday needs fills this system can't model |
| **ETF** | ✗ | ✗ | ~ | **~** | **✓** | 200-DMA trend is monthly/weekly; buy-and-hold is measured (90.2% of 10y windows +) |
| **CRYPTO** | ✗ | ✗ | ~ | ~ | ✗ | 24/7, funding + liquidation edges are hours-to-days; vol 60–80% makes sizing dominate signal |
| **FOREX** | ✗ | ~ | ~ | ✗ | ✗ | carry is weeks-months but 10–20 bps spread vs single-digit-bp edge |
| **COMMODITY** | ✗ | ✗ | ~ | ~ | ? | COT positioning is weeks-months; n=7 verified, cannot judge |
| **FUTURES** | ✗ | ✗ | ~ | ~ | ? | roll yield is monthly; 0 verified marks |
| **BOND** | ✗ | ✗ | ✗ | ~ | ✓ (duration) | carry/duration is a hold, not a trade; measured PF 0.59 |
| **MEME / PENNY** | ✗ | ✗ | ✗ | ✗ | ✗ | measured PF 0.02 / 0.18 |
| **MUTUAL FUND** | ✗ | ✗ | ✗ | ✗ | **✓** | once-daily NAV; only monthly-clock allocation is executable |

**Read the diagonal:** the only cells with both a mechanism and supporting data are EQUITY swing/position,
ETF long-term, and (thinly) FOREX swing. Everything intraday is structurally excluded by cost.

---

## 3. Documented, contest-audited algorithms

The World Cup Trading Championships (Robbins, live capital, broker-audited, since 1984) is the closest
thing to a public, falsifiable track record. Figures below are the organiser's published net returns,
as reproduced by [completetradersedge.com](https://completetradersedge.com/world-cup-trading-championships)
and [worldcupchampionships.com](https://www.worldcupchampionships.com/).

| Trader | Year(s) | Net return | What is actually established |
|---|---|---|---|
| Larry Williams | 1987 | **+11,376%** | One audited year, ~$10k → ~$1.1M. Never beaten; ~45× the median champion (251.8%) |
| Andrea Unger | 2008 / 2009 / 2010 / 2012 | +671.9% / +115.4% / +239.6% / +82.8% | **Only four-time champion** — the strongest repeatability evidence in the contest |
| Kurt Sakaeda | 2000 / 2004 | +595.3% / +929.1% | Repeat winner |
| Michael Cook | 2007 / 2014 | +249.7% / +366.0% | Repeat winner |
| Chuck Hughes | 1999 / 2015 | +315.6% / +309.1% | Repeat winner |
| Kevin Davey | 2006 | +106.7% | Won with the *lowest* return of the modern era — consistency over spectacle |
| Michelle Williams | 1997 | +1,001.0% | Won as a teenager using her father's method — suggests method transfer, not luck |
| Stefan Seibert | 2020 / 2022 | +342.3% / +262.3% | Repeat winner in the modern era |

**What this table does and does not prove.** It proves these are real, audited, live-capital results.
It does **not** prove persistence: the organiser itself disclaims that a WCC account may not represent
all accounts a competitor controls. One contest year ≠ a decade of managed money. The honest reading:
**repeat winners (Unger, Sakaeda, Cook, Hughes, Seibert) are the only evidence of durability**, and the
common thread among them is risk control and small position sizing, not signal cleverness.

**"Hoffman"** — I could not verify any World Cup or TradingView contest winner by that name in the
organiser standings. I am not going to assert one. If you mean a specific person (Hoffman? Hoffmann?
Hoffman of a particular firm), give me the context and I'll check it directly.

**TradingView contests** are *not* audited performance competitions — they are Pine Script / idea
contests judged on originality and presentation. A TradingView "winner" badge carries no return claim.
Treat any strategy marketed on that basis as **unvalidated**.

**Peer-reviewed / literature-backed (stronger than any contest):**
- **Time-series momentum** (Moskowitz, Ooi, Pedersen 2012) — 12-month lookback, cross-asset. The basis for ETF/futures trend rules.
- **Faber 2007 tactical allocation** — 10-month SMA; the specific rule behind `etf_200dma_trend`.
- **Connors & Alvarez RSI-2** — the actual basis of `stocks_rsi2_pullback` and `etf_rsi2_pullback`.
- **Deflated Sharpe / PBO** (Bailey & López de Prado) — the correction any of the above needs after being tested 361 times.

---

## 4. Mapping famous methods onto this repo

| Method | Repo implementation | Status here | Style/horizon |
|---|---|---|---|
| RSI-2 mean reversion | `stocks_rsi2_pullback`, `etf_rsi2_pullback` | EQUITY PF 1.15/738 marks; ETF all-zero closes | swing |
| Faber 10-month SMA | **not implemented** | — | position / long-term |
| Time-series momentum | `cta_cross_asset_tsmom` | FOREX PF 3.57 raw, inflated by one bad row | position |
| COT positioning | `multi_asset_cot` | PF 21.33 on n=144 = concentration artefact | position |
| Funding-rate carry | `funding_rate_arb.py` | needs T-bill cash-floor comparison (3.7–4.8% vs 4.5%) | days |
| 200-DMA trend | **not implemented** | — | position |

Two of the six highest-confidence documented methods in finance are **absent** from a system with 361
strategies. That is a statement about where the effort went.

---

## 5. The style conclusion

1. **Do not scalp or day trade here.** Measured per-trade Sharpe is below the cost floor for those styles, and the system cannot model fills well enough to try.
2. **Swing (2–20 days) is where the measured edge lives** — EQUITY reversion, FOREX trend.
3. **Position/long-term is where the *reliable* return lives** — ETF/Faber trend and plain beta.
4. **Contest records are not strategies.** They are existence proofs that audited profit is possible with strict risk control. Copy the risk control, not the signal.
5. Any method claiming TradingView-contest provenance should be treated as **unproven** until it clears the L1 gates.
