# experiments/

One subfolder per **pre-registered** run: `experiments/<run_id>/`.

Each `run_id` folder must contain, before execution:

- `HYPOTHESIS.md` — the single falsifiable claim, plus which inventory row (F#) it responds to
- `config.json` — universe, dates, timeframe, parameters, cost model, seed (frozen; any change = a NEW run_id)
- `run.py` — seeded, runnable, reads only `config.json`
- `results/` — equity curve, trade log, metrics JSON
- `VERDICT.md` — pass/fail against each of the 10 proof steps, with the exact number that decided it

## Rules

- **No run without a frozen `config.json`.** Editing config after results = new hypothesis, new run_id.
- **Trial counter:** every `run_id` increments the project-wide trial count. That number feeds the deflated-Sharpe correction (proof step 3). Under-reporting it invalidates every downstream significance claim.
- **Rejected runs are kept**, not deleted. The negative results are the most valuable asset in this repo.
- Naming: `<asset_class>_<signal_family>_<YYYYMMDD>_<seq>` e.g. `equity_quality_momentum_20261115_001`.

## Current runs

| run_id | hypothesis | status |
|---|---|---|
| (none yet — Phase 2 opens the first run: `equity_quality_momentum_20261115_001`) | cross-sectional quality-momentum vs SPY | pre-registered, not started |
