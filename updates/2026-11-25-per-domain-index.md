# Per-domain index — 50webs account, 2026-11-25

All nine vhosts under `/services/users/z50websp3/ejaguiar1/www/`.

| vhost | files | PHP | .htaccess | kit found | kit now |
|---|---|---|---|---|---|
| tdotevent.ca | 68,896 | 1,368 | 71 | yes | deleted (FTP-verified absent) |
| findtorontoevents.ca | 45,367 | 1,268 | 67 | yes | deleted (FTP-verified absent) |
| friendpair2.50webs.org | 11,064 | 1,632 | 5 | no | n/a |
| torontoeventsvamp.50webs.org | 9,050 | 2 | 7 | yes | deleted (FTP-verified absent) |
| fixwindows.50webs.org | 7,810 | 1,563 | 8 | no | n/a |
| surftorontoevents.50webs.org | 3,474 | 1 | 2 | no | n/a |
| ZZZ_OLD | 1,507 | 286 | 4 | no | n/a |
| mysqlbackup | 140 | 1 | 1 | no | n/a |
| ejaguiar1.50webs.com | 11 | 2 | 1 | yes | deleted (FTP-verified absent) |

Root `.htaccess` on both main vhosts: 1,867 B `aa38aa95979aa1c85e7f23bdc100c204` — no kit rewrite, no deny-from block.

No `.htaccess` anywhere on the account contains `de/index.php`, `##Off to the Mouse they go##`, `auto_prepend_file` or an external redirect; the only WAF-off rule is `favcreators/.htaccess` (`SecRuleRemoveById 1-999999`, 2 paths) and it is on the outstanding list.
