# 01_SPECIFICATION — MUTUAL FUNDS

**Asset Class:** MUTUAL FUNDS
**Status:** NOT REGISTERED AS ACTIVE PICK CLASS — VALID ONLY AS PASSIVE CORE ALLOCATION
**sizing_allowed:** false (class id = -1, NOT_BUILT)
**Source:** `alpha_engine/asset_class.py`, `ml_gatekeeper/gatekeeper.py:73`, `alpha_engine/pick_failure_root_cause.py:64-70`, `alpha_engine/mf_screener.py`, `alpha_engine/data/mutual_fund_metadata_sample.json`

---

## 1. Algorithm Specification

### Structural Constraints (Why Mutual Funds Cannot Be Active Picks)

| Constraint | Impact on Active Picking |
|------------|-------------------------|
| **NAV struck once daily after market close** | No intraday price available; next-NAV execution only |
| **No intraday TP/SL execution possible** | Cannot implement take-profit/stop-loss orders |
| **Load fees** (front-end/back-end, typically 1-5.75%) | Round-trip entry/exit costs destroy short-term edge |
| **12b-1 fees** (ongoing distribution fee, typically 0.25-1.00%/yr) | Drag on returns even for no-load funds |
| **Expense ratio** (typically 0.015%-0.74%/yr) | Compounds against high-frequency trading |
| **Frequent-trading limits** | Many funds restrict or penalize frequent trading |
| **Min initial investment** ($0-$3,000+) | Creates minimum position size constraints |
| **Redemption fees / holding-period restrictions** | Some funds charge short-term redemption fees (< 30-90 days) |
| **T+1 settlement** | Cash from sales not available until next business day |

### Why Mutual Funds Cannot Be Active Picks

The active-pick pipeline is built around intraday bars, entry_price/take_profit/stop_loss, and same-bar-or-next-bar resolution. Mutual funds have none of these:
- No intraday price → cannot enter at 10:30 AM and exit at 2:00 PM
- No TP/SL → cannot place take-profit or stop-loss orders
- Next-NAV execution → orders placed during the day fill at the next calculated NAV (typically evening close), not current price
- Load/12b-1 costs → pure drag on any short-term strategy

**Sources:**
- `multi_asset/portfolio_defs.py:713-716`: "Mutual funds settle T+1 and can only be traded at NAV close. No intraday execution. Short selling not permitted."
- `alpha_engine/pick_failure_root_cause.py:64-70`: "Not a TP/SL pick. Daily NAV only."
- `alpha_engine/mf_screener.py:6-8`: "NOT an active pick system — mutual funds are structurally incompatible with intraday TP/SL picking (daily NAV only)."

---

## 2. Mutual Fund Metadata (Actual Data from Repo)

**File:** `alpha_engine/data/mutual_fund_metadata_sample.json` (8 funds, NOT the claimed 38)

| Symbol | Name | Type | ER | Load | 12b-1 | Min Initial | AUM | Turnover | Track Record |
|--------|------|------|-----|------|-------|-------------|-----|----------|--------------|
| VFIAX | Vanguard 500 Index Admiral | Index | 0.05% | 0 | 0 | $3,000 | $500B | 3% | 25y |
| VTSAX | Vanguard Total Stock Mkt Admiral | Index | 0.04% | 0 | 0 | $3,000 | $1.4T | 3% | 25y |
| FXAIX | Fidelity 500 Index Premium | Index | 0.015% | 0 | 0 | $0 | $400B | 3% | 25y |
| SWTSX | Schwab Total Stock Mkt Index | Index | 0.03% | 0 | 0 | $0 | $180B | 4% | 25y |
| VBTLX | Vanguard Total Bond Mkt Admiral | Index | 0.05% | 0 | 0 | $3,000 | $300B | 35% | 20y |
| VWELX | Vanguard Wellington | Active | 0.25% | 0 | 0 | $3,000 | $100B | 15% | 80y |
| VGSLX | Vanguard Real Estate Index Admiral | Index | 0.12% | 0 | 0 | $3,000 | $50B | 10% | 25y |
| VTIAX | Vanguard Total Intl Stock Admiral | Index | 0.11% | 0 | 0 | $3,000 | $400B | 8% | 25y |

**ER range:** 0.015% (FXAIX) to 0.25% (VWELX active)
**AUM range:** $50B (VGSLX) to $1.4T (VTSAX)
**Load fees:** All 0 (no-load)
**12b-1 fees:** All 0
**Min initial:** $0 (FXAIX, SWTSX) or $3,000 (others)
**Turnover:** 3% to 35%
**Track record:** 20-80 years

---

## 3. Hard Gates for Mutual Fund Passive Allocation

**File:** `alpha_engine/mf_screener.py` (lines 31-42)

| Criterion | Threshold | Purpose |
|-----------|-----------|---------|
| Expense ratio (index) | ≤ 0.09% | Minimize cost drag |
| Expense ratio (active) | ≤ 0.20% | Minimize cost drag |
| Load fee | None | No entry/exit penalty |
| 12b-1 fee | None | No ongoing distribution cost |
| Min initial investment | ≤ $1,000 | Accessibility |
| AUM | ≥ $1B | Institutional scale/liquidity |
| Turnover ratio | ≤ 20% | Low trading cost |
| Tracking error | ≤ 0.25% vs benchmark | Close benchmark tracking |
| Track record | ≥ 10 years | Multi-market-cycle evidence |
| NAV freshness | ≤ 24h | Current pricing |

