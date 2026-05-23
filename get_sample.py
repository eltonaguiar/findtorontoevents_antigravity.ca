import re

SQL_FILE = r'C:\Users\zerou\Downloads\ejaguiar1_stocks_apr62026_extract.sql'

with open(SQL_FILE, 'r', encoding='utf-8', errors='ignore') as f:
    count = 0
    found = 0
    samples = []
    for line in f:
        count += 1
        if 'INSERT INTO `algorithm_performance`' in line:
            found += 1
            if found > 1:  # Skip the header
                samples.append(f'Line {count}: ' + line[:400])
                if found > 5:
                    break

with open('sample_output.txt', 'w', encoding='utf-8') as f:
    f.write('\n---\n'.join(samples))
    f.write(f"\n\nTotal lines checked: {count}")

print(f"Found {len(samples)} samples")
print(f"Checked {count} lines")
