#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('battleground/data/bundle_babies.db')
cursor = conn.cursor()

# Fix direction_bias values
cursor.execute("UPDATE bundle_babies SET direction_bias = 'both_directions' WHERE direction_bias = 'both'")
conn.commit()

# Verify
cursor.execute('SELECT bundle_id, direction_bias FROM bundle_babies')
print('Updated direction_bias values:')
for row in cursor.fetchall():
    print(f'  {row[0]}: {row[1]}')

conn.close()
print('Fixed!')
