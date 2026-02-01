import re

file_path = 'next/_next/static/chunks/a2ac3a6616d60872.js'
with open(file_path, 'r', encoding='utf-8', errors='surrogateescape') as f:
    content = f.read()

print(f'File size: {len(content)} characters')

wrong = re.findall(r'href:"/favcreators/"', content)
correct = re.findall(r'href:"/favcreators/#/guest"', content)

print(f'Wrong URL (href:"/favcreators/"): {len(wrong)}')
print(f'Correct URL (href:"/favcreators/#/guest"): {len(correct)}')

if len(wrong) > 0:
    print('ERROR: Still has wrong URLs!')
    for i, match in enumerate(wrong[:3]):
        idx = content.find(match)
        if idx > -1:
            context = content[max(0, idx-50):min(len(content), idx+100)]
            print(f'  Match {i+1} context: ...{context}...')
elif len(correct) > 0:
    print('SUCCESS: File has correct URLs!')
    for i, match in enumerate(correct[:3]):
        idx = content.find(match)
        if idx > -1:
            context = content[max(0, idx-50):min(len(content), idx+100)]
            print(f'  Match {i+1} context: ...{context}...')
else:
    print('WARNING: No favcreators URLs found in file')
