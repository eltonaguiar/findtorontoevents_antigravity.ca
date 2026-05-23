# Grok Handoff — Bailey-Lopez Reference Implementations Appendix — 2026-05-20T0440Z

**Companion to:** [`reports/GROK_HANDOFF_FULL_2026-05-20T0430Z.md`](GROK_HANDOFF_FULL_2026-05-20T0430Z.md)

**Purpose:** before Grok writes `alpha_engine/bailey_lopez_gates.py`, here are three
independent engine drafts produced by the coding-swarm
(`swarm_runs/canonical_ldp_2026-05-20T0420Z/`). Grok should treat these as
**candidate references** — cross-check formulas against canonical Bailey-Lopez
papers, NOT copy verbatim. Each has issues; none is ship-ready as-is.

---

## Swarm run summary

| Engine | rc | bytes | schema | status |
|--------|----|-------|--------|--------|
| xai (Grok-Production-Quant) | 0 | 8462 | ✅ schema-compliant | code + 10 tests delivered |
| deepseek | 0 | 14347 | ❌ wrapped in markdown fences | code present in raw .txt, parser fell back |
| cerebras (ChatGPT-4o relay) | 0 | 9218 | ❌ embedded newlines invalid | code present in raw .txt, parser fell back |

All three contain implementations of: `annualized_sharpe`,
`deflated_sharpe_ratio`, `probability_backtest_overfitting`,
`minimum_track_record_length`, `lopez_de_prado_gates`.

Files on disk:

```
swarm_runs/canonical_ldp_2026-05-20T0420Z/
├── _summary.json
├── xai.json                  ← schema-clean (parse this)
├── xai.json.raw.txt          ← raw model output
├── deepseek.json             ← parse_status: non_json_fallback
├── deepseek.json.raw.txt     ← raw markdown-wrapped Python
├── cerebras.json             ← parse_status: non_json_fallback
└── cerebras.json.raw.txt     ← raw schema-broken JSON, code intact
```

---

## Reference draft #1 — xAI (Grok-Production-Quant), schema-compliant

**File:** `swarm_runs/canonical_ldp_2026-05-20T0420Z/xai.json`
**Module bytes:** 5280 | **Tests bytes:** 1825 | **math_self_check:** 4 entries

### Strengths (auditor's read)

- ddof=1 on sample std ✓
- `gamma_e * (1 - γ_E)` Euler constant correct ✓
- DSR formula `((sr - sr_0) * sqrt(n-1)) / sqrt(1 - skew*sr + ((kurt-1)/4)*sr^2)` matches Bailey 2014 eq. 10 ✓
- CSCV via `itertools.combinations(range(S), S//2)` matches Bailey 2017 ✓
- MinTRL `1 + var_term * (z_alpha / denom)**2` matches Bailey 2014 eq. 12 ✓
- NaN-safe via early returns ✓

### Issues Grok should fix

1. **`annualized_sharpe` called with `periods_per_year=1.0` inside DSR** — assumes
   caller pre-annualized. Bailey 2014 SR is per-period; annualization optional.
   This is OK but **must be documented in docstring** so caller knows.
2. **`kurt = stats.kurtosis(..., fisher=True) + 3.0`** — Fisher returns excess
   kurtosis. Bailey's `(κ-1)/4` denominator term uses **raw kurtosis** (κ=3 for
   normal). xAI's `+3.0` conversion is correct. **VERIFY** against Bailey 2014
   eq. 10 — some literature treats κ as excess + 1.
3. **`n_trials=1` edge case** — `sqrt(2*log(1)) = 0` and `norm.ppf(0) = -inf`.
   Need explicit guard: if `n_trials <= 1`, `sr_0 = 0`.
4. **PBO `oos_ranks[best_is] > (N+1)/2` median test** — Bailey 2017 uses
   `λ = log(rank / (N - rank + 1))` logit, then `PBO = P(λ < 0)`. xAI uses
   median-rank shortcut. **Approximation, not canonical.** Grok must implement
   the logit version.
5. **Tests are weak** — `test_dsr_matches_paper` only asserts `n == 500`.
   Should replicate a published Bailey 2014 Table 1 example (e.g., SR=2.5,
   skew=-3, kurt=10, n=1250 → DSR known value).
6. **`test_per_trade_vs_daily`** — asserts `s_trade > s_daily` which is
   mathematically guaranteed by `sqrt(N) > sqrt(252)` when N=1000. Tautology,
   not a behavior test.

### Verbatim xAI module source (for Grok cross-check)

See `swarm_runs/canonical_ldp_2026-05-20T0420Z/xai.json` field
`module_full_python_source`. Tests at `tests_full_python_source`.

---

## Reference draft #2 — DeepSeek, schema-broken (markdown-wrapped)

**File:** `swarm_runs/canonical_ldp_2026-05-20T0420Z/deepseek.json.raw.txt`
**Raw bytes:** 13538 | **Wrapped in:** ` ```python ` ... ` ``` `

