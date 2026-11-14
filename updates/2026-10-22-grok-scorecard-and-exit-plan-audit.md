# GROK scorecard and explicit exit-plan audit

## What was broken

The main Crypto/Non-Crypto cards mixed server aggregates, bounded client rows,
post-hoc conviction filters and an "exclude killed" switch. They headlined a
product of overlapping, capped trade returns as if it were a real funded account.
Small samples displayed confident WR, zero/sentinel/batch closes could enter
statistics, and the recent preview obscured real timestamps.

The owned paper page did not show per-observation TP/SL/deadline. A bar label
such as SWING could be mistaken for a complete holding rule. Generic ML scores
and historical targets could be mistaken for calibrated certainty and forecasts.

## Implementation checklist

- [x] Isolate from origin/main on `feat/ghcopilot-grok-scorecard`; do not edit the
  shared checkout or its stashes.
- [x] Cache the public baseline and capture local before screenshots.
- [x] Add deterministic reason-coded artifact screens and exact source grouping.
- [x] Version the published thresholds, hash the rules and write verdict JSON.
- [x] Replace the targeted card render paths and guide with the common scorecard.
- [x] Fail closed on unavailable/mismatched verdicts; no fallback candidate list.
- [x] Display explicit direction, stored entry/TP/SL, gross payoff geometry and
  source holding deadlines; never infer a time stop from a bar timeframe.
- [x] Preserve the frozen experiment; show its existing 48-hour limit.
- [x] Wire final-snapshot verdict generation and JS deployment to all three sites.
- [x] Add targeted Python, Node, browser, deployment-mock and reproducibility tests.
- [x] Review snapshot freshness and full owned-source identity; add regressions.
- [x] Document measured changes, remaining evidence gaps and proposed kills.
- [ ] Merge/deploy: deliberately excluded; the user requested one unmerged PR.

## What changed

