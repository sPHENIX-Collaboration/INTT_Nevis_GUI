
# Implements the serial interface to the E3633A and E3634A power supplies,
# using the SCPI protocol over an RS232 cable.  Based on what I have read
# in the E3634-90001.pdf manual.

# requires the pyserial module, found at http://pyserial.sourceforge.net

from __future__ import with_statement # >=2.5 only
import atexit
import serial
import time
import threading
import sys

# Toggling of the DTR is crucial for handshaking.  Here we define
# the true and false states of the DTR line as required by the target device.
DTR_TRUE = 0
DTR_FALSE = 1

# Default value of the serial port to use (note this is windows-oriented)
comport = 'COM1'

VERBOSE = 0

# Mutex lock to guarantee only one entity can access the serial port
# at a time.  (Not sure if this is needed quite yet)

class e363xx:
    def __init__(self,portname,intimeout,openflag):
        if VERBOSE: print 'e363xx: create serial port'
        self.portname = portname
        if openflag:
            if VERBOSE: print 'e363xx: open serial port'
            self.port = serial.Serial(portname,timeout=intimeout)
            self.port.setDTR(DTR_FALSE)
            self.port.write("SYST:REM\n")
            time.sleep(0.5)
        else:
            self.port = serial.Serial(None,timeout=intimeout)
            self.port.port = portname
        self.port.stopbits = 2
        self.lock = threading.Lock();
        if VERBOSE: print self.port
        if VERBOSE: print 'e363xx: register exit routine'
        atexit.register(self.close,self)
        if VERBOSE: print 'e363xx: done'
        return

    def isOpen(self):
        with self.lock:
            return self.port.isOpen()

    # Read a line from the device, stripping off the EOL stuff.
    def readline(self) :
        with self.lock:
            # PS won't send data unless DTR is "true". TODO: protect
            # from exceptions, making sure DTR is set to false on exit
            self.port.setDTR(DTR_TRUE)
            line = self.port.readline()
            line = line.rstrip('\n') # Strip the NL from the input
            line = line.rstrip('\r') # Strip the CR from the input
            self.port.setDTR(DTR_FALSE)
        return line

    # According to the E3633A manual:
    # The power supply returns four fields separated by commas and the fourth
    # field is a revision code which contains three numbers. The first number is
    # the firmware revision number for the main processor; the second is for the
    # input/output processor; and the third is for the front-panel processor.
    #
    # Examples:
    #   "HEWLETT-PACKARD,E3633A,0,X.X-X.X-X.X" (E3633A)
    #   "HEWLETT-PACKARD,E3634A,0,X.X-X.X-X.X" (E3634A)
    #
    def identify(self):
        self.port.write("*IDN?\n")
        time.sleep(0.5)
        devIdstr = self.readline()
        time.sleep(0.5)
        return devIdstr

    # Read an error from the queue, return a list of the code and message
    def readError(self):
        with self.lock:
            self.port.write("SYST:ERR?\n")
        time.sleep(0.5)
        errstr = self.readline()
        return errstr.split(",")
    
    # Close the device, making sure to leave it in local mode.
    def close(self,*args) :
        with self.lock:
            if self.port.isOpen():
                if VERBOSE: print 'Closing device -- Set Local mode'
                self.port.write("SYST:LOC\n")
                time.sleep(0.5)
                self.port.close()
            else:
                print 'e363xx.close: Device already closed'
        return

    # Measure the output voltage, returns it as a float
    def getVoltage(self):
        with self.lock:
            self.port.write("MEAS:VOLT?\n")
            time.sleep(0.4)
        ans = self.readline()
        #AMV incase the PS isn't hooked up
	if ans=="":
	    ans=-9999
	return float(ans)

    # Measure the output current, returns it as a float
    def getCurrent(self):
        with self.lock:
            self.port.write("MEAS:CURR?\n")
            time.sleep(0.4)
        ans = self.readline()
        #AMV incase the PS isn't hooked up
        if ans=="":
            ans=-9999
	return float(ans)

    def output_onoff(self,val=0):
        if val == 0:
            with self.lock:
                self.port.write("OUTPUT OFF\n")
                time.sleep(0.4)
        else:
            with self.lock:
                self.port.write("OUTPUT ON\n")
                time.sleep(0.4)
        return

    def getOutputState(self):
        with self.lock:
            self.port.write("OUTPUT?\n")
            time.sleep(0.4)
        ans = self.readline()
        #AMV incase the PS isn't hooked up
        if ans=="":
            ans=0
        return int(ans)  

if __name__ =='__main__':

    # Test code for the above class.

    print 'Create e363xx object'
    #ps = e363xx('COM1',1,False)
    try:
        ps = e363xx('COM1',1,True)
    except:
        ps.close()
        sys.exit()
        
    print 'open status = ', ps.isOpen()
    if ps.isOpen():
        # Read the entire error queue, stopping when there are no more
        for i in range(0,20):
            err = ps.readError()
            print 'last error =', err
            if err[1] == '"No error"': break

        # Get some info from the device
        print 'Model:', ps.identify()
        print 'Output Voltage Readback =',ps.getVoltage()
        print 'Output Current Readback =',ps.getCurrent()

        ps.close()

    print 'Call sys.exit()'
    sys.exit()
    
