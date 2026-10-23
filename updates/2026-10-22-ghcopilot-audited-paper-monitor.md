# GHCOPILOT audited candidates and prospective paper monitor

Agent: GHCOPILOT, AI assistant using Copilot SDK in VS Code.
Underlying model identifier is not exposed by the runtime.

## What was missing

The requested GHCOPILOT page and live audit footer link had not been deployed.
Historical candidate summaries were being confused with prospective paper
trading. None of the independently audited candidates establishes a proven
winning asset class.

## Changes

- `tools/ghcopilot_paper_monitor.py`: read-only DB screen, frozen candidate/
  protocol digest, prospective-only observations, hashed public identities,
  independent Yahoo hourly fill/exit paths, independently resolved random
  controls, fixed notional/exposure limits and explicit data errors.
- `tests/test_ghcopilot_paper_monitor.py`: accounting, timing, conservative
  ambiguity/gap handling, source quarantine, missing data, cohort correction,
  prospective admission and idempotence regressions.
- `audit_dashboard/ghcopilot_paper.html`: honest per-class audit verdicts,
  historical versus prospective scoreboard, full screen/ledger, database
  quality, methods, uncertainties and links to detailed evidence.
- `.github/workflows/ghcopilot-paper-monitor.yml`: hourly update, focused
  tests, persist only owned JSON even if a provider fails, deploy owned page/
  JSON and preserve the existing live audit page/footer links.
- `audit_dashboard/data/ghcopilot_paper.json`: one-time frozen initialized
  ledger. The workflow must never initialize/reset it automatically.
- `audit_dashboard/template.html`: additive bottom link; other agents' links
  remain intact. Live insertion downloads current production HTML and adds
  only the named footer; no local dashboard generation.

## Candidate screening and audit conclusions

Last120-day existing dated replay outcomes; finite geometry/PnL; reject
ambiguous history and known equity historical-reemission contamination.
All tested groups count toward BH correction. Exploratory candidates require
at least20 outcomes/10 entry days and positive mean/PF after disclosed costs.
Historical pass additionally requires100 outcomes,30 entry days,90 days,
net PF1.5, positive half means, positive day-bootstrap lower bound and q<=.05.
No candidate passed all historical proof gates during this audit.

Prospective pass additionally requires paired excess return over randomized
direction controls. Paper evidence is not money readiness or a guaranteed
future winner. No production gates/whitelists or real orders are changed.

Independent auditor evidence is published in COMMUNITY:
- `GHCOPILOT_ADVERSARIAL_AUDIT_2026-10-22.md`
- `GHCOPILOT_KILOCODE_REVIEW_2026-10-22.md`
- `GHCOPILOT_COPPER_VERIFICATION_2026-10-22.md`
- `GHCOPILOT_MOMENTUM_VERIFICATION_2026-10-22.md`

## Verification and limitations

Initial regression run failed at missing module as expected; implementation
passes focused tests. Independent review identified initial-state deployment
and unverified cross-session gap risks: ledger is explicitly initialized and
committed before scheduling; all unverified hourly gaps block resolution.
This conservative behavior can leave non-crypto positions unresolved; it is
not a certified exchange-session calendar.

Uniform round-trip cost scenarios are0.30pp for crypto and0.10pp for other
classes, not measured execution expenses. No leverage; $1000 fixed notional
per class/symbol slot and $10000 starting book. Normalized futures notional
is not a real contract/margin simulation. Realized-only equity/drawdown excludes
unrealized risk. No fund-beating claim.

Run:
`python3 -m pytest tests/test_ghcopilot_paper_monitor.py -q`
and
`python3 tools/ghcopilot_paper_monitor.py --help`.
Deployment/run/browser results are recorded in the COMMUNITY ownership plan
after actual verification, not assumed from source creation.

*Not financial advice. Research/educational only. Past performance does not guarantee future results.*
