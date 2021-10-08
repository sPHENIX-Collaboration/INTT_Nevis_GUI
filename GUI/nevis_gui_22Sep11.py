#!/usr/bin/python

from Tkinter import *
import tkFileDialog
import tkMessageBox
import struct
from ctypes import * #create_string_buffer
import sys
import os
from fphxtb import *
import time
from datetime import datetime
from datetime import timedelta
import socket
import Tix
import ConfigParser
import comm_panel
import random

"""
Info by Fredrik Lundh:
This module implements a validating version of the Tkinter Entry widget.
It uses the textvariable option to attach a StringVar to the widget,
and uses the variable trace function to keep track of what's going on (in real time, as the user types the input).
To specify how validation is to be done, override the validate method.
Note that the constructor takes a parent widget, and also allows you to use the value option to specify the initial contents.
All other options are passed on to the Entry widget itself.
"""
class ValidatingEntry(Entry):
    # base class for validating entry widgets
    def __init__(self, master, value="", extra_cb='', **kw):
        apply(Entry.__init__, (self, master), kw)
        self.__value = value
        self.__variable = StringVar()
        self.__variable.set(value)
        if extra_cb != '': self.__variable.trace("w", extra_cb) # add the extra callback first, so it gets called second.
        self.__variable.trace("w", self.__callback)
        self.config(textvariable=self.__variable)
        self.results = StringVar()
        if self.__value is None: self.results.set(None)
        else:
                self.results.set(self.__value)

    def __callback(self, *dummy):
        value = self.__variable.get()
        #print 'calling __callback, value =', value
        newvalue = self.validate(value)
        if newvalue is None:
            self.__variable.set(self.__value)
        elif newvalue != value:
            self.__value = newvalue
            self.__variable.set(newvalue)
        else:
            self.__value = value

    def validate(self, value):
        # override: return value, new value, or None if invalid
        self.results.set(value)
        return value

    def getresults(self, value):
        # override: return value, or chopped value in the case of ChopLengthEntry
        return self.results.get()

    def add_callback(self,callback):
        print 'before calling trace'
        print self.__variable.trace_vinfo()
        self.__variable.trace("w",callback)
        print 'after calling trace'
        print self.__variable.trace_vinfo()
        return

class ChipIdEntry(ValidatingEntry):
    def validate(self,value):
        try:
            if value:
                v = int(value)
                #print 'v = ', v
                if v>=0 and v<32:
                    self.results.set(value)
                else:
                    value = None
                    self.results.set(value)
            return value
        except ValueError:
            print 'Caught ValueError'
            return None

# Data directory
data_dir = "C:/data"

# Default chip id
wild_chip_id = 21
chip_id = 0

# Wild register id
wild_reg = 21

# The name of the DAQ program to launch when reading data
daq_program = "Debug/read_DAQ.exe"
daq_read = "Debug/read_DAQ.exe"

# global paramters describing the state of the run
global runnumber
global filename
global beam_species
global beam_energy
global starttime
global endtime

fem_addr_const = 15
fem_lvl1_delay_const = 5
pulse_module_const = 0
pulse_wedge_const = 0

global stop_daq_handler
stop_daq_handler = None

# Global socket for controlling comm to the daq program
global sock
sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)

# Global name of the configuration file
global configfname
configfname = None

# Description strings for the register panel.  split_vals is a per-register flag
# indicating if the register value actually represents two things.
split_vals = [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0 ]

descript = [ 'Mask', 'Dig Ctrl', 'Vref', 'DAC0', 'DAC1', 'DAC2', 'DAC3', 'DAC4', 'DAC5', 'DAC6', 'DAC7',
             'N1Sel <3:0>', 'FB1Sel <3:0>', 'P3Sel <1:0>', 'GSel <2:0>', 'P1Sel <2:0>', 'LVDS Current', 'Resets' ]

descript2 = [ '', '', '', '', '', '', '', '', '', '', '', 'N2Sel <7:4>', 'LeakSel <7:4>', 'P2Sel <7:4>', 'BWSel <7:3>',
              'InjSel <5:3>', '', '', '', '' ]

# Comparison function for sorting chip ids, that forces 21 to always appear first
def chip_cmp(x,y):
    if x == 21: return -1
    if y == 21: return 1
    else: return x-y

# Comparison function for sorting side ids, that forces 15 to always appear first
def side_cmp(x,y):
    if x == 15: return -1
    if y == 15: return 1
    else: return x-y

# Comparison function for sorting module ids, that forces 15 to always appear first
def module_cmp(x,y):
    if x == 15: return -1
    if y == 15: return 1
    else: return x-y

# Compose and write a random max-length packet to the FEM controller
def sendrndmhex():
    datalength = int(0xFFFF)- 3  # 3 for address packets and end byte (FF)
    databuf = create_string_buffer(datalength)

    offset = 0
    # random data, max length
    for i in range(0,datalength):
        val = int(255*random.random())
        struct.pack_into("B",databuf,offset,val)
        offset += 1
        
    cmd = 0x03
    wedgeaddr = 0xFF # override user: Write to all wedgeaddr for now.
    femaddr = 0x0F # override user: Write to 0x0Ffor now  
    buf = create_packet(cmd,databuf.raw,wedgeaddr,femaddr)        
    write_bytes_to_target(buf.raw,comm_panel.getTarget())

    print 'Sending random max-length packet to FEM controller...'
    return
    
# Compose and write a reset packet to the Spartan board
def send_reset(regpanels):
    for i in range(0,len(regpanels)):
        if regpanels[i].get_module_enable(): regpanels[i].send_reset()
        else: print 'send_reset: Module %d not enabled, skipping' % regpanels[i].get_moduleid()
    return

def send_fpga_reset():
    femaddr = None
    if use_roc.get() == 2: femaddr = femaddr_var.get()
    write_fpga_reset(0xFF, femaddr,comm_panel.getTarget())
    return

def send_init(regpanels):
    for i in range(0,len(regpanels)):
        if regpanels[i].get_module_enable(): regpanels[i].send_init()
        else: print 'send_init: Module %d not enabled, skipping' % regpanels[i].get_moduleid()
    return

def send_fo_sync():
    femaddr = None
    if use_roc.get() == 2: femaddr = femaddr_var.get()
    write_fo_sync(0xFF, femaddr,comm_panel.getTarget())
    return

def send_fem_lvl1_delay(delay):
    femaddr = None
    if use_roc.get() == 2: femaddr = femaddr_var.get()
    write_fem_lvl1_delay(delay, 0xFF, femaddr,comm_panel.getTarget())
    return

def send_bco_start():
    femaddr = None
    if use_roc.get() == 2: femaddr = femaddr_var.get()
    write_bco_start(0xFF, femaddr,comm_panel.getTarget())
    return


# Compose and write a calib packet to the Spartan board.  This only
# tells the fpga to start the sequence.  The user needs to start the
# daq program separately.  We issue one calib command for the entire DAQ.
# Otherwise we run into timing offsets between modules!
def send_calib() :
    wedgeaddr = None
    if use_roc.get(): wedgeaddr = 0xFF
    femaddr = None
    if use_roc.get() == 2: femaddr = femaddr_var.get()
    calib_fphx(use_roc.get(),femaddr,comm_panel.getTarget())
    return

def start_daq_prog(regpanels):
    if printData.get() == 0:
        printFlag = ''
    else:
        printFlag = '-p'
    if use_roc.get():
        roc_flag = '-r'
    else:
        roc_flag = ''
    sys_type = sys.platform
    runno = get_runnumber()
    runnumber.set(str(runno))
    now = datetime.now()
    filename.set("%s/fphx_raw_%s_%d.dat" % (data_dir,now.strftime("%Y%m%d-%H%M"),runno))
    print filename.get()
    # update the database
    updatedb(regpanels)
    # Launch the daq program
    if sys_type == 'win32' :
        cmd = 'start %s %s %s -e %d -s %d -f %s -v %d' % (daq_prog.get(), printFlag, roc_flag, int(num_events.get()),
                                                          int(sample_MHz_var.get()),filename.get(),int(chipVersions.get()))
    elif sys_type == 'darwin' : cmd = "echo system is darwin"
    elif sys_type.count('linux') > 0: cmd = "echo system is linux"
    print 'cmdline: %s ' % (cmd)
    os.system(cmd)
    open_socket(regpanels)
    try:
        hours, mins, secs = duration_var.get().split(":")
        duration = timedelta(hours=int(hours),minutes=int(mins),seconds=int(secs))
        if duration.seconds > 0:
            print "Stop DAQ after %d millisec\n" % (duration.seconds*1000)
            stop_daq_handler = master.after(duration.seconds*1000,stop_daq_prog)
    except:
        pass
    return

def stop_daq_prog():
    # TODO: send update to DB with the end-run time
    print "Stopping the DAQ by closing the socket"
    if stop_daq_handler != None: master.after_cancel(stop_daq_handler)
    close_socket()

def global_start_daq_prog():
	send_fo_sync()
	send_fpga_reset()
	time.sleep(2)
	#send_fo_sync()
	send_reset(regpanels)
	send_init(regpanels)
	send_enable_ro(regpanels)
	send_latch()
	send_latch()
	send_latch()
	send_fem_lvl1_delay(int(fem_lvl1_delay_var.get()))
	send_pulse_module(int(pulse_module_var.get()),int(pulse_wedge_var.get()), f(int(femaddr_var.get())))
	start_daq_prog(regpanels)
	send_bco_start()
	send_calib()

def browse_daq_prog(progvar):
    exe_fname = tkFileDialog.askopenfilename( filetypes=[('Executable Files','*.exe'), ('All Files', '*')],
                                             initialfile=daq_program, defaultextension='exe' )
    if ( exe_fname != '' ):
        progvar.set(exe_fname)
    return

def browse_packet_file(packetfile):
    fname = tkFileDialog.askopenfilename( filetypes=[('Packet Files','*.dat'), ('All Files', '*')],
                                          initialfile="", defaultextension='dat' )
    if ( fname != '' ):
        packetfile.set(fname)
    return

# Trace callback for the IntVar representing the print state of the daq program
# Sets new text for the button as well as toggling the colors.
def print_data(b,*args):
    if printData.get() == 1:
        printDataText.set('Print on')
        b.config(fg='black',bg='green')
    elif printData.get() == 0:
        printDataText.set('Print off')
        b.config(fg='white',bg='red')

def send_enable_ro(regpanels):
    for i in range(0,len(regpanels)):
        if regpanels[i].get_module_enable(): regpanels[i].send_enable_ro()
        else: print 'send_enable_ro: Module %d disabled, skipping' % regpanels[i].get_moduleid()
    return

def send_disable_ro(regpanels):
    for i in range(0,len(regpanels)):
        if regpanels[i].get_module_enable(): regpanels[i].send_disable_ro()
        else: print 'send_disable_ro: Module %d disabled, skipping' % regpanels[i].get_moduleid()
    return

def send_core_reset(regpanels):
    for i in range(0,len(regpanels)):
        if regpanels[i].get_module_enable(): regpanels[i].send_core_reset()
        else: print 'send_core_reset: Module %d disabled, skipping' % regpanels[i].get_moduleid()
    return

def send_bco_reset(regpanels):
    wedgeaddr = None
    if use_roc.get(): wedgeaddr = 0xFF
    femaddr = None
    if use_roc.get() == 2: femaddr = femaddr_var.get()
    print "send_bco_reset, chipid",wild_chip_id,"wedgeaddr",wedgeaddr,"femaddr",femaddr
    prog_reset_fphx(wild_chip_id,FPHX_RESET,wedgeaddr,femaddr,comm_panel.getTarget())
    #for i in range(0,len(regpanels)):
    #    if regpanels[i].get_module_enable(): regpanels[i].send_bco_reset()
    #    else: print 'send_bco_reset: Module %d disabled, skipping' % regpanels[i].get_moduleid()
    return

