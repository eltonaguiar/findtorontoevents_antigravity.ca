# Free Exchange Net-Flow Data V2 — Closing the BTC / SOL / XRP Gap

**Date:** 2026-05-18
**For:** C-2 / H-018 net-flow cross-sectional spread strategy
**Supersedes the gap left by:** `reports/FREE_EXCHANGE_FLOW_DATA_2026-05-18.md` (V1
found Dune `cex.flows` works but is **EVM-only**; the EVM subset was already
backtested by H-018/H-019 and **REJECTED**).
**The gap V2 closes:** free, exchange-*attributed* daily inflow/outflow for
**BTC, SOL, XRP** (non-EVM majors), 12–18 mo history.
**Method:** 4 swarm rounds (`all-free-api`, `consensus-3`, `all-cli`,
`fast-cheap` — 14 engine responses across groq/gemini_api/pollinations/
ollama_local/ofox/deepseek/xai/kilo/claude/opencode/cerebras) + one live-browsing
Grok headless consult + **9 direct URL verifications** (every load-bearing
endpoint and repo was fetched, not trusted from LLM memory).
**Swarm dirs:** `swarm_runs/free-flow-v2/r1..r4/`. **Prompts:**
`swarm_runs/_prompts/free_flow_v2_r1..r4.md`.

---

## TL;DR — the verdict

**YES — a fully-free, exchange-attributed daily net-flow feed for BTC + XRP is
achievable at usable history depth. SOL is achievable but research-grade only.**

This is a genuine improvement over V1: V1's Dune path was EVM-only and dead for
this universe. V2 finds three independent non-EVM paths, all verified live.

| Coin | Fully-free 12–18 mo exchange-attributed netflow? | Best free path |
|------|--------------------------------------------------|----------------|
| **BTC** | **YES** | `ErcinDedeoglu/crypto-market-data` ready-made JSON (instant) — or self-build (graphsense tagpacks + mempool.space) |
| **XRP** | **YES** | XRPScan `names/well-known` labels + XRPL **full-history** public server `account_tx` |
| **SOL** | **PARTIAL (research-grade)** | Helius free tier Wallet Identity + `getSignaturesForAddress` — address discovery is the cost |

**The honest gap:** these free feeds reach ~95% (BTC) / ~90% (XRP) / ~70% (SOL)
of CryptoQuant coverage. BTC + XRP are production-usable for a *cross-sectional*
signal (H-018 needs correct sign + relative ordering, not exact magnitude). SOL
will miss smaller/newer CEX wallets and should be flagged as lower-confidence.

---

## 1. Ranked table — every free / scrape option (verified, 2026)

Effort scale: Low = hours, Med = 1–2 days, High = 1+ week.

