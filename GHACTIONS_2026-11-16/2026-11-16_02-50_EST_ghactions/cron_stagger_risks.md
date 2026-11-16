# cron_stagger_risks.md — skipped files, risk flags, plan/rule conflicts

**STAMP:** 2026-11-16_02-50_EST_ghactions
**Scope:** `/tmp/kilo/mdland/.github/workflows/*.yml|.yaml` (active only; `.disabled`/`.retired`/`.draft` excluded)
**Policy applied:** minute offset `M = zlib.crc32(filename) % 60`, alphabetical `+1 mod 60` tie-break within each
cron group (identical old cron string), per `GHACTIONS_2026-11-16/2026-11-15_21-00-33_EST_ghactions/cron_stagger_plan.md`.
Companion file: `cron_stagger_manifest.tsv` (310 modified cron lines).

**Validation conventions used for `old_fires_per_day` / `new_fires_per_day`:**
7-day simulation at minute resolution, window **2026-11-16T00:00Z .. 2026-11-23T00:00Z** (all 7 weekdays covered),
step semantics `N/step` = `N..field-max/step` (verified against robfig/cron `parser.go`:
`// Special handling: "N/step" means "N-max/step"`), DOM/DOW both-restricted uses the Vixie OR-rule.
Fires-per-day = 7-day total / 7 (fractional values expected for weekly/monthly/date-pinned crons, e.g. `0.143` = 1/week).

**Headline counts:** 285 files modified (310 cron lines) · 19 files skipped (17 rule-2 + 2 rule-3 risk) ·
4 files untouched by design (policy no-op) · 359 real cron entries before = after (entry count preserved).

---

## 1. Rule-2 skips — `github.event.schedule` string-compared against a cron literal we would change (17 files, UNTOUCHED)

Changing the cron string would break the branch; the whole file is untouchable.

| file | compared literal(s) (line) | matches cron line | note |
|------|---------------------------|-------------------|------|
| analyst-tracker.yml | `'15 */4 * * *'` (23), `'0 * * * *'` (72) | lines 6, 8 | named-mode dispatcher |
| automated-reporting.yml | `"0 9 * * 1"` (58, shell `==`) | line 8 | |
| backtest-and-deploy.yml | `'0 6 * * *'` (62) | line 5 | plan table row `6  6 * * *` blocked |
| claude-gainer-tracker.yml | `'0 6 * * 0'` (310, `contains(...)`) | line 7 | `contains` counts as string comparison |
| kimi-feb172026-live.yml | `"0 */4 * * *"` (55), `"0 0 * * *"` (57, shell) | lines 7, 8 | plan table rows `7  */2`/`7  */4` blocked |
| live-monitor-refresh.yml | `'0 2 * * 0'` (154) | line 9 | |
| master-automation-scheduler.yml | `'0 * * * *'` (33), `'0 */4 * * *'` (186), `'0 3 * * *'` (220), `'0 0 * * 0'` (340) | lines 6, 8, 10, 12 | plan table rows `9  */4`/`9  *`/`9  3` blocked |
| meme-scanner-v2.yml | `'0 * * * *'` (45, 67), `'*/10 * * * *'` (79), `'0 */3 * * *'` (135, 176) | lines 14, 10, 12 | plan table row `15  * * * *` blocked |
| meme-scanner.yml | `'0 */3 * * *'` (45) | line 11 | plan table row `24  */2 * * *` blocked |
| meta-strategy.yml | `"0 5,11,17,23 * * *"` (63, via captured `CRON="${{ github.event.schedule }}"` at 62) | line 8 | captured-var comparison counts as schedule comparison |
| regime-detector.yml | `'0 14 * * 0'` (73) | line 8 | |
| sec-edgar-fetch.yml | `'0 6 * * 0'` (83) | line 8 | |
| smart-money-tracker.yml | `'0 14 * * 0'` (16 `!=`, 91 `==`, 123 `!=`) | line 8 | `!=` counts as string comparison |
| torontoevent-backtest-and-deploy.yml | `'0 6 * * *'` (53) | line 5 | plan table row `13  6 * * *` blocked |
| torontoevent-backtest-and-deploy-ROOCODE.yml | `'0 6 * * *'` (53) | line 5 | plan table row `19  6 * * *` blocked |
| worldclass-intelligence.yml | `'0 14 * * 0'` (152, 219) | line 8 | |
| worldclass-pipeline.yml | `'0 15 * * 0'` (223) | line 9 | |

