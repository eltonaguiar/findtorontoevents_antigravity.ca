# PR Scope: H-037 Wiring — ETF VIX Term Structure Carry as Opt-In Research Sidecar (Firing 10)

**Date:** 2026-05-21 (Firing 10 of the 30m continual 6-gate research loop)  
**Subagent Focus:** Prototype the wiring of H-037 (hypothesis_registry.json:416-462)  
**Priority:** P1 (post-hygiene) — highest-conviction un-wired ETF candidate (T2; strong on hygiene/power/G2/G4/G7/G8; needs real accrual for G1). Prepares for immediate wiring + 30-60d shadow/paper once hygiene patch (FIRING7/8/9) is merged.  
**Goal:** Add as opt-in research sidecar (shadow-first, tv-paper-trade compatible) with consistent strategy name `h037_vix_term_structure_carry`, post-`_infer_asset_class` ETF tagging for XL* symbols, explicit `contango`/`backwardation` regime tag, and built-in respect for registry kill rules (10% Kelly sizing note + live WR<52% stop after n=50).

## Located Main Emitter Paths (Audit / Alpha / Paper)
Primary ingestion + normalization for all resolved/audit picks happens here (these are the paths that feed universal_resolved_picks, dashboard JSON, validate_resolved_picks.py --by-asset-class, statistical_validation_framework, edge_stability_harness, and public /audit):
- **audit_trail/dashboard_generator.py** (central): 
  - `JSON_PICK_SOURCES` list (starts ~3589) — registration point for all sidecar JSON emitters (e.g. etf_sector_rotation at 3975, cot_positioning at ~4101, leveraged_etf_decay, bond_scanner, etc.).
  - `_derive_asset_class` (~3319-3546) + `_coerce_asset_class` + legacy fallbacks (8254/8282 hardcoded "FOREX"/"EQUITY").
  - Post-hygiene: will call `_infer_asset_class` (from FIRING7/8 patched refs + FIRING9 backfill script) so XL* → "ETF" cleanly (no CRYPTO pollution).
  - Also handles regime hints via `reason` / extra fields; vix_snapshot logic at ~6027.
