#!/usr/bin/env python
"""Compare user_id=2's expected creators (from user's list) vs database."""
import re
import json

# The list the user provided (from their UI screenshot)
expected_creators = [
    "Hasanabi",
    "Stableronaldo", 
    "Jasontheween",
    "Shabellow",
    "Nelkboys",
    "Pokimane",
    "Seherrrizvii",
    "Lofe",
    "Rajneetkk",
    "Jerodtheguyofficial",
    "Saruuuhhhh",
    "Abz",
    "Zherka",
    "Orientgent",
    "A.r.a.moore",
    "Lolalocaaaa",
    "Khadija.mx_",
    "Dantes",
    "Fredbeyer",
    "Zople",
    "Ninja",
    "Nazakanawaki",
    "Nevsrealm",
    "Alkvlogs",
    "Cuffem",
    "Chessur",
    "Demisux",
    "Biancita",
    "Jcelynaa",
    "Honeymoontarot30",
    "Xqc",
    "Loltyler1",
    "333ak.s",
    "Carenview",
    "Baabytrinity",
    "Autsyn",
    "Gabbyvn3",
    "Gillianunrestricted",
    "Pripeepoopoo",
    "Brunitarte",
    "Tony Robbins",
    "Chantellfloress",
    "WTFPreston",
    "Clavicular",
    "The Benji Show",
    "Zarthestar",
    "Adin Ross",
    "Starfireara",
    "Chavcriss",
    "Jubal Fresh",
    "Brooke & Jeffrey",
    "Clip2prankmain",
    "Briannasumba",  # The one user wants to add
]

# Read the SQL file
with open('ejaguiar1_favcreators.sql', 'r', encoding='utf-8') as f:
    content = f.read()

# Find user_id=2's INSERT line
lines = content.split('\n')
user2_line = None
for line in lines:
    if line.startswith("(2, '["):
        user2_line = line
        break

if not user2_line:
    print("ERROR: Could not find user_id=2 data in SQL")
    exit(1)

# Extract the JSON
match = re.match(r"\(2, '(.+)', '(\d{4}-\d{2}-\d{2})", user2_line)
json_str = match.group(1)
# Properly unescape SQL-escaped JSON
json_str = json_str.replace('\\"', '"')
json_str = json_str.replace("\\/", "/")
json_str = json_str.replace("\\'", "'")
json_str = json_str.replace("\\\\", "\\")

creators = json.loads(json_str)
db_names = [c.get('name', '(no name)') for c in creators]

print("=" * 60)
print("COMPARISON: Expected vs Database for user_id=2")
print("=" * 60)
print(f"\nExpected creators (from UI): {len(expected_creators)}")
print(f"Database creators: {len(db_names)}")

# Normalize names for comparison
def normalize(name):
    return name.lower().strip().replace(' ', '').replace('.', '').replace('_', '')

expected_normalized = {normalize(n): n for n in expected_creators}
db_normalized = {normalize(n): n for n in db_names}

# Find missing from database
missing_from_db = []
for norm, original in expected_normalized.items():
    if norm not in db_normalized:
        missing_from_db.append(original)

# Find extra in database
extra_in_db = []
for norm, original in db_normalized.items():
    if norm not in expected_normalized:
        extra_in_db.append(original)

# Find matches
matches = []
for norm, original in expected_normalized.items():
    if norm in db_normalized:
        matches.append((original, db_normalized[norm]))

print(f"\n{'='*60}")
print("MATCHES (in both lists):")
print(f"{'='*60}")
for exp, db in sorted(matches):
    if exp.lower() == db.lower():
        print(f"  [OK] {db}")
    else:
        print(f"  [OK] {exp} -> {db} (name differs)")

if missing_from_db:
    print(f"\n{'='*60}")
    print("MISSING FROM DATABASE (user expects but not in DB):")
    print(f"{'='*60}")
    for name in sorted(missing_from_db):
        print(f"  [MISSING] {name}")

if extra_in_db:
    print(f"\n{'='*60}")
    print("EXTRA IN DATABASE (in DB but user didn't list):")
    print(f"{'='*60}")
    for name in sorted(extra_in_db):
        print(f"  + {name}")

print(f"\n{'='*60}")
print("SUMMARY:")
print(f"{'='*60}")
print(f"  Expected: {len(expected_creators)} creators")
print(f"  In DB:    {len(db_names)} creators")
print(f"  Matching: {len(matches)} creators")
print(f"  Missing:  {len(missing_from_db)} creators")
print(f"  Extra:    {len(extra_in_db)} creators")

# Show all DB creators with their accounts info
print(f"\n{'='*60}")
print("FULL DATABASE LIST FOR user_id=2:")
print(f"{'='*60}")
for i, c in enumerate(creators, 1):
    name = c.get('name', '(no name)')
    accounts = c.get('accounts', [])
    platforms = [a.get('platform', '?') for a in accounts]
    note = c.get('note', '')
    note_str = f' [{note[:30]}...]' if note and len(note) > 30 else (f' [{note}]' if note else '')
    print(f"{i:3}. {name:<25} - {', '.join(platforms)}{note_str}")
