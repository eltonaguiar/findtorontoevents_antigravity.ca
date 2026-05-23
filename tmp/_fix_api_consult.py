path = 'tools/swarm/api_consult.py'
content = open(path, encoding='utf-8').read()
old1 = '    content = data.get("choices", [{}])[0].get("message", {}).get("content", "") or ""'
new1 = '    choices = data.get("choices") or [{}]\n    content = choices[0].get("message", {}).get("content", "") or ""'
old2 = '    content = (data.get("choices", [{}])[0].get("message", {}).get("content") or "")'
new2 = '    choices = data.get("choices") or [{}]\n    content = (choices[0].get("message", {}).get("content") or "")'
if old1 in content:
    content = content.replace(old1, new1)
    print('replaced 1')
else:
    print('old1 not found')
if old2 in content:
    content = content.replace(old2, new2)
    print('replaced 2')
else:
    print('old2 not found')
open(path, 'w', encoding='utf-8').write(content)
