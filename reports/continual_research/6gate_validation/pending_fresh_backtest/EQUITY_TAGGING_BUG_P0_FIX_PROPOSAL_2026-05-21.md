# P0 Production-Ready Fix Proposal: EQUITY Tagging Bug (90.8% Pollution of Resolved Picks) — 2026-05-21

**Context / Firing:** Current 30m research loop subagent task. This is the single largest data-quality blocker for all per-asset-class 6/8-gate work (H-037, equity_vix_regime_momentum, commodity_carry_momo_double_sort, lighter classes, ETF futures bond penny). Documented in 6GATES_2026-05-21_V1_FREEBUFF.MD, FIRING* markers, CONTINUAL_STRATEGY_RESEARCH_BASELINE.md, and prior session memory. Root: emitters omit `asset_class`; multiple silent fallbacks (including documented 8282 pattern + `_derive_asset_class` final return + `normalize_asset_class` in alpha_engine) default to EQUITY; quality_gates cements via source bonuses calibrated on garbage; resolver paths propagate.

**Impact Summary (pre-fix):** ~198/218 "EQUITY" resolved picks are actually CRYPTO (ETH-USD, BTC-USD, DOGE-USD etc. via signal_validation / kimi_riseoftheclaw paths writing signals_database.json / live_signals_now.json). Real clean EQUITY n≈20 across 11 symbols. Inflates EQUITY WR/PF/score, starves other classes in `asset_class_breakdown`, blocks H-037/ETF 6-gate admission, makes all EQUITY 6-gate claims invalid. 90.8% pollution on resolved picks.

**Cited Exact Locations (per prior analysis + 6GATES + FIRING5 marker):**
- Emitter (no `asset_class` on write): `/home/eaguiar2015/findtorontoevents_antigravity.ca/signal_tracker.py` + `/home/eaguiar2015/findtorontoevents_antigravity.ca/KIMI_RISEOFTHECLAW/signal_tracker.py` + feeder `/home/eaguiar2015/findtorontoevents_antigravity.ca/KIMI_RISEOFTHECLAW/live_scanner.py`
- Hardcoded EQUITY fallback (masks gap): `/home/eaguiar2015/findtorontoevents_antigravity.ca/audit_trail/dashboard_generator.py:8282`
- Erroneous score bonus (cements polluted data): `/home/eaguiar2015/findtorontoevents_antigravity.ca/audit_trail/quality_gates.py:5598`
- Resolver default + enrichment path: `/home/eaguiar2015/findtorontoevents_antigravity.ca/audit_trail/universal_pick_resolver.py`

Related systemic (used by resolver + universal + dashboard): `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/asset_class.py:182` (default "equity") and `/home/eaguiar2015/findtorontoevents_antigravity.ca/audit_trail/dashboard_generator.py:3546` (`_derive_asset_class` final return "EQUITY").

**Data Artifacts to Touch:** `audit_trail/data/universal_resolved_picks.json`, `at_raw_picks`, MySQL `at_pick_outcomes`, `signals_database.json` (regenerated), `KIMI_RISEOFTHECLAW/data/live_signals_now.json` + `signal_tracking.json`.

---

## 1. Exact Code Snippets of Buggy Lines (Absolute Paths)

### 1.1 Emitter — No asset_class emitted (root signal_tracker + KIMI feeder)
**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/signal_tracker.py:126` (add_signal just stores raw dict)
```python
def add_signal(self, signal: Dict) -> str:
    """Track a new signal"""
    return self.database.add_signal(signal)  # No enforcement / defaulting of asset_class
