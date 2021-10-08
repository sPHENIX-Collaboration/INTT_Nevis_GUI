
import platform
print 'Version       :', platform.python_version()
print 'Compiler      :', platform.python_compiler()
print 'Build         :', platform.python_build()

import struct
from ctypes import * #create_string_buffer
try:
    import ftd2xx # For the API to the DLP2232 USB controller (Future Technologies)
    print 'ftd2xx Version:',ftd2xx.getLibraryVersion() 
except ImportError:
    print "Failed to import ftd2xx"
except:
    pass

# Flag to determine whether we want to use db access or not.
# This is intended to avoid long timeouts if there is a problem
# detected in the db access (in which case we should set to 0).
dbaccess = 1

import sys
try:
    if sys.platform == 'win32':
        #import dbi
        import odbc
        #import phenix
    else:
        import pyodbc
except ImportError, inst:
    print "Failed to import ODBC and related modules: ", inst
    dbaccess = 0
except:
    pass

import re
import time
import ftplib
import traceback

# Raise the value to get more debug chatter from module
FPHXTB_VERBOSE = 0

# ODBC Data Source Name
DSN = "phenixdb_fvtx"
runnumber_table = "runnumber_generator"
runnumber_field = "next_runnumber"

# Beginning-of-packet and End-of-packet markers
BOPMARKER = 0xFF
EOPMARKER = 0xFF

# some symbols for the available FPHX ops
# READ is not really a defined command, it's an unused instruction.  We use this
# cause the register to send back its value w/o changing anything in the register
FPHX_READ    = 0x0
FPHX_WRITE   = 0x1 
FPHX_SET     = 0x2
FPHX_RESET   = 0x5
FPHX_DEFAULT = 0x6

# some symbols for the available teststand ops
# PLEASE DO NOT CHANGE THESE.  ADD TO THEM, DO NOT CHANGE.
TESTBENCH_EPROM_WRITE = 0x01 # Write to the EPROM
TESTBENCH_EPROM_READ  = 0x02 # Read from the EPROM
TESTBENCH_FPHX        = 0x03 # FPHX op (Send packet payload to FPHX)
#TESTBENCH_RESET_FEMONLY = 0x44
#TESTBENCH_RESET_ROCFEM = 0xC4
#TESTBENCH_RESET       = 0xC4 # Reset for both FEM and ROC = 0x`C4.  For just ROC = 0x04.  For just FEM = 0x44
TESTBENCH_RESET       = 0x0b # FFR (firefighter reset) for FPHX chip
TESTBENCH_CALIB       = 0x05 # Start calibration sequence
TESTBENCH_PULSEAMP    = 0x06 # Set the pulser amplitude
TESTBENCH_PULSE       = 0x07 # Generate a pulse
TESTBENCH_PULSER      = 0x08 # Configure the pulse train
TESTBENCH_LATCHFPGA   = 0x09 # Send the latch command to the FPGA(s)
TESTBENCH_PULSE_MODULE = 0x0a # Send the module that should be pulsed (bits 0-2 - side, bits 4-7 = wedge location)
TESTBENCH_EEPROM_READ_WRITE          = 0x50 # Read or Write from the EEPROM on the FEM
TESTBENCH_EEPROM_BATCH_DOWNLOAD = 0x47 # Batch download of EEPROM from FEM to ROC
TESTBENCH_FOSYNC      = 0X41 # Send the FEM fiber opticy synch command (upper 4 bit means FEM command)
TESTBENCH_FEMLVL1DELAY      = 0X45 # Send the FEM fiber opticy synch command (upper 4 bit means FEM command)
TESTBENCH_BCOSTART    = 0x62 # Send BCO start command to the FEM_IB and the FEM
TESTBENCH_FPGARESET   = 0xC4 # Reset for both FEM and ROC = 0x`C4.  For just ROC = 0x04.  For just FEM = 0x44


def hexify_bytes(bytestr):
    val = ""
    for byte in bytestr[0:len(bytestr)]:
        val += "%02x " % struct.unpack("B",byte)
    return val

def listDevices():
    return ftd2xx.listDevices()

# Open a device and return the handle to it
def opendev(devid):
    port = ftd2xx.openEx(devid)
    return port

