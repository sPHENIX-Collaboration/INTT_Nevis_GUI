
import ftd2xx
import ctypes as c
import struct
import time
import sys, traceback
import math

DLPTH1VID = 0x0403
DLPTH1PID = 0xFBF9
DLPTH1DESC = "DLP-TH1"

SUCCESS	      = 0
FAILURE       = ~SUCCESS
DLPTH1BITMODE = 0x01			# asynchrous bit-bang mode
DLPTH1INVALID = float(999)
SET           = 1
CLEAR         = 0
DLPTH1INPUT   = 1			# bit-bang direction INPUT = 1
DLPTH1OUTPUT  = 0			# bit-bang direction OUTPUT = 0
DLPTH1DATAPOS = 1			# SHT11 pin 2 (DATA) = FT232R pin 5 (bit-bang data bus bit 1)
DLPTH1SCKPOS  = 0			# SHT11 pin 3 (SCK)  = FT232R pin 1 (bit-bang data bus bit 0)

# DLPTH1 commands
DLPTH1CMDMEASTEMP    = 0x03
DLPTH1CMDMEASHUM     = 0x05
DLPTH1CMDWRITESTATUS = 0x06
DLPTH1CMDREADSTATUS  = 0x07
DLPTH1CMDSOFTRESET   = 0x1E

DLPTH1CONFIG = 0x00
	# bit 7: reserved
	# bit 6: status of low voltage detection
	# bit 5: reserved
	# bit 4: reserved
	# bit 3: testing only, do not use
	# bit 2: heater ON/OFF
	# bit 1: no reload of calibration data
	# bit 0: resolution 0=(12bit RH, 14bit TEMP) 1=(8bit RH, 12bit TEMP)

DEBUG = False			# print debug information

