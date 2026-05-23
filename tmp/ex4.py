import sys,io
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
c=open(r'TORONTOEVENTS_ANTIGRAVITY\MOVIESHOWS2\app.html',encoding='utf-8').read()
# Find the top category bar
idx=c.find('Now Playing')
x='NAV BAR AREA'
print(x)
print(c[max(0,idx-500):idx+1000])
print()
# Find where the scroll container starts relative to body
idx2=c.find('overflow-y-scroll')
y='SCROLL CONTAINER CONTEXT'
print(y)
print(c[max(0,idx2-800):idx2+500])
print()
# Find volume-x icon context
idx3=c.find('volume-x')
z='VOLUME BUTTON'
print(z)
print(c[max(0,idx3-200):idx3+200])
