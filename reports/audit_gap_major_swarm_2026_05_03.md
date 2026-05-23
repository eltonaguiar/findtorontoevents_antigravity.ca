# Major Audit Gap Swarm — 2026-05-03

Goal prioritized: **#1 — audit dashboard performance and integrity**.

## Scope

This run continued the `tools/swarm` audit-gap investigation for `findtorontoevents.ca/audit`, comparing prior Kimi audit claims against current repository/dashboard evidence. It incorporated Claude's smoke-test notes and verified the contested Equity OOS Sharpe value directly from `audit_dashboard/data/dashboard_data.json` before launching the deeper rounds.

## Live-Data Verification

Command:

```powershell
python -c "import json; from pathlib import Path; data=json.loads(Path('audit_dashboard/data/dashboard_data.json').read_text(encoding='utf-8')); wf=data.get('walkforward') or {}; bc=wf.get('by_class') or {}; print('walkforward_generated_at', wf.get('generated_at')); print('classes', list(bc.keys())); ..."
```

Result:

- `walkforward_generated_at`: `2026-05-04T02:17:31.728676+00:00`
- `EQUITY`: `folds=47`, `oos_sharpe=3.527`, `oos_sharpe_std=9.164`, `oos_wr=57.9`, `worst_fold_wr=20.0`
- `ETF`: `folds=12`, `oos_sharpe=6.368`, `oos_sharpe_std=16.882`
- `CRYPTO`: `oos_sharpe=-0.088`
- `FOREX`: `oos_sharpe=-1.406`
- `COMMODITY`: `oos_sharpe=-2.412`

Verdict: the `+3.527` Equity Sharpe is present in current live dashboard data, but the very high standard deviation means it is not allocation-grade by itself. Treat it as a promising but noisy signal until DSR/PSR, confidence intervals, and multiple-testing correction are computed.

## Commands Run

Round 1 API/heavy batch:

```powershell
python tools/swarm/swarm_run.py --prompt-file "swarm_runs/audit_gap_round1_major_prompt_2026_05_03.md" --engines cerebras,inception,xai,deepseek,openrouter,ollama_cloud --out-dir "swarm_runs/audit_gap_round1_api_2026_05_03" --max-parallel 6 --cost-cap-usd 0.75 --json-strict
python tools/swarm/swarm_inspect.py "swarm_runs/audit_gap_round1_api_2026_05_03"
```

Round 1 CLI/free-agent batch:

```powershell
python tools/swarm/swarm_run.py --prompt-file "swarm_runs/audit_gap_round1_cli_prompt_2026_05_03.md" --engines kilo,opencode,agent,codex,openclaude --out-dir "swarm_runs/audit_gap_round1_cli_2026_05_03" --max-parallel 3 --cost-cap-usd 0.25 --json-strict
python tools/swarm/swarm_inspect.py "swarm_runs/audit_gap_round1_cli_2026_05_03"
```

Round 2 persona batches:

```powershell
python tools/swarm/swarm_run.py --prompt-file "swarm_runs/round2_forex_diagnostic_prompt_2026_05_03.md" --engines cerebras,inception,xai,deepseek --persona forex-diagnostic-surgeon --out-dir "swarm_runs/audit_gap_round2_forex_2026_05_03" --max-parallel 4 --cost-cap-usd 0.25 --json-strict
python tools/swarm/swarm_run.py --prompt-file "swarm_runs/round2_resolver_contract_prompt_2026_05_03.md" --engines cerebras,inception,xai,deepseek --persona audit-resolver-v2 --out-dir "swarm_runs/audit_gap_round2_resolver_2026_05_03" --max-parallel 4 --cost-cap-usd 0.25 --json-strict
python tools/swarm/swarm_run.py --prompt-file "swarm_runs/round2_cross_asset_quant_prompt_2026_05_03.md" --engines cerebras,inception,xai,deepseek --persona cross-asset-quant --out-dir "swarm_runs/audit_gap_round2_cross_asset_2026_05_03" --max-parallel 4 --cost-cap-usd 0.25 --json-strict
python tools/swarm/swarm_inspect.py "swarm_runs/audit_gap_round2_forex_2026_05_03"
python tools/swarm/swarm_inspect.py "swarm_runs/audit_gap_round2_resolver_2026_05_03"
python tools/swarm/swarm_inspect.py "swarm_runs/audit_gap_round2_cross_asset_2026_05_03"
```

## Engine Health

- API/heavy batch: `6/6` engines returned output. Schema-valid JSON from `deepseek`, `openrouter`, `xai`; substantive parse-failed output from `cerebras`, `inception`, `ollama_cloud`.
- CLI/free-agent batch: `5/5` commands exited OK. Useful schema-valid JSON from `kilo` and `opencode`; `agent` gave substantive commentary; `codex` hit usage limit; `openclaude` returned a schema/tool error.
- Persona Round 2: `12/12` outputs healthy with no suspect engines across `forex-diagnostic-surgeon`, `audit-resolver-v2`, and `cross-asset-quant`.
- Copilot was intentionally excluded from large-prompt rounds after Claude's smoke test confirmed Windows argv limit failures (`WinError 206`) around large prompts. `openrouter` was used as the Copilot stand-in for the large pass.

## Consensus Findings

### P1 — R:R Claims And Code Gates Are Misaligned

Multiple engines converged on the same gap: prior Kimi materials describe a `1.5-2.0R` sweet spot and danger above `2.0R`, while current code has `MIN_RR = 1.2` and no obvious upper cap. The dashboard guide also contains conflicting copy: crypto `R:R >=2.0` is described as high-performing in one place, while another footnote says `R:R >=1.5` underperforms every asset class.

Action: rederive R:R bands from closed picks by asset class, then align `forward_test_gates.py`, dashboard guide copy, and any UI filters to one canonical rule. Do not enforce a hard `2.0R` cap blindly until the crypto exception is verified or rejected.

### P1 — FOREX Is Still A Rescue Case, But Not A Silent Kill

Round 2 persona results classified FOREX as mostly `mixed`, with one Cerebras output calling it `measurement_contaminated`. Current evidence is very bad (`PF 0.27`, `WR ~46%`, `oos_sharpe -1.406`) but the swarm recommends running resolver/feed diagnostics before a final kill decision.

Action: follow the three-phase FOREX protocol: validate FX feed schema and latency, sandbox re-run resolver-v2 on the latest FOREX feed, quantify PF before/after resolver impact, then run mutation-before-kill. If PF does not recover materially, enforce dampening/quarantine.

### P1 — Resolver/UI Contract Drift Can Create Phantom Confidence

Round 2 `audit-resolver-v2` outputs independently flagged `UNKNOWN` asset class fallback to crypto-tight threshold, placeholder High Conviction thresholds, narrow Verified Alpha membership, and the UEPS `const closedPicks = [];` stub. These are user-facing integrity risks because labels can look more mature than the underlying contract.

Action: give `UNKNOWN` an explicit threshold policy or exclude it from promotional cards; calibrate HC thresholds against closed-book evidence; label UEPS as building until a real closed-picks source is wired.

### P1 — Equity Sharpe Is Verified But Too Noisy For Allocation Alone

The Kimi/Claude-flagged Equity `oos_sharpe=3.527` is not hallucinated; it exists in current dashboard data. The caveat is `oos_sharpe_std=9.164`, only `47` folds, and a `worst_fold_wr=20.0`. Engines converged on `watch` rather than clean `scale` for Equity unless DSR/PSR and multiple-testing checks clear.

Action: compute Deflated Sharpe Ratio and Probabilistic Sharpe Ratio for Equity and ETF; report confidence intervals and fold dispersion beside any headline Sharpe.

### P2 — Commodity Looks Good In Asset Health But Bad In Walk-Forward

Commodity has asset health `PF 1.78` on `n=750`, but walk-forward `oos_sharpe=-2.412`. The cross-asset personas disagreed on `scale` vs `watch`, which is itself the signal: do not promote commodity until the divergence is explained by regime, resolver, or sample slicing.

Action: run regime clustering and per-source attribution for commodity; compare closed-book PF to walk-forward fold returns under the same cost model.

### P2 — Prior Trust Score And Risk-Of-Ruin Claims Need Source Reproduction

Several engines flagged that prior claims like `trust_score >=5` producing `68-71% WR` and meme/penny risk-of-ruin values are not currently reproducible from the evidence pasted into the prompts. They may be true, but should not be promoted without a reproducer command and source dataset.

Action: add a small reproduction script or report section that ties those values to specific rows/files, or downgrade the claims to hypotheses.

## Recommended Next Work

1. Run a deterministic R:R band audit from closed picks and patch the dashboard guide / code gate conflict.
2. Run the FOREX resolver/feed diagnostic before any kill decision.
3. Add DSR/PSR and confidence interval reporting for Equity/ETF Sharpe cards.
4. Replace or explicitly label UEPS placeholder closed-pick state.
5. Create a resolver contract test for `UNKNOWN` asset class threshold handling.

## Artifacts

- `swarm_runs/audit_gap_round1_major_prompt_2026_05_03.md`
- `swarm_runs/audit_gap_round1_cli_prompt_2026_05_03.md`
- `swarm_runs/audit_gap_round1_api_2026_05_03/`
- `swarm_runs/audit_gap_round1_cli_2026_05_03/`
- `swarm_runs/round2_forex_diagnostic_prompt_2026_05_03.md`
- `swarm_runs/round2_resolver_contract_prompt_2026_05_03.md`
- `swarm_runs/round2_cross_asset_quant_prompt_2026_05_03.md`
- `swarm_runs/audit_gap_round2_forex_2026_05_03/`
- `swarm_runs/audit_gap_round2_resolver_2026_05_03/`
- `swarm_runs/audit_gap_round2_cross_asset_2026_05_03/`
