import sys,io,os
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
c=open(os.path.join('TORONTOEVENTS_ANTIGRAVITY','MOVIESHOWS2','scroll-fix.js'),encoding='utf-8').read()
# Key functions
import re
fns=re.findall(r'function\s+(\w+)',c)
print('ALL FUNCTIONS:',len(fns))
for f in fns:
    print(' -',f)
print()
# Find scrollTo or scrollToSlide
idx=c.find('scrollTo')
print('SCROLL LOGIC:')
print(c[max(0,idx-200):idx+500])
print()
# Find iframe creation
idx2=c.find('iframe')
print('IFRAME CREATION:')
print(c[max(0,idx2-100):idx2+500])
