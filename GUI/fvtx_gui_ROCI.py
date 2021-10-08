#!/usr/bin/python

#  FVTX Graphic User Interface
#  Author: Zhengyun You 
#  Usage:  python fvtx_gui.py -test
#          or -roc -fvtx -ldrd 

from Tkinter import *
from tkMessageBox import showerror
import struct
import sys
import time
import tkFileDialog
import string
import os
import shutil
try:
    import ftd2xx
except:
    print "Failed to import ftx2dxx"
from ctypes import * #create_string_buffer

# Debugging the FTD2xx read function
#import ctypes

option_chip = 'fphx'
for arg in sys.argv[1:] :
    if arg.count( 'fpix' ) > 0 :
        option_chip = 'fpix'
    elif arg.count( 'fphx' ) > 0 :
        option_chip = 'fphx'

option_destine = 'chip'

option = 'test'
#print 'Number of argv is : %d' % len(sys.argv)
for arg in sys.argv[1:] :
    #print arg
    if arg.count( 'test' ) > 0 :
        option = 'test'
    elif arg.count( 'ldrd' ) > 0 :
        option = 'ldrd'
    elif arg.count( 'fvtx' ) > 0 :
        option = 'fvtx'
    elif arg.count( 'roc' ) > 0 :
        option = 'roc'
print 'option mode is %s' % option    
if option == 'test' :
    n_module = [2, 2, 2, 2]
    n_column = 1
    n_chip = [2, 2, 2, 2]
elif option == 'ldrd' :
    print 'Opening LDRD configure...'
    n_module = [12, 20, 20, 20]
    n_column = 1
    n_chip = [8, 8, 8, 8]
elif option == 'fvtx' :
    print 'Opening FVTX configure...'
    n_module = [48, 48, 48, 48]
    n_column = 2
    n_chip = [5, 13, 13, 13]
elif option == 'roc' :
    print 'Opening ROC configure...'
    n_module = [2, 2, 2, 2]
    n_column = 2
    n_chip = [5, 13, 13, 13]

n_station = 4
if option_chip == 'fpix' :
    n_register = 32
    register_name = ['', 'lbp1', 'lbp2', 'lbb', 'lff', 'Verf', 'Vfb2', 'Vth0',
                     'Vth1', 'Vth2', 'Vth3', 'Vth4', 'Vth5', 'Vth6', 'Vth7', 'AqBCO',
                     'Alines', 'Kill', 'Inject', 'SendData', 'RejectHits', 'WildReg', 'Mod256', 'SPR',
                     'SPR', 'SPR', 'SPR', 'SPR', 'SCR', 'SCR', 'SCR', 'SCR']
    register_default = [0, 100, 74, 29, 13, 202,172, 8, 8, 8, 8, 8, 8, 8, 8, 0,
                        0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    register_display_no = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 17]
elif option_chip == 'fphx' :
    n_register = 18
    n_seg_max = 2
    register_info = [[['Mask', 0, 7, 0]],
                     [['Digital Ctrl', 0, 7, 1]],
                     [['Vref', 0, 1, 1]],
                     [['Thr DAC 0', 0, 7, 8]],
                     [['Thr DAC 1', 0, 7, 16]],
                     [['Thr DAC 2', 0, 7, 32]],
                     [['Thr DAC 3', 0, 7, 48]],
                     [['Thr DAC 4', 0, 7, 80]],
                     [['Thr DAC 5', 0, 7, 112]],
                     [['Thr DAC 6', 0, 7, 144]],
                     [['Thr DAC 7', 0, 7, 176]],
                     [['N1Sel', 0, 3, 6], ['N2Sel', 4, 7, 4]],
                     [['FB1Sel', 0, 3, 4], ['LeakSel', 4, 7, 0]],
                     [['P3Sel', 0, 1, 0], ['P2Sel', 4, 7, 4]],
                     [['GSel', 0, 1, 1],  ['BWSel', 3, 7, 4]],
                     [['P1Sel', 0, 2, 5], ['InjSel', 3, 5, 0]],
                     [['LVDS Current', 0, 3, 15]],
                     [['Programmable Reset', 0, 7, 0]]]

    register_default = [0, 1, 1, 8, 16, 32, 48, 80,
                        112, 144, 176, 6, 4, 0, 1, 5,
                        15, 0]    
    register_display_no = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]

global register_data
register_data = []

wild_chip_state = 1
if option == 'roc' :
    wild_chip_state = 0
        
data_mode = 1
instr_id = '001'
check_id = '000'

station_file_name = ['station0.txt', 'station1.txt', 'station2.txt', 'station3.txt']
station_new_file_name = ['station0_new.txt', 'station1_new.txt', 'station2_new.txt', 'station3_new.txt']

class Alarm(Frame):
    def repeater(self):                           # on every N millisecs
        self.bell( )                              # beep now
        self.stopper.flash( )                     # flash button now
        self.after(self.msecs, self.repeater)      # reschedule handler
    def __init__(self, msecs=1000):              # default = 1 second
        Frame.__init__(self)
        self.msecs = msecs
        self.pack( )
        stopper = Button(self, text='Stop the beeps!', command=self.quit)
        stopper.pack( )
        stopper.config(bg='navy', fg='white', bd=8)
        self.stopper = stopper
        self.repeater( )

class Cur_Time( Frame ) :
    def repeater( self ) :
        self.time_lbl.config( text=time.ctime() )
        self.after( self.msecs, self.repeater )
    def __init__( self, msecs=1000 ) :
        Frame.__init__( self )
        self.msecs = msecs
        self.pack()
        #print time.strftime('%Y-%m-%d',time.localtime(time.time()))
        time_lbl = Label( self, text=time.ctime() )
        time_lbl.config( bg='navy', fg='white', bd=8 )
        time_lbl.pack()
        self.time_lbl = time_lbl
        self.repeater()

def bin_to_dec( bin_str ) :
    dec_num = 0
    n_bit = len( bin_str )
    for i in range( 0, n_bit ) :
        cur_bit = int( bin_str[n_bit-i-1 : n_bit-i] )
        dec_num += cur_bit * (2**i)
    return dec_num

def check_dec_length( dec_num, n_bit ) :
    if dec_num >= 2**n_bit :
        print 'dec_to_bin error: input num ', dec_num, ' > ', 2**n_bit-1, '(', n_bit, ' bit range)'
        return 0
    elif dec_num < 0 :
        print 'dec_to_bin error: can not transform negative num ', dec_num
        return 0
    else :
        return 1
    
def dec_to_bin( dec_num, n_bit ) :
    if check_dec_length( dec_num, n_bit ) == 0 : return ''
    bin_str = ''
    i_bit = 0
    while dec_num != 0 :
        mod = dec_num % 2
        dec_num = (dec_num - mod) / 2
        bin_str = str( mod ) + bin_str
        i_bit += 1
    for i in range( n_bit-i_bit) :
        bin_str = '0' + bin_str
    #print bin_str
    return bin_str

def bin_to_hex( bin_str) :
    hex_str = ''
    n_bit = len(bin_str)
    for i in range( 0, n_bit, 4 ) :
        dec_num = 0
        for j in range(0, 4) :
            cur_bit = int( bin_str[n_bit-(i+j)-1 : n_bit-(i+j)] )
            dec_num += cur_bit * (2**j)
        hex_num = str(dec_num)
        if (dec_num == 10) : hex_num = 'A'
        elif (dec_num == 11) : hex_num = 'B'
        elif (dec_num == 12) : hex_num = 'C'
        elif (dec_num == 13) : hex_num = 'D'
        elif (dec_num == 14) : hex_num = 'E'
        elif (dec_num == 15) : hex_num = 'F'
        hex_str = str(hex_num) + hex_str
    return hex_str
        
def get_bytes( bin_str ) :
    byte_list = []
    for i in range( 0, len(bin_str), 8 ) :
        sub_str = bin_str[i:i+8]
        dec_num = bin_to_dec( sub_str )
        byte_chr = chr(dec_num)
        print sub_str, dec_num, byte_chr
        byte_list.append( byte_chr )
    #print byte_list
    return byte_list

def pack_string( bin_str ) :
    nbytes = len(bin_str) / 8
    #byte_list = []
    #raw = create_string_buffer(16)
    raw = create_string_buffer(nbytes)
    n = 0
    #print len(bin_str)
    for i in range( 0, len(bin_str), 8 ) :
        sub_str = bin_str[i:i+8]
        dec_num = bin_to_dec( sub_str )
        byte_chr = chr(dec_num)
        #print sub_str, dec_num, byte_chr
        struct.pack_into("B",raw,n,dec_num)
        n = n+1
    #print byte_list
    return raw

def write_bytes( file, bin_str ) :
    for i in get_bytes( bin_str ) :
        file.write( i )

def read_bytes( file, n_bytes ) :
    buf = file.read( n_bytes )
    #print buf
    bin_str = ''
    for i in buf :
        dec_num = int( struct.unpack('b', i)[0] )  # unpack return a tuple
        if dec_num < 0 : dec_num += 256
        str_tmp = dec_to_bin( dec_num, 8 )
        #print str(dec_num).rjust(3), '=', str_tmp
        bin_str += str_tmp
    #print bin_str
    return bin_str

