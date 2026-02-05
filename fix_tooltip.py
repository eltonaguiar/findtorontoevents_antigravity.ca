with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the old long text with new shorter text in the JavaScript constant
old_text = "Ever wish you could find one of your favorite creators, or track your creators latest stories/live stream status across multiple platforms? Track TikTok, Twitch, Kick & YouTube in one place so they don't get lost in your feed!"
new_text = "Track your favorite creators across TikTok, Twitch, Kick and YouTube. Never miss their live streams or stories!"

if old_text in content:
    content = content.replace(old_text, new_text)
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Replaced text in index.html')
else:
    print('Text not found')
