# overrides/

Approved exceptions to charter rules, consumed by
`.claude/agents/quant-performance-auditor-deep.md`. The fast variant and
the original `quant-performance-auditor` ignore this directory entirely
(CI must be deterministic regardless of who's logged in).

## File format

One YAML file per override, named `<ticket_id>.yaml`. Required fields:

```yaml
ticket_id: PROJ-1234
rule_id: risk:kelly-unproven       # which rule in config/charter_floors.yaml this overrides
expires_at: 2026-06-30              # ISO date; agent refuses overrides past this date
override_reason: |
  Quarterly review (2026-05-05) approved Eighth-Kelly on FOREX during the
  mutate-before-kill protocol per docs/MUTATION_THREE_AXIS_PROTOCOL.md.
  WR is below floor by design (intentional regime stress test).
approver: "@username"
scope:                              # optional — narrows the override
  asset_class: FOREX
  strategy: forex_rsi2_mean_reversion
```

## What overrides do

When a claim's `rule_id` matches an unexpired override AND any `scope`
fields match the claim's context, the claim is recorded as
`verdict: pass` with an `override` block carrying `ticket_id`,
`expires_at`, and `approver`. A `log[]` entry with `outcome: override`
is also written.

## What overrides don't do

- Don't bypass the `INSUFFICIENT_DATA` verdict. If
  `dashboard_data.json` is malformed, no override saves the run.
- Don't bypass the fabrication-check sanity gate. If the agent reports
  file paths that don't exist, the run is marked `hallucination_suspected`
  regardless of any override.
- Don't bypass `range_checks`. A WR of 1.5 is a unit bug, not a
  legitimate exception.
- Don't apply retroactively. An override created today doesn't change
  yesterday's audit log entries.

## Lifecycle

1. PR proposes an override with `ticket_id` referencing the underlying
   issue.
2. PR description must include the link to the approving review (Slack /
   Linear / GH issue) plus the `expires_at` justification.
3. After `expires_at`, the agent refuses the override and emits a claim
   with `rule_id: ci:expired-override`. Either renew the override (new
   PR with new date) or remove the file.

## Audit trail

Every override application is logged in the agent's `log[]` array with
`outcome: override`. The structured log is the audit trail; this README
is documentation only.
