import re,sys,io
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
f=open(r'TORONTOEVENTS_ANTIGRAVITY\MOVIESHOWS2\app.html',encoding='utf-8')
c=f.read()
f.close()
patterns=[('bg-gradient',100,400),('bottom-0',50,400),('absolute inset-0',50,300),('poster',100,300),('thumbnail',100,300),('opacity-',50,200),('onclick',100,300),('script',100,400),('__NEXT_DATA__',100,400),('_next/static',100,200)]
for name,bef,aft in patterns:
    hits=[(max(0,m.start()-bef),min(len(c),m.end()+aft)) for m in re.finditer(re.escape(name),c)]
    print('=== '+name+' === ('+str(len(hits))+' matches)')
    for s,e in hits[:2]:
        print(c[s:e])
        print('---')
