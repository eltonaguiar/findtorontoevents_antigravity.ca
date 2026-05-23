# Next-Session P0 Design Specs (Design-Only)

**Date:** 2026-04-29
**Author:** subagent (claude-opus-4-7 1M)
**Status:** DESIGN ONLY — no code, no PRs, no env-flag activations.
**Inputs:**
- `reports/HFPA_PHASE-5-testing-protocol-2026-04-29.md` (testing protocol constraints)
- `reports/PHASE_3_RANKED_PROPOSALS_2026_04_29.md` (Phase 3 retro grade C)
- `reports/DEFERRED_PHASE_3_RANKED_PROPOSAL_NOTE.md` (deferred-list alignment)
- `reports/action_B_resolver_2026_04_27.md` (Workstream B investigation)
- `reports/resolver_fix_implementation_2026_04_28.md` (already-shipped v2 work)
- `alpha_engine/outcome_resolver.py` (current v2, already at 5bp non-crypto)
- `tools/cftc_cot_fetcher.py` (PR #526 scaffold, default-OFF)
- `audit_trail/quality_gates.py` (`passes_active_gate`, `_is_crypto_bull_regime`)
- `alpha_engine/regime_router.py`, `alpha_engine/regime_filter.py`, `alpha_engine/multi_asset_test_portfolios.py`, `scripts/regime_detector.py` (HMM)

**Phase 5 staggering rule applied:** No two HIGH-risk gates flip default-on in the same week. Item-by-item shadow ≥14d, n≥30 NEW closed picks, Wilson 95% CI lower ≥ baseline.

---

## Reality check vs the dispatch brief

The brief's framing of Item 1 was "5bp threshold proposed; design A/B test." Investigation shows:

- `alpha_engine/outcome_resolver.py:115-125` **already has** `PNL_WIN_THRESHOLD_BY_CLASS` with 5bp non-crypto / 0.1bp crypto (shipped 2026-04-28 in the v2 implementation).
- `alpha_engine/outcome_resolver.py:97` legacy comment was updated; `PNL_WIN_THRESHOLD = PNL_WIN_THRESHOLD_DEFAULT` at `:148` is a back-compat alias only.
- Bar-replay TP/SL detection (replacing live-spot close) is shipped at `:363-459`.
- A dry-run re-resolve script exists at `tools/re_resolve_historical_v2.py`.
- 29 v2 tests pass at `tests/test_outcome_resolver_v2.py`.

The actual gap is therefore **NOT the threshold change** but the **historical A/B replay**:
1. Re-resolve the 1,860 historical non-crypto picks under v2 (still dry-run).
2. Compare v1 metrics (current dashboard payload) vs v2 metrics (re-resolved) per class.
3. Use the comparison to validate or roll back the v2 threshold values.

Item 1 is therefore re-scoped to **"v1 vs v2 A/B replay + apply"** rather than "code the 5bp change." This matches the deferred-note (`reports/DEFERRED_PHASE_3_RANKED_PROPOSAL_NOTE.md` §51) phrasing of "FOREX resolver A/B test (5bp threshold) — Phase 2-C 6/7 panel verdict, queued."

Items 2 and 3 are unchanged from the brief.

---

## Item 1: FOREX/COMMODITY resolver v1-vs-v2 A/B replay

### Scope (re-framed)

The v2 threshold + bar-replay logic is already merged. What's missing: a **paired A/B comparison on historical picks** to validate that v2 actually fixes the 63%/67% noise share (Phase 2-C/2-D finding) without destroying real edge. Then a gated "apply" run that overwrites the historical pick files.

### Files

| Path | Role | Action |
|---|---|---|
| `alpha_engine/outcome_resolver.py:115-149` | `PNL_WIN_THRESHOLD_BY_CLASS` map + helpers | NO CHANGE (already 5bp non-crypto) |
| `alpha_engine/outcome_resolver.py:363-459` | `resolve_single_pick` bar-replay | NO CHANGE |
| `tools/re_resolve_historical_v2.py` | Dry-run re-resolve CLI (already exists per `reports/resolver_fix_implementation_2026_04_28.md` §2) | EXTEND — add `--ab-report` mode that emits paired v1/v2 metrics per class without writing |
| `tests/test_outcome_resolver_v2.py` | 29 existing tests | EXTEND — add 4 A/B-pair regression tests (FOREX 3bp/6bp pair, COMMODITY 3bp/50bp pair, non-jpy retain) |
| `reports/re_resolve_delta_2026_04_28.csv` | Per-pick delta (one row per candidate) | NEW (output of dry-run) |
| `reports/HFPA_resolver_v2_AB_2026_05_*.md` | A/B summary, paired metrics | NEW (output of synthesizer) |

**No env-flag added.** The brief's `RESOLVER_PNL_WIN_THRESHOLD` env-flag is unnecessary — v2 ships per-class thresholds, and the A/B is on historical data, not live.

### Diff sketch (`tools/re_resolve_historical_v2.py` extension, ~30 lines)

```python
# Add subcommand: --ab-report
# Walks all candidate non-crypto picks across:
#   - alpha_engine/data/closed_picks.json
#   - alpha_engine/data/closed_picks_fast.json
#   - copy_trader_intel/data/*_picks.json
#   - genome/data/revival_*_picks.json
# For each pick:
#   v1_label = classify_outcome(pnl_pct)             # legacy 0.1bp threshold
#   v2_label = classify_outcome(pnl_pct, asset_class) # 5bp non-crypto
# Emits paired metrics:
#   - per-class WR (v1 vs v2)
#   - per-class PF (v1 vs v2)
#   - per-class Sharpe (v1 vs v2)
#   - n_flipped (WON->FLAT, WON->LOST, LOST->FLAT, etc.)
#   - non_jpy retention (FOREX subset)
# Writes CSV + Markdown summary. NO source-file mutation.
```

### Test plan

1. `pytest tests/test_outcome_resolver_v2.py -v` — 29 + 4 = 33 tests pass.
2. `python tools/re_resolve_historical_v2.py --ab-report` — emits CSV + summary; runs in <60s on full history (in-memory, no network).
3. Spot-check 10 random FOREX picks in `reports/re_resolve_delta_2026_04_28.csv`: confirm v2 label change matches `|pnl_pct| < 0.05` rule.
4. Spot-check non_jpy FOREX subset retains PF > 5 (Phase 2-C finding floor).

### Acceptance criteria (panel 6/7 ratified)

- v2 FOREX **clean WR** (pure non-flicker n) ≥ 0.466 (Phase 5 floor: baseline 0.496 minus 0.03).
- v2 COMMODITY metals sum_pnl_pct ≥ +$25 (Phase 5 floor).
- **v2 FOREX Sharpe lift ≥ +0.5** vs v1 (panel acceptance).
- **v2 FOREX PF ≥ 1.5** post-replay (panel acceptance).
- **v2 non_jpy FOREX PF > 5** preserved (Phase 2-C subset).
- **n_flipped FOREX ≈ 250** (estimate from `reports/resolver_fix_implementation_2026_04_28.md` §5.2).
- **n_flipped COMMODITY ≈ 170** (same source).
- v2 EQUITY metrics within ±5% of v1 (EQUITY didn't flow through live-spot path; should be near-no-op).

### Rollback triggers

- v2 FOREX PF < 1.2 → revert v2 threshold map back to 0.1bp default (one-line revert at `:115-125`).
- v2 non_jpy FOREX PF < 4 → same revert.
- v2 CRYPTO metrics drift > 1% (regression-pin: crypto path should be unaffected).
- n_flipped EQUITY > 50 (signals unexpected EQUITY pickup of v2 path; investigate before apply).

### Estimated implementation effort

**S** (~3-4 hours):
- 30 LOC extension of `tools/re_resolve_historical_v2.py` (subcommand + paired classification)
- 4 new pytest cases in `tests/test_outcome_resolver_v2.py`
- Run + write `reports/HFPA_resolver_v2_AB_2026_05_*.md` synthesis
- One follow-up PR (data-only) to apply `--apply` if A/B passes

---

## Item 2: CFTC COT live-wire (post-#526 scaffold)

### Scope

PR #526 shipped `tools/cftc_cot_fetcher.py` (default-OFF, env-gated, CLI-only, no production callers). This item wires the `commercial_net_extreme` z-score into the active gate as a **per-class edge multiplier / reject signal** for FOREX/COMMODITY/FUTURES picks when COT extreme aligns with pick direction.

### Files

| Path | Role | Action |
|---|---|---|
| `tools/cftc_cot_fetcher.py` | Fetcher (already exists; default-OFF) | NO CHANGE (just keep its env-flag + run weekly) |
| `data/cftc_cot/<contract>_latest.json` | Per-contract cache (Friday-refreshed) | NO CHANGE schema |
| `data/cftc_cot/calendar.json` | Top-level index, freshness watchdog source | NO CHANGE schema |
| `audit_trail/quality_gates.py` (~`:680-720` near `_crypto_short_gate_block_reason`) | Add `_cot_signal_block_reason(pick)` helper | NEW (sidecar pattern, mirrors `_crypto_short_gate_block_reason`) |
| `audit_trail/quality_gates.py:3884` (FOREX section) + `:3908` (ETF/futures) | Insert `_cot_signal_block_reason` call after symbol checks | NEW call site (~3 lines per class) |
| `tests/test_cftc_cot_fetcher.py` | Existing CFTC fetcher tests | EXTEND — add 6 tests for `_cot_signal_block_reason` (extreme positive z + LONG → ALLOW with bonus, extreme negative z + LONG → BLOCK, missing cache → ALLOW, stale cache > 8d → ALLOW with warning) |
| `.github/workflows/cftc-cot-fetch.yml` | NEW weekly cron | NEW — Friday 21:00 UTC + manual dispatch |
| `.github/workflows/cftc-cot-fetch.yml` includes commit step pushing `data/cftc_cot/*.json` to `main` | NEW | Same workflow |

### Env-flags

| Flag | Default | Effect |
|---|---|---|
| `CFTC_COT_FETCHER_ENABLED` | `0` (existing from #526) | Allows fetcher to network. Flip ON FIRST after weekly cron runs once. |
| `CFTC_COT_GATE_ENABLED` | `0` (NEW) | Master switch for the gate logic in `_cot_signal_block_reason`. |
| `CFTC_COT_GATE_FOREX_ENABLED` | `0` (NEW) | Per-class override (FOREX). |
| `CFTC_COT_GATE_COMMODITY_ENABLED` | `0` (NEW) | Per-class override (COMMODITY). |
| `CFTC_COT_GATE_FUTURES_ENABLED` | `0` (NEW) | Per-class override (FUTURES). |
| `CFTC_COT_EXTREME_Z_THRESHOLD` | `2.0` (matches fetcher constant) | z-score abs threshold for "extreme." |

All default-OFF → no behavior change at merge. Operator flips per-class flags incrementally during shadow.

### Diff sketch (`audit_trail/quality_gates.py` ~25 lines)

```python
# At module top: cache COT signals on first read, stale >8d
_COT_CACHE_DIR = os.path.join(_REPO_ROOT, "data", "cftc_cot")
_COT_SIGNAL_CACHE: Dict[str, Any] = {"loaded_at": 0.0, "by_yf_ticker": {}}
_COT_STALENESS_HARD_LIMIT_HOURS = 192  # 8 days (CFTC publishes weekly)

def _cot_signal_for_symbol(symbol: str) -> Optional[Dict[str, Any]]:
    """Load latest commercial_net_extreme signal for a yf-ticker.
    Returns None if cache missing or > 8d stale."""
    # ... reads data/cftc_cot/<TICKER>_latest.json,
    # ... returns {"z": float, "extreme": bool, "report_date": str} or None

def _cot_signal_block_reason(pick: Dict[str, Any]) -> Optional[str]:
    """Block FOREX/COMMODITY/FUTURES picks whose direction OPPOSES the
    commercial-trader extreme position. Returns block reason or None.
    Default-OFF via CFTC_COT_GATE_ENABLED."""
    if os.environ.get("CFTC_COT_GATE_ENABLED", "0") != "1":
        return None
    asset_class = str(pick.get("asset_class", "") or "").upper()
    if asset_class not in ("FOREX", "COMMODITY", "FUTURES"):
        return None
    per_class_flag = f"CFTC_COT_GATE_{asset_class}_ENABLED"
    if os.environ.get(per_class_flag, "0") != "1":
        return None
    sig = _cot_signal_for_symbol(str(pick.get("symbol", "")))
    if not sig or not sig.get("extreme"):
        return None
    z = sig.get("z")
    direction = str(pick.get("direction") or "").upper()
    # Commercials are usually contrarian. extreme negative z = commercials net SHORT
    # → suggests price will fall → block LONG picks. Opposite for positive z.
    if z is not None and z < -2.0 and direction in ("LONG", "BUY"):
        return f"cot_commercials_extreme_short_z={z:.2f}"
    if z is not None and z > 2.0 and direction in ("SHORT", "SELL"):
        return f"cot_commercials_extreme_long_z={z:.2f}"
    return None
```

Call site in `passes_active_gate` (after JPY-cross block, before strategy blocklist):
```python
_cot_block = _cot_signal_block_reason(pick)
if _cot_block is not None:
    logger.debug("Pick rejected: %s (%s)", _cot_block, symbol)
    return False
```

### GHA workflow sketch (`.github/workflows/cftc-cot-fetch.yml`, ~50 lines)

```yaml
name: CFTC COT Weekly Fetch
on:
  schedule:
    - cron: '0 22 * * 5'   # Friday 22:00 UTC = 5pm ET (CFTC publishes ~3:30pm ET, 30min buffer)
  workflow_dispatch:
jobs:
  fetch:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with: { python-version: '3.11' }
      - name: Fetch CFTC COT
        env:
          CFTC_COT_FETCHER_ENABLED: '1'
        run: python tools/cftc_cot_fetcher.py -v
      - name: Commit cache updates
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add data/cftc_cot/*.json
          git diff --staged --quiet || git commit -m "data: weekly CFTC COT refresh [skip ci]"
          git push
```

### Test plan

1. `pytest tests/test_cftc_cot_fetcher.py -v` — existing tests + 6 new pass.
2. **Bootstrap data:** dispatch the workflow manually once → verify `data/cftc_cot/calendar.json` populated, ≥9 contracts have `commercial_net_z` filled (need ≥10 weekly rows).
3. **Shadow run (4 weeks per Phase 5 universe-PR holdout window):** flip `CFTC_COT_FETCHER_ENABLED=1` (workflow secret) but leave `CFTC_COT_GATE_ENABLED=0`. Log shadow-decisions via dashboard panel: "would have blocked N picks today."
4. After 4 weeks: flip `CFTC_COT_GATE_FOREX_ENABLED=1` first (most-tested class via #517 surgical kill). Hold 14 days, evaluate.
5. Then `CFTC_COT_GATE_COMMODITY_ENABLED=1` (Phase 2-D 6/7 priority). Stagger 14 days.
6. Then `CFTC_COT_GATE_FUTURES_ENABLED=1` last (low n; depends on #526 whitelist active).

### Acceptance criteria

- `cftc_data_freshness_hours_max` ≤ 24 in steady state, ≤192 hard limit (Phase 5 panel: kimi).
- `cot_signal_block_reason` non-null rate < 5% of FOREX/COMMODITY picks (sanity: extreme z=2 events are rare).
- 4-week shadow: positive Sharpe contribution per class on the would-have-blocked subset (compare blocked-pick PnL distribution vs allowed-pick distribution).
- After per-class flip: class WR Wilson 95% lower bound ≥ pre-flip baseline (n≥30 new closed).
- Non_jpy FOREX PF retention > 5 (Phase 2-C floor).

### Rollback triggers

- COT data stale > 192h → fetcher silently no-ops (cache returns None → gate no-ops). Alert via freshness watchdog.
- WR drops > 2pp absolute on flipped class within 14d shadow → flip per-class flag back to 0.
- `cot_signal_block_reason` non-null rate > 25% → likely cache corruption or wrong sign convention; rollback master flag.
- COT data integration errors > 2% (Phase 5 panel: glm-4.6) → rollback.

### Estimated implementation effort

**M** (~6-8 hours):
- 25 LOC in `audit_trail/quality_gates.py` (helper + call site + caching)
- 50 LOC GHA workflow (`.github/workflows/cftc-cot-fetch.yml`)
- 6 new pytest cases in `tests/test_cftc_cot_fetcher.py`
- Bootstrap fetcher run + 4-week shadow log dashboard panel (small HTML/JS in `audit_dashboard/template.html`, ~30 LOC)
- Smoke test the freshness watchdog
- Operator coordination for the 3 staggered per-class flag flips

---

## Item 3: HMM regime detection live wire-up

### Scope

`alpha_engine/regime_router.py` + `alpha_engine/regime_filter.py` + `scripts/regime_detector.py` already exist. `regime_report.json` is updated daily by the `regime-detector.yml` workflow. PR #525 already uses the proxy `is_bull` reading via `audit_trail/quality_gates.py:614 _is_crypto_bull_regime`. Phase 1 9/9 panel verdict: HMM regime should be **PRIMARY stratification per asset class** (not just CRYPTO BULL/non-BULL).

This item lifts the existing CRYPTO-only proxy into a **per-asset-class regime filter sidecar** that gates BULL/BEAR/CHOPPY/RANGING per class.

### Files

| Path | Role | Action |
|---|---|---|
| `alpha_engine/regime_router.py` | Two-layer regime architecture (composite + 2D matrix) | NO CHANGE — read-only consumer |
| `alpha_engine/regime_filter.py` | Per-symbol ADX/Hurst/BB classifier | NO CHANGE — read-only consumer |
| `alpha_engine/data/regime_report.json` | Hourly composite regime artifact | NO CHANGE schema (already has `regime`, `btc_trend`, `adx`, `atr_pct`, `long_confidence`, `short_confidence`) |
| `alpha_engine/risk/regime_filter.py` | NEW sidecar: `passes_regime_filter(pick) -> Optional[str]` | NEW (~120 LOC, per Wire-Up Rule sidecar pattern) |
| `audit_trail/quality_gates.py` (`passes_active_gate`, after `_crypto_short_gate_block_reason` call at `:3820`) | Insert `passes_regime_filter` call gated by `REGIME_FILTER_ENABLED` | NEW call site (~5 lines) |
| `tests/test_regime_filter_sidecar.py` | NEW — per-class block-reason matrix | NEW (~150 LOC, 12 tests) |

**Important:** the existing `_is_crypto_bull_regime` helper at `:614-655` stays. The new sidecar is **additive** and only activates when `REGIME_FILTER_ENABLED=1`. `CRYPTO_SHORT_REGIME_GATE_ENABLED` (already shipped in #525) remains the narrow gate that #525 panel approved; the new sidecar is the broader Phase 1 / Goal #1 deployment.

### Env-flags (all default-OFF; per-class isolation)

| Flag | Default | Effect |
|---|---|---|
| `REGIME_FILTER_ENABLED` | `0` | Master switch for the new sidecar. |
| `REGIME_FILTER_CRYPTO_ENABLED` | `0` | Per-class override (CRYPTO). |
| `REGIME_FILTER_FOREX_ENABLED` | `0` | Per-class override (FOREX). |
| `REGIME_FILTER_COMMODITY_ENABLED` | `0` | Per-class override (COMMODITY). |
| `REGIME_FILTER_EQUITY_ENABLED` | `0` | Per-class override (EQUITY). |
| `REGIME_FILTER_FUTURES_ENABLED` | `0` | Per-class override (FUTURES). |
| `REGIME_FILTER_LOG_ONLY` | `1` | Default to log-only (shadow) mode at first flip; flip to `0` to actually block. |

### Diff sketch (`alpha_engine/risk/regime_filter.py`, ~120 LOC NEW)

```python
"""
Per-asset-class regime filter sidecar.
Wire-Up Rule compliance: imported by audit_trail/quality_gates.passes_active_gate
when REGIME_FILTER_ENABLED=1.

Reads alpha_engine/data/regime_report.json (canonical hourly artifact)
and applies per-class regime → direction-allow rules.
"""
from __future__ import annotations
import json, os, logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)
_REGIME_REPORT_PATH = Path(__file__).resolve().parents[1] / "data" / "regime_report.json"

# Per-class direction-allow matrix (Phase 1 9/9 panel + Hamilton 1989).
# Row: regime; Col: direction; Value: allow?
_ALLOW_MATRIX: Dict[str, Dict[str, Dict[str, bool]]] = {
    "CRYPTO": {
        "BULL":   {"LONG": True,  "SHORT": False},
        "BEAR":   {"LONG": False, "SHORT": True},
        "CHOPPY": {"LONG": True,  "SHORT": True},  # don't block in chop
        "RANGING":{"LONG": True,  "SHORT": True},
    },
    "FOREX":     {  # ditto, but Hamilton: FX has weaker regime persistence
        "BULL":   {"LONG": True,  "SHORT": True},   # don't block FOREX
        "BEAR":   {"LONG": True,  "SHORT": True},
        "CHOPPY": {"LONG": True,  "SHORT": True},
        "RANGING":{"LONG": True,  "SHORT": True},
    },
    "COMMODITY": { ... },  # similar permissive default; activate only after metals retain edge
    "EQUITY":    { ... },
    "FUTURES":   { ... },
}

_REGIME_CACHE = {"mtime": 0.0, "regime": "CHOPPY"}

def _read_current_regime() -> str:
    try:
        st = _REGIME_REPORT_PATH.stat()
    except (OSError, FileNotFoundError):
        return "CHOPPY"  # conservative default
    if st.st_mtime == _REGIME_CACHE.get("mtime"):
        return _REGIME_CACHE["regime"]
    try:
        data = json.loads(_REGIME_REPORT_PATH.read_text(encoding="utf-8"))
        regime = str(data.get("regime", "CHOPPY") or "CHOPPY").upper()
        _REGIME_CACHE.update(mtime=st.st_mtime, regime=regime)
        return regime
    except Exception as e:
        logger.debug(f"regime_report load failed: {e}")
        return "CHOPPY"

def passes_regime_filter(pick: Dict[str, Any]) -> Optional[str]:
    """Return block reason (str) or None to pass through.
    Default-OFF via REGIME_FILTER_ENABLED.
    Honors REGIME_FILTER_LOG_ONLY=1 (default) to log without blocking."""
    if os.environ.get("REGIME_FILTER_ENABLED", "0") != "1":
        return None
    asset_class = str(pick.get("asset_class") or "").upper()
    if not asset_class or asset_class not in _ALLOW_MATRIX:
        return None
    per_class = f"REGIME_FILTER_{asset_class}_ENABLED"
    if os.environ.get(per_class, "0") != "1":
        return None
    regime = _read_current_regime()
    direction = str(pick.get("direction") or pick.get("signal_type") or "").upper()
    if direction in ("BUY",): direction = "LONG"
    if direction in ("SELL",): direction = "SHORT"
    allow = _ALLOW_MATRIX[asset_class].get(regime, {}).get(direction, True)
    if allow:
        return None
    reason = f"regime_filter_block:{asset_class}:{regime}:{direction}"
    # Shadow (log-only) mode: log but don't block
    if os.environ.get("REGIME_FILTER_LOG_ONLY", "1") == "1":
        logger.info("[shadow] would block: %s symbol=%s", reason, pick.get("symbol"))
        return None
    return reason
```

Call site in `passes_active_gate` (after `_crypto_short_gate_block_reason` at `:3823`):
```python
try:
    from alpha_engine.risk.regime_filter import passes_regime_filter
    _regime_block = passes_regime_filter(pick)
    if _regime_block is not None:
        logger.debug("Pick rejected: %s (%s)", _regime_block, symbol)
        return False
except ImportError:
    pass  # sidecar absent → no-op
```

### Test plan

1. `pytest tests/test_regime_filter_sidecar.py -v` — 12 new tests pass (default-off no-op, log-only mode does not block, per-class flags work, per-regime matrix correct, missing regime_report.json → conservative default).
2. `pytest tests/test_quality_gates.py -v` — existing tests pass with new import (regression).
3. **Phase 5 staggered flip:**
   - Week 0: merge with all flags OFF (no-op).
   - Week 1: `REGIME_FILTER_ENABLED=1` + `REGIME_FILTER_CRYPTO_ENABLED=1` + `REGIME_FILTER_LOG_ONLY=1` → shadow log only.
   - Week 3 (14d shadow per Phase 5 default-OFF window): if shadow shows ≥30 would-block decisions per class, flip `REGIME_FILTER_LOG_ONLY=0` for CRYPTO only.
   - Week 5+: stagger per-class enables ≥7d apart per Phase 5 panel rule (CRYPTO → EQUITY → FOREX → COMMODITY → FUTURES).

### Acceptance criteria

- **Phase 1 unanimous:** edge must persist in ≥2 of 3 regimes per class. Validate via `tools/edge_by_asset_class.py` rerun stratified by `regime` field.
- `regime_gate_accuracy` ≥ 0.85 (Phase 5 panel: qwen).
- Per-class WR Wilson 95% CI lower ≥ pre-flip baseline once `LOG_ONLY=0`.
- n≥30 NEW closed picks per class before declaring success (Phase 5 panel: 4-of-6).
- No cross-asset contamination (Phase 5 panel: kimi) → integration test that flipping `REGIME_FILTER_CRYPTO_ENABLED=1` does NOT alter EQUITY/FOREX pick decisions.
- `REGIME_FILTER_LOG_ONLY=1` window ≥ 14d before flipping to `0`.

### Rollback triggers

- Any class WR drops ≥ 2pp absolute within 14d of LOG_ONLY=0 flip → flip per-class flag back to 0.
- `regime_gate_accuracy` < 0.85 → flip master flag back to 0.
- regime_report.json freshness > 24h → emit warning, sidecar continues with cached regime.
- Cross-asset contamination detected (e.g., flipping CRYPTO flag changed EQUITY metrics) → mutual-exclusion violation, hard rollback.
- CRYPTO MDD > 195% baseline +18% within 14d (Phase 5 hard floor) → rollback CRYPTO regime filter immediately.

### Estimated implementation effort

**M** (~6-8 hours):
- 120 LOC new `alpha_engine/risk/regime_filter.py`
- 5 LOC integration into `audit_trail/quality_gates.py`
- 150 LOC test file `tests/test_regime_filter_sidecar.py`
- Operator coordination for 5 staggered per-class flag flips (multi-week)
- Allowance matrix tuning per Phase 1 panel methodology

---

## Recommended dispatch order (per Phase 5 staggering rules)

Phase 5 panel (5/6 unanimous): **never flip 2 high-risk gates default-on the same week.** Phase 3 panel (7/7 unanimous): **quantified-drag fixes ship before broad gates.**

| Order | Item | Risk class | Why this order |
|---|---|---|---|
| **1st** | **Item 1 (resolver A/B replay)** | LOW (data-only, no live behavior change) | Data-quality fix that retroactively re-labels historical picks. Once applied, every downstream metric (WR, PF, Sharpe) becomes trustworthy. Items 2 & 3 acceptance thresholds depend on **clean post-resolver-fix metrics**, so this MUST land before they're evaluated. Phase 3 panel 7/7 ranked this as #1 missed action of last session. |
| **2nd** | **Item 3 (HMM regime sidecar, LOG_ONLY=1 first)** | MED (default-OFF; LOG_ONLY=1 makes shadow mandatory) | Provides the regime context that Item 2 depends on. PR #525 already wires CRYPTO-only proxy; this lifts to per-class. Use 14-day LOG_ONLY shadow before any actual blocking. |
| **3rd** | **Item 2 (CFTC COT live-wire)** | MED (default-OFF + 4-week shadow) | Depends on Item 3 regime context (panel rationale: "block LONG when commercials are extreme short" only makes sense if you know the regime). Also requires bootstrap data accumulation (4+ weeks for n=4 z-score data points beyond the 10-week minimum window). |

**Calendar sketch:**

- **Week 0** (current session): merge Item 1 A/B harness + Item 3 sidecar (default-OFF) + Item 2 GHA workflow + helper (default-OFF).
- **Week 1:** run Item 1 A/B replay; if acceptance passes, run `--apply` and merge re-resolved data PR. Bootstrap Item 2 fetcher (CFTC_COT_FETCHER_ENABLED=1).
- **Week 2:** flip Item 3 `REGIME_FILTER_ENABLED=1` + `CRYPTO_ENABLED=1` + `LOG_ONLY=1` → 14d shadow.
- **Week 4:** flip Item 3 CRYPTO LOG_ONLY=0 if acceptance passes. Flip EQUITY LOG_ONLY=1 (stagger ≥7d).
- **Week 5:** flip Item 2 `CFTC_COT_GATE_ENABLED=1` + `FOREX_ENABLED=1`.
- **Week 6+:** continue staggered per-class enables for Items 2 and 3.

---

## Cross-PR interaction warnings

| Pair | Risk | Mitigation |
|---|---|---|
| **Item 1 ↔ Item 2/3 acceptance** | If Item 1 applied AFTER Item 2/3 flipped, Items 2/3 acceptance metrics break (baseline shifts under them). | **Strict ordering:** Item 1 `--apply` must merge BEFORE Item 2/3 per-class flips. Re-baseline Phase 4 forensic post-Item-1. |
| **Item 2 ↔ Item 3 (FUTURES)** | Both gate FUTURES picks. If both flip on same week, attribution impossible. | **Stagger ≥14d** per Phase 5 panel kimi/deepseek rule. Item 3 FUTURES first (broader), Item 2 FUTURES second (narrower). |
| **Item 3 ↔ #525 (already merged)** | Both read `is_bull` regime. Item 3 expanded matrix could conflict with #525's narrow CRYPTO_SHORT_REGIME_GATE_ENABLED rule. | **Mutual exclusion rule:** if `REGIME_FILTER_CRYPTO_ENABLED=1` AND `CRYPTO_SHORT_REGIME_GATE_ENABLED=1`, log a deprecation warning. Phase 1 panel direction is to fold #525's logic into Item 3 long-term. |
| **Item 3 ↔ #527 (already merged, still default-OFF)** | Both touch CRYPTO sizing/direction. Phase 5 panel: stagger #525↔#527 by ≥7d. | **Re-extend rule:** if Item 3 CRYPTO is flipped while #527 vol-target is also flipped, treat as compound CRYPTO change → MDD circuit at 140% (kimi hard stop) applies to BOTH. |
| **Item 2 ↔ #520 (kill agro/oil COMMODITY)** | #520 already kills oil/agro. Item 2 COMMODITY gate adds COT block on top. Risk: over-restriction → empty COMMODITY emit. | **Monitor n_emit_commodity:** if drops > 50% post-Item-2 flip, rollback Item 2 COMMODITY first (#520 has higher EV per panel). |
| **Item 3 ↔ #515 (trust-tier disable for non-CRYPTO)** | Both gate non-CRYPTO. #515 default-on; Item 3 default-off. Independent for now. | No conflict at default state. Validate independently. |
| **Item 1 ↔ ML retraining (Workstream A)** | If Item 1 applies and re-labels 1,860 picks, any ML model trained pre-Item-1 has stale labels. | **Sequence:** Item 1 `--apply` → wait 7 days for resolver to re-stamp incremental picks → only then trigger ML retrain. Per `reports/action_B_resolver_2026_04_27.md` §9.2. |

---

## Appendix A — Wire-Up Rule compliance per item

Per CLAUDE.md "Wire-Up Rule (integration modules)":

- **Item 1:** No new module — extends existing `tools/re_resolve_historical_v2.py` and adds tests. Production caller already exists (`alpha_engine/outcome_resolver.py` is the canonical path; resolver-cron consumes v2 already). ✅ **Wired**.
- **Item 2:** New helper `_cot_signal_block_reason` is added to `audit_trail/quality_gates.py` and called from `passes_active_gate` (production pick-display path). ✅ **Wired** at site (gated by env-flag for default-off behavior, but the gate IS in the production path).
- **Item 3:** `alpha_engine/risk/regime_filter.py` is a NEW sidecar but imported + called from `audit_trail/quality_gates.passes_active_gate`. Per Wire-Up Rule clause 1 (production pick/score path inclusion). ✅ **Wired** at site.

All three pass the rule's grep test:
```
grep -rln "from alpha_engine\.risk\.regime_filter\|_cot_signal_block_reason" \
  audit_trail/ alpha_engine/ tools/
```
must return at least one production-path file.

---

## Appendix B — File touchlist summary

**Item 1:**
- `tools/re_resolve_historical_v2.py` (extend, ~30 LOC)
- `tests/test_outcome_resolver_v2.py` (extend, ~40 LOC)
- `reports/HFPA_resolver_v2_AB_2026_05_*.md` (new synthesis)
- `reports/re_resolve_delta_2026_04_28.csv` (new artifact)

**Item 2:**
- `audit_trail/quality_gates.py` (add helper + call site, ~25 LOC)
- `.github/workflows/cftc-cot-fetch.yml` (new, ~50 LOC)
- `tests/test_cftc_cot_fetcher.py` (extend, ~80 LOC)
- `data/cftc_cot/*.json` (workflow-managed, no manual edits)

**Item 3:**
- `alpha_engine/risk/regime_filter.py` (new, ~120 LOC)
- `audit_trail/quality_gates.py` (add 5-LOC call site)
- `tests/test_regime_filter_sidecar.py` (new, ~150 LOC)

Total: ~600 LOC across all three items. All under "M" effort per item with shared sequencing constraint.

---

## Appendix C — Sample n→days conversion (Phase 5 panel n≥30 floor)

Per Phase 2 historical baseline (3,500 closed picks Apr-21 to Apr-28, 7 days):

| Class | picks/day approx | Days to reach n=30 |
|---|---|---|
| CRYPTO | ~300 | 1 |
| EQUITY | ~50 | 1 |
| FOREX | ~25 | 2 |
| COMMODITY | ~15 | 2-3 |
| FUTURES | ~3 (whitelisted ZN/ES/NQ only post-#526) | **10-14** |
| ETF | ~10 | 3 |

Item 2 FUTURES per-class flag flip needs **calendar window ≥14d** to satisfy Phase 5 n≥30 floor. Item 3 FUTURES per-class flag has same floor. This is why dispatch order #3 (Item 2) lands AFTER #2 (Item 3) — Item 3 FUTURES will already be live and have generated regime decisions before Item 2 FUTURES gate activates.

---

*Spec authored 2026-04-29. No code changes were made. This is design-only per Phase 5 staggering rule.*
