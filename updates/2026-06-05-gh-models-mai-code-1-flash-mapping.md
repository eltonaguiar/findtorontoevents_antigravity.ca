# GitHub Models MAI-Code-1-Flash Mapping Fix (2026-06-05)

## What was broken
- The repository model registry in `config/model_persona_mapping.json` did not include a GitHub Models entry for `MAI-Code-1-Flash`.
- Any workflow that relies on this mapping could not select or route to that model ID.

## What changed
- Added a new model key: `gh_models_mai_code_1_flash`.
- Provider settings mirror existing GitHub Models wiring:
  - `provider`: `GitHub Models`
  - `api_type`: `openai_compat`
  - `api_key_env`: `GH_MODELS_API_KEY`
  - `endpoint`: `https://models.inference.ai.azure.com/chat/completions`
  - `model_name`: `MAI-Code-1-Flash`
- Reused the standard assignment matrix used by adjacent model entries to preserve expected behavior.

## Verification
- Confirmed the model string was previously absent via ripgrep search.
- Validated JSON syntax for `config/model_persona_mapping.json` after edit.
- Confirmed the new key/value appear in the file and remain parseable.

## Notes
- This change updates repository-side model mapping. If VS Code Copilot's UI model picker still does not show this model, that UI availability is controlled by GitHub/Microsoft service rollout and account entitlements outside this repo.