def test_write_bytes() :
    test_file = open( 'test_write_bytes.txt', 'wb' )
    write_bytes( test_file, '0000001100001100' )
    dec_to_bin( 31, 8 )
    test_file.close()

def write_txt( file, i_register, data ) :
    txt_str = ('reg' + str(i_register)).ljust(8) + str(data).rjust(4) + '\n'
    file.write( txt_str )

def read_txt() :
    print "read"
    
def get_file_name( i_station = -1, i_module = -1, i_column = -1, i_chip = -1, i_new=-1 ) :
    if i_station != -1 :
        file_name = 'station_' + str(i_station)
    if i_module != -1 :
        file_name += '_module_' + str(i_module)
    if i_column != -1 :
        file_name += '_column_' + str(i_column)
    if i_chip != -1 :
        file_name += '_chip_' + str(i_chip)
    file_name += '.dat'

    if i_new != -1 :
        file_name = 'new_' + file_name
    return file_name

def write_chip( i_station, i_module, i_column, i_chip ) :
    head = 1
    return

def write_module( i_station, i_module ) :
    #print "station %i module %i " % (i_station, i_module)
    for i_column in range( n_column ) :
        for i_chip in range( n_chip[i_station] ) :
            write_chip( i_station, i_module, i_column, i_chip )
    return

def update_register( i_station = -1, i_module = -1, i_column = -1, i_chip = -1, i_register = -1, register_data_tmp = -1 ) :
    for i_seg in range( len(register_info[i_register]) ) :
#        if check_reply[i_station][i_module][i_column][i_chip][i_register] :
            print 'update_register ', register_data_tmp
            #mem_data_lbl[i_station][i_module][i_column][i_chip][i_register][i_seg].config( text=str( decode_register(register_data_tmp, i_register, i_seg) ) )
            data_ent[i_station][i_module][i_column][i_chip][i_register][i_seg].delete( 0, END )
            data_ent[i_station][i_module][i_column][i_chip][i_register][i_seg].insert( 0, str( decode_register(register_data_tmp, i_register, i_seg) ) )
            print 'register_data = ', data_ent[i_station][i_module][i_column][i_chip][i_register][i_seg].get()
    return

def highlight_register( i_station = -1, i_module = -1, i_column = -1, i_chip = -1, i_register = -1, i_seg = 0 ) :
    if data_ent[i_station][i_module][i_column][i_chip][i_register][i_seg] :
        #print data_ent[i_station][i_module][i_column][i_chip][i_register][i_seg].cget( 'font' )
        data_ent[i_station][i_module][i_column][i_chip][i_register][i_seg].config( fg='red', font='{FixedSys}' )
    return

def un_highlight_register( i_station = -1, i_module = -1, i_column = -1, i_chip = -1, i_register = -1, i_seg = -1 ) :
    if data_ent[i_station][i_module][i_column][i_chip][i_register][i_seg] :
        data_ent[i_station][i_module][i_column][i_chip][i_register][i_seg].config( fg='SystemWindowText', font='{MS Sans Serif} 8' )
    return

def write_file_dialog( i_station = -1, i_module = -1, i_column = -1, i_chip = -1 ) :
    default_name = get_file_name( i_station, i_module, i_column, i_chip )
    file_name = tkFileDialog.asksaveasfilename( filetypes=[('Binary Files','*.dat'), ('Text Files','*.txt'), ('All Files', '*')], initialfile=default_name, defaultextension='dat' )
    print file_name
    if( file_name == '' ) :
        return

    file_format = 'txt'
    file = open(file_name, 'w')
    if file_name[-3:] == 'dat' :
        file_format = 'bin'
        file = open(file_name, 'wb')
    print "file_format = ", file_format

    global register_data
    station_begin = i_station
    station_end = i_station + 1
    if i_station == -1 :
        station_begin = 0
        station_end = n_station
    for i_station in range( station_begin, station_end ) :
        module_begin = i_module
        module_end = i_module + 1
        if i_module == -1 :
            module_begin = 0
            module_end = n_module[i_station]
        for i_module in range( module_begin, module_end ) :
            column_begin = i_column
            column_end = i_column + 1
            if i_column == -1 :
                column_begin = 0
                column_end = n_column
            for i_column in range( column_begin, column_end ) :
                chip_begin = i_chip
                chip_end = i_chip + 1
                if i_chip == -1 :
                    chip_begin = 0
                    chip_end = n_chip[i_station]
                for i_chip in range( chip_begin, chip_end ) :
                    for i_register in range( 0, n_register ) :
                        packet_data = get_write_packet( i_station, i_module, i_column, i_chip, i_register, register_data[i_station][i_module][i_column][i_chip][i_register] )
                        print i_station, str(i_module).rjust(2), i_column, str(i_chip).rjust(2), str(i_register).rjust(2), ' = ', packet_data
                        if file_format == 'txt' :
                            write_txt( file, i_register, register_data[i_station][i_module][i_column][i_chip][i_register] )
                        if file_format == 'bin' :
                            write_bytes( file, packet_data )
    file.close()

def read_file_dialog( i_station = -1, i_module = -1, i_column = -1, i_chip = -1, register_no = -1 ) :
    default_name = get_file_name( i_station, i_module, i_column, i_chip )
    file_name = tkFileDialog.askopenfilename( filetypes=[('Config Files','*.dat'), ('All Files', '*')], initialfile=default_name, defaultextension='dat' )
    print file_name
    if( file_name == '' ) :
        return
    file = open(file_name, 'rb')
    
    global register_data
    station_begin = i_station
    station_end = i_station + 1
    if i_station == -1 :
        station_begin = 0
        station_end = n_station
    for i_station in range( station_begin, station_end ) :
        module_begin = i_module
        module_end = i_module + 1
        if i_module == -1 :
            module_begin = 0
            module_end = n_module[i_station]
        for i_module in range( module_begin, module_end ) :
            column_begin = i_column
            column_end = i_column + 1
            if i_column == -1 :
                column_begin = 0
                column_end = n_column
            for i_column in range( column_begin, column_end ) :
                chip_begin = i_chip
                chip_end = i_chip + 1
                if i_chip == -1 :
                    chip_begin = 0
                    chip_end = n_chip[i_station]
                for i_chip in range( chip_begin, chip_end ) :
                    for i_register in range( 0, n_register ) :
                        packet_data = read_bytes( file, 12 )
                        register_data_tmp[i_station][i_module][i_column][i_chip][i_register] = bin_to_dec( packet_data[77:85] )
                        if register_no == -1 or register_no == i_register :
                            #register_data[i_station][i_module][i_column][i_chip][i_register] = register_data_tmp[i_station][i_module][i_column][i_chip][i_register]
                            update_register( i_station, i_module, i_column, i_chip, i_register,register_data_tmp[i_station][i_module][i_column][i_chip][i_register] )
                            #print i_station, i_module, i_column, i_chip, i_register, str( register_data[i_station][i_module][i_column][i_chip][i_register] ).rjust(3), ' in ', packet_data
    file.close()

def get_register_data_default( i_station = -1, i_module = -1, i_column = -1, i_chip = -1, i_register = -1 ) :
    register_value = 0
    if len(register_info[i_register]) == 1 :
        register_value = register_info[i_register][0][3]
    else :
        for i_seg in range( len(register_info[i_register]) ) :
            register_value += (2**register_info[i_register][i_seg][1]) * register_info[i_register][i_seg][3]
    #print register_value
    return register_value
    
def init() :
    global register_data    
    register_data = [[[[[ get_register_data_default(i,j,k,l,m) for m in range(n_register)] for l in range(max(n_chip))] for k in range(n_column)] for j in range(max(n_module))] for i in range(n_station)]     
    #print len( register_data )
    #print register_data[0][0][0][0][0][1]
    global register_data_tmp
    register_data_tmp = [[[[[0 for m in range(n_register)] for l in range(max(n_chip))] for k in range(n_column)] for j in range(max(n_module))] for i in range(n_station)] 
    global module_win
    module_win = [[0 for j in range(max(n_module))] for i in range(n_station)]
    global chip_win
    chip_win = [[[[0 for l in range(max(n_chip))] for k in range(n_column)] for j in range(max(n_module))] for i in range(n_station)]
    global data_ent
    data_ent = [[[[[[0 for n in range(n_seg_max)] for m in range(n_register)] for l in range(max(n_chip))] for k in range(n_column)] for j in range(max(n_module))] for i in range(n_station)]
    global module_data_ent
    module_data_ent = [[[[[0 for n in range(n_seg_max)] for m in range(n_register)] for k in range(n_column)] for j in range(max(n_module))] for i in range(n_station)]
    global mem_data_lbl
    mem_data_lbl = [[[[[[0 for n in range(n_seg_max)] for m in range(n_register)] for l in range(max(n_chip))] for k in range(n_column)] for j in range(max(n_module))] for i in range(n_station)]
    global module_mem_data_lbl
    module_mem_data_lbl = [[[[[[0 for n in range(n_seg_max)] for m in range(n_register)] for l in range(max(n_chip))] for k in range(n_column)] for j in range(max(n_module))] for i in range(n_station)]
#    usb_comm()
    return
    
