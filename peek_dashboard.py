import json
import os

with open('e:/findtorontoevents_antigravity.ca/audit_dashboard/data/dashboard_data.json', 'r', encoding='utf-8') as f:
    chunk = f.read(5000)
    print(chunk)