def closedev(port):
    port.close()
    return

### Write a data packet to the usb port.  The packet data is in raw bytes.  It returns
### the 1-byte response from the device, but in raw form also.  This version requires the
### caller to specify the target device.
##def write_bytes_to_usb(target,rawbuf):
##    try:
##        # TODO: some sanity checks to make sure it's an FT device?
##        port = ftd2xx.openEx(target)
##    except:
##        print 'write_bytes_to_usb(target,rawbuf): Caught exception opening USB port %s, check that ftd2xx module loaded properly' % target
##        return
##    
##    port.setBitMode(255,4) # set port direction FF = all output, 00 = input, bit bang mode
##    port.purge(3) # 1 == FT_PURGE_RX, 2 == FT_PURGE_TX, 3 == both TX and RX (OR of 1 and 2)
##    nwritten = port.write(rawbuf)
##    if FPHXTB_VERBOSE>0: print 'write_bytes_to_usb: wrote',nwritten,'bytes'
##    if port.getQueueStatus() < 1 :
##        timeout = 10000
##        if FPHXTB_VERBOSE>0: print 'getQueueStatus reports no RX data, set read timeout to',timeout,'msec'
##        port.setTimeouts(timeout,0)
##    if FPHXTB_VERBOSE>0: print 'write_bytes_to_usb: try to read 1 byte'
##    buf = port.read(1)
##    if ( len(buf) < 1 ) : print 'write_bytes_to_usb: WARNING: No data read back from USB port'
##    if FPHXTB_VERBOSE>0: print 'write_bytes_to_usb: Length of readback from USB = ',len(buf)
##    val = int( struct.unpack('B', buf)[0] )
##    if FPHXTB_VERBOSE>0: print 'write_bytes_to_usb: read back response: ', dec_num
##    return val

# Write a data packet to the usb port.  The packet data is in raw bytes.  It returns
# the 1-byte response from the device, but in raw form also.
def write_bytes_to_usb(rawbuf,target=None,baud=None) :
    #print 'write_bytes_to_usb'
    #usbdev = None
    if target is None:
        # Use openEx to get a list of USB devices.  This is because
        # open() just takes the first one, which may not be the one we want!
        devices = ftd2xx.listDevices()
        if devices is None:
            print "No FTD2xx devices found"
            return None
        test = re.compile("^FT.*A$", re.IGNORECASE) # Look only for the "A" channel
        result = filter(test.search,devices)
        if not result: raise Exception, "No valid USB devices found"
        #print ftd2xx.listDevices()
        target = result[0]
        if not target: raise Exception, "listDevices succeeded, but gave no valid USB devices"
    try:
        if FPHXTB_VERBOSE>0: print 'write_bytes_to_usb: open using openEx on device',usbdev
        port = ftd2xx.openEx(target)
    except NameError:
        print 'Caught NameError exception opening USB port %s, check that ftd2xx module loaded properly' % usbdev
        return
    except Exception, e:
        print "Caught (unhandled) exception opening USB port %s: %s" % (target,e)
        print "Check that USB cable is connected properly"
        return
    
    # Here we do 2 write-read operations to be able to get back the expected response from the chip.
    # This is because of the unfortunate feature of the DLP-2232's Sync BitBang mode that it sends you the current data
    # on the pins before reading them again.
    #print 'latency timer =',port.getLatencyTimer()
    #port.setLatencyTimer(2)
    if baud is not None:
        print 'Setting baud rate to',baud
        port.setBaudRate(baud)
    for i in range(1) :
        port.setBitMode(255,4) # set port direction FF = all output, 00 = input, bit bang mode
        port.purge(3) # 1 == FT_PURGE_RX, 2 == FT_PURGE_TX, 3 == both TX and RX (OR of 1 and 2)
        nwritten = port.write(rawbuf)
        time.sleep(0.1)
        if FPHXTB_VERBOSE>0: print 'write_bytes_to_usb: wrote',nwritten,'bytes'
        if port.getQueueStatus() < 1 :
            timeout = 10000
            #if FPHXTB_VERBOSE>0: print 'getQueueStatus reports no RX data, set read timeout to',timeout,'msec'
            print 'getQueueStatus reports no RX data, set read timeout to',timeout,'msec'
            port.setTimeouts(timeout,0)
        if FPHXTB_VERBOSE>0: print 'write_bytes_to_usb: try to read 1 byte'
        buf = port.read(1)
        if ( len(buf) < 1 ) : print 'write_bytes_to_usb: WARNING: No data read back from USB port'
        if FPHXTB_VERBOSE>0: print 'write_bytes_to_usb: Length of readback from USB = ',len(buf)
    dec_num = int( struct.unpack('B', buf)[0] )
    if FPHXTB_VERBOSE>0: print 'write_bytes_to_usb: read back response: ', dec_num
    #print 'write_bytes_to_usb: read back response: ', dec_num
    port.close()
    #return buf
    return dec_num