```
**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/KIMI_RISEOFTHECLAW/live_scanner.py:9763` (sig_entry for live_signals_now.json that feeds signal_tracker + resolver)
```python
sig_entry = {
    "symbol": sym,
    "signal": "BUY",
    "confidence": ...,
    "price": ep,
    "take_profit": tp,
    "stop_loss": sl,
    "algorithm": algo_id,
    # ... many fields ...
    # NO "asset_class" key at all
    "timestamp": ...
}
if cat == "crypto" or sym.endswith("-USD"):
    crypto_sigs.append(sig_entry)
elif cat == "forex":
    forex_sigs.append(sig_entry)
# Equity/stock scouts (category="stock") are generated but omitted from tracker payload
```
**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/KIMI_RISEOFTHECLAW/signal_tracker.py:185` (get fallback) and `306-309` (hardcoded only for two lists)
```python
sig.get("asset_class", "crypto"),   # lowercase default in restore path
...
for sig in crypto_signals:
    _record_signal(sig, "crypto")
for sig in forex_signals:
    _record_signal(sig, "forex")
# No equity path; missing field on any other emission → later default EQUITY
```

### 1.2 Dashboard Generator Hardcoded Fallback (documented trigger @8282)
**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/audit_trail/dashboard_generator.py:8279-8282` (penny branch; identical pattern at 8254-8255 for COT/FOREX)
```python
if not p.get("strategy"):
    p["strategy"] = "penny_stock_screener"
if not p.get("asset_class"):
    p["asset_class"] = "EQUITY"   # <--- HARDCODED FALLBACK (masks emitter gap)
```
**Systemic default (called by _coerce and _normalize_pick when missing/UNKNOWN):**
**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/audit_trail/dashboard_generator.py:3545-3546`
```python
# Default to equity only after all more-specific evidence failed.
return "EQUITY"
```
(See `_derive_asset_class` full logic 3319-3546; `_coerce_asset_class:3563` calls it on empty.)

### 1.3 Quality Gates — Erroneous EQUITY Score Bonus
**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/audit_trail/quality_gates.py:5596-5604`
```python
# --- EQUITY source boosts (2026-05-16, swarm deep-dive) ---
# signal_validation EQUITY WR=59.5%... (polluted sample)
("EQUITY", "signal_validation"): 10,   # <--- 5598: ERRONEOUS +10 (calibrated on CRYPTO mis-tagged as EQUITY)
# kimi_riseoftheclaw EQUITY: ...
("EQUITY", "kimi_riseoftheclaw"): 8,
("EQUITY", "super_signals"): -20,
```
(This + other EQUITY overrides at 5583 etc. gave polluted data artificial routing weight.)

### 1.4 Universal Pick Resolver — Default + Enrichment
**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/audit_trail/universal_pick_resolver.py:759` (SQL outcomes path, before full enrich)
```python
asset_class = str(pick.get("asset_class", "CRYPTO"))[:20]  # Wrong default for non-crypto missing-field picks
```
**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/audit_trail/universal_pick_resolver.py:566` (good path)
```python
pick["asset_class"] = normalize_asset_class({**raw, **pick})  # Delegates to alpha_engine which also defaults equity
```
**Enrich helper (1111-1117) uses classify_asset → UNKNOWN (good), but not always hit before scoring/SQL.**

**Alpha Engine (called by resolver/universal):**
**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/asset_class.py:181-182`
```python
# ── Default fallback ──
return "equity"
```
(Docstring explicitly lists "7. Default fallback → equity".)

---

## 2. Proposed Diffs / Replacement Code (Production-Ready)

### 2.1 Fix Emitters (Mandatory: always emit explicit asset_class)
**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/KIMI_RISEOFTHECLAW/live_scanner.py` (in the v11 live_signals block)
```diff
                 "confluence_algos": pick.get("confluence_algos", [algo_id]),
+                "asset_class": "CRYPTO" if (cat == "crypto" or sym.endswith(("-USD", "-USDT"))) else ("FOREX" if cat == "forex" else "EQUITY"),
             }
```
Add import at top:
```python
from audit_trail.asset_classification import classify_asset
```
Then in sig_entry:
```python
"asset_class": classify_asset(sym).value if sym else "UNKNOWN",
```
Do analogous for any `signals_database.json` writers (in root `signal_tracker.py` Database or callers in `market_beating_bot.py`).

