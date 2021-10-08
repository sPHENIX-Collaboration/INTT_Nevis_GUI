
from __future__ import with_statement # >=2.5 only
from Tkinter import *
import threading
import Queue
import time
import random
from fphxtb import *
import ftd2xx
import dlpth1

class env_panel(Frame):
    def __init__(self,parent,poll=True):
        Frame.__init__(self,parent)
        self.queue = Queue.Queue()
        self.update_interval = 100

        self.sensor = dlpth1.dlpth1()

        # Probe for all available temp sensors
        envDevList = []
        devs = listDevices()
        if devs:
            for i, e in enumerate(devs):
                details = ftd2xx.getDeviceInfoDetail(i)
            #print details
            if details['description'] == 'DLP-TH1':
                envDevList.append(details['serial'])
        envDevList.append("None")

        self.envDev = StringVar(None,envDevList[0])
        envDev_menu = OptionMenu(self,self.envDev,*envDevList)
        envDev_menu.grid(row=0, column=1,sticky=W)
        self.temp_var = DoubleVar(None,0.0)
        self.relh_var = DoubleVar(None,0.0)
        self.dewp_var = DoubleVar(None,0.0)
        Label(self,text="Temp").grid(row=0,column=2)
        Entry(self,state="readonly",textvariable=self.temp_var,readonlybackground='white',justify=RIGHT,width=6).grid(row=0,column=3)
        Label(self,text="C",justify=LEFT).grid(row=0,column=4,sticky=W)
        Label(self,text="RelHumid").grid(row=0,column=5)
        Entry(self,state="readonly",textvariable=self.relh_var,readonlybackground='white',justify=RIGHT,width=6).grid(row=0,column=6)
        Label(self,text="%",justify=LEFT).grid(row=0,column=7,sticky=W)
        Label(self,text="DewPt").grid(row=0,column=8)
        Entry(self,state="readonly",textvariable=self.dewp_var,readonlybackground='white',justify=RIGHT,width=6).grid(row=0,column=9)
        Label(self,text="%",justify=LEFT).grid(row=0,column=10,sticky=W)

        self.lock = threading.Lock();
        self.var = DoubleVar(None,1.1)
        #Label(self, text="Output:").grid(row=0,sticky=W)
        #Entry(self,textvariable=self.var,state="readonly",readonlybackground='white',justify=RIGHT).grid(row=0,column=1)
        self._stop = threading.Event()
        if poll:
            self.thread = threading.Thread(target=self.do_something)
            if sys.version_info >= (2, 6): self.thread.daemon = True
            else: self.thread.setDaemon(True)
            self.thread.start()
        self.update_display()
        return

    def __del__(self):
        print "__del__"

    def stop (self):
        print 'stop'
        self._stop.set()
        
    def stopped (self):
        return self._stop.isSet()

    def clear(self):
        self.queue.put(None)
        return
        
    def write(self,obj):
        self.queue.put(obj)
        return

    def update_display(self):
        try:
            while 1:
                obj = self.queue.get_nowait()
                if obj is None:
                    print "no object"
                else:
                    #self.var.set(float(obj))
                    self.temp_var.set(obj['temp'])
                    self.relh_var.set(obj['relh'])
                    self.dewp_var.set(obj['dewp'])
                self.update_idletasks()
        except Queue.Empty:
            pass
        self.after(self.update_interval, self.update_display)
        return
    
    # TODO: Replace the body of this code with readout of the sensor + calculation of
    # the values from the raw data
    def do_something(self):
        while not self.stopped():
            time.sleep(2)
            if self.envDev.get() != 'None':
                try:
                    val1, val2, val3 = self.getValues()
                except:
                    val1, val2, val3 = 0.0, 0.0, 0.0
                    pass # If the device is not present, it's not catastrophic
#                with self.lock:
#                    self.sensor.open(self.envDev.get())
#                    self.sensor.configure()
#                    self.sensor.read_temp()
#                    self.sensor.read_humid()
#                    val1, val2, val3 = self.sensor.getMeasurement()
#                    self.sensor.close()
            else:
                val1, val2, val3 = 0.0, 0.0, 0.0
            #val1 = random.random()
            #val2 = random.random()
            #val3 = random.random()
            self.write({'temp':val1, 'relh':val2, 'dewp':val3})
        return

    def getValues(self):
        with self.lock:
            try:
                self.sensor.open(self.envDev.get())
                self.sensor.configure()
                self.sensor.read_temp()
                self.sensor.read_humid()
                a = self.sensor.getMeasurement()
                self.sensor.close()
            except:
                a = 0.0, 0.0, 0.0
            self.write({'temp':a[0], 'relh':a[1], 'dewp':a[2]})
            return a

if __name__ =='__main__':

    # Test code for the above class.
    master = Tk()
    env_panel(master,False).grid(row=0,column=0)
    master.mainloop()
