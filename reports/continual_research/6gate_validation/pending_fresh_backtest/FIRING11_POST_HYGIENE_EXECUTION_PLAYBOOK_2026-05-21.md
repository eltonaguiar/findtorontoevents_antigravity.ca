# Firing 11 Post-Hygiene Execution Playbook — Clean Backtest + Wiring for Top Candidates
**Date:** 2026-05-21 (Firing 11 of the 30m continual 6-gate research loop)  
**Focus:** Immediate execution of clean post-tagging-hygiene validation + wiring for the three highest-conviction candidates carried from Firing 9/10:  
- Funding arb family (CRYPTO) — T1 A_passed candidate  
- E-ANON-001 (EQUITY short_term_price_momentum) — strongest hygiene beneficiary  
- H-037 (ETF VIX term structure carry) — T2 wiring + shadow launch candidate  

**Purpose:** Provide copy-paste-ready, exact command sequences that can be executed the instant the Firing 7/8/9/10 tagging hygiene patch set (dashboard_generator.py + emitters + quality_gates + backfill) + FIRING9 backfill are applied and verified. All outputs target `reports/continual_research/6gate_validation/` (or its `pending_fresh_backtest/` subdir) per corrected-path hygiene.

**Status:** Research-only, M-107 compliant, fully cited. No production sizing until 6+/8 gates + edge_stability_harness admissible + registry update.

---

## 1. Prerequisites & One-Time Setup (MUST COMPLETE BEFORE ANY VALIDATION RUN)

These unblock trustworthy asset-class slices and G1 (daily PnL / realistic Sharpe).

### 1.1 Apply the Tagging Hygiene Patch (Minimal Merge)
Use the exact smallest diff that replaces the two hardcoded defaults (`"FOREX"` at CFTC branch, `"EQUITY"` at penny branch) with calls to the production `_infer_asset_class()`.

**Source:** `FIRING10_HYGIENE_MINIMAL_MERGE_DIFF_2026-05-21.md` (lines 13-76) + `FIRING8_DASHBOARD_GENERATOR_PATCHED_REFERENCE_2026-05-21.py` (the reference `_infer` impl) + `FIRING9_TAGGING_BACKFILL_SCRIPT_2026-05-21.py:46-84` (robust version) + `dashboard_generator.py:8254/8282` (exact pollution sites) + `FIRING7_TAGGING_HYGIENE_PR_SCOPE_2026-05-21.md`.

**Steps:**
1. Merge the two `if not p.get("asset_class")` diffs into `audit_trail/dashboard_generator.py`.
2. Insert the full `_infer_asset_class(self, symbol: str) -> str` helper (fail-loud, CRYPTO-first, ETF XL*/SPY/QQQ/TLT markers, FOREX =X, COMMODITY futures, conservative EQUITY fallback, UNKNOWN).
3. Apply analogous guards (recommended) in:
   - `KIMI_RISEOFTHECLAW/signal_tracker.py`
   - `audit_trail/quality_gates.py:5598` (remove erroneous +10 EQUITY bonus)
   - `universal_pick_resolver.py`
4. Verify `_infer` is called for all paths (post-legacy fallbacks).

**Post-merge verification command (pollution analyzer):**
```bash
# Pre (should show ~90.8% pollution)
python reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING10_CURRENT_POLLUTION_ANALYZER_2026-05-21.py \
  --input audit_trail/data/dashboard_data.json   # or universal_resolved_picks.json / closed exports

# After backfill (see below) — expect 0 crypto in EQUITY, XL* → ETF, clean CRYPTO/FOREX/ETF/ COMMODITY counts
```

### 1.2 Run the Firing 9 Tagging Backfill (Historical Reclass)
**Source:** `FIRING9_TAGGING_BACKFILL_SCRIPT_2026-05-21.py` (full docstring + `_infer_asset_class` + `process_picks` + JSONL audit + SQL mode) + `CYCLE_2026-05-21_FIRING9_SUMMARY.md:30` + baseline.

