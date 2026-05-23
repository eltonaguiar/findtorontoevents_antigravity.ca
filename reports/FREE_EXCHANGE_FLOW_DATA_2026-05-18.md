# Free Alternatives to CryptoQuant Exchange Net-Flow Data — Research Report

**Date:** 2026-05-18
**For:** C-2 / H-018 net-flow cross-sectional spread strategy
**Method:** Multi-round agent research swarm (4 rounds, 11 engine responses) + direct
Grok consultation (headless) + 8 web verifications of current (2026) free-tier terms.
**Brief:** `swarm_runs/_prompts/free_exchange_flow_data_2026-05-18.md`
**Swarm output dirs:** `swarm_runs/free-exchange-flow-r1/ .../r2/ .../r3/`

---

## TL;DR

**There is no truly free 1:1 replacement for CryptoQuant's per-coin exchange
net-flow feed.** Exchange-wallet *attribution* (knowing which addresses belong to
which exchange, and maintaining that as exchanges rotate hot wallets) is the moat
every paid vendor charges for.

- **Best free path:** a **self-built Dune Analytics query on the `cex.flows` /
  `cex.addresses` Spellbook tables** (free tier = 2,500 credits/month, API
  included). Strong for EVM coins (ETH, BNB, AVAX, LINK); medium effort for
  BTC/SOL; weak attribution for XRP/ADA/DOGE/LTC.
- **Honest verdict:** Dune gets you ~70–85% of CryptoQuant quality for backtest
  /research, but with real SQL effort + ongoing label maintenance and patchy
  non-EVM coverage. **For a production trading signal, the cheapest paid fallback
  — CryptoQuant Advanced ~$29/mo (or Professional ~$99/mo for full token API) —
  is the rational answer.** Multiple engines independently said: "if you value
  your time at >$30/hr, just pay."

---

## 1. Ranked table of free / near-free sources (verified, 2026)

| # | Source | Truly free? | Per-coin exchange-attributed flow? | History depth | API or scrape | Effort | Verdict |
|---|--------|-------------|-----------------------------------|---------------|---------------|--------|---------|
| 1 | **Dune Analytics** (`cex.flows`, `cex.addresses`) | **Yes** — 2,500 credits/mo, API included on free tier | **Yes, if you build the SQL.** Curated labels for major CEX wallets | Full chain history (limited by when labels were added) | API (free tier) + SQL editor | **High** (4–20 h to build/validate 10 coins; periodic label upkeep) | **Best free option** |
| 2 | DefiLlama (`/cexs`, `/protocol/{cex}`) | Yes — no login, free API | **No** — gives total CEX *balance/holdings* (PoR-based); you diff snapshots for approximate aggregate net-flow, not per-coin daily flow | ~2 yr | Free API + CSV export | Low | Useful aggregate complement; insufficient alone |
| 3 | CryptoQuant **free tier** | Charts only | Partial — BTC/ETH/SOL netflow charts, ~3 yr in UI | ~3 yr (UI) | **No free API for flow endpoints** (Pro/Premium only) | Low | Visual cross-check only; not pipeline-able |
| 4 | Coinglass (web `/spot-inflow-outflow`) | Free web tables; **no free API** | Spot netflow for BTC/ETH/SOL/XRP/DOGE — but this is **order-flow/taker pressure**, not on-chain wallet-attributed flow | 5m–30d windows | Scrape only (API = $29+/mo Hobbyist) | Med (scrape) | Different metric; supplement not match |
| 5 | Glassnode **free tier** | Free signup | **No** — exchange netflow is T2 "Essential" (paid). Free = T1 only, **no API on free** | n/a on free | Paid API only | n/a | Not usable free |
| 6 | Santiment SanAPI free | Yes | Exchange in/outflow metrics exist but **restricted on free**: ~1 yr history **minus last 30 days** (30-day lag), **1,000 calls/month total** | 1 yr, 30-day hold | GraphQL API | Low | 30-day lag = look-ahead-safe but stale; 1k calls/mo too thin for 10 coins × 18 mo daily |
| 7 | Arkham Intelligence | Free web tier | Yes for forensic ("address X sent to Binance"); weak for **bulk 18-mo daily aggregates/export** | varies | Web; API = enterprise/pilot | Med-High | Great for spot-checks, not a feed |
| 8 | Nansen | Free = 1,000 one-time trial credits | Yes (`/tgm/flows`) but credits deplete fast; free tier read-only dashboard otherwise | full | API behind paid | n/a | Trial only — not sustainable |
| 9 | Whale Alert | Free trial then ~$29/mo | **No** — only large individual transfers (>$10M-ish), no aggregation | real-time only | API | n/a | Misses small/mid flows; not net-flow |
| 10 | BGeometrics | Yes | BTC-only inflow/outflow/netflow/reserves | ~4 yr | API, **~8–15 req/day** | Low | BTC only, tiny limits |
| 11 | blockchain.com / Etherscan-BscScan | Yes | **No** — raw tx / basic stats; you must label exchange addresses yourself | full | API | Very high | Raw material only — equivalent to building Dune from scratch |
| 12 | Amberdata / IntoTheBlock / Messari / Token Terminal | No free flow API | Dashboard-only or paid | varies | paid | n/a | Not free for this use case |

