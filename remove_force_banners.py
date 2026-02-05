with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and remove the FORCE BANNERS script
start_marker = '<script>\n(function() {\n  console.log(\'[FORCE BANNERS] Aggressive banner protection loaded\');'
end_marker = '})();\n</script>'

start_idx = content.find(start_marker)
if start_idx > 0:
    # Find the end of this script block
    end_idx = content.find(end_marker, start_idx)
    if end_idx > 0:
        end_idx += len(end_marker)
        # Remove the entire script block
        content = content[:start_idx] + content[end_idx:]
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(content)
        print('Removed FORCE BANNERS script')
    else:
        print('End marker not found')
else:
    print('FORCE BANNERS script not found')
