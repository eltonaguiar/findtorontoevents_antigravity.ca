# Red-Team PR #233 Persona Activation Diffs — Cross-Verify — 2026-05-31

**PR:** #233 `docs: persona activation diff packets (6 classes × 33 steps)`
**File:** `reports/peer_claude-PERSONA_ACTIVATION_DIFFS_6_CLASSES_2026-05-31.md`
**Reviewer:** RT_233 (Claude Opus 4.7)

## Verified facts
- All 6 persona JSONs exist at `config/personas/strategy_persona__*.json`.
- `tools/populate_picks.py:405` and `:456` ARE `PERSONA_STRATEGIES` and `PERSONA_THESIS_MAP` (verified by grep — exact line match).
- `alpha_engine/auto_tuner.py` has `PERMANENTLY_KILLED` (171), `LOW_CONFIDENCE_STRATEGIES` (71), `HARD_DISABLED_PATTERNS` (195). None contain `stocks_rsi2_pullback`, `fx_smart_carry_trade_momentum`, `regime_mild_bull`, or `futures_momentum`. Kill-list pre-flights pass.
- The 4 model names cited (cursor_agent, claude_opus, ring_261T, gemini_25_pro) all exist in `config/model_persona_mapping.json`.
- Resolver intrabar IS a real outstanding blocker (session memory `project-session-close-2026-05-31`: "resolver intrabar is THE upstream T2 blocker"). **CRYPTO HARD BLOCK is correctly stated.**

## Defects found

### DEFECT-1 (HIGH) — Wrong JSON schema in apply commands (5 of 6 classes)
PR #233 apply commands write to `d['<model>']['<asset_class>']` (top-level model keys). Actual schema is:
```
d['models']['<model>']['assignments']['<asset_class>']
```
Running the doc's `python -c` snippets verbatim would CREATE new top-level keys and leave the real `models.<x>.assignments.<asset_class>` arrays untouched — silently failing the activation. Affects EQUITY (step 4), FOREX (step 3), ETF (step 3), BOND (step 3), COMMODITY (step 5).

### DEFECT-2 (HIGH) — Wrong file for `passes_active_gate` (CRYPTO step 1)
Doc says: `alpha_engine/smart_picks_engine.py::passes_active_gate`. Actual location: `audit_trail/quality_gates.py` (2 defs). Confirmed via `alpha_engine/config.py:333` cross-reference. CRYPTO diff target #1 is fabricated.

### DEFECT-3 (MED) — Missing source-report citation (CRYPTO blocker table)
Doc cites `reports/phase10b_crypto_money_maker_readyv2_2026-05-31.md` for "Plan #198 blocklist". File does not exist. Closest match: `reports/peer_claude-phase10b-money-maker-crypto_{plan,result}_2026-05-31.md`. Source URL incorrect.

### DEFECT-4 (LOW) — Pre-flight grep expected-line list is stale
Doc says expect lines `393, 394, 405, 456, 557, 651, 657, 821`. Live grep matches all 8 — verified clean. (Not a defect; included as positive confirm.)

## Quality signals
- **CRYPTO dependency guard is ACCURATE**: resolver intrabar rewrite + plan #198 blocklist wiring are both genuinely outstanding per session memory. The HARD BLOCK call is correct, the gate text is appropriately conservative, and the "do not activate before re-derived PF>0.8 in clean data" framing matches the M-107 mutate-before-kill discipline. This is the right call.
- COMMODITY is correctly marked DEFERRED (scaffold, no signal source).
- Activation gates (FOREX per-symbol cap, ETF asset_class-not-category, BOND symbol_whitelist) match real risk surfaces noted in `CLAUDE.md` (USDJPY 55% concentration, category-mess, futures_momentum commodity contamination).

## Per-class verdicts
| Class | Verdict | Reason |
|---|---|---|
| EQUITY | NEEDS_CORRECTION | JSON schema wrong (DEFECT-1) |
| FOREX | NEEDS_CORRECTION | JSON schema wrong (DEFECT-1) |
| CRYPTO | NEEDS_CORRECTION | Wrong file for passes_active_gate (DEFECT-2) + missing report (DEFECT-3); but dependency guard CORRECT |
| ETF | NEEDS_CORRECTION | JSON schema wrong (DEFECT-1) |
| BOND | NEEDS_CORRECTION | JSON schema wrong (DEFECT-1) |
| COMMODITY | VERIFIED | Correctly deferred; no real apply commands to validate |

## Tally
- VERIFIED: 1 (COMMODITY)
- NEEDS_CORRECTION: 5 (EQUITY, FOREX, CRYPTO, ETF, BOND)
- FABRICATED: 0

## Recommendation
PR #233 is **docs-only** so the schema bug ships no code damage, but any operator who copy-pastes the apply commands will silently misconfigure model_persona_mapping. Land a follow-up that:
1. Rewrites the 5 JSON-edit snippets to use `d['models'][m]['assignments'][asset_class]`.
2. Re-targets CRYPTO step 1 to `audit_trail/quality_gates.py::passes_active_gate`.
3. Replaces the fabricated `phase10b_crypto_money_maker_readyv2` citation with the real `peer_claude-phase10b-money-maker-crypto_result_2026-05-31.md`.

CRYPTO HARD BLOCK on resolver intrabar is **CORRECT** — keep it as written.

`RT_233:verified=1:needs_correction=5:fabricated=0`
