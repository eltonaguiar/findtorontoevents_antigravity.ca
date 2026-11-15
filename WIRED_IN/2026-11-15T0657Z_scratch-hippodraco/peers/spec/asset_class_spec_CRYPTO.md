# Algorithm Specification — CRYPTO

**Worktree:** scratch-hippodraco  
**Asset Class:** CRYPTO  
**Status:** BLOCKED  
**T2 Gate Status:** Not cleared — current verdict NOT_READY

---

## 1. Current Money-Ready Verdict (2026-11-15T00:05)

| Metric | Value |
|--------|-------|
| n_resolved | 3,705 |
| WR | 35.87% |
| PF | 0.9196 |
| Verdict | NOT_READY |

---

## 2. Why BLOCKED

CRYPTO has the highest volume but is dragged down by toxic sources, fill bugs, and stale data. No CRYPTO strategy cleared the T2 gate in any backtest version.

## 3. Blockers (must be resolved before unblocking)

| Blocker | Detail | Required Action |
|---------|--------|-----------------|
| OHLCV history depth | `crypto_ohlcv` holds only ~30 days of 1h bars | Backfill to ≥180 days 1h bars |
| Intrabar truth gap | CRYPTO WR drops 52.3% → 42.9% on intrabar replay; 26.4% of TP_HITs hit SL first | Run `tools/reresolve_intrabar.py --apply` after backfill |
| Toxic sources | CRYPTO sources fail training-PF gate | Exclude banned sources; apply sane-pnl guard (95 bps cap) |
| Multiple testing | ~658 strategies tested; ~33 expected false positives at p=5% | Correct `nb_trials`; DSR ≥ 0.95 |
| Data freshness | Stale prices / frozen quotes in curated displays | Resolver throughput; drain OPEN backlog |

## 4. Block Mechanism (Corrected)

CRYPTO is **NOT** in `BLOCKED_ASSET_CLASSES` in `quality_gates.py` (that set contains {FOREX, COMMODITY, FUTURES, BOND}). CRYPTO is blocked **policy/verdict-based**:
- `money_ready_verdict.json`: verdict = NOT_READY (PF 0.92 < 1.5, WR 35.9% < 50%)
- `ml_gatekeeper/gatekeeper.py`: CRYPTO has its own threshold gating at line 735-744

## 5. Hypothetical Specification (for when unblocked)

**Strategy:** `crypto-mom-lb12-skip1-nl5`  
**Universe:** BTC-USD, ETH-USD, SOL-USD, ADA-USD, DOT-USD, AVAX-USD, LINK-USD  
**Lookback:** 12 months  
**Skip:** 1 month  
**n_long:** 5  
**Cost model:** 30 bps round-trip (exchange fees, taker/maker, funding for perps)  
**Benchmark:** BTC-USD total return  
**T2 gate:** PF ≥ 1.5, WR ≥ 50%, MDD ≤ 20%, n ≥ 100  

**Probability of profitability:** LOW — until OHLCV backfill and intrabar replay are complete.

---

## 6. Do Not

- Do not unblock CRYPTO trading until OHLCV ≥180d 1h backfill completes.
- Do not trust dashboard headline WR/PF (CRYPTO Smart Picks showed 78.9% vs raw DB 39.4% — single-source concentration).
- Do not use AI tournament leaderboard WR (43–89 resolved, wide CIs).

---