# Write a raw buffer to an ftp socket.  Target is an IP address or IP Address
# followed by a port, separated by a colon.
def write_bytes_to_ftp(rawbuf,target):
    val = None
    a = target.split(":")
    if len(a) == 1:
        ip = a[0]
        port = 21
    elif len(a) == 2:
        ip = a[0]
        port = int(a[1])
    else:
        raise Exception, "Malformed IP spec: %s" % target

    try:
        session = ftplib.FTP()
        session.connect(ip,port)
        session.login('anonymous')
        open('WriteFile.txt',"wb").write(str(rawbuf))
        session.storbinary('STOR WriteFile.txt',open('WriteFile.txt',"rb"))
        session.retrbinary('RETR ReadFile.txt',open('ReadFile.txt','wb').write)
        b = open("ReadFile.txt","rb").read()
        val = 1
#        val = int( struct.unpack('B', b)[0] )
    except Exception, e:
        traceback.print_exc(file=sys.stdout)
        print "Failure opening or during FTP session: %s" % e
    return val

def write_bytes_to_target(rawbuf,target=None,baud=None):
    print "target = %s" % target
    if target is None:
        #print "write_bytes_to_target: target is None, defaulting to USB"
        return write_bytes_to_usb(rawbuf,target,baud)
    if re.match("^FT.*A$", target):
        #print "write_bytes_to_target: target is USB"
        return write_bytes_to_usb(rawbuf,target,baud)
    else:
        #print "write_bytes_to_target: target is FTP"
        return write_bytes_to_ftp(rawbuf,target)

# Format a single 32-bit word as a FPHX command.  User supplies chipid, reg address (starts from 1)
# the command and the data.  Returns the word with the proper header/trailer and formatting.
def make_fphx_cmd(chipId, regId, cmd, data) :
    header = 0x67 # FPHX design requires first 5 bits to be 1100111
    trailer = 0x0 # FPHX design requires last 4 bits to be 0000
    word = int(0)
    word = header << (32-7)
    word |= (0x1F & chipId)<<(32-12) # 5 bits of chip id
    word |= (0x1F & regId) <<(32-17) # 5 bits of register id
    word |= (0x7 & cmd) <<(32-20) # 3 bits of instruction
    word |= (0xFF & data) <<(32-28) # 8 bits of data
    word |= (0xF & trailer) # trailer bits
    return word

# Create a packet based on a single FPHX command word.  This wraps all the
# slow control info around the word.  Optional wedgeaddr can be supplied.
def create_packet_fphx(word,wedgeaddr=None,femaddr=None):
    buflen = 5+4+1
    length = 4+1
    if wedgeaddr is not None:
        length += 1
        buflen += 1
    if femaddr is not None:
        length += 1
        buflen += 1
    #print "buflen, length = %d, %d" % (buflen,length)
    buf = create_string_buffer(buflen)
    offset = 0
    struct.pack_into("B",  buf,offset,BOPMARKER)   # start-of-packet
    offset += 1
    struct.pack_into(">H", buf,offset,length) # 2 bytes representing length of payload, packed big-endian
    offset += 2
    struct.pack_into("B",  buf,offset,TESTBENCH_FPHX) # command byte
    offset += 1
    if wedgeaddr is not None:
        struct.pack_into("B",buf,offset,wedgeaddr) # Pack the optional byte of wedge address
        offset += 1
    if femaddr is not None:
        struct.pack_into("B",buf,offset,femaddr) # Pack the optional byte of FEM address
        offset += 1
    struct.pack_into(">I", buf,offset,word)   # data payload
    offset += 4
    
    checksum = bool(False)

    tempbuf = create_string_buffer(4)
    struct.pack_into(">I", tempbuf,0,word)

    for i in range(4):
        checksum = checksum ^ struct.unpack_from(">B",tempbuf,i)[0]

    print 'XOR checksum = %s' % hex(checksum)

    struct.pack_into(">B",buf,offset,checksum)
    offset += 1    
    struct.pack_into("B",  buf,offset,EOPMARKER)   # end-of-packet
    return buf