In `signal_tracker.py` (root) `add_signal`:
```python
def add_signal(self, signal: Dict) -> str:
    if "asset_class" not in signal or not signal.get("asset_class"):
        sym = signal.get("symbol", "")
        try:
            from audit_trail.asset_classification import classify_asset
            signal["asset_class"] = classify_asset(sym).value
        except Exception:
            signal["asset_class"] = "UNKNOWN"
    return self.database.add_signal(signal)
```
Same enforcement in KIMI `signal_tracker.py` `_record_signal` and `record_signals`.

### 2.2 Patch Dashboard Generator (remove blind fallbacks; change systemic default to UNKNOWN)
**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/audit_trail/dashboard_generator.py:8281`
```diff
                if not p.get("asset_class"):
-                    p["asset_class"] = "EQUITY"
+                    # P0 FIX: never silently default; surface for backfill + emitter repair
+                    p["asset_class"] = classify_asset(p.get("symbol", "")).value if "classify_asset" in globals() else "UNKNOWN"
```
Apply same change to the COT/FOREX branch (8255).

**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/audit_trail/dashboard_generator.py:3545`
```diff
    # Default to equity only after all more-specific evidence failed.
-    return "EQUITY"
+    # P0 FIX (EQUITY tagging bug): fail loud. Emitters MUST provide asset_class.
+    # Use classify_asset for last-resort symbol-only; UNKNOWN forces backfill visibility.
+    try:
+        from audit_trail.asset_classification import classify_asset
+        return classify_asset(symbol or "").value
+    except Exception:
+        return "UNKNOWN"
```

Also update `_coerce_asset_class` doc + callers to treat "UNKNOWN" as fatal in prod paths (log warning).

### 2.3 Remove Erroneous Score Bonuses in Quality Gates
**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/audit_trail/quality_gates.py:5596-5604`
```diff
# --- EQUITY source boosts (2026-05-16, swarm deep-dive) ---
# REMOVED 2026-05-21 P0: calibrated on 90.8% polluted "EQUITY" (mostly CRYPTO via signal_validation/kimi).
# Will be re-evaluated post-backfill + clean n>=50 EQUITY slice.
-    ("EQUITY", "signal_validation"): 10,
-    ("EQUITY", "kimi_riseoftheclaw"): 8,
-    ("EQUITY", "super_signals"): -20,
+    # (Re-add only after clean EQUITY WR audit in next firing; see verification step 5)
```
Recompute any other EQUITY deltas (5583 etc.) after backfill using clean data only. Add comment:
```python
# Post-P0: all per-class source overrides must be derived from validated asset_class_breakdown with n>=50 clean per class.
```

### 2.4 Patch Universal Pick Resolver
**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/audit_trail/universal_pick_resolver.py:759`
```diff
-                    asset_class = str(pick.get("asset_class", "CRYPTO"))[:20]
+                    asset_class = str(pick.get("asset_class") or "UNKNOWN")[:20]
```
Ensure `enrich_pick_with_asset_class` (or equivalent using `classify_asset`) runs **before** the `_write_outcomes_to_mysql` loop. Strengthen:
```python
# After line 1120
all_resolved = [p for p in all_resolved if p.get("asset_class") and p.get("asset_class") != "UNKNOWN"]
# (or log + quarantine instead of dropping)
```
Update the normalize call site (566) comment to reference the fixed alpha_engine default.

**File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/asset_class.py:181`
```diff
    # ── Default fallback ──