# Tell the FPGAs to send a pulse.  We include the "optional" wedge address,
# though I am not 100% sure the pulses are segmented that way.  
def send_pulse(amp,wedgeaddr,femaddr):
    #wedgeaddr = None
    #if use_roc.get(): wedgeaddr = 0xFF
    write_pulse_amp(amp,wedgeaddr,femaddr,comm_panel.getTarget())
    write_pulse(wedgeaddr,femaddr,comm_panel.getTarget())

def send_pulse_module(module,wedge,femaddr):
    #wedgeaddr = None
    if use_roc.get(): wedgeaddr = 0xFF
    write_pulse_module(module,wedge,wedgeaddr,femaddr,comm_panel.getTarget())
    
def send_latch():
    femaddr = None
    if use_roc.get() == 2: femaddr = femaddr_var.get()
    write_latch(0xFF, femaddr, comm_panel.getTarget())
    return

def send_file(fname):
    print 'open file'
    f = open(fname.get(),"rb")
    print 'read file'
    buf = f.read()
    print 'write to usb'
    write_bytes_to_target(buf,comm_panel.getTarget())
    return

def updatedb(regpanels):
    global use_db
    fname = os.path.basename(filename.get())
    runno = int(runnumber.get())
    species = beam_species.get()
    starttime = int(time.time()) # it's only approximate anyway
    endtime = starttime
    energy = float(beam_energy.get())
    temp = float(23)
    humid = float(80)
    chipids = []
    masks = []
    values = []
    for i, panel in enumerate(regpanels):
        if panel.get_module_enable():
            # Loop over the chip ids and get the values
            print 'Module %d' % (panel.get_moduleid())
            #packed_chipids = panel.get_enabled_chipids()
            #for id in (packed_chipids): chipids.append(id)
            configs = panel.get_config_lists()
            mod_chipids = map(lambda x: x[0],configs)
            mod_masks = map(lambda x: x[1],configs)
            mod_values = map(lambda x: x[2],configs) 
            print configs
            print 'chipids=',mod_chipids
            print 'masks=',mod_masks
            print 'regvals=',mod_values
            chipids += mod_chipids
            masks += mod_masks
            values += mod_values
    if use_db.get():
        insertdb(runno,starttime,endtime,fname,species,energy,temp,humid,chipids,masks,values)
    return

def open_socket(regpanels):
    global sock
    host = "localhost"
    port = 9000
    # Start from a known state.  Then connect to the listening port.
    # TODO: Consider having the GUI act as server; the socket could be opened
    # and setup before the DAQ subprocess is started, thereby removing any potential
    # race condition.
    if sock is not None: sock.close()
    sock = None
    sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    print "Connecting to %s:%d" % (host,port)
    try:
        time.sleep(2)
        sock.connect((host,port))
    except Exception, e:
        print "Failed to connect to %s:%d. Exception type is %s" % (host,port,`e`)
        sock = None
        return

    # Here we construct the record to be written to the socket.  It consists of:
    #
    #  runnumber  : 32 bits
    #  chip id    : 16        \
    #  mask 0     : 16         \
    #   ...                    |
    #  mask 7     : 16         +> repeat for each required chip id (variable # of ids)
    #  reg 2      : 8          |
    #   ...                    /
    #  reg 17     : 8         /
    #  Padding    : variable, in order to have record with multiple of 32-bit words
    #
    # The actual packet written to the socket also includes an extra
    # word at the start indicating how many words the rest of the packet contains.
    #
    # The chip id is actually packed to include both wedge address and 5-bit FPHX id:
    #
    #      bits 15 - 13 : unused
    #      bits 12 -  5 : wedgeaddr, 4 bits Side Id, 4 bits Module number
    #      bits  4 -  0 : Chip Id
    #
    # All bytes are packed in network order (big-endian)
    #

    runno = int(runnumber.get())
    chip_configs = []
    for i, panel in enumerate(regpanels):
        if panel.get_module_enable():
            configs = panel.get_config_lists()
            print 'Module %d %s' % (panel.get_moduleid(),configs)
            chip_configs += configs

    print chip_configs

    # Byte length of one configuration is chip + 8 masks + 16 register values
    conf_length = 2 + 8*2 + 16

    # Data byte length is num of configs times config length
    length = len(chip_configs)*conf_length

    # Buffer byte length is length + runnum + data
    total_bytes = 4 + 4 + length
    rem = total_bytes % 4
    #print 'total_bytes,rem = ',total_bytes,rem
    if rem != 0: total_bytes += 4 - rem
    #print 'new total_bytes = ', total_bytes

    buf = create_string_buffer(total_bytes)

    offset = 0
    struct.pack_into("I",buf,offset,total_bytes/4-1) # Length of data payload in 32-bit words, excluding this integer
    offset += 4
    struct.pack_into("I",buf,offset,runno)
    offset += 4

    for i, conf in enumerate(chip_configs):
        struct.pack_into("H",buf,offset,conf[0])
        offset += 2
        struct.pack_into("8H",buf,offset,*conf[1])
        offset += 8*2; # just packed 8 shorts
        struct.pack_into("16B",buf,offset,*conf[2])
        offset += 16 # just packed 16 bytes
        
    # Pack any remaining pad bytes with zeros
    fmt = "%dB" % rem
    padding = [0 for i in range(rem)]
    #print fmt, buf, offset, padding
    struct.pack_into(fmt,buf,offset,*padding)

    print "Writing %d bytes to socket" % sizeof(buf)
    sock.send(buf.raw)
    print "Wrote %d bytes to socket" % sizeof(buf)
    return

def close_socket():
    global sock
    if sock is None:
        print "ERROR: Socket not open, bailing"
        return
    print "Closing socket"
    runno = int(runnumber.get())
    endtime = int(time.time()) # it's only approximate anyway
    try:
        #updatedb_endtime(runno,endtime)
        pass
    except:
        pass
    sock.close()
    sock = None
    return
    
# For debugging purposes, print out the contents of the ChipConfigs
def print_configs(*args):
    for imod in range(0,len(chipconfigs)):
        for i in range(0,len(chipconfigs[imod])):
            chipconfigs[imod][i].dump()

def enable_module(i, name, index, mode):
    #print "callback called with name=%r, index=%r, mode=%r, val=%r" % (name, index, mode, i)
    print " module_enables[%d] = %d" % (i,module_enables[i].get())
    if module_enables[i].get() == 1:
        regpanels[i].set_module_enable(1)
    else:
        regpanels[i].set_module_enable(0)
    return

def save_config(fname):
    if fname is None:
        fname = tkFileDialog.asksaveasfilename( filetypes=[('Config Files','*.ini'), ('All Files', '*')],
                                                initialfile="", defaultextension='ini' )
    if fname == '':
        print 'save_config: operation cancelled'
        return
        
    global configfname
    configfname = fname
    if configfname is None: configfname = "teststand.ini"

    config = ConfigParser.ConfigParser()
    if config.has_section("Global") == False:
        config.add_section("Global")
    config.set('Global','Module Ids'," ".join([ "%d" % (panel.get_moduleid()) for panel in (regpanels) ]))
    
    config.set('Global','teststand',(lambda: "ROC" if use_roc.get() else "Spartan3")())
    config.set('Global','Beam Species',beam_species.get())
    config.set('Global','Beam Energy',beam_energy.get())
    config.set('Global','DAQ program',daq_prog.get())
    config.set('Global','DAQ sample rate',sample_MHz_var.get())
    config.set('Global','Pulser Amp',pulse_amp.get())
    config.set('Global','Number of Pulses',num_pulses.get())
    config.set('Global','Pulse Interval',bco_spacing.get())

    for panel in (regpanels):
        moduleid = panel.get_moduleid()
        section = "Module %d" % moduleid
        print "Add section %s" % section
        config.add_section(section)
        enable = panel.get_module_enable()
        config.set(section,"enable",enable)
        side_enable = panel.get_side_enable()
        config.set(section,"active side",side_enable)
        #chipconfs = panel.get_config_lists()
        #print chipconfs
        
    print "Writing file %s" % configfname
    configfile = open(configfname, 'wb')
    if configfile: config.write(configfile)

    return

def saveas_config(*args):
    global configfname
    configfname = tkFileDialog.asksaveasfilename( filetypes=[('Config Files','*.ini'), ('All Files', '*')],
                                                  initialfile="", defaultextension='ini' )    
    return

def read_config(*args):
    global configfname
    configfname = tkFileDialog.askopenfilename( filetypes=[('Config Files','*.ini'), ('All Files', '*')],
                                                initialfile="", defaultextension='ini' )
    if configfname == '':
        return
    print "read_config: filename = %s" % configfname

    config = ConfigParser.SafeConfigParser()
    config.read(configfname)
    if config.has_section("Global"):
        print "Global section detected"
        if config.has_option("Global","Module Ids"):
            moduleids = map(int,config.get("Global","Module Ids").split(" "))
            print "Module ids %s" % moduleids
    
    return

#HEERE
def write_page(femaddr,row,col,side,chipid): 

    # Register addresses
    regs = [   1, 2, 3, 4,  5,  6,  7,  8,   9,  10,  11, 12, 13, 14, 15, 16, 17 ]

    # Which operation to perform on each register (1=Write, 2=Set, etc. cf. FPHX manual)
    ops  = [   1, 1, 1, 1,  1,  1,  1,  1,   1,   1,   1,  1,  1,  1,  1,  1,  1 ]

    # Here are the values to send for each register
    vals = [ (0x0 << 7) |  1, # Global unmask all channels - dummy value?
             (0x0 << 7) | (0xFF & 5), # Digital control: 00000111 to activate both serial lines, accept hits, enable inject
             (0x0 << 3) |  1, # Vref: 0001
             (0x0 << 7) | (0xFF & 8),#   Threshold DAC 0: 00001000
             (0x0 << 7) | (0xFF & 16),#  Threshold DAC 1: 00010000
             (0x0 << 7) | (0xFF & 32),#  Threshold DAC 2: 00100000
             (0x0 << 7) | (0xFF & 48),#  Threshold DAC 3: 01001000
             (0x0 << 7) | (0xFF & 80),#  Threshold DAC 4: 01010000
             (0x0 << 7) | (0xFF & 112),# Threshold DAC 5: 01110000
             (0x0 << 7) | (0xFF & 144),# Threshold DAC 6: 10010000
             (0x0 << 7) | (0xFF & 176),# Threshold DAC 7: 10110000
             (0x0 << 7) | (0xF & 4)  << 4 | (0xF & 6),# N1Sel & N2Sel: 01000110
             (0x0 << 7) | (0xF & 0)  << 4 | (0xF & 4), # LeakSel & FB1Sel: 00000100
             (0x0 << 7) | (0x3F & 4) << 4 | (0x3 & 0), # P2Sel & P3Sel: 01000000
             (0x0 << 7) | (0x1F & 8) << 3 | (0x7 & 2), # BWSel & GSel: 00100010
             (0x0 << 7) | (0x1F & 0) << 3 | (0x7 & 5), # InjSel & P1Sel: 00000101
             (0x0 << 7) | (0xFF & 3)
             ]

    length = int(17*4) # 17 commands
    dest = TESTBENCH_EEPROM_READ_WRITE # destination == FEM EEPROM

    datalen = length+1+3+16 # +8 bits for "instruction" in page write seq
                         # +24 bits for page address & 15 zeros
                         # +128 bits for channel mask
    data = create_string_buffer(datalen)
    offset = 0

    word = (0x0 << 7) | (0xFF & 2)

    #This is for the page write? (MLB, 5-Aug-11):
    
    struct.pack_into(">B",data,offset,word)
    offset += 1

    # page address bits