def create_packet(dest,data,wedgeaddr=None,femaddr=None):
    length = len(data) + 1 # length of data + 1 byte for dest
    buflen = 4 + 1 # Packet markers + length word +1 for checksum
    if wedgeaddr: length += 1 # one more byte for optional wedgeaddr
    if femaddr: length += 1   # one more byte for optional femaddr
    buflen += length # add number of bytes in data (data must be a string)
    print "buflen, length = %d, %d" % (buflen,length)
    buf = create_string_buffer(buflen)
    offset = 0
    struct.pack_into("B",buf,offset,BOPMARKER) # beginning of packet
    offset += 1
    struct.pack_into(">H",buf,offset,length) # 2 bytes representing length, packed big-endian
    offset += 2
    struct.pack_into("B", buf,offset,dest) # destination byte
    offset += 1
    if wedgeaddr is not None:
        struct.pack_into("B",buf,offset,wedgeaddr) # Pack the optional byte of wedge address
        offset += 1
    if femaddr is not None:
        struct.pack_into("B",buf,offset,femaddr) # Pack the optional byte of wedge address
        offset += 1
    struct.pack_into("%ds"%len(data),buf,offset,data)   # data payload
    offset += len(data)

    checksum = bool(False)

    for i in range(len(data)):
        checksum = checksum ^ struct.unpack_from(">B",data,i)[0]

    print 'XOR checksum = %s' % hex(checksum)

    struct.pack_into(">B",buf,offset,checksum)
    offset += 1
    
    struct.pack_into("B",buf,offset,EOPMARKER)   # end-of-packet
    return buf

def write_fphx_cmd(chipid,regid,cmd,data,wedgeaddr=None,femaddr=None,target=None,baud=None):
    word = make_fphx_cmd(chipid,regid,cmd,data)
    buf = create_packet_fphx(word,wedgeaddr)
    return write_bytes_to_target(buf.raw,target,baud)

# Send a command to enable chip with chipid.  Requires user to
# supply an initial value (this allows the other bits in the register
# to be preserved, for instance).
def write_enable_ro(chipid,initialval,wedgeaddr=None,femaddr=None,target=None,baud=None):
    chipid = 0x1F & int(chipid)
    regid = 2
    val = initialval
    val |= 1<<1 # Set the enable bit, leave the rest unchanged
    cmd = FPHX_WRITE
    word = make_fphx_cmd(chipid,regid,cmd,val)
    buf = create_packet_fphx(word,wedgeaddr,femaddr)
    if FPHXTB_VERBOSE>0: print 'write_enable_ro: FPHX command = 0x%x' % word
    if FPHXTB_VERBOSE>0: print 'write_enable_ro: Send FPHX packet = %s' % hexify_bytes(buf)
    write_bytes_to_target(buf.raw,target,baud)
    return

# Send a command to disable chip with chipid.  Requires user to
# supply an initial value (this allows the other bits in the register
# to be preserved, for instance).
def write_disable_ro(chipid,initialval,wedgeaddr=None,femaddr=None,target=None,baud=None):
    chipid = 0x1F & int(chipid)
    regid = 2
    val = initialval
    val &= ~(1<<1) # Zero the enable bit, leave the rest unchanged
    cmd = FPHX_WRITE
    word = make_fphx_cmd(chipid,regid,cmd,val)
    buf = create_packet_fphx(word,wedgeaddr,femaddr)
    if FPHXTB_VERBOSE>0: print 'write_enable_ro: FPHX command = 0x%x' % word
    if FPHXTB_VERBOSE>0: print 'write_enable_ro: Send FPHX packet = %s' % hexify_bytes(buf)
    write_bytes_to_target(buf.raw,target,baud)
    return