def kill_module( event ) :
    global module_win
    #print event.widget
    index = str(event.widget).replace('.','_').split('_')
    print index
    i_station = int( index[2] )
    i_module = int( index[4] )
    module_win[i_station][i_module] = 0

def kill_chip( event ) :
    global chip_win
    #print event.widget
    index = str(event.widget).replace('.','_').split('_')
    #print index
    i_station = int( index[2] )
    i_module = int( index[4] )
    i_column = int( index[6] )
    i_chip = int( index[8] )
    chip_win[i_station][i_module][i_column][i_chip] = 0

def focus_chip( i_station, i_module, i_column, i_chip ) :
    global chip_win
    chip_win[i_station][i_module][i_column][i_chip].deiconify()
    
def read_data( i_station, i_module, i_column, i_chip, i_register ) :
    read_file_dialog(  i_station, i_module, i_column, i_chip, i_register )
    #update_register( i_station, i_module, i_column, i_chip, i_register )
    focus_chip( i_station, i_module, i_column, i_chip )
    
def write_data( i_station, i_module, i_column, i_chip, i_register ) :
    global data_ent
    global module_data_ent
    tmp_data = 0
    for i_seg in range( len(register_info[i_register]) ) :
        if (i_chip == -1) : ent_value = int( module_data_ent[i_station][i_module][i_column][i_register][i_seg].get() )
        else : ent_value = int( data_ent[i_station][i_module][i_column][i_chip][i_register][i_seg].get() )
        if check_dec_length( ent_value, register_info[i_register][i_seg][2]-register_info[i_register][i_seg][1]+1 ) == 0 : showerror(title='Error', message='data value out of range.\n fix it!' )
        #encode
        tmp_data += ent_value * (2**register_info[i_register][i_seg][1])
    if (i_chip == -1) :
        for j_chip in range( n_chip[i_station] ) :
            register_data[i_station][i_module][i_column][j_chip][i_register] = tmp_data
    else :
        register_data[i_station][i_module][i_column][i_chip][i_register] = tmp_data
    for i_seg in range( len(register_info[i_register]) ) :
        if (i_chip == -1) :
            for j_chip in range( n_chip[i_station] ) :
                module_mem_data_lbl[i_station][i_module][i_column][j_chip][i_register][i_seg].config( text=str( decode_register(register_data[i_station][i_module][i_column][j_chip][i_register], i_register, i_seg)))
                print i_station, i_module, i_column, j_chip, i_register, '=', register_data[i_station][i_module][i_column][j_chip][i_register]
        else :
            mem_data_lbl[i_station][i_module][i_column][i_chip][i_register][i_seg].config( text=str( decode_register(register_data[i_station][i_module][i_column][i_chip][i_register], i_register, i_seg)))
            un_highlight_register( i_station, i_module, i_column, i_chip, i_register, i_seg )
            print i_station, i_module, i_column, i_chip, i_register, '=', register_data[i_station][i_module][i_column][i_chip][i_register]
    if (i_chip != -1) : focus_chip( i_station, i_module, i_column, i_chip )

def check_reply( reply_file_name ) :
    while 1 :
        e = os.path.exists( reply_file_name )   
        #print e #   True
        if e :
            #print 'reply exist'
            reply_file = open( reply_file_name, 'rb')
            break;
#       else :
#           print 'no reply exist'
#       time.sleep(1)
    buf = reply_file.read(1)
    dec_num = int( struct.unpack('b', buf)[0] )
    if dec_num < 0 : dec_num += 256
    print buf, ' = ', dec_num
    reply_file.close()
    #time.sleep(1)
    os.remove( reply_file_name )    
    return dec_num

def get_write_enable_packet() :
    head = dec_to_bin( 255, 8 )
    length = dec_to_bin( 2, 16 ) # 1bytes
    tail = dec_to_bin( 255, 8 )
    if (option_chip == 'fpix') :
        command_bit = dec_to_bin( 1, 8 )
        instruction = dec_to_bin( 6, 8 )  # 06 means write enable, one more byte to avoid too short to be indentified
    elif (option_chip == 'fphx') :
        destine_bit = dec_to_bin( 4, 8 )  # reset : 4
        instruction = dec_to_bin( 7, 8 )  # 111 : 7
    packet_data = head + length + command_bit + instruction + tail
    return packet_data

def make_fphx_cmd(chipId, regId, cmd, data) :
    header = 0x76
    trailer = 0x0
    word = int(0)
    word = header << (32-7)
    word |= (0x1F & chipId)<<(32-12)
    word |= (0x1F & regId) <<(32-17)
    word |= (0x7 & cmd) <<(32-20)
    word |= (0xFF & data) <<(32-28)
    word |= (0xF & trailer)
    return word
        
def get_write_packet( i_station, i_module, i_column, i_chip, i_register, instr ) :
    global register_data
    global wild_chip_state
    if (option_chip == 'fpix') :
        register_start = register_display_no[0]
        head = dec_to_bin( 255, 8 )
        length = dec_to_bin( 8, 16 ) # 8bytes
        destine_bit = dec_to_bin( 1, 8 )
        location = dec_to_bin( i_station, 2 ) + dec_to_bin( i_module, 6 )
        instruction = dec_to_bin( 2, 8 )  # 02 means write
        address = dec_to_bin( 2048*i_chip + 3*i_register, 24 )
        tail = dec_to_bin( 255, 8 )
        chip_id = dec_to_bin( i_column, 1 ) + dec_to_bin( i_chip, 4 )
        register_id = dec_to_bin( i_register+1, 5 )
        instr_id = dec_to_bin( instr, 3 )
        data_id = dec_to_bin( register_data[i_station][i_module][i_column][i_chip][i_register], 8 )
        check_id = dec_to_bin( 0, 3 )
        packet_data = head + length + destine_bit + instruction + address + check_id + chip_id + register_id + instr_id + data_id + tail
    elif (option_chip == 'fphx') :
        head = dec_to_bin( 255, 8 )
        length = dec_to_bin( 5, 16 ) # 5bytes
        if option_destine=='eprom' :
            destine_bit = dec_to_bin( 1, 8 ) # 1: eprom, 2: read, 3: chip, 4: reset
        elif option_destine=='chip' :
            destine_bit = dec_to_bin( 3, 8 )
        command_head = '1100111'
        if wild_chip_state :
#            chip_id = dec_to_bin( 21, 5 ) # wild_chip : '10101'
            chip_id = dec_to_bin( 0, 5 ) # chip_id : '00000'
        else :
            chip_id = dec_to_bin( i_column, 1 ) + dec_to_bin( i_chip, 4 )
        register_id = dec_to_bin( i_register+1, 5 )
        instr_id = dec_to_bin( instr, 3 )
        data_id = dec_to_bin( register_data[i_station][i_module][i_column][i_chip][i_register], 8 )
        command_tail = '0000' 
        tail = dec_to_bin( 255, 8 )
        packet_data = head + length + destine_bit + command_head + chip_id + register_id + instr_id + data_id + command_tail + tail 
    return packet_data

def get_read_packet( i_station, i_module, i_column, i_chip, i_register ) :
    if (option_chip == 'fpix') :
        head = dec_to_bin( 255, 8 )
        length = dec_to_bin( 6, 16 ) # 8bytes
        command_bit = dec_to_bin( 1, 8 )
        instruction = dec_to_bin( 3, 8 ) # 03 means read
        tail = dec_to_bin( 255, 8 )
        register_id = dec_to_bin( 2048*i_chip + 3*i_register+2, 24 ) + dec_to_bin( 0, 8 )
        packet_data = head + length + command_bit + instruction + register_id + tail
    elif (option_chip == 'fphx') :
        head = dec_to_bin( 255, 8 )
        length = dec_to_bin( 6, 16 ) # 8bytes
        command_bit = dec_to_bin( 1, 8 )
        instruction = dec_to_bin( 3, 8 ) # 03 means read
        tail = dec_to_bin( 255, 8 )
        register_id = dec_to_bin( 2048*i_chip + 3*i_register+2, 24 ) + dec_to_bin( 0, 8 )
        packet_data = head + length + command_bit + instruction + register_id + tail    
    return packet_data

# Utility to purge the USB port, user supplying the flag controlling which direction
def purge_usb(flag) :
    port = ftd2xx.open()
    port.purge(flag)
    port.close()
    return None

# DLW, 2008-10-21
# Write a data packet to the usb port.  The packet data is formatted as a string
# (literally!) of 1's and 0's.  It returns the 1-byte response from the device, in decimal
# form.
def write_bin_str_to_usb(packet_data) :
    print 'write_bin_str_to_usb : len(packet_data)=',len(packet_data),'\"bits\"'
    rawbuf = pack_string(packet_data)
    print 'write_bin_str_to_usb : len(rawbuf)=',len(rawbuf),'bytes'
    buf = write_bytes_to_usb(rawbuf)
    dec_num = int( struct.unpack('b', buf)[0] )
    if dec_num < 0 : dec_num += 256 # poor man's unsigned variable
    print 'write_bin_str_to_usb: returned response: ', dec_num
    return dec_num

