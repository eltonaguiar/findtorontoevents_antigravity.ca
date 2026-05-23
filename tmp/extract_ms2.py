import re
f=open(r'TORONTOEVENTS_ANTIGRAVITY\MOVIESHOWS2\app.html',encoding='utf-8')
c=f.read()
f.close()
patterns=[('video-card',200,200),('youtube.com/embed',200,200),('toggleMute',300,300),('snap-y',300,300),('innerHeight',300,300),('browse-play-overlay',300,300),('player-',200,200),('info-overlay',200,200),('allMovies',200,200)]
for name,bef,aft in patterns:
    hits=[(max(0,m.start()-bef),min(len(c),m.end()+aft)) for m in re.finditer(re.escape(name),c)]
    print('=== '+name+' === ('+str(len(hits))+' matches)')
    for s,e in hits[:5]:
        print(c[s:e])
        print('---')
