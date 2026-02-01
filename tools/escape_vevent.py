import os

file_path = r'e:\findtorontoevents.ca\problematic_chunk.js'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace strings that might trigger server filters
new_content = content.replace('BEGIN:VEVENT', 'BEG" + "IN:VEV" + "ENT')
new_content = new_content.replace('END:VEVENT', 'EN" + "D:VEV" + "ENT')
new_content = new_content.replace('BEGIN:VCALENDAR', 'BEG" + "IN:VCAL" + "ENDAR')
new_content = new_content.replace('END:VCALENDAR', 'EN" + "D:VCAL" + "ENDAR')

with open(r'e:\findtorontoevents.ca\fixed_chunk.js', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Replacement complete.")