class dlpth1:
    def __init__(self):
    	# initialize structure members
    	self.vid = DLPTH1VID
    	self.pid = DLPTH1PID
    	self.desc = DLPTH1DESC
    	self.data = 0
    	self.isOpen = False

        # only on linux?
        #ftd2xx.setVIDPID(self.vid,self.pid)
        return

    def open(self,devstr):
        self.port = ftd2xx.openEx(devstr)
        if self.port: self.isOpen = True

        # set timeouts
        self.port.setTimeouts(5000, 1000) # read timeout 5 sec, write timeout of 1 sec
        mask = 0xFF
        enable = DLPTH1BITMODE
        self.port.setBitMode(mask,enable)
        return

    def close(self):
        self.port.close()
        return

    def set_data_direction(self,dir):
        if dir == DLPTH1INPUT: # bit 1 set to low: input
            mask = 0xFD
        else:                  # bit 1 set to high: output
            mask = 0xFF
        enable = DLPTH1BITMODE
        self.port.setBitMode(mask,enable)
        if DEBUG: print "set_data_direction: Bit-bang data direction changed."
        return

    def set_clear_bit(self,hilow,bitpos):
        # TODO: check for valid args
        if not self.port or (bitpos<0 or bitpos>7):
            if DEBUG: print "set_clear_bit: Invalid arguments!"
            raise Exception, "set_clear_bit: Invalid arguments"
        
        # setup a mask with bit set in bitpos
        mask = 0x01;
        mask = mask << bitpos;

        # invert mask for clearing
        if hilow == 0: mask = ~mask
        
        # set or clear bit in dlp->data using mask
        if hilow == 0: self.data = self.data & mask
        else:          self.data = self.data | mask

        buf = c.create_string_buffer(1)
        struct.pack_into("B",buf,0,self.data)
        nbytes = self.port.write(buf)
        if DEBUG: print "set_clear_bit: Write to dlp-th1 success: nwritten %d data 0x%02x" % (nbytes,self.data)
        return 

    def transmission_start(self):
        # check if device is open
        if not self.isOpen:
            if DEBUG: print "transmission_start: Device is not open!"
            raise Exception,"Device not open"

        if DEBUG: print "transmission_start: Will send transmission start signal."

        self.set_data_direction(DLPTH1OUTPUT);		# direction = output	
        self.set_clear_bit(SET, DLPTH1DATAPOS);	    # set DATA
        self.set_clear_bit(SET, DLPTH1SCKPOS);		# set SCK
        self.set_clear_bit(CLEAR, DLPTH1DATAPOS);	# clear DATA
        self.set_clear_bit(CLEAR, DLPTH1SCKPOS);	# clear SCK
        self.set_clear_bit(SET, DLPTH1SCKPOS);		# set SCK
        self.set_clear_bit(SET, DLPTH1DATAPOS);	    # set DATA
        self.set_clear_bit(CLEAR, DLPTH1SCKPOS);	# clear SCK
        self.set_clear_bit(CLEAR, DLPTH1DATAPOS);	# clear DATA

        if DEBUG: print "transmission_start: Completed sending transmission start signal."
        return

    def write_byte(self,data):
        # check if device is open
        if not self.isOpen:
            if DEBUG:
                print "write_byte: Device is not open!"
            raise Exception,"Device not open"

        if DEBUG: print "write_byte: Loop over bits to write"
        for count in range(8,0,-1):
            bitvalue = data & 0x80 # select bit 7 as value to write
            self.set_clear_bit(bitvalue, DLPTH1DATAPOS)	
            self.set_clear_bit(SET, DLPTH1SCKPOS)
            self.set_clear_bit(CLEAR, DLPTH1SCKPOS)
            data <<= 1			# shift next bit in

    	# send ACK
    	if DEBUG: print "write_byte: send ACK"
    	self.set_clear_bit(CLEAR, DLPTH1DATAPOS)
    	self.set_clear_bit(SET, DLPTH1SCKPOS)
    	self.set_clear_bit(CLEAR, DLPTH1SCKPOS)

        if DEBUG: print "write_byte: Completed writing byte"
        return

    def read_byte(self,lastbyte):
        # check if device is open
        if not self.isOpen:
            if DEBUG: print "read_byte: Device is not open!"
            raise Exception,"Device not open"
        self.set_data_direction(DLPTH1INPUT)    # direction = input
        # read in the byte
        bitvalue = 0
        bytevalue = 0
        for count in range(8,0,-1):
            self.set_clear_bit(SET, DLPTH1SCKPOS)
            # read the data bit state
            bitvalue = self.port.getBitMode()
            # check for valid return?  or does it throw an exception?
            self.set_clear_bit(CLEAR, DLPTH1SCKPOS)
            bitvalue = bitvalue & 0x02                # select the data bit
            bytevalue = bytevalue << 1                # shift left by 1 bit
            if bitvalue: bytevalue |= 1     # add new data bit to byte
        # send ACK
        self.set_data_direction(DLPTH1OUTPUT)               # direction = output	
        if lastbyte == 0: self.set_clear_bit(CLEAR, DLPTH1DATAPOS)
        self.set_clear_bit(SET, DLPTH1SCKPOS)
        self.set_clear_bit(CLEAR, DLPTH1SCKPOS)
        if DEBUG: print "read_byte: Read byte value 0x%x" % bytevalue
        return bytevalue

    # Configure the advanced options of the sensor
    def configure(self):
        # check if device is open
        if not self.isOpen:
            if DEBUG: print "configure: Device is not open!"
            raise Exception,"Device not open"

        self.transmission_start()
        self.write_byte(DLPTH1CMDWRITESTATUS)
        self.write_byte(0x00)

        self.transmission_start()
        self.write_byte(DLPTH1CMDREADSTATUS)
        readbyte = self.read_byte(0)
        if DEBUG: print "configure: Read status register (val = %i)" % readbyte
        readbyte = self.read_byte(1)
        if DEBUG: print "configure: Read status register CRC (val = %i)" % readbyte

        if DEBUG: print "configure: Completed writing status register"
        return

    def calcrc(self, x):
       dscrc_table = [ 0, 49, 98, 83, 196, 245,166, 151,185, 136,219,
           234,125, 76, 31, 46, 67, 114,33, 16, 135, 182,229, 212,250,
           203,152, 169,62, 15, 92, 109,134, 183,228, 213,66, 115,32,
           17, 63, 14, 93, 108,251, 202,153, 168,197, 244,167, 150,1,
           48, 99, 82, 124, 77, 30, 47, 184, 137,218, 235,61, 12, 95,
           110,249, 200,155, 170,132, 181,230, 215,64, 113,34, 19,
           126, 79, 28, 45, 186, 139,216, 233,199, 246,165, 148,3, 50,
           97, 80, 187, 138,217, 232, 127, 78, 29, 44, 2, 51, 96, 81,
           198, 247,164, 149,248, 201,154, 171,60, 13, 94, 111, 65,
           112,35, 18, 133, 180,231, 214,122, 75, 24, 41, 190,
           143,220, 237,195, 242,161, 144, 7, 54, 101, 84, 57, 8, 91,
           106,253, 204,159, 174,128, 177,226, 211,68, 117,38, 23,
           252, 205,158, 175,56, 9, 90, 107,69, 116,39, 22, 129,
           176,227, 210,191, 142,221, 236, 123, 74, 25, 40, 6, 55,
           100, 85, 194, 243,160, 145,71, 118,37, 20, 131, 178,225,
           208, 254, 207,156, 173,58, 11, 88, 105,4, 53, 102, 87, 192,
           241,162, 147,189, 140,223, 238, 121, 72, 27, 42, 193,
           240,163, 146,5, 52, 103, 86, 120, 73, 26, 43, 188, 141,222,
           239, 130, 179,224, 209,70, 119,36, 21, 59, 10, 89, 104,255,
           206,157, 172 ]
       if DEBUG: print "calcrc: tablelen = %d, dowcrc = 0x%02x, x = 0x%02x, dowcrc^x = %d" % (len(dscrc_table),self.dowcrc,x,self.dowcrc ^ x)
       self.dowcrc = dscrc_table[self.dowcrc ^ x]    # ^ = XOR
       return

    def read_temp(self):
        #int i, measurement
        #unsigned char msb, lsb, crc, ret_crc
        if not self.isOpen:
            if DEBUG: print "read_temp: Device is not open!"
            raise Exception, "read_temp: Device is not open!"

        self.transmission_start()
        self.write_byte(DLPTH1CMDMEASTEMP)
        self.set_data_direction(DLPTH1INPUT)

        # wait for conversion to finish
        if DEBUG: print "read_temp: Wait for conversion to finish"
        busy = 1
        while busy:
            self.data = self.port.getBitMode()
            busy = self.data & 0x02;
            # sleep for 10 ms
            time.sleep(0.1)

        # read temp data
        msb = self.read_byte(0);
        lsb = self.read_byte(0);
        crc = self.read_byte(1);

    	# process CRC for the command byte
    	self.dowcrc = 0
    	self.calcrc(3)
    	self.calcrc(msb)
    	self.calcrc(lsb)

    	# reverse bit order of the returned checksum
    	ret_crc = crc
    	crc = 0
    	for i in range(0,9):
            crc = crc << 1
            if ret_crc & 0x01: crc = crc | 0x01
            ret_crc = ret_crc >> 1

        if crc != self.dowcrc:
            if DEBUG: print "read_temp: CRC of temperature reading failed!"
            self.degc = DLPTH1INVALID;
            #return
        else:
            if DEBUG: print "read_temp: CRC of temperature reading passed."

    	measurement = lsb | (msb << 8)
    	self.degc = -40.10 + (0.01 * measurement)	# Vdd = 5.0 V, 14-bit measurement
    	if DEBUG: print "read_temp: temperature =  %.1f C" % (self.degc)
    	return self.degc

    def read_humid(self):
        if not self.isOpen:
            if DEBUG: print "read_humid: Device is not open!"
            raise Exception, "read_humid: Device is not open!"

        self.transmission_start()
        self.write_byte(DLPTH1CMDMEASHUM)
        self.set_data_direction(DLPTH1INPUT)


        # wait for conversion to finish
        if DEBUG: print "read_temp: Wait for conversion to finish"
        busy = 1
        while busy:
            self.data = self.port.getBitMode()
            busy = self.data & 0x02;
            # sleep for 10 ms
            time.sleep(0.1)

        # Read humidity data
        msb = self.read_byte(0)
        lsb = self.read_byte(0)
        crc = self.read_byte(1)

        # Process CRC for the command byte
        self.dowcrc = 0
        self.calcrc(5)
        self.calcrc(msb)
        self.calcrc(lsb)

        # Reverse bit order of the returned checksum
        ret_crc = crc
        crc = 0
        for i in range(0,9):
            crc <<= 1
            if ret_crc & 0x01: crc |= 0x01
            ret_crc >>= 1

        if crc != self.dowcrc:
            if DEBUG: print "read_hum: CRC of humidity reading failed"
            self.hum = DLPTH1INVALID
        else:
            if DEBUG: print "read_him: CRC of humidity reading passed"

        measurement = lsb | (msb<<8)
        rhlin = -2.0468 + (0.0367*measurement) + (-1.5955e-6*measurement*measurement)
        rhtrue = (self.degc - 25.0) * (0.01 + .00008 * measurement) + rhlin
        self.hum = rhtrue

        if self.degc > 0:
            Tn = 243.12
            m = 17.62
        else:
            Tn = 272.62
            m = 22.46

        a = m * self.degc / (Tn + self.degc)
        b = math.log(self.hum/100)
        self.dewp = Tn * (a + b) / (m - a - b)

        if DEBUG:
            print "read_hum: humidity = %.1f %%" % self.hum
            print "read_hum: dewpoint = %.1f %%" % self.dewp
        return self.hum, self.dewp

    def getMeasurement(self):
        return self.degc, self.hum, self.dewp

if __name__ == "__main__":

    envDevList = []
    devs = ftd2xx.listDevices()
    if devs:
        for i, e in enumerate(devs):
            details = ftd2xx.getDeviceInfoDetail(i)
            #print details
            if details['description'] == 'DLP-TH1':
                envDevList.append(details['serial'])
    envDevList.append("None")

    try:
        DEBUG = 0
        sensor = dlpth1()
        print "Open device %s" % envDevList[0]
        sensor.open(envDevList[0])
        sensor.configure()
        sensor.read_temp()
        sensor.read_humid()
        tempc, rhum, dewp = sensor.getMeasurement()
        print "Temperature: %.1f C" % tempc
        print "Humidity:    %.1f %%" % rhum
        print "Dew point:   %.1f %%" % dewp
        
        sensor.close()
    except Exception, e:
        traceback.print_exc(file=sys.stdout)
        print "exception: %s" % e
        
