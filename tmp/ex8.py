import sys,io,os,re
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
c=open(os.path.join('TORONTOEVENTS_ANTIGRAVITY','MOVIESHOWS2','scroll-fix.js'),encoding='utf-8').read()
for fname in ['scrollToSlide','createSlide','findScrollContainer','playVideo','setupVideoObserver']:
    pat='function '+fname
    idx=c.find(pat)
    if idx==-1:
        print('NOT FOUND: '+fname)
        continue
    end=min(len(c),idx+1500)
    sep='=== '+fname+' ==='
    print(sep)
    print(c[idx:end])
    print()
