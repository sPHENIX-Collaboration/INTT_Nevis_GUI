#!/usr/bin/python


# Implement a panel representing a PS (the E363xx models)

import e363xx
import time
import threading
from Tkinter import *
import tkMessageBox
import Tix
import threading
import Queue
import sys

class ps_panel(Tix.Frame):
    def __init__(self,master,**options):
        self.master = master
        # Create a register frame to contain all the register display info
        Tix.Frame.__init__(self,master)
        self.ps = None
        try:
            #self.ps = e363xx.e363xx('COM1',1,True)
            self.ps = e363xx.e363xx(0,1,True) # Open the first serial port
        except Exception, e:
            msg = "Failed to open PS:\n%s" % (`e`)
            tkMessageBox.showwarning("Power Supply Access",msg)

        self.voltage = StringVar(None,"0.0")
        self.current = StringVar(None,"0.0")
        self.UPDATE_INTERVAL = 2000 # in ms

        # Create and layout the widgets
        devIdstr = "No Serial Port found"
        state = -1
        if self.ps:
            devIdstr = "No Power Supply Found on Serial Port"
            dev = self.ps.identify()
            if dev:
                a = dev.split(",")
                devIdstr = "%s %s" % (a[0],a[1])
                state = self.ps.getOutputState()
            
        Label(self, text="Model:").grid(row=0,sticky=W)
        Label(self, text=devIdstr).grid(row=0,column=1,columnspan=5)
        Label(self, text="Output:").grid(row=1,sticky=W)
        Entry(self,textvariable=self.voltage,state="readonly",readonlybackground='white',justify=RIGHT).grid(row=1,column=1)
        Label(self, text="V").grid(row=1,column=2)
        Entry(self,textvariable=self.current,state="readonly",readonlybackground='white',justify=RIGHT).grid(row=1,column=3)
        Label(self, text="A").grid(row=1,column=4)
        self.outputtext_var = StringVar(None,"Output Off")
        self.outputdata_var = IntVar(None,0)
        if state == 1:
            self.outputdata_var.set(1)
            self.outputtext_var.set("Output On")
        self.output_state = Checkbutton(self, textvariable=self.outputtext_var, bg="palegreen1",
                                        indicatoron=0, selectcolor='red', variable=self.outputdata_var,
                                        width=9).grid(row=1,column=5)
        self.outputdata_var.trace("w",lambda *args: self.toggle_output(self))

        # Start the readout
        if self.ps != None:
            self.queue = Queue.Queue()
            self._stop = threading.Event()
            self.thread = threading.Thread(target=self.read_outputvals,name="VIReadThread")
            if sys.version_info >= (2, 6): self.thread.daemon = True
            else: self.thread.setDaemon(True)
            self.thread.start()
            self.update_display()
        return

    def get_outputstate(self):
        return self.ps.getOutputState()

    def toggle_output(self,*args):
        if self.outputdata_var.get() == 1:
            self.outputtext_var.set('Output On')
            self.ps.output_onoff(1)
            #self.output_state.config(fg='black',bg='green')
        elif self.outputdata_var.get() == 0:
            self.outputtext_var.set('Output Off')
            self.ps.output_onoff(0)
            #self.output_state.config(fg='white',bg='red')
        return

    def stop(self):
        self._stop.set()
        return

    def stopped (self):
        return self._stop.isSet()

    def clear(self):
        self.queue.put(None)
        return
        
    def write(self,obj):
        self.queue.put(obj)
        return

    def read_outputvals(self):
        while not self.stopped():
            try:
                voltStr = self.ps.getVoltage()
                currStr = self.ps.getCurrent()
                self.write((voltStr,currStr))
            except:
                pass
            time.sleep(2.0)
        return

    def update_display(self):
        try:
            while 1:
                obj = self.queue.get_nowait()
                if obj is None:
                    print "no object"
                else:
                    self.voltage.set(float(obj[0]))
                    self.current.set(float(obj[1]))
                self.update_idletasks()
        except Queue.Empty:
            pass
        self.after(self.UPDATE_INTERVAL, self.update_display)
        return

    def getVoltage(self):
        val = "0.0"
        if self.ps: val = self.ps.getVoltage()
        return float(val)

    def getCurrent(self):
        val = "0.0"
        if self.ps: val = self.ps.getCurrent()
        return float(val)

#
# Main body of the script
#
if __name__ =='__main__':

    # Test code for the above class.

    master = Tk()
    ps_panel(master).grid(row=0,column=0)
    master.mainloop()
