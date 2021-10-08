#!/usr/bin/python

# NB: from __future__ imports must occur at the beginning of the file
from __future__ import with_statement # >=2.5 only
from Tkinter import *
import tkMessageBox
import Tix
import time
from datetime import datetime
import sys, os
import socket
import traceback
import tkSimpleDialog
import logging
import Queue
import threading

import ProgressBar
import ps_panel
import env_panel
from fphxtb import *
import BeautifulSoup
import postdata


import tkSimpleDialog

global pspanel

DEBUG = 0

# The default location for output data
#data_dir = "C:\data"
#data_dir = "E:\data"
data_dir = "C:/e/data"

# The default location for the log files
default_logdir = "C:/e/log"
if sys.platform.count('linux')>0:
    default_logdir = '/scratch0/wedge_qa'

# Global socket for controlling comm to the daq program
#global sock
#sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
daq_host = "localhost"
daq_port = 9000

CHIPID_WILD = 21
REGID_WILD = 21
WEDGESIDE_WILD = 0xFF
tests_running = 0
vscan = []
iscan = []

class TestingStopped(Exception):    
    pass

def checkTesting():
    #print "checkTesting: tests_running = %d" % tests_running
    if not tests_running: raise TestingStopped
    return

# unpack a string of the form "1,20-29" into an array of numbers
# representing the selection
def select_numbers(selection):
    vals = []
    aa = re.split('\s*,\s*',selection) # break up comma-delimited list, removing whitespace as well
    for a in aa:
        # Search for matches to strings like '1-10' or '1-'.  For the latter, default to the max 13
        # Fail for strings like '-13'.  Works like this: match the first number (\d+), then match
        # a "-" delimiter one or more times, then if the minus was matched, try to match another number
        # 0 or 1 times.
        m = re.search('(\d+)(?P<minus>-)+(?(minus)(\d+))?',a)
        if m:
            first = m.group(1)
            last = m.group(3)
            if last == None: last = 13
            vals.extend(range(int(first),int(last)+1))
        else:
            # if the match failed, assume that we are dealing with a single number
            if a: vals.append(int(a))
    return vals

def open_socket():
    #global sock
    global daq_host
    global daq_port
    # Start from a known state.  Then connect to the listening port.
    # TODO: Consider having the GUI act as server; the socket could be opened
    # and setup before the DAQ subprocess is started, thereby removing any potential
    # race condition.
    #if sock is not None: sock.close()
    #sock = None
    sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    try:
        time.sleep(2)
        if DEBUG: print "Connecting to %s:%d" % (daq_host,daq_port)
        sock.connect((daq_host,daq_port))
    except Exception, e:
        logger.critical("Failed to connect to %s:%d. Exception type is %s" % (daq_host,daq_port,`e`))
        sock = None
    return sock

def start_daq(verbose,filter=None):
    sys_type = sys.platform
    runno = get_runnumber()
    #runnumber.set(str(runno))
    now = datetime.now()
    print_flag = ""
    roc_flag = ""
    filter_flag = ""
    if verbose: print_flag = "-p"
    if use_roc.get(): roc_flag = "-r"
    if filter:
        filter_flag = "-bco_min %d -bco_max %d" % (filter['bco_min'],filter['bco_max'])
    daq_prog = StringVar(None,"Debug/read_DAQ.exe")
    #filename = StringVar(None,"E:/data/fphx_raw_%s_%d.dat" % (now.strftime("%Y%m%d-%H%M"),runno))
    #filename = StringVar(None,"C:/e/data/fphx_raw_wedge%03d_%s_%d.dat" % (wedgenum_var.get(),
    #                                                                      now.strftime("%Y%m%d-%H%M"),runno))
    filename = StringVar(None,"C:/e/data/fphx_raw_wedge%03d_%s_%s_%d.dat" % (wedgenum_var.get(),wedgeSize.get(),
                                                                          now.strftime("%Y%m%d-%H%M"),runno))
    logger.info("DAQ filename: %s" % filename.get())
    #chipVersions = StringVar(None,"1")
    num_events = StringVar(None,"0")
    #sample_MHz_var = StringVar(None,"5")
    if sys_type == 'win32' :
        cmd = 'start %s %s %s %s -e %d -s %d -f %s -v %d' % (daq_prog.get(), filter_flag, print_flag, roc_flag,
                                                             int(num_events.get()),int(sample_MHz_var.get()),
                                                             filename.get(),int(chipVersions.get()))
    else:
        logger.critical("Unsupported system type")
        return None
    print 'cmdline: %s ' % (cmd)
    os.system(cmd)
    sock = open_socket()
    if sock == None:
        logger.error("Failed to open socket to daq program")
        raise Exception
    
    total_bytes = 8
    buf = create_string_buffer(total_bytes)
    offset = 0
    struct.pack_into("I",buf,offset,total_bytes/4-1) # Length of data payload in 32-bit words, excluding this integer
    offset += 4
    struct.pack_into("I",buf,offset,runno)
    offset += 4
    if DEBUG: print "Writing %d bytes to socket" % sizeof(buf)
    sock.send(buf.raw)
    if DEBUG: print "Wrote %d bytes to socket" % sizeof(buf)
    return sock

# Implementation of a simple meter, since Tix.Meter doesn't seem to exist in ActiveState 2.5
# python
class Meter(Frame):
   '''A simple progress bar widget.'''
   def __init__(self, master, fillcolor='orchid1', text='',value=0.0, **kw):
       Frame.__init__(self, master, bg='white')
       self.configure(**kw)

       self._c = Canvas(self, bg=self['bg'],width=self['width'], height=self['height'],highlightthickness=0, relief='flat',bd=0)
       #self._c.pack(fill='x', expand=1)
       self._c.grid(sticky=W+E)
       self._r = self._c.create_rectangle(0, 0, 0,int(self['height']), fill=fillcolor, width=0)
       self._t = self._c.create_text(int(self['width'])/2,int(self['height'])/2, text='')

       self.set(value, text)

   def set(self, value=0.0, text=None):
       #make the value failsafe:
       if value < 0.0:
           value = 0.0
       elif value > 1.0:
           value = 1.0
       if text == None:
       #if no text is specified get the default percentage string:
           text = str(int(round(100 * value))) + ' %'
       self._c.coords(self._r, 0, 0, int(self['width']) * value,int(self['height']))
       self._c.itemconfigure(self._t, text=text)
       self._c.update()