**Exact commands (start dry-run):**
```bash
cd /home/eaguiar2015/findtorontoevents_antigravity.ca

# 1. Dry-run on key artifacts (recommended first)
python reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING9_TAGGING_BACKFILL_SCRIPT_2026-05-21.py \
  --input audit_trail/data/universal_resolved_picks.json \
  --output pending_fresh_backtest/universal_resolved_picks_hygiene_clean_2026-05-21.json \
  --dry-run

python reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING9_TAGGING_BACKFILL_SCRIPT_2026-05-21.py \
  --input audit_trail/data/dashboard_data.json --dry-run

# 2. Apply (writes corrected + full change JSONL audit log)
python reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING9_TAGGING_BACKFILL_SCRIPT_2026-05-21.py \
  --input audit_trail/data/universal_resolved_picks.json \
  --output audit_trail/data/universal_resolved_picks.json \
  --apply

# 3. SQL mode for DB tables (ejaguiar1_* — ejaguiar1_stocks, backtests, etc.)
python reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING9_TAGGING_BACKFILL_SCRIPT_2026-05-21.py \
  --sql-mode --table at_raw_picks --apply   # emits safe UPDATEs; review before exec
```

**Safety:** Script defaults to DRY-RUN, always emits audit JSONL, supports --output for corrected file. Never mutates without --apply.

**Also backfill any closed_picks exports or other JSON sources used by resolver/validate.**

### 1.3 Fix/Extend Validate Script for Research-Loop Slice Support (Remaining Hygiene Item)
**Source:** `tools/validate_resolved_picks.py:59` (hardcoded `OUTPUT_DIR = ROOT / "reports"`), parser at ~318 (only --min-trades, --by-asset-class, --output, --save-csv), Firing summaries (FIRING10_EQUITY_FOREX_EXPANSION_2026-05-21.md:86-92, CYCLE summaries, baseline:109), prereqs mentioning `--output-dir reports/continual_research/6gate_validation/`, `--strategy-filter`, `--save-json`.

Current script lacks the slice flags used in all proposed Firing 9/10 commands. **Add before Firing 11 runs:**

- `--output-dir` (override OUTPUT_DIR, default to `reports/continual_research/6gate_validation/`)
- `--strategy-filter "regex"` (post-load filter on strategy name before grouping)
- `--save-json <path>` (for clean per-family slices, in addition to or instead of full report)

After edit, re-test `--by-asset-class` writes clean reports + slices to target dir.

### 1.4 Extend Statistical Validation Framework + Edge Harness CLI (If Not Present)
**Sources:** `alpha_engine/statistical_validation_framework.py:1159` (minimal --example-run only; real daily_pnl / slice logic at ~557+), `alpha_engine/edge_stability_harness.py:543` (class + `is_admissible`), Firing MD command outlines.

Proposed (add if missing for direct invocation):
```bash
python alpha_engine/statistical_validation_framework.py \
  --input <slice.json> \
  --asset-class CRYPTO \
  --framework full \
  --daily-pnl \
  --slippage-bps 15 \
  --output <report.json>
```
(Or equivalent python -c / import harness run for now.)

`edge_stability_harness.py` supports programmatic `EdgeStabilityHarness().is_admissible(...)` (EFF_MIN=0.30, MIN_STABLE_WINDOWS=3, 14d windows).

### 1.5 Other Standing Prereqs (Carried)
- Daily PnL series (framework --daily-pnl or resolver aggregation; per-trade Sharpe inflates G1 per 6GATES appendix + validate:77 `_sharpe_from_trades`).
- Post-backfill verification: `python tools/validate_resolved_picks.py --by-asset-class --min-trades 10 --output-dir reports/continual_research/6gate_validation/` (expect clean rise in CRYPTO/ETF counts, 0 -USD in EQUITY, ETF XL* tagged correctly).
- Data freshness: yfinance/CBOE/CFTC feeds live; 1h granularity for some FOREX (not in F11 scope).
- M-107: All three candidates pre-registered (E-ANON-001:495-560, H-037:416-462, funding arb family variants in registry + Firing4/9 notes).

**Verification after full hygiene + backfill + script fixes:**
```bash
python tools/validate_resolved_picks.py --by-asset-class --min-trades 5 --output-dir reports/continual_research/6gate_validation/pending_fresh_backtest/
# Manual spot-check: no BTC-USD/ETH-USD/ SOL-USD in EQUITY bucket; XLK/XLF/XLE etc. → ETF; funding symbols clean CRYPTO.
```

---

## 2. Funding Arb Family — Clean CRYPTO Slice Validation + Full Framework (Highest Immediate Priority)