def write_pulse_amp(amp,wedgeaddr=None,femaddr=None,target=None,baud=None):
    cmd = TESTBENCH_PULSEAMP
    #data = 0xFF & amp
    #databuf = create_string_buffer(1)
    #struct.pack_into("B",databuf,0,data)
    # For future 16-bit version...
    # The Future is NOW
    if amp > 1023:
        print "ERROR: Amplitude must be < 1024"
        return
    data = 0xFFFF & amp
    databuf = create_string_buffer(2)
    struct.pack_into(">H",databuf,0,data)
    buf = create_packet(cmd,databuf.raw,wedgeaddr,femaddr)
    #if FPHXTB_VERBOSE>0: print 'write_pulse_amp: Send pulse amp packet = %s' % hexify_bytes(buf)
    print 'write_pulse_amp: Send pulse amp packet = %s' % hexify_bytes(buf)
    write_bytes_to_target(buf.raw,target,baud)
    return

def write_pulse_module(module,wedgeaddr=None,femaddr=None,target=None):
    cmd = TESTBENCH_PULSE_MODULE
    data = module
    databuf = create_string_buffer(1)
    struct.pack_into("B",databuf,0,data)
    # For future 16-bit version...
    #data = 0xFFFF & amp
    #databuf = create_string_buffer(2)
    #struct.pack_into("B",databuf,0,data)
    buf = create_packet(cmd,databuf.raw,wedgeaddr,femaddr)
    #if FPHXTB_VERBOSE>0: print 'write_pulse_module: Send pulse module packet = %s' % hexify_bytes(buf)
    print 'write_pulse_module: Send pulse module packet = %s' % hexify_bytes(buf)
    write_bytes_to_target(buf.raw,target)
    return

def write_pulse_config(num, deltabco, wedgeaddr=None, femaddr=None, target=None,baud=None):
    cmd = TESTBENCH_PULSER
    databuf = create_string_buffer(8)
    struct.pack_into(">I",databuf,0,deltabco)
    struct.pack_into(">I",databuf,4,num)
    buf = create_packet(cmd,databuf.raw,wedgeaddr,femaddr)
    if FPHXTB_VERBOSE>0: print 'write_pulse_config: Send pulse config packet = %s' % hexify_bytes(buf)
    write_bytes_to_target(buf.raw,target,baud)
    return
        
def write_pulse(wedgeaddr=None,femaddr=None,target=None,baud=None):
    cmd = TESTBENCH_PULSE
    data = 0x01 # not sure what the value means, just replicating contents of "pulse.dat"
    databuf = create_string_buffer(1)
    struct.pack_into("B",databuf,0,data)
    buf = create_packet(cmd,databuf.raw,wedgeaddr,femaddr)
    if FPHXTB_VERBOSE>0: print 'write_pulse2: Send pulse packet = %s' % hexify_bytes(buf)
    write_bytes_to_target(buf.raw,target,baud)

        
def write_pulse_train(num, deltabco, amp, wedgeaddr=None, femaddr=None, target=None,baud=None):
    if FPHXTB_VERBOSE>0: print "Write %d pulses with amp %d and spacing %d" % (num,amp,deltabco)
    # first set the pulse amplitude
    #write_pulse_amp(amp,wedgeaddr)
    # Add a small delay to prevent FPGA lockup
    #time.sleep(0.5)
    # now set the spacing and number
    write_pulse_config(num,deltabco,wedgeaddr,femaddr,target,baud)
    return

def write_latch(wedgeaddr=None,femaddr=None,target=None,baud=None):
    cmd = TESTBENCH_LATCHFPGA
    data = 0xFF # data? I just replicate what's in the file 'reset.dat'
    databuf = create_string_buffer(1)
    struct.pack_into("B",databuf,0,data)
    buf = create_packet(cmd,databuf.raw,wedgeaddr,femaddr)
    #if FPHXTB_VERBOSE>0: print 'write_latch: Send FPHX packet = %s' % hexify_bytes(buf)
    print 'write_latch: Send FPHX packet = %s' % hexify_bytes(buf)
    write_bytes_to_target(buf.raw,target,baud)
    return

