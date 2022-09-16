import base64
import subprocess
import requests
import libsodium

cmd="nix hash file --base32 i4s7b4gabs21d01fdwxxz9lhfgmsdrw8.nar".split(' ')


#useless_cat_call = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
#output, errors = useless_cat_call.communicate()
#useless_cat_call.wait()
#print("out: *"+output.strip() + "*")
#print("err: "+errors)

def getNarinfo(hash):
    url="http://binarycache.vedenemo.dev/"+hash+".narinfo"
    r = requests.get(url)
    return r

def getFingerprint(narinfo):
    splitData=narinfo.text.split("\n")
    storePath=splitData[0].split(': ')[1]
    narHash=splitData[3].split(': ')[1]
    narSize=splitData[4].split(': ')[1]
    refs=splitData[5].split(': ')[1].replace(' ', ',')

    #print (storePath)
    #print (narHash)
    #print (narSize)
    #print (refs)

    return '1;'+storePath+';'+narHash+';'+narSize+';'+refs

def getSignature(narinfo):
    splitData=narinfo.text.split("\n")
    return splitData[7].split(': ')[1].split(':')[1]


h='i4s7b4gabs21d01fdwxxz9lhfgmsdrw8'
narinfo = getNarinfo(h)
finger = getFingerprint(narinfo)
#print (finger)
sig = base64.b64decode(getSignature(narinfo))
print(sig)

pubkey = base64.b64decode('binarycache.vedenemo.dev:Yclq5TKpx2vK7WVugbdP0jpln0/dPHrbUYfsH3UXIps='.split(':')[1])

ret = libsodium.crypto_sign_verify_detached(sig, finger, pubkey)
print (ret)