**Candidate:** kimi_funding_arb_relaxed_mut + funding_rate_arb + coinglass_funding_confluence + basis_carry cross-venue family (alpha_engine/funding_rate_arb.py, basis_carry.py, coinglass_strategies/funding_confirmation.py, etc.).

**Why now:** Real CLOSED resolved evidence (+2.5% TP_HIT examples in universal_resolved_picks.json:10715+), partial G7/G8 support, largest CRYPTO power, native hygiene unlock for accurate n. Distinct from killed H-006/012/035. Top A_passed candidate per Firing 9 subagent.

**Sources:** `FIRING9_CRYPTO_SUBAGENT_FINDINGS_2026-05-21.md:35-52` (exact commands), subagent ID 019e49ff-5853-..., `CYCLE_2026-05-21_FIRING9_SUMMARY.md`, `CONTINUAL_STRATEGY_RESEARCH_BASELINE.md:13-18,134-138`, `hypothesis_registry.json` (funding entries ~912+), `6GATES_2026-05-21_V1_FREEBUFF.MD`, `alpha_engine/crypto_strategy_harness.py`, `tools/edge_stability_harness.py:41-43`, `universal_resolved_picks.json:10715+`.

**Exact Execution Sequence (post-hygiene + backfill + verify clean CRYPTO):**

```bash
# 1. Extract clean CRYPTO funding-family slice (post-filter on resolved)
python tools/validate_resolved_picks.py \
  --by-asset-class CRYPTO \
  --min-trades 20 \
  --strategy-filter "kimi_funding|funding_rate_arb|coinglass_funding|funding_arb|basis_carry|perp_funding" \
  --save-json reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING11_CRYPTO_FUNDING_SLICE_2026-05-21.json \
  --output-dir reports/continual_research/6gate_validation/pending_fresh_backtest/

# 2. Full 6/8-gate statistical framework (G1-6 + daily PnL for realistic Sharpe/costs) on the slice
python alpha_engine/statistical_validation_framework.py \
  --input reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING11_CRYPTO_FUNDING_SLICE_2026-05-21.json \
  --asset-class CRYPTO \
  --framework full \
  --daily-pnl \
  --slippage-bps 30 \
  --output reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING11_CRYPTO_FUNDING_6GATE_2026-05-21.json

# 3. Edge stability / admissible check (G4 WF consistency)
python -c "
from alpha_engine.edge_stability_harness import EdgeStabilityHarness
h = EdgeStabilityHarness()
admissible = h.is_admissible(
    'funding_arb_family',
    slice_json='reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING11_CRYPTO_FUNDING_SLICE_2026-05-21.json',
    windows='14d',
    eff_floor=0.30,
    min_stable=3
)
print('Admissible for promotion:', admissible)
" 2>&1 | tee reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING11_CRYPTO_FUNDING_EDGE_ADMISSIBLE_2026-05-21.log

# 4. (Optional) Crypto-specific harness cross-check + cost survival
python alpha_engine/crypto_strategy_harness.py --family funding --input <slice> --costs 0.003 --wf  # if CLI extended; else programmatic
```

**Expected Gate Outcomes (on clean data):**
- G7/G8: Already partially evidenced (real +2.5% CLOSED, WR/PF thresholds).
- G4 (WF via harness): Likely (CRYPTO power + n large post-filter + eff).
- G1 (Sharpe daily + 30bps costs): Now credible (prior per-trade inflation fixed).
- G2/G3/G5/G6: High n enables bootstrap/CI/MC/FDR.
- If 6+/8 + admissible + cost_survival >=0.6 → **A_passed/kimi_funding_arb_family_2026-05-21.md** (format per luxalgo_confluence_2026-05-21.md in A_passed/).

**Next after run:** Update hypothesis_registry (funding entries), baseline, public log (updates/.../index.html Firing 11 section), create marker, promote if pass. Launch H-017 shadow collector in parallel (`python tools/h017_liquidation_cascade.py --json --collect` daily for n>=50).

---

## 3. E-ANON-001 — Clean EQUITY Slice + equity_strategy_harness + Statistical Framework

**Candidate:** E-ANON-001 (short_term_price_momentum / 5d-vs-30d rolling avg return family). Distinct from long-term momentum_factor_12m (equity_strategies.py:73+).