# DLW, 2008-10-21
# Write a data packet to the usb port.  The packet data is in raw bytes.  It returns
# the 1-byte response from the device, but in raw form also.
def write_bytes_to_usb(rawbuf) :
    print 'write_bytes_to_usb'
    port = ftd2xx.open()

    # Here we do 2 write-read operations to be able to get back the expected response from the chip.
    # This is because of the unfortunate feature of the DLP-2232's Sync BitBang mode that it sends you the current data
    # on the pins before reading them again. 
    for i in range(2) :
        port.setBitMode(255,4) # set port direction FF = all output, 00 = input, bit bang mode
        port.purge(3) # 1 == FT_PURGE_RX, 2 == FT_PURGE_TX, 3 == both TX and RX (OR of 1 and 2)
        nwritten = port.write(rawbuf)
        print 'write_bytes_to_usb: wrote',nwritten,'bytes'
        if port.getQueueStatus() < 1 :
            timeout = 10000
            print 'getQueueStatus reports no RX data, set read timeout to',timeout,'msec'
            port.setTimeouts(timeout,0)
        print 'write_bytes_to_usb: try to read 1 byte'
        buf = port.read(1)
    ############################# Test code that mimics the implmentation of ftd2xx.read().
##    port.setBitMode(0,4)
##    port.purge(1)
##    b_read = ctypes.wintypes.DWORD()
##    nchars = 1
##    b = ctypes.c_buffer(nchars)
##    FT_Read = WinDLL('ftd2xx.dll').FT_Read
##    ftd2xx.call_ft(FT_Read, port.handle, b, nchars, ctypes.byref(b_read))
##    if b_read.value != nchars : print 'WARNING: Read ',b_read.value,' bytes, wanted 1'
##    buf = b.raw[:b_read.value]
    #############################
        if ( len(buf) < 1 ) : print 'write_bytes_to_usb: WARNING: No data read back from USB port'
        print 'write_bytes_to_usb: Length of readback from USB = ',len(buf)
    dec_num = int( struct.unpack('b', buf)[0] )
    if dec_num < 0 : dec_num += 256
    print 'write_bytes_to_usb: read back response: ', dec_num
    port.close()
    return buf

def write_enable_packet(packet_file_name, reply_file_name) :
    write_enable_data = get_write_enable_packet()
    write_bin_str_to_usb(write_enable_data) # Use the USB device directly, instead of the middle-man file
#    print bin_to_hex( write_enable_data )
#    packet_file = open( packet_file_name, 'wb' )
#    write_bytes( packet_file, write_enable_data )
#    packet_file.close()
    #( reply_file_name )
    return

def write_all_packet_on_column( i_station, i_module, i_column, i_register ) :
    for i_chip in range( n_chip[i_station] ) :
        write_packet( i_station, i_module, i_column, i_chip, i_register, 1)
    return

def read_all_packet_on_column( i_station, i_module, i_column, i_register ) :
    for i_chip in range( n_chip[i_station] ) :
        read_packet( i_station, i_module, i_column, i_chip, i_register)
    return

# DLW, 2008-10-21
# Reimplement write_packet to use the routines that access the usb port
# directly instead of via intermediate files.
def write_packet( i_station, i_module, i_column, i_chip, i_register, instr ) :
    print 'write_packet (new)'
    if (i_register == -1) :
        packet_data = ""
        for i_register_display in range( len(register_display_no) ) :
            packet_data = packet_data + get_write_packet( i_station, i_module, i_column, i_chip, register_display_no[i_register_display], instr )
    else :
        packet_data = get_write_packet( i_station, i_module, i_column, i_chip, i_register, instr)
    print bin_to_hex( packet_data )
    dec_num = write_bin_str_to_usb(packet_data)
    print 'write_packet: read back response = ', dec_num
    return
    
#def write_packet( i_station, i_module, i_column, i_chip, i_register, instr ) :
#    print 'write_packet'
#    packet_file_name = 'packet.dat'
#    reply_file_name = 'reply.dat'
#    if option_destine=='eprom' :
#        write_enable_packet(packet_file_name, reply_file_name)
#    
#    packet_file = open( packet_file_name, 'wb')
#    if (i_register == -1) :
#        packet_data = ""
#        for i_register_display in range( len(register_display_no) ) :
#            packet_data = packet_data + get_write_packet( i_station, i_module, i_column, i_chip, register_display_no[i_register_display], instr )
#    else :
#        packet_data = get_write_packet( i_station, i_module, i_column, i_chip, i_register, instr)
#    print bin_to_hex( packet_data )
#    write_bytes( packet_file, packet_data )
#    packet_file.close()
#    check_reply( reply_file_name )
#    return

def read_packet( i_station, i_module, i_column, i_chip, i_register ) :
    print 'read_packet'
    packet_file_name = 'packet.dat'
    reply_file_name = 'reply.dat'
#    packet_file = open( packet_file_name, 'wb')
    packet_data = get_write_packet( i_station, i_module, i_column, i_chip, i_register, 1 )
    print bin_to_hex( packet_data )
    reply_data = write_bin_str_to_usb(packet_data) # Use the USB device directly, instead of the middle-man file
#    write_bytes( packet_file, packet_data )
#    packet_file.close()
#    reply_data = check_reply( reply_file_name )
    print 'reply data returns ', reply_data
    update_register( i_station, i_module, i_column, i_chip, i_register, reply_data )
    highlight_register( i_station, i_module, i_column, i_chip, i_register)
    return

def write_packet_from_file( source_file ) :

    packet_file_name = 'packet.dat'
    reply_file_name = 'reply.dat'
    if len( source_file ) == 0 :
        file_name = tkFileDialog.askopenfilename( filetypes=[('Packet Files','*.dat'), ('All Files', '*')], initialfile='init.dat', defaultextension='dat' )
    else :
        file_name = source_file
    print 'write_packet_from_file : ', file_name
    if option_destine=='eprom' :
        write_enable_packet(packet_file_name, reply_file_name)
## Fix this line to read in file_name rather than source_file, so that it works in
## write_from_file interactive mode. --MLB & Soumik
##    packet_file = open( source_file, 'rb')
    packet_file = open( file_name, 'rb')
    buf = packet_file.read()
    write_bytes_to_usb(buf) # Use the USB device directly, instead of the middle-man file
    #shutil.copyfile( file_name, packet_file_name )
    #check_reply( reply_file_name )
    return

def write_reset() :
    #write_packet_from_file('reset.dat')
    raw = create_string_buffer(2+2+2)
    struct.pack_into("B",raw,0,0xFF) # start-of-packet
    struct.pack_into(">H",raw,1,0x02) # 2 bytes in length, packed big-endian
    struct.pack_into("B",raw,3,0x04) # 0x04 = reset command
    struct.pack_into("B",raw,4,0xFF) # data? I just replicate what's in the file 'reset.dat'
    struct.pack_into("B",raw,5,0xFF) # end-of-packet
    #print 'test packet = ',repr(raw.raw)
    write_bytes_to_usb(raw)

# Initialize the chip registers with a canned sequence of values
def write_init() :
    filename = 'init.dat'
    if os.path.exists(filename) :
        write_packet_from_file('init.dat')
        return
    else :
        print 'write_init:',filename,'does not exist'

    # User wildchip id for init
    chipId = 21
    regs = [3,4, 5, 6, 7, 8,  9, 10, 11,12,13,14,15,16,17,  1,2]
    ops  = [1,1, 1, 1, 1, 1,  1,  1,  1, 1, 1, 1, 1, 1, 1,  2,1]
    vals = [1,8,16,32,48,80,112,144,176,70, 4,64,33, 5, 3,128,7]

    length = int(17*4+1) # 17 commands + one destination byte
    dest = 0x3 # destination = to FPHX

    packet = create_string_buffer(73) # total length = length + 2 bytes of marker + 2 bytes of length value
    offset = 0
    struct.pack_into("B",packet,offset,0xFF) # start-of-packet
    offset += 1
    struct.pack_into(">H",packet,offset,length) # 
    offset += 2
    struct.pack_into("B",packet,offset,dest) # 
    offset += 1

    #print "0x%x" % struct.unpack("B",packet[0])
    #print "0x%x" % struct.unpack("B",packet[1])
    #print "0x%x" % struct.unpack("B",packet[2])
    #print "0x%x" % struct.unpack("B",packet[3])

    offset = 4    
    for i in range(0,17) :
        word = make_fphx_cmd(chipId,regs[i],ops[i],vals[i])
        #print "offset %d 0x%x" % (offset,word)
        struct.pack_into(">I",packet,offset,word)
        offset += 4

    struct.pack_into("B",packet,offset,0xFF) #end of packet

    #print repr(packet.raw)
    write_bytes_to_usb(packet)
    
def set_btn_state( btn, state ) :
    #print btn
    #print btn['text']
    if state :
        btn.config( text='X', bg='red' )
    else :
        btn.config( text='O', bg='green')
    return

def mask_channel( i_station, i_module, i_column, i_chip, channel ) :
    global register_data
    global mask_btn
    register_data[i_station][i_module][i_column][i_chip][0] = channel
    mask_state = 1
    if mask_btn[channel]['text'] == 'O' :
        mask_state = 1
        instr = 2  # instr : 010
    else :
        mask_state = 0
        instr = 5  # instr : 101
    set_btn_state( mask_btn[channel], mask_state )
    write_packet( i_station, i_module, i_column, i_chip, 0, instr ) # i_register = 0 is mask
    return