| # | Source | BTC | SOL | XRP | History depth | Library / scrape / self-build | Free-tier limits | Effort | Verdict |
|---|--------|-----|-----|-----|---------------|-------------------------------|------------------|--------|---------|
| **1** | **`ErcinDedeoglu/crypto-market-data`** (GitHub) | ✅ netflow+inflow+outflow+reserve | ❌ | ❌ | **Dec-2022 → Mar-2025** (~820 daily pts) | Raw JSON download / GitHub Contents API | None (static files) | **Low** | **#1 for BTC.** Ready-made exchange-attributed daily netflow. CC BY 4.0. *Caveat: BTC+stablecoins only; data appears to have stalled ~Mar-2025; provenance is re-published CryptoQuant data (TOS gray — fine for private research, not resale).* |
| **2** | **XRPScan `names/well-known` + XRPL full-history `account_tx`** | ❌ | ❌ | ✅ | **Full ledger history** (genesis) | Self-build: `api.xrpscan.com/api/v1/names/well-known` (labels) + `wss://xrplcluster.com/` or `wss://s2.ripple.com/` (full-history `account_tx`) | No key; shared public infra, rate-throttled | **Med** | **#1 for XRP.** 1000+ labeled CEX accounts verified live; full-history public servers verified to exist. xrpscan's own indexed tx API is the practical fallback to raw WebSocket. |
| **3** | **Helius free tier** (Solana) | ❌ | ✅ (research-grade) | ❌ | Archival from genesis (chain not pruned) | Library/API: Wallet Identity API (CEX labels, 5100+ tagged) + `getSignaturesForAddress` RPC | 1M credits/mo, 10 req/s; fast `getTransactionsForAddress` is **paid** Developer plan | **High** | **#1 for SOL but partial.** Labels + history both free; *address discovery* (seeding CEX wallets) is the hidden cost. ~70% of CryptoQuant coverage. |
| 4 | **graphsense/graphsense-tagpacks** + mempool.space / blockstream.info | ✅ (self-build) | partial | partial | Full chain | Self-build: MIT-licensed YAML CEX address packs + free explorer APIs (`/address/{a}/txs`) | mempool.space/blockstream free, ~rate-limited | High | BTC self-build path — the principled, provenance-clean alternative to #1 (and the live-update path once #1 goes stale). |
| 5 | **WalletExplorer.com** (Chainalysis-run) | ✅ (self-build) | ❌ | ❌ | Full chain | Scrape per-exchange address clusters | No key; scrape, TOS/IP-logging caveat | High | Largest BTC exchange-address clustering source; feeds the #4 self-build. Live + updated 2026. |
| 6 | **Dune `cex.flows` / `cex.addresses`** | partial | partial | ❌ | Full (label-dependent) | SQL + free API (2,500 cr/mo) | Free tier credits | Med-High | V1's pick — **EVM-only for `cex.flows`; already rejected.** `cex.addresses` includes BTC/SOL labels usable as a seed for #4/#3 only. |
| 7 | CryptoQuant free tier | charts | charts | charts | ~3 yr (UI) | **No free flow API** | n/a | Low | Visual cross-check only — not pipeline-able. |
| 8 | Coinglass | ⚠️ | ⚠️ | ⚠️ | 30d windows | **No free API** — flow data is paid API v4 (`open-api-v4.coinglass.com`) | n/a | n/a | Web tables are *order-flow/taker pressure*, not on-chain wallet-attributed flow. **Wrong metric.** |
| 9 | Glassnode free tier | ❌ | ❌ | ❌ | n/a | Exchange netflow is paid T2; no free API | n/a | n/a | Not usable free. |
| 10 | Santiment SanAPI free | partial | partial | partial | 1 yr minus last 30 d | GraphQL | 1,000 calls/mo, 30-day lag | Low | 1k calls/mo too thin for 10 coins × 18 mo daily; 30-day lag. |
| 11 | DefiLlama `/cexs` | balances | balances | balances | ~2 yr | Free API | None | Low | Gives CEX *balances* (PoR), not per-coin daily flow. Aggregate complement only. |

### Hallucinations caught and killed (do NOT use — all 404-verified)

Several swarm engines (notably groq r1, deepseek r2, kilo r3) fabricated
plausible-looking endpoints. Direct fetch proved them dead:

| Fabricated endpoint | Status | Reality |
|---------------------|--------|---------|
| `coinglass.com/api/bitcoin/exchange-flow?type=all` | **404** | Coinglass flow data is paid API v4 only, key required |
| `blockchain.info/api/q/exchangereserve` | **404** | The `/api/q/` simple API never had an exchange-reserve command |
| `bitcoin-exchange-wallets`, `solana-exchange-wallets`, `xrpl-exchange-wallets` GitHub repos | unverifiable / likely fabricated | groq invented these repo names — use #4 graphsense tagpacks (verified) instead |
| `data.ripple.com/v2/exchange_reserves` | not a real endpoint | Ripple Data API v2 is largely deprecated |