**Why now:** TESTED_PASS in registry (PF=1.2307, WR=0.5379, n=48,616, 2020-2026 S&P mid/large 59 symbols, 5-fold OOS 4/5 folds PF>=1.2, VIX gate tested). Largest EQUITY power + direct hygiene beneficiary (clean EQUITY bucket post-backfill vs. prior ~20 real picks polluted). Sidecar pre-reg ready.

**Sources:** `FIRING10_EQUITY_FOREX_EXPANSION_2026-05-21.md:73-131` (full plan + commands), hypothesis_registry.json:495-560 (exact backtest_result + verdict + VIX gate), `alpha_engine/equity_strategy_harness.py:149+ (MomentumFactorSignal etc.) + 507`, `alpha_engine/equity_strategies.py:73-1292`, `CYCLE_2026-05-21_FIRING10_SUMMARY.md`, baseline, `6GATES_2026-05-21_V1_FREEBUFF.MD:171` (EQUITY power notes), `tools/validate_resolved_picks.py`.

**Exact Execution Sequence (post-clean EQUITY verify):**

```bash
# 1. Extract clean EQUITY E-ANON-001 slice
python tools/validate_resolved_picks.py \
  --by-asset-class EQUITY \
  --min-trades 20 \
  --strategy-filter "short_term|momentum|E-ANON|price_momentum|5d.*30d|e_anon_001" \
  --save-json reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING11_EQUITY_EANON001_SLICE_2026-05-21.json \
  --output-dir reports/continual_research/6gate_validation/pending_fresh_backtest/

# 2. Full 6/8-gate framework (daily PnL critical for G1)
python alpha_engine/statistical_validation_framework.py \
  --input reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING11_EQUITY_EANON001_SLICE_2026-05-21.json \
  --asset-class EQUITY \
  --framework full \
  --daily-pnl \
  --slippage-bps 15 \
  --output reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING11_EQUITY_EANON001_6GATE_2026-05-21.json

# 3. Edge stability admissible (14d windows)
python -c "
from alpha_engine.edge_stability_harness import EdgeStabilityHarness
h = EdgeStabilityHarness()
print(h.is_admissible('E-ANON-001', slice_json='...FIRING11_EQUITY_EANON001_SLICE_2026-05-21.json', windows=14))
" | tee ...FIRING11_EQUITY_EANON001_ADMISSIBLE.log

# 4. Equity-specific harness (MomentumFactorSignal + WF + factors + costs)
python alpha_engine/equity_strategy_harness.py \
  --strategy momentum \
  --universe sp500_mid_large \
  --backtest E-ANON-001 \
  --wf-folds 5 \
  --costs 0.0015 \
  --input reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING11_EQUITY_EANON001_SLICE_2026-05-21.json \
  --output reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING11_EQUITY_EANON001_HARNESS_2026-05-21.json

# 5. Cross-check / repro (baby or anon if needed) + Whites RC
# python baby_strategies_backtest.py --family equity_momentum --filter e_anon   # or equivalent
```

**Gate Mapping (leveraging prior anon stats + hygiene power):**
- G4 (harness WF): Strong (4/5 folds positive).
- G7/G8: Already 53.8% / 1.23 — PASS.
- G1 (daily Sharpe post-slip): Target >=0.5-1.0.
- G2/3/5/6: High n enables.
- If 6+/8 + admissible: **A_passed/e_anon_001_short_term_momentum_equity_2026-05-21.md**; wire to emitters/quality_gates for shadow/paper (tv-paper-trade); update registry + 90-day plans.

**If fails:** B_failed/ with gap analysis (e.g., bear-fold VIX weakness); propose regime fix.

**Wire as opt-in sidecar (if not present):** strategy_name="e_anon_001_short_term_momentum" or "short_term_price_momentum_equity" using equity_strategy_harness.MomentumFactorSignal base. Emit to alpha_engine/data/ for dashboard ingestion.

---

## 4. H-037 Wiring + Shadow Launch + Clean ETF Validation

**Candidate:** H-037 (vix_term_structure_carry / ETF SPDR sector rotation on VIX contango/backwardation). Universe: 11 SPDR XL* (XLK,XLF,XLE,...XLC). Registry kill: 10% Kelly + live WR<52% stop after n=50. Pre-reg M-107 2026-05-19. Ring rec: top free-data diversifier.