def send_init(chipid,wedgeaddr):
    #print 'send_init: Send init for chip %d' % chipid

    # Here are the values to send for each register.  Wre use a dictionary that
    # is keyed by register address.
    vals = { 1: 128, # Global mask all channels
             2: 0x5, # Global inject on, 2 Active lines
             3: 1, # Vref
             4: 8, # DAC0
             5: 16,
             6: 32,
             7: 48,
             8: 80,
             9: 112,
             10: 144,
             11: 176, # DAC7
             12: 6 | 4<<4,
             13: 4 | 0<<4,
             14: 0 | 4<<4,
             15: 2 | 8<<3,
             16: 5 | 0<<3,
             17: 15
            } 

    length = int(17*4+1) # 17 commands + one destination byte
    dest = TESTBENCH_FPHX # destination == 'to FPHX'

    #print "send_init: Chip %d WedgeAddr 0x%02X:" % (chipid,(lambda:wedgeaddr if wedgeaddr else 0)())
    #for r, o, v in zip(regs,ops,vals):
    #    print "Register %d: oper %d with val %d" % (r,o,v)

    if wedgeaddr:
        length += 1
    packetlen = length + 2 + 2  # total length = length + 2 bytes of marker + 2 bytes of length value
    packet = create_string_buffer(packetlen)
    offset = 0
    struct.pack_into("B",packet,offset,0xFF) # 
    offset += 1
    struct.pack_into(">H",packet,offset,length) # 
    offset += 2
    struct.pack_into("B",packet,offset,dest) # 
    offset += 1
    if wedgeaddr:
        struct.pack_into("B",packet,offset,wedgeaddr)
        offset += 1

    for regaddr, value in vals.iteritems():
        op = 1
        if regaddr == 1: op = 2
        word = make_fphx_cmd(chipid,regaddr,op,value)
        struct.pack_into(">I",packet,offset,word)
        offset += 4
                
    struct.pack_into("B",packet,offset,0xFF) #end of packet
    #print 'send_init: Send init packet = %s' % hexify_bytes(packet)
    write_bytes_to_usb(packet.raw)

def store_qa_db(logger,data):
    #username, password = password_tuple
    logger.info("Store QA data: %s" % data)
    url = "http://www.phenix.bnl.gov/WWW/p/draft/winter/work/devel/online/fvtx/Database/wedge_qa_entry.php"
    status = postdata.postdata(url,data)
    if status:
        logger.info("Finished storing QA data: %s" % data)
    else:
        logger.info("Failed to store QA data")
        do_retry = tkMessageBox.askretrycancel("Retry upload","Upload failed. Retry it?")
        if do_retry:
            store_qa_db(logger,data)
            #print "Retry not yet implemented. SORRY"
    return

class ScanLVDSReadbackCurrent:#(threading.Thread):
    def __init__(self,logger,progress_queue,pspanel):
        #threading.Thread.__init__(self)
        self.logger = logger
        self.progress_queue = progress_queue
        self.pspanel = pspanel
        self.min_lvds = IntVar(None,1)
        self.max_lvds = IntVar(None,15)
        self.name = "ScanLVDSReadBackCurrent"
        return

    def getName(self):
        return self.name

    def getPasscode(self):
        return self.task.passcode

    def getnumtasks(self):
        return len(range(self.min_lvds.get(),self.max_lvds.get()))

    def body(self,parent,color):
        f = Frame(parent,bg=color)
        Label(f,text="Min LVDS",bg=color).grid(row=0,column=0)
        Entry(f,textvariable=self.min_lvds,justify=RIGHT,width=5).grid(row=0,column=1)
        Label(f,text="Max LVDS",bg=color).grid(row=0,column=2)
        Entry(f,textvariable=self.max_lvds,justify=RIGHT,width=5).grid(row=0,column=3)
        return f

    def create_task(self):
        kwargs= {}
        kwargs['min_val'] = self.min_lvds.get()
        kwargs['max_val'] = self.max_lvds.get()
        kwargs['pspanel'] = self.pspanel
        self.task = ScanLVDSReadbackCurrent.Task(self.logger,self.progress_queue,kwargs=kwargs)
        return self.task

    class Task(threading.Thread):
        def __init__(self,logger,progress_queue,kwargs):
            threading.Thread.__init__(self)
            self.logger = logger
            self.progress_queue = progress_queue
            self.pspanel = kwargs['pspanel']
            self.min_lvds = kwargs['min_val']
            self.max_lvds = kwargs['max_val']
            self.passcode = 0
    
        def getnumtasks(self):
            return len(range(self.min_lvds,self.max_lvds+1))+1

        def run(self):
            try:
                checkTesting()
                self.progress_queue.put(('start',self.getnumtasks()))
                cmd = FPHX_WRITE
                regid = 17
                chipid = 21
                wedgeaddr = 0xFF
                reset_fphx(wedgeaddr)
                self.progress_queue.put(('update','reset fphx'))
                for data in range(self.min_lvds,self.max_lvds+1):
                    checkTesting()
                    write_fphx_cmd(chipid,regid,cmd,data,wedgeaddr)
                    self.progress_queue.put(('update','update LVDS value'))
                    time.sleep(0.1)
                    if self.pspanel: 
                        voltage = self.pspanel.getVoltage()
                        current = self.pspanel.getCurrent()
                        logger.info("%2i: %f V %f A" % (data,voltage,current))
                        vscan.append(voltage)
                        iscan.append(current)
                self.progress_queue.put(('done','success'))
                self.passcode = 1
            except TestingStopped:
                self.progress_queue.put(('done','failed with exception'))
            return

