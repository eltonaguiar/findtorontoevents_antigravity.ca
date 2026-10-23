# Fund strategy explanations and session QA

## What was missing

The Strategy Funds page displayed performance and holdings without a consistent
objective, method, allocation, exit-policy, benchmark or evidence section.
Readers could mistake simulated trading systems for regulated mutual funds,
or interpret a trust tier as proof that a stated objective was achieved.

The user-supplied `file_funds.html` snapshot was byte-identical to this branch's
pre-change page. No duplicate profile implementation was present. Open fund PRs
#759 and #760 address research/accounting rather than this presentation change.
Other agents' broad disclaimer and credential edits were left untouched.

## What changed

`audit_dashboard/funds.html` now calls one shared `renderStrategyProfile()` in
both the system-detail modal and the Fact Sheets tab. The section shows:

- Objective, strategy, allocation/sizing, holding/exit policy, benchmark and risks.
- Publisher-reported evidence assessment, specification source and checked date.
- Expandable plain-English explanation and observed strategy names.
- Exact-match existing editorial descriptions, explicitly distinguished from
  executable rules and independent validation.
- Explicit missing-specification messages rather than inferred TP, SL, horizon,
  allocations or profitability.
- Text escaping and HTTP(S)-only specification links without embedded credentials.

### Data contract

The existing `system.strategies` array of `{name: string, ...}` is used immediately
for observed methods. Exact existing `STRAT_INFO` entries supply editorial
descriptions; fuzzy strategy-name matching is deliberately not used.

An optional `system.strategy_profile` object supports string fields:
`objective`, `strategy`, `allocation`, `exits`, `benchmark`, `risks`,
`verification`, `source_url`, `checked_at`, `eli5`.

**The backend does not currently emit that object.** No backend/payload schema was
changed. On current payloads the method breakdown works, while absent mandate
fields honestly remain "Not supplied." Populating those fields requires a reviewed
source specification; this change does not pretend to have audited every system.
Metadata is labelled publisher-reported, never independent proof.

No scoring, trade gates, fees, price feeds or return calculations were changed.
This is not a new mutual-fund recommendation list.

## Verification

New checks:

- `node tests/test_fund_strategy_profile.js` — passed. Tests supplied/missing/
  malformed metadata, exact-only descriptions, escaped text, safe/unsafe links,
  long strategy lists, modal/fact-sheet callers and syntax of inline page scripts.
- `node tests/test_fund_strategy_profile_browser.js` — passed at 1280px and 390px.
  Chromium executes the actual modal/fact-sheet functions with deterministic
  fixtures; checks expandable explanations, both callers, width and page errors.
  It does not exercise production network feeds or certify financial claims.
- `git -c core.whitespace=cr-at-eol diff --check` — passed. The HTML's existing
  CRLF convention is preserved.

Extended QA across this session's owned worktrees:

| Surface | Exact validation | Result |
|---|---|---|
| FTP repair | `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_ftp_credentials.py -q -p no:cacheprovider` | 21 passed |
| FTP shell | `bash -n tools/deploy_sports_files.sh` | Passed |
| Real FTPS | `python3 tools/ftp_credentials.py --check` | Authenticated and verified site access; no upload |
| Fund durability | `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_fund_durability.py -q -p no:cacheprovider` | 12 passed |
| BTC daily MTM repair | `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_crypto_published_mtm.py -q -p no:cacheprovider` | 14 passed |
| Scorecard / paper monitor | `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_audit_scorecard.py tests/test_ghcopilot_paper_monitor.py -q -p no:cacheprovider` | 54 passed |
| Scorecard UI | `node tests/test_audit_scorecard_ui.js` | 7 passed |
| Dashboard card arithmetic | `node tests/test_card_metrics.js` | 14 passed |
| Existing HC filter | `node tests/test_hc_filter.js` | FAIL: first "v3 PROVEN pick passes all gates" assertion |

The HC test and its implementation are byte-identical to this branch's HEAD.
The failure is pre-existing, not evidence that this UI change altered trading gates.
It remains unresolved; this is not an all-green/full-repository QA claim.

## Cross-agent QA boundaries

Zoo's supplied report says `updates/qa_report.md` contains a 97% disclaimer
inventory. That file and the alleged canonical audit-report path are absent from
this branch snapshot, so the counts were not independently certified.
`KIMI_RISEOFTHECLAW/index.html` does have zero literal "not financial advice"
matches, consistent with Zoo's narrow phrase check. Phrase presence/absence alone
is not a legal-compliance or financial-integrity assessment.

Earlier COMMUNITY notes have dated corrections: the merged table predates
OpenCode's 04:27 fixes. The later Grok scorecard cross-check and fund
promise-versus-delivery report explain those updates; do not interpret the older
snapshot as the newest state.

## Viable next research, not invented winners

1. **Index implementation:** compare net tracking difference, broker availability,
   fund series and total purchase costs. TDB902 is a Canadian mutual-fund lead,
   not a proven best-in-class ranking; RBC availability remains unverified.
2. **Active-manager attribution:** reconcile VPMCX/FCNTX distribution-adjusted
   returns with issuer tables, then compare style-matched rolling windows and
   manager eras. FOCPX still needs an independent replay.
3. **Catalyst-based equity continuation:** the user's BHVN/MLTX/EGBN/POOL/HCSG
   screenshot is selected after the jumps. It cannot establish an early-warning
   edge. Earnings/news timestamp, next executable entry, failed catalysts and
   delisted stocks are required before testing a frozen hypothesis.
4. **Do not rerun failed selectors under new names:** trailing return, trailing
   Sharpe and low-volatility annual fund selection already failed to establish
   durable selection skill in H-141.

No new hypothesis was backtested, no live orders were emitted, and no strategy
was promoted. This change does not fix the independently identified peer
portfolio/monkey-test arithmetic or eliminate their open validation gaps.

## Integration

Changes are isolated on `feat/ghcopilot-fund-strategy-profile`; no production
dashboard generator was run and no other agent's edits were overwritten.
The branch must be integrated before the ordinary audit deployment picks it up.
This QA does not claim all files modified by every agent today were reviewed.