**Why now:** Strong post-fix proxy (n=1185, WR58.9%, PF1.295, eff=0.75, 3/4 admissible, G4/G7/G8 clear; hygiene unblocks ETF tag). Highest-conviction un-wired ETF seed. Sibling equity_vix B_failed (power/G1=0.202).

**Sources:** `FIRING10_H037_WIRING_PR_SCOPE_2026-05-21.md:1-296` (full PR scope + copy-paste emitter prototype + verification steps), `FIRING9_H037_POSTFIX_REVALIDATION_SIM_2026-05-21.md`, `FIRING8_H037_POSTFIX_6GATE_SIM_2026-05-21.md`, hypothesis_registry.json:416-462 (exact entry + wiring:"OPT-IN RESEARCH SIDECAR" + kill rule), `tools/h037_vix_carry.py` (backtest harness, SECTOR_ETFS, carry calc), `paper_trading/strategies/h037_vix_carry.py` (H037VIXCarry BaseStrategy + regime filter + NormalizedPick), `paper_trading/data/h037_verification_state.json`, `alpha_engine/etf_strategies.py`, `dashboard_generator.py:3589 (JSON_PICK_SOURCES), 3319 (_derive), 3975 (etf example)`, `CYCLE summaries`, baseline, `6GATES MD`.

### 4.1 One-Time Wiring Steps (Create + Register + Unify)

1. **Create emitter** (paste full prototype from FIRING10_H037_WIRING_PR_SCOPE_2026-05-21.md:75-258 into new file):
   ```bash
   cat > tools/h037_vix_term_structure_emitter.py << 'EOF'
   # [paste the entire documented prototype here — shebang + docstring + _infer-compliant XL* emission + regime_tag + kill-rule state check + H037_VIX_CARRY_EMITTER_ENABLED guard + writes alpha_engine/data/h037_vix_carry_picks.json ]
   EOF
   chmod +x tools/h037_vix_term_structure_emitter.py
   ```

2. **Register in dashboard_generator.py** (near etf_sector_rotation ~3975):
   ```python
   # In JSON_PICK_SOURCES list
   ("h037_vix_term_structure_carry", "alpha_engine/data/h037_vix_carry_picks.json", None),
   ```

3. **Unify paper_trading name** (for tv-paper-trade + promotion consistency):
   - Edit `paper_trading/strategies/h037_vix_carry.py`: rename class/strategy `H037VIXCarry` / `h037_vix_carry` → `h037_vix_term_structure_carry` (and display).
   - Register class in `paper_trading/strategies/incubator_strategies.py`.
   - (Optional) Add to `.github/workflows/alpha-engine-etf.yml` gated call.

4. **Optional:** Add `def h037_vix_term_structure_carry(...)` to `alpha_engine/etf_strategies.py` or `equity_vix_regime_momentum.py` for reuse. Wire quality_gates kill-rule check if desired.

**Dry-run test of emitter (pre-enablement):**
```bash
H037_VIX_CARRY_EMITTER_ENABLED=1 python tools/h037_vix_term_structure_emitter.py --dry-run
# Confirm: XL* picks, regime_tag=contango|backwardation, strategy="h037_vix_term_structure_carry", no forced wrong asset_class, Kelly note in reason.
```

### 4.2 Shadow Launch (Post-Wiring, Opt-In, 30-60d Accrual)

```bash
# Enable + run (manual or cron / .github workflow)
H037_VIX_CARRY_EMITTER_ENABLED=1 python tools/h037_vix_term_structure_emitter.py

# Ingest via dashboard (or CI alpha-engine-etf.yml)
python -m audit_trail.dashboard_generator   # or equivalent full run that hits JSON_PICK_SOURCES

# Verify in resolved / dashboard
python tools/validate_resolved_picks.py --by-asset-class ETF --min-trades 1 --output-dir reports/continual_research/6gate_validation/pending_fresh_backtest/
# Expect H-037 slice n>0, clean "ETF" tags, regime_tag present.

# Paper trading shadow (tv-paper-trade compatible)
# - Use paper_trading/strategies/h037_vix_carry.py (renamed) + scanner/promotion_pipeline
# - Or direct tv skills: switch to SCALPER/TESTER/etc account, load strategy
# - Track in paper_trading/data/h037_verification_state.json (trades/wins for kill rule)
# - Daily PnL accrual required for final G1.
```