class ReadBackDefaultValues:
    def __init__(self,logger,progress_queue):
        self.logger = logger
        self.progress_queue = progress_queue
        self.name = "ReadBackDefaultValues"
        #self.regids = range(2,18)
        #self.sideids = range(0,2)
        self.chipid_var = [ StringVar(None,"1-5"),  StringVar(None,"1-5") ]

    def getName(self):
        return self.name

    def getPasscode(self):
        return self.task.passcode

    def body(self,parent,color):
        frame = Frame(parent,bg=color)
        Label(frame,text="ChipIds 0",bg=color).grid(row=0,column=6)
        Entry(frame,textvariable=self.chipid_var[0],justify=RIGHT,width=5).grid(row=0,column=7)
        Label(frame,text="ChipIds 1",bg=color).grid(row=1,column=6)
        Entry(frame,textvariable=self.chipid_var[1],justify=RIGHT,width=5).grid(row=1,column=7)
        return frame

    def wedgeSizeChanged(self,size):
        if size == 'Large':
            self.chipid_var[0].set("1-13")
            self.chipid_var[1].set("1-13")
        else:
            self.chipid_var[0].set("1-5")
            self.chipid_var[1].set("1-5")            

    def create_task(self):
        kwargs= {}
        kwargs['chipids_side0'] = select_numbers(self.chipid_var[0].get())
        kwargs['chipids_side1'] = select_numbers(self.chipid_var[1].get())
        self.task = ReadBackDefaultValues.Task(self.logger,self.progress_queue,kwargs=kwargs)
        return self.task

    class Task(threading.Thread):
        def __init__(self,logger,progress_queue,kwargs):
            threading.Thread.__init__(self)
            self.logger = logger
            self.progress_queue = progress_queue
            self.chipids = [ kwargs['chipids_side0'], kwargs['chipids_side1'] ]
            self.regids = range(2,18)
            self.sideids = range(0,2)
            self.expected = {  2:1,
                               3:1,
                               4:8,
                               5:16,
                               6:32,
                               7:48,
                               8:80,
                               9:112,
                              10:144,
                              11:176,
                              12:6+(4<<4),
                              13:4,
                              14:4<<4,
                              15:1+(4<<3),
                              16:5,
                              17:15 # Documentation says 16, but emperically it appears to be 15
                            }
            self.passcode = 0
            #print "Task"

        def getnumtasks(self):
            return (len(self.chipids[0])+len(self.chipids[1])) * len(self.regids) + 1
        
        def run(self):
            try:
                checkTesting()
                self.progress_queue.put(('start',self.getnumtasks()))
                cmd, data, wedgeaddr = FPHX_DEFAULT, 0, 0xFF
                reset_fphx(wedgeaddr)
                write_fphx_cmd(CHIPID_WILD,REGID_WILD,cmd,data,wedgeaddr)
                time.sleep(1.0)
                cmd = FPHX_READ
                moduleid = 0x0 # Default to large wedge module id #0xF
                if wedgeSize.get() == 'Small': moduleid = 0x1
                errors = 0
                for sideid in self.sideids:
                    self.logger.info("***** Side ID %d ******" % (sideid))
                    wedgeaddr = None
                    if use_roc.get(): wedgeaddr = (sideid<<4) | moduleid # Upper 4 bits are side, lower are module
                    for chipid in self.chipids[sideid]:
                        if wedgeaddr is None: self.logger.info(" ---- Chip ID %2d Wedgeaddr (None) ---- " % (chipid))
                        else:                 self.logger.info(" ---- Chip ID %2d Wedgeaddr 0x%02X ---- " % (chipid,wedgeaddr))
                        for regid in self.regids:
                            checkTesting()
                            write_fphx_cmd(chipid,regid,FPHX_DEFAULT,data,wedgeaddr)
                            val = write_fphx_cmd(chipid,regid,FPHX_READ,data,wedgeaddr)
                            if val is None: val = -1
                            if val != self.expected[regid]:
                                flag = "*** BAD ***"
                                errors += 1
                            else:
                                flag = ""
                            self.logger.info(" RegID %2d Value %3d Expected %3d %s" % (regid,val,self.expected[regid],flag))
                            self.progress_queue.put(('update','read register'))
                            time.sleep(0.2)
                self.progress_queue.put(('done','success'))
                if errors == 0: self.passcode = 1
            except TestingStopped:
                self.progress_queue.put(('done','failed with exception'))
            self.logger.info("Register Default Value errors = %d" % errors)
            return

