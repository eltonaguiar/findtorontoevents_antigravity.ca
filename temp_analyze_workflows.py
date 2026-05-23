import os
import yaml
import glob
import re

workflow_dir = "E:\\findtorontoevents_antigravity.ca\\.github\\workflows"
active_workflows = []

for file in glob.glob(os.path.join(workflow_dir, "*.yml")):
    with open(file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        
    # check for cron (simple check if 'cron:' is active)
    if re.search(r'^\s*- cron:', content, re.MULTILINE):
        # find what it runs
        scripts = re.findall(r'run:\s*python(?:3)?\s+([^\s]+.py)', content)
        name_match = re.search(r'^name:\s*(.+)$', content, re.MULTILINE)
        name = name_match.group(1).strip() if name_match else os.path.basename(file)
        
        active_workflows.append({
            'file': os.path.basename(file),
            'name': name.replace('"', '').replace("'", ""),
            'scripts': list(set(scripts))
        })

with open('workflow_analysis.txt', 'w', encoding='utf-8') as out:
    out.write(f"Found {len(active_workflows)} active workflows with cron schedules.\n")
    for wf in sorted(active_workflows, key=lambda x: x['name']):
        out.write(f"{wf['name']} ({wf['file']}): {', '.join(wf['scripts']) if wf['scripts'] else 'No python script found'}\n")