def write_fo_sync(wedgeaddr=None,femaddr=None,target=None,baud=None):
    cmd = TESTBENCH_FOSYNC
    data = 0x0F # Just need a signal that is high for at least one clock
    databuf = create_string_buffer(1)
    struct.pack_into("B",databuf,0,data)
    buf = create_packet(cmd,databuf.raw,wedgeaddr,femaddr)
    if FPHXTB_VERBOSE>0: print 'write_fo_sync: Send FEM packet = %s' % hexify_bytes(buf)
    write_bytes_to_target(buf.raw,target,baud)
    return

def write_fpga_reset(wedgeaddr=None,femaddr=None,target=None):
    cmd = TESTBENCH_FPGARESET
    data = 0x0f # Just need a signal that is high for at least one clock
    databuf = create_string_buffer(1)
    struct.pack_into("B",databuf,0,data)
    buf = create_packet(cmd,databuf.raw,wedgeaddr,femaddr)
    if FPHXTB_VERBOSE>0: print 'write_fpga_reset: Send FEM packet = %s' % hexify_bytes(buf)
    write_bytes_to_target(buf.raw,target)
    return

def write_fem_lvl1_delay(delay,wedgeaddr=None,femaddr=None,target=None,baud=None):
    cmd = TESTBENCH_FEMLVL1DELAY
    data = delay # Just need a signal that is high for at least one clock
    databuf = create_string_buffer(1)
    struct.pack_into("B",databuf,0,data)
    buf = create_packet(cmd,databuf.raw,wedgeaddr,femaddr)
    if FPHXTB_VERBOSE>0: print 'write_fem_lvl1_delay: Send FEM packet = %s' % hexify_bytes(buf)
    write_bytes_to_target(buf.raw,target,baud)
    return

def write_bco_start(wedgeaddr=None,femaddr=None,target=None,baud=None):
    cmd = TESTBENCH_BCOSTART
    data = 0x01 # Just need a signal that is high for at least one clock
    databuf = create_string_buffer(1)
    struct.pack_into("B",databuf,0,data)
    buf = create_packet(cmd,databuf.raw,wedgeaddr,femaddr)
    if FPHXTB_VERBOSE>0: print 'write_bco_start: Send FEM packet = %s' % hexify_bytes(buf)
    write_bytes_to_target(buf.raw,target,baud)
    return


# Unmask a single channel for a given chipid
def unmask_chan_fphx(chipid,chan,wedgeaddr=None,femaddr=None,target=None,baud=None):
    reg = 1
    cmd = FPHX_RESET
    data = 0xFF & chan
    word = make_fphx_cmd(chipid,reg,cmd,data)
    if FPHXTB_VERBOSE>0: print 'FPHX command = 0x%x' % (word)
    buf = create_packet_fphx(word,wedgeaddr)
    if FPHXTB_VERBOSE>0: print 'unmask_chan_fphx: Send FPHX packet = %s' % hexify_bytes(buf)
    write_bytes_to_target(buf.raw,target,baud)

# Unmask ALL channels for a given chip id
def unmask_all_fphx(chipid,target=None,wedgeaddr=None,femaddr=None,baud=None):
    # Just call the channel unmask with global bit
    unmask_chan_fphx(chipid,128,wedgeaddr,femaddr,target,baud)

# Mask a single channel for a given chip id
def mask_chan_fphx(chipid,chan,wedgeaddr=None,femaddr=None,target=None,baud=None):
    reg = 1
    cmd = FPHX_SET
    data = 0xFF & chan
    word = make_fphx_cmd(chipid,reg,cmd,data)
    if FPHXTB_VERBOSE>0: print 'FPHX command = 0x%x' % word
    buf = create_packet_fphx(word,wedgeaddr)
    if FPHXTB_VERBOSE>0: print 'mask_chan_fphx: Send FPHX packet = %s' % hexify_bytes(buf)
    write_bytes_to_target(buf.raw,target,baud)

# Mask ALL channels for a given chip id
def mask_all_fphx(chipid,wedgeaddr=None,femaddr=None,target=None,baud=None):
    mask_chan_fphx(chipid,128,wedgeaddr,femaddr,target,baud)

