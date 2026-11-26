# Local `act` execution results

Every row was actually executed in a container with `catthehacker/ubuntu:act-latest`; the class says how it went.

| Class | Count | Meaning |
|---|---|---|
| PASS | 0 | ran green locally |
| BLOCKED_ENV | 0 | needs a secret / DB / FTP / network the local box cannot supply |
| FAIL | 2 | broke for a reason in our control |
| SKIP_RUNNER | 0 | windows/macos runner, act cannot emulate |
| TIMEOUT | 0 | exceeded the per-workflow timeout |

## Failures worth fixing

- `master-picks-health.yml` — unclassified non-zero exit ([log](reports/act_logs/master-picks-health.yml.log))
- `meme-scanner.yml` — unclassified non-zero exit ([log](reports/act_logs/meme-scanner.yml.log))

## Env-blocked by cause


## Passing locally

