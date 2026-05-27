# Audit remaining items — EAGLE backlog

**Timestamp:** 2026-05-27 02:17 EST (Toronto local review window)  
**Model / provider:** GPT-5.4 / OpenAI

## Batch ordering

### Batch A — finished / low-risk first

- Dedup review helper now supports direct canonical path output via `--paths-only`
- Quick-win and backlog docs created

### Batch B — next instrumentation / observability PRs

1. **Profitable-but-filtered audit lane**
   - Goal: log and expose picks that failed a gate but later would have won materially
   - Files: `audit_trail/quality_gates.py`, `audit_trail/dashboard_generator.py`, optional sidecar writer/table
2. **Hot-streak exemption with audit trail**
   - Goal: make streak-based exemptions explicit, bounded, and reviewable
   - Files: `audit_trail/quality_gates.py`, optional config + dashboard surfacing
3. **HC parity cleanup**
   - Goal: eliminate JS/Python decision drift
   - Files: `audit_dashboard/hc_filter.js`, `tools/dashboard_hc_rules.py`, `config/hc_gate_params.json`
4. **Unified findings schema**
   - Goal: replace split INCIDENT_/ENHANCEMENT_ families with one lifecycle model
   - Files: schema / migration docs + renderer consumers

### Batch C — asset-class corrective PRs

#### EQUITY

1. **Large-cap vs penny/meme split**
2. **Hard VIX / SPY regime gate merge**
3. **PEAD / earnings sleeve on clean large-cap universe**

#### ETF

4. **VIX-gated sector rotation activation**
5. **Dual-momentum fallback when primary sector filter emits zero**
6. **ETF mixed-source dilution audit (especially XLE concentration)**

#### COMMODITY

7. **Historical COT re-aggregation**
8. **Independent-cycle-only class health**
9. **Diversified carry/momo + multi-symbol COT sleeve**

#### FOREX

10. **4-major paper-only isolate**
11. **SHORT / DXY / session gating**
12. **Hard-disable fallback if no clean recovery**

#### CRYPTO

13. **Liquid-core universe with ADV gate**
14. **Source whitelist + noisy-source quarantine**
15. **Enable on-chain / funding sleeve for majors**

#### BOND

16. **Research-only pilot trio**
    - TIPS mean reversion
    - Curve carry
    - HYG-LQD credit mean reversion

#### FUTURES

17. **Unify futures taxonomy**
18. **If kept separate, only as research-only financial-futures sleeve**

## Direct answers to the review questions

### Did we likely block some picks that would have won big?

**Yes, probably.** The most likely locations are:

- concentrated sleeves caught by generic concentration gates,
- FOREX / thin-sample sleeves blocked by forward-trade minimums,
- asset classes penalized by mixed good+bad sources instead of isolating the good sleeve,
- quarantined sleeves with no “profitable-but-quarantined” reporting lane.

### Do any picks deserve exemption to safety gates?

**Not blindly.** The better pattern is:

1. require evidence over a rolling clean window,
2. limit exemptions to specific sleeves, not whole classes,
3. time-box them,
4. log every exemption,
5. auto-revoke on deterioration.

### Do hot streaks deserve exemptions?

**Potentially, but only in a bounded way.** Current repo logic has streak-aware scoring, but not a proper hot-streak exemption contract. The right follow-up PR is:

- minimum clean sample,
- capped exemption duration,
- per-sleeve only,
- explicit audit row,
- automatic rollback when the streak ends.

### Are any trades basically “sure things” that bounce between two prices?

**No credible evidence supports treating any current setup as a sure thing.** The closest candidates are classic bounded mean-reversion sleeves in:

- ETF rotation / SPY-QQQ Connors-style setups,
- bond credit-spread mean reversion,
- selected major-FX mean reversion windows,

but those still need paper validation and should never be promoted as guaranteed oscillators.

## Best per-asset-class strategy targets

| Class | Top strategy target |
| --- | --- |
| CRYPTO | Liquid-core majors + funding/on-chain + whitelist |
| EQUITY | Large-cap momentum/quality/PEAD with VIX/SPY regime gating |
| ETF | VIX-gated sector rotation + dual momentum |
| COMMODITY | Deduped independent-cycle COT + carry/momo diversification |
| FOREX | 4-major paper-only SHORT/DXY/session-gated sleeve |
| BOND | Research-only TIPS / curve / credit MR pilots |
| FUTURES | Unified futures taxonomy, then selective financial-futures pilots |
| PENNY/MEME | No production strategy; quarantine only |

## Concrete PR menu

1. **PR-001:** dedup-md-files paths-only output
2. **PR-002:** audit review docs + roadmap normalization proposal
3. **PR-003:** profitable-but-filtered audit lane
4. **PR-004:** HC JS/Python parity
5. **PR-005:** EQUITY universe split
6. **PR-006:** ETF VIX-gated sector rotation activation
7. **PR-007:** COMMODITY COT re-aggregation and honest class reset
8. **PR-008:** FOREX isolate winners + hard-disable fallback
9. **PR-009:** CRYPTO liquid-core and source-whitelist pilot
10. **PR-010:** unified findings tables and renderer migration

## Verification plan for later PRs

- `py_compile` on touched Python files
- targeted script invocation for any utility change
- only existing repo tests / checks
- no local dashboard generation
- only stage/commit files created or edited for the PR at hand