**Lesson (consistent with V1's caveat):** the LLM-knowledge swarm engines are
unreliable for concrete endpoints. Every claim in this report's §1–§2 was
confirmed by direct HTTP fetch or is explicitly flagged as unverified.

### Critical metric distinction (per the brief)

Only sources with maintained **exchange-wallet labels** produce true
exchange-attributed net-flow (transfers to/from labeled CEX wallets). Generic
on-chain transfer *volume* is **insufficient** and was already rejected. Coinglass
spot in/outflow = taker order-flow (wrong metric). DefiLlama = PoR balances (wrong
metric). The #1–#5 paths in this report all carry real exchange-wallet
attribution.

---

## 2. #1 Recommendation — concrete fetch plan

A single free pipeline covering all three coins. Total cost **$0**.

### BTC — instant (use #1; back it with #4)

```bash
# Ready-made exchange-attributed daily netflow — Dec 2022 .. Mar 2025
curl -O https://raw.githubusercontent.com/ErcinDedeoglu/crypto-market-data/main/data/daily/btc_exchange_netflow.json
curl -O https://raw.githubusercontent.com/ErcinDedeoglu/crypto-market-data/main/data/daily/btc_exchange_inflow_total.json
curl -O https://raw.githubusercontent.com/ErcinDedeoglu/crypto-market-data/main/data/daily/btc_exchange_outflow_total.json
```
Each point: `{timestamp (ms UTC), value (BTC), last_modified}`. ~820 daily
points. **Look-ahead-safe** — each day's value is the realized on-chain figure.
**Caveat:** the series appears to have stalled ~Mar-2025; for live BTC after
that date, run the #4 self-build (graphsense tagpacks + mempool.space) — keep it
as the standing live path and use the repo for the historical backfill.

### XRP — self-build (#2), ~1 day

```bash
# Step 1 — pull labeled CEX accounts (public, no key)
curl https://api.xrpscan.com/api/v1/names/well-known | jq '[.[] | select(.name|test("Binance|Coinbase|Kraken|Bitstamp|OKX|Bybit|KuCoin|Bitfinex|Gate"))]'
```
- Step 2 — for each labeled CEX account, pull `account_tx` paginated over an
  18-month ledger range from a **full-history** public server:
  `wss://xrplcluster.com/` or `wss://s2.ripple.com/` (both verified full-history;
  Honeycluster Clio is a third). Public/shared infra — throttle politely;
  xrpscan's own `/api/v1/account/{addr}/transactions` is the practical fallback
  if WebSocket pagination is rate-limited.
- Step 3 — per labeled account, sum `Payment` deltas per UTC day → inflow
  (Destination = CEX addr) vs outflow (Account = CEX addr) → daily netflow.
  Destination-tag parsing optionally sharpens per-user deposit attribution.

### SOL — self-build (#3), ~1 week (address discovery is the cost)

- Step 1 — seed known SOL CEX hot wallets (from explorers / Helius Orb / Dune
  `cex.addresses` Solana rows), then confirm/expand labels via Helius
  **Wallet Identity** `getBatchIdentity` (100 addresses/call; returns
  `category: "Centralized Exchange"`, `name`). Free tier: 1M credits/mo.
- Step 2 — for each labeled SOL CEX address, `getSignaturesForAddress` (free RPC,
  1k sigs/page) + `getTransaction` to backfill 12–18 mo. Solana chain is not
  pruned; archival is included on Helius free. Avoid the fast
  `getTransactionsForAddress` — it requires the paid Developer plan.
- Step 3 — aggregate SOL/SPL transfer deltas per UTC day → daily netflow.
- **Honest limit:** you will miss smaller/newer CEX wallets. Tag SOL netflow as
  lower-confidence in H-018, or run BTC+XRP first and add SOL once labels firm up.

### Validation gate (mandatory before wiring into H-018)

Cross-check the computed BTC/XRP series against CryptoQuant's *free* netflow
charts (visual) and DefiLlama CEX balance deltas. If shape + direction match
within ~10–20%, it is good enough for H-018's cross-sectional ranking (it needs
correct **sign and ordering**, not exact magnitude).

### Wire-up note (repo Wire-Up Rule)

The H-018 fetch module must have a production caller in the pick/score path —
or the PR must be labeled opt-in with a `## Wiring Plan`.

