#!/usr/bin/env python
"""Analyze user_id=2's creators from SQL export."""
import re
import json

# Read the SQL file
with open('ejaguiar1_favcreators.sql', 'r', encoding='utf-8') as f:
    content = f.read()

# Find user_id=2's INSERT line - it starts with (2, '[
lines = content.split('\n')
user2_line = None
for line in lines:
    if line.startswith("(2, '["):
        user2_line = line
        break

if not user2_line:
    print("Could not find user_id=2 data")
    exit(1)

# Extract the JSON blob - it's between (2, ' and ', '2026
# Format: (2, '[...json...]', '2026-02-05...')
match = re.match(r"\(2, '(.+)', '(\d{4}-\d{2}-\d{2})", user2_line)
if not match:
    print("Could not parse user_id=2 line")
    print(f"Line starts: {user2_line[:200]}")
    exit(1)

json_str = match.group(1)
# The JSON is escaped for SQL - need to unescape it
# Replace escaped quotes first
json_str = json_str.replace('\\"', '"')
json_str = json_str.replace("\\/", "/")
json_str = json_str.replace("\\'", "'")
json_str = json_str.replace("\\\\", "\\")

try:
    creators = json.loads(json_str)
except json.JSONDecodeError as e:
    print(f"JSON parse error: {e}")
    print(f"JSON starts with: {json_str[:500]}")
    exit(1)

print(f"Total creators for user_id=2: {len(creators)}")
print()
print("Creator names:")
for i, c in enumerate(creators, 1):
    name = c.get('name', '(no name)')
    accounts = c.get('accounts', [])
    platforms = [a.get('platform', '?') for a in accounts]
    print(f"{i:3}. {name} - {', '.join(platforms)}")

# Check for briannasumba
print()
has_brianna = False
for c in creators:
    name = c.get('name', '').lower()
    if 'brianna' in name or 'sumba' in name:
        has_brianna = True
        print(f"Found briannasumba: {c.get('name')}")
        break

if not has_brianna:
    print("briannasumba NOT found in user_id=2's list!")
