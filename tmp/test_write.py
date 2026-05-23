with open('tools/swarm/api_consult.py', 'r', encoding='utf-8') as f:
    content = f.read()
marker = 'content = data.get("choices", [{}])[0]'
print('has old:', marker in content)
content = content.replace(marker, 'CHOICES_FIX')
with open('tools/swarm/api_consult.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('wrote')