# Create and send a packet for the reset of the TB.  The argument wedgeaddr
# is the address of the target half-wedge.  The lower 4 bits are the module number
# and the upper 4 bits are the side address.  A value of 0xF for either is a wild
# value.  The argument is optional so that we can use this code with the Spartan3
# board (at least until the spartan board can understand -- and ignore -- the wedge
# information).
# The behavior of the reset is based on the cmd argument.  By default it will reset the ROC.
# if you need it to do anything other than that, call this function with a different value.
def reset_fphx(wedgeaddr=None,femaddr=None,target=None,baud=None,cmd=TESTBENCH_RESET):
    #cmd = TESTBENCH_RESET
    data = 0xFF # data? I just replicate what's in the file 'reset.dat'
    databuf = create_string_buffer(1)
    struct.pack_into("B",databuf,0,data)
    buf = create_packet(cmd,databuf.raw,wedgeaddr,femaddr)
    if FPHXTB_VERBOSE>0: print 'reset_fphx: Send FPHX packet = %s' % hexify_bytes(buf)
    write_bytes_to_target(buf.raw,target,baud)
    return

# Send a programmable reset, depending on the cmd used
def prog_reset_fphx(chipid,cmd,wedgeaddr=None,femaddr=None,target=None,baud=None):
    regid = 18
    data = 0
    word = make_fphx_cmd(chipid,regid,cmd,data)
    if FPHXTB_VERBOSE>0: print 'FPHX command = 0x%x' % word
    buf = create_packet_fphx(word,wedgeaddr,femaddr)
    if FPHXTB_VERBOSE>0: print 'prog_reset_fphx: Send FPHX packet = %s' % hexify_bytes(buf)
    write_bytes_to_target(buf.raw,target,baud)

def clear_hits_fphx(chipid,wedgeaddr=None,femaddr=None,target=None,baud=None):
    prog_reset_fphx(chipid,FPHX_SET,wedgeaddr,femaddr,target,baud)
    return

def clear_bco_fphx(chipid,wedgeaddr=None,femaddr=None,target=None,baud=None):
    prog_reset_fphx(chipid,FPHX_RESET,wedgeaddr,femaddr,target,baud)
    return

# Create and send the calib packet.  Optionally prepend a BCO reset
# the packet payload
def calib_fphx(wedgeaddr=None,femaddr=None,target=None,baud=None):
    cmd = TESTBENCH_CALIB
    data = 0x01 # data? I just replicate what's in the file 'calib.dat'
    databuf = create_string_buffer(1)
    struct.pack_into("B",databuf,0,data)
    if wedgeaddr is not None: wedgeaddr = 0xFF # override user: Write to all wedgeaddr for now.
    buf = create_packet(cmd,databuf.raw,wedgeaddr,femaddr)
    if FPHXTB_VERBOSE>0: print 'calib_fphx: Send calib packet = %s' % hexify_bytes(buf)
    write_bytes_to_target(buf.raw,target,baud)
    return

# Database access routines.

# Fetch the next unique runnumber from the generating database.  This operation is designed
# to be atomic.  As long as only this routine (or its atomic equivalent) is used, we will
# get a sequence of unique run numbers.
def get_runnumber():
    global dbaccess
    if dbaccess:
        try:
            if sys.platform == 'win32':
                if FPHXTB_VERBOSE>0: print "win32 system opening connection to DSN %s" % DSN
                d = odbc.odbc(DSN)
                c = d.cursor()
            else:
                if FPHXTB_VERBOSE>0: print "non-win32 system opening connection to DSN %s" % DSN
                d = pyodbc.connect("DSN=%s;UID=%s" % (DSN,"postgres"),ansi=True)
                c = d.cursor()
                if FPHXTB_VERBOSE>0: print "successful connection to DSN %s" % DSN
        except:
            print "Invalid Data Source Name: %s" % DSN
            print "Disabling db access"
            dbaccess = 0
            return 0
    else:
        print 'db access disabled'
        return 0
    
    c.execute("BEGIN TRANSACTION")
    c.execute("LOCK TABLE %s;" % runnumber_table)
    c.execute("SELECT %s FROM %s;" % (runnumber_field,runnumber_table))
    result = c.fetchall()
    c.execute("UPDATE %s SET %s = %s + 1" % (runnumber_table,runnumber_field,runnumber_field) )
    c.execute("COMMIT TRANSACTION")
    # TODO: check that we got > 0 results
    runnumber = result[0][0]
    d.close()
    return runnumber


