# Algorithm Specification — COMMODITY / FUTURES

**Worktree:** scratch-hippodraco  
**Asset Class:** COMMODITY / FUTURES  
**Status:** BLOCKED  
**T2 Gate Status:** Not cleared — no real feed; historical PF contaminated

---

## 1. Current Money-Ready Verdict (2026-11-15T00:05)

| Metric | COMMODITY | FUTURES |
|--------|-----------|---------|
| n_resolved | 229 | 52 |
| WR | 40.17% | 42.31% |
| PF | 1.0256 | 1.0936 |
| Verdict | WATCH | INSUFFICIENT_DATA |

---

## 2. Why BLOCKED

COMMODITY generator maps crypto proxies (RNDR→silver, XLM/DOT→oil) — labelled COMMODITY rows may have **no commodity exposure**. FUTURES is "dead" (5.9% WR, −96% PnL, zombie tile; real futures hidden under COMMODITY).

## 3. Blockers (must be resolved before unblocking)

| Blocker | Detail | Required Action |
|---------|--------|-----------------|
| No real commodity feed | Generator uses crypto proxies, not commodity instruments | Fix symbol→instrument mapping; get commodity-appropriate feed |
| Crypto-proxy mapping | RNDR mapped to silver, XLM/DOT mapped to oil | Remove proxy mappings; use actual commodity symbols |
| n too small | COMMODITY n=229, FUTURES n=52; need ≥100 for T2 | Accumulate real data |
| Blocked asset class | FUTURES administratively blocked in `quality_gates.py` | Unblock only with real feed + contract specs + costs |

## 4. Block Mechanism

COMMODITY and FUTURES are in `BLOCKED_ASSET_CLASSES` in `quality_gates.py` (set contains {FOREX, COMMODITY, FUTURES, BOND}).

## 5. Hypothetical Specification (for when unblocked)

**Strategy:** `commodity-cot-trend`  
**Universe:** GC=F (gold), SI=F (silver), CL=F (crude oil), NG=F (natural gas), ZC=F (corn)  
**Cost model:** 15 bps round-trip (commission + slippage in ticks + financing)  
**Benchmark:** Appropriate continuous futures or cash commodity  
**Contract specs required:** Multiplier, tick value, margin, roll schedule  
**T2 gate:** PF ≥ 1.5, WR ≥ 50%, MDD ≤ 20%, n ≥ 100  

**Note:** There is **no COMMODITY-specific MDD override** (MDD ≤ 55%). The `classify()` function applies MDD ≤ 20% for TIER_2 to all classes uniformly.

**Historical reference (use with caution):** `cot_positioning` family DSR=1.0000, WR 86.5%, Sharpe +1.377, n=104 — but `multi_asset_cot` PF 21.33 likely one-symbol (CT=F cotton) concentration artifact.

**Probability of profitability:** LOW — until real feed and mapping are fixed. Blind unblock is vetoed.

---

## 6. Do Not

- Do not blind-unblock FUTURES/COMMODITY by removing blocklists while feeds/mapping/costs are wrong.
- Do not trust COMMODITY PF 3.94 without verifying `multi_asset_cot` PF 21.33 concentration.
- Do not treat crypto proxies as commodity exposure.

---