# Class for checking if the chips respond to commands targeted at them
# The approach is a little different than just reading back the slow control. Because
# we want to verify that each responds only to its id and that id is unique, we enable
# them one by one and pulse.  If everything is OK we should only get hits from one chip
# at a time.
class ValidateChipIds:
    def __init__(self,name):
        self.name = name
        self.sideids = range(0,2) # reset to 2 when we have a 26-chip module
        self.channels_var = StringVar(None,"32,33")
        self.channels = [ 32, 33 ] # Choose an even and an odd?
        self.dac0_var = IntVar(None,8)
        self.npulses_var = IntVar(None,1)
        self.amp_var = IntVar(None,255)
        self.chipid_var = [ StringVar(None,"1-5"),
                            StringVar(None,"1-5") ]
        self.bcomin_var = IntVar(None,1)
        self.bcomax_var = IntVar(None,999)
        self.passcode = 0
        return

    def getName(self):
        return self.name

    def getPasscode(self):
        return self.passcode

    def getnumtasks(self):
        pass
        return self.npulses_var.get() * len(self.sideids) * len(self.chipid_var[0].get()+self.chipid_var[1].get())

    def body(self,parent,color):
        config_frame = Frame(parent,bg=color)
        Label(config_frame,text="ChipIds 0",bg=color).grid(row=0,column=0)
        Entry(config_frame,textvariable=self.chipid_var[0],justify=RIGHT,width=5).grid(row=0,column=1)
        Label(config_frame,text="ChipIds 1",bg=color).grid(row=1,column=0)
        Entry(config_frame,textvariable=self.chipid_var[1],justify=RIGHT,width=5).grid(row=1,column=1)
        Label(config_frame,text="DAC0",bg=color).grid(row=0,column=2)
        Entry(config_frame,textvariable=self.dac0_var,justify=RIGHT,width=5).grid(row=0,column=3)
        Label(config_frame,text="Amp",bg=color).grid(row=0,column=4)
        Entry(config_frame,textvariable=self.amp_var,justify=RIGHT,width=5).grid(row=0,column=5)
        Label(config_frame,text="Npulses",bg=color).grid(row=0,column=6)
        Entry(config_frame,textvariable=self.npulses_var,justify=RIGHT,width=5).grid(row=0,column=7)
        Label(config_frame,text="BCO min",bg=color).grid(row=1,column=2)
        Entry(config_frame,textvariable=self.bcomin_var,justify=RIGHT,width=5).grid(row=1,column=3)
        Label(config_frame,text="BCO max",bg=color).grid(row=1,column=4)
        Entry(config_frame,textvariable=self.bcomax_var,justify=RIGHT,width=5).grid(row=1,column=5)
        return config_frame

    def wedgeSizeChanged(self,size):
        if size == 'Large':
            self.chipid_var[0].set("1-13")
            self.chipid_var[1].set("1-13")
        else:
            self.chipid_var[0].set("1-5")
            self.chipid_var[1].set("1-5")            
        return

    def run(self,meter,logger,progress_queue):
        ids = [ [], [] ]
        progress = 0
        meter.updateProgress(progress)
        dbco = 1023 # NB: this isn't used in the case of 1 pulse
        initial_val = 0x5 # Two active lines, Global inject enable
        filter = {}
        pulseamp = self.amp_var.get()
        dac0_val = self.dac0_var.get()
        npulses = self.npulses_var.get()
        filter['bco_min'] = self.bcomin_var.get()
        filter['bco_max'] = self.bcomax_var.get()

        sock = start_daq(True,filter)
        if sock == None:
            logger.warning("Failed to open socket to daq program")
            return

        # Grok the user's requested chip ids (treat each side independently)
        ids[0] = select_numbers(self.chipid_var[0].get())
        ids[1] = select_numbers(self.chipid_var[1].get())

        ntasks = npulses * (len(ids[0]) + len(ids[1]))
        step = 100.0 / ntasks
        try:
            logger.info("DAC0: %d, Npulses: %d, Amp: %d" % (dac0_val,npulses,pulseamp))
            for sideid in self.sideids:
                logger.info("***** Side ID %d ******" % (sideid))
                for chipid in ids[sideid]:
                    if use_roc.get(): wedgeaddr = 0xFF
                    else : wedgeaddr = None
                    # Start by disabling all
                    if DEBUG: print "Reset DAQ"
                    reset_fphx(wedgeaddr)
                    if DEBUG: print "Send Init to chip(s)"
                    send_init(21,wedgeaddr)
                    write_fphx_cmd(21,17,FPHX_WRITE,15,wedgeaddr) # set the current to a non-default value
                    write_fphx_cmd(21,4,FPHX_WRITE,dac0_val,wedgeaddr) # set the DAC0 high to avoid unbias noise
                    if use_roc.get(): wedgeaddr = 0xF | (sideid<<4) # Upper 4 bits are side, lower are module
                    # Unmask test channel(s) for the current chip id
                    for chan in self.channels:
                        unmask_chan_fphx(chipid,chan,wedgeaddr)
                    # Enable the chip for readout
                    if wedgeaddr: logger.info("  Enable RO ChipID %2d Wedgeaddr 0x%02X" % (chipid,wedgeaddr))
                    else:         logger.info("  Enable RO ChipID %2d (No wedgeaddr)" % (chipid))
                    write_enable_ro(chipid,initial_val,wedgeaddr)
                    wedgeaddr = 0xFF
                    write_latch(wedgeaddr)
                    # Send pulses
                    write_pulse_amp(pulseamp,wedgeaddr)
                    write_pulse_train(self.npulses_var.get(),dbco,0,wedgeaddr)
                    progress += step
                    meter.updateProgress(progress)
                    # TODO: figure out how to get feedback from the hits
                    # Means we have to terminate the daq process and analyze the
                    # hits
            self.passcode = 1
        except Exception, err:
            traceback.print_exc(file=sys.stdout)
            logger.error("Exception when performing tests:",err)
            
        if DEBUG: print "Reset DAQ"
        reset_fphx(0xFF)
        if DEBUG: print "Close DAQ control socket (Sleep 1 second first)"
        time.sleep(1)
        sock.close()
        return

