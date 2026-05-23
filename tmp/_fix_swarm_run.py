path = 'tools/swarm/swarm_run.py'
content = open(path, encoding='utf-8').read()
old = '            per_strict = bool(em.get("json_strict")) or fleet_json_strict'
new = '            per_strict = em.get("json_strict") if "json_strict" in em else fleet_json_strict'
if old in content:
    content = content.replace(old, new)
    print('replaced')
else:
    print('old not found')
open(path, 'w', encoding='utf-8').write(content)