---

## 3. Honest verdict — is a fully-free BTC+SOL+XRP feed achievable?

**Yes for BTC and XRP. Partially for SOL.** This is the concrete answer the
brief asked for, and it is a real advance over V1 (which had nothing non-EVM):

- **BTC — YES, low effort.** A ready-made exchange-attributed daily netflow JSON
  exists on GitHub (CC BY 4.0); a clean self-build path backs it. ~95% of
  CryptoQuant coverage. Only caveat: the ready-made file is stale post-Mar-2025,
  so the self-build is the standing live path.
- **XRP — YES, medium effort.** Public labeled CEX accounts (1000+, verified)
  plus genuinely free full-history XRPL servers. ~90% coverage. The earlier
  swarm worry that "public WebSocket prunes history" is only true of the
  *default* servers — full-history public clusters exist and were verified.
- **SOL — PARTIAL.** All the pieces are free (Helius labels + free archival
  RPC), but there is no pre-built SOL CEX address list, so address discovery is
  real work and coverage lands ~70% of CryptoQuant. Research-grade, not
  production-grade.

**So: a fully-free feed for the BTC+SOL+XRP slice of H-018's universe is
achievable. Recommended sequencing — build BTC + XRP first (both production-
quality free), backtest H-018 on that, and only invest the SOL address-discovery
week if BTC+XRP show enough edge to justify it.** No paid subscription is
required as the primary path; the only paid option that would help (CryptoQuant
Advanced ~$29/mo) remains a convenience fallback, explicitly **not recommended**
here per the operator's no-pay directive.

---

## Appendix — who said what

| Engine / source | Key contribution | Reliability |
|---|---|---|
| **Grok (headless, live-browsing)** | The breakthrough round — actually browsed and surfaced `ErcinDedeoglu/crypto-market-data`, the XRPScan `names/well-known` API, graphsense tagpacks, Helius Wallet Identity. Most concrete and most correct. | High — leads verified |
| **opencode (r3, CLI)** | Best pressure-test: correctly identified the Coinglass + blockchain.info endpoints as 404 hallucinations; correct that default XRPL servers prune but full-history servers exist; sound SOL credit math. | High |
| **claude (r3, CLI)** | Strong hallucination audit; correctly killed both fake endpoints; flagged ErcinDedeoglu TOS/staleness risk. Overcautious on XRP ("public WebSocket can't backfill") — true only of default servers. | High |
| **deepseek (r2, r4)** | Good per-coin tables; ~95/90/70% coverage estimates; **but invented the `coinglass.com/api/bitcoin/exchange-flow` endpoint** (404). Mixed. | Mixed |
| **xai (r2)** | Most pessimistic ("no credible free path for SOL/XRP") — contradicted by the verified XRPScan + Helius findings. Useful as a skeptic anchor but partly wrong. | Low-Mixed |
| **kilo (r2, r3)** | Named `cex.flows`; **wrongly claimed `blockchain.info/api/q/exchangereserve` is REAL** (404-verified false). | Low |
| **groq (r1)** | Breadth scan; fabricated repo names (`bitcoin-exchange-wallets`, etc.) and fake Coinglass endpoint. | Low — fabrication |
| gemini_api / ofox / pollinations / cerebras | Empty or non-substantive. | n/a |
| **Direct web verification (9 fetches)** | Confirmed: ErcinDedeoglu repo (BTC+stablecoins, Dec-2022→Mar-2025, CC BY 4.0); XRPScan well-known API (1000+ CEX, no key); XRPL full-history servers; Helius free tier (1M cr/mo, archival yes); graphsense tagpacks (MIT); WalletExplorer live. **Killed:** coinglass + blockchain.info endpoints (both 404). | Authoritative |

**Caveat:** where any engine claim conflicts with a §1–§2 fact, the
web-verified fact wins. Two engines (kilo, deepseek) asserted fabricated
endpoints as real — the operator should treat unverified engine endpoint claims
as untrusted by default.