- [Rules](../audit/gates.json) transcribe the requested
  [Grok source](https://github.com/eltonaguiar/COMMUNITY/blob/main/GROK_20261022_1855.MD).
  The cached source hash is pinned in the rules, and output carries the rules hash.
- [Builder](../tools/audit_scorecard.py) reads closed rows without DB writes or
  strategy changes. It recomputes LONG/SHORT price PnL, rejects artifacts, groups
  exact source/class/strategy/direction, and discloses every excluded identity.
- [Renderer](../audit_dashboard/audit_scorecard.js) drives the very-top verified
  section, Crypto/Non-Crypto cards and owned-strategy header from that output.
  Historical legacy render functions are retained but have no current entry
  point; unavailable verdicts never call them. Other old dashboard sections are
  not represented as having been migrated or independently certified.
- [Main template](../audit_dashboard/template.html) uses the audited paths.
  The guide now opens the common explanation, not legacy n=5 "PROVEN" criteria.
- [Paper page](../audit_dashboard/ghcopilot_paper.html) shows the shared scorecard,
  its separate frozen experiment, explicit TP/SL and 48-hour expiration.
  Ownership uses full keys; ambiguous source normalization fails closed.
- [Production workflow](../.github/workflows/audit-dashboard.yml) builds verdicts
  from the **final** deployment snapshot after commit/retry generation. JS is
  uploaded to each mirror; `data/*.json` already uploads the verdicts file.
  Missing data/builds fail visibly. Source timestamp matching prevents a stale
  sidecar from borrowing a fresher dashboard's credibility.
- [Monitor deploy](../tools/ghcopilot_paper_monitor.py) also uploads its JS
  dependency, without altering candidate selection, checksum, ledger or rules.
- [CI](../.github/workflows/ci-tests.yml) adds focused guards before the broad
  suite and includes the new producer/rules/renderer in path filters.
- Expandable beginner explanations cover every configured gate, its analogy,
  actual PASS/FAIL/N/A evidence and the gap to a defensible result. The high-level
  summary explicitly says profit and S&P 500/buy-and-hold superiority are not
  established. Historical diagnostic leads remain separate from verified picks.
- Grok's production resolver/DSR prerequisites are in open PR #756, not merged
  at checked origin/main `42beaa794e8`. This PR neither duplicates those repairs
  nor imports their unverified DSR claims. The research report distinguishes
  the proposed five-class experiment queue from tests actually executed.

### Definitions and limits

Only MONEY-READY / CANDIDATE / FAIL are common verdict labels; gate outcomes
are PASS / FAIL / N/A. Missing independent evidence is N/A, not a PASS.
No strategy is promoted from this bounded closed-row snapshot.
Actual costs, portfolio marks, trial matrices and sealed forward proof cannot
be conjured from a self-reported closed ledger.

Scenario round-trip costs from the supplied framework: CRYPTO 0.25 percentage
points, EQUITY/ETF 0.05. Others and mixed non-crypto have no defensible universal
percentage scenario and show unverified net metrics, not zero. These differ
from the separate frozen monitor's 0.30/0.10 experiment costs; its protocol
is intentionally unchanged. Net-scenario W/L and PF share the same basis.

PF intervals use 10,000 fixed-seed **whole UTC entry-day** bootstrap replicates.
Distinct **close** days are a separate column. Undefined/no-loss replicates
remain explicitly undefined, not PF=999 and not silently removed.

Compound Return and MDD remain **unverified**: this input has no audited,
capital-constrained daily MTM/sizing book. A future curve adapter needs its own
audited contract; this release does not certify user-supplied curve booleans.
There is no compound-vs-sum sign badge when compound cannot be established.
Reported-PnL-vs-price disagreements are tracked separately.

Health distinguishes EMPTY, snapshot OK, runtime STALE (>7 days), and reported
BROKEN. Browser age checks include future/missing snapshot dates; stale top
claims are suppressed, and historical tables are explicitly dated/marked.
Endpoint errors accepted through sanitized `endpoint_health` input never echo
raw usernames, hosts, IPs or exception bodies. **This is not a DB-auth repair or
a claim every legacy API was probed successfully.** Fresh public portfolio-page
checks returned HTTP 412 during this session; earlier Access-denied reports are
not silently relabeled healthy. Snapshot health does not certify an API or quote.

## Frozen measurement

Public source: `https://findtorontoevents.ca/audit/data/dashboard_data.json`.
Payload timestamp: **2026-10-22T22:14:47.662743+00:00**.
Input SHA-256:
`b370aab8a252279a93d4848e48bec9b3faaffb712f9d5e1ec4665ecd110bfafc`.

The public slice contains **3,500 of 13,162** declared closed picks, covering
2026-02-21T07:08:50Z to 2026-10-22T21:39:13Z.
**2,398 retained; 1,102 excluded; 181 source/class/strategy/direction groups.**
MONEY-READY=0; CANDIDATE=0 under the strict common proof contract.
No full-history exporter exists in this branch; the cap is prominently disclosed,
not presented as an all-DB scan.

### Before/after cards

Old numbers are captured from the unchanged template with the exact same public
input. The old default view excluded killed sources/strategies and used other
legacy filters; the new view removes artifacts without post-hoc survivor filters.
These are intentionally **different denominators and different cost bases**,
not a claim of "PF uplift" or improved actual trading performance.

| Card | Old n | Old PF | Old "EW compound" | New n | New scenario PF | New funded compound | Excluded |
|---|---:|---:|---:|---:|---:|---|---:|
| Crypto | 1,668 | 1.24 | -93.77% | 1,105 | 0.9104 | unverified | 940 |
| Non-Crypto aggregate | 93 | not shown | not shown | 1,293 | unverified mixed costs | unverified | 162 |
| Equity | 17 | 8.82 | +33.72% | 638 | 1.1872 | unverified | 65 |
| Forex | 51 | 3.88 | +18.45% | 124 | unverified | unverified | 70 |
| Commodity | 7 | 1.56 | +3.25% | 6 | unverified | unverified | 1 |
| Futures | 1 | 0.00 | -0.47% | 1 | unverified | unverified | 0 |
| ETF | 13 | 0.38 | -7.65% | 495 | 1.0411 | unverified | 24 |
| Bond | 4 | 2.87 | +1.06% | 29 | unverified | unverified | 2 |
| Mutual funds / options | absent | absent | absent | 0 | unverified / EMPTY | unverified | 0 |

### Mutually exclusive exclusion counts

Each rejected row receives its first applicable reason, avoiding double-counted
headline exclusions. Counts do not prove the excluded data was fraudulent.

| Class | Reasons |
|---|---|
| CRYPTO | batch-close second 153; <2-minute hold 152; missing entry timestamp 149; overlap 486 |
| EQUITY | batch-close second 18; missing entry timestamp 29; placeholder flat 1; overlap 8; zero exit 9 |
| FOREX | batch-close second 15; <2-minute hold 3; placeholder flat 10; overlap 13; zero exit 29 |
| ETF | batch-close second 14; <2-minute hold 1; missing entry timestamp 1; nonmonotonic timestamp 4; placeholder flat 1; overlap 3 |
| BOND | batch-close second 1; nonmonotonic timestamp 1 |
| COMMODITY | missing entry timestamp 1 |
| FUTURES | none |

Global: 201 batch, 156 short holds, 180 missing entry timestamps,
5 nonmonotonic, 12 placeholder flats, 510 overlap, 38 zero exits.
Sentinel, duplicate-id, minute-identity and wrong-class fixtures are tested even
though those are not the first exclusion reason for any row in this snapshot.
One-at-a-time overlap is per exact source/strategy/symbol book; it is not a
whole-fund exposure simulation or an independence certificate.

## Verification

Run from the repository/worktree root. No generator, trading scanner, retrain,
DB mutation, real order or FTP deployment was run for this unmerged PR.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
  tests/test_audit_scorecard.py tests/test_ghcopilot_paper_monitor.py \
  -q -p no:cacheprovider
node --test tests/test_audit_scorecard_ui.js
node tests/test_card_metrics.js
node tests/test_active_pick_why_justification.js
node tests/audit_scorecard_browser.cjs
python3 tools/audit_scorecard.py --input /path/to/snapshot.json --output /path/to/verdicts.json
git diff --check
```

- Python: 54 passing tests (artifact counts, 19/20 WR, short sign, genuine flats,
  scenario basis, source collisions, explicit clocks, unknown evidence,
  deterministic output and unchanged-ledger mocked deployment).
- Node helpers: 7 passing tests; old dashboard guards: 14 + 18 passing.
- Browser: desktop 1440 and mobile 390, missing/mismatched verdicts, sanitized
  endpoint errors, literal-text rendering, ELI5 expansion, no invented horizon,
  source TP/SL, existing paper deadline, and the real snapshot: passed.
- YAML and embedded production-deploy Python ASTs parsed; modified Python and
  JS syntax checks passed. Same snapshot/rules produce byte-identical output.
- Independent code review found runtime freshness and bare-name owned matching;
  both fixed with regressions. Historical statistics remain explicitly dated,
  not removed simply because a report becomes old.
- Full repository suite / hosted CI not claimed green. No local pandas `ME`
  collection failure occurred in the focused suite; pandas was not bumped.
- Hosted Python 3.11 and 3.12 broad suites subsequently failed collection in
  unchanged `tests/test_combined_book_sleeves.py` at `freq="ME"` with
  `ValueError: Invalid frequency: ME` (run 39872410127). This is the anticipated
  dependency compatibility issue, not a focused scorecard failure. No pandas
  bump or unrelated test rewrite was made. Hosted Gitleaks and new-addition
  secret checks passed.
- Secret-shaped-string and exact private-key comparisons run before publishing;
  no new credential is included in the code, reports, screenshots or PR body.

Screenshots: [before](evidence/grok-before-desktop.png),
[after](evidence/grok-after-desktop.png),
[after card detail](evidence/grok-after-cards.png),
[mobile](evidence/grok-after-mobile.png).
The raw 25MB input and generated verdict JSON are retained as session evidence,
not committed as another large generated dashboard blob.

## Proposed kills

**None.** No strategy blocklist, position size or live trading policy was changed.
Investigate the spectacular generic crypto subset; independently reproduce the
stock/ETF breakout lead; repair feed and execution evidence before promotion.
See [the algorithm/horizon research](../reports/GHCOPILOT_EXECUTION_AND_ALGORITHM_REVIEW_2026-10-22.md)
for symbol-specific stored plans, cross-agent critiques and ML limitations.
