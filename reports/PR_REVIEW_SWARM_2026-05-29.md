# Swarm PR Review — 22 open PRs — 2026-05-29

**Reviewer:** Claude Opus 4.7 orchestrator + 22 `pr-reviewer` subagents (one evidence-backed verdict per PR). All sub-reviews self-reported LOW fabrication risk with file:line citations.
**Dominant theme:** main has advanced **341–2,197 commits** beyond most branches. The large majority are **stale, superseded, or conflicting**. Very few are clean merges.

## Decision table

| PR | Title (abbrev) | Verdict | Why / key evidence |
|----|----------------|---------|--------------------|
| **30** | docs: 3-model gap + GHA audit | **MERGE** | Docs-only, +124/-0, verified non-redundant. Minor: note 10→23 model count. |
| **29** | remove fabricated commit hashes from DB Health panel | **MERGE** | 5 cited hashes confirmed absent from all 9,268 commits — real fabrication removed. FTP-deploy after. |
| **19** | widen secret-fallback chains (23 models) | **MERGE after doc fix** | MERGEABLE/CLEAN; canonical keeper vs #24/#25. Fix stale TODO comments (OPENAI/ANTHROPIC keys *are* now set); INCEPTION→TOGETHER fallback is a harmless no-op. |
| **9** | zero CRYPTO confidence weight | **CLOSE (superseded)** | All 3 code blocks already on main verbatim (`git show main:…smart_picks_engine.py`). Doc says "multiplicative"; actually additive. |
| **27** | bump pipeline timeout 15→45 | **CLOSE (superseded)** | Identical change already on main (`aa5ab7781`); main already reads 45. |
| **36** | remove claude_gainer_st carve-outs | **CLOSE (superseded)** | Core fix `1916f62ed` already on main. Two real follow-ups to file fresh: orphaned `_SOURCE_SYSTEM_SCORES["claude_gainer_st"]:15` (+15 for a killed source); no dashboard `_monitor_mode` filter for baby strats. |
| **16** | EAGLE end-to-end quick-wins | **CLOSE — ⚠ DANGEROUS to merge** | All good changes already on main; merging would **REVERT** the FOREX Tier-0 freeze, 9 blacklist entries, 2 FOREX source-pair blocks, Cycle16/17 weights. Do **not** merge. |
| **17** | EAGLE v2 review report | **HOLD** | Docs-only but documents fix `cb5173e68` (at_signal_outcomes 121→2131) **not on main** → dangling audit trail. Land the fix or annotate supersession. |
| **35** | wire AdaptiveKeltnerReversion +2 | **REQUEST_CHANGES** | CONFLICTING; Wire-Up Rule fail (paper-trading.yml DISABLED since 2026-03-12 → no prod caller); KeltnerVWAP (PF1.34/WR42.5%) mislabeled "Forward-Proven" alongside T2; batch3/4 tests use hash-based fake win_prob. Split bundle. |
| **34** | revoke COMMODITY FV exempt + hourly sync | **REQUEST_CHANGES** | Logic correct, but new `audit_data` deploy tag is never invoked by any workflow (dead FTP path) → money_ready_verdict.json won't reach live. 398 behind; rebase. |
| **33** | AI-tournament CI leaderboard + deploy diag | **REQUEST_CHANGES** | `generate_diagnostics.py` invoked in CI but **not committed** to branch; drops `money_ready_verdict.json` deploy entry; regresses "two-table" explainer. |
| **32** | audit Tier-1 drift / data-binding | **REQUEST_CHANGES** | Python clean; one 3-way conflict in pick_funnel.html (main `1ef3093a7` inserted Smart-Picks block at same anchor). Rebase, keep both. |
| **26** | harden API callers (429 backoff) | **REQUEST_CHANGES** | Backoff logic sound + bounded; rebase (main deleted LATEST_PICKS block); add timeout-cap + jitter. |
| **25** | restore full model fleet | **REQUEST_CHANGES → prefer CLOSE** | Superseded (timeout+DB-rebuild already on main); CONFLICTING; stale hardcoded BASE_PRICES; **triple overlap** w/ #19+#24 → close in favor of #19. |
| **24** | bridge 3-model gap + scaling | **REQUEST_CHANGES** | Superseded timeout; stale committed diagnostics JSON; `already_generated()`→always False (23× API cost, no de-dup); overlaps #25/#19. `build_model_diagnostics.py` is the one net-new keeper. |
| **21** | per-class gates (VIX/liquidity) | **REQUEST_CHANGES** | Gates sound + wired, but `ETF_VIX_GATE_ENABLED` env collision (two thresholds), ETF reject-reason copy-pastes EQUITY string, `already_generated()`→False, bundles tournament churn, conflicts w/ #18. |
| **18** | CI VIX gate ordering + GHA bootstrap | **REQUEST_CHANGES** | ⚠ 23,539-line **gitignored** `strategy_performance.json` force-added (history bloat) — drop it. Conflicts w/ #21 on same function. Keep the CI bootstrap. |
| **15** | WON/LOST relabel in mysql_dedup_fix | **REQUEST_CHANGES → prefer CLOSE** | Superseded by live `db_p0_integrity_remediation.py`; writes `WON` but canonical schema is `TP_HIT`; missing `pnl_pct IS NULL` guard; no merge base. |
| **14** | trust_score NULL fallback + backfill | **REQUEST_CHANGES** | JS fallback sound but `trust===0` conflates real-0 vs NULL; MySQL backfill has no pre-update backup; branch carries 5 extra commits incl a separate P0. |
| **13** | kill antigravity_bond + wire 3 bond | **REQUEST_CHANGES** | Kill/wiring at wrong layer — `bond_scanner.py`/`bond-agent.yml` bypass both kill-list and NON_CRYPTO policy; missing elite-score baselines. |
| **11** | wire forex_carry_ppp + widen FOREX SL | **REQUEST_CHANGES** | No-op under `FOREX_HARD_DISABLE=1`; Wire-Up fail (no prod caller); backtest n=13 LOCKED/`production_eligible:false`; widening SL on net-neg class. |
| **10** | gatekeeper leakage-purge + A/B | **REQUEST_CHANGES** | Leakage-purge correct, but `AB_ENABLED` default change is **decoupled** from gatekeeper.py's own hardcoded `'0'` gate → kill-switch doesn't work as described; no merge base; dup cron. |

