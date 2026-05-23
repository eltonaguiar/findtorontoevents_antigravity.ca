import sys,io,os
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
c=open(os.path.join('TORONTOEVENTS_ANTIGRAVITY','MOVIESHOWS2','scroll-fix.js'),encoding='utf-8').read()
idx=c.find('function createSlide')
end=c.find('function addMovieToFeed')
print(c[idx:end])