**Critical distinction (per the brief, and H-014's prior kill):** generic on-chain
transfer *volume* is NOT what H-018 needs and is **insufficient**. Only sources
with maintained **exchange-wallet labels** (Dune `cex.*`, CryptoQuant, Glassnode,
Nansen) produce true exchange-attributed net-flow. DefiLlama/Coinglass give
adjacent metrics (PoR balance deltas / taker order-flow) that are *not* the same
signal.

---

## 2. #1 Recommendation — Self-built Dune query on `cex.flows`

**Source:** Dune Analytics free tier — 2,500 credits/month, API access included
(verified at `docs.dune.com/learning/how-tos/credit-system`, 2026). Credits are
compute-based; simple daily GROUP-BY aggregates are cheap, so 10 coins × daily is
well within budget. Free-tier rate limit ~15 req/min (executions), 2 min query
timeout, exports cost credits (~1 credit/1k rows).

**Tables (Dune Spellbook):**
- `cex.flows` — ready-made exchange flow classification, **EVM chains only (~21:
  Ethereum, BNB Chain, Avalanche, Arbitrum, Polygon, Base, etc.)**. Columns
  include `block_time`, `blockchain`, token identity, `amount_usd`, and a
  `flow_type` of inflow/outflow per transfer. **This directly serves ETH, BNB,
  AVAX, LINK** (and stablecoins) — a daily per-coin netflow query is ~10 lines.
- `cex.addresses` — curated labeled CEX hot/cold/deposit wallets across **~29
  chains incl. Bitcoin, Solana, Tron**. Used to hand-build BTC/SOL flows by
  joining against native transfer tables.
- `cex.deposit_addresses` — heuristic per-user deposit addresses that consolidate
  into CEX hot wallets.

**Data-fetch plan (look-ahead-free):**

1. **EVM coins (ETH, BNB, AVAX, LINK) — low effort.** One query on `cex.flows`:
   ```sql
   SELECT date_trunc('day', block_time) AS day,
          blockchain, symbol,
          SUM(CASE WHEN flow_type='inflow'  THEN amount_usd ELSE 0 END) AS inflow_usd,
          SUM(CASE WHEN flow_type='outflow' THEN amount_usd ELSE 0 END) AS outflow_usd,
          SUM(CASE WHEN flow_type='inflow'  THEN amount_usd ELSE -amount_usd END) AS net_flow_usd
   FROM cex.flows
   WHERE block_time >= NOW() - INTERVAL '18' MONTH
     AND symbol IN ('ETH','BNB','AVAX','LINK','USDT','USDC')
   GROUP BY 1,2,3 ORDER BY 1;
   ```
2. **BTC, SOL — medium effort.** Join `cex.addresses` (filtered to the chain)
   against `bitcoin` UTXO outputs / `tokens_solana.transfers`; sum value where
   `to`/`from` is a labeled exchange address. Community dashboards already do
   this — fork "CEX flows" / "exchange netflow" / Solana CEX queries rather than
   writing from zero.
3. **XRP, ADA, DOGE, LTC — weakest.** Labels are thin; accept partial coverage,
   or drop these coins from H-018's universe initially and add them once labels
   improve. Do NOT substitute generic volume here.
4. **History backfill (look-ahead-free):** run the query once with the full
   18-month `block_time` window — Dune returns the *historical* per-day values as
   they were on-chain, so each day's net-flow is knowable at that day's UTC
   close. Store in a local DB keyed by `date`. **Caveat:** Dune labels are not
   perfectly retroactive — a wallet only counts from when it was labeled — so
   very old history has slightly thinner coverage than recent. This is a known,
   bounded bias; document it in the backtest.
5. **Daily live refresh:** schedule one API execution at ~00:10 UTC for the
   prior UTC day across all coins. Well within 2,500 credits/mo.
6. **Label drift maintenance:** exchanges rotate hot wallets — re-check
   `cex.addresses` coverage roughly quarterly (hours/quarter, not daily). Spellbook
   accepts PRs to add missing addresses.

**Validation step (mandatory before wiring into H-018):** cross-check the Dune
BTC/ETH netflow series against CryptoQuant's *free* BTC/ETH/SOL netflow charts
(visual) and DefiLlama aggregate CEX balance deltas. If Dune is within ~10–20% of
CryptoQuant's shape/direction, it is good enough for the cross-sectional spread
(H-018 ranks coins relative to each other — it needs correct *sign and ordering*,
not exact magnitude).

**Effort estimate (swarm consensus):** 4–8 h for the EVM coins + BTC/SOL via
forked dashboards; up to ~20 h if building BTC/SOL attribution carefully and
validating all 10. Plus ~2 h/quarter upkeep.

**Wire-up note (repo Wire-Up Rule):** the H-018 integration module must have a
production caller — wire the Dune fetch into the H-018 pick/score path, or label
the PR opt-in with a `## Wiring Plan`.

---

## 3. Honest free-vs-paid verdict

**No free source truly replaces CryptoQuant.** The unanimous finding across
DeepSeek (×2), xAI/Grok, Groq, Kilo, and the standalone Grok consult:

- Dune free tier is the **only** path that yields genuine exchange-*attributed*
  per-coin net-flow at zero cost — but it costs SQL effort, has incomplete labels
  (worst for non-EVM XRP/ADA/DOGE/LTC), and needs maintenance.
- Every other "free tier" either gives the wrong metric (DefiLlama balances,
  Coinglass order-flow, Whale Alert big-txns), has no free API (Glassnode,
  CryptoQuant flow endpoints), is too rate-limited (Santiment 1k calls/mo +
  30-day lag, BGeometrics 8–15 req/day, Arkham), or is trial-only (Nansen).

**Cheapest paid fallback (recommended for production):**
- **CryptoQuant Advanced ≈ $29/mo** — all assets, full history, daily resolution,
  ~100 req/day. Covers all 10 majors with maintained attribution and zero
  maintenance. *(Note: full programmatic token-level API may require the
  Professional ≈ $99/mo tier — confirm the exact endpoint scope of the $29 tier
  against `cryptoquant.com/pricing` before subscribing, since the $29 plan's API
  scope was the one fact swarm engines disagreed on.)*
- This is **$348–$1,188/yr** — negligible against a strategy trading meaningful
  notional, and it removes the look-ahead and label-drift risks of a hand-rolled
  Dune pipeline.

**Recommended decision rule:**
1. **Backtest / research H-018 on the free Dune `cex.flows` pipeline** (EVM coins
   first, BTC/SOL via forked dashboards). If H-018 shows no edge here, you've
   spent $0 to learn that — stop.
2. **If the backtest shows promising edge**, subscribe to CryptoQuant Advanced
   (~$29/mo) for the live signal — clean attribution, all 10 coins, no
   maintenance — and keep Dune as a free cross-check.

---

## 4. Is the self-built Dune query the viable free path? — Yes, with caveats

**Yes.** It is the only legitimately-free route to exchange-attributed net-flow.
`cex.flows` is pre-built Spellbook (no labeling from scratch for EVM coins);
`cex.addresses` covers BTC/SOL labels. Viable and free for **research and
backtesting**. Caveats: (a) non-EVM coin coverage is patchy — XRP/ADA/DOGE/LTC
labels are thin; (b) labels are community-maintained and not perfectly
retroactive, so old history is slightly thinner; (c) free-tier credits/rate
limits are fine for one daily 10-coin pull but not for high-frequency automation;
(d) requires SQL skill and ~quarterly upkeep. For a low-maintenance production
signal across all 10 coins, paid CryptoQuant remains the better engineering
trade-off.

---

## Appendix — who said what

| Engine / source | Key contribution |
|---|---|
| **Grok (headless consult)** | Most detailed & current: confirmed `cex.flows` = 21 EVM chains, `cex.addresses` = ~29 chains incl. BTC/SOL; Dune free = 2,500 credits/mo; CryptoQuant free = charts only no flow API; Santiment 1k calls/mo + 30-day lag; Glassnode exchange flows = paid T2; DefiLlama = PoR balances not per-coin flow; Coinglass = order-flow not on-chain attribution. Verdict: no truly free 1:1; Dune ~70–85%; pay for production. |
| **DeepSeek (r2, r3)** | Strong "Frankenstein" framing; provided concrete Dune SQL; flagged Coinglass/Glassnode free tiers as BTC/ETH-only; recommended CryptoQuant Community ~$30/mo fallback; "if you value time >$30/hr, just pay." |
| **xAI (r2)** | Source-by-source reality table; stressed BTC attribution is the weak spot on Dune; 1–2 weeks to build a solid query set; "~70–80% of value free, won't get CryptoQuant cleanliness without paying." |
| **Kilo (r2)** | Named `cex.flows` table + 2,500 free credits/mo; CryptoQuant API requires paid tier; recommended Dune+manual or $29/mo CryptoQuant Advanced. |
| **Groq (r1, r3)** | Breadth scan of 17 candidate sources; flagged Dune as the build-it path; weaker on concrete limits. |
| **ollama_local (r1)** | Some figures unreliable (claimed 12-mo Glassnode free flow — contradicted by web verification); used only for breadth. |
| **gemini_api / ofox / pollinations / cerebras** | Returned empty or non-substantive output this run. |
| **Web verification (2026)** | Dune docs: free = 2,500 credits/mo, API included. CryptoQuant: no free API for flow endpoints (Pro/Premium only). Coinglass: no free tier, $29/mo Hobbyist entry. Santiment free: 1k calls/mo, 1 yr history minus last 30 days. Glassnode: exchange netflow is paid T2, no free API. |

**Caveat on swarm reliability:** several engine answers were LLM-knowledge-based
and partly inconsistent (e.g., Glassnode/CryptoQuant free-tier specifics). The
web-verified facts in §1 and the appendix override any conflicting engine claim.
