#!/usr/bin/python

from Tkinter import *
from fphxtb import *
import os
import sys

# Issue reset
reset_fphx()

chipid = 1
daq_prog = 'read_DAQ.exe'

data = 0
word = make_fphx_cmd(chipid,21,FPHX_DEFAULT,data)
buf = create_packet_fphx(word)
print 'Send FPHX packet = %s' % hexify_bytes(buf)
write_bytes_to_usb(buf.raw)    

# set the bwsel to 8
regid = 15
data = 1 | 8<<3
word = make_fphx_cmd(chipid,regid,FPHX_WRITE,data)
print 'data = %d 0x%02x' % (data, data)
print 'FPHX command = 0x%x' % word
buf = create_packet_fphx(word)
print 'Send FPHX packet = %s' % hexify_bytes(buf)
write_bytes_to_usb(buf.raw)    

# Enable the readout.  TODO: wrap this up in a nice function in the library
regid = 2 # Digital control
val = 7 # Both output lines, enable RO, global inject enable
cmd = FPHX_WRITE
word = make_fphx_cmd(chipid,regid,cmd,val)
buf = create_packet_fphx(word)
print 'FPHX command = 0x%x' % word
print 'enable_ro: Send FPHX packet = %s' % hexify_bytes(buf)
write_bytes_to_usb(buf.raw)    

##### Example of starting the calibration #####
# First launch the daq program
sys_type = sys.platform
if sys_type == 'win32' : cmd = "start %s" % (daq_prog)
elif sys_type == 'darwin' : cmd = "echo system is darwin"
elif sys_type.count('linux') > 0: cmd = '%s' % (daq_prog)
os.system(cmd)
# Now tell the TB to calibrate
prog_reset_fphx(chipid,FPHX_RESET)
calib_fphx(21)

