with open('add-promos.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the tooltip CSS to match static HTML
# Change: w-64 p-3 with left-0 and inline style
# To: w-72 p-4 with right-0 and proper inline style

old_tooltip = '''<div class="jsx-1b9a23bd3fa6c640 absolute top-full left-0 mt-2 w-64 p-3 bg-[var(--surface-1)] border border-white/10 rounded-lg shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-300 z-50" style="left: auto; right: 0;">'''

new_tooltip = '''<div class="jsx-1b9a23bd3fa6c640 absolute top-full right-0 mt-2 w-72 p-4 bg-[var(--surface-1)] border border-white/10 rounded-lg shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-300 z-50" style="max-width: 300px; line-height: 1.5;">'''

if old_tooltip in content:
    content = content.replace(old_tooltip, new_tooltip)
    with open('add-promos.js', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Fixed tooltip CSS in add-promos.js')
else:
    print('Old tooltip pattern not found, checking for variations...')
    # Try a simpler replacement
    if 'w-64 p-3' in content and 'left-0' in content:
        content = content.replace('w-64 p-3', 'w-72 p-4')
        content = content.replace('left-0', 'right-0')
        # Fix the inline style
        content = content.replace('style="left: auto; right: 0;"', 'style="max-width: 300px; line-height: 1.5;"')
        with open('add-promos.js', 'w', encoding='utf-8') as f:
            f.write(content)
        print('Fixed tooltip CSS (alternative method)')
    else:
        print('Could not find patterns to replace')
