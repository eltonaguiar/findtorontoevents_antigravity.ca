# Emitter whitelist + toxic kill switch (T2-01 / T2-02) — 2026-05-19

## What shipped

- **`alpha_engine/emitter_whitelist.py`** — loads `pf_registry.json`, builds allowlist (PF≥1.4, WR≥55%, n≥50) + manual seeds, auto-toxic (n≥20, PF<1.2), hardcoded swarm kills.
- **`audit_trail/quality_gates.py`** — `passes_active_gate` calls registry gate; added class-level blocks for quan_engine/CRYPTO, cta_replicator/COMMODITY, multi_asset_copytrader on FOREX/EQUITY.
- **`alpha_engine/forward_validator.py`** — emission-time skip for toxic/non-whitelisted signals.
- **`ml_consensus/consensus.py`** — drops toxic (class, strategy) from consensus scoring.
- **`tools/model_grill_sequential.py`** — local runs use Ollama HTTP `/api/generate` (not CLI `ollama run`).
- **`docs/swarm_prompts/`** — tracked copies of money-ready grill prompts (gitignored under `swarm_runs/_prompts`).
- **`tests/test_emitter_whitelist.py`** — 5 tests, all pass.

## Env flags

| Env | Default | Effect |
|-----|---------|--------|
| `EMITTER_REGISTRY_GATE` | `1` | Run gate in `passes_active_gate` / forward_validator |
| `EMITTER_WHITELIST_ENFORCE` | `0` | `1` = reject non-allowlisted strategies (shadow stamps `_emitter_registry_would_block` when off) |

## Verification

```powershell
python -m pytest tests/test_emitter_whitelist.py -q
python -c "import py_compile; py_compile.compile('alpha_engine/emitter_whitelist.py', doraise=True)"
```

## Remaining

- Set `EMITTER_WHITELIST_ENFORCE=1` in production only after 7d shadow review of `_emitter_registry_would_block` counts.
- Intraday crypto probe (H-035) still paper-only per MERGED_ACTION_PLAN.
