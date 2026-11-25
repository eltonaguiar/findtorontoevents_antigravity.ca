# Workflow lint audit: one real bug fixed, one scare disproven

**Date:** 2026-11-25 · **Scope:** all 379 `.yml` workflows on `main` · **API calls:** 0

Tools, installed locally into `~/.local/bin` (not committed): `actionlint 1.7.7`,
`shellcheck 0.10.0`, `zizmor 1.33.1`.

## Fixed: unquoted `>=` in `pip install` was a shell redirection (SC2261, 32 sites)

`regime-detector.yml` and `worldclass-pipeline.yml` installed dependencies like this:

```yaml
pip install --quiet \
  yfinance>=0.2.30 \
```

Bash treats `>` as a redirection, so that line actually ran

```
pip install --quiet yfinance
```

— the package installed **unpinned**, and bash created a file literally named `=0.2.30` in the
workspace. Reproduced directly:

```
$ bash -x /tmp/redir_test.sh
+ pip install --quiet yfinance
$ ls -la '=0.2.30'
-rw-rw-r-- 1 ... 0 Nov 25 23:16 =0.2.30
```

Both files now quote every specifier (`'yfinance>=0.2.30'`): **32 sites** (11 + 21). Verified after
the change: `SC2261 remaining: 0`, YAML still parses, and repo-wide shellcheck findings drop from
**374 to 342** (exactly the 32 removed). One unrelated `SC2046` warning remains at
`worldclass-pipeline.yml:84` (quote `$(...)`) and is left for the backlog.

## Disproven: `artipacked` (384 findings) is not a credential leak in this repo

`zizmor` flags any job that checkouts with persisted credentials and uploads an artifact. Twenty jobs
here do exactly that with a long-lived PAT (`secrets.GH_PAT || github.token`), which looks alarming
in a public repo. It is not, and I checked before changing anything:

**every one of those 20 jobs uploads a narrow, explicit path** — `trading_results.json`,
`reports/health/`, `genome/data/market/`, `alpha_engine/output/` — and **none can include `.git`**.
An artifact only leaks a token if it contains `.git/config`, which none of them do.

So I did **not** add `persist-credentials: false`. Doing it blindly would be a regression risk:
several of these workflows push later via `.github/scripts/safe_push.sh`, which relies on the
persisted credential. If we want the belt-and-braces version, it has to be per job: set
`persist-credentials: false` **and** pass the token explicitly on the push. That is a refactor with
zero current exposure behind it, so it stays on the backlog rather than in this commit.

## Backlog, measured (not estimated)

| finding | count | priority |
|---|---|---|
| `template-injection` (`${{ github.event.* }}` inside `run:`) | 173 | high — real command-injection class |
| `dangerous-triggers` (`pull_request_target` in `deploy-*-ftp.yml`) | 7 | high |
| `actionlint`: undefined step ids (`steps.monitor-quality`, `validate-thresholds`, `generate-report`) | 4 | high — these gates silently never run |
| `excessive-permissions` | 78 | medium |
| workflows with no top-level `permissions:` | 74 | medium |
| `unpinned-uses` (tag instead of SHA) | 825 | low — needs org-level decision + Dependabot |
| `artipacked` | 384 | low — pattern only, see above |
| `concurrency: queue` flagged as unexpected key | 4 | verify against docs first; may be the linter being older than the platform |
| jobs without `timeout-minutes` | 4 of 418 | trivial |

`zizmor` severity mix overall: High 953, Medium 83, Low 373, Informational 62.

## Repro (zero API calls)

```bash
actionlint .github/workflows/*.yml                                  # 8 native findings
actionlint -shellcheck=shellcheck .github/workflows/*.yml           # 342 (mostly SC2086 info)
zizmor --offline --format json .github/workflows | jq '[.[]|.ident]|group_by(.)|map({k:.[0],n:length})'
python3 tools/gha_web_census.py --health --dormant                  # run state, no REST
```