**Kill rule test:** Manually bump state n=60, wr=0.50 → emitter emits [] + "KILLED per H-037 registry".

**Registry update post-wiring:** Set wiring field to "WIRED 2026-05-21 (Firing 11), emitter + dashboard + paper sidecar, shadow accruing".

### 4.3 Clean ETF / H-037 Validation (After Shadow Accrual or Immediate Proxy on Clean Tags)

```bash
# 1. Extract clean ETF / H-037 slice (post-wiring + some accrual or on historical proxy)
python tools/validate_resolved_picks.py \
  --by-asset-class ETF \
  --min-trades 5 \
  --strategy-filter "h037_vix_term_structure_carry|H-037|vix_term" \
  --save-json reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING11_ETF_H037_SLICE_2026-05-21.json \
  --output-dir reports/continual_research/6gate_validation/pending_fresh_backtest/

# 2. Full framework + daily PnL (G1 now possible)
python alpha_engine/statistical_validation_framework.py \
  --input ...FIRING11_ETF_H037_SLICE...json \
  --asset-class ETF \
  --framework full \
  --daily-pnl \
  --slippage-bps 5 \
  --output ...FIRING11_ETF_H037_6GATE_2026-05-21.json

# 3. Regime-split edge stability (contango vs backwardation)
python -c "
from alpha_engine.edge_stability_harness import EdgeStabilityHarness
h = EdgeStabilityHarness()
print('Contango admissible:', h.is_admissible(..., regime_tag='contango'))
print('Overall:', h.is_admissible(...))
" 

# 4. Reproduce harness numbers (tools/h037_vix_carry.py or etf harness)
python tools/h037_vix_carry.py --revalidate --input <clean slice or live> --output pending.../FIRING11_H037_REVAL...
```

**Post-Accrual Promotion Path:** If 6+/8 + admissible + respects kill rule + 30-60d shadow positive EV → **A_passed/h037_vix_term_structure_carry_etf_2026-05-21.md** (update registry status to SHADOW_LIVE or ADMITTED, 10% Kelly note). Else B_failed with exact gap (e.g., G1 costs on real daily).

**Rollback:** Unset env var, delete emitter registration line, remove 1-line dashboard registration → zero impact.

---

## 5. Post-Run Consolidation & Promotion Checklist (All Three Candidates)

For each successful run:
1. Create `A_passed/<slug>_2026-05-21.md` (format: luxalgo_confluence example in A_passed/).
2. Update `reports/hypothesis_registry.json` (status, result gates, harness_verdict, hygiene_fix_applied=true, wiring/accrual date).
3. Append to `reports/CONTINUAL_STRATEGY_RESEARCH_BASELINE.md` (Firing 11 block).
4. Update living public log: `updates/2026-05-21-continual-6gate-asset-class-research/index.html` (Firing 11 Research Log section with ✅ Just Finished, 🔄 Working, 📅 Plan).
5. Move or copy marker to `reports/continual_research/6gate_validation/A_passed/` or B_failed/ as appropriate.
6. If wiring candidate: enable in alpha-engine-*.yml workflows + tv-paper-trade.
7. Parallel: Continue H-017 shadow, FOREX prereqs (direction/symbol quarantine, 1h data, real FRED/COT, DXY), COMMODITY COT re-agg with new guard, lighter classes.
8. Re-run full `validate_resolved_picks.py --by-asset-class` + framework on entire clean set; update 6GATES MD if thresholds tuned per class.

**Daily PnL / G1 note (all paths):** Use framework --daily-pnl (or resolver daily aggregation) for credible Sharpe vs. per-trade inflation (validate.py:77, 6GATES appendix). Target cost_survival >=0.6 on family.

---

## 6. Citations (Exhaustive — Every Source File + Prior Marker)

