# Fix: Add missing `load_dotenv` to `tools/swarm/config_loader.py`

## What was broken
CI on main was failing with:
```
ImportError: cannot import name 'load_dotenv' from 'config_loader' (tools/swarm/config_loader.py)
```

The test `tests/test_swarm_tooling.py::SwarmToolingTests::test_load_dotenv_overrides_empty_env` expected to import `load_dotenv` from `config_loader`, but the function did not exist.

## What changed
Added `load_dotenv(env_path: str) -> dict` to `tools/swarm/config_loader.py`.

Behavior:
- Reads a `.env` file line-by-line
- Skips comments (`#`) and blank lines
- For each `KEY=value` pair, only overrides the environment variable if the current value is `None` or whitespace-only
- Returns a dict of the variables that were actually applied

## How it was verified
```bash
python -m pytest tests/test_swarm_tooling.py::SwarmToolingTests::test_load_dotenv_overrides_empty_env -v
```
Result: **1 passed**