##    word= int(0)
##    word |= (0x3 & row) << 8#7
##    word |= (0x3 & col) << 6#5
##    word |= (0x1 & side) << 5#4
##    word |= (0xFF & chipid) #(0xF & chipid)
##    word = word << 14#15

    #EEPROM Page Address info.
    # IMPORTANT NOTE:  The 7 MSBs of the page address are not used by the EEPROM
    # so data needed to shift up by 8 rather than the previous 15 that were in this code.
    word= int(0)
    word |= (0x3 & row) << 7
    word |= (0x3 & col) << 5
    word |= (0x1 & side) << 4
    word |= (0xF & (chipid))
    word = word << 8

    struct.pack_into(">H",data,offset,word >> 8)
    offset += 2
    struct.pack_into(">B",data,offset,0x0 << 7)
    offset += 1

    # FPHX commands
    # Try wild-card chip_id:
    for i in range(2,17) :
        word = make_fphx_cmd((chipid+1),regs[i],ops[i],vals[i])
        struct.pack_into(">I",data,offset,word)
        offset += 4

    word = make_fphx_cmd((chipid+1),regs[1],ops[1],vals[1])
    struct.pack_into(">I",data,offset,word)
    offset += 4

    word = make_fphx_cmd((chipid+1),regs[0],ops[0],vals[0])
    struct.pack_into(">I",data,offset,word)
    offset += 4
    
    # 128 bit channel mask
    for i in range(0,16):
        if i==0:
          struct.pack_into(">B",data,offset,0x10)
          offset += 1
        else:
            struct.pack_into(">B",data,offset,0x00)
            offset += 1

    print 'the result: %s' % hexify_bytes(data)

    #Try to write to appropriate wedge address instead of FF:
    wedgeaddr = 0xFF # override user: Write to all wedgeaddr for now.

    
##    femaddr = 0x0F # override user: Write to 0x0F for now  

   # Write enable eeprom

    buf = create_packet(dest,data.raw,wedgeaddr,femaddr)

    print 'the packet result: %s' % hexify_bytes(buf) 

    we_eeprom(femaddr)
    write_bytes_to_target(buf.raw,comm_panel.getTarget())
    wd_eeprom(femaddr)

    return

def write_initpages_eeprom():

    #row, column range should be 0,4 rather than 0,3 (4 possible stations, wedges) - (MLB, 5-Aug-11)
    rwclrng = range(0,4)
    sdrng = range(0,2)
    femaddr = 0x0F

    for rw in rwclrng:
        for cl in rwclrng:
            for sd in sdrng:
                if rw == 0:
                    cidrng = range(0,5)
                    
                else:
                    cidrng = range(0,13)
                print 'rw = %d' % rw
                print 'cl = %d' % cl
                for cid in cidrng:
                    print 'cid = %d' % cid
                    write_page(femaddr,rw,cl,sd,cid)
    return

def test_write():
    dest = TESTBENCH_EEPROM_READ_WRITE
    datalen = 1+3+1
    data = create_string_buffer(datalen)
    offset = 0

    word = (0x0 << 7) | (0xFF & 2)
    struct.pack_into(">B",data,offset,word)
    offset += 1

    #page address bits
    word = int(0)
    word = (0x0 << 23)

    struct.pack_into(">H",data,offset,word >> 8)
    offset += 2
    struct.pack_into(">B",data,offset,0x0 << 7)
    offset += 1

    #data bits
    struct.pack_into(">B",data,offset,0xFF)
    offset += 1

    wedgeaddr = 0xFF # override user: Write to all wedgeaddr for now.
    femaddr = 0x0F # override user: Write to 0x0Ffor now  

    buf = create_packet(dest,data.raw,wedgeaddr,femaddr)

    print 'the packet result: %s' % hexify_bytes(buf)

    # Write enable eeprom
    we_eeprom(femaddr)
    # send data
    write_bytes_to_target(buf.raw,comm_panel.getTarget())
    # Write disable eeprom
    wd_eeprom(femaddr)

    return

def read_page(femaddr,row,col,side,chipid): 
    dest = TESTBENCH_EEPROM_READ_WRITE # destination == FEM EEPROM

    datalen = 1+3+1      # +8 bits for "instruction" in page write seq
                         # +24 bits for page address & 15 zeros
                         # + 8 bits of 0s to keep CS high for 40 total bits
                         
    data = create_string_buffer(datalen)
    offset = 0

    word = (0x0 << 7) | (0xFF & 3)

    struct.pack_into(">B",data,offset,word)
    offset += 1

    # page address bits
    word= int(0)
    word |= (0x3 & row) << 7
    word |= (0x3 & col) << 5
    word |= (0x1 & side) << 4
    word |= (0xF & chipid)
    word = word << 8

    #page address bits
#    word = int(0)
#    word = (0x0 << 23)

    struct.pack_into(">H",data,offset,word >> 8)
    offset += 2
    struct.pack_into(">B",data,offset,(0x0 << 7) | (0x02)) # reads the third (index 2) byte of the page
    offset += 1
    
    struct.pack_into(">B",data,offset,0x0 << 7)
    offset += 1

    print 'the result: %s' % hexify_bytes(data)

    wedgeaddr = 0xFF # override user: Write to all wedgeaddr for now.
    femaddr = 0x0F # override user: Write to 0x0Ffor now  

    buf = create_packet(dest,data.raw,wedgeaddr,femaddr)

    write_bytes_to_target(buf.raw,comm_panel.getTarget())

    return

def read_page2(femaddr,row,col,side,chipid):

    dest = TESTBENCH_EEPROM_BATCH_DOWNLOAD #0x07

    datalen = 3

    data = create_string_buffer(datalen)
    offset = 0

    # page address bits
    word= int(0)
    word |= (0x3 & row) << 7
    word |= (0x3 & col) << 5
    word |= (0x1 & side) << 4
    word |= (0xF & chipid)
    word = word << 15

    struct.pack_into(">H",data,offset,word >> 8)
    offset += 2
    struct.pack_into(">B",data,offset,0x0 << 7)
    offset += 1

    print 'page address: %s' % hexify_bytes(data)

    wedgeaddr = 0xFF # override user: Write to all wedgeaddr for now.
    femaddr = 0x0F # override user: Write to 0x0F for now  

    buf = create_packet(dest,data.raw,wedgeaddr,femaddr)

    write_bytes_to_target(buf.raw,comm_panel.getTarget())
    
    return

# Write enables the EEPROM of a given FEM
def we_eeprom(femaddr):
    dest = TESTBENCH_EEPROM_READ_WRITE # destination == FEM EEPROM 
    datalen = int(1) 
    data = create_string_buffer(datalen)
    struct.pack_into(">B",data,0,0x06)
    wedgeaddr = 0xFF
    buf = create_packet(dest,data.raw,wedgeaddr,femaddr)
    write_bytes_to_target(buf.raw,comm_panel.getTarget())
    return

# Write disables the EEPROM of a given FEM
def wd_eeprom(femaddr):
    dest = TESTBENCH_EEPROM_READ_WRITE # destination == FEM EEPROM
    datalen = int(1) 
    data = create_string_buffer(datalen)
    struct.pack_into(">B",data,0,0x04)
    wedgeaddr = 0xFF
    buf = create_packet(dest,data.raw,wedgeaddr,femaddr)
    write_bytes_to_target(buf.raw,comm_panel.getTarget())
    return

def erase_eeprom(femaddr):

    dest = TESTBENCH_EEPROM_READ_WRITE
    datalen = 1
    data = create_string_buffer(datalen)
    offset = 0

    word = 0xC7
    struct.pack_into(">B",data,offset,word)

    print 'erase command sent: %s' % hexify_bytes(data)

    wedgeaddr = 0xFF

    buf = create_packet(dest,data.raw,wedgeaddr,femaddr)

    # Write enable eeprom
    we_eeprom(femaddr)
    # send data
    write_bytes_to_target(buf.raw,comm_panel.getTarget())
    # Write disable eeprom
    wd_eeprom(femaddr)

    return