class CalibrateWedge(threading.Thread):
    def __init__(self,logger,progress_queue):
        threading.Thread.__init__(self)
        self.logger = logger
        self.progress_queue = progress_queue
        self.name = "CalibrateWedge"
        #self.sideids = range(0,2)
        self.chipid_var = [ StringVar(None,"21"),
                            StringVar(None,"21") ]
        self.dac0_var = IntVar(None,8)
        self.lvds_var = IntVar(None,15)
        self.passcode = 0
        pass

    def getName(self):
        return self.name

    def getPasscode(self):
        return self.task.passcode

    def body(self,parent,color):
        frame = Frame(parent,bg=color)
        Label(frame,text="ChipIds 0",bg=color).grid(row=0,column=0)
        Entry(frame,textvariable=self.chipid_var[0],justify=RIGHT,width=5).grid(row=0,column=1)
        Label(frame,text="ChipIds 1",bg=color).grid(row=1,column=0)
        Entry(frame,textvariable=self.chipid_var[1],justify=RIGHT,width=5).grid(row=1,column=1)
        Label(frame,text="DAC0",bg=color).grid(row=0,column=2)
        Entry(frame,textvariable=self.dac0_var,justify=RIGHT,width=5).grid(row=0,column=3)
        Label(frame,text="LVDS",bg=color).grid(row=0,column=4)
        Entry(frame,textvariable=self.lvds_var,justify=RIGHT,width=5).grid(row=0,column=5)
        return frame

    def wedgeSizeChanged(self,size):
        pass

    def create_task(self):
        kwargs= {}
        kwargs['chipids_side0'] = select_numbers(self.chipid_var[0].get())
        kwargs['chipids_side1'] = select_numbers(self.chipid_var[1].get())
        kwargs['dac0_val'] = self.dac0_var.get()
        kwargs['lvds_val'] = self.lvds_var.get()
        self.task = CalibrateWedge.Task(self.logger,self.progress_queue,kwargs=kwargs)
        return self.task

    class Task(threading.Thread):
        def __init__(self,logger,progress_queue,kwargs):
            threading.Thread.__init__(self)
            self.logger = logger
            self.progress_queue = progress_queue
            self.sideids = range(0,2)
            self.chipids = [ kwargs['chipids_side0'], kwargs['chipids_side1'] ]
            self.dac0_val = kwargs['dac0_val']
            self.lvds_val = kwargs['lvds_val']
            self.passcode = 0
            return

        def run(self):
            try:
                checkTesting()
                self.passcode = 0
                self.progress_queue.put(('start',7))
                initial_val = 0x5 # Two active lines + Global inject enable
                wedgeaddr = WEDGESIDE_WILD
                chipid = CHIPID_WILD
                self.logger.info("DAC0: %d   LVDS: %d" % (self.dac0_val,self.lvds_val))
                sock = start_daq(False)
                if sock == None:
                    self.logger.warning("Failed to open DAQ socket")
                    self.progress_queue.put(('failed','Error opening DAQ socket'))
                    return
                self.progress_queue.put(('update','start DAQ program'))
                reset_fphx(wedgeaddr)
                self.progress_queue.put(('update','reset wedge'))
                checkTesting()
                send_init(chipid,wedgeaddr)
                write_fphx_cmd(chipid,17,FPHX_WRITE,self.lvds_val,wedgeaddr) # set the current to user input value
                write_fphx_cmd(chipid,4,FPHX_WRITE,self.dac0_val,wedgeaddr) # set the DAC0 to user input value
                self.progress_queue.put(('update','init wedge'))
                checkTesting()
                for sideid in self.sideids:
                    wedgeaddr = None
                    if use_roc.get(): wedgeaddr = 0xF | (sideid<<4) # Upper 4 bits are side, lower are module
                    for chipid in self.chipids[sideid]:
                        self.logger.info("Enable readout for chip %d side %d" % (chipid,sideid))
                        write_enable_ro(chipid,initial_val,wedgeaddr)
                self.progress_queue.put(('update','enable chips'))
                checkTesting()
                wedgeaddr = WEDGESIDE_WILD
                write_latch(wedgeaddr)
                self.progress_queue.put(('update','latch FPGA'))
                checkTesting()
                calib_fphx(wedgeaddr)
                self.progress_queue.put(('update','start calib'))
                checkTesting()
                time.sleep(40) # No way to know when the calibration is complete, unfortunately
                if sock != None: sock.close()
                checkTesting()
                self.progress_queue.put(('done','success'))
                self.passcode = 1
            except TestingStopped:
                self.progress_queue.put(('done','testing cancelled'))
            except:
                traceback.print_exc(file=sys.stdout)
                self.progress_queue.put(('failed','failed with exception'))
            return

class SourceTest(threading.Thread):
    def __init__(self,logger,progress_queue):
        threading.Thread.__init__(self)
        self.name = "SourceTest"
        self.logger = logger
        self.progress_queue = progress_queue
        self.chipid_var = [ StringVar(None,"21"),
                            StringVar(None,"21") ]
        self.dac0_var = StringVar(None,"11")
        self.lvds_var = StringVar(None,"15")
        self.time_var = StringVar(None,"15")
        pass

    def getName(self):
        return self.name

    def getPasscode(self):
        return self.task.passcode

    def body(self,parent,color):
        frame = Frame(parent,bg=color)
        Label(frame,text="ChipIds 0",bg=color).grid(row=0,column=0)
        Entry(frame,textvariable=self.chipid_var[0],justify=RIGHT,width=5).grid(row=0,column=1)
        Label(frame,text="ChipIds 1",bg=color).grid(row=1,column=0)
        Entry(frame,textvariable=self.chipid_var[1],justify=RIGHT,width=5).grid(row=1,column=1)
        Label(frame,text="DAC0",bg=color).grid(row=0,column=2)
        Entry(frame,textvariable=self.dac0_var,justify=RIGHT,width=5).grid(row=0,column=3)
        Label(frame,text="LVDS",bg=color).grid(row=0,column=4)
        Entry(frame,textvariable=self.lvds_var,justify=RIGHT,width=5).grid(row=0,column=5)
        Label(frame,text="Length(min)",bg=color).grid(row=0,column=6)
        Entry(frame,textvariable=self.time_var,justify=RIGHT,width=5).grid(row=0,column=7)
        return frame

    def wedgeSizeChanged(self,size):
        pass

    def create_task(self):
        kwargs= {}
        kwargs['chipids_side0'] = select_numbers(self.chipid_var[0].get())
        kwargs['chipids_side1'] = select_numbers(self.chipid_var[1].get())
        kwargs['dac0_val'] = self.dac0_var.get()
        kwargs['lvds_val'] = self.lvds_var.get()
        kwargs['time_val'] = self.time_var.get()
        self.task = SourceTest.Task(self.logger,self.progress_queue,kwargs=kwargs)
        return self.task

    class Task(threading.Thread):
        def __init__(self,logger,progress_queue,kwargs):
            threading.Thread.__init__(self)
            self.logger = logger
            self.progress_queue = progress_queue
            self.sideids = range(0,2)
            self.chipids = [ kwargs['chipids_side0'], kwargs['chipids_side1'] ]
            self.dac0_val = kwargs['dac0_val']
            self.lvds_val = kwargs['lvds_val']
            self.time_val = kwargs['time_val']
            self.passcode = 0
            return

        def run(self):
            try:
                checkTesting()
                self.passcode = 0
                self.progress_queue.put(('start',7))
                dac0_val, lvds_val, time_val = int(self.dac0_val), int(self.lvds_val), int(self.time_val)
                sleep_time = time_val * 60
                sock = start_daq(False)
                self.progress_queue.put(('update','start DAQ program'))
                initial_val = 0x5 # Two active lines + Global inject enable
                wedgeaddr = WEDGESIDE_WILD
                chipid = CHIPID_WILD
                self.logger.info("DAC0: %d   LVDS: %d" % (dac0_val,lvds_val))
                self.logger.info("Duration: %d:00" % (int(self.time_val)))
                checkTesting()
                if sock == None:
                    logger.warning("Failed to open DAQ socket")
                    self.progress_queue.put(('failed','Error opening DAQ socket'))
                    return
                checkTesting()
                reset_fphx(wedgeaddr)
                self.progress_queue.put(('update','reset wedge'))
                send_init(chipid,wedgeaddr)
                write_fphx_cmd(chipid,17,FPHX_WRITE,lvds_val,wedgeaddr) # set the current to user input value
                write_fphx_cmd(chipid,4,FPHX_WRITE,dac0_val,wedgeaddr) # set the DAC0 to user input value
                self.progress_queue.put(('update','init wedge'))
                # enable the channels on the chips
                unmask_all_fphx(CHIPID_WILD,wedgeaddr=wedgeaddr)
                self.progress_queue.put(('update','unmask channels'))
                # enable the readout on the selected chip ids
                for sideid in self.sideids:
                    wedgeaddr = None
                    if use_roc.get(): wedgeaddr = 0xF | (sideid<<4) # Upper 4 bits are side, lower are module
                    for chipid in self.chipids[sideid]:
                        logger.info("Enable readout for chip %d side %d" % (chipid,sideid))
                        write_enable_ro(chipid,initial_val,wedgeaddr)
                self.progress_queue.put(('update','enable chips'))
                wedgeaddr = WEDGESIDE_WILD
                checkTesting()
                write_latch(wedgeaddr)
                #self.logger.info("Don't forget to re-enable WRITE LATCH")
                self.progress_queue.put(('update','latch FPGA'))
                # Sleep for the requested amount of time.  TODO: use a timer instead
                time.sleep(sleep_time)
                if sock != None: sock.close()
                self.progress_queue.put(('done','success'))
                self.passcode = 1
            except TestingStopped:
                self.progress_queue.put(('done','testing cancelled'))
            except:
                traceback.print_exc(file=sys.stdout)
                self.progress_queue.put(('failed','failed with exception'))
            return

    
