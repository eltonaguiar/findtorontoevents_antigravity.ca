---
name: canada-job-search
description: Find live job postings with links (ServiceNow, Salesforce, and any other role) for Toronto / Ontario / fully-remote Canada using the LOCAL Ollama stack. Use when the user asks "find me the latest <role> jobs in Toronto", "fully-remote Canadian <role> jobs", "Salesforce jobs including Toronto on-site", or any variant of job-hunting-by-role-and-location. Aliases - jobsearch, canada-jobs, find-jobs, servicenow-jobs, salesforce-jobs, toronto-jobs.
---

# canada-job-search

Find real, linkable job postings using the **local** Ollama web-search API — $0, no API key, no paid model.

## The one command

```bash
python3 tools/job_search.py --role "ServiceNow Developer" --location "Toronto, ON"
python3 tools/job_search.py --role "ServiceNow Developer" --remote-ca
python3 tools/job_search.py --role "Salesforce Developer" --location "Toronto, ON" --include-remote
python3 tools/job_search.py --role "ServiceNow" --role "Salesforce" --remote-ca --json
```

Useful flags: `--no-llm` (raw table, fastest), `--limit N`, `--extra-query "..."`, `--model <ollama-tag>`.

## Why this works (the mechanism)

The local Ollama daemon exposes a **web-search API**:

```
POST http://localhost:11434/api/experimental/web_search
     {"query": "...", "max_results": 10}
  -> {"results": [{"title","url","content"}, ...]}
```

Note the path is **`/api/experimental/web_search`**. `/api/web_search` returns **404**.
It needs no key — it rides the signed-in Ollama account.

`tools/job_search.py` expands the request into several queries, runs them, dedupes by
URL, ranks (real ATS/board links, Toronto/Canada signals, recency), then optionally has a
local model (default `qwen3.5:35b-a3b`) format the result as a table.

## HARD RULES

1. **Never invent a posting, company, or URL.** Report only what the search returned.
2. **Always include the URL** so the human can verify. Postings expire fast.
3. If nothing is found, say so — do NOT pad the list with guesses.
4. Never present a posting as "verified" unless `--validate` actually confirmed it (that flag fetches every URL live).
5. Prefer official ATS links (workdayjobs, ashbyhq, greenhouse, lever, jobbank.gc.ca)
   over aggregator pages that may be stale.
6. Note the search date — job data rots within days.

## Run it with the venv interpreter

```bash
.venv/bin/python tools/job_search.py ...    # <- ddgs fallback lives in .venv
```

System `python3` works for the Ollama backend (stdlib only) but **cannot** import `ddgs`.

## Search backends (`--search-backend auto|ollama|ddgs`)

`auto` (default) tries each in order and uses the first non-empty result set.

| Backend | Key? | Quality | Notes |
|---|---|---|---|
| `ollama` | no | **best** — returns individual postings *with page content* | `POST localhost:11434/api/experimental/web_search`. **Rate-limits (HTTP 429) under load** — this is what the fallback is for. Auto-retries with 15/30/45s backoff. |
| `ddgs` | no | mixed — mostly aggregator *listing* pages | `pip install ddgs` (already installed in `.venv`). Keyless DuckDuckGo. |

Listing pages (`ziprecruiter.com/Jobs/...`, `/search?q=`, `linkedin.com/jobs/<role>-jobs-<city>`)
are auto **down-ranked** so individual postings sort first. Ad/redirect URLs (`bing.com/aclick`,
`googleadservices`) are dropped outright.

## Other keyless sources worth wiring in

Verified reachable (no API key):

| Source | Endpoint | Gives |
|---|---|---|
| **Ashby** (verified) | `https://api.ashbyhq.com/posting-api/job-board/<company>` | full JSON job board for a company |
| Greenhouse | `https://boards-api.greenhouse.io/v1/boards/<company>/jobs` | JSON |
| Lever | `https://api.lever.co/v0/postings/<company>?mode=json` | JSON |
| RemoteOK | `https://remoteok.com/api` | remote roles, JSON |
| Remotive | `https://remotive.com/api/remote-jobs?search=<term>` | remote roles, JSON |
| Canada Job Bank | `https://www.jobbank.gc.ca/jobsearch/jobsearch?searchstring=X&locationstring=Y` | HTML 200 but JS-rendered — needs bs4/lxml |

Keyed / paid (not configured): Brave Search API, Tavily, Serper, Google Programmable Search.
**SearXNG** (self-hosted metasearch in Docker) is the strongest keyless upgrade — no rate
limits, fully local, aggregates Google/Bing/DDG.

## Validation (`--validate`)

Fetches every URL live and reports:

- `VERIFIED` — HTTP 200 **and** the page text matches the title/company
- `REACHABLE` — 200 but no title match (usually JS-rendered)
- `BLOCKED` — 403/429/999 bot-protection; **cannot** be verified programmatically (LinkedIn, ZipRecruiter)
- `DEAD` — 404/410, the posting is gone
- `ERROR` — anything else

A `DEAD` result means the search engine had a stale index — always run `--validate`
before handing links to a human.

## Scope handling

| User says | Flags |
|---|---|
| "jobs in Toronto" / "Toronto, Ontario" | `--location "Toronto, ON"` |
| "fully-remote Canadian" | `--remote-ca` |
| "Toronto on-site, and remote is fine too" | `--location "Toronto, ON" --include-remote` |
| "anywhere in Canada" | `--location "Canada"` |
| two role families at once | repeat `--role` |

## Output shape

```markdown
## ServiceNow Developer — Toronto, ON
| Job Title | Company | Location | Posted | URL |
```

Then follow with a short note on which look freshest and any that are remote-friendly.

## Prerequisites / troubleshooting

- Ollama must be running: `curl -s localhost:11434/api/version`
- Sanity-check the search itself:
  `curl -s http://localhost:11434/api/experimental/web_search -X POST -H 'Content-Type: application/json' -d '{"query":"test","max_results":3}'`
- Model missing/slow: add `--no-llm` to skip synthesis (search still works).
- Big local models need free memory. If a load fails with
  "requires more system memory than is available", free memory first — vLLM started with
  `--gpu-memory-utilization 0.85` reserves ~103 GB of the 121 GB on the GX10.
- Ollama older than ~0.35 cannot pull the newest tags (e.g. `qwen3.6:*` returns
  HTTP 412 "requires a newer version of Ollama"). `qwen3.5:35b-a3b` works on 0.24.0.

## Related

- `tools/llm_message_sweep.py` — trace which provider served a given message
- `/consult-local`, `/consult-minimax` — local fleet consults
- Memory: `/memories/repo/litellm-proxy-introspection.md`
