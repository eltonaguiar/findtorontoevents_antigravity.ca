import re

SQL_FILE = r'C:\Users\zerou\Downloads\ejaguiar1_stocks_apr62026_extract.sql'

with open(SQL_FILE, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read(50000000)  # Read first 50MB
    
# Find all INSERT statements for algorithm_performance
matches = re.findall(r'INSERT INTO `algorithm_performance`.*?VALUES\s+\((.+?)\);', content, re.DOTALL)

print(f"Found {len(matches)} INSERT statements")

if matches:
    for i, match in enumerate(matches[:3]):
        print(f"\n--- Sample {i+1} ---")
        print(match[:500])