# A class representing a chip configuration. Includes
# the chip ID and the register values.  We encode both the string vars
# and the integer variables here, because I don't really know the
# best way of keeping track of the split variables easily.
class ChipConfig:
    # Constructor assumes there are 18 register values, even if
    # only 2-17 have well-defined 'values'.  It's just easier that way.
    # The input array vals is a placeholder for now, but eventually
    # it will be used to supply initial values for the configuration.
    def __init__(self,chipid,*vals):
        self.chipid = chipid

        # This is an array of values for the registers.  These are
        # the values that are read when any of the register operation
        # buttons are pressed.  There is a little python/Tk magic in use
        # here.  There are a couple of registers that contain 2 fields of
        # information, and in the GUI are displayed with 2 Entry widgets.
        # This means there are two StringVars associated with the
        # register.  What I have done is define a callback assigned to
        # each of the StringVars that gets called whenever the Entry is
        # modified.  The callback call includes the number of bits and the
        # starting bit for each field.  Thus modification of either field
        # triggers code that will update the bits in the reg_vars element.
        # Then when the value is needed (eg for a write operation), we can
        # look at one variable: reg_vars[].
        #
        self.reg_vals = [ StringVar(master,'0'),   StringVar(master,'5'),   StringVar(master,'1'),
                          StringVar(master,'8'),   StringVar(master,'16'),  StringVar(master,'32'),
                          StringVar(master,'48'),  StringVar(master,'80'),  StringVar(master,'112'),
                          StringVar(master,'144'), StringVar(master,'176'), StringVar(master,'6'),
                          StringVar(master,'4'),   StringVar(master,'0'),   StringVar(master,'2'),
                          StringVar(master,'5'),   StringVar(master,'3'),  StringVar(master,'n/a') ]

        self.reg_vals2= [ StringVar(master,''),  StringVar(master,''),  StringVar(master,''),
                          StringVar(master,''),  StringVar(master,''),  StringVar(master,''),
                          StringVar(master,''),  StringVar(master,''),  StringVar(master,''),
                          StringVar(master,''),  StringVar(master,''),  StringVar(master,'4'),
                          StringVar(master,'0'), StringVar(master,'4'), StringVar(master,'8'),
                          StringVar(master,'0'), StringVar(master,''),  StringVar(master,''),
                          StringVar(master,''),  StringVar(master,''),  StringVar(master,''),
                          StringVar(master,''),  StringVar(master,''),  StringVar(master,'') ]

        self.reg_vars = [ int(self.reg_vals[i].get()) for i in range(11) ]
        self.reg_vars.append(int(self.reg_vals[11].get())+(int(self.reg_vals2[11].get())<<4))
        self.reg_vars.append(int(self.reg_vals[12].get()))
        self.reg_vars.append(int(self.reg_vals[13].get())+(int(self.reg_vals2[13].get())<<4))
        self.reg_vars.append(int(self.reg_vals[14].get())+(int(self.reg_vals2[14].get())<<3))
        self.reg_vars.append(int(self.reg_vals[15].get()))
        self.reg_vars.append(int(self.reg_vals[16].get()))
        self.reg_vars.append(0)

        # Connect the StringVars with callbacks to update the register values
        self.reg_vals[0].trace("w",   lambda *args: self.update_regvar(self.reg_vals[0],  0,  8, 0, *args))
        self.reg_vals[1].trace("w",   lambda *args: self.update_regvar(self.reg_vals[1],  1,  8, 0, *args))
        self.reg_vals[2].trace("w",   lambda *args: self.update_regvar(self.reg_vals[2],  2,  8, 0, *args))
        self.reg_vals[3].trace("w",   lambda *args: self.update_regvar(self.reg_vals[3],  3,  8, 0, *args))
        self.reg_vals[4].trace("w",   lambda *args: self.update_regvar(self.reg_vals[4],  4,  8, 0, *args))
        self.reg_vals[5].trace("w",   lambda *args: self.update_regvar(self.reg_vals[5],  5,  8, 0, *args))
        self.reg_vals[6].trace("w",   lambda *args: self.update_regvar(self.reg_vals[6],  6,  8, 0, *args))
        self.reg_vals[7].trace("w",   lambda *args: self.update_regvar(self.reg_vals[7],  7,  8, 0, *args))
        self.reg_vals[8].trace("w",   lambda *args: self.update_regvar(self.reg_vals[8],  8,  8, 0, *args))
        self.reg_vals[9].trace("w",   lambda *args: self.update_regvar(self.reg_vals[9],  9,  8, 0, *args))
        self.reg_vals[10].trace("w",  lambda *args: self.update_regvar(self.reg_vals[10], 10, 8, 0, *args))
        self.reg_vals[11].trace("w",  lambda *args: self.update_regvar(self.reg_vals[11], 11, 4, 0, *args))
        self.reg_vals2[11].trace("w", lambda *args: self.update_regvar(self.reg_vals2[11],11, 4, 4, *args))
        self.reg_vals[12].trace("w",  lambda *args: self.update_regvar(self.reg_vals[12], 12, 4, 0, *args))
        self.reg_vals2[12].trace("w", lambda *args: self.update_regvar(self.reg_vals2[12],12, 4, 4, *args))
        self.reg_vals[13].trace("w",  lambda *args: self.update_regvar(self.reg_vals[13], 13, 2, 0, *args))
        self.reg_vals2[13].trace("w", lambda *args: self.update_regvar(self.reg_vals2[13],13, 4, 4, *args))
        self.reg_vals[14].trace("w",  lambda *args: self.update_regvar(self.reg_vals[14], 14, 3, 0, *args))
        self.reg_vals2[14].trace("w", lambda *args: self.update_regvar(self.reg_vals2[14],14, 5, 3, *args))
        self.reg_vals[15].trace("w",  lambda *args: self.update_regvar(self.reg_vals[15], 15, 3, 0, *args))
        self.reg_vals2[15].trace("w", lambda *args: self.update_regvar(self.reg_vals2[15],15, 3, 3, *args))
        self.reg_vals[16].trace("w",  lambda *args: self.update_regvar(self.reg_vals[16], 16, 8, 0, *args))

        # List of IntVars representing the enable mask for the chip.  We use IntVar so we can
        # easily connect them to the buttons in the RegisterConfigPanel.  Default is OFF (ie. 0) for
        # each channel
        self.enable_mask = [ IntVar(None,0) for i in range(128) ]

        return

    def get_chipid(self):
        return self.chipid

    def set_value(self,reg,val):
        self.reg_vals[reg] = val
        return

    def get_value(self,reg):
        return self.reg_vals[reg]

    def dump(self):
        print 'Chip Config for ID %d:' % self.chipid
        for i in range(0,len(self.reg_vars)): print " Register Addr %d = %d" % (i+1,self.reg_vars[i])

    def update_regvar(self, var, ireg, nbits, start, name, index, mode):
        #print "ChipConfig.update_regvar: callback called with name=%r, index=%r, mode=%r, value=%r" % (name, index, mode, var.get())
        s = var.get()
        if len(s) != 0:
            val = int(var.get())
            mask = c_uint8(0x00)
            clear_mask = mask
            for i in range(0,nbits):
                mask.value |= 1<<(i+start)
            clear_mask = c_uint8(~mask.value)
            self.reg_vars[ireg] &= clear_mask.value # clear the field we are updating (leave the rest as is)
            self.reg_vars[ireg] |= val<<start # OR in the the value
        return

    def send_init(self,wedgeaddr,femaddr):
        # chip ID
        chipid = int(self.chipid)

        print 'ChipConfig.send_init: Send init for chip %d' % (int(self.chipid))

        # Register addresses
        regs = [   1, 2, 3, 4,  5,  6,  7,  8,   9,  10,  11, 12, 13, 14, 15, 16, 17 ]

        # Which operation to perform on each register (1=Write, 2=Set, etc. cf. FPHX manual)
        ops  = [   2, 1, 1, 1,  1,  1,  1,  1,   1,   1,   1,  1,  1,  1,  1,  1,  1 ]

        # Here are the values to send for each register
        vals = [ 128, # Global mask all channels
                 int(self.reg_vals[1].get()), # The reset we initialize from the corresponding values
                 int(self.reg_vals[2].get()),
                 int(self.reg_vals[3].get()),
                 int(self.reg_vals[4].get()),
                 int(self.reg_vals[5].get()),
                 int(self.reg_vals[6].get()),
                 int(self.reg_vals[7].get()),
                 int(self.reg_vals[8].get()),
                 int(self.reg_vals[9].get()),
                 int(self.reg_vals[10].get()),
                 int(self.reg_vals2[11].get())<<4 | int(self.reg_vals[11].get()),
                 int(self.reg_vals2[12].get())<<4 | int(self.reg_vals[12].get()),
                 int(self.reg_vals2[13].get())<<4 | int(self.reg_vals[13].get()),
                 int(self.reg_vals2[14].get())<<3 | int(self.reg_vals[14].get()),
                 int(self.reg_vals2[15].get())<<3 | int(self.reg_vals[15].get()),
                 int(self.reg_vals[16].get())
                 ]

        length = int(17*4) # 17 commands
        dest = TESTBENCH_FPHX # destination == 'to FPHX'

        print "Chip %d WedgeAddr 0x%02X:" % (chipid,(lambda:wedgeaddr if wedgeaddr else 0)())
        #for r, o, v in zip(regs,ops,vals):
        #    print "Register %d: oper %d with val %d" % (r,o,v)

        datalen = length

        data = create_string_buffer(datalen)
        offset = 0

        for i in range(0,17) :
            word = make_fphx_cmd(chipid,regs[i],ops[i],vals[i])
            struct.pack_into(">I",data,offset,word)
            offset += 4

        # if use_roc.get(): wedgeaddr = (0xF & self.moduleid) | (0xF & iside)<<4
        if use_roc.get(): wedgeaddr = (0xFF)
        femaddr = None
        if use_roc.get() == 2: femaddr = femaddr_var.get()

        buf = create_packet(dest,data.raw,wedgeaddr,femaddr)
        
        print 'ChipConfig.send_init: Send init packet = %s' % hexify_bytes(buf)
        write_bytes_to_target(buf.raw,comm_panel.getTarget())
        
        # Now send down the enable mask
        self.send_mask(wedgeaddr,femaddr)

        return

    def send_enable_ro(self,wedgeaddr,femaddr):
        chipid = 0x1F & int(self.chipid)
        print 'ChipConfig.enable_ro: Send enable RO for chip %d' % (chipid)
        regid = 2
        val = self.reg_vars[1]
        val |= 1<<1
        cmd = FPHX_WRITE
        word = make_fphx_cmd(chipid,regid,cmd,val)
        buf = create_packet_fphx(word,wedgeaddr,femaddr)
        print 'ChipConfig.enable_ro: FPHX command = 0x%x' % word
        print 'ChipConfig.enable_ro: Send FPHX packet = %s' % hexify_bytes(buf)
        write_bytes_to_target(buf.raw,comm_panel.getTarget())    
        return

    def send_disable_ro(self,wedgeaddr,femaddr):
        chipid = 0x1F & int(self.chipid)
        print 'ChipConfig.send_disable_ro: Send disable RO for chip %d' % (chipid)
        regid = 2
        val = self.reg_vars[1]
        val &= ~(1<<1)
        cmd = FPHX_WRITE
        word = make_fphx_cmd(chipid,regid,cmd,val)
        buf = create_packet_fphx(word,wedgeaddr,femaddr)
        print 'ChipConfig.send_disable_ro: FPHX command = 0x%x' % word
        print 'ChipConfig.send_disable_ro: Send FPHX packet = %s' % hexify_bytes(buf)
        write_bytes_to_target(buf.raw,comm_panel.getTarget())
        return

    def send_core_reset(self,wedgeaddr,femaddr):
        print "ChipConfig.send_core_reset, chipid %d" % (self.chipid)
        prog_reset_fphx(int(self.chipid),FPHX_SET,wedgeaddr,femaddr,comm_panel.getTarget())
        return

    def send_bco_reset(self,wedgeaddr,femaddr):
        print "ChipConfig.send_bco_reset, chipid %d" % (self.chipid)
        prog_reset_fphx(int(self.chipid),FPHX_RESET,wedgeaddr,femaddr,comm_panel.getTarget())
        return

    # Take the current state of the channel enables and send them to the chip
    def send_mask(self,wedgeaddr,femaddr):
        chipid = self.get_chipid()
        print 'ChipConfig.send_mask: Wedge 0x%02x ChipId %d' % ((lambda:wedgeaddr if wedgeaddr else 0)(),chipid)
        masked = []
        unmasked = []
        for i in range(0,len(self.enable_mask)):
            if self.enable_mask[i].get() == 1:
                unmasked.append(i)
            else:
                masked.append(i)
        print 'ChipConfig.send_mask: %d masked, %d unmasked' % (len(masked),len(unmasked))
        data = 1<<7
        reg = 1
        if ( len(masked) >= len(unmasked) ):
            print 'ChipConfig.send_mask: Disabling all channels'
            cmd = FPHX_SET
            channels = unmasked
        else:
            print 'ChipConfig.send_mask: Enabling all channels'
            cmd = FPHX_RESET
            channels = masked
        word = make_fphx_cmd(chipid,reg,cmd,data)
        print 'ChipConfig.send_mask: FPHX command = 0x%x' % word
        buf = create_packet_fphx(word,wedgeaddr,femaddr)
        write_bytes_to_target(buf.raw,comm_panel.getTarget())
        for i in range(0,len(channels)):
            chan = channels[i]
            data = chan
            if self.enable_mask[chan].get() == 1:
                cmd = FPHX_RESET # if button is depressed, we want the channel unmasked (enabled)
            else:
                cmd = FPHX_SET # if button is un-depressed, we want the channel masked (disabled)
            print 'ChipConfig.send_mask: cmd %d for channel %d' % (cmd,chan)
            word = make_fphx_cmd(chipid,reg,cmd,data)
            print 'ChipConfig.send_mask: FPHX command = 0x%x' % word
            buf = create_packet_fphx(word,wedgeaddr,femaddr)
            print 'ChipConfig.send_mask: Send FPHX packet = %s' % hexify_bytes(buf)
            write_bytes_to_target(buf.raw,comm_panel.getTarget())
        return

    def get_enablemask(self):
        # Loop over the channel masks
        mask = [ 0, 0, 0, 0, 0, 0, 0, 0 ]
        for i in range(0,128):
            if self.enable_mask[i].get() == 1:
                mask[int(i/16)] |= 1<<(i%16)
        return mask

    def get_config_list(self):
        chipid = self.chipid
        mask = self.get_enablemask()
        regvals = [ self.reg_vars[i] for i in range(1,17) ]
        return [chipid,mask,regvals]