def testHarness(tests,meter,logger,progress_queue):
    #tkSimpleDialog.askinteger("test","test")

    # Check if the user entered a valid module number
    if wedgenum_var.get() == 0:
        tkMessageBox.showwarning("Invalid Wedge Number","Zero is not a valid wedge number")
        return

    # Check if the user has remembered to turn on the output LV
    if pspanel.ps is not None: # TODO: print something?
        if pspanel.get_outputstate() == 0:
            if not tkMessageBox.askokcancel("PS State","Power Supply is off. Continue?"):
                return

    # Check if the user has entered valid info for the bias supply
    newstage = stageVar.get()
    if newstage == 'Sensor' or newstage == 'Encap':
        if biasVoltage_var.get() <= 0.0 or biasCurrent_var.get() <= 0:
            if not tkMessageBox.askokcancel("Bias Data","Bias voltage or current (or both)\nappears invalid. Continue?"):
                return
    
    startB.configure(state=DISABLED)
    cancelB.configure(state=NORMAL)
    
    # create file handler and set level to debug
    starttime = datetime.now()
    fh = logging.FileHandler("%s/qa_wedge%03d_%s_%s.log" % (default_logdir,wedgenum_var.get(),wedgeSize.get(),
                                                         starttime.strftime("%Y%m%d-%H%M")),
                             mode="w")
    fh.setLevel(logging.DEBUG)
    # create formatter
    formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
    # add formatter to file handler
    fh.setFormatter(formatter)
    # add FH to logger
    logger.addHandler(fh)
    
    logger.info("Now logging QA results")
    logger.info("START TEST SUITE")
    logger.info("Wedge %d: Size %s, Rev %d" % (wedgenum_var.get(),wedgeSize.get(),hdiRev.get()))
    logger.info("Test Stage: %s" % (stageVar.get()))
    logger.info("DAQ Type: %s" % daq_types[use_roc.get()])
    # Query the environment
    degc, hum, dewp = envpanel.getValues()
    logger.info("Temperature(C): %.2f" % degc)
    logger.info("Humidity(%%): %.2f" % hum)
    logger.info("Dewpoint(%%): %.2f" % dewp)
    logger.info("Bias V, I: %f, %f" % (biasVoltage_var.get(),biasCurrent_var.get()))
    global tests_running
    tests_running = 1
    testNames = []
    passcodes = []
    global vscan
    global iscan
    vscan = []
    iscan = []
    try:
        for t,e in zip(tests,enable_vars):
            logger.info("Test %s, enabled = %d" % (t.getName(),e.get()))
            if e.get():
                testNames.append(t.getName())
                try:
                    #print "Start test thread"
                    task = t.create_task()
                    task.start()
                    #print "Read progress from test thread"
                    while True: # TODO: potential infinite loop, try to guarantee 'done' will be sent!
                        #logger.info('updating')
                        #if not tests_running:
                        #    print "OH NO! Tests have been cancelled"
                        #    raise TestingStopped
                        master.update_idletasks()
                        master.update() # which is better?
                        try:
                            item = progress_queue.get(True,0.5)
                            #logger.info(item) # temp
                            if item[0] == 'start':
                                totalProgress = item[1]
                                progress = 0
                            if item[0] == 'done' or item[0] == 'update':
                                progress += 100.0/totalProgress
                            meter.updateProgress(progress)
                            if item[0] == 'done': break
                            if item[0] == 'failed':
                                tkMessageBox.showwarning("%s Failure" % t.getName(),item[1])
                                raise TestingStopped
                                break
                        except Queue.Empty:
                            continue
                    logger.info("Join test thread")
                    task.join()
                except AttributeError:
                    print "AttributeError: Test appears to be non-threaded.  Trying run() method"
                    t.run(meter,logger,progress_queue)
                passcodes.append(str(t.getPasscode()))
    finally:
        #print "finally block entered"
        tests_running = 0
        stoptime = datetime.now()
        logger.info("END TEST SUITE")
        delta = stoptime - starttime
        logger.info("Elapsed wall time = %s" % delta)
        tests_str = "{%s}" % ",".join(testNames)
        passcodes_str = "{%s}" % ",".join(passcodes)
        vscan_str = "{%s}" % ",".join(str(x) for x in vscan)
        iscan_str = "{%s}" % ",".join(str(x) for x in iscan)
        #iscan_str = "null"
        qa_data = { 
            'wedge_id'  : wedgenum_var.get(),
            'size'      : wedgeSize.get(),
            'startdate' : "%s" % starttime,
            'enddate'   : "%s" % stoptime,
            'tempc'     : degc,
            'rhperc'    : hum,
            'dewpt'     : dewp,
            'vbias'     : biasVoltage_var.get(),
            'ibias'     : biasCurrent_var.get(),
            'stage'     : stageVar.get(),
            'tests'     : tests_str,
            'passcodes' : passcodes_str,
            'vscan'     : vscan_str,
            'iscan'     : iscan_str
            }
        store_qa_db(logger,qa_data)
        fh.close()
        logger.removeHandler(fh)
        #logging.shutdown()
        startB.configure(state=NORMAL)
        cancelB.configure(state=DISABLED)
    return