def mask_all_on_press( i_station, i_module, i_column, i_chip ) :
    global mask_btn
    global mask_all_state
    mask_all_state = not mask_all_state
    print 'mask all : ', mask_all_state
    instr = 5
    if mask_all_state :
        instr = 2
    else :
        instr = 5
    register_data[i_station][i_module][i_column][i_chip][0] = 128
    write_packet( i_station, i_module, i_column, i_chip, 0, instr)
    for i_channel in range( len(mask_btn) ) :
         set_btn_state( mask_btn[i_channel], mask_all_state )
    return

def set_all_btn_state() :
    global mask_btn
    global mask_all_state
    print 'set_all_btn_state'
    for i_channel in range( len(mask_btn) ) :
        set_btn_state( mask_btn[i_channel], mask_all_state )
    return

def init_all_channel() :
    global mask_all_state
    global mask_all_btn
    mask_all_state = 1
    set_all_btn_state()
    mask_all_btn.select()
    #write_packet_from_file('init.dat')
    write_init()
    return
    
def destine_report( destine ) :
    global option_destine 
    print 'write to ', destine
    if destine=='chip' :
        option_destine = 'chip'
    elif destine=='eprom' :
        option_destine = 'eprom'
    return

def wild_chip_on_press() :
    global wild_chip_state
    wild_chip_state = not wild_chip_state
    print 'write all chips : ', wild_chip_state
    return

def usb_comm() :
    sys_type = sys.platform
    if sys_type == 'win32' :
        os.system("start usb_test.exe")
    elif sys_type == 'darwin' :
        print 'OS X system'
    elif sys_type.count('linux') > 0 :
        print 'linux system'
    return

def ni_comm() :
    write_packet_from_file('calib.dat')
    sys_type = sys.platform
    if sys_type == 'win32' :
        os.system("start ni_daq_read.exe.lnk")
    elif sys_type == 'darwin' :
        print 'OS X system'
    elif sys_type.count('linux') > 0 :
        print 'linux system'
    return

def read_ni_comm() :
    sys_type = sys.platform
    if sys_type == 'win32' :
        os.system("start ni_daq_read_print.exe.lnk")
    elif sys_type == 'darwin' :
        print 'OS X system'
    elif sys_type.count('linux') > 0 :
        print 'linux system'
    return

def root_comm() :
    sys_type = sys.platform
    if sys_type == 'win32' :
        os.system("start root.exe -l C:/FVTX/plot_calib.C")
    elif sys_type == 'darwin' :
        print 'OS X system'
    elif sys_type.count('linux') > 0 :
        print 'linux system'
    return

def root_fit_comm() :
    sys_type = sys.platform
    if sys_type == 'win32' :
        os.system("start root.exe -l C:/FVTX/Erf_fit_fphx_nhits.C")
    elif sys_type == 'darwin' :
        print 'OS X system'
    elif sys_type.count('linux') > 0 :
        print 'linux system'
    return

def decode_register( data, i_register, i_seg ) :
    tmp_data = data
    if len(register_info[i_register]) == 1 :
        return data
    else :
        for j_seg in range(i_seg+1, len(register_info[i_register])) :
            #print int(tmp_data/(2**register_info[i_register][j_seg][1]))
            tmp_data = tmp_data - int(tmp_data/(2**register_info[i_register][j_seg][1])) * 2**(register_info[i_register][j_seg][1]);
        tmp_data = int(tmp_data/(2**register_info[i_register][i_seg][1]));
    return tmp_data

def update_pulse_no() :
    global pulse_no_ent
    global data_pulse_no
    pulse_no_ent_value = int( pulse_no_ent.get() )
    data_pulse_no = pulse_no_ent_value 
    print "update_pulse_no = ", data_pulse_no

def update_pulse_spacing() :
    global pulse_spacing_ent
    global data_pulse_spacing
    pulse_spacing_ent_value = int( pulse_spacing_ent.get() )
    data_pulse_spacing = pulse_spacing_ent_value 
    print "update_pulse_spacing = ", data_pulse_spacing

def update_pulse_amplitude() :
    global pulse_amplitude_ent
    global data_pulse_amplitude
    pulse_amplitude_ent_value = int( pulse_amplitude_ent.get() )
    data_pulse_amplitude = pulse_amplitude_ent_value 
    print "update_pulse_amplitude = ", data_pulse_amplitude
    
def write_pulse() :
    global data_pulse_no
    global data_pulse_spacing
    global data_pulse_amplitude
    pulse_output = dec_to_bin(255, 8) + dec_to_bin(9, 16) + dec_to_bin(8, 8) + dec_to_bin( data_pulse_spacing, 32) + dec_to_bin( data_pulse_no, 32) + dec_to_bin(255, 8)
    write_bin_str_to_usb(pulse_output)
    print "data_pulse = ", bin_to_hex(pulse_output)
    
def write_pulse_amplitude() :
    global data_pulse_no
    global data_pulse_spacing
    global data_pulse_amplitude
    pulse_amplitude_output = dec_to_bin(255, 8) + dec_to_bin(2, 16) + dec_to_bin(6, 8) + dec_to_bin( data_pulse_amplitude, 8) + dec_to_bin(255, 8)
    write_bin_str_to_usb(pulse_amplitude_output)
    print "data_pulse_amplitude = ", bin_to_hex(pulse_amplitude_output)
    
def collect_data() :
    write_pulse_amplitude()
    write_pulse()
    sys_type = sys.platform
    if sys_type == 'win32' :
        os.system("start ni_daq_read.exe.lnk")
    elif sys_type == 'darwin' :
        print 'OS X system'
    elif sys_type.count('linux') > 0 :
        print 'linux system'
    return

