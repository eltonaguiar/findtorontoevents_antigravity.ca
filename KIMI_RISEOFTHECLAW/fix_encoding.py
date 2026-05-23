"""Fix encoding by doing byte-level replacements of all known garbled sequences"""

with open('dashboard_live.html', 'rb') as f:
    raw = f.read()

# Map all garbled byte sequences to correct UTF-8
# Found by examining the raw bytes in the file
byte_fixes = {
    # Em dash: ÔÇö -> —
    b'\xc3\x94\xc3\x87\xc3\xb6': '\u2014'.encode('utf-8'),
    # Em dash alternate
    b'\xc3\x94\xc3\x87\xc3\xa8': '\u2014'.encode('utf-8'),
    # Multiplication sign: ├ù -> ×
    b'\xc3\xa2\xc2\x94\xc2\x9c\xc3\xb9': '\u00d7'.encode('utf-8'),
    b'\xe2\x94\x9c\xc3\xb9': '\u00d7'.encode('utf-8'),
    # Middle dot: ┬À -> ·  
    b'\xe2\x94\xac\xc3\x80': '\u00b7'.encode('utf-8'),
    b'\xc3\xa2\xc2\x94\xc2\xac\xc3\x80': '\u00b7'.encode('utf-8'),
    # Left arrow: ÔåÉ -> ←
    b'\xc3\x94\xc3\xa5\xc3\x89': '\u2190'.encode('utf-8'),
    # Bullet: ÔùÅ -> ●
    b'\xc3\x94\xc3\xb9\xc3\x85': '\u25cf'.encode('utf-8'),
    # Emoji: 🪙 (coin)
    b'\xc2\xad\xc6\x92\xc2\xac\xc3\x96': '\ud83e\ude99'.encode('utf-8'),
    # Emoji: 📊 (chart)
    b'\xc2\xad\xc6\x92\xc3\xb4\xc3\xa8': '\ud83d\udcca'.encode('utf-8'),
    # Emoji: � (green circle)
    b'\xc2\xad\xc6\x92\xc6\x92\xc3\xb3': '\ud83d\udfe2'.encode('utf-8'),
    # Emoji: � (red circle)
    b'\xc2\xad\xc6\x92\xc3\xb6\xc2\xb4': '\ud83d\udd34'.encode('utf-8'),
    # Emoji: � (triangle up)
    b'\xc2\xad\xc6\x92\xc3\xb6\xc2\xba': '\ud83d\udd3a'.encode('utf-8'),
    # Emoji: 📈 (chart up)
    b'\xc2\xad\xc6\x92\xc3\xb4\xc3\xaa': '\ud83d\udcc8'.encode('utf-8'),
    # Emoji: 🐕 (dog)
    b'\xc2\xad\xc6\x92\xc3\x89\xc3\xb2': '\ud83d\udc15'.encode('utf-8'),
    # Emoji: � (skull)
    b'\xc2\xad\xc6\x92\xc5\xb8\xc3\x87': '\ud83d\udc80'.encode('utf-8'),
    # Emoji: 🏆 (trophy)
    b'\xc2\xad\xc6\x92\xc3\x85\xc3\xa5': '\ud83c\udfc6'.encode('utf-8'),
    # Bitcoin symbol: ₿
    b'\xc3\x94\xc5\xb8\xc2\xbf': '\u20bf'.encode('utf-8'),
    # Lightning: ⚡
    b'\xc3\x94\xc3\xba\xc2\xa1': '\u26a1'.encode('utf-8'),
    # &amp; entity fix
    b'\x26amp;': b'&amp;',
}

count = 0
for garbled, correct in byte_fixes.items():
    if garbled in raw:
        n = raw.count(garbled)
        raw = raw.replace(garbled, correct)
        count += n
        print(f'  Fixed {n}x: {garbled[:20]}... -> {correct}')

print(f'\nTotal fixes: {count}')

with open('dashboard_live.html', 'wb') as f:
    f.write(raw)

# Verify by reading back as text
with open('dashboard_live.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Check if any obvious garbled sequences remain
import re
garbled_pattern = re.compile(r'[\xc2\xc3][\x80-\xbf]{1,2}[\xc2\xc3][\x80-\xbf]')
remaining = garbled_pattern.findall(text)
if remaining:
    print(f'Warning: {len(remaining)} potential garbled sequences remain')
    for r in remaining[:5]:
        print(f'  {repr(r)}')
else:
    print('No obvious garbled sequences remain!')

# Show the key lines
lines = text.split('\n')
for i, line in enumerate(lines):
    s = line.strip()
    if any(k in s for k in ['Strategies', 'filter-btn', 'Strategy Arsenal', '<title>']):
        print(f'  L{i+1}: {s[:120]}')
