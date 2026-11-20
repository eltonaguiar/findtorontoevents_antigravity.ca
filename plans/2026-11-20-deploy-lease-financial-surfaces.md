# Deploy lease — financial surfaces (one deployer)

**Status:** in force 2026-11-20, 24h objection window  
**Deployer:** `freebuff` (seat `inbox/gx10-c9b9/findtorontoevents_antigravity-ca/freebuff`)  
**Applies to:** money-facing publishing + statistical gate surfaces only  
**Bus copy:** `notes/deploy-lease-financial-surfaces-20261120-freebuff` (byte-identical body below)

## Why this exists

Three consecutive deploys re-measured each other, and two published claims changed meaning between hourly snapshots (PBO 0.286 -> 0.143 after matrix alignment; PF denominator 6,874 -> 6,788). Two agents writing the same publishing surface in parallel, with nobody rerunning the suite on the combined tree, is sufficient to produce that on its own. The human instruction behind this document is: *stick to one agent to deploy, others provide guidance.*

## Rules

1. One deployer: `freebuff`. Only it merges/pushes a branch touching a gated surface. No "small fix" exceptions.
2. Peers contribute patches, reviews, repros and verdicts — not pushes.
3. Serial, off `origin/main`: one branch, rebase if main moved, full suite on the combined tree, refuse publish on stale base.
4. Every deploy reposts four numbers: test count, `py_compile`, `pf_label_audit` coverage, gate exit code.
5. Claim before edit (`claim/<item>`, exact files). Exact-file conflict blocks; directory overlap warns. Liveness from heartbeat, never a stored claim.
6. Transfer only by retained note naming the new deployer. Silence is consent to the lease, not to a second deployer.
7. Not covered: COMS tooling, scrapers, docs, job board, worktree hygiene.

## Gated surface list

Workflows: `audit-dashboard.yml`, any new anti-overfit/gate workflow.  
Publishing: `audit_trail/dashboard_generator.py`, `audit_dashboard/template.html`, `audit_dashboard/data/*.json`.  
Statistics: `alpha_engine/{money_ready_verdict,audit3_tribunal,anti_overfit_validator,pf_basis,benchmark_closed_ledger,production_scanner}.py`.  
Tools: `tools/{run_anti_overfit_audit,anti_overfit_audit_sidecar,pf_label_audit,crypto_pf_reconcile}.py`.  
Ledger/registry: `reports/hypothesis_registry.json`, and any `reports/*.md` publishing a PF, win-rate, DSR or verdict.

## The three sequenced items

| Item | Owner | Guidance (no push) |
|---|---|---|
| A. Demote the 74/80 strategies below DSR 0.95, label `PROBATION`, keep every row and its n visible | freebuff | copilot-cli-moneyresearch (verdict semantics, PF ceiling 5.0 vs 25.0, invalid_row budget), subq-savant-1-4 (claim plane), gemini-3-pro-preview-coordinator (adversarial) |
| B. Split the anti-overfit gate into its own blocking workflow, **after** A | freebuff | kilo (workflow/concurrency), no concurrent `.github/workflows` edits |
| C. Stress-test the 6 DSR survivors: purged splits, regime split, cost drag, n disclosed | analysis by opencode-beam-free, review by grok-4-7; report merged by freebuff | gemini-3-pro-preview-coordinator |

## Explicit non-goals under this lease

- No financial push without the four checks (rule 4).
- No demote/promote while a class denominator is unmeasured; cost stays `None`, never `0.0`.
- No lowering the DSR threshold to make CI green: measured 0.99 -> 6/80, 0.95 -> 6/80, 0.90 -> 7/80, 0.50 -> 10/80.
- No merging third-party branches into a gated surface; patches with repro + expected exit code instead.

---
