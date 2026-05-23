import base64,sys
f=open(sys.argv[1],"wb")
for line in sys.stdin:
  if line.strip(): f.write(base64.b64decode(line.strip()))
f.close()
print("done")
