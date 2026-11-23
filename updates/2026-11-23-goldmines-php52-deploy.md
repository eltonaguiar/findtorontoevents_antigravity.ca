# Goldmines PHP 5.2 fix — deployed and live-verified

**Date:** 2026-11-23
**Owner:** `copilot-cli-deepseek-flash`
**Scope:** `investments/goldmines/**` (served PHP), `tools/validate_php52.py`, `tests/test_php52_goldmines.py`
**Host:** PHP **5.2.17** at 50webs (FTP only, no shell) → `ftps2.50webs.com`

---

## TL;DR

Two served PHP files were **unparseable** on the production host. They are now
**parse-clean and confirmed by the live host's own parser**. Nothing else about
them works yet: both are blocked on database configuration (todo #5).

| File | Before | After |
|---|---|---|
| `kimi/kimi_goldmine_api.php` | `Parse error: unexpected T_FUNCTION` (line 21) | **parses**; returns valid JSON |
| `antigravity/check_dead_data.php` | `Parse error: unexpected '['` (line 20) | **parses**; runs to line 14 |

The third finding is less comfortable: **the deploy gate that was supposed to catch
this reported "passed: 7 file(s)"** while both files still contained 13 short-array
literals and 6 function-call dereferences. The gate was wrong, and it is now fixed
and regression-tested.

---

## 1. What was broken — three separate layers

PHP 5.2 fails at **parse time**, before a single statement runs. A page can
therefore render perfectly (HTML needs no PHP) while every API call 500s.

**Layer 1 — closures (PHP 5.3+)**

```php
set_error_handler(function($errno, $errstr) {   // T_FUNCTION on PHP 5.2
```

**Layer 2 — function-call array dereferencing (PHP 5.4+)**

```php
$stats['total_picks_tracked'] = (int)$res->fetch_assoc()['c'];   // 6 occurrences
```

**Layer 3 — short array literals (PHP 5.4+)**

```php
$systems = [                    // and 12 more sites, mostly nested/multi-line
    'crypto_winners' => [
```

`check_dead_data.php` additionally used `__DIR__` (PHP 5.3+).

## 2. What changed

**`investments/goldmines/kimi/kimi_goldmine_api.php`** (`8367421b1fde207c`, 27,500 B)

* closure → named function `goldmine_api_error_handler()`
* 2 short array literals → `array(...)`
* all 6 `(int)$res->fetch_assoc()['c']` → new helper `goldmine_api_fetch_count($res)`

**`investments/goldmines/antigravity/check_dead_data.php`** (`011c52609bd7b88d`, 6,455 B)

* `__DIR__` → `dirname(__FILE__)`
* 13 short array literals → `array(...)`

The conversion is **purely structural**: `git diff -U0` shows only
`[` → `array(` and `]` → `)`, 24 substitutions total. Parentheses balance
(52/52), URLs are byte-identical, and index writes such as `$result['status'] = ...`
and `$alerts[] = ...` are untouched.

Line endings: the originals were 100% CRLF, the committed files are LF. PHP is
line-ending agnostic; deploying the exact committed bytes makes
`sha256(repo) == sha256(live)` a checkable invariant, which was verified.

## 3. The gate was wrong (fixed)

`tools/validate_php52.py` shipped this rule for short arrays:

```python
("short array syntax []", re.compile(r"(^|[=\(,\{]\s*)\[[^\]\r\n]*[,\=>][^\]\r\n]*\]"))
```

`[^\]\r\n]*` forbids newlines, so the **entire literal had to sit on one line**.
Multi-line literals — how everybody writes nested config arrays — were invisible.
There was also **no rule at all** for `)['k']` dereferencing.

Result: `PHP 5.2 validation passed: 7 file(s)` for two files that could not parse.

Rewritten to scan with a string/comment-aware tokeniser (`scan_php54`) that:
* tracks the previous significant token, so `[` after `$var` is a subscript
  (legal) while `[` after `=`/`=>`/`,`/`return` is a literal (illegal);
* catches `)` immediately followed by `[` (dereference);
* blanks strings, heredocs/nowdocs and all three comment forms **before**
  matching, so `/findmutualfunds2/portfolio2/api/...` can never look like syntax.

### Verified in both directions

```
$ python3 tools/validate_php52.py investments/goldmines
PHP 5.2 validation passed: 7 file(s)

$ python3 tools/validate_php52.py <ORIGINAL kimi api>
  → 9 issues   (2 short arrays, 6 dereferences, 1 closure)          exit 1

$ python3 tools/validate_php52.py <ORIGINAL check_dead_data>
  → 14 issues  (13 short arrays, 1 __DIR__)                          exit 1
```

`tests/test_php52_goldmines.py` (7 passed) now pins the false-PASS case itself:
a multi-line `<newline>$systems = [` must fail, while
`$a['k'] = 1`, `$b[] = 2` and URL strings must pass.

## 4. Deployment and verification

Live files were **backed up before any upload** (`/tmp/live_kimi_api.php`,
`/tmp/live_check_dead.php`), then uploaded over FTPS with credentials supplied
via curl stdin config so the password never entered `argv`.

Backups confirmed the live files were the unfixed originals (27,155 B with
1 closure), and after upload a **download-back hash comparison matched exactly**
for both files.

The definitive test is the host's own parser:

```
$ curl -s '.../kimi/kimi_goldmine_api.php?action=dashboard'
{"ok":false,"error":"require_once(.../findstocks/portfolio2/api/db_connect.php)
  failed to open stream: No such file or directory"}

$ curl -s '.../antigravity/check_dead_data.php'
Warning: mysqli::mysqli(): (28000/1045): Access denied for user 'root'@'localhost'
  (using password: NO) ... on line 14
Connection failed:
```

Both responses are **runtime** errors. No `Parse error`. The syntax layer is fixed.

## 5. Incident disclosure — I deployed a corrupt file

While converting `check_dead_data.php` I used a first-draft converter that
computed replacement offsets itself. It mispaired brackets and injected a `)`
**inside a string literal** (`portfolio2` → `portfol)o2`), and rewrote index
writes into `$resultarray('status')`. That corrupt version was uploaded and was
live for a few minutes, producing:

```
Fatal error: Can't use function return value in write context ... on line 94
```

It was detected immediately by the live check, the file was restored from the
pre-conversion backup, and the rewrite was redone with a **line-structure rule**
(literals here always open at end-of-line and close at line-start) plus hard
assertions that abort on `$vararray(`, unbalanced parentheses, or a mutilated
URL. Production was never left in a worse state than it started — it was already
unparseable — but the corrupt deploy was my error and is recorded here rather
than smoothed over.

Lesson for the toolchain: **offset arithmetic on source text is the wrong tool.**
Prefer conversions whose correctness is checkable by diff inspection.

## 6. Remaining blockers (not fixed here)

1. **`kimi_goldmine_api.php` include is dead.** It requires
   `findstocks/portfolio2/api/db_connect.php`, which returns **404 on live** and
   does not exist in the repo at that path (only
   `findstocks/kimis_claw/api/db_connect.php` does). Needs either the file
   deployed or the include path corrected, plus real credentials.
2. **`check_dead_data.php` ships template placeholders** —
   `$db_user = 'root'`, `$db_pass = ''`, `$db_name = 'your_database'`. These were
   never filled in. Needs credentials.
3. Both are therefore **todo #5**, which stays blocked.

Also noted: the `.kimi/sessions/.../baseline/` copies of all three kimi PHP files
on the Windows host are **0 bytes** (sha256 of the empty file). That "baseline"
snapshot contains nothing and cannot be reconciled — the Windows `Downloads`
copies were the only substantive source.

## 7. Reproduce

```bash
python3 tools/validate_php52.py investments/goldmines          # expect: passed 7
python3 -m pytest tests/test_php52_goldmines.py -q             # expect: 7 passed
curl -s 'https://findtorontoevents.ca/investments/goldmines/kimi/kimi_goldmine_api.php?action=dashboard'
curl -s 'https://findtorontoevents.ca/investments/goldmines/antigravity/check_dead_data.php'
```

Deploy (credentials read locally, never committed):

```bash
curl -sS --ftp-ssl --insecure -T investments/goldmines/kimi/kimi_goldmine_api.php \
     ftp://ftps2.50webs.com/findtorontoevents.ca/investments/goldmines/kimi/kimi_goldmine_api.php \
     --user "$FTP_USER:$FTP_PASS"
```

---

Infrastructure only. No picks, signals, sizing or capital are affected by this
change, and nothing here is investment advice.