class RegisterConfigPanel(Tix.Frame):
    def __init__(self,master,moduleid,chipid,chipconfigs):
        self.master = master
        # Create a register frame to contain all the register display info
        Tix.Frame.__init__(self,master)
        self.grid(row=0, column=0, rowspan=8)

        self.moduleid = moduleid
        self.chipconfigs = chipconfigs

        # Register frame: Create a frame to contain the column labels and each register line
        desc_width = 11
        val_width = 5
        send_width = 6

        irow = 0
        icol = 0
        reg_frame = Tix.Frame(self)
        reg_frame.grid(row=irow,column=icol,rowspan=4)
        
        self.label_line = Tix.Frame(reg_frame, relief=RAISED, borderwidth=1, height=40)
        self.label_line.grid(row=irow,column=icol,sticky=N+W+E+S,columnspan=9)
        Label(reg_frame, text="Reg").grid(row=0,column=icol)
        icol += 1
        Label(reg_frame, text="Desc", width=desc_width).grid(row=0,column=icol)
        icol += 1
        Label(reg_frame, text="To\nChip", width=val_width).grid(row=0,column=icol)
        icol += 1
        Label(reg_frame, text="From\nChip", width=val_width).grid(row=0,column=icol)
        icol += 1
        Label(reg_frame, text="Chip Command",width=20).grid(row=0,column=icol,columnspan=5)
        icol += 1

        # Create a subframe for each register
        # First register is the wild-register
        irow += 1
        icol = 0
        self.wild_reg_val = StringVar(None,'0')
        bgColor = 'white'
        reg_line = Tix.Frame(reg_frame, bg=bgColor)
        reg_line.grid(row=irow,column=icol,sticky=N+W+E+S,columnspan=9)

        self.reg_entries = []
        self.reg_entries2 = [ None for i in range(18) ]

        Label(reg_frame, text="*", bg=bgColor, width=5).grid(row=irow, column=icol)
        icol += 1
        Label(reg_frame, text="Wild", bg=bgColor, width=desc_width).grid(row=irow, column=icol)
        icol += 1
        reg_entry = Entry(reg_frame, textvariable=self.wild_reg_val, bg=bgColor, width=val_width, justify=RIGHT)
        reg_entry.grid(row=irow,column=icol)
        icol += 1
        Label(reg_frame,text="", bg=bgColor, width=val_width, justify=RIGHT).grid(row=irow,column=icol)
        icol += 1 
        b = Button(reg_frame,text="Read", bg=bgColor, width=send_width)
        b.grid(row=irow,column=icol)
        b.config(state=DISABLED)
        icol += 1

        write_button = Button(reg_frame,text="Write", bg=bgColor, width=send_width,
                              command=( lambda c=FPHX_WRITE, r=wild_reg, v=self.wild_reg_val:
                                            self.send_register_value(c,r) ))
        write_button.grid(row=irow,column=icol)
        icol += 1
        set_button = Button(reg_frame,text="Set", bg=bgColor, width=send_width,
                             command=( lambda c=FPHX_SET, r=wild_reg, v=self.wild_reg_val: 
                                       self.send_register_value(c,r) ))
        set_button.grid(row=irow,column=icol)
        icol += 1
        reset_button = Button(reg_frame,text="Reset", bg=bgColor, width=send_width,
                              command=( lambda c=FPHX_RESET, r=wild_reg, v=self.wild_reg_val: self.send_register_value(c,r) ))
        reset_button.grid(row=irow,column=icol)
        icol += 1
        default_button = Button(reg_frame,text="Default", bg=bgColor, width=send_width,
                                command=( lambda c=FPHX_RESET, r=wild_reg, v=self.wild_reg_val: self.send_register_value(c,r) ))
        default_button.grid(row=irow,column=icol)
        icol += 1
        irow += 1
        self.rb_vals = [StringVar(None,'') for i in range(18) ] # StringVars for displaying the readback values from "Read".
        self.rb_entries = [] # Entry widgets displaying the readback StringVars.
        for i in range(18):
            reg_name = str(i+1)
            bgColor = 'grey' if i%2 == 0 else 'white'
            reg_line = Frame(reg_frame, bg=bgColor)
            reg_line.grid(row=irow,column=icol,sticky=N+W+E+S,columnspan=9)
            Label(reg_frame, text=reg_name, bg=bgColor, width=5).grid(row=irow, column=0)
            Label(reg_frame, text=descript[i], bg=bgColor, width=desc_width).grid(row=irow, column=1)
            reg_entry = Entry(reg_frame, bg=bgColor, width=val_width, justify=RIGHT)
            reg_entry.grid(row=irow,column=2)
            self.reg_entries.append(reg_entry)
            icol = 3
            rb_entry=None
            self.rb_vals[i] = StringVar(None,'')
            if ( i > 0 and i < 17 ) :
                rb_entry = Entry(reg_frame, bg=bgColor, width=val_width, justify=RIGHT, textvariable=self.rb_vals[i])
                rb_entry.grid(row=irow,column=icol)
                self.rb_entries.append(rb_entry)
            else:
                tmp = Label(reg_frame,text="", bg=bgColor, width=val_width, justify=RIGHT)
                tmp.grid(row=irow,column=icol)
                self.rb_entries.append(tmp)
            icol += 1
            b = Button(reg_frame,text="Read", bg=bgColor, width=send_width,
                       command=( lambda r=i : self.readback_register(r)))
            b.grid(row=irow,column=icol)
            icol += 1
            write_button = Button(reg_frame,text="Write", bg=bgColor, width=send_width,
                                  command=( lambda c=FPHX_WRITE, r=i: self.send_register_value(c,r) ))
            write_button.grid(row=irow,column=icol)
            icol += 1
            set_button = Button(reg_frame,text="Set", bg=bgColor, width=send_width,
                                command=( lambda c=FPHX_SET, r=i: self.send_register_value(c,r) ))
            set_button.grid(row=irow,column=icol)
            icol += 1
            reset_button = Button(reg_frame,text="Reset", bg=bgColor, width=send_width,
                                  command=( lambda c=FPHX_RESET, r=i: self.send_register_value(c,r) ))
            reset_button.grid(row=irow,column=icol)
            icol += 1
            default_button = Button(reg_frame,text="Default", bg=bgColor, width=send_width,
                                    command=( lambda c=FPHX_RESET, r=i: self.send_register_value(c,r) ))
            default_button.grid(row=irow,column=icol)
            icol += 1
            
            # Some registers don't have certain operations defined
            if i == 0 or i == 17 :
                b.config(state=DISABLED)
                write_button.config(state=DISABLED)
                default_button.config(state=DISABLED)            
                
            # Some registers don't use the data bits
            if i == 17:
                reg_entry.config(state=DISABLED)
                    
            # Special handling for those registers that contain more than one setting.
            # 
            if ( split_vals[i] ):
                irow += 1
                Frame(reg_frame, bg=bgColor).grid(row=irow,column=0,sticky=N+W+E+S,columnspan=9)
                Label(reg_frame, text="", bg=bgColor, width=5).grid(row=irow, column=0)
                Label(reg_frame, text=descript2[i], bg=bgColor, width=desc_width).grid(row=irow, column=1)
                reg_entry2 = Entry(reg_frame, bg=bgColor, width=val_width, justify=RIGHT)
                reg_entry2.grid(row=irow,column=2)
                self.reg_entries2[i] = reg_entry2
            irow += 1

        # Variable for use in an external check button to enable/disable the state of this module
        self.module_enable = IntVar(self,0)

        # Create a frame for the chip ID
        icol = 0
        self.chipconfig_enable = IntVar(self,0)
        chipconfig_frame = LabelFrame(self,text='Chip Control',labelanchor=N)
        self.chipid_text = StringVar(self.master,chipid);
        self.chipid_text.trace("w",lambda *args: self.load_chipconfig(*args))
        Label(chipconfig_frame, text="Display/Modify Configuration for Chip ID", justify=LEFT).grid(row=0,column=icol)
        icol += 1
        cb = lambda *args: self.load_chipconfig(*args)
        self.chipid_entry = ChipIdEntry(chipconfig_frame, value="21", textvariable=self.chipid_text, extra_cb=cb, width=10, justify=RIGHT)
        self.chipid_entry.grid(row=0,column=icol)
        icol += 1
        side_options = ( "Side 15", "Side 0", "Side 1" )
        self.side_selection = StringVar(self,side_options[0])
        side_menu = OptionMenu(chipconfig_frame,self.side_selection,*side_options)
        side_menu.grid(row=0,column=icol)
        self.side_selection.trace("w",lambda *args: self.load_chipconfig(*args))
        icol += 1
        chipconfig_frame.grid(row=1,column=1,columnspan=2)

        # Channel selection panel
        #
        mask_frame = Frame(self,bg='linen')
        mask_frame.grid(row=2,column=1,sticky=N,columnspan=4)

        self.chan_btn = []
        chan_per_row = 16
        nrows = 8
        rstart = 0
        bgColor = mask_frame.cget('bg')
        Label(mask_frame,text="Channel Mask\n[Red = Off, Green = On]",bg=bgColor,width=56).grid(row=0,column=0,columnspan=chan_per_row+1)
        for irow in range(0,nrows) :
            for icol in range(0,chan_per_row):
                Label(mask_frame,text=str(icol),bg=bgColor).grid(row=1,column=icol)
                chan_num = chan_per_row*irow+icol
                channel_btn = Checkbutton(mask_frame,text=str(chan_num),bg='red',fg='white',width=3,height=1,
                                          indicatoron=0,selectcolor='green')
                channel_btn.grid(row=2+irow,column=icol,pady=1)
                self.chan_btn.append(channel_btn)

        maskbtn_line = Frame(mask_frame)
        maskbtn_line.grid(row=3+nrows,column=0,columnspan=chan_per_row+1,pady=2)
        Button(maskbtn_line,text='Mask All',  width=10,command=lambda: self.mask_all()).grid(row=0,column=0)
        Button(maskbtn_line,text='Unmask All',width=10,command=lambda: self.unmask_all()).grid(row=0,column=1)
        Button(maskbtn_line,text='Toggle All',width=10,command=lambda: self.toggle_all()).grid(row=0,column=2)
        Button(maskbtn_line,text='Send',width=10,command=lambda: self.send_mask()).grid(row=0,column=3)

        # Now that we have a defined chipid in the config frame, initiate a load_chip to initialize
        # the config display.
        self.load_chipconfig()

        chipsel_frame = LabelFrame(self,text='Chip Side Enable',labelanchor=N)
        chipsel_frame.grid(row=3,column=1,sticky=N+W+E+S,columnspan=4)
        irow = 0
        icol = 0
        chips_per_col = 8
        self.chip_enables = { 15: {}, 0: {}, 1: {} } # "List" indexed by side id, each element is a dictionary keyed by chipid
        for ichip in range(0,32):
            id = ichip
            irow = ichip % chips_per_col
            icol = 4*int(ichip/chips_per_col)
            l = Label(chipsel_frame,text=str(id))
            l.grid(row=irow,column=icol)
            #if id == 21: l.config(bg='yellow')
            icol += 1
            self.chip_enables[15][id] = IntVar(self,0) 
            self.chip_enables[0][id]  = IntVar(self,0)
            self.chip_enables[1][id]  = IntVar(self,0)
            Checkbutton(chipsel_frame,indicatoron=0,variable=self.chip_enables[15][ichip],text='15',selectcolor='green').grid(row=irow,column=icol)
            icol += 1
            Checkbutton(chipsel_frame,indicatoron=0,variable=self.chip_enables[0][ichip],text='0',selectcolor='green').grid(row=irow,column=icol)
            icol += 1
            Checkbutton(chipsel_frame,indicatoron=0,variable=self.chip_enables[1][ichip],text='1',selectcolor='green').grid(row=irow,column=icol)
            icol += 1
            #self.chip_enables[15][id].trace("w",lambda v=self.chip_enables[15][id], x=self.chip_enables[0][ichip], y=self.chip_enables[1][ichip],*args: v.set(1) if x.get() and y.get() else v.set(0) )
            if id == 21:
                self.chip_enables[15][id].set(1)
                #self.chip_enables[0][ichip].set(1)
                #self.chip_enables[1][ichip].set(1)

    # Load a chip configuration into the panel.  There is a weird effect here that I can't figure out how to 
    # solve.  The way I've coded it, load_chipconfig() is an extra callback to the ValidateEntry widget, and 
    # gets called after validation.  Validation gets called for EVERY edit, including deleting the current value
    # displayed in the entry (this is true even if you highlight the contents and overwrite them).  The validate
    # function handles this intermediate problem OK (ignoring the empty value), but then load_chipconfig here
    # queries the results member -- which hasn't been modified yet.  Thus we load the config for the already
    # loaded chip id.  Slightly excessive, but otherwise not really a problem.  If I can figure out how to fix this
    # I will, but for now it should work...
    # Another observation: when typing two digits, each one gets called back!  Again, not a huge problem, but a little
    # annoying.  Perhaps a way out of this is to add a separate load step instead, like a load button, or initiate the
    # load when a bound keystroke happend (eg. return, loss of focus, etc.)
    def load_chipconfig(self,*args):
        side = int(self.get_chip_sideid())
        inChipid = self.chipid_entry.results.get()
        if inChipid is None:
            print "load_chipconfig: side %d inChipid = %s, bailing" % (side,inChipid)
            return
        try: 
            chipid = int(inChipid)
        except:
            print "Invalid value for chipid, bailing"
            return
        print "load chip config for side %d chipid %d" % (side,chipid)
        #self.chipconfigs[side][chipid].dump()
        for i in range(18):
            #print "Load reg %d value %d" % (i,self.chipconfigs[side][chipid].reg_vars[i])
            self.reg_entries[i].config(textvariable=self.chipconfigs[side][chipid].reg_vals[i])
            if ( split_vals[i] ):
                self.reg_entries2[i].config(textvariable=self.chipconfigs[side][chipid].reg_vals2[i])

        # Connect the chip's enable mask variables to the mask panel
        for i in range(128):
            self.chan_btn[i].config(variable=self.chipconfigs[side][chipid].enable_mask[i])

        return

    def update_regvar(self, var, ireg, nbits, start, name, index, mode):
        #print "RegisterConfigPanel.update_regvar: callback called with name=%r, index=%r, mode=%r, value=%r" % (name, index, mode, var.get())
        s = var.get()
        if len(s) != 0:
            val = int(var.get())
            mask = c_uint8(0x00)
            clear_mask = mask
            for i in range(0,nbits):
                mask.value |= 1<<(i+start)
            clear_mask = c_uint8(~mask.value)
            self.reg_vars[ireg] &= clear_mask.value # clear the field we are updating (leave the rest as is)
            self.reg_vars[ireg] |= val<<start # OR in the the value
        return

    def send_register_value(self,cmd,register):
        side = self.get_chip_sideid()
        chipid = self.get_chipid()
        varray = self.chipconfigs[side][chipid].reg_vars
        wedgeaddr = None
        if use_roc.get():
            #print 'set wedgeaddr, using ROC'
            wedgeaddr = (0xF & self.moduleid) | (0xF & self.get_chip_sideid())<<4
        femaddr = None
        if use_roc.get() == 2: femaddr = femaddr_var.get()

        if cmd == FPHX_WRITE: # If writing to the reg, send the value given
            val = int(varray[register])
        elif register == 0 and (cmd == FPHX_SET or cmd == FPHX_RESET):
            # if the first reg, and doing set or reset, use the value given
            val = int(varray[register])
        else:
            # some registers and command combos ignore the bits (eg. Set and Reset in registers > 0)
            val = 0
        
        #print 'send register %d the value %d' % (register,val)
        data = 0xFF & val
        regid = register + 1 # address starts from 1
        word = make_fphx_cmd(chipid,regid,cmd,data)
        #print 'use_roc.get = ', use_roc.get()
        #print 'self.moduleid = ', self.moduleid
        #print 'self.get_chip_sideid = ', self.get_chip_sideid()
        if wedgeaddr is not None: print 'wedgeaddr = %d 0x%02x' % (wedgeaddr,wedgeaddr)
        else: print 'wedgeaddr = None'
        print 'chipid = %d 0x%02x' % (chipid, chipid)
        print 'cmd    = %d 0x%02x' % (cmd, cmd)
        print 'regid  = %d 0x%02x' % (regid, regid)
        print 'data   = %d 0x%02x' % (data, data)
        print 'FPHX command = 0x%x' % word
        buf = create_packet_fphx(word,wedgeaddr,femaddr)
        print 'Send FPHX packet = %s' % hexify_bytes(buf)
        write_bytes_to_target(buf.raw,comm_panel.getTarget())    
        return

    # Toggle the colors around to show the user what's new
    # in the readback display boxes.
    def update_rb_status(self,reg):
        for i in range(18):
            self.rb_entries[i].config(fg='black')
            self.rb_entries[reg].config(fg='red')
        return

    # Read a register for its value.  Update the display with the value.
    # TODO: add side 
    def readback_register(self,reg):
        chipid = int(self.get_chipid())
        if chipid == 21:
            tkMessageBox.showwarning("Read from Chip","Cannot read from Wildchip ID")
            return
        print 'readback_register: chipid %d regid %d' % (chipid,reg)
        wedgeaddr = None
        if use_roc.get(): wedgeaddr = (0xF & self.moduleid) | (0xF & self.get_chip_sideid())<<4
        femaddr = None
        if use_roc.get() == 2: femaddr = femaddr_var.get()
        cmd = FPHX_READ
        data = 0
        regid = reg + 1 # address starts from 1
        word = make_fphx_cmd(chipid,regid,cmd,data)
        print 'chipid = %d 0x%02x' % (chipid, chipid)
        print 'cmd    = %d 0x%02x' % (cmd, cmd)
        print 'regid  = %d 0x%02x' % (regid, regid)
        print 'data   = %d 0x%02x' % (data, data)
        print 'FPHX command = 0x%x' % word
        buf = create_packet_fphx(word,wedgeaddr,femaddr)
        # Read twice because of funny buffering in the DLP USB chip
        for i in range(2):
            print 'Send FPHX packet = %s' % hexify_bytes(buf)
            val = write_bytes_to_target(buf.raw,comm_panel.getTarget(),comm_panel.getBaudRate())    
            print 'readback value = ',val
            time.sleep(0.05)
        if val == None:
            self.rb_vals[reg].set('n/a')
        else:
            self.rb_vals[reg].set(str(val))
        self.update_rb_status(reg)
        return

    def get_module_enable(self):
        return self.module_enable.get()

    def set_module_enable(self,val):
        print 'set enable %d for module %d' % (val,self.moduleid)
        if ( val != 0 ): self.module_enable.set(1)
        else: self.module_enable.set(0)

    def get_chipconfig_enable(self):
        return self.chipconfig_enable.get()

    def set_chipconfig_enable(self,val):
        print 'set chipconfig enable %d for module %d' % (val,self.moduleid)
        if ( val != 0 ): self.chipconfig_enable.set(1)
        else: self.chipconfig_enable.set(0)
        return

    # Return the moduleid of this panel
    def get_moduleid(self):
        return int(self.moduleid)

    # Return the side number of the currently displayed chip configuration
    def get_chip_sideid(self):
        if self.side_selection.get() == "Side 15": return 15
        if self.side_selection.get() == "Side 0": return 0
        else : return 1
        return

    # Return the value of the active "side".  This can be 0xFF (both), 0 or 1
    def get_side_enable(self):
        return self.side_enable.get()

    def set_side_enable(self,val):
        print 'set side enable Module %d Side %d' % (self.moduleid,val)
        return

    # Return the chip id of the currently displayed configuration
    def get_chipid(self):
        return int(self.chipid_entry.results.get()) 

    def send_reset(self):
        for i in range(0,len(self.chan_btn)):
            self.chan_btn[i].deselect()
            self.chan_btn[i].config(fg='white')
            
        wedgeaddr = (0xF & self.get_moduleid()) | (0xF & self.get_side_enable())<<4
        femaddr = None
        if use_roc.get() == 2: femaddr = femaddr_var.get()
        if use_roc.get()>1: print "send_reset: write to wedge addr 0x%02x fem addr 0x%02x" % (wedgeaddr,femaddr)
        elif use_roc.get()>0: print "send_reset: write to wedge addr 0x%02x fem addr (None)" % (wedgeaddr)
        else: print "send_reset: write to wedge addr (None) fem addr (None)"
        reset_fphx(wedgeaddr,femaddr,comm_panel.getTarget())
        return

    # Attempt at implementing some sort of oft-used idiom for looping over the chips 
    # and calling a function for each one.
    def loop_chips(self,func):
        #for iside in range(0,len(self.chipconfigs)):
        for iside in (lambda sk=self.chipconfigs.keys(): sk.sort(side_cmp) or sk)():
            if self.get_side_enable() == 0xFF or self.get_side_enable() == iside:
                wedgeaddr = None
                if use_roc.get(): wedgeaddr = (0xF & self.moduleid) | (0xF & iside)<<4
                femaddr = None
                if use_roc.get() == 2: femaddr = femaddr_var.get()
                for key in (lambda k=self.chipconfigs[iside].keys(): k.sort(chip_cmp) or k)():
                    #print 'side %d chipid %d' % (iside,key)
                    # IF the chip is enabled for BOTH (ie 0xFF), fire off the action.  If 0xFF side is
                    # not enabled, check if this specific side is.  If so, fire off the action.
                    if self.chip_enables[15][key].get() or self.chip_enables[iside][key].get():
                        #print "RegisterConfigPanel.loop_chips: call %s for side %d chipid %d wedgeaddr 0x%02x" % (func,iside,key,lambda: wedgeaddr if wedgeaddr else 0)
                        func(self.chipconfigs[iside][key],wedgeaddr,femaddr)
                    else:
                        #print "RegisterConfigPanel.loop_chips: side %d chipid %d not enabled, skipping,  wedgeaddr 0x%02x" % (iside,key,wedgeaddr)
                        pass
            else:
                print "RegisterConfigPanel.loop_chips: side %d not enabled, skipping" % iside
        return

    def send_init(self):
        print 'Send init for module %d chip %d' % (self.moduleid,int(self.chipid_entry.results.get()))
        self.loop_chips(ChipConfig.send_init)
        return

    def send_enable_ro(self):
        print 'Send enable RO for module %d chip %d' % (self.moduleid,int(self.chipid_entry.results.get()))
        self.loop_chips(ChipConfig.send_enable_ro)
        return

    def send_disable_ro(self):
        print 'Send disable RO for module %d chip %d' % (self.moduleid,int(self.chipid_entry.results.get()))
        self.loop_chips(ChipConfig.send_disable_ro)
        return

    def send_core_reset(self):
        print 'Send core reset for module %d chip %d' % (self.moduleid,int(self.chipid_entry.results.get()))
        self.loop_chips(ChipConfig.send_core_reset)
        return

    def send_bco_reset(self):
        print 'Send BCO reset for module %d chip %d' % (self.moduleid,int(self.chipid_entry.results.get()))
        self.loop_chips(ChipConfig.send_bco_reset)
        return

    def send_calib(self):
        # First send a Core Reset to all currently displayed chip.  TODO: replace with a loop
        # over the enabled chips in the Chip Enable panel
        wedgeaddr = None
        if use_roc.get(): wedgeaddr = (0xF & self.moduleid) | (0xF & self.get_side_enable())<<4
        femaddr = None
        if use_roc.get() == 2: femaddr = femaddr_var.get()
        prog_reset_fphx(int(self.chipid_entry.results.get()),FPHX_RESET,wedgeaddr,femaddr)
        # Now tell the TB to calibrate
        do_bco_reset = 0
        print 'femaddr = ', femaddr
        calib_fphx(wedgeaddr,femaddr,comm_panel.getTarget())
        return

    # Set the states of all the channel select buttons to be off
    def mask_all(self):
        side = self.get_chip_sideid()
        chipid = int(self.chipid_entry.results.get())
        print "Mask all for module %d side %d chip %d" % (self.moduleid,side,chipid)
        for i in range(0,len(self.chan_btn)):
            self.chan_btn[i].deselect()
            #print 'enable_mask[%d] = %d' % (i,self.chipconfigs[side][chipid].enable_mask[i].get())
        return

    # Set the states of all the channel select buttons to be on
    def unmask_all(self):
        side = self.get_chip_sideid()
        chipid = int(self.chipid_entry.results.get())
        print "Unmask all for module %d side %d chip %d" % (self.moduleid,side,chipid)
        for i in range(0,len(self.chan_btn)):
            self.chan_btn[i].select()
            #print 'enable_mask[%d] = %d' % (i,self.chipconfigs[side][chipid].enable_mask[i].get())
        return

    # Toggle the states of the channel select buttons
    def toggle_all(self):
        for i in range(0,len(self.chan_select)):
            if self.chan_select[i].get() == 1:
                self.chan_select[i].set(0)
                self.chan_btn[i].deselect()
            else:
                self.chan_select[i].set(1)
                self.chan_btn[i].select()
        return

    # Take the current state of the channel select buttons and send them to the chip
    def send_mask(self):
        side = self.get_chip_sideid()
        chipid = self.get_chipid()
        wedgeaddr = None
        if use_roc.get(): wedgeaddr = (0xF & self.moduleid) | (0xF & side)<<4
        femaddr = None
        if use_roc.get() == 2: femaddr = femaddr_var.get()
        print 'RegisterConfigPanel.send_mask: Module %d Side %d ChipId %d' % (self.moduleid,side,chipid)
        self.chipconfigs[side][chipid].send_mask(wedgeaddr,femaddr)
        return

    def get_enablemask(self):
        # Loop over the channel masks
        mask = [ 0, 0, 0, 0, 0, 0, 0, 0 ]
        #for i in range(0,128):
        #    if self.chan_select[i].get() == 1:
        #        mask[int(i/16)] |= 1<<(i%16)
        return mask

    def get_regvals(self):
        # Return a list of the current register values from reg 2 to 16
        side = self.get_chip_sideid()
        chipid = self.get_chipid()
        return [ self.chipconfigs[side][chipid].reg_vars[i] for i in range(1,17) ]

    # Return a list of enabled "packed" chip ids.
    def get_enabled_chipids(self):
        chipids = []
        for iside in (lambda sk=self.chipconfigs.keys(): sk.sort(side_cmp) or sk)():
            wedgeaddr = (0xF & self.moduleid) | (0xF & iside)<<4
            for key in (lambda k=self.chipconfigs[iside].keys(): k.sort(chip_cmp) or k)():
                if self.side_enable.get() == 15 or self.side_enable.get() == iside:
                    if self.chip_enables[iside][key].get():
                        packed_id = (wedgeaddr << 5) | (0x1F & key)
                        chipids.append(packed_id)
        return chipids

    def get_enabled_enablemasks(self):
        enabled_masks = []
        for iside in (lambda sk=self.chipconfigs.keys(): sk.sort(side_cmp) or sk)():
            wedgeaddr = (0xF & self.moduleid) | (0xF & iside)<<4
            for key in (lambda k=self.chipconfigs[iside].keys(): k.sort(chip_cmp) or k)():
                if self.side_enable.get() == 15 or self.side_enable.get() == iside:
                    if self.chip_enables[iside][key].get():
                        masks = self.get_enablemask()
                        enabled_masks.append(masks)
        return masks

    def get_config_lists(self):
        configs = []
        for iside in (lambda sk=self.chipconfigs.keys(): sk.sort(side_cmp) or sk)():
            wedgeaddr = (0xF & self.moduleid) | (0xF & iside)<<4
            for key in (lambda k=self.chipconfigs[iside].keys(): k.sort(chip_cmp) or k)():
                if self.side_enable.get() == 15 or self.side_enable.get() == iside:
                    if self.chip_enables[iside][key].get():
                        config = self.chipconfigs[iside][key].get_config_list()
                        config[0] = wedgeaddr<<5 | (0x1F&config[0]) # Pack the wedgeaddr into the chipid field
                        print config
                        configs.append(config)
        return configs