def open_module( i_station, i_module ) :
    global module_win
    #print i_station, i_module
    #print module_win
    if module_win[i_station][i_module] :
        print 'window', module_win[i_station][i_module], 'exist'
        module_win[i_station][i_module].deiconify()
    else :
        module_win_name = 'station_' + str(i_station) + '_module_' + str(i_module)
        if option == 'roc' :
            module_win[i_station][i_module] = Tk()
        else :
            module_win[i_station][i_module] = Toplevel( name=module_win_name )
            module_win[i_station][i_module].bind( '<Destroy>', kill_module )
        win = module_win[i_station][i_module]
        win.title( module_win_name )
        x_edge = 20
        y_edge = 20
        x_max = 0
        y_max = 0
        reg_lbl_width = 30
        reg_f_height = 20
        reg_name_f_width = 120
        column_ctrl_f_width = 300
        chip_f_width = 60
        chip_f_height = 21.5*reg_f_height
        #print n_chip[i_station]
        column_f_width = reg_name_f_width + chip_f_width*n_chip[i_station] + column_ctrl_f_width
        column_f_height = chip_f_height
        module_ctrl_f_width = column_f_width
        module_ctrl_f_height = 60
        cur_x = x_edge
        cur_y = y_edge
        btn_width = 60
        btn_height = 30
        bg_color = 'grey'
        for i_column in range( 0, n_column ) :
            if i_column == 1 : bg_color = 'white'
            column_f = Frame( master=win, bg=bg_color )
            column_f.place( x=cur_x, y=cur_y, width=column_f_width, height=column_f_height )
            cur_x = 0
            cur_y = 0
            reg_name_f = Frame( master=column_f, bg='grey' )
            reg_name_f.place( x=cur_x, y=cur_y, width=reg_name_f_width, height=chip_f_height )

            for i_register_display in range( len(register_display_no) ) :
                i_register = register_display_no[i_register_display]
                for i_seg in range ( len(register_info[i_register]) ) :
                    register_no_name = ''
                    if i_seg == 0 : register_no_name = '' + str(i_register+1)
                    bg_color = 'grey'
                    if i_register_display % 2 == 0 : bg_color = 'white'
                    cur_x = 0
                    register_no_lbl = Label( master=reg_name_f, text=register_no_name, bg=bg_color )
                    register_no_lbl.place( x=cur_x, y=cur_y, width=reg_lbl_width, height=reg_f_height )
                    cur_x += reg_lbl_width
                    register_name_lbl = Label( master=reg_name_f, text=register_info[i_register][i_seg][0], bg=bg_color )
                    register_name_lbl.place( x=cur_x, y=cur_y, width=(reg_name_f_width-reg_lbl_width), height=reg_f_height )
                    #mem_data_lbl[i_station][i_module][i_column][i_chip][i_register][i_seg] = Label( master=register_f, text=str( decode_register(register_data[i_station][i_module][i_column][i_chip][i_register], i_register, i_seg) ), bg=bg_color )
                    #a_lbl = mem_data_lbl[i_station][i_module][i_column][i_chip][i_register][i_seg];
                    #a_lbl.place( x=cur_x, rely=label_y )
                    #cur_x += x_step
                    cur_y += reg_f_height
            cur_x = reg_name_f_width
            cur_y = 0
            for i_chip in range( 0, n_chip[i_station] ) :
                if i_chip % 2 == 0 : bg_color = 'white'
                else : bg_color = 'grey'
                chip_f = Frame( master=column_f, bg=bg_color )
                chip_f.place( x=cur_x, y=cur_y, width=chip_f_width, height=chip_f_height )
                for i_register_display in range( len(register_display_no) ) :
                    i_register = register_display_no[i_register_display]
                    for i_seg in range ( len(register_info[i_register]) ) :
                        bg_color = 'grey'
                        if i_register_display % 2 == 0 : bg_color = 'white'
                        module_mem_data_lbl[i_station][i_module][i_column][i_chip][i_register][i_seg] = Label( master=chip_f, text=str( decode_register(register_data[i_station][i_module][i_column][i_chip][i_register], i_register, i_seg) ), bg=bg_color )
                        a_lbl = module_mem_data_lbl[i_station][i_module][i_column][i_chip][i_register][i_seg];
                        a_lbl.place( x=0, y=cur_y, width=chip_f_width, height=reg_f_height )
                        cur_y += reg_f_height
                
                chip_name = 'Chip_' + str( i_chip )
                chip_btn = Button( master=chip_f, text=chip_name, bg='green', activebackground='red' )
                chip_btn.config( command=( lambda i=i_station, j=i_module, k=i_column, l=i_chip: open_chip(i, j, k, l) ) )
                chip_btn.place( x=10, y=cur_y+5 )
                cur_x += chip_f_width
                if cur_x > x_max : x_max = cur_x
                cur_y = 0
            column_ctrl_f = Frame( master=column_f, bg='blue' )
            column_ctrl_f.place( x=cur_x, y=0, width=column_ctrl_f_width, height=chip_f_height )
            for i_register_display in range( len(register_display_no) ) :
                i_register = register_display_no[i_register_display]
                for i_seg in range ( len(register_info[i_register]) ) :
                    bg_color = 'grey'
                    if i_register_display % 2 == 0 : bg_color = 'white'
                    column_chip_ctrl_f = Frame( master=column_ctrl_f, bg=bg_color )
                    column_chip_ctrl_f.place( x=0, y=cur_y, width=column_ctrl_f_width, height=chip_f_height )
                    module_data_ent_name = 'column_' + str(i_column) + 'register_' + str(i_register) + '_seg' + str(i_seg)
                    module_data_ent[i_station][i_module][i_column][i_register][i_seg] = Entry( name=module_data_ent_name, master=column_chip_ctrl_f, bg=bg_color, width=10 )
                    a_ent = module_data_ent[i_station][i_module][i_column][i_register][i_seg]
                    a_ent.insert( 0, str( decode_register(register_data[i_station][i_module][i_column][0][i_register], i_register, i_seg)) )
                    a_ent.bind( '<Return>', (lambda event, i=i_station, j=i_module, k=i_column, l=-1, m=i_register : write_data(i,j,k,l,m)) )
                    a_ent.place( x=20, y=0 )
                    write_btn = Button( master = column_chip_ctrl_f, text='update', bg='green' )
                    write_btn.config( command=( lambda i=i_station, j=i_module, k=i_column, l=-1, m=i_register : write_data(i,j,k,l,m) ) )
                    write_btn.place( x=100, y=0)
                    write_packet_btn = Button( master = column_chip_ctrl_f, text='write_pkt', bg='green' )
                    write_packet_btn.config( command=( lambda i=i_station, j=i_module, k=i_column, m=i_register : write_all_packet_on_column(i,j,k,m) ) )
                    write_packet_btn.place( x=160, y=0)
                    read_packet_btn = Button( master = column_chip_ctrl_f, text='read_pkt', bg='green' )
                    read_packet_btn.config( command=( lambda i=i_station, j=i_module, k=i_column, m=i_register : write_all_packet_on_column(i,j,k,m) ) )
                    read_packet_btn.place( x=230, y=0)                
                    cur_y += reg_f_height
            column_name = 'Column_' + str( i_column )
            column_lbl_x = btn_width
            column_lbl = Label( master=column_ctrl_f, text= column_name )
            column_lbl.place( x=0, y=cur_y )
            x_max = cur_x + column_ctrl_f_width
            cur_x = x_edge
            cur_y = 0
            cur_y += (column_f_height + 2*y_edge) 
        cur_x = x_max = column_f_width + x_edge
        cur_y = y_max = n_column*column_f_height + 2*y_edge
        module_ctrl_f = Frame( master=win, bg='yellow' )
        module_ctrl_f.place( x=x_edge, y=cur_y, width=module_ctrl_f_width, height=module_ctrl_f_height )
        read_btn = Button( master=module_ctrl_f, text='read', bg='green' )
        read_btn.config( command=( lambda i=i_station, j=i_module: read_file_dialog(i, j) ) )
        read_btn.place( x=0, y=0 )
        write_btn = Button( master=module_ctrl_f, text='write', bg='green' )
        write_btn.config( command=( lambda i=i_station, j=i_module: write_file_dialog(i, j) ) )
        write_btn.place( x=400, y=0 )
        y_max += module_ctrl_f_height
        win.config( width=x_max+x_edge, height=y_max+y_edge )

