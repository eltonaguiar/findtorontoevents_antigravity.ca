import re
f=open(r'TORONTOEVENTS_ANTIGRAVITY\MOVIESHOWS2\app.html',encoding='utf-8')
c=f.read()
f.close()
patterns=[('bg-gradient-to-t',100,400),('absolute bottom-0',100,400),('text-white',50,200),('svg',50,150),('onclick',100,300),('click',100,200),('button',100,300),('image.tmdb',100,300),('_next/static',100,200),('script',100,300)]
for name,bef,aft in patterns:
    hits=[(max(0,m.start()-bef),min(len(c),m.end()+aft)) for m in re.finditer(re.escape(name),c)]
    print('=== '+name+' === ('+str(len(hits))+' matches)')
    for s,e in hits[:3]:
        print(c[s:e])
        print('---')
