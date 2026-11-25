# The 7 "dangerous trigger" workflows are `workflow_run`, not `pull_request_target`

**Date:** 2026-11-25
**Scope:** the 7 findings zizmor reports as `dangerous-triggers` (Medium) across `.github/workflows/`

## Correcting the record first

The task was framed as "the 7 `pull_request_target` deploy workflows". **There are zero
`pull_request_target` occurrences in this repository.** Measured three ways:

```
git grep -c pull_request_target HEAD          -- .github/workflows/   → no output
git grep -c pull_request_target origin/main   -- .github/workflows/   → no output
grep -rn pull_request_target --include=*.yml --include=*.yaml .       → no output
```

The 7 findings zizmor actually reports are `workflow_run`, which shares the `dangerous-triggers` rule
because both event types run with elevated (default-branch) privileges:

| File | Trigger |
|---|---|
| `deploy-battleground-ftp.yml` | `workflow_run: [Audit Impact Tracker, Battleground Mass Backtest, …]` |
| `deploy-competition-to-site.yml` | `workflow_run: [Algorithm Competition Refresh, Forward Test Daily, …]` |
| `deploy-findcryptopairs-ftp.yml` | `workflow_run: [Rapid Fire - NOW Scanner]` |
| `deploy-fte-events-json.yml` | `workflow_run: [Scrape events]` |
| `deploy-fte-index.yml` | `workflow_run: [Scrape events]` |
| `pine-generator.yml` | `workflow_run: [ALPHA ENGINE - Live Autonomous Scanner]` |
| `torontoevent-deploy-competition.yml` | `workflow_run: [Algorithm Competition Refresh, …]` |

## Are they actually unsafe? No — and here is the evidence

The real `workflow_run` hazard is checking out **the triggering run's head** (which can be
attacker-controlled via a fork PR) and then executing or pushing that code with default-branch
secrets. Measured across all workflows:

```
grep -rn "workflow_run.head_sha|workflow_run.head_branch|workflow_run.pull_requests" .github/workflows/*.yml
→ no matches
```

None of the 7 reads the triggering run's ref. Every one checks out the default branch, and the only
`workflow_run` field any of them uses is `github.event.workflow_run.conclusion` inside an `if:`
(an expression evaluation, not a shell interpolation). Six of the seven already declare
`permissions: contents: read`; the FTP operations use secrets passed via `env:`, never interpolated
into `run:`. `torontoevent-deploy-competition.yml` additionally guards its blast radius with
`assert_ftp_host.sh`.

**Conclusion: the finding is a pattern match, not an exploitable defect.** It was reported as Medium
confidence by the scanner, which cannot see that the ref is pinned or that no head-ref is read.

## What changed

Cheap structural hardening so the safe behaviour cannot silently regress: an explicit
`ref: ${{ github.event.repository.default_branch }}` on the checkout of the 6 workflows that relied on
the implicit default (deploy-battleground-ftp, deploy-competition-to-site, deploy-findcryptopairs-ftp,
deploy-fte-events-json, pine-generator, torontoevent-deploy-competition).

`deploy-fte-index.yml` already pinned `ref: main` and was left unchanged. `pine-generator.yml` gets an
extra-strong note because it pushes commits — a head-ref checkout there would mean committing on top of
untrusted code.

This is behaviour-preserving for all four trigger types (`push`, `schedule`, `workflow_dispatch`,
`workflow_run` all resolve the repository's default branch to `main`), and it removes the failure mode
where a future edit copies the "check out the triggering run" idiom from a blog post.

## Verification

- `python3 -c "yaml.safe_load(...)"` — all 7 parse.
- `actionlint -shellcheck=` — no native findings for any of the 7.
- shellcheck counts unchanged for all 7 (deploy-competition-to-site 1→1, torontoevent 2→2, rest 0→0).
- Re-ran the `head_sha`/`head_branch` grep after the edit: still no matches.

## Residual

All 7 still fire on `workflow_run`, so zizmor will keep reporting them. That is correct and expected:
the trigger itself is legitimate (deploy after the data-producing workflow finishes), and the finding
cannot be closed without dropping the trigger. The mitigation is the pinned ref, documented above and
in each file.
