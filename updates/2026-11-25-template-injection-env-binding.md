# Template injection: 23 inline `${{ }}` expansions in `run:` moved into `env:`

**Date:** 2026-11-25
**Files:** `_dynamic-runner-template.yml`, `alpha-engine-daily-picks.yml`, `dna_strategy_pipeline.yml`, `ml-model-autotraining.yml`

## What was broken

Each of these workflows pasted values straight into a shell script with `${{ }}`:

```yaml
run: |
  UNIVERSE="${{ github.event.inputs.universe || 'default' }}"
  git commit -m "Update active picks - ... [${{ steps.gen.outputs.regime }}] [skip ci]"
```

GitHub expands `${{ }}` **before** the shell sees the script, so the substituted text is parsed as
shell syntax. A value containing `"`, `$(...)` or a backtick breaks out of the quoting and runs as a
command. `github.event.inputs.*` is dispatch-supplied and `steps.*.outputs.*` / `needs.*.outputs.*` are
written by whatever the previous step produced — neither is a trusted shell literal.

zizmor reported these as `template-injection`: 3 in `_dynamic-runner-template.yml`, 7 in each of the
other three.

## What changed

Every offending value is now bound in the step's `env:` block and read as a shell variable, which the
shell treats as data and never re-parses:

```yaml
env:
  IN_UNIVERSE: ${{ github.event.inputs.universe }}
  IN_TOP_K: ${{ github.event.inputs.top_k }}
  IN_MODE: ${{ github.event.inputs.mode }}
run: |
  UNIVERSE="${IN_UNIVERSE:-default}"
  TOP_K="${IN_TOP_K:-20}"
  MODE="${IN_MODE:-picks}"
```

The `:-default` form preserves the old `|| 'default'` semantics exactly, including the scheduled-run
case where dispatch inputs are empty. Specific bindings:

- **`_dynamic-runner-template.yml`** — `inputs.runner` → `SELECTED_RUNNER` in both steps that echoed it.
- **`alpha-engine-daily-picks.yml`** — the three dispatch inputs → `IN_UNIVERSE` / `IN_TOP_K` / `IN_MODE`
  in the generation step, and the same plus `PICKS_STATUS` / `PICK_COUNT` in the `Summary` step.
- **`dna_strategy_pipeline.yml`** — the three dispatch inputs → `IN_SYMBOLS` / `IN_REGIME` / `IN_MAX_PICKS`;
  step output `steps.gen.outputs.regime` → `REGIME_DETECTED` in the commit message;
  `needs.generate-picks.outputs.*` → env in `phoenix-revival` (read via `os.environ`, with
  `import os` added) and in `notify`.
- **`ml-model-autotraining.yml`** — `steps.check.outputs.*` → `TOTAL_RESOLVED` / `NEW_SIGNALS` /
  `TRAIN_REASONS` in `Commit trained models`, `Notify Discord` and `Skip notification`.

Two adjacent quoting bugs surfaced by the change were fixed in the same edit
(`echo "$SYMBOLS" | tr ...`, and `--symbols/--regime/--max-picks "$VAR"`).

## Verification

| Check | Result |
|---|---|
| zizmor `template-injection`, repo total | **173 → 150** |
| `_dynamic-runner-template.yml` | 3 → 1 |
| `alpha-engine-daily-picks.yml` | 7 → **0** |
| `dna_strategy_pipeline.yml` | 7 → **0** |
| `ml-model-autotraining.yml` | 7 → **0** |
| `yaml.safe_load` on all 4 | parse OK |
| `actionlint -shellcheck=` (native) on all 4 | exit 0, no findings |
| shellcheck count per file (base → now) | alpha 7→7, dna **12→10**, ml 1→1, template 0→0 — none increased |

No assertions were relaxed and no `if:`/gate logic changed; only the transport of the values.

## Residual (deliberately not changed)

`_dynamic-runner-template.yml` keeps one finding: `${{ runner.name }}`, `${{ runner.os }}`,
`${{ runner.arch }}` inside an `echo`. zizmor rates it **Low / Informational**. `runner.*` is set by the
GitHub runner, not by an event field an outsider can influence, so moving it to `env:` would add noise
without removing any reachable injection path. Left as-is and recorded here so a future audit does not
re-flag it as an oversight.

## Note on scope

The same pattern exists in ~150 other sites repo-wide (worst remaining:
`ml-gatekeeper-train-ab.yml`, `battleground-mass-backtest.yml`, `clear-channel-command.yml`). Each needs
per-file judgement about which values are attacker-reachable, so they were not batch-regexed here.