def open_chip( i_station, i_module, i_column, i_chip ) :
    global chip_win
    global data_ent
    global mem_data_lbl
    #print i_station, i_module, i_column, i_chip
    if chip_win[i_station][i_module][i_column][i_chip] :
        #print 'window', chip_win[i_station][i_module][i_column][i_chip], 'exist'
        chip_win[i_station][i_module][i_column][i_chip].deiconify()
    else :
        chip_win_name = 'station_' + str(i_station) + '_module_' + str(i_module) + '_column_' + str(i_column) + '_chip_' + str(i_chip)
        if option=='test' :
            chip_win[i_station][i_module][i_column][i_chip] = Tk()
        else :
            chip_win[i_station][i_module][i_column][i_chip] = Toplevel( name=chip_win_name )
            chip_win[i_station][i_module][i_column][i_chip].bind( '<Destroy>', kill_chip )
        win = chip_win[i_station][i_module][i_column][i_chip]
        win.title( chip_win_name )
        frm_width = 650
        frm_height = 40
        x_begin = 30
        x_step = 70
        cur_x = x_begin
        cur_y = 0
        label_y = 0.3
        for i_register_display in range( len(register_display_no) ) :
            i_register = register_display_no[i_register_display]
            for i_seg in range ( len(register_info[i_register]) ) :
                register_no_name = ''
                if i_seg == 0 : register_no_name = 'REG' + str(i_register+1)
                bg_color = 'grey'
                if i_register_display % 2 == 0 : bg_color = 'white'
                cur_x = x_begin
                register_f = Frame( master=win, bg=bg_color )
                register_f.place( x=0, y=cur_y, width=frm_width, height=frm_height )
                register_no_lbl = Label( master=register_f, text=register_no_name, bg=bg_color )
                register_no_lbl.place( x=cur_x, rely=label_y )
                cur_x += x_step
                register_name_lbl = Label( master=register_f, text=register_info[i_register][i_seg][0], bg=bg_color )
                register_name_lbl.place( x=cur_x, rely=label_y )
                cur_x += x_step
                mem_data_lbl[i_station][i_module][i_column][i_chip][i_register][i_seg] = Label( master=register_f, text=str( decode_register(register_data[i_station][i_module][i_column][i_chip][i_register], i_register, i_seg) ), bg=bg_color )
                a_lbl = mem_data_lbl[i_station][i_module][i_column][i_chip][i_register][i_seg];
                a_lbl.place( x=cur_x, rely=label_y )
                cur_x += x_step
                data_ent_name = 'register_' + str(i_register) + '_seg' + str(i_seg)
                data_ent[i_station][i_module][i_column][i_chip][i_register][i_seg] = Entry( name=data_ent_name, master=register_f, bg=bg_color, width=10 )
                a_ent = data_ent[i_station][i_module][i_column][i_chip][i_register][i_seg]
                a_ent.insert( 0, str( decode_register(register_data[i_station][i_module][i_column][i_chip][i_register], i_register, i_seg)) )
                a_ent.bind( '<Return>', (lambda event, i=i_station, j=i_module, k=i_column, l=i_chip, m=i_register : write_data(i,j,k,l,m)) )
                a_ent.place( x=cur_x, rely=label_y )
                cur_x += x_step
                read_btn = Button( master = register_f, text=' load ', bg='green' )
                read_btn.config( command=( lambda i=i_station, j=i_module, k=i_column, l=i_chip, m=i_register : read_data(i,j,k,l,m) ) )
                read_btn.place( x=cur_x, rely=label_y)
                cur_x += x_step
                write_btn = Button( master = register_f, text='update', bg='green' )
                write_btn.config( command=( lambda i=i_station, j=i_module, k=i_column, l=i_chip, m=i_register : write_data(i,j,k,l,m) ) )
                write_btn.place( x=cur_x, rely=label_y)
                cur_x += x_step
                write_packet_btn = Button( master = register_f, text='write_packet', bg='green' )
                write_packet_btn.config( command=( lambda i=i_station, j=i_module, k=i_column, l=i_chip, m=i_register : write_packet(i,j,k,l,m, 1) ) )
                write_packet_btn.place( x=cur_x, rely=label_y)
                cur_x += (x_step+20)
                read_packet_btn = Button( master = register_f, text='read_packet', bg='green' )
                read_packet_btn.config( command=( lambda i=i_station, j=i_module, k=i_column, l=i_chip, m=i_register : read_packet(i,j,k,l,m) ) )
                read_packet_btn.place( x=cur_x, rely=label_y)
                cur_x += (x_step+20)
                cur_y += frm_height
        destine_frm = Frame( master=win )
        destine_frm.place( x=0, y=cur_y, width=frm_width, height= 2*frm_height )
        destine_var = StringVar( )
        destine_chip_btn = Radiobutton( master=destine_frm, text='Write to chip(Default)', variable=destine_var, value=str(1) )
        destine_chip_btn.config( command=( lambda destine='chip' : destine_report(destine) ) )
        destine_chip_btn.place( relx=0.3, rely=0.1 )
        destine_eprom_btn = Radiobutton( master=destine_frm, text='Write to eprom', variable=destine_var, value=str(0) )
        destine_eprom_btn.config( command=( lambda destine='eprom' : destine_report(destine) ) )
        destine_eprom_btn.place( relx=0.3, rely=0.6 )
        destine_chip_btn.select()
        global wild_chip_state
        wild_chip_state = 1
        wild_chip_btn = Checkbutton( master=destine_frm, text='Write all chips' )
        wild_chip_btn.config( command=( lambda : wild_chip_on_press() ) )
        wild_chip_btn.place( relx=0.1, rely=0.1 )
        wild_chip_btn.select()
        cur_y += 2*frm_height
        control_frm = Frame( master=win )
        control_frm.place( x=0, y=cur_y, width=frm_width, height= frm_height )
        usb_btn = Button( master=control_frm, text='usb_comm', bg='green' )
        usb_btn.config( command=( lambda : usb_comm() ) )
        #usb_btn.config( command=sys.exit )
        usb_btn.place( relx=0.1, rely=0.3 )
        read_chip_btn = Button( master=control_frm, text='load_data', bg='green' )
        read_chip_btn.config( command=( lambda i=i_station, j=i_module, k=i_column, l=i_chip : read_file_dialog(i,j,k,l) ) )
        read_chip_btn.place( relx=0.25, rely=0.3 )
        write_chip_btn = Button( master=control_frm, text='save_data', bg='green' )
        write_chip_btn.config( command=( lambda i=i_station, j=i_module, k=i_column, l=i_chip : write_file_dialog(i,j,k,l) ) )
        write_chip_btn.place( relx=0.4, rely=0.3 )
        write_from_file_btn = Button( master=control_frm, text='write_from_file', bg='green' )
        write_from_file_btn.config( command=( lambda : write_packet_from_file('') ) )
        write_from_file_btn.place( relx=0.55, rely=0.3 )
        write_all_reg_btn = Button( master=control_frm, text='write_all_reg', bg='green' )        
        write_all_reg_btn.config( command=( lambda i=i_station, j=i_module, k=i_column, l=i_chip : write_packet(i,j,k,l,-1) ) )
        write_all_reg_btn.place( relx=0.69, rely=0.3 )
        read_all_reg_btn = Button( master=control_frm, text='read_all_reg', bg='green' )
        read_all_reg_btn.config( command=( lambda i=i_station, j=i_module, k=i_column, l=i_chip : read_packet(i,j,k,l,-1) ) )
        read_all_reg_btn.place( relx=0.83, rely=0.3 )
        cur_y += frm_height

        global n_btn_x
        global n_btn_y
        if (option_chip == 'fpix') :
            n_btn_x = 22
            n_btn_y = 128
            can_width = 480
            can_height = 2400
            edge = 20
        elif (option_chip == 'fphx') :
            n_btn_x = 16
            n_btn_y = 8
            can_width = 480
            can_height = 400
            edge = 20
        step_x = (can_width-2*edge)/(n_btn_x+1)
        step_y = (can_height-2*edge)/n_btn_y
        frm_height_total = cur_y  #cur_y

        global data_pulse_no
        global data_pulse_spacing
        global data_pulse_amplitude
        data_pulse_no = 9
        data_pulse_spacing = 10
        data_pulse_amplitude = 31
        cur_y = 0
        x_offset_in_pulse = 30
        x_step_in_pulse = 100
        y_step_in_pulse = 40
        cur_x_in_pulse = x_offset_in_pulse
        cur_y_in_pulse = 0
        pulse_frm_height = 120
        pulse_frm = Frame( master=win )
        pulse_frm.place( x=cur_x, y=0, width=can_width, height=pulse_frm_height )
        pulse_label_y = 0.3

        bg_color = "grey"        
        pulse_no_frm = Frame( master=pulse_frm, bg=bg_color )
        pulse_no_frm.place( x=0, y=cur_y_in_pulse, width=can_width, height=y_step_in_pulse )
        Label( master=pulse_no_frm, text="pulse # ", bg=bg_color ).place( x=cur_x_in_pulse, rely=pulse_label_y )
        cur_x_in_pulse += x_step_in_pulse
        global pulse_no_ent
        pulse_no_ent_name = 'pulse_no'
        pulse_no_ent = Entry( name=pulse_no_ent_name, master=pulse_no_frm, bg=bg_color, width=10 )
        pulse_no_ent.insert( 0, str(data_pulse_no) )
        pulse_no_ent.bind( '<Return>', (lambda event : update_pulse_no()) )
        pulse_no_ent.place( x=cur_x_in_pulse, rely=pulse_label_y )
        cur_x_in_pulse += x_step_in_pulse
        update_pulse_no_btn = Button( master = pulse_no_frm, text='update', bg='green' )
        update_pulse_no_btn.config( command=( lambda : update_pulse_no() ) )
        update_pulse_no_btn.place( x=cur_x_in_pulse, rely=pulse_label_y )
        cur_x_in_pulse += x_step_in_pulse
        write_pulse_no_btn = Button( master = pulse_no_frm, text='write', bg='green' )
        write_pulse_no_btn.config( command=( lambda : collect_data() ) )
        write_pulse_no_btn.place( x=cur_x_in_pulse, rely=pulse_label_y )
        cur_x_in_pulse += x_step_in_pulse
        cur_y_in_pulse += y_step_in_pulse
        
        bg_color = "white"
        pulse_spacing_frm = Frame( master=pulse_frm, bg=bg_color )
        pulse_spacing_frm.place( x=0, y=cur_y_in_pulse, width=can_width, height=y_step_in_pulse )
        cur_x_in_pulse = x_offset_in_pulse
        Label( master=pulse_spacing_frm, text="pulse spacing ", bg=bg_color ).place( x=cur_x_in_pulse, rely=pulse_label_y )
        cur_x_in_pulse += x_step_in_pulse
        global pulse_spacing_ent
        pulse_spacing_ent_name = 'pulse_spacing'
        pulse_spacing_ent = Entry( name=pulse_spacing_ent_name, master=pulse_spacing_frm, bg=bg_color, width=10 )
        pulse_spacing_ent.insert( 0, str(data_pulse_spacing) )
        pulse_spacing_ent.bind( '<Return>', (lambda event : update_pulse_spacing()) )
        pulse_spacing_ent.place( x=cur_x_in_pulse, rely=pulse_label_y )
        cur_x_in_pulse += x_step_in_pulse
        update_pulse_spacing_btn = Button( master = pulse_spacing_frm, text='update', bg='green' )
        update_pulse_spacing_btn.config( command=( lambda : update_pulse_spacing() ) )
        update_pulse_spacing_btn.place( x=cur_x_in_pulse, rely=pulse_label_y )
        cur_x_in_pulse += x_step_in_pulse
        write_pulse_spacing_btn = Button( master = pulse_spacing_frm, text='write', bg='green' )
        write_pulse_spacing_btn.config( command=( lambda : collect_data() ) )
        #write_pulse_spacing_btn.place( x=cur_x_in_pulse, rely=pulse_label_y )
        cur_x_in_pulse += x_step_in_pulse
        cur_y_in_pulse += y_step_in_pulse
        cur_y = cur_y_in_pulse
        
        bg_color = "grey"
        pulse_amplitude_frm = Frame( master=pulse_frm, bg=bg_color )
        pulse_amplitude_frm.place( x=0, y=cur_y_in_pulse, width=can_width, height=y_step_in_pulse )
        cur_x_in_pulse = x_offset_in_pulse
        Label( master=pulse_amplitude_frm, text="pulse amplitude ", bg=bg_color ).place( x=cur_x_in_pulse, rely=pulse_label_y )
        cur_x_in_pulse += x_step_in_pulse
        global pulse_amplitude_ent
        pulse_amplitude_ent_name = 'pulse_amplitude'
        pulse_amplitude_ent = Entry( name=pulse_amplitude_ent_name, master=pulse_amplitude_frm, bg=bg_color, width=10 )
        pulse_amplitude_ent.insert( 0, str(data_pulse_amplitude) )
        pulse_amplitude_ent.bind( '<Return>', (lambda event : update_pulse_amplitude()) )
        pulse_amplitude_ent.place( x=cur_x_in_pulse, rely=pulse_label_y )
        cur_x_in_pulse += x_step_in_pulse
        update_pulse_amplitude_btn = Button( master = pulse_amplitude_frm, text='update', bg='green' )
        update_pulse_amplitude_btn.config( command=( lambda : update_pulse_amplitude() ) )
        update_pulse_amplitude_btn.place( x=cur_x_in_pulse, rely=pulse_label_y )
        cur_x_in_pulse += x_step_in_pulse
        write_pulse_amplitude_btn = Button( master = pulse_amplitude_frm, text='write', bg='green' )
        write_pulse_amplitude_btn.config( command=( lambda : collect_data() ) )
        #write_pulse_amplitude_btn.place( x=cur_x_in_pulse, rely=pulse_label_y )
        cur_x_in_pulse += x_step_in_pulse
        cur_y_in_pulse += y_step_in_pulse
        cur_y = cur_y_in_pulse
        
        mask_name_frm = Frame( master=win )
        Label( master=mask_name_frm, text='Bit Mask' ).pack()
        mask_name_frm.place( x=cur_x, y=cur_y, width=can_width, height=frm_height )
        cur_y += frm_height
        mask_all_frm = Frame( master=win )
        mask_all_frm.place( x=cur_x, y=cur_y, width=can_width, height= frm_height )
        cur_y += frm_height
        reset_btn = Button( master=mask_all_frm, text='reset', bg='red' )
        #reset_btn.config( command=( lambda : write_packet_from_file('reset.dat') ) )
        reset_btn.config( command=( lambda : write_reset() ) )
        reset_btn.place( relx=0.05, rely=0.3 )
        init_btn = Button( master=mask_all_frm, text=' init ', bg='green' )
        init_btn.config( command=( lambda : init_all_channel() ) )
        init_btn.place( relx=0.15, rely=0.3 )
        calib_btn = Button( master=mask_all_frm, text='calib', bg='yellow' )
        calib_btn.config( command=( lambda : ni_comm()) )
        calib_btn.place( relx=0.25, rely=0.3 )
        read_btn = Button( master=mask_all_frm, text='read', bg='yellow' )
        read_btn.config( command=( lambda : read_ni_comm()) )
        read_btn.place( relx=0.32, rely=0.3 )
        ampl_btn = Button( master=mask_all_frm, text='amp', bg='white' )
        ampl_btn.config( command=( lambda : write_packet_from_file('write_ampl.dat')) )
        ampl_btn.place( relx=0.4, rely=0.3 )
        pulse_btn = Button( master=mask_all_frm, text='pulse', bg='white' )
        pulse_btn.config( command=( lambda : write_packet_from_file('pulse.dat')) )
        pulse_btn.place( relx=0.46, rely=0.3 )
        analy_btn = Button( master=mask_all_frm, text='analyze', bg='lightblue' )
        analy_btn.config( command=( lambda : root_comm()) )
        analy_btn.place( relx=0.55, rely=0.3 )
        fit_btn = Button( master=mask_all_frm, text='fit', bg='lightblue' )
        fit_btn.config( command=( lambda : root_fit_comm()) )
        fit_btn.place( relx=0.65, rely=0.3 )
        global mask_all_state
        mask_all_state = 1
        global mask_all_btn
        mask_all_btn = Checkbutton( master=mask_all_frm, text='Mask all channels' )
        mask_all_btn.config( command=( lambda i=i_station, j=i_module, k=i_column, l=i_chip : mask_all_on_press(i, j, k, l) ) )
        mask_all_btn.place( relx=0.7, rely=0.3 )
        mask_all_btn.select()
        mask_btn_frm = Frame( master=win)
        mask_btn_frm.place( x=cur_x, y=cur_y, width=can_width, height=frm_height_total-frm_height )
        cur_x += can_width
        mask_btn_no_frm = Frame( mask_btn_frm, width=can_width, height=20 )
        mask_btn_no_frm.pack()
        pos_x = edge+step_x-5
        for col in range(n_btn_x) :
            mask_x_lbl = Label( master=mask_btn_no_frm, text=str(col) )
            mask_x_lbl.place( x=pos_x, rely=0.1 )
            pos_x += step_x
        mask_btn_can = Canvas( master=mask_btn_frm )
        mask_btn_can.config( bg='grey', width=frm_width, height=frm_height_total-frm_height, scrollregion=(0, 0, can_width, can_height) )
        #mask_btn_can.create_line( 100, 100, 300, 300 )      
        can_y_scr = Scrollbar( master=mask_btn_frm )
        can_y_scr.config( orient=VERTICAL, command=mask_btn_can.yview )
        can_y_scr.pack( side=RIGHT, fill=Y )
        mask_btn_can.config( yscrollcommand=can_y_scr.set )
        mask_btn_can.pack( side=LEFT, expand=YES, fill=BOTH )
        pos_y = edge
        n_mask_channel = n_btn_x * n_btn_y
        global mask_btn
        mask_btn = []
        for row in range( n_btn_y ) :
            pos_x = edge
            mask_y_lbl = Label( mask_btn_can, text=str(row), bg='grey' )
            mask_y_lbl.place( x=pos_x, y=pos_y )
            mask_btn_can.create_window( pos_x, pos_y, width=15, height=15, window=mask_y_lbl )
            pos_x += step_x
            for col in range( n_btn_x ) :
                channel = row*n_btn_x + col
                a_mask_btn = Button( mask_btn_can, text='X', bg='red' )
                mask_btn.append( a_mask_btn )
                mask_btn[channel].config( command=( lambda i=i_station, j=i_module, k=i_column, l=i_chip, channel=channel : mask_channel( i, j, k, l, channel ) ) )
                mask_btn[channel].place( x=pos_x, y=pos_y )
                mask_btn_can.create_window( pos_x, pos_y, width=15, height=15, window=mask_btn[channel] )
                pos_x += step_x
            pos_y += step_y
        win.config( width=cur_x+30, height=frm_height_total )
            
