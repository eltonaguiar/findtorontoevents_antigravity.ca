import sys,io
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
c=open(r'TORONTOEVENTS_ANTIGRAVITY\MOVIESHOWS2\app.html',encoding='utf-8').read()
idx=c.find(chr(60)+'body')
x='BODY START'
print(x)
print(c[idx:idx+3000])
y='TAIL'
print(y)
print(c[-3000:])
