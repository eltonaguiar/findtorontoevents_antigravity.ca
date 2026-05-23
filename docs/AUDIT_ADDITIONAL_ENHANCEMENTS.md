# Additional audit / scoring enhancements (beyond Phase A–F checklist)

This note collects **extra** improvements discovered while reviewing [`docs/AUDIT_PREDICTION_SYSTEM_ENHANCEMENT_PLAN.md`](AUDIT_PREDICTION_SYSTEM_ENHANCEMENT_PLAN.md), the Cursor plan (`audit_score_enhancements_c5a87edd`), Hyro/main-dashboard investigations, and the codebase. It **does not replace** the canonical plan; it **extends** it with implementation hooks and automation opportunities.

---

## 1. Align downstream tools with unified SMART semantics (Phase A follow-through)

| Item | Why | Where |
|------|-----|--------|
| **Backfill script uses `classify_pick_quality`** | After `classify_pick_quality_v2` exists, closed-pick enrichment should use the **same** SMART/ACTIVE/REJECTED rules as live Smart Picks. | [`tools/backfill_closed_smart_scores.py`](tools/backfill_closed_smart_scores.py) (`_tier_if_still_active`, imports from `quality_gates`) |
| **`validate_quality_gates.py` heuristics** | Script prints coarse checks (e.g. score ≥ 65) that can **diverge** from real `passes_smart_gate`. Replace or supplement with **gate-aligned** diagnostics (count `passes_smart_gate`, mismatch vs legacy bucket). | [`validate_quality_gates.py`](validate_quality_gates.py) |

**Success signal:** Running backfill + validation after a dashboard JSON refresh reports **zero** systematic tier skew between “smart_score ranking” and `passes_smart_gate` on reconstructed active rows.

---

## 2. Expand automated tests before refactoring gates (Phase F enabler)

| Item | Why | Where |
|------|-----|--------|
| **Fixture matrix for `passes_smart_gate`** | Existing tests cover slices (e.g. source-less pick); add **forex low forward WR**, **crypto SHORT vs LONG** (with `SMART_PICKS_CRYPTO_LONG_ONLY`), **SCALP**, **panic health**, **concentration** edge cases. | [`tests/test_quality_gates.py`](tests/test_quality_gates.py) |
| **`classify_pick_quality_v2` parity tests** | Once implemented: `SMART` iff `passes_smart_gate`, `REJECTED` iff `not passes_active_gate`, else `ACTIVE`. | New tests colocated with quality gates |

---

## 3. CI: dedicated score-calibration workflow (Phase F)

| Item | Why | Where |
|------|-----|--------|
| **Pinned `dashboard_data.json` subset** | Regression needs **deterministic** input; avoid flaky live URL pulls on every PR. Commit a **trimmed** or **versioned** snapshot under `tools/data/` or `audit_dashboard/data/` (with size limits). | New workflow + repo policy |
| **`audit-score-regression.yml`** | Run `tools/analyze_audit_scores_vs_pnl.py` + `tools/audit_score_pnl_quadrant_deep_dive.py`; emit Spearman + decile summary; **non-blocking** until thresholds tuned. | [`.github/workflows/`](.github/workflows/) |
| **Reuse drift infra cautiously** | [`audit-drift-telemetry.yml`](.github/workflows/audit-drift-telemetry.yml) already processes `dashboard_data.json` for backtest/forward drift — **do not conflate** with Spearman score–PnL checks without a separate step name and artifact. | Coordination only |

---

## 4. Analytics extensions (Phase B1)

| Item | Why | Where |
|------|-----|--------|
| **Raw-score deciles stratified by `strategy_family`** | Detect copy vs systematic inversion without manual SQL. | Extend [`tools/analyze_audit_scores_vs_pnl.py`](tools/analyze_audit_scores_vs_pnl.py) (optional `--stratify strategy_family` or JSON config) |
| **Export monotonicity flag** | Machine-readable `monotonic_ok: bool` per stratum for CI gating. | Output JSON alongside `score_pnl_analysis.json` |

---

## 5. Trust and UX (Phase D + product)

| Item | Why | Where |
|------|-----|--------|
| **Dual column names in JSON schema doc** | Prevents consumers from mixing `trust_tier` (registry) with stamped strategy trust. | Short paragraph in [`audit_trail/dashboard_generator.py`](audit_trail/dashboard_generator.py) module doc or `docs/` |
| **Hyro vs main audit copy** | User-facing text should **not** imply Hyro WR applies to **copy-trader raw scores** on the main feed. | Audit dashboard templates + [`docs/AUDIT_PREDICTION_SYSTEM_ENHANCEMENT_PLAN.md`](AUDIT_PREDICTION_SYSTEM_ENHANCEMENT_PLAN.md) external validation section |

---

## 6. Blocklist and closed history (Phase E)

| Item | Why | Where |
|------|-----|--------|
| **`strategy_retired` on closed rows** | Makes historical analytics honest when strategies are later added to [`alpha_engine/strategy_blocklist.py`](alpha_engine/strategy_blocklist.py). | [`audit_trail/dashboard_generator.py`](audit_trail/dashboard_generator.py) + audit UI |
| **Ingress grep checklist** | Scripted search for `sanitize_active_picks` / `is_valid_active_pick` on every pick publisher. | One-off script under `tools/` or CI step |

---

## 7. Shared helpers: elite_scorer ↔ smart_score (Phase B/C)

| Item | Why | Where |
|------|-----|--------|
| **Single `_is_copy_pick` / BTC-major allowlist** | Avoid divergent heuristics between [`alpha_engine/elite_scorer.py`](alpha_engine/elite_scorer.py) and `calculate_smart_score`. | Small shared module, e.g. `audit_trail/copy_pick_utils.py` (import from both) |

---

## 8. Operational monitoring (KPIs)

| KPI | Suggested action |
|-----|------------------|
| Spearman(`smart_score`, `pnl_pct`) weekly | Dashboard or `GITHUB_STEP_SUMMARY` from scheduled workflow |
| **Hyro** vs **main audit** WR | Separate panels — do not blend in one headline number |
| Blocklist enforcement | Quarterly grep report of ingress paths |

---

## Priority suggestion

1. **Tests + backfill alignment** (sections 1–2) — reduces regression risk before changing production scoring.  
2. **Pinned snapshot + CI workflow** (section 3) — makes Phase F real.  
3. **Analytics stratification** (section 4) — feeds piecewise base calibration.  
4. **UX/trust/blocklist** (sections 5–6) — user trust and forensic clarity.  
5. **Shared copy helpers** (section 7) — refactor after behavior is validated.

---

*Document version: 2026-04-19. Maintainers: keep in sync with `AUDIT_PREDICTION_SYSTEM_ENHANCEMENT_PLAN.md`.*