def insertdb(runno,starttime,endtime,filename,beam_species,beam_energy,temp,humid,chipids,masks,values):
    global dbaccess
    if dbaccess:
        try:
            if sys.platform == 'win32':
                d = odbc.odbc(DSN)
                c = d.cursor()
            else:
                d = pyodbc.connect("DSN=%s;UID=%s" % (DSN,"postgres"))
                c = d.cursor()
        except:
            print "Invalid Data Source Name: %s" % DSN
            print "Disabling db access"
            dbaccess = 0
            return 0
    else:
        print 'db access disabled'
        return 0

    chipidstr = "{"
    for i in range(0,len(chipids)):
        chipidstr += "%d" % chipids[i]
        if i != len(chipids)-1: chipidstr += ","
    else:
        chipidstr += "}"

    maskstr = "{"
    for n in range(0,len(masks)):
        maskstr += "{"
        for i in range(0,len(masks[n])):
            maskstr += "%d" % masks[n][i]
            if i != len(masks[n])-1: maskstr += ","
        else: # Post-for-loop
            maskstr += "}"
        if n != len(masks)-1: maskstr += ","
    maskstr += "}"    

    print values
    valuestr = "{"
    for i in range(0,len(values)):
        valuestr += "{"
        for j in range(0,len(values[i])):
            valuestr += "%d" % values[i][j]
            if j != len(values[i])-1: valuestr += ","
        else: # Post for-loop step
            valuestr += "}"
        if i != len(values)-1: valuestr += ","
    valuestr += "}"
    
    if FPHXTB_VERBOSE>0: print 'Inserting into db',runno,starttime,endtime,filename,beam_species,beam_energy,temp,humid,chipidstr,valuestr

    cmd = "INSERT INTO runcontrol VALUES (%d,%d,%d,\'%s\',\'%s\',%f,%f,%f,\'%s\',\'%s\',\'%s\')" %(runno,starttime,endtime,filename,
                                                                                                   beam_species,beam_energy,temp,humid,
                                                                                                   chipidstr,maskstr,valuestr)
    if FPHXTB_VERBOSE>0: print cmd

    c.execute("BEGIN TRANSACTION")
    c.execute(cmd)
    c.execute("COMMIT TRANSACTION")
    return 1

def updatedb_endtime(runno,endtime):
    global dbaccess
    if dbaccess:
        try:
            if sys.platform == 'win32':
                d = odbc.odbc(DSN)
                c = d.cursor()
            else:
                d = pyodbc.connect("DSN=%s;UID=%s" % (DSN,"postgres"))
                c = d.cursor()
        except:
            print "Invalid Data Source Name: %s" % DSN
            print "Disabling db access"
            dbaccess = 0
            return 0
    else:
        print 'db access disabled'
        return 0

    if FPHXTB_VERBOSE>0: print 'Updating DB runnumber %d with endtime %d' % (runno,endtime)
    cmd = "UPDATE runcontrol SET endruntime = %d WHERE runnumber = %d" %(endtime,runno)
    if FPHXTB_VERBOSE>0: print cmd
    c.execute("BEGIN TRANSACTION")
    c.execute(cmd)
    c.execute("COMMIT TRANSACTION")
    return 1

if __name__ == '__main__':

    wedgeaddr = 0x1F
    femaddr = None

    word = make_fphx_cmd(21,17,FPHX_WRITE,10)
    data = create_string_buffer(4)
    struct.pack_into(">I",data,0,word)
    buf = create_packet(0x3,data.raw)
    buf2 = create_packet_fphx(word)
    print 'output of create_packet_fphx = %s' % hexify_bytes(buf2)
    print 'output of create_packet      = %s' % hexify_bytes(buf)
    FPHXTB_VERBOSE = 1
    write_pulse(wedgeaddr)
    write_pulse_amp(255,wedgeaddr)
    write_pulse_amp2(255,wedgeaddr)

    pass
