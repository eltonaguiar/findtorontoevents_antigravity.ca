import re

SQL_FILE = r'C:\Users\zerou\Downloads\ejaguiar1_stocks_apr62026_extract.sql'

with open(SQL_FILE, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read(200 * 1024 * 1024)  # First 200MB

# Find where alpha_picks table structure is defined  
alpha_pos = content.find('CREATE TABLE `alpha_picks`')
print(f'alpha_picks CREATE TABLE at position: {alpha_pos}')

if alpha_pos > 0:
    snippet = content[alpha_pos:alpha_pos+2000]
    print('\n--- Table structure ---')
    print(snippet)

# Find INSERT statements
insert_pos = content.find('INSERT INTO `alpha_picks`')
print(f'\nFirst INSERT at position: {insert_pos}')

if insert_pos > 0:
    snippet = content[insert_pos:insert_pos+1500]
    print('\n--- First INSERT ---')
    print(snippet)