if __name__ =='__main__':

    master = Tix.Tk()
    master.title( "FPHX TestStand DAQ" )

    # create the menubar
    menubar = Menu(master)

    filemenu = Menu(menubar, tearoff=0)
    filemenu.add_command(label="Open", command=lambda: read_config(), accelerator='Ctrl-O')
    master.bind('<Control-o>',lambda *args: read_config(*args))
    filemenu.add_command(label="Save", command=lambda : save_config(configfname), accelerator='Ctrl-S')
    master.bind('<Control-s>',lambda *args: save_config(*args))
    filemenu.add_command(label="Save As", command=lambda : saveas_config(), accelerator='...')
    filemenu.add_separator()
    filemenu.add_command(label="Quit", command=master.destroy,  # better than root.quit (at least in IDLE)
                         accelerator='Ctrl-Q')
    master.bind('<Control-q>','exit') # Type Ctrl-q to exit application
    
    menubar.add_cascade(label="File", menu=filemenu)
    master.config(menu=menubar)


    # Create a frame to hold everything
    #top_frame = Frame(master)
    #top_frame.pack(fill=X, side=TOP)
    sw = Tix.ScrolledWindow(master,scrollbar=BOTH)
    sw.pack(fill=BOTH, expand=1)
    top_frame = sw.window

    nb = Tix.NoteBook(top_frame, name='nb', ipadx=6, ipady=6)
    nb.grid(row=0, column=0, rowspan=20)

    use_roc = IntVar(None,2)
    tbselect_frame = LabelFrame(top_frame,text='TestStand')
    tbselect_frame.grid(row=0,column=1,stick=W)
    Radiobutton(tbselect_frame,variable=use_roc,value=0,text='Spartan3').grid(row=0,column=0)
    Radiobutton(tbselect_frame,variable=use_roc,value=1,text='ROC').grid(row=0,column=1)
    Radiobutton(tbselect_frame,variable=use_roc,value=2,text='ROC+FEM',padx=10).grid(row=0,column=2)
    fem_frame = Frame(tbselect_frame,relief=RIDGE,bd=1,padx=10)
    fem_frame.grid(row=0,column=3)
    femaddr_var = IntVar(None,fem_addr_const)
    Label(fem_frame,text="FEM Addr",justify=RIGHT).grid(row=0,column=1)
    Entry(fem_frame,textvariable=femaddr_var,width=5,justify=RIGHT).grid(row=0,column=2)

    use_db = IntVar(None,0)
    #use_db.trace("w",lambda *args: fphxtb.dbaccess=1)
    dbselect_frame = LabelFrame(top_frame,text="DB Access")
    dbselect_frame.grid(row=0,column=2,stick=W)
    Radiobutton(dbselect_frame,variable=use_db,value=1,text='On').grid(row=0,column=0)
    Radiobutton(dbselect_frame,variable=use_db,value=0,text='Off').grid(row=0,column=1)
    

    # Create an operations frame for the ops buttons    
    ops_frame = LabelFrame(top_frame,text='Global Chip/DAQ Operations')
    ops_frame.grid(row=1,column=1,sticky=NW,columnspan=2)

    daq_frame = LabelFrame(top_frame,text='DAQ Configuration')
    daq_frame.grid(row=2,column=1,sticky=N+W+E+S,columnspan=2)

    pulser_frame = LabelFrame(top_frame,text='Pulser Configuration')
    pulser_frame.grid(row=3,column=1,sticky=N+W+E+S,columnspan=2)
        
    module_frame = LabelFrame(top_frame,text='Module Enable')
    module_frame.grid(row=4,column=1,sticky=N+W+E+S,columnspan=2)

    manual_frame = LabelFrame(top_frame,text='Manual Packet Send')
    manual_frame.grid(row=5,column=1,sticky=N+W+E+S,columnspan=2)

    regpanels = []
    moduleid = [ 15, 0, 1 ]
    sideid = [ 15, 0, 1 ]
    chipids = [ i for i in range(0,32) ]
    for imod in range(0,len(moduleid)):
        name = "module_%d" % (moduleid[imod])
        title = "Module %d" % (moduleid[imod])
        tab = nb.add(name, label=title)

        chipconfigs = {}
        for iside in range(0,len(sideid)):
            chipconfigs[sideid[iside]] = {}
            for ichip in range(0,len(chipids)):
                chipconfigs[sideid[iside]][chipids[ichip]] = ChipConfig(chipids[ichip])

        regpanel = RegisterConfigPanel(tab,moduleid[imod],chipids[0],chipconfigs)
        if moduleid[imod] == 15:
            regpanel.set_module_enable(1)
            regpanel.set_chipconfig_enable(1)
        regpanel.grid(row=0,column=0)
        regpanels.append(regpanel)

    #master.bind('<Control-p>',print_configs) # Type Ctrl-p to print the chip configs
    #master.bind('<Control-p>',lambda *args: updatedb(regpanels)) # Type Ctrl-p to print the chip configs
    master.bind('<Control-p>',lambda *args: open_socket(regpanels)) # Type Ctrl-p to print the chip configs
            
    # Fill the chip-operations panel
    daq_prog = StringVar(None,daq_program)
    col = 0
    reset_button = Button(ops_frame,text="FFR",width=10,bg='magenta')
    reset_button.grid(row=1,column=col,sticky=N)
    reset_button.config(command=(lambda: send_reset(regpanels)))
    init_button = Button(ops_frame,text="Init",width=10,bg='cyan')
    init_button.grid(row=2,column=col,sticky=N)
    init_button.config(command=lambda: send_init(regpanels))
    fo_sync_button = Button(ops_frame,text="FO Sync",width=10,bg='magenta')
    fo_sync_button.grid(row=3,column=col,sticky=N)
    fo_sync_button.config(command=(lambda: send_fo_sync()))
    fpga_reset_button = Button(ops_frame,text="FPGA RST",width=10,bg='cyan')
    fpga_reset_button.grid(row=4,column=col,sticky=N)
    fpga_reset_button.config(command=(lambda: send_fpga_reset()))
    col += 1
    erseeprom_button = Button(ops_frame,text="Er. EEPROM",width=10,bg='light blue')
    erseeprom_button.grid(row=4,column=col,sticky=N)
    erseeprom_button.config(command=lambda : erase_eeprom(0x0F))    
    enaRO_button = Button(ops_frame,text="Enable RO",width=10,bg='green')
    enaRO_button.grid(row=1,column=col,sticky=N)
    enaRO_button.config(command=lambda : send_enable_ro(regpanels))
    disRO_button = Button(ops_frame,text="Disable RO",width=10,bg='red',fg='white')
    disRO_button.grid(row=2,column=col,sticky=N)
    disRO_button.config(command=lambda : send_disable_ro(regpanels))
    fem_set_lvl1_delay_button = Button(ops_frame,text="Set L1 Delay",width=10,bg='green')
    fem_set_lvl1_delay_button.grid(row=3,column=col,sticky=N)
    fem_set_lvl1_delay_button.config(command=(lambda: send_fem_lvl1_delay(int(fem_lvl1_delay_var.get()))))
    col += 1
    wp_button = Button(ops_frame,text="Write Page",width=10,bg='light blue')
    wp_button.grid(row=4,column=col,sticky=N)
    wp_button.config(command=(lambda: write_page(0x0f,3,2,1,6)))
