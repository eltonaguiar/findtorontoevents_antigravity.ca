# Algorithm Specification — MUTUAL FUNDS

**Worktree:** scratch-hippodraco  
**Asset Class:** MUTUAL FUNDS  
**Status:** BLOCKED — zero coverage; infrastructure does not exist  
**T2 Gate Status:** N/A — not a predicted class (class id −1)

---

## 1. Why BLOCKED

Mutual funds are **not a predicted asset class** in this system. No MF scanner, no MF strategy, class id −1 (dropped by ML gate), no NAV data source, no dashboard tile. The `findmutualfunds2` folder exists but was not verified as empty of production path.

## 2. Structural Blockers (must be resolved before any MF picks)

| Blocker | Detail | Required Action |
|---------|--------|-----------------|
| No class registration | `ASSET_CLASS_MAP` has no `MUTUAL_FUND` entry; class id −1 dropped by ML gate | Register `MUTUAL_FUND` as id 7 in `_CAT_MAP`, `_LOWER_TO_UPPER`, `ASSET_CLASS_MAP` |
| No NAV data source | Mutual fund NAV struck once daily after close; no NAV pipeline | Source NAV data (CSV/JSON feed; yfinance fallback); freshness gate: stale if NAV > 24h (T+1) |
| No scanner/strategy | `alpha_engine/mutual_fund_scanner.py` and `mutual_fund_strategies.py` do not exist | Build scanner + strategy stubs mirroring bond structure |
| No dashboard tile | `"mutual_fund"` not in `_PER_ASSET_CLASSES`, `_CANONICAL`, `_AC_TF_GRID_ASSET_CLASSES` | Add MF dashboard tile |
| ML gate drops MF | `ml_gatekeeper/gatekeeper.py` classifies MF as unknown (-1) | Add `ASSET_CLASS_MAP["MUTUAL_FUND"] = 7` |

**Verified from source:** `gatekeeper.py` ASSET_CLASS_MAP has no MUTUAL_FUND entry (uses `.get(..., -1)` at line 146); `asset_class.py` has no `mutual_fund` in `_CAT_MAP`/`_LOWER_TO_UPPER`.

## 3. Why MF Is NOT an ML Prediction Edge

Mutual funds are structurally unsuited to active prediction:

| Characteristic | Implication |
|----------------|-------------|
| NAV struck once daily after close | No intraday TP/SL; orders fill at next NAV |
| 30-day frequent-trading limits | Day trading/scalping impossible; penalties apply |
| Expense ratios (0.03–1.0%+/yr) | Drag on returns; must be modeled |
| Loads (front-end/back-end) | Transaction costs that kill short-horizon edges |
| No cash-flow beta for active timing | Long-run returns = equity risk premium + bond yield, not alpha |

**Conclusion:** Any MF "pick" is an **allocation decision on a monthly clock**, not a daytrade/swing signal. The highest-probability MF path is **buy-and-hold low-cost index mutual funds** (ER ≤0.20%, high AUM, low turnover) — not ML prediction. Probability as low-cost allocation: HIGH (~85–90% over 10-year horizons). Probability as ML prediction edge: NEAR 0%.

## 4. Hypothetical Specification (for when infrastructure exists)

**Strategy:** `mf-index-core`  
**Universe:** VFIAX, VTSAX, FXAIX, VWINX, VFSTX, PRBLX, PIMIX, VWELX  
**Data:** NAV close-to-close (EOD)  
**Cost model:** Expense ratio + load drag; 5 bps round-trip trading cost  
**Benchmark:** Appropriate index fund (Vanguard 500 Index for VFIAX, etc.)  
**Holding period:** Monthly (NAV cycle)  
**T2 gate:** PF ≥ 1.5 after costs, WR ≥ 50%, MDD ≤ 20%, n ≥ 100  

**Probability of profitability as prediction edge:** NEAR 0%.  
**Probability as low-cost allocation:** HIGH (~85–90% over 10-year horizons).

---

## 5. Do Not

- Do not build MF prediction picks until class registration, NAV data, and scanner exist.
- Do not claim MF performance from placeholder/prototype artifacts.
- Do not use crypto-style intraday TP/SL logic for MF NAV trading.

---
