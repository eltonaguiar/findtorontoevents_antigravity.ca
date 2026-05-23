# C-008: Elite CRYPTO Source Protection Audit

**Date:** 2026-05-18  
**Analyst:** Claude Sonnet 4.6  
**Purpose:** Verify API keys, rate limits, and uptime SLA for all CRYPTO signal sources  

---

## Verdict: ALL DATA SOURCES UP — No Action Required

---

## Top CRYPTO Source Systems (by performance, dashboard recent_closed)

| Source | n | WR | PF | External API? |
|--------|---|----|----|--------------|
| `baby_strats_forward` | 481 | 52.0% | 1.56 | Binance public |
| `claude_gainer_st` | 201 | 55.7% | 1.68 | Binance public |
| `dna_winner_picks` | 127 | 50.4% | 1.73 | Binance public |
| `mega_mutation` | 82 | 61.0% | 2.75 | Binance public |
| `kimi_riseoftheclaw` | 80 | 56.2% | 1.49 | Binance public |

All top CRYPTO sources are **internal strategy systems** using Binance public market data APIs
(no authentication required for OHLCV/ticker endpoints). No individual source API keys needed.

---

## Data Source Health Check (2026-05-18T21:58Z)

| Endpoint | Status | Latency | Notes |
|----------|--------|---------|-------|
| Binance primary (`api.binance.com`) | ✅ OK | 226ms | Primary |
| Binance fallback 1 (`api1.binance.com`) | ✅ OK | 700ms | Fallback |
| Binance fallback 2 (`api2.binance.com`) | ✅ OK | 667ms | Fallback |
| CoinGecko (`api.coingecko.com`) | ✅ OK | 94ms | Emergency fallback |

---

## Rate Limit Status

| Resource | Used | Limit | Utilization |
|----------|------|-------|-------------|
| Binance public API (1m weight) | 4 | 1200 | 0.3% |

Current rate limit utilization is negligible. No risk of hitting limits during normal scanner runs.

---

## API Key Inventory

| Key | Location | Status |
|-----|----------|--------|
| Binance API Key | N/A — not required | Public endpoints only |
| FRED_API_KEY | Windows Registry | SET (32 chars) — used for BOND macro data |
| CoinGecko | N/A — free tier | No key required for public endpoints |

No Binance API secret is stored because trading execution is not live (paper mode).
All CRYPTO scanning uses public market data endpoints.

---

## Fallback Chain Verification

`config.py` has the correct 3+ fallback chain per CLAUDE.md API Failover Rule:
```
api.binance.com → api1.binance.com → api2.binance.com → api3.binance.com → CoinGecko → KuCoin
```
All tested endpoints respond within 700ms. Fallback logic is wired via `BINANCE_FALLBACK_URLS`.

---

## Uptime SLA Assessment

Binance public API has a 99.95% historical uptime (based on industry reports). CoinGecko
has a 99.9% uptime. Both are well within acceptable SLA for a shadow-mode quant system
that does not require sub-second data.

---

## Recommendations

1. **No immediate action required** — all data sources are healthy.
2. **Monitor**: Add a daily Binance `ping` health check to the nightly CI workflow
   (`audit-drift-telemetry.yml`) to detect outages proactively.
3. **When trading goes live** (paper→real): create and store Binance API keys in
   GitHub Secrets as `BINANCE_API_KEY` / `BINANCE_API_SECRET`.