**Core Firing 9/10 Artifacts (this playbook's direct sources):**
- `reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING9_CRYPTO_SUBAGENT_FINDINGS_2026-05-21.md` (funding commands + families + subagent 019e49ff-5853...)
- `reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING10_EQUITY_FOREX_EXPANSION_2026-05-21.md` (E-ANON-001 plan + commands + subagent 019e4a14-b4c1...)
- `reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING10_H037_WIRING_PR_SCOPE_2026-05-21.md` (full emitter prototype, wiring steps, verification, subagent 019e4a14-a43d...)
- `reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING10_HYGIENE_MINIMAL_MERGE_DIFF_2026-05-21.md` (exact two-line diff)
- `reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING9_TAGGING_BACKFILL_SCRIPT_2026-05-21.py` (backfill impl + _infer)
- `reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING10_CURRENT_POLLUTION_ANALYZER_2026-05-21.py`
- `reports/continual_research/6gate_validation/CYCLE_2026-05-21_FIRING9_SUMMARY.md` + `CYCLE_2026-05-21_FIRING10_SUMMARY.md`
- `reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING9_H037_POSTFIX_REVALIDATION_SIM_2026-05-21.md` + `FIRING8_H037_POSTFIX_6GATE_SIM_2026-05-21.md`
- `reports/CONTINUAL_STRATEGY_RESEARCH_BASELINE.md` (Firing 9/10 blocks + all prior)
- `updates/2026-05-21-continual-6gate-asset-class-research/index.html` (living Firing 9/10 log)

**Core Code & Data (lines cited in sources):**
- `audit_trail/dashboard_generator.py:8254/8282` (hardcoded), 3589 (JSON_PICK_SOURCES), 3319 (_derive), 3471 (ETF), 3975 (etf example), 6027 (vix)
- `tools/validate_resolved_picks.py:59` (OUTPUT_DIR), parser ~318, _sharpe_from_trades:77, by-asset-class path
- `alpha_engine/statistical_validation_framework.py:557+` (daily), 1159 (CLI), Bootstrap/WF/MC/MTC classes
- `alpha_engine/edge_stability_harness.py:41-43` (EFF_MIN etc.), 164-197 (is_admissible), 543 (class)
- `alpha_engine/equity_strategy_harness.py:149+`, 507 (Momentum), 1864 (main)
- `alpha_engine/equity_strategies.py:73-1292`, `funding_rate_arb.py`, `basis_carry.py`, `crypto_*.py`, `etf_strategies.py`, `equity_vix_regime_momentum.py`
- `tools/h037_vix_carry.py` (carry logic, SECTOR_ETFS=11 XL*, wf harness)
- `paper_trading/strategies/h037_vix_carry.py` (BaseStrategy, regime filter VIX>14/CONTANGO_MIN=0.05, NormalizedPick)
- `paper_trading/data/h037_verification_state.json`, `incubator_strategies.py:812`
- `alpha_engine/data/h037_vix_carry_picks.json` (future emitter output)
- `reports/hypothesis_registry.json:416-462` (H-037 full + wiring + kill + 10% Kelly), `495-560` (E-ANON-001 TESTED_PASS), funding entries (~912+), H-017 etc.
- `audit_trail/data/universal_resolved_picks.json:10715+` (real funding CLOSED examples)
- `6GATES_2026-05-21_V1_FREEBUFF.MD:66/147/232-262` (gate defs, per-class tuning, tagging bug 73-178, real EQUITY ~20, daily vs per-trade)
- `alpha_engine/config.py` (symbol dicts, ETF_SYMBOLS partial), `asset_class.py:35`
- Prior markers: `FIRING7_TAGGING_HYGIENE_PR_SCOPE_2026-05-21.md`, `FIRING5_VALIDATION_ATTEMPT_H037_HYGIENE_2026-05-21.md`, `FIRING4_CANDIDATES_3PLUSNEW_PREREQS_2026-05-20.md`, B_failed/ equity_vix / commodity_cot / forex_stressed / lighter..., A_passed/luxalgo_confluence_2026-05-21.md, `EQUITY_TAGGING_BUG_P0_FIX_PROPOSAL_2026-05-21.md`, `COMMODITY_COT_GUARD_PATCH_firing10_2026-05-21.md`

**Subagent IDs:** 019e49ff-5853... (CRYPTO F9), 019e4a14-... (F10 three parallel).

All work directly traceable. Ready for autonomous execution the moment hygiene patch + backfill live.

**End of Firing 11 Post-Hygiene Execution Playbook.**  
Execute, promote passers, update markers/baseline/log/registry, continue the 30m loop (next: H-017 accrual, FOREX fixes, COMMODITY re-agg, lighter classes). Research mode only.

*Marker created 2026-05-21 per convention. Cite this file + all listed sources in future Firing 12 summary.*