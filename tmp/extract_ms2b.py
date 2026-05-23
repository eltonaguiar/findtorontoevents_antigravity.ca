import re
f=open(r'TORONTOEVENTS_ANTIGRAVITY\MOVIESHOWS2\app.html',encoding='utf-8')
c=f.read()
f.close()
patterns=[('data-index',200,300),('snap-center',100,300),('snap-mandatory',200,300),('overflow-y-scroll',200,300),('unmute',200,300),('mute',100,200),('iframe',100,300),('playMovie',200,300),('scrollTo',200,300),('window.inner',200,300)]
for name,bef,aft in patterns:
    hits=[(max(0,m.start()-bef),min(len(c),m.end()+aft)) for m in re.finditer(re.escape(name),c)]
    print('=== '+name+' === ('+str(len(hits))+' matches)')
    for s,e in hits[:3]:
        print(c[s:e])
        print('---')