def cancelTests():
    print "WARNING: attempt to cancel tests"
    global tests_running
    tests_running = 0
    return

def wedgeSizeChanged(*args):
    for t in tests:
        try:
            t.wedgeSizeChanged(wedgeSize.get())
        except AttributeError:
            pass
        except:
            raise
    return

# Action for when the test stage menu item changes
def stageVarChanged(*args):
    newstage = stageVar.get()
    if newstage == 'Sensor' or newstage == 'Encap':
        #print 'set DAC0 to 10'
        testhash["ValidateChipIds"].dac0_var.set(10)
        testhash["CalibrateWedge"].dac0_var.set(10)
        testhash["SourceTest"].dac0_var.set(10)
    else:
        #print 'set DAC0 to 8'
        testhash["ValidateChipIds"].dac0_var.set(8)
        testhash["CalibrateWedge"].dac0_var.set(8)
    return

def selectSourceTest():
    #print "selectSourceTest",sourceTestEnableVar.get()
    if sourceTestEnableVar.get() == 1:
        #print "-> disable everything else"
        for e in testEnableVars: e.set(0)
    return

def deselectSourceTest(var):
    #print "deselectSourceTest"
    if var.get() == 1 and sourceTestEnableVar.get() == 1:
        #print "-> disable source test"
        sourceTestEnableVar.set(0)
    return

def do_login():
    # Ask user for authentication info
    d = tkGetPasswd.GetPasswd(master,"Login to RCF")
    password_tuple = d.result
    if password_tuple[0] is not None and password_tuple[1] is not None:
        menubar.entryconfig(2,label="Welcome, %s" % password_tuple[0])
        menubar.entryconfig(3,label="Logout",command=do_logout)
    return

def do_logout():
    password_tuple = None
    menubar.entryconfig(2,label="Login required for DB access")
    menubar.entryconfig(3,label="Login",command=do_login)