##    wp_button.config(command=(lambda: test_write()))    
    latch_button = Button(ops_frame,text="Latch FPGA",width=10,bg='pink')
    latch_button.grid(row=1,column=col,sticky=N)
    latch_button.config(command=(lambda: send_latch()))
    calib_button = Button(ops_frame,text="Calib",width=10,bg='yellow')
    calib_button.grid(row=2,column=col,sticky=N)
    calib_button.config(command=(lambda: send_calib()))
    fem_lvl1_delay_var = IntVar(None,fem_lvl1_delay_const)
    fem_delay_frame = Frame(ops_frame,relief=RIDGE,bd=1,padx=5)
    fem_delay_frame.grid(row=3,column=col)
    Label(fem_delay_frame,text="Delay",justify=RIGHT).grid(row=3,column=col)
    Entry(fem_delay_frame,textvariable=fem_lvl1_delay_var,width=3,justify=RIGHT).grid(row=3,column=col+1)
    col += 1
    rp_button = Button(ops_frame,text="Read Page",width=10,bg='yellow')
    rp_button.grid(row=4,column=col,sticky=N)
##    rp_button.config(command=(lambda: read_page(0x0f,2,1,1,5)))
    rp_button.config(command=(lambda: read_page2(0x0f,3,2,1,6)))    
    corerst_button = Button(ops_frame,text="Core Reset",width=10,bg='light blue')
    corerst_button.grid(row=1,column=col,sticky=N)
    corerst_button.config(command=lambda: send_core_reset(regpanels))
    timerst_button = Button(ops_frame,text="BCO Reset",width=10,bg='light blue')
    timerst_button.grid(row=2,column=col,sticky=N)
    timerst_button.config(command=lambda: send_bco_reset(regpanels))
    bco_start_button = Button(ops_frame,text="BCO Start",width=10,bg='green')
    bco_start_button.grid(row=3,column=col,sticky=N)
    bco_start_button.config(command=(lambda: send_bco_start()))     
    col += 1
    wa_button = Button(ops_frame,text="Write All",width=10,bg='light blue')
    wa_button.grid(row=4,column=col,sticky=N)
    wa_button.config(command=(lambda: write_initpages_eeprom()))   
    b = Button(ops_frame,text="Start DAQ",width=10,bg='green')
    b.grid(row=1,column=col)
    b.config(command=lambda : start_daq_prog(regpanels))
    b = Button(ops_frame,text="Stop DAQ",width=10,bg='red',fg='white')
    b.grid(row=2,column=col)
    b.config(command=lambda : stop_daq_prog())

    b = Button(ops_frame,text="Global Start",width=10,bg='black',fg='white')
    b.grid(row=3,column=col)
    b.config(command=lambda : global_start_daq_prog())
    col += 1

    irow = 0
    icol = 0
    irow += 1
    Label(daq_frame,text="DAQ Program").grid(row=irow,column=icol,sticky=W)
    icol += 1
    Entry(daq_frame,textvariable=daq_prog,width=20).grid(row=irow,column=icol,sticky=W)
    icol += 1
    b = Button(daq_frame,text="Browse",width=10)
    b.grid(row=irow,column=icol)
    b.config(command=lambda b=daq_prog: browse_daq_prog(b))
    irow += 1
    icol = 0
    sample_MHz_var = StringVar(None,'5')
    Label(daq_frame,text="NI DAQ Sample Rate (MHz)").grid(row=irow,column=icol,sticky=W)
    icol += 1
    Entry(daq_frame,textvariable=sample_MHz_var,width=10,justify=RIGHT).grid(row=irow,column=icol,sticky=W)
    irow += 1    
    icol = 0
    num_events = StringVar(None, '0')
    Label(daq_frame,text="Num of events (0==inf)").grid(row=irow,column=icol,sticky=W)
    icol += 1
    Entry(daq_frame,textvariable=num_events,width=10,justify=RIGHT).grid(row=irow,column=icol,sticky=W)
    irow += 1    
    icol = 0
    duration_var = StringVar(None, 'HH:MM:SS')
    Label(daq_frame,text="Duration HH:MM:SS (0:00:00==inf)").grid(row=irow,column=icol,sticky=W)
    icol += 1
    Entry(daq_frame,textvariable=duration_var,width=10,justify=RIGHT).grid(row=irow,column=icol,sticky=W)
    irow += 1
    icol = 0
    printData = IntVar(None,0)
    printDataText = StringVar(None,'Print Off')
    Label(daq_frame,text="Print Output",justify=LEFT).grid(row=irow,column=icol,sticky=W)
    icol += 1
    print_btn = Checkbutton(daq_frame, text='Print off', bg='red', fg='white', width=10, height=1,
                            indicatoron=0, selectcolor='green',variable=printData, textvariable=printDataText)
    printData.trace("w",lambda *args: print_data(print_btn,args))
    print_btn.grid (row=irow, column=icol,sticky=W)
    irow += 1
    icol = 0
    Label(daq_frame,text="FPHX version (for Print)",justify=LEFT).grid(row=irow,column=icol,sticky=W)
    icol += 1
    chipVersionList = ( "1", "2" )
    chipVersions = StringVar(None,chipVersionList[1])
    chipversion_menu = OptionMenu(daq_frame,chipVersions,*chipVersionList)
    chipversion_menu.grid(row=irow, column=icol,sticky=W)

    # The runnumber and filename widgets are Entry, even though I disable the ability
    # to modify them.  What I really needed was more like Label, but I also like the
    # fact that the textvariable is automatically redisplayed when it changes.  So when
    # the GUI constructs the filename based on date and run number, it gets dislayed automatically
    # here.  I use the "readonly" state because this allows the user to cut and paste the
    # the text (DISABLED does not).
    runnumber = StringVar(None,'')
    filename = StringVar(None,'')
    beamlist = ( "None","Cosmic Ray","proton" )
    beam_species = StringVar(None,beamlist[0])
    beam_energy = StringVar(None,'0')
    irow += 1
    icol = 0
    Label(daq_frame,text="Run Number",justify=LEFT).grid(row=irow,column=icol,sticky=W)
    runnumber_label = Entry(daq_frame,textvariable=runnumber,justify=LEFT)
    runnumber_label.grid(row=irow,column=1,sticky=W)
    runnumber_label.config(relief=FLAT,state="readonly")
    irow += 1
    icol = 0
    Label(daq_frame,text="Filename",justify=LEFT).grid(row=irow,column=icol,sticky=W)
    filename_entry = Entry(daq_frame,textvariable=filename,justify=LEFT,width=34)
    icol += 1
    filename_entry.grid(row=irow,column=icol,sticky=W,columnspan=4)
    filename_entry.config(relief=FLAT,state="readonly")
    irow += 1
    icol = 0
    Label(daq_frame,text="Beam Species",justify=LEFT).grid(row=irow,column=icol,sticky=W)
    species_menu = OptionMenu(daq_frame,beam_species,*beamlist)
    icol += 1
    species_menu.grid(row=irow,column=icol,sticky=W)
    irow += 1
    icol = 0
    Label(daq_frame,text="Beam Energy",justify=LEFT).grid(row=irow,column=icol,sticky=W)
    energy_entry = Entry(daq_frame,textvariable=beam_energy,justify=RIGHT,width=10)
    icol += 1
    energy_entry.grid(row=irow,column=icol,sticky=W)

    # Pulser configuration
    #
    num_pulses = StringVar(None,'1')
    bco_spacing = StringVar(None,'1023')
    pulse_amp = StringVar(None,'255')
    w = lambda x: x if use_roc.get() else None # quickie fix to adding conditional wedgeaddr to lambda expression
    f = lambda x: x if use_roc.get()>1 else None # quickie fix to adding conditional femaddr to lambda expression
    col = 0
    irow = 0
    irow += 1
    numpulses_line = Frame(pulser_frame)
    numpulses_line.grid(row=irow,column=col)
    col = 0
    Label(numpulses_line,text="Pulse amplitude (10 bits max)",justify=LEFT).grid(row=0,column=col,sticky=W)
    col += 1
    Entry(numpulses_line,textvariable=pulse_amp,width=10,justify=RIGHT).grid(row=0,column=col)
    col += 1
    b = Button(numpulses_line,text="Config Amp",width=10,bg='light blue')
    b.grid(row=0,column=col,sticky=E,padx=2)
    #b.config(command=lambda: write_pulse_amp(int(pulse_amp.get()),w(0xFF)))
    b.config(command=lambda: write_pulse_amp(int(pulse_amp.get()),w(0xFF),f(int(femaddr_var.get())),comm_panel.getTarget()))
    col += 1
    b = Button(numpulses_line,text="Pulse",width=10,bg='light blue')
    b.grid(row=0,column=col,sticky=E,padx=2)
    b.config(command=lambda: send_pulse(int(pulse_amp.get()),w(0xFF),f(int(femaddr_var.get()))))

    irow = 1
    col = 0
    #Label(numpulses_line,text="Amplitude bits",justify=LEFT).grid(row=irow,column=col,sticky=W)
    #col += 1
    ampbits = IntVar(None,8);
    ampbits_frame = Frame(numpulses_line)
    #ampbits_frame.grid(row=irow,column=col,stick=W)
    #Radiobutton(ampbits_frame,variable=ampbits,value=8,text='8').grid(row=0,column=0)
    #Radiobutton(ampbits_frame,variable=ampbits,value=16,text='16',state=DISABLED).grid(row=0,column=1)
    #irow += 1
    #col = 0
    Label(numpulses_line,text="Num of Pulses",justify=LEFT).grid(row=irow,column=col,sticky=W)
    col += 1
    Entry(numpulses_line,textvariable=num_pulses,width=10,justify=RIGHT).grid(row=irow,column=col)
    col += 1
    b = Button(numpulses_line,text="Pulse Train",width=10,bg='light blue')
    b.grid(row=irow,column=col,sticky=E,padx=2)
    b.config(command=lambda: write_pulse_train(int(num_pulses.get()),int(bco_spacing.get()),
                                               int(pulse_amp.get()),w(0xFF),f(int(femaddr_var.get())),
                                               comm_panel.getTarget()))
    irow += 1
    col = 0
    Label(numpulses_line,text="BCOs between pulses",justify=LEFT).grid(row=irow,column=col,sticky=W)
    col += 1
    Entry(numpulses_line,textvariable=bco_spacing,width=10,justify=RIGHT).grid(row=irow,column=col)
    col += 1

    #Set the wedge number that you want to pulse (0-3)
    pulse_wedge_var = IntVar(None,pulse_wedge_const)
    #pulse_wedge_frame = Frame(pulser_frame,relief=RIDGE,bd=1,padx=5)
    pulse_wedge_frame = Frame(numpulses_line,relief=RIDGE,bd=1,padx=5)
    pulse_wedge_frame.grid(row=irow,column=col+2)
    Label(pulse_wedge_frame,text="Wedge",justify=RIGHT).grid(row=irow,column=col+2)
    Entry(pulse_wedge_frame,textvariable=pulse_wedge_var,width=3,justify=RIGHT).grid(row=irow,column=col+3)


    #Set the wedge side that you want to pulse (0-7 for station 0, side 0, station 0, side 1....)    
    pulse_module_var = IntVar(None,pulse_module_const)
    pulse_module_frame = Frame(numpulses_line,relief=RIDGE,bd=1,padx=5)
    pulse_module_frame.grid(row=irow+1,column=col+2)
    Label(pulse_module_frame,text="Module",justify=RIGHT).grid(row=irow,column=col+2)
    Entry(pulse_module_frame,textvariable=pulse_module_var,width=3,justify=RIGHT).grid(row=irow,column=col+3)
    col +=1
    set_pulse_module_button = Button(numpulses_line,text="Set Module",width=10,bg='green')
    set_pulse_module_button.grid(row=irow+1,column=col+3,sticky=N)
    set_pulse_module_button.config(command=(lambda: send_pulse_module(int(pulse_module_var.get()),
                                                                      int(pulse_wedge_var.get()), f(int(femaddr_var.get())))))
    #set_pulse_module_button.config(command=(lambda: send_pulse_module(int(pulse_module_var.get(), f(int(femaddr_var.get()))))))
    
    irow = 0
    module_enables = []
    side_enables = []
    for i in range(0,len(moduleid)):
        icol = 0
        name = "Module %d" % moduleid[i]
        Label(module_frame,text=name,justify=LEFT).grid(row=irow,column=icol)
        icol += 1
        # Create a check button to enable/disable the state of this module
        module_enables.append(IntVar(None,0))
        if moduleid[i] == 15: module_enables[i].set(1)
        Checkbutton(module_frame,indicatoron=0,text='On', variable=module_enables[i],selectcolor='green',
                    command=lambda i=i:regpanels[i].set_module_enable(module_enables[i].get())
                    ).grid(row=irow,column=icol)
        icol += 1
        Checkbutton(module_frame,indicatoron=0,text='Off',variable=module_enables[i],onvalue=0,offvalue=1,selectcolor='red',
                    command=lambda i=i:regpanels[i].set_module_enable(module_enables[i].get())
                    ).grid(row=irow,column=icol)
        icol += 1
        side_enables.append(IntVar(None,15))
        regpanels[i].side_enable = side_enables[i]
        Radiobutton(module_frame,variable=side_enables[i],value=15,text='Both',
                    command=lambda i=i:regpanels[i].set_side_enable(side_enables[i].get())
                    ).grid(row=irow,column=icol)
        icol += 1
        Radiobutton(module_frame,variable=side_enables[i],value=0, text='Side 0',
                    command=lambda i=i:regpanels[i].set_side_enable(side_enables[i].get())
                    ).grid(row=irow,column=icol)
        icol += 1
        Radiobutton(module_frame,variable=side_enables[i],value=1, text='Side 1',
                    command=lambda i=i:regpanels[i].set_side_enable(side_enables[i].get())
                    ).grid(row=irow,column=icol)
        icol += 1
        irow += 1

    # Manual packet operation frame
    irow = 0
    icol = 0
    manual_packet = StringVar(None,"")
    Label(manual_frame,text="Packet file to send").grid(row=irow,column=icol)
    icol += 1
    Entry(manual_frame,textvariable=manual_packet).grid(row=irow,column=icol)
    icol += 1
    Button(manual_frame,text="Browse",command=lambda: browse_packet_file(manual_packet)).grid(row=irow,column=icol)
    icol += 1
    Button(manual_frame,text="Send",command=lambda: send_file(manual_packet)).grid(row=irow,column=icol)
    icol += 1

    # Create a communications frame for the I/O (USB or FTP)
    comm_panel = comm_panel.comm_panel(top_frame,text='Communications')
    comm_panel.grid(row=8,column=1,sticky=N+W+E+S,columnspan=2)

    save_config('junk.dat')

    master.mainloop()