DeepSeek wrote a longer implementation with more inline docstring math. To
extract, Grok should:

```bash
python -c "
import re
txt = open('swarm_runs/canonical_ldp_2026-05-20T0420Z/deepseek.json.raw.txt', encoding='utf-8').read()
# Strip first ```python fence and last ``` fence
m = re.search(r'```python\s*\n(.*?)\n```', txt, re.DOTALL)
if m: print(m.group(1))
"
```

**Notable differences from xAI** (to compare against):
- DeepSeek's `deflated_sharpe_ratio` likely uses different SR-annualization
  convention. Grok must compare line-by-line.
- DeepSeek's PBO may use the canonical logit `λ = log(r/(N-r+1))` instead of
  median-rank shortcut. **Worth checking.**
- DeepSeek's MinTRL may include the `+1` constant correctly per Bailey 2014
  eq. 12.

---

## Reference draft #3 — Cerebras (ChatGPT-4o relay), schema-broken (newline-escape)

**File:** `swarm_runs/canonical_ldp_2026-05-20T0420Z/cerebras.json.raw.txt`
**Raw bytes:** 9218 | **First chars:** `{ "engine": "ChatGPT-4o", "module_path": "alpha_engine/bailey_lopez_gates.py", "module_full_python_source": "import numpy as np\\n...`

Cerebras produced a JSON with literal `\n` characters embedded in the source
string that confused the swarm parser. To extract:

```bash
python -c "
import json
txt = open('swarm_runs/canonical_ldp_2026-05-20T0420Z/cerebras.json.raw.txt', encoding='utf-8').read()
# Try lenient json5/json parse with single-quote tolerance
d = json.loads(txt)
print(d['module_full_python_source'])
" 2>/dev/null || echo "needs manual cleanup"
```

**Risk flag:** Cerebras stamped itself as `ChatGPT-4o` engine — suggests it's a
relay endpoint. Trust level lower than xAI/DeepSeek direct outputs.

---

## What Grok should produce (canonical, ship-ready)

`alpha_engine/bailey_lopez_gates.py` that:

1. **Cites paper equations in docstrings.** Every formula gets an
   `# Bailey 2014 eq. N` comment.
2. **Implements PBO via canonical logit**, not median-rank shortcut.
   `λ_c = log(r_c / (N - r_c + 1))` per Bailey-Borwein-Lopez-Zhu 2017 §4.
3. **Handles n_trials=1 edge case** with explicit `sr_0 = 0` fallback.
4. **Documents annualization convention** in `annualized_sharpe` docstring —
   make it explicit that caller passes `periods_per_year = trades_per_year`
   for per-trade PnL input.
5. **Tests replicate at least ONE published Bailey 2014 numerical example.**
   E.g., Table 1 of arXiv:1212.4495 — given SR=2.5, skew=-3, kurt=10, n=1250
   → DSR has a published value Grok can assert against.
6. **PBO test uses Bailey 2017 synthetic example** — Table 3 or §6 has
   known-truth PBO values for noise vs signal mixtures.
7. **Fails closed.** All edge cases return `False, {'reason': '...'}`,
   never bare `False`.

---

## Cross-engine verification step (mandatory before ship)

After Grok writes the canonical module:

```bash
# Step 1 — independent math review
python tools/swarm/swarm_run.py \
  --prompt-file swarm_runs/_prompts/canonical_ldp_postship_review.md \
  --engines xai,cerebras,deepseek,mercury,inception \
  --out-dir swarm_runs/canonical_ldp_postship_review_<utc>

# Step 2 — cavecrew read-only verification (no LLM)
# Confirm formulas match canonical papers; no fabricated terms
Agent(subagent_type="cavecrew-investigator") with prompt:
  "Verify alpha_engine/bailey_lopez_gates.py implements Bailey-Lopez 2014/2017
   canonically. Output file:line table for each formula vs paper eq. number.
   Flag any term not in the published math."

# Step 3 — unit tests must pass
pytest tests/test_bailey_lopez_gates.py -v

# Step 4 — apply via fetch-origin-patch to origin/main (no local push)
```

---

## Pointers Grok needs

- **Audit prompt that killed Grok's original patch:**
  `swarm_runs/_prompts/ldp_gates_methodology_audit_2026-05-20T0410Z.md`
- **Implementation spec:**
  `swarm_runs/_prompts/canonical_ldp_implementation_2026-05-20T0420Z.md`
- **Main handoff:**
  `reports/GROK_HANDOFF_FULL_2026-05-20T0430Z.md`
- **M-107 binding:**
  `tools/edge_stability_harness.py::is_admissible()` UNMODIFIED
- **Canonical ledger:**
  `audit_dashboard/data/pf_registry.json::by_asset_class_policy_clean_net`

---

*Generated 2026-05-20T04:40Z by claude-opus-4-7-desktop. Companion appendix to
the full Grok handoff. Three independent engine drafts available on disk for
cross-validation; none ship-ready as-is. Canonical implementation delegated
to Grok with the post-ship multi-engine review + cavecrew verification gate.*
