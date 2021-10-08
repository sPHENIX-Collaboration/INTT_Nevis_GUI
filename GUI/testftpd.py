import sys
from pyftpdlib import ftpserver
from ctypes import *
import struct
import os

port = 9900
host = "127.0.0.1"
home_dir = "/home/nobody"

if sys.platform == 'win32':
    home_dir = "C:/"

# write out a dummy response file
f = open("%s/ReadFile.txt" % home_dir,"wb")
print f
b = create_string_buffer(1)
print b
struct.pack_into("B",b,0,21)
print b,b.raw
f.write(b.raw)
f.close()
print os.stat("%s/ReadFile.txt" % home_dir)

authorizer = ftpserver.DummyAuthorizer()
print "add_anon with home dir %s" % home_dir
authorizer.add_anonymous(home_dir,perm=('', 'r','w'))
handler = ftpserver.FTPHandler
handler.authorizer = authorizer
address = (host, port)
ftpd = ftpserver.FTPServer(address, handler)
ftpd.serve_forever()
