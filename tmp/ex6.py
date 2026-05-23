import sys,io,os
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
base=os.path.join('TORONTOEVENTS_ANTIGRAVITY','MOVIESHOWS2')
for fn in ['scroll-fix.js','db-connector.js','ui-minimal.js','ms2-enhancer.js']:
    path=os.path.join(base,fn)
    try:
        d=open(path,encoding='utf-8').read()
        print('=== '+fn+' len='+str(len(d)))
        print(d[:3000])
        print()
    except Exception as e:
        print('FAILED '+fn+' '+str(e))