init()
if option == 'test' :
    open_chip(0,0,0,0)
    focus_chip(0,0,0,0)
    chip_win[0][0][0][0].mainloop()
elif option == 'roc' :
    open_module(1,0)   # station 0 : 5 chips, 1 : 13 chips  
    module_win[1][0].mainloop()
else :
    mw_x = 800
    mw_y = 1000
    mw = Tk()
    mw.config( width=mw_x, height=mw_y )
    mw_title = option.upper() + '_GUI'
    mw.title( mw_title )

    cur_y = 0
    time_frm_y = 50
    time_frm = Cur_Time( )
    time_frm.place( x=0, y=cur_y, width=mw_x, height=time_frm_y )
    cur_y += time_frm_y

    station_lbl_y = 50
    station_lbl_frm = Frame( mw, bg='yellow' )
    station_lbl_frm.place( x=0, y=cur_y, width=mw_x, height=station_lbl_y )
    cur_y += station_lbl_y
    station_lbl = range(n_station)
    for i_station in range(0, n_station) :
        station_name = 'Station_' + str(i_station)
        station_x = 0.2*i_station + 0.15

        station_lbl[i_station] = Label( station_lbl_frm )
        station_lbl[i_station].config( text=station_name )
        station_lbl[i_station].place( relx=station_x, rely=0.3 )

    module_frm_y = max( n_module )*18
    module_frm = Frame( mw )
    module_frm.place( x=0, y=cur_y, width=mw_x, height= module_frm_y )
    cur_y += module_frm_y

    module_btn = [[0 for x in range(max(n_module))] for y in range(n_station)]
    #print len( module_btn )
    for i_station in range(0, n_station) :
        for i_module in range(0, n_module[i_station]) :
            module_x = 0.2*i_station + 0.08*( int(i_module) / int(n_module[i_station]/2) ) + 0.1
            module_y = 1.96/float(max(n_module)) * (i_module%(n_module[i_station]/2)) + 0.02
            module_name = str(i_module)
        
            module_btn[i_station][i_module] = Button( module_frm, text=module_name, bg='green', activebackground='red' )
            module_btn[i_station][i_module].config( command=( lambda i=i_station, j=i_module: open_module(i, j) ) )
            module_btn[i_station][i_module].place( width=40, height=20, relx=module_x, rely=module_y )
        
    control_frm_y = 100
    control_frm = Frame( mw )
    control_frm.config( bg='grey' )
    control_frm.place( x=0, y=cur_y, width=mw_x, height=control_frm_y )
    cur_y += control_frm_y
    for i_station in range( n_station ) :
        read_station_btn_x = 0.2*i_station + 0.15
        read_station_btn = Button( control_frm, text='read', bg='green', command=( lambda i=i_station: read_file_dialog(i) ) )
        read_station_btn.place( relx=read_station_btn_x, rely=0.2, width=40, height=20 )

        write_station_btn = Button( control_frm, text='write', bg='green', command=( lambda i=i_station: write_file_dialog(i) ) )
        write_station_btn.place( relx=read_station_btn_x, rely=0.6, width=40, height=20 )

    status_txt_y = 100
    status_txt = Text( mw, bg='white' )
    status_txt.place( x=0, y=cur_y, width=mw_x, height=status_txt_y )
    cur_y += status_txt_y

    exit_btn = Button( mw, text='exit', bg='green', activebackground='red', command=sys.exit )
    exit_btn.place( relx=0.925, rely=0.01 )

    mw.config( width=mw_x, height=cur_y )
    mw.mainloop()




    