#
# Main body of the script
#
if __name__ =='__main__':

    # Check for output dir(s)
    try:
        os.stat(default_logdir)
    except:
        print "log dir %s not found, creating" % default_logdir
        os.mkdir(default_logdir)

    # create logger
    logger = logging.getLogger("Wedge_QA")
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    # create formatter
    ch_formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
    # add formatter to file handler
    ch.setFormatter(ch_formatter)
    # add ch to logger
    logger.addHandler(ch)

    progress_queue = Queue.Queue()

    master = Tk()
    master.title('Wedge QA')
    master.withdraw() # Prevent the window from being drawn while dialog is up

    # Ask user for authentication info
    #d = tkGetPasswd.GetPasswd(master,"Login to RCF")
    #password_tuple = d.result

    # create the menubar
    menubar = Menu(master)
    filemenu = Menu(menubar, tearoff=0)
    filemenu.add_separator()
    # master.destroy is better than master.quit (at least in IDLE)
    filemenu.add_command(label="Quit", command=master.destroy,accelerator='Ctrl-Q')
    # Type Ctrl-q to exit application
    master.bind('<Control-q>','exit')
    menubar.add_cascade(label="File", menu=filemenu)
    # if password_tuple:
    #     menubar.add_command(label="Welcome, %s" % password_tuple[0], state=DISABLED)
    #     menubar.add_command(label="Logout", command=do_logout)
    # else:
    #     menubar.add_command(label="Login Required for DB access", state=DISABLED)
    #     menubar.add_command(label="Login", command=do_login)

    #menubar.entryconfig(3,label="Login NEW")
    master.config(menu=menubar)

    # Create the Power supply frame
    irow = 0
    psframe = LabelFrame(master,text='Power Supply')
    psframe.grid(row=irow,sticky=W+E)
    pspanel = ps_panel.ps_panel(psframe)
    pspanel.grid(row=0)
    irow += 1

    # Get a list of DLP devices connected to the host
    devList = []
    devs = listDevices()
    if devs:
        for i, e in enumerate(devs):
            details = ftd2xx.getDeviceInfoDetail(i)
            test = re.match('^DLP2232M.*',details['description'])
            if test:
                devList.append(details['serial'])
    devList.append("None")

    # Build the slow control interface frame
    if devList == None or len(devList) == 0:
        devList = [ "None" ]
    devChoice = StringVar(None,devList[0])
    sc_frame = LabelFrame(master,text="Slow Control Interface")
    sc_frame.grid(row=irow,sticky=W+E)
    Label(sc_frame,text="Device").grid(row=0,column=0,sticky=W)
    devChoice_menu = OptionMenu(sc_frame,devChoice,*devList)
    devChoice_menu.grid(row=0, column=1)
    irow += 1

    # Build the temp/humidity frame. For now, it's a dummy since we
    # don't have a device to read.
    env_frame = LabelFrame(master,text="Environment")
    env_frame.grid(row=irow,sticky=W+E)
    envpanel = env_panel.env_panel(env_frame,False)
    envpanel.grid(row=0)
    irow += 1    

    tests = [ ScanLVDSReadbackCurrent(logger,progress_queue,pspanel),
              ReadBackDefaultValues(logger,progress_queue),
              ValidateChipIds("ValidateChipIds"),
              CalibrateWedge(logger,progress_queue),
              SourceTest(logger,progress_queue)
            ]

    # Slight hack to ease lookup of specific tests
    testhash = { "ReadBackDefaultValues" : tests[1],
                 "ValidateChipIds" : tests[2],
                 "CalibrateWedge" : tests[3],
                 "SourceTest" : tests[4]
                }

    icol = 0
    daqframe = LabelFrame(master,text='DAQ Configuration')
    daqframe.grid(row=irow,sticky=W+E)
    use_roc = IntVar(None,1)
    tbselect_frame = Frame(daqframe)
    tbselect_frame.grid(row=0,column=icol,stick=W)
    daq_types = [ 'Spartan3', 'ROC', 'ROC+FEM' ]
    for i, t in enumerate(daq_types):
        Radiobutton(tbselect_frame,variable=use_roc,value=i,text=t).grid(row=0,column=i)
    
    chipver_frame = Frame(daqframe)
    chipver_frame.grid(row=0,column=1)
    Label(chipver_frame,text="FPHX",justify=LEFT).grid(row=0,column=0,sticky=W)
    chipVersionList = [ 1, 2 ]
    chipVersions = IntVar(None,chipVersionList[1])
    chipversion_menu = OptionMenu(chipver_frame,chipVersions,*chipVersionList)
    chipversion_menu.grid(row=0, column=1,sticky=W)

    sample_MHz_var = StringVar(None,'5')
    sample_frame = Frame(daqframe)
    sample_frame.grid(row=0,column=2)
    Label(sample_frame,text="Sample Rate (MHz)").grid(row=0,column=0,sticky=W)
    Entry(sample_frame,textvariable=sample_MHz_var,width=5,justify=RIGHT).grid(row=0,column=1,sticky=W)

    irow += 1

    wedgenum_var = IntVar(None,0)
    wedge_frame = LabelFrame(master,text='Wedge Configuration')
    wedge_frame.grid(row=irow,sticky=W+E)
    Label(wedge_frame,text="Serial Num",justify=LEFT).grid(row=0,column=0,sticky=W)
    Entry(wedge_frame,textvariable=wedgenum_var,width=5,justify=RIGHT).grid(row=0,column=1,sticky=W)
    Label(wedge_frame,text="Size",justify=LEFT).grid(row=0,column=2,sticky=W)
    wedgeSizeList = [ 'Large', 'Small' ]
    wedgeSize = StringVar(None,wedgeSizeList[1])
    wedgeSize.trace("w",wedgeSizeChanged)
    wedgeSize_menu = OptionMenu(wedge_frame,wedgeSize,*wedgeSizeList)
    wedgeSize_menu.grid(row=0,column=3,sticky=W)
    Label(wedge_frame,text="HDI Rev",justify=LEFT).grid(row=0,column=4,sticky=W)
    hdiRevList = [ 1, 2, 3 ]
    hdiRev = IntVar(None,hdiRevList[1])
    hdiRev_menu = OptionMenu(wedge_frame,hdiRev,*hdiRevList)
    hdiRev_menu.grid(row=0,column=5,sticky=W)
    Label(wedge_frame,text="Bias V(V)",justify=RIGHT).grid(row=0,column=6,sticky=W)
    biasVoltage_var = DoubleVar(None,0.0)
    Entry(wedge_frame,textvariable=biasVoltage_var,width=5,justify=RIGHT).grid(row=0,column=7,sticky=W)
    Label(wedge_frame,text="Bias I(uA)",justify=RIGHT).grid(row=0,column=8,sticky=W)
    biasCurrent_var = DoubleVar(None,0.0)
    Entry(wedge_frame,textvariable=biasCurrent_var,width=5,justify=RIGHT).grid(row=0,column=9,sticky=W)
    Label(wedge_frame,text="Assy Stage",justify=RIGHT).grid(row=1,column=2,sticky=W)
    stageList = [ 'Chips', 'Sensor', 'Encap' ]
    if wedgeSize.get() == 'Small': 
        stageVar = StringVar(None,stageList[2])
    else:
        stageVar = StringVar(None,stageList[0])
    stageVar.trace("w",stageVarChanged)
    stage_menu = OptionMenu(wedge_frame,stageVar,*stageList)
    stage_menu.grid(row=1,column=3,sticky=W)
    irow += 1
 
    opframe = LabelFrame(master,text='Operations')
    opframe.grid(row=irow,sticky=W+E)
    startB = Button(opframe,text="Start",width=10)
    startB.grid(padx=5,sticky=W)
    cancelB = Button(opframe,text="Cancel",state=DISABLED,width=10)
    cancelB.grid(row=0,column=1,padx=1,sticky=W)
    meter = ProgressBar.ProgressBar(opframe,width=300,height=20)
    meter.grid(row=0,column=2,sticky=W+E)#,padx=30)
    meter.updateProgress(0.1) # exact 0 suppresses the label in the bar. epsilon results in "0%"
    startB.configure(command=lambda *args: testHarness(tests,meter,logger,progress_queue))
    cancelB.configure(command=lambda *args: cancelTests())
    
    irow += 1

    enable_vars = []
    testEnableVars = []
    test_frame = Frame(master)
    test_frame.grid(row=irow,sticky=N+S+W+E)
    Label(test_frame,text="Enabled").grid(row=0,column=0)
    Label(test_frame,text="Name").grid(row=0,column=1)
    Label(test_frame,text="Configuration").grid(row=0,column=2)
    trow = 1
    colors = [ "light gray", "gray" ]
    icolor = 0
    for test in tests:
        color = colors[trow % 2]
        enable_vars.append(IntVar(None,1))
        if test.getName() == "SourceTest":
            enable_vars[-1].set(0)
            #enable_vars[-1].trace("w",toggleSourceTest)
            sourceTestEnableVar = enable_vars[-1]
        else:
            #enable_vars[-1].trace("w",toggleTest)
            testEnableVars.append(enable_vars[-1])
        c = Checkbutton(test_frame,variable=enable_vars[-1],bg=color)
        c.grid(row=trow,column=0,sticky=N+S+W+E)
        if test.getName() == "SourceTest": c.config(command=selectSourceTest)
        else: c.config(command=lambda v=enable_vars[-1]: deselectSourceTest(v))
        Label(test_frame,text=test.getName(),bg=color).grid(row=trow,column=1,sticky=N+S+W+E)
        frame = test.body(test_frame,color)
        #frame.configure(bg=colors[trow % 2])
        frame.grid(row=trow,column=2,sticky=N+S+W+E)
        trow += 1
        
    # Display the window
    master.deiconify()

    master.mainloop()
    
