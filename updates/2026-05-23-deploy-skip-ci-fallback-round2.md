# 2026-05-23 - Deploy skip-ci fallback hardening (round 2)

## What this addresses

A follow-up review found additional deploy workflows where upstream automation frequently commits watched files with `[skip ci]`, preventing `push`-triggered deploy jobs from firing immediately.

## Changes made

1. `.github/workflows/deploy-battleground-ftp.yml`
- Added hourly fallback schedule:
  - `cron: '15 * * * *'`
- Keeps existing `push`, `workflow_dispatch`, and `workflow_run` triggers.
- Purpose: ensure battleground deploy runs even when upstream producers push with `[skip ci]`.

2. `.github/workflows/deploy-competition-to-site.yml`
- Expanded `workflow_run.workflows` fallback list to include:
  - `Audit Hourly Update`
  - `Unified Audit Dashboard`
  - `Fast Trading Variants  Master Scheduler`
- Existing entries retained.
- Purpose: cover additional upstream writers that can affect watched competition/update/audit artifacts while using `[skip ci]`.

3. `.github/workflows/torontoevent-deploy-competition.yml`
- Expanded `workflow_run.workflows` fallback list to include:
  - `Audit Hourly Update`
  - `Fast Trading Variants  Master Scheduler`
- Purpose: align torontoevent competition deploy fallback coverage with known skip-ci upstream producers for its watched paths.

## Verification

- Confirmed YAML syntax remains valid by preserving existing structure and trigger keys.
- Confirmed exact workflow names used match `name:` fields in their source workflow files.
- Confirmed these changes are additive (no existing trigger paths removed).