## Tally
- **MERGE now:** #30, #29 (+ #19 after a 2-line doc fix) → **3**
- **CLOSE (superseded / dangerous):** #9, #27, #36, #16, + prefer-close #25 & #15 → **~6**
- **HOLD (land the code, not just docs):** #17
- **REQUEST_CHANGES (rebase/fix):** #35, #34, #33, #32, #26, #24, #21, #18, #14, #13, #11, #10 → **12**

## Cross-cutting red flags (highest priority)
1. **#16 must NOT be merged** — it silently reverts the FOREX freeze + blacklist hardening now on main.
2. **`already_generated()`→always-False** appears in #21/#24/#25 — would 23× the tournament API spend with no de-dup. Don't let any of those land that hunk.
3. **#18 force-adds a 23.5k-line gitignored data file** — permanent history bloat; strip before any merge.
4. **Triple overlap #19/#24/#25** on the model-coverage gap → keep **#19** (cleanest, MERGEABLE), close the other two.
5. **Dead deploy paths** (#34 `audit_data` tag, #33 dropped `money_ready_verdict` entry) — would silently break the live DISPUTED-CRYPTO banner.

## Recommended action commands (NOT yet executed — peer-owned PRs)
```bash
# clean merges
gh pr merge 30 --squash --delete-branch
gh pr merge 29 --squash --delete-branch   # then: python3 tools/deploy_audit_files.py --only ... (FTP)
# #19 after author fixes the stale OPENAI/ANTHROPIC TODO comments

# close as superseded / unsafe
gh pr close 9  -c "Superseded — changes already on main verbatim."
gh pr close 27 -c "Superseded — identical timeout bump already on main (aa5ab7781)."
gh pr close 36 -c "Core fix already on main (1916f62ed); file follow-ups for _SOURCE_SYSTEM_SCORES + baby-monitor dashboard filter."
gh pr close 16 -c "Superseded; merging would revert FOREX freeze + blacklist hardening. Closing."
gh pr close 25 -c "Superseded + conflicting; consolidating model-coverage on #19."
# (#24 keep build_model_diagnostics.py only via fresh PR; #15 re-file targeting TP_HIT)
```
