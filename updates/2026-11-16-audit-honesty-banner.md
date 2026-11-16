# Audit banner no longer calls ghosts a pass

What was broken: `audit_dashboard/template.html` said "5/5 checks pass" next to 22,947 ghost rows, quoted retired June PF2.6/PF2.4 sleeves, and labelled Polymarket consensus as Verified Alpha.

What changed: the footer says the ghost-row check fails. The June PF figures are not quoted. The prediction-market panel is labelled shadow, not PROVEN.

How verified: `python3 -m pytest tests/test_audit_truth_claims.py -q`. Live check is `python3 tools/audit_honesty_live_check.py`, which stays red until this branch is on main and `audit-dashboard.yml` deploys.