## 2. Rule-3 RISK flags — market-close / data-cutoff semantics + new minute within 10 min after 20:00/21:00 UTC weekdays (2 files, UNTOUCHED, for coordinator review)

| file | old cron | would-be new | risk analysis |
|------|----------|--------------|---------------|
| alpha-trend-catcher.yml | `5 0,4,8,12,16,20 * * *` | `1 0,4,8,12,16,20 * * *` | header ties runs to 4H **candle close** (data cutoff). New fires **20:01** UTC daily — within 10 min after 20:00 UTC on weekdays. New minute :01 is **earlier** than old :05 and closer to the 20:00 boundary (1-min post-candle may read unsettled data). |
| populate-alpha-macro-daily.yml | `7 21 * * *` | `1 21 * * *` | header: *"Daily at 21:00 UTC — after US market close (20:00 UTC) data is settled"*. New fires **21:01** UTC — within 10 min after 21:00 UTC (EST close variant) on weekdays. New minute :01 is **earlier** than old :07 and closer to the boundary. |

## 3. Plan vs hard-rule conflicts — **plan loses to rules**

The plan's before→after tables (verbatim target shown) assign final crons to files the hard rules make untouchable.
Hard rules win; files left unchanged:

| plan table | plan final cron | file | why plan loses |
|------------|-----------------|------|----------------|
| `0 */2 * * *` | `24  */2 * * *` | meme-scanner.yml | rule 2 |
| `0 */2 * * *` | `7  */2 * * *` | kimi-feb172026-live.yml | rule 2 |
| `0 */4 * * *` | `7  */4 * * *` | kimi-feb172026-live.yml | rule 2 |
| `0 */4 * * *` | `9  */4 * * *` | master-automation-scheduler.yml | rule 2 |
| `0 * * * *` | `9  * * * *` | master-automation-scheduler.yml | rule 2 |
| `0 * * * *` | `15  * * * *` | meme-scanner-v2.yml | rule 2 |
| `0 * * * *` | `56  * * * *` | analyst-tracker.yml | rule 2 |
| `0 4 * * *` | `50  4 * * *` | secret-scan.yml | file now `secret-scan.yml.disabled` ("disable dead Secret Scan workflow" commit) — active-only scope excludes it |
| `0 6 * * *` | `6  6 * * *` | backtest-and-deploy.yml | rule 2 |
| `0 6 * * *` | `13  6 * * *` | torontoevent-backtest-and-deploy.yml | rule 2 |
| `0 6 * * *` | `19  6 * * *` | torontoevent-backtest-and-deploy-ROOCODE.yml | rule 2 |
| `0 3 * * *` | `9  3 * * *` | master-automation-scheduler.yml | rule 2 |

Also resolved in rules' favor: the plan's impact note "`*/30` (12 files) … remain on their native cadence" is ambiguous vs
STEP-2's explicit transformation `*/30 * * * *` → `M/30 * * * *`. Read as *cadence* preserved (still every 30 min) and
minute-phase stagger applied per the explicit transformation. Fires-per-day verified identical.

## 4. Frequency-preserving deviations from the literal `M/N` transformation (rule 1 wins over the example syntax)

`M/N` (robfig/Vixie semantics `N..59/N`) keeps `*/N`'s fire count **only when `M < N`**. For `M >= N` a literal
`M/30`-style rewrite would silently halve (or worse) the run frequency — a hard-rule-1 violation. Those 9 lines use the
count-preserving wrapped-list form `M,(M+N)%60,...` — the exact form rule 1 prescribes for the equivalent `0,30`
pattern — with count and spacing preserved. Verified fires-equal for all 9.

| file:line | old | new | M |
|-----------|-----|-----|---|
| claudes-test-portfolios.yml:5 | `*/30 * * * *` | `46,16 * * * *` | 46 |
| gainer-predictor.yml:5 | `*/30 * * * *` | `30,0 * * * *` | 30 |
| momentum-catcher.yml:6 | `*/30 * * * *` | `42,12 * * * *` | 42 |
| quan-engine-live.yml:5 | `*/30 * * * *` | `43,13 * * * *` | 43 |
| regime-terminal.yml:5 | `*/30 * * * *` | `36,6 * * * *` | 36 |
| signal-engine.yml:5 | `*/30 * * * *` | `39,9 * * * *` | 39 |
| top-gainers-scan.yml:7 | `*/30 13-19 * * 1-5` | `34,4 13-19 * * 1-5` | 34 |
| sports-data-snapshots.yml:29 | `*/15 * * * *` | `59,14,29,44 * * * *` | 59 |
| tv-paper-tpsl-watchdog.yml:6 | `*/15 * * * *` | `26,41,56,11 * * * *` | 26 |