- **alpha_engine/** (strategy logic + data emitters):
  - `alpha_engine/commodity_cot_contrarian.py` — canonical OPT-IN RESEARCH SIDECAR example (docstring explicitly says "OPT-IN SIDECAR per Wire-Up Rule (CLAUDE.md)", writes `alpha_engine/data/commodity_cot_contrarian_signals.json`, env DISABLE guard, targets dashboard_generator registration + 14d shadow).
  - `tools/etf_sector_emitter.py` — production emitter template for ETF sidecars (writes `alpha_engine/data/etf_sector_picks.json`, uses yfinance + alpha_engine/etf_strategies, NORMALIZE + schema with strategy/asset_class/reason, env ENABLED_FLAG, --dry-run, Wire-Up Rule note).
  - `alpha_engine/etf_strategies.py`, `alpha_engine/equity_vix_regime_momentum.py` (sibling VIX term logic — contango/backwardation on SPY/QQQ etc.), `alpha_engine/asset_class.py:35` (ETF_SYMBOLS has partial XL*; _infer markers will extend).
  - Other emitters: `alpha_engine/cot_positioning.py`, `tools/new_strategies_emitter.py` (has its own `_infer_asset_class`).
- **audit_trail/** supporting:
  - `recorder.py` (raw pick recording + `_extract_strategy` + derive_asset_class).
  - `quality_gates.py:5598` (prior bonus removal site; will need optional gate entry for new strategy's WR<52% kill).
  - `universal_pick_resolver.py` (post-emit normalization).
- **paper_trading/** (live/paper path):
  - `paper_trading/strategies/h037_vix_carry.py` — already implements `H037VIXCarry(BaseStrategy)` with regime filter (VIX>14 + contango>5%), NormalizedPick emission, CBOE/yf fallback, direction logic for SVXY/UVXY etc. (note: uses vol products; registry prefers XL* sector rotation — can be unified).
  - `paper_trading/strategies/incubator_strategies.py:812` (registry of classes for promotion pipeline), `paper_trading/scanner.py`, `paper_trading/strategy_promotion_pipeline.py`.
  - State: `paper_trading/data/h037_verification_state.json` (ACTIVE/30d forward kill switches — reuse for WR tracking).
- **Call-site examples for sidecar invocation**:
  - `.github/workflows/alpha-engine-etf.yml` (and alpha-engine-*.yml family) — runs etf_sector_emitter.py etc. under push/cron; add gated `H037_VIX_CARRY_EMITTER_ENABLED=1 python tools/h037..._emitter.py`.
  - Manual / CI: `python tools/h037_vix_term_structure_emitter.py [--dry-run]`.
  - Paper path: once registered in incubator, `paper_trading` scanner/promotion will pick it up for tv-paper-trade (tv skills).

These paths ensure emitted picks appear in resolved data with correct `asset_class="ETF"`, `strategy="h037_vix_term_structure_carry"`, and regime tags for harness/filtering.

## Studied H-037 Source Files (Exact)
- **tools/h037_vix_carry.py** (backtest harness, 339 LOC):
  - Core carry logic: `carry = (vix_3m - vix_spot) / vix_spot`; `signal = "LONG" if carry > 0 else "FLAT"` (contango = risk-on for XL* basket).
  - 11 SPDR: `SECTOR_ETFS = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLU", "XLB", "XLRE", "XLY", "XLP", "XLC"]`.
  - Harness: `_walk_forward_eff`, backtest(), WR/PF/eff/admissible, registry stats (n=1185, WR=0.589, PF=1.295, eff=0.75, 3/4 admissible).
  - Regime explicit in records: "contango" implied by carry>0.
  - Ready for live extraction: `_download` + `_align` + signal loop can be reused/minimized for emitter.
- **paper_trading/strategies/h037_vix_carry.py** (live template, 203 LOC):
  - `class H037VIXCarry(BaseStrategy)`: `name = "h037_vix_carry"`, `category="etf"`.
  - `_fetch_vix_term_structure` (CBOE markets.cboe.com + yf fallback), `_passes_regime_filter` (VIX_FLOOR=14, CONTANGO_MIN=0.05).
  - `generate_picks` → `NormalizedPick(..., strategy=self.name, reason= f"... regime={'contango' if ...}", ...)` with TP/SL.
  - Direction: contango → LONG inverse (SVXY); backwardation → LONG long-vol (UVXY/VIXY/VXX).
  - **Note for wiring**: Rename class/strategy to `h037_vix_term_structure_carry` for consistency with registry + task spec; unify XL* vs. vol symbols or keep dual (research XL* rotation primary).
- Both ready for integration (logic + paper template). Registry explicitly calls for "contango/backwardation regime tag at emission for harness".

## Minimal Integration Plan (Opt-In, Hygiene-Compliant, Kill-Rule Aware)
1. **Create emitter** (primary wiring vehicle, modeled 1:1 on `tools/etf_sector_emitter.py` + `commodity_cot_contrarian.py` patterns + carry logic from studied files). Output: `alpha_engine/data/h037_vix_carry_picks.json` (schema: `{ "generated_at": iso, "scanner": "h037_vix_term_structure_carry", "picks": [ {symbol, direction, entry_price, tp, sl, strategy, reason, regime_tag, ... } ] }`).
2. **Register** in `audit_trail/dashboard_generator.py:JSON_PICK_SOURCES` (append tuple; add _FRESHNESS if needed).
3. **Post-_infer**: Emitter emits XL* symbols **without** forcing asset_class (or sets "ETF" as hint); after hygiene merge, `_infer_asset_class` / `_derive` (etf_markers list with all XL*) + `if stripped in _AC_ETF_SYMBOLS` will tag "ETF". Add `regime_tag: "contango"|"backwardation"` (and carry value) in every pick for G4 harness / quality_gates.
4. **Paper unification**: Rename `H037VIXCarry.name` etc. to `h037_vix_term_structure_carry`; register class in `paper_trading/strategies/incubator_strategies.py` registry + promotion (so tv-paper-trade can shadow).
5. **Kill rules (registry)**: In emitter, load `paper_trading/data/h037_verification_state.json` (or simple local jsonl for live WR); if n>=50 and rolling WR < 0.52 → return [] + log "KILLED per H-037 registry (WR<52% after n=50)". Default Kelly note in reason: "sizing: 10% Kelly (contango only when VIX<VIX3M)".
6. **Opt-in guards**: `H037_VIX_CARRY_EMITTER_ENABLED=1` (or =0 to disable); --dry-run; stale data guard (VIX fetch <1d).
7. **Call sites**: Add gated invocation to `.github/workflows/alpha-engine-etf.yml` (or new alpha-engine-h037.yml); also manual in research loop. Paper path via promotion.
8. **Downstream**: Picks flow to resolved → `validate_resolved_picks.py --by-asset-class` (continual_research target) + framework (daily PnL for G1) + edge_stability_harness (regime tag helps splits) → A_passed/ or B_failed marker + registry update.
9. **No breakage**: All behind env flag + shadow (0 impact until manually enabled + 14d watch).

## Files Changed / Created (Minimal)
- **NEW**: `tools/h037_vix_term_structure_emitter.py` (full prototype below; ~150 LOC)
- **MODIFY**: `audit_trail/dashboard_generator.py` (~3 lines: append to JSON_PICK_SOURCES near etf_sector_rotation line ~3975; optional _infer call site if extending legacy paths)
- **MODIFY**: `paper_trading/strategies/h037_vix_carry.py` (rename name/display/strategy to "h037_vix_term_structure_carry" for consistency; optional XL* rotation path)
- **MODIFY**: `paper_trading/strategies/incubator_strategies.py` (add import + registry entry for the class)
- **OPTIONAL/MINOR**: 
  - `alpha_engine/etf_strategies.py` (add `def h037_vix_term_structure_carry(...)` for reuse by emitter)
  - `.github/workflows/alpha-engine-etf.yml` (gated call)
  - `audit_trail/quality_gates.py` (optional WR<52% entry for the strategy name)
  - `reports/hypothesis_registry.json` (update "wiring" field post-merge)
  - `alpha_engine/data/h037_vix_carry_picks.json` (produced artifact)
- **NO CHANGE** to core hygiene paths (relies on post-merge _infer).

## Copy-Paste Ready Code Snippet: Minimal H-037 Emitter (tools/h037_vix_term_structure_emitter.py)
```python
#!/usr/bin/env python3
"""H-037 VIX Term Structure Carry — Opt-In Research Sidecar Emitter (Firing 10 prototype).

Wires the carry logic (tools/h037_vix_carry.py + paper_trading/strategies/h037_vix_carry.py)
as a shadow-only emitter. Consistent name: "h037_vix_term_structure_carry".
Uses post-_infer for XL* → "ETF" (emit without asset_class or as hint).
Adds explicit "regime_tag": "contango" | "backwardation".
Respects registry: 10% Kelly note + WR<52% kill after n>=50 (state in paper_trading/data/h037_verification_state.json).

Run (opt-in):
    H037_VIX_CARRY_EMITTER_ENABLED=1 python tools/h037_vix_term_structure_emitter.py
    H037_VIX_CARRY_EMITTER_ENABLED=1 python tools/h037_vix_term_structure_emitter.py --dry-run

Output: alpha_engine/data/h037_vix_carry_picks.json (ingested by dashboard_generator.py JSON_PICK_SOURCES).
Wire-up: append ("h037_vix_term_structure_carry", "alpha_engine/data/h037_vix_carry_picks.json", None)
         to audit_trail/dashboard_generator.py:JSON_PICK_SOURCES.
After hygiene merge: XL* auto-ETF via _infer_asset_class etf_markers + _AC_ETF_SYMBOLS.

See: hypothesis_registry.json:416-462 (kill rule), FIRING* H037 markers, etf_sector_emitter.py, commodity_cot_contrarian.py.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "alpha_engine" / "data" / "h037_vix_carry_picks.json"
ENABLED_ENV = "H037_VIX_CARRY_EMITTER_ENABLED"
STATE_PATH = ROOT / "paper_trading" / "data" / "h037_verification_state.json"  # reuse for live WR tracking

SECTOR_ETFS = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLU", "XLB", "XLRE", "XLY", "XLP", "XLC"]
VIX_TICKERS = ["^VIX", "^VIX3M"]

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _is_enabled() -> bool:
    val = os.environ.get(ENABLED_ENV, "0").strip().lower()
    return val in ("1", "true", "yes", "on")

def _load_state() -> Dict[str, Any]:
    try:
        if STATE_PATH.exists():
            return json.loads(STATE_PATH.read_text())
    except Exception:
        pass
    return {"status": "ACTIVE", "trades": 0, "wins": 0, "last_kill_check": None}

def _should_kill(state: Dict[str, Any]) -> bool:
    n = state.get("trades", 0)
    if n < 50:
        return False
    wr = (state.get("wins", 0) / n) if n > 0 else 1.0
    return wr < 0.52

def _fetch_latest_vix_and_prices() -> Optional[Dict[str, Any]]:
    """Minimal live version of tools/h037_vix_carry.py _download + carry calc.
    Returns dict with vix, vix3m, carry, regime, prices for XLs (latest close).
    """
    try:
        import yfinance as yf
        tickers = VIX_TICKERS + SECTOR_ETFS
        data = yf.download(tickers, period="5d", progress=False, auto_adjust=True)
        if data.empty:
            return None
        # Flatten if MultiIndex
        if hasattr(data.columns, "get_level_values"):
            try:
                data.columns = data.columns.get_level_values(0)
            except Exception:
                pass
        closes = data["Close"].iloc[-1].to_dict() if "Close" in data else {}
        vix = float(closes.get("^VIX", 0) or 0)
        vix3m = float(closes.get("^VIX3M", 0) or 0)
        if vix <= 0 or vix3m <= 0:
            return None
        carry = (vix3m - vix) / vix
        regime = "contango" if carry > 0 else "backwardation"
        etf_prices = {etf: float(closes.get(etf, 0) or 0) for etf in SECTOR_ETFS if closes.get(etf)}
        return {
            "vix": round(vix, 2),
            "vix3m": round(vix3m, 2),
            "carry": round(carry, 4),
            "regime": regime,
            "etf_prices": etf_prices,
            "ts": _now_iso(),
        }
    except Exception as exc:
        print(f"[h037_emitter] fetch error: {exc}", file=sys.stderr)
        return None

def _build_picks(live: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Emit per-XL* picks on regime (LONG basket proxy on contango per harness).
    Minimal: one pick per symbol for simplicity + harness alignment.
    Sets regime_tag + Kelly note. asset_class omitted → post-_infer handles XL* → ETF.
    """
    picks: List[Dict[str, Any]] = []
    if not live or not live.get("etf_prices"):
        return picks
    regime = live["regime"]
    carry = live["carry"]
    vix = live["vix"]
    reason_base = (f"H-037 VIX term carry: VIX={vix} VIX3M={live['vix3m']} carry={carry:.2%} "
                   f"regime={regime} (10% Kelly when contango per registry)")
    direction = "LONG" if regime == "contango" else "FLAT"  # or SHORT for some rotation; harness was LONG/FLAT

    for sym, price in live["etf_prices"].items():
        if price <= 0:
            continue
        # Simple TP/SL (harness 5d hold style; paper template 4%/3%)
        tp = round(price * (1.04 if direction == "LONG" else 0.96), 2)
        sl = round(price * (0.97 if direction == "LONG" else 1.03), 2)
        pick = {
            "symbol": sym,
            "direction": direction,
            "entry_price": round(price, 2),
            "tp": tp,
            "sl": sl,
            "strategy": "h037_vix_term_structure_carry",
            "strategy_name": "H-037 VIX Term Structure Carry",
            "reason": f"{reason_base}; XL* sector rotation signal",
            "regime_tag": regime,  # explicit for harness / quality_gates / --by-asset-class splits
            "carry": carry,
            "vix": vix,
            "generated_at": live["ts"],
            "source_system": "h037_vix_term_structure_carry_emitter",
            "category": "etf",
            # "asset_class": "ETF",  # omit or set; post-_infer (FIRING7/8/9) will ensure for XL* after hygiene merge
            "confidence": 0.65,  # from harness WR=58.9%
            "timeframe": "5d",
            "meta": {"h037": True, "family": "vix_term_structure_carry"},
        }
        picks.append(pick)
    return picks

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not _is_enabled():
        print(f"[h037_emitter] DISABLED (set {ENABLED_ENV}=1 to enable). Exiting 0.", file=sys.stderr)
        sys.exit(0)

    state = _load_state()
    if _should_kill(state):
        print("[h037_emitter] KILLED per H-037 registry rule (WR<52% after n=50). No picks emitted.", file=sys.stderr)
        if not args.dry_run:
            # optionally write empty or marker
            OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
            OUT_PATH.write_text(json.dumps({"generated_at": _now_iso(), "scanner": "h037_vix_term_structure_carry", "picks": [], "killed": True}, indent=2))
        sys.exit(0)

    live = _fetch_latest_vix_and_prices()
    if not live:
        print("[h037_emitter] No live data. Emitting empty (safe).", file=sys.stderr)
        picks: List[Dict[str, Any]] = []
    else:
        picks = _build_picks(live)

    payload = {
        "generated_at": _now_iso(),
        "scanner": "h037_vix_term_structure_carry",
        "picks": picks,
        "regime": live.get("regime") if live else None,
        "meta": {"h037": True, "n_symbols": len(picks), "source": "tools/h037_vix_carry.py + paper_trading/strategies/h037_vix_carry.py"},
    }

    if args.dry_run:
        print(json.dumps(payload, indent=2))
        print(f"\n[DRY-RUN] Would write {len(picks)} picks to {OUT_PATH}", file=sys.stderr)
        return

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2))
    print(f"[h037_emitter] Wrote {len(picks)} picks (regime={payload.get('regime')}) to {OUT_PATH}", file=sys.stderr)

if __name__ == "__main__":
    main()
```

**Usage after drop-in**:
- `H037_VIX_CARRY_EMITTER_ENABLED=1 python tools/h037_vix_term_structure_emitter.py --dry-run`
- Then register + enable in workflow for shadow accrual.

## Verification Steps (Post-Merge + Wiring)
1. Run emitter (enabled, dry-run) → confirm XL* picks + `regime_tag` + `strategy="h037_vix_term_structure_carry"` + no forced wrong asset_class.
2. `python -m audit_trail.dashboard_generator ...` (or CI) → picks appear under ETF tile with clean tags.
3. `python tools/validate_resolved_picks.py --by-asset-class --min-trades 5` (target continual_research/) → H-037 slice shows n>0, ETF count rises cleanly.
4. Shadow 30-60d via tv-paper-trade (use paper_trading/strategies/h037... after rename) + daily PnL.
5. Full 6/8 re-run (framework + edge_stability_harness on regime splits) → promote or B_failed.
6. Confirm kill rule: manually bump state n=60, wr=0.50 → emitter emits [].

## Rollback / Safety
- Unset env var or delete emitter file + remove 1-line registration → zero picks.
- State kill is conservative (never emits on breach).
- All research-only; no prod sizing until A_passed + registry update to SHADOW_LIVE (10% Kelly).

## Citations (Exact, for PR + Review)
- hypothesis_registry.json:416-462 (full H-037, wiring note, 10% Kelly + WR<52% stop, XL* universe, contango/backwardation).
- tools/h037_vix_carry.py (carry calc, SECTOR_ETFS, backtest harness, wf eff).
- paper_trading/strategies/h037_vix_carry.py (BaseStrategy impl, regime filter, NormalizedPick, reason regime string).
- audit_trail/dashboard_generator.py:3589 (JSON_PICK_SOURCES), 3319 (_derive), 3471 (ETF_SYMBOLS check), 3975 (etf_sector example), 8254/8282 (legacy to replace with _infer), 6027 (vix_snapshot).
- tools/etf_sector_emitter.py (full emitter template + Wire-Up Rule).
- alpha_engine/commodity_cot_contrarian.py:10 (OPT-IN SIDECAR docstring + JSON write pattern).
- alpha_engine/asset_class.py:35 (ETF_SYMBOLS partial), alpha_engine/equity_vix_regime_momentum.py (sibling VIX logic).
- FIRING7_TAGGING_HYGIENE_PR_SCOPE_2026-05-21.md + FIRING8/9_H037* + FIRING7/8/9_DASHBOARD_*_REFERENCE.py + FIRING9_TAGGING_BACKFILL_SCRIPT_2026-05-21.py (exact _infer_asset_class for XL* → ETF post-hygiene).
- paper_trading/data/h037_verification_state.json + reports/continual.../FIRING*H037*.md (state + prior recs for regime tag + sidecar).
- .github/workflows/alpha-engine-etf.yml (call site pattern).
- CONTINUAL_STRATEGY_RESEARCH_BASELINE.md:82-88, updates/2026-05-21-.../index.html (wiring recs), 6GATES_2026-05-21_V1_FREEBUFF.MD.

This PR scope is copy-paste ready for the hygiene-post merge wiring step. Drop the emitter, one-line register, rename for name consistency, gate the call — H-037 becomes shadow-live immediately for accrual + final 6/8 validation on clean ETF data.

**Next after wiring**: 30-60d tv-paper + corrected validate + framework (daily for G1) → A_passed/h037_vix_term_structure_carry_etf_*.md or B_failed + registry update.

(End of FIRING10 H-037 Wiring PR Scope — ready for immediate use post-hygiene.)
