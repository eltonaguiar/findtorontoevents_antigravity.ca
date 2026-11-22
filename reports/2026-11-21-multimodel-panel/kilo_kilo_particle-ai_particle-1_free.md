
> code · particle-ai/particle-1:free

$ ls -la /tmp/consult 2>/dev/null | head -50; echo "---"; ls /tmp/consult/reports /tmp/consult/audit_dashboard/data 2>/dev/null
total 124
drwxrwxr-x   2 eaguiar2015 eaguiar2015   4096 Nov 21 09:01 .
drwxrwxrwt 344 root        root        118784 Nov 21 09:01 ..
---

$ find / -name "audit3_ledger.json" -o -name "hypothesis_registry.json" 2>/dev/null | head -20
/home/eaguiar2015/findtorontoevents_antigravity_ca/audit_trail/data/hypothesis_registry.json
/home/eaguiar2015/findtorontoevents_antigravity_ca/reports/hypothesis_registry.json
/home/eaguiar2015/.local/share/kilo/worktree-pool/findtorontoevents-antigravity-ca-ce998ce016c3/candied-ruby/audit_trail/data/hypothesis_registry.json
/home/eaguiar2015/.local/share/kilo/worktree-pool/findtorontoevents-antigravity-ca-ce998ce016c3/candied-ruby/audit_dashboard/data/audit3_ledger.json
/home/eaguiar2015/.local/share/kilo/worktree-pool/findtorontoevents-antigravity-ca-ce998ce016c3/candied-ruby/reports/hypothesis_registry.json
/home/eaguiar2015/fix-db-ghost-rows-and-freshness/reports/hypothesis_registry.json
/home/eaguiar2015/wired-in-research-temp/audit_trail/data/hypothesis_registry.json
/home/eaguiar2015/wired-in-research-temp/reports/hypothesis_registry.json
/home/eaguiar2015/wt-ci/audit_trail/data/hypothesis_registry.json
/home/eaguiar2015/wt-ci/reports/hypothesis_registry.json
/home/eaguiar2015/wired-in-research/audit_trail/data/hypothesis_registry.json
/home/eaguiar2015/wired-in-research/reports/hypothesis_registry.json
/home/eaguiar2015/repo-clean/reports/hypothesis_registry.json
/home/eaguiar2015/wt-reason/audit_trail/data/hypothesis_registry.json
/home/eaguiar2015/wt-reason/reports/hypothesis_registry.json
/home/eaguiar2015/quant-risk-REDACTED/reports/hypothesis_registry.json
/home/eaguiar2015/findtorontoevents_antigravity.ca/.kilo/worktrees/moneyresearch/audit_trail/data/hypothesis_registry.json
/home/eaguiar2015/findtorontoevents_antigravity.ca/.kilo/worktrees/moneyresearch/audit_dashboard/data/audit3_ledger.json
/home/eaguiar2015/findtorontoevents_antigravity.ca/.kilo/worktrees/moneyresearch/reports/hypothesis_registry.json
/home/eaguiar2015/findtorontoevents_antigravity.ca/.kilo/worktrees/vh-hotfix/reports/hypothesis_registry.json

Error: [Particle AI] particle-ai/particle-1:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok
