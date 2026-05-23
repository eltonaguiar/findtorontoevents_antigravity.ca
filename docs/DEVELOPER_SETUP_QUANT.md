# Developer setup — quant / Python tests

## Environment

```bash
cd /path/to/findtorontoevents_antigravity.ca
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
pip install pytest
```

Optional: `pip install ruff` for linting (config can be added later).

## Run a focused pytest subset

```bash
pytest tests/test_risk_policy_loader.py tests/test_validation_gate.py tests/test_conviction_stack.py -q
```

## Run HC filter / quant smoke (if present)

```bash
npm run test:hc-filter
python tools/mimo_strategy_validation_smoke.py
```

## GitHub CLI

See `tools/GITHUB_CLI_AND_PR.md` — ensure `%USERPROFILE%\.local\bin` is on `PATH` for `gh`.

## Environment variables

Never commit `.env`. Copy from a private template if your team maintains one. Required variables vary by subsystem (FTP, APIs); see subsystem READMEs under `alpha_engine/`, `favcreators/`, etc.
