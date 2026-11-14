# Mutual Funds Quick Wins — MERGED (Coverage Gap)

**Scope:** Mutual funds (VFINX, VTSAX, VBTLX, VTIAX, VGSLX, FXAIX, FBALX, etc.)
**Merged sources:** My flaxen-hair audit + peer `finpredict-v4` audit + peer `childlike-airport` proposed fixes
**Date:** 2026-11-14

## Consolidated finding — MUTUAL FUNDS: ZERO coverage (CONFIRMED by both audits)

| Evidence | Source |
|---|---|
| `live_picks.db` asset classes present: STOCKS 5, CRYPTO 101, FOREX 4, BOND 2, EQUITY 6, COMMODITY 5, UNKNOWN 6 — **no mutual fund class**, no mutual fund rows | Peer childlike mutual_funds |
| Closed picks (16,771 deduped): **no mutual fund class** anywhere | Peer childlike mutual_funds |
| `alpha_engine/asset_class.py`: no `MUTUAL_FUND_SYMBOLS` frozenset; `asset_class_from_symbol()`/`normalize_asset_class()` return `"unknown"` or fall back to `"equity"` for fund tickers (e.g. `VFIAX`, `VTSAX`, `FXAIX`) | Peer childlike mutual_funds |
| `ml_gatekeeper/gatekeeper.py:73` `ASSET_CLASS_MAP = {"CRYPTO": 0, "FOREX": 1, "EQUITY": 2, "COMMODITY": 3, "ETF": 4, "BOND": 5, "FUTURES": 6}` — **no mutual fund entry**. Any mutual fund pick gets `-1` (unknown class) in feature extraction. | Peer childlike mutual_funds |
| `alpha_engine/` strategy inventory: `bond_*`, `etf_*`, `equity_*`, `forex_*`, `crypto_*`, `commodities_*`, `futures_*` scanners/strategies exist; **no `mutual_fund_*` scanner or strategy** | Peer childlike mutual_funds |
| Dashboard grouping (`audit_trail/dashboard_generator.py:6763` `_PER_ASSET_CLASSES`, `:6128` `_CANONICAL`, `:14201` `_AC_TF_GRID_ASSET_CLASSES`) — **no mutual fund tile/bucket** | Peer childlike mutual_funds |
| None of the 9–10 asset classes tracked (CRYPTO, EQUITY, FOREX, COMMODITY, ETF, BOND, FUTURES, MEMECOIN, PENNY_STOCK, UNKNOWN) is a mutual fund class | Peer audits INDEX.md L137 |

**Impact:** Mutual fund picks (if ever emitted) are misclassified as EQUITY/UNKNOWN, dropped by the ML gate (class id -1), and invisible in per-class dashboards. User explicitly requested mutual funds — this is a gap to close.

## Consolidated quick wins

| # | Quick win | Severity | Effort | Files | Source |
|---|---|---|---|---|---|
| MF-1 | Document gap confirmation (this audit) | MED | LOW | this file | My audit |
| MF-2 | Add `MUTUAL_FUND_SYMBOLS` frozenset to `alpha_engine/asset_class.py` with starter universe (VFIAX, VTSAX, FXAIX, VWINX, VFSTX, PRBLX, PIMIX, VWELX, Vanguard/Fidelity/Schwab share classes) | P0/High | LOW | `alpha_engine/asset_class.py` | Peer childlike mutual_funds §3.1 |
| MF-3 | Register `"mutual_fund"` in `_CAT_MAP` and `"mutual_fund": "MUTUAL_FUND"` in `_LOWER_TO_UPPER` | P0/High | LOW | `alpha_engine/asset_class.py` | Peer childlike mutual_funds §3.1 |
| MF-4 | Add mutual fund handling to `asset_class_from_symbol()` and `normalize_asset_class()` so fund symbols classify as `"mutual_fund"` before falling back to equity | P0/High | LOW | `alpha_engine/asset_class.py` | Peer childlike mutual_funds §3.1 |
| MF-5 | Add `"MUTUAL_FUND": 7` to `ASSET_CLASS_MAP` in `ml_gatekeeper/gatekeeper.py:73` | P0/High | LOW | `ml_gatekeeper/gatekeeper.py` | Peer childlike mutual_funds §3.2 |
| MF-6 | Add `"MUTUAL_FUND"` to `_PER_ASSET_CLASSES` in `audit_trail/dashboard_generator.py:6763` and to `_CANONICAL` / `_AC_TF_GRID_ASSET_CLASSES` so dashboard renders a mutual fund tile | P0/High | LOW | `audit_trail/dashboard_generator.py` | Peer childlike mutual_funds §3.1 |
| MF-7 | Add `is_mutual_fund(pick)` helper mirroring `is_crypto`/`is_non_crypto` | MED | LOW | `alpha_engine/asset_class.py` | Peer childlike mutual_funds §3.1 |
| MF-8 | Add `MUTUAL_FUND_STRATEGY_HINTS` tuple (`"mutual_fund"`, `"fund_"`, `"index_fund"`, `"vanguard"`, `"fidelity"`) and consult in `_strategy_hint_class()` | MED | LOW | `alpha_engine/asset_class.py` | Peer childlike mutual_funds §3.1 |
| MF-9 | Create `alpha_engine/mutual_fund_scanner.py` (mirror `alpha_engine/bond_scanner.py` structure) | MED | MEDIUM | `alpha_engine/mutual_fund_scanner.py` (new) | Peer childlike mutual_funds §3.3 |
| MF-10 | Create `alpha_engine/mutual_fund_strategies.py` stubs (empty signals, yfinance placeholder) | MED | MEDIUM | `alpha_engine/mutual_fund_strategies.py` (new) | Peer childlike mutual_funds §3.3 |
| MF-11 | Wire mutual fund into PnL normalization + freshness gate (avoid the pnl_pct unit bug; NAV-based daily rebalance) | P0/High | LOW-MED | `quick_wins/shared/normalize_pnl_units.py`, `tools/db_freshness_check.py` | My audit |
| MF-12 | Propose data source for mutual fund NAVs (CSV/JSON feed; yfinance fallback) | MED | LOW | documentation | My audit |

## Minimal skeleton — NAV-based mutual fund pick
Proposed file: `multi_asset/mutual_fund_strategies.py` (see my original `quick_wins/05_mutual_funds/MUTUAL_FUNDS_QUICK_WINS.md` for full skeleton code).

## Integration notes (PnL / freshness guard)
Mutual fund NAVs are once-daily at 16:00 ET — do NOT inherit crypto-style `pnl_pct` unit bug or intraday freshness:
- Freshness gate: treat data stale if NAV timestamp > 24h (T+1 settlement), not crypto <1h bar.
- PnL normalization: compute on NAV close-to-close (no intraday wicks); use fixed `%` stop/target in `MF_RISK`, not equity ATR trailing stops.
- Add `"mutual_fund": ("MUTUAL_FUND", ...)` to scanner `_CAT_TO_ASSET_CLASS` and `RISK_PARAMS["mutual_fund"] = (-0.05, 0.08, 21)`.

Minimal: additive changes only — no existing class is re-mapped, no existing picks change class. One new file + ~6 edits to existing config/scanner/dashboard files; no new dependencies beyond yfinance (already a requirement).

Per AGENTS.md: document each implemented fix in `updates/<date>-<description>.md` and commit fix + doc on a clean branch containing only your changes.
