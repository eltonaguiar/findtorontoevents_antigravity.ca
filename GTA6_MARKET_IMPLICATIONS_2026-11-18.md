# GTA 6 / Grand Theft Auto VI — Market Implications & Pick Candidates
**Date:** 2026-11-18 | **Status:** Research report (internal trading-strategy repo)

## 1. Release facts
- **Source:** Rockstar Games official site, https://www.rockstargames.com/VI (fetched directly). Page renders "Coming November 19, 2026".
- **Confirmed:** Rockstar announced GTA VI; official release window shown on Rockstar's page is **November 19, 2026** (previously the 2025 window was delayed). Trailer 1 launched May 6, 2025 (also shown on the page).
- **Rumored/unconfirmed:** Specific first-week sales figures, PC release timing, online mode launch details, crypto/blockchain features — none are officially confirmed.
- Rockstar Newswire (https://www.rockstargames.com/newswire) fetched but is a JS-rendered shell (no article text in HTML); could not extract additional confirmations from it.
- **Officially confirmed vs rumored:** Only the Nov 19, 2026 date and the trailer appear on Rockstar's own page; all other details (crypto, sales, PC port) are rumors.

## 2. Take-Two Interactive (TTWO) equity
- **Source that worked:** Yahoo Finance chart API `https://query1.finance.yahoo.com/v8/finance/chart/TTWO` (returned full JSON). Stooq CSV endpoint returned empty (RC=28 / no data) — did NOT work.
- **Current price:** $217.15 (regular market, 2026-11-18), +6.48% on the day. 52-wk high $265.94, low $183.86. Volume 9.54M.
- **6-month history:** $242.16 (May 18) → peak $258.41 (Jul 6) → trough $190.17 (Oct 30) → $217.15 (Nov 18). 30d +5.05%, 90d -9.58%.
- **Analyst targets:** Nasdaq API `https://api.nasdaq.com/api/analyst/TTWO/targetprice` returned consensus: low $262, high $330, mean $290.5, 16 buy / 0 sell / 0 hold (consensus Buy). Yahoo quoteSummary returned "Invalid Crumb" (did not work).
- **Read:** TTWO trades ~25% below consensus target; the GTA6 release is the dominant catalyst.

## 3. Other equity names with GTA-6 linkage
| Ticker | Price (2026-11-18) | Linkage | Strength |
|---|---|---|---|
| MSFT | $507.72 | Xbox console/platform for GTA6; Game Pass | Weak (GTA6 not exclusive; revenue share) |
| SONY (NYSE) / 6758.T | $26.66 / ¥4241 | PlayStation console — GTA6 historically PlayStation-first marketing; hardware cycle | Moderate-weak (narrative) |
| NVDA | $151.10 | GPU/PC port demand if PC version ships | Speculative (PC timing unconfirmed) |
| EA | $209.70 | Peer game publisher; no direct GTA6 linkage | None (narrative only) |
| Console peripherals (Logitech, Razer) | not verified | Speculative demand uplift | Speculative |

Honesty: Only TTWO has a direct, quantifiable revenue linkage. Console makers have a real but indirect and already-priced linkage. GPU/peripheral links are narrative.

## 4. Crypto angle
- No official partnership between any token issuer/exchange and Rockstar/Take-Two found via fetches. GTA Online historically has had no cryptocurrency.
- **Verdict: NO VERIFIABLE CRYPTO LINKAGE.** Any "GTA6 crypto token" is unverified/speculative.

## 5. Prediction markets
- Polymarket Gamma API (`https://gamma-api.polymarket.com/markets`) queried; **0 markets** matching GTA / Grand Theft / Take-Two out of 100 fetched. Polymarket search page also returned no GTA-6 market listings.
- Kalshi search page returned no GTA-6 matches.
- **Verdict: NONE FOUND** for GTA-6 release date / first-week sales / delay markets as of 2026-11-18.

## 6. Verdict line
**Proven edge: NO / UNPROVEN** — TTWO's GTA6 catalyst is well-known and largely priced; analyst consensus is Buy with ~$290 target vs $217 price, but that is a published consensus, not a proven edge. No prediction-market or crypto mispricing was found to exploit. Treat as narrative, not tradeable edge.

## Data sources that actually worked
- Yahoo Finance chart API (TTWO, MSFT, SONY, NVDA, EA, 6758.T) — worked.
- Nasdaq analyst target API (TTWO consensus) — worked.
- Rockstar Games /VI page (release date) — worked.
- Polymarket Gamma API + search — worked (no GTA markets).
- Kalshi search — worked (no GTA markets).
- Stooq CSV — did NOT work (empty). Yahoo quoteSummary — did NOT work (crumb).
