# 2026-11-19 — design-debate position, peer cross-check package, capital answer, and a 50-session watcher

**Author:** Buffy (Freebuff), worktree `review-main`
**Type:** documentation + one unattended monitor + three published corrections

## What was asked

1. Check COMS and have peers cross-check my work, giving them a framework, the files, my intent, and
   an honest statement of how close I am to something worth real money — including whether a mutual
   fund is generally good, which one, index ETF vs low-fee index fund, versus penny / sub-$5 stocks.
2. Start the debate about whose design elements are worth keeping in the final design and why; check
   COMS, recent GitHub work (local and remote), and the live `/audit`, `/audit2`, `/audit3`.
3. Set 50 scheduled check-ins at 20-minute intervals, reviewing recent edits, remote GitHub and the
   three live audit surfaces between sessions.

## What was produced

| Artifact | Purpose |
|---|---|
| `reports/PEER_CROSSCHECK_BUFFY_2026-11-19.md` | Three falsifiable claims, file manifest with SHA-1s, six tests, stated biases, honest distance-to-real-money, and the falsifiers that would change my mind |
| `reports/CAPITAL_2000_FUND_VS_ETF_VS_PENNY_2026-11-19.md` | The $2,000 answer: index mutual fund vs index ETF vs active fund vs penny/sub-$5 |
| `reports/DESIGN_DEBATE_BUFFY_POSITION_2026-11-19.md` | Judgments on debate elements 7 and 13, the seven-part TAA promotion bar, new element 20, and one-line keep/cut for all 19 |
| `tools/wakeup_watch_20min.py` | 50 wakeups at 20-minute intervals; records local edits, remote branch tips, live surface state and parity, and COMS inbound |

## Three corrections to my own published work

1. **"0 proven is structurally forced" — WITHDRAWN.** The live `/audit3/audit3_ledger.json`
   (21:02:25Z) has `selection_alpha.available = true`; it was `false` in the 16:42Z build I reviewed.
   G8 runs now, and still returns nothing, so the null is *earned*. This makes the conclusion
   stronger, not weaker. Both documents that carried the old claim were edited with the correction
   noted inline rather than silently.
2. **`lag=1` in `tools/taa_settle_sweep.py` means one *month*, not one day.** That is stricter than a
   monthly-rebalance strategy requires, and it is why my 0/576 result and copilot's lag-1-day
   reproduction (PR #962) appeared to conflict. They differ on lag *and* universe. Under the fair
   convention — month-end close, fill next open — **their 0.82 vs 0.69, −20.9% MDD, −1.9pp CAGR
   passes my pre-registered bar** and I have said so to them directly.
3. **PDT blocks day trading at $2,000 — WRONG.** FINRA Regulatory Notice 26-10 replaced the
   pattern-day-trader rule with intraday margin standards effective 2026-06-04 (phase-in to
   2027-10-20): no $25,000 minimum, no day-trade count. $2,000 is the margin minimum. The legal
   barrier is gone; only the arithmetic remains.

## Live findings made while verifying

- **Two divergent copies of the same ledger are served by the same site.**
  `/audit/data/audit3_ledger.json` = 627,649 B, sha `b0ca1de6…`, `generated_at 18:32:40Z`, 8,613 rows.
  `/audit3/audit3_ledger.json` = 665,028 B, sha `557cb3f1…`, `generated_at 21:02:25Z`, 8,621 rows.
  2h30m and 8 rows apart, and neither page discloses which copy it renders. Provenance cannot detect
  this because both copies are internally consistent — hence the parity assertion below.
- **`/audit3/data/*.json` returns 404** for all three expected filenames; the working paths are
  undocumented. **`/audit2` renders em-dashes** ("Verdicts — —") because its ledger fetch fails.
- **The sleeve layer is not evidence.** `tools/sleeve_reconciliation.py` reports **0/10 sleeves
  verified against audit3 cells, 9/10 single-source**, with CRYPTO sleeve PFs of **155.85, 111.81,
  56.73, 49.37, 33.09** inside a class whose aggregate PF is **0.8383**. A profit factor of 155 means
  the average win is 155× the average loss; that is a grading artefact, not a strategy.

## Security issue flagged (not fixed by me — needs a human rotation)

Commit **`b5f42b39ec1`** (`github-actions[bot]`, 21:08:46Z, branch
`feat/audit-review-organization-2026-11-19`) writes a **plaintext database password into 14 tracked
files and names the value in the commit message**, on a branch pushed to a public repository. The
value is therefore in history; scrubbing the tip does not remove it.

**Recommendation:** treat the credential as compromised and rotate it, then have every consumer read
`os.environ.get('AUDIT_DB_PASS')` with **no default**, failing loudly when unset. I did not and will
not echo the value. This was reported to the fleet over COMS as a rotation item, separate from the
design debate.

## Verification performed

- `python3 -m py_compile tools/wakeup_watch_20min.py` → pass.
- First live run recorded (`reports/wakeups/2026-11-19.jsonl`, run 1/50):
  `parity=DIVERGENT, rows=[8613, 8621]`, all three pages HTTP 200, 12 new COMS messages captured.
- Both live ledger copies fetched independently and hash-compared, twice.
- Live `selection_alpha.available` read from the deployed 21:02Z build, not from the local copy.
- COMS: three sends, all `rc=0` (debate on `mentions/all` + retained to my seat; cross-check retained
  to copilot's seat; security on `mentions/all`).
- Cron armed (`buffy/wakeup-20min-50`, `*/20`, `flock`-guarded) and confirmed present in `crontab -l`.

## Not done / limitations

- **I did not commit or push these files.** The working tree carries other agents' uncommitted work
  (5 dirty tracked files, 25 untracked), and this repo has a documented silent-revert hazard. They
  are written to disk and reported; committing is left to an owner decision.
- **I did not fix the divergent ledger or the `/audit2` fetch failure** — that is deploy/pipeline
  territory owned by others, and my instruction is to reconcile and report, not to edit their paths.
- The watcher is a monitor only: it never edits tracked source. It self-disables after 50 runs.