For `M < N` the literal mandated form is kept (fires-equal verified): actions-failure-guardian.yml `19/30`,
consensus-outcome-tracker.yml `2/30`, multi-asset-scanner.yml `14/30`, swarm-sync-v2.yml `4/30`,
torontoevent-deploy-riseoftheclaw.yml `17/30`, torontoevent-spike-scanner.yml `29/30`.

## 5. Tie-break displacements (`+1 mod 60`, alphabetical within group)

| group | file | base | final | status |
|-------|------|------|-------|--------|
| `0 */2 * * *` | signal_tracking.yml (vs backfill.yml) | 34 | **35** | named in plan — applied |
| `0 4 * * *` | sign-coherence-gate.yml (vs db-backup-email.yml) | 32 | **33** | named in plan — applied |
| `*/30 * * * *` | quan-engine-live.yml (vs momentum-catcher.yml) | 42 | **43** | not in plan (plan snapshot `ae3f4dc` predates this collision); plan's own policy block mandates it |
| `0 2 * * *` | signal-engine.yml (vs refresh-creator-updates.yml) | 39 | **40** | same as above |

Note: the tie-break chain is computed over **all** cron lines in a group (including skipped files' base offsets) so the
result is the plan's deterministic policy verbatim; skipped files simply keep their old crons.

## 6. Reviewed but NOT skipped (judgment notes for the coordinator)

| file | why reviewed | decision |
|------|--------------|----------|
| stocks-daily.yml (**the rule-3 example file**) | `35 21 * * 1-5`, close-tied header | new minute **41** → 21:41 UTC is 41 min after 21:00 and **later** than :35 — outside the 10-min window, not earlier/closer → edited |
| equities-agent.yml | header "close (21:00 UTC = 17:00 ET)" | `0 21` → `14 21` = 21:14 — outside 10-min window → edited |
| commodities-agent.yml | header "except close" | `0 20` → `29 20` = 20:29 — outside window → edited |
| stocks-daily-stocksunify.yml | close-tied header | `40 21` → `32 21` = 21:32 — outside window → edited |
| top-gainers-scan.yml | "Stops before 20:00 UTC to avoid running after 4 PM ET market close" | new `34,4 13-19` fires :04/:34 in hours 13–19 only — never after 20:00 → edited |
| kimi-goldmine-collector.yml | header ties to market **hours** (intraday window), not close/cutoff | `0 */2` → `8 */2` fires 20:08 — in window but no close/cutoff tie → edited (borderline) |
| asterdex-paper-trading.yml | `github.event.schedule == '0 0 * * *'` (187) | literal is **not** one of the file's cron entries (only `5 * * * *`); branch is schedule-dead before and after — not a cron we change → edited |
| signal-recorder.yml | `contains(github.event.schedule, '3 4')` (51/55/59) | literal `'3 4'` is a 2-token fragment, not a cron expression, and matches no cron entry (legacy "4:03 nightly" mode is already dead); edit `48` → `33` cannot affect the branch → edited (judgment call) |

## 7. Policy no-ops and inert comment lines (untouched by design)

| item | detail |
|------|--------|
| alpha-quant-stack.yml:6 | `5,35 * * * *`, M=5 → transformation is identity |
| crypto-winner-scan.yml:8,10 | `0 */6 * * *`, `0 3 * * 0`, M=0 → minute unchanged |
| gate-config-emit.yml:11 | `0 5 * * *`, M=0 → minute unchanged |
| validate-hf-asset-class.yml:30 | `35 6 * * *`, M=35 → identity |
| crypto-winner-scan.yml:6 | `# - cron: '*/15 * * * *'` — commented-out cron, not an entry, left as-is |
| fast-stocks-competition.yml:6 | `#   - cron: "0 14,18 * * 1-5"` — commented-out cron, left as-is |

## 8. Validation results

| check | result |
|-------|--------|
| YAML parse (`yaml.safe_load` over all 355 active `*.yml`) | **PASS** |
| Cron entry count per file (old vs new, all 308 cron-bearing files) | **PASS** — 359 entries before = after |
| Non-minute cron fields unchanged on all 310 modified lines | **PASS** |
| Fires-per-day equality, 7-day minute-resolution sim, 310 modified lines | **PASS** (310/310 equal) |
| Manifest | `cron_stagger_manifest.tsv`, **310 rows** |
