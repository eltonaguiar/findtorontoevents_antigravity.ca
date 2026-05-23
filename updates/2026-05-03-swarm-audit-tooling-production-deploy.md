# Swarm Audit Tooling Production Deploy

Date: 2026-05-03

## Summary

Completed the `tools/swarm` smoke test and gap-research pass for `findtorontoevents.ca/audit`, using the Kimi Prediction Edge Audit attachments as prior-report context and current repo evidence as the source of truth.

## What Changed

- Fixed `tools/swarm/swarm_run.py` so direct flag-mode runs load `.env` before dispatching isolated API-engine workers.
- Fixed `tools/swarm/config_loader.py` so whitespace-only environment values are treated as unset and can be filled from `.env`.
- Fixed `tools/swarm/worker_runner.py` so GitHub Copilot bypasses the Windows npm `.cmd` shim and uses packaged `copilot-*/copilot.exe` when available, preserving prompts verbatim.
- Added `tests/test_swarm_tooling.py` to guard the `.env` override behavior and Copilot prompt preservation.
- Documented the audit gap findings in `reports/audit_gap_swarm_2026_05_03.md`.
- Documented all tooling changes and commands in `reports/swarm_audit_tooling_changes_2026_05_03.md`.

## Swarm Results

- Attachment smoke test: Copilot, Mercury/Inception, and Grok all produced substantive raw outputs.
- Gap research: structured findings came from 3 healthy JSON outputs out of the original 5-engine run (`deepseek`, Mercury/Inception, Grok).
- Copilot later corroborated the same gap cluster as raw commentary, but not schema-valid JSON.
- Cerebras remained unavailable because `cerebras-cloud-sdk` is not installed.

## Main Audit Gaps Found

- R:R policy drift between prior Kimi claims, current Guide copy, and backend gate constants.
- ML score threshold drift between prior `0.90` recommendation and current `0.50` backend gate.
- Verified Alpha and High Conviction feed membership still rely on narrow/manual or placeholder logic.
- UNKNOWN asset-class results may be polluted by crypto-tight resolver fallback thresholds.
- FOREX remains stressed and should stay under investigation/quarantine rather than be silently promoted.
- UEPS closed picks are still stubbed in client code.
- Tier-card sample and sparkline fields need consistency validation.

## Verification

Local checks passed:

```powershell
python -m py_compile tools/swarm/swarm_run.py tools/swarm/worker_runner.py tools/swarm/config_loader.py tests/test_swarm_tooling.py
python tests/test_swarm_tooling.py
```

Deployment target:

- FTP remote path: `findtorontoevents.ca`
- Deploy mode: `python tools/deploy_to_ftp.py --updates-only`

No full-site deploy was required for the swarm tooling changes because they do not affect public runtime assets. The production deploy publishes this update note under `/updates/`.