**File:** `alpha_engine/risk_qa_validator.py:244-259` (`validate_mutual_fund`)
- Same hard gates with min_initial ≤ $1,000 (stricter than screener's $3,000)

### Screening Result (from `alpha_engine/data/mf_screening_results.json`)

| Total Funds | Passed | Failed | Passing Funds |
|-------------|--------|--------|---------------|
| 8 | 2 | 6 | FXAIX, SWTSX |

**Funds that failed:**
- VFIAX, VTSAX: failed `min_initial` ($3,000 > $1,000 gate in validator)
- VBTLX: failed `min_initial` + `turnover` (35% > 20%)
- VWELX: failed `expense_ratio` (0.25% > 0.20% active), `min_initial`, `tracking_error` (3% > 0.25%)
- VGSLX: failed `expense_ratio` (0.12% > 0.09% index), `min_initial`
- VTIAX: failed `expense_ratio` (0.11% > 0.09% index), `min_initial`

**Passing funds (eligible for passive core allocation only):** FXAIX (0.015% ER, $0 min), SWTSX (0.03% ER, $0 min)

---

## 4. Walk-Forward Backtest Results

**None exist.** `audit_dashboard/data/mf_traits_walkforward_results.json` does not exist. No walk-forward backtest results for mutual funds anywhere in the repo. n=0 walk-forward windows, n=0 funds with backtest results.

`final_v3/quant-audit-2026-11-14/04_asset_class_fixes/ASSET_CLASS_FIXES.md` (line 21, Class Verdict Table):
| MUTUAL_FUND | — | — | — | NOT_BUILT | Add infra; low-fee subset focus |
No n, no WR, no PF — all dashes.

---

## 5. Are Mutual Funds Emitted as Active Picks?

**No. Confirmed across multiple independent code paths:**

1. **`alpha_engine/pick_failure_root_cause.py:64-70`** — `emit_now: False`, "Never promote as an active pick", `horizon_hours: None`
2. **`alpha_engine/mf_screener.py:6-8`** — Module docstring: "NOT an active pick system — mutual funds are structurally incompatible with intraday TP/SL picking (daily NAV only)."
3. **`ml_gatekeeper/gatekeeper.py:73`** — `ASSET_CLASS_MAP` has no MUTUAL_FUND → resolves to `-1` → ML gate would drop/reject it
4. **`audit_dashboard/data/`** — Grep of all JSON files for `mutual_fund`/`MUTUAL_FUND` found only an old enhancement-plan brainstorm, not a single emitted pick
5. **`audit_dashboard/database_consolidation.py:81-82`** — The `classify_asset()` mutual_fund bucket exists but can never match (no emitter sets `category=mutual_fund`)

**Conclusion: Zero mutual fund picks are emitted as active trades.** The screener validates funds for passive allocation; nothing routes them into `active_picks.json` or any pick emission pipeline.

---

## 6. Final Verdict

| Question | Answer | File Path |
|----------|--------|-----------|
| Is MUTUAL_FUND registered in `asset_class.py`? | **NO** — returns crypto/forex/futures/bond/etf/equity/unknown only; fund tickers fall back to "equity" | `alpha_engine/asset_class.py` (lines 102-120, 260) |
| Is MUTUAL_FUND in gatekeeper `ASSET_CLASS_MAP`? | **NO** — 7 classes (CRYPTO=0…FUTURES=6); MUTUAL_FUND resolves to **-1** (NOT_BUILT) | `ml_gatekeeper/gatekeeper.py:73` |
| Gatekeeper class id for MUTUAL_FUND? | **-1** (via `.get(..., -1)`) | `ml_gatekeeper/gatekeeper.py:146` |
| Mutual fund metadata count (actual file)? | **8 funds** in sample JSON; 38-fund CSV does not exist | `alpha_engine/data/mutual_fund_metadata_sample.json` |
| ER range (actual)? | 0.015% – 0.25% | `alpha_engine/data/mutual_fund_metadata_sample.json` |
| AUM range (actual)? | $50B – $1.4T | `alpha_engine/data/mutual_fund_metadata_sample.json` |
| Funds passing hard gates? | **2 of 8** (FXAIX, SWTSX) | `alpha_engine/data/mf_screening_results.json` |
| Walk-forward backtest results for MF? | **n = 0** — file does not exist | `audit_dashboard/data/mf_traits_walkforward_results.json` (absent) |
| MF picks emitted as active trades? | **Zero** — `emit_now: False`, "Never promote as an active pick" | `alpha_engine/pick_failure_root_cause.py:64-70` |
| MF valid as passive core allocation? | **YES** — low-ER, no-load, no-12b-1 index funds | `alpha_engine/mf_screener.py` |
| MF valid as active prediction picks? | **NO** — daily NAV, no intraday TP/SL possible | `multi_asset/portfolio_defs.py:713-716` |

### Final recommendation (consistent with repo's own stance)

**Mutual funds are VALID as passive core allocation** — e.g., 60% US equity (FXAIX/SWTSX), 20% international (VTIAX), 20% bonds/T-bills (VBTLX), with ER ≤0.09% index / ≤0.20% active, turnover ≤20%, track record ≥10 years, no load, no 12b-1, min initial ≤$3,000 (Admiral shares eligible). Two of the eight sample funds pass (FXAIX at 0.015% ER/$0 min, SWTSX at 0.03% ER/$0 min).

**Mutual funds are NOT valid as active prediction picks** — the daily NAV structure makes intraday TP/SL impossible, load/12b-1 costs destroy short-term edges, and no infrastructure exists to emit them as picks (class id -1, no emitter, no walk-forward results, `emit_now: False`).

**Do not add MUTUAL_FUND to canonical asset classes before a real NAV source and emitter exist** — this was explicitly vetoed in the v1 master plan and v3 peer review (see `COMMON_THEMES.md` Theme 5 and `ASSET_CLASS_FIXES.md` lines 147-148: "Do NOT add stub scanner to create fake coverage").