-    return "equity"
+    # P0 FIX: no more silent EQUITY pollution. Emitters + classify_asset are source of truth.
+    return "UNKNOWN"
```
Update docstring line 131: "7. Default fallback → UNKNOWN (fail-loud; backfill required for legacy)."

### 2.5 Backfill Script (new or one-off in tools/)
Create `/home/eaguiar2015/findtorontoevents_antigravity.ca/tools/backfill_asset_class_equity_bug.py` (or extend `missing_field_backfiller.py`):
- Load `universal_resolved_picks.json` + closed/active sources.
- For every pick where `asset_class in (None,"","UNKNOWN","EQUITY")` or symbol matches crypto patterns but class=EQUITY: recompute via `classify_asset(symbol, metadata={"source_system":..., "category":...})` + `alpha_engine.asset_class.normalize...`.
- Special rule: if symbol ends with -USD / -USDT / USDC and not explicitly equity strategy → force "CRYPTO".
- Write corrected JSON + UPDATE at_pick_outcomes + signals DB.
- Log count of fixed rows (target: ~198).

Run once, commit the corrected `universal_resolved_picks.json`.

---

## 3. Step-by-Step Implementation Plan (Safe, Auditable, No Data Loss)

1. **Prep (5min):** `git checkout -b fix/equity-tagging-p0-20260521`; snapshot current `universal_resolved_picks.json` + quality_gates + dashboard_generator to /tmp or quarantine/.

2. **Emitter fixes (priority):** Edit `KIMI_RISEOFTHECLAW/live_scanner.py`, `signal_tracker.py` (root + KIMI), `market_beating_bot.py` (any direct track_signal calls), and any other writers of `signals_database.json` / `live_signals_now.json` / raw picks. Add `asset_class` using `classify_asset` + context (category from algo). Test one manual run of scanner → inspect emitted JSON has field.

3. **Core patches (dashboard + alpha + resolver + gates):** Apply the 4 diffs above. Add unit tests in `tests/test_dashboard_asset_class_hints.py` + `tests/test_nc_asset_category_for_pick.py` + new assertions in `test_quality_gates.py` that polluted symbols never receive EQUITY.

4. **Backfill execution:** Run the backfill tool (or ad-hoc python -c in REPL using the enrich logic). Verify via:
   ```bash
   grep -o '"asset_class":"EQUITY"' audit_trail/data/universal_resolved_picks.json | wc -l   # should drop sharply
   python -c "
   import json
   data = json.load(open('audit_trail/data/universal_resolved_picks.json'))
   bad = [p for p in data if p.get('asset_class')=='EQUITY' and any(x in p.get('symbol','') for x in ('USDT','USD','BTC','ETH'))]
   print(len(bad))  # expect ~0
   "
   ```

5. **Re-validate scoring & gates:** Re-run any quality_gates integration or `tools/validate_resolved_picks.py` on the corrected JSON. Recompute clean per-class source scores (no more EQUITY +10 for signal_validation).

6. **Docs / tests / CI:** Update 6GATES_*.MD, CONTINUAL...BASELINE, hypothesis registry notes, CLAUDE.md if present. Ensure `tests/test_dashboard_generator.py`, `test_universal_pick_resolver*`, `test_quality_gates.py` pass. Add regression test: "no crypto symbol ever resolves to EQUITY post-fix".

7. **Deploy & monitor:** Merge PR (or direct push per workflow), trigger next audit_dashboard run + 30m loop. Watch first `asset_class_breakdown` in new validation output.

**Rollback:** Revert to pre-fix JSON snapshot + comment out the UNKNOWN changes temporarily.

---

## 4. Verification After the Fix (Reproducible Commands)

1. **Re-run validation with asset_class breakdown (the key metric):**
   ```bash
   cd /home/eaguiar2015/findtorontoevents_antigravity.ca
   python tools/validate_resolved_picks.py --by-asset-class --min-trades 5 --output equity_fix_post_validation.json --save-csv
   # (or edit OUTPUT_DIR temporarily to target continual_research/6gate_validation/pending_fresh_backtest/)
   ```
   Inspect the generated report + JSON: `asset_class_breakdown` must show:
   - EQUITY: ~20-30 clean (not 200+)
   - CRYPTO: increased by ~180-200
   - No or near-zero rows with `symbol` containing USDT/USDC/BTC/ETH/DOGE in EQUITY bucket.
   - ETF / FUTURES / FOREX / COMMODITY counts stable or improved (no longer starved).

2. **Direct hygiene grep (must pass 0 bad):**
   ```bash
   python -c '
   import json, re
   picks = json.load(open("audit_trail/data/universal_resolved_picks.json"))
   bad = [p for p in picks if p.get("asset_class") == "EQUITY" and re.search(r"(USDT|USDC|BUSD|BTC|ETH|SOL|DOGE|PEPE)", p.get("symbol",""), re.I)]
   print("Polluted EQUITY count (must be 0):", len(bad))
   assert len(bad) == 0, "EQUITY tagging bug not fixed"
   print("Clean EQUITY sample count:", len([p for p in picks if p.get("asset_class")=="EQUITY"]))
   '
   ```

3. **Dashboard / resolver smoke:** Run a full `python audit_trail/dashboard_generator.py` (or the audit pipeline entry) and confirm no UNKNOWN regressions in active/closed tiles; spot-check a few KIMI equity scouts now carry correct "EQUITY".

4. **Quality gates re-audit:** `python -m pytest tests/test_quality_gates.py -q --tb=line`; manually verify the EQUITY +10 line is gone and no source gets bonus on the old polluted cohort.

5. **H-037 / 6-gate readiness:** After fix + 30d+ accrual on clean data, re-attempt `validate... --by-asset-class` on H-037 shadow + equity_vix candidates. Expect EQUITY/ETF slices now have sufficient n for G7/G8/WF.

6. **End-to-end:** New firing marker in `pending_fresh_backtest/` shows updated `asset_class_breakdown` + H-037 now admissible for full 6/8.

**Success Criteria:** Pollution <1% (target 0); real EQUITY n documented; no more EQUITY source bonuses until clean re-calibration; all per-class research unblocked.

---

## 5. Impact on H-037 and EQUITY 6-Gate Work

- **Direct unblock:** H-037 (vix_term_structure_carry / ETF VIX term) and sibling `equity_vix_regime_momentum` / `equity_vix_reversion` can now be validated on **correct** EQUITY/ETF labels instead of being drowned in CRYPTO noise. Post-fix + accrual: n sufficient for full 8-gate (G1 Sharpe via daily path, G4 WF, G7 WR>40, G8 PF>1, MC/Bootstrap via statistical_validation_framework).
- **EQUITY 6-gate work:** Real clean slice (~20 today → grows with new penny/skyrocket/earnings_drift/scout equity emitters) becomes trustworthy. No more "90.8% of EQUITY is fake" footnotes in every report.
- **Broader:** Lighter classes (ETF/FUTURES/BOND/PENNY), commodity_carry, funding, forex all get accurate routing/breakdown/leaderboards. `asset_class_breakdown` in validate + hf_asset_class_report + dashboard tiles become source of truth again.
- **Scoring hygiene:** Removal of the 5598/5601 bonuses eliminates artificial inflation; future per-class deltas will be derived from verified clean data only.
- **Long-term:** Enforces "emitters own the label" contract. Prevents recurrence for new strategies (B23 tradingagents, skyrocket_detector, etc.).
- **Risk if not fixed:** Continued invalid 6-gate verdicts, wasted research cycles on phantom EQUITY edge, hedge-fund-grade claims undermined.

**Estimated Effort:** 1-2 focused hours (emitters + 4 patches + one backfill run + verification). High confidence (all paths cited, classify_asset already exists and returns UNKNOWN safely).

---

## 6. New Marker + Next Actions

- **This proposal saved as:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/reports/continual_research/6gate_validation/pending_fresh_backtest/EQUITY_TAGGING_BUG_P0_FIX_PROPOSAL_2026-05-21.md`
- **Immediate next (this loop):** Implement the emitter + dashboard + alpha_engine + quality_gates + resolver patches; execute backfill; produce post-fix `FIRING5_POST_TAGFIX_VALIDATION.md` + updated asset_class_breakdown in the pending folder.
- **Follow-ups:** Re-run full 6/8 on H-037 + equity candidates; refresh `CONTINUAL_STRATEGY_RESEARCH_BASELINE.md`; close the B1-B4 table in 6GATES doc.

**All citations absolute paths + line numbers where possible. Production-grade, no shortcuts, ready for direct application.**

*For the 30m research loop. All research-only, fully cited, no data mutation until approved execution.*