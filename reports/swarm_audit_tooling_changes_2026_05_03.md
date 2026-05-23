# Swarm Audit Tooling Changes and Command Log - 2026-05-03

## Purpose

The user asked to use `tools/swarm` to research overlooked gaps in `findtorontoevents.ca/audit`, first smoke-testing GitHub Copilot, Mercury, and Grok against two Kimi audit attachments.

This note documents the code changes, generated artifacts, and commands run so another agent can vet the work.

## Files Changed

### `tools/swarm/swarm_run.py`

Changed flag-mode runs to load the repo `.env` before worker dispatch.

Why: YAML config mode already hydrated `.env` through `config_loader.load_config()`, but direct flag-mode runs did not. That caused API engines such as `xai` to be launched through `isolated_env()` without keys even though `.env` contained them.

### `tools/swarm/config_loader.py`

Changed `.env` hydration so empty parent-shell variables are treated as unset.

Why: if a key existed in `os.environ` as an empty string, `load_dotenv()` skipped the real value from `.env`. That could still leave a worker with no usable key.

### `tools/swarm/worker_runner.py`

Changed the Copilot adapter to:

- Bypass the Windows npm `.cmd` shim and call a packaged `copilot-*/copilot.exe` directly when available.
- Preserve prompt text, including newlines and cmd metacharacters `|`, `<`, and `>`.
- Run Copilot with `--no-custom-instructions`, `--no-ask-user`, `--output-format text`, `-s`, and `--stream off`.

Why: the first Copilot smoke run followed repo/session instructions and attempted shell execution instead of reviewing the pasted attachment excerpts. Later, a larger JSON prompt hit a Windows shim parsing issue: `'limited' is not recognized...`, likely from the JSON enum text `substantive|limited|failed`. A prior lossy sanitizer was removed after review because it corrupted prompts and broke cross-engine equivalence.

### `tests/test_swarm_tooling.py`

Added `unittest` regressions for:

- `.env` loading overriding empty/whitespace env vars but not non-empty env vars.
- Copilot receiving prompts unchanged, including `substantive|limited|failed`, `PF > 1.5`, `WR < 50%`, bullets, and newlines.

### `swarm_runs/audit_attachment_smoke_prompt_2026_05_03.md`

Added the two-attachment smoke prompt with excerpts from:

- `C:\Users\zerou\Downloads\Kimi_Agent_Prediction Edge Audit\quant_audit_requirements.md`
- `C:\Users\zerou\Downloads\Kimi_Agent_Prediction Edge Audit\quant_audit_sec01.md`

### `swarm_runs/audit_gap_research_prompt_2026_05_03.md`

Added the larger gap-research prompt containing current repo evidence and requesting JSON-only gap findings.

### `updates/2026-05-03-swarm-smoke-runner-fix.md`

Added a short fix note describing the swarm smoke runner issues and verification command.

### `reports/audit_gap_swarm_2026_05_03.md`

Added a concise synthesis of the audit gap swarm results.

## Commands Run

### Initial Tool/Attachment Inspection

```powershell
Get-ChildItem "C:\Users\zerou\.cursor\projects\c-findtorontoevents-antigravity-ca\terminals" | Select-Object Name,Length,LastWriteTime; Get-ChildItem "swarm_runs" | Select-Object -First 5 Name,Mode,LastWriteTime
```

Purpose: checked terminal metadata and verified `swarm_runs` parent before creating/running new swarm artifacts.

### First Three-Engine Smoke Run

```powershell
python tools/swarm/swarm_run.py --prompt-file "swarm_runs/audit_attachment_smoke_prompt_2026_05_03.md" --engines copilot,inception,xai --out-dir "swarm_runs/audit_attachment_smoke_2026_05_03" --max-parallel 3
```

Result: `3/3` process-level OK, but inspection showed:

- Mercury/Inception produced a substantive raw response.
- Grok/XAI raw output was empty due missing key in env.
- Copilot returned an unrelated command-execution transcript.

```powershell
python tools/swarm/swarm_inspect.py "swarm_runs/audit_attachment_smoke_2026_05_03"
```

Result: suspect flags for all three because the smoke prompt requested prose, not schema JSON; `xai` was `ZERO`, Copilot and Inception were `PARSE_FAILED`.

### Copilot and Key Diagnostics

```powershell
where.exe copilot; copilot --version; copilot --help
```

Purpose: verified Copilot CLI exists and reviewed supported non-interactive flags.

```powershell
copilot -p "Answer exactly: PONG" --no-custom-instructions --no-ask-user --output-format text -s --stream off
```

Result: Copilot returned `PONG`.

```powershell
python -c "import os; keys=('X_AI_KEY','XAI_API_KEY','X_AI','GROK_SUPER','INCEPTION_AI_KEY'); print({k: bool(os.environ.get(k)) for k in keys})"
```

Result: all printed false in the parent process.

```powershell
python tools/swarm/config_loader.py
```

Result: repo `.env` was present and contained masked keys for `xai`, `inception`, and other API engines.

### Repeated Smoke Verification Runs

```powershell
python -m py_compile tools/swarm/swarm_run.py tools/swarm/worker_runner.py; if ($LASTEXITCODE -eq 0) { python tools/swarm/swarm_run.py --prompt-file "swarm_runs/audit_attachment_smoke_prompt_2026_05_03.md" --engines copilot,inception,xai --out-dir "swarm_runs/audit_attachment_smoke_2026_05_03_rerun" --max-parallel 3 }
```

Result: first attempted fix failed because `swarm_run.py` import fallback was wrong (`ModuleNotFoundError: No module named 'tools.swarm'`). Fixed the import path.

```powershell
python -m py_compile tools/swarm/swarm_run.py tools/swarm/worker_runner.py; if ($LASTEXITCODE -eq 0) { python tools/swarm/swarm_run.py --prompt-file "swarm_runs/audit_attachment_smoke_prompt_2026_05_03.md" --engines copilot,inception,xai --out-dir "swarm_runs/audit_attachment_smoke_2026_05_03_rerun" --max-parallel 3 }
```

Result: `3/3` process-level OK, but `xai` still had no key and Copilot still returned old/unwanted style output.

```powershell
python tools/swarm/swarm_inspect.py "swarm_runs/audit_attachment_smoke_2026_05_03_rerun"
```

Result: `copilot` and `inception` raw responses were non-empty, `xai` was zero.

```powershell
python -c "import sys; sys.path.insert(0,'tools/swarm'); from config_loader import load_dotenv; from safety import isolated_env; print('applied', sorted(load_dotenv().keys())); env=isolated_env('xai'); print('xai keys', {k: bool(env.get(k)) for k in ('X_AI_KEY','XAI_API_KEY','X_AI','GROK_SUPER')})"
```

Result: confirmed `.env` hydration could populate `xai` keys when loaded correctly.

```powershell
python -m py_compile tools/swarm/swarm_run.py tools/swarm/worker_runner.py tools/swarm/config_loader.py; if ($LASTEXITCODE -eq 0) { python tools/swarm/swarm_run.py --prompt-file "swarm_runs/audit_attachment_smoke_prompt_2026_05_03.md" --engines copilot,inception,xai --out-dir "swarm_runs/audit_attachment_smoke_2026_05_03_rerun2" --max-parallel 3 }
```

Result: all three engines produced process-level OK; `xai` and `inception` substantive, Copilot tiny and said excerpts were not included.

```powershell
python tools/swarm/swarm_inspect.py "swarm_runs/audit_attachment_smoke_2026_05_03_rerun2"
```

Result: `xai` and `inception` healthy raw outputs, Copilot tiny.

```powershell
python -m py_compile tools/swarm/swarm_run.py tools/swarm/worker_runner.py tools/swarm/config_loader.py; if ($LASTEXITCODE -eq 0) { python tools/swarm/swarm_run.py --prompt-file "swarm_runs/audit_attachment_smoke_prompt_2026_05_03.md" --engines copilot,inception,xai --out-dir "swarm_runs/audit_attachment_smoke_2026_05_03_rerun3" --max-parallel 3 }
```

Result: Copilot and Mercury/Inception substantive; XAI key issue still present due a previous patch not persisting as expected.

```powershell
python tools/swarm/swarm_inspect.py "swarm_runs/audit_attachment_smoke_2026_05_03_rerun3"
```

Result: Copilot and Mercury/Inception healthy raw outputs, XAI zero.

```powershell
python -m py_compile tools/swarm/swarm_run.py tools/swarm/worker_runner.py tools/swarm/config_loader.py; if ($LASTEXITCODE -eq 0) { python tools/swarm/swarm_run.py --prompt-file "swarm_runs/audit_attachment_smoke_prompt_2026_05_03.md" --engines copilot,inception,xai --out-dir "swarm_runs/audit_attachment_smoke_2026_05_03_final" --max-parallel 3 }
```

Result: final smoke run produced non-empty, substantive raw responses for all three engines.

```powershell
python tools/swarm/swarm_inspect.py "swarm_runs/audit_attachment_smoke_2026_05_03_final"
```

Result: all three raw outputs healthy by byte size. Inspector still showed `PARSE_FAILED` because the smoke prompt asked for prose instead of schema JSON.

### Repo Evidence Gathering

```powershell
python -c "import json; from pathlib import Path; data=json.loads(Path('audit_dashboard/data/dashboard_data.json').read_text(encoding='utf-8')); print('top_keys', sorted(data.keys())[:80]); perf=data.get('performance') or {}; print('performance_subkeys', list(perf.keys())[:50] if isinstance(perf,dict) else None); health=perf.get('asset_class_health') if isinstance(perf,dict) else None; print('asset_class_health_type', type(health).__name__, 'len', len(health) if hasattr(health,'__len__') else 'na'); [print('asset_health', cls, {k: row.get(k) for k in ['profit_factor','win_rate','n','max_drawdown','status','tier','verdict','sample_size']}) for cls,row in (health.items() if isinstance(health,dict) else [])]"
```

Purpose: summarized current dashboard payload structure and asset-class metrics.

```powershell
python -c "import json; from pathlib import Path; data=json.loads(Path('audit_dashboard/data/dashboard_data.json').read_text(encoding='utf-8')); health=data['performance']['asset_class_health']; [print(cls, sorted(row.keys()), row) for cls,row in list(health.items())[:3]]; print('walkforward type', type(data.get('walkforward')).__name__); print('walkforward keys', list((data.get('walkforward') or {}).keys())[:30] if isinstance(data.get('walkforward'),dict) else ''); print('tier2', data.get('tier2_proven_strategies'))"
```

Purpose: inspected `asset_class_health`, `walkforward`, and `tier2_proven_strategies` fields.

Also used `rg`/ReadFile tooling to inspect:

- `audit_dashboard/template.html`
- `audit_trail/forward_test_gates.py`
- `audit_trail/feed_membership.py`
- `alpha_engine/outcome_resolver.py`
- R:R, ML score, trust score, Verified Alpha, High Conviction, UEPS, and resolver-related references.

### Gap Research Swarm

```powershell
python tools/swarm/swarm_run.py --prompt-file "swarm_runs/audit_gap_research_prompt_2026_05_03.md" --engines copilot,inception,xai,deepseek,cerebras --out-dir "swarm_runs/audit_gap_research_2026_05_03" --max-parallel 5 --cost-cap-usd 0.50
```

Result:

- Healthy JSON: `deepseek`, `inception` (Mercury), `xai` (Grok).
- Failed/zero raw output: `copilot`, `cerebras`.
- `cerebras` failed because `cerebras-cloud-sdk` is not installed.
- `copilot` failed on larger prompt due Windows shim parsing: `'limited' is not recognized as an internal or external command`.

```powershell
python tools/swarm/swarm_inspect.py "swarm_runs/audit_gap_research_2026_05_03"
```

Result: 3 healthy, 2 suspect.

### Final Checks

```powershell
python -m py_compile tools/swarm/swarm_run.py tools/swarm/worker_runner.py tools/swarm/config_loader.py
```

Result: passed.

```powershell
python -m py_compile tools/swarm/swarm_run.py tools/swarm/worker_runner.py tools/swarm/config_loader.py tests/test_swarm_tooling.py; if ($LASTEXITCODE -eq 0) { python tests/test_swarm_tooling.py }
```

Result: passed, 2 tests.

```powershell
python tools/swarm/swarm_run.py --prompt-file "swarm_runs/audit_gap_research_prompt_2026_05_03.md" --engines copilot --out-dir "swarm_runs/audit_gap_research_2026_05_03_copilot_retry" --max-parallel 1 --cost-cap-usd 0.10
```

Result: interrupted by user after about 45 seconds.

```powershell
python tools/swarm/swarm_run.py --prompt-file "swarm_runs/audit_gap_research_prompt_2026_05_03.md" --engines copilot --out-dir "swarm_runs/audit_gap_research_2026_05_03_copilot_retry2" --max-parallel 1 --cost-cap-usd 0.10
python tools/swarm/swarm_inspect.py "swarm_runs/audit_gap_research_2026_05_03_copilot_retry2"
```

Result: Copilot ran through the direct executable path and produced healthy raw output. It still failed schema parsing, so it should be treated as corroborating commentary rather than a schema-valid JSON vote.

Follow-up from Claude review: the resolver now globs `copilot-*/copilot.exe` under the Copilot npm package rather than hardcoding only `copilot-win32-x64`, so future Windows package variants can use the same shim-bypass path.

## Consensus Findings From Healthy Engines

The healthy structured gap research engines (`deepseek`, Mercury/Inception, Grok) converged on these high-signal gaps. Copilot later corroborated the same cluster in raw malformed-JSON commentary.

- P0: R:R policy drift between prior Kimi report, current Guide copy, and backend gate constants.
- P0/P1: ML score threshold drift: prior `0.90` recommendation vs current `0.50` backend gate.
- P1: Verified Alpha and High Conviction are not fully wired; backend comments still call HC thresholds placeholders.
- P1: `UNKNOWN` asset class may use crypto-tight resolver fallback and shows suspicious high PF on insufficient data.
- P1: FOREX remains stressed with PF `0.27` and PnL `-987.03`, despite prior recommendation to halt/quarantine.
- P2: UEPS closed picks are still stubbed in client code.
- P2: tier-card consistency issues around `signal_validation` and `claude_gainer`.

See `reports/audit_gap_swarm_2026_05_03.md` for the shorter synthesis.

## Validation Status

- Python compile passed for changed swarm Python files.
- `python tests/test_swarm_tooling.py` passed.
- No deploy was run. These changes affect local swarm tooling and documentation, not the live site.
- Wire-Up Rule note: not applicable. These changes are local swarm/dev tooling, not a new production pick-generation or scoring integration module.

## Known Caveats

- Copilot is still not fully trusted for larger JSON prompts as a schema-valid engine. The Windows npm shim issue was fixed by direct `copilot.exe` invocation, but Copilot still returned malformed JSON on the large gap prompt.
- Cerebras requires `cerebras-cloud-sdk` before that engine can participate.
- The swarm gap analysis did not browse the live site; it compared attachment excerpts against current repo/data evidence.
