from Tkinter import *
import Tix
try:
    import ftd2xx # For the API to the DLP2232 USB controller (Future Technologies)
    #print 'ftd2xx Version:',ftd2xx.getLibraryVersion() 
except ImportError:
    print "Failed to import ftd2xx"
except:
    pass
import ftplib
import re

#default_ip = "127.0.0.1"
#BNL Physics 2-89:
default_ip = "192.168.60.220" 
default_port = 9900

# Create a communications frame for the I/O (USB or FTP)
class comm_panel(LabelFrame):
    def __init__(self,parent,**kwargs):
        LabelFrame.__init__(self,parent,kwargs)
        # Get a list of DLP devices connected to the host
        devList = []
        devs = ftd2xx.listDevices()
        if devs:
            for i, e in enumerate(devs):
                details = ftd2xx.getDeviceInfoDetail(i)
                test = re.match('^DLP2232M.*',details['description'])
                if test:
                    devList.append(details['serial'])
        devList.append("None")

        self.comm_var = IntVar(None,0)
        Radiobutton(self,variable=self.comm_var,value=0,text='USB').grid(row=0,column=0)
        self.usbdev_var = StringVar(None,devList[0])
        usbdev_menu = OptionMenu(self,self.usbdev_var,*devList)
        usbdev_menu.grid(row=0, column=1,sticky=W)
        self.baud_rate = IntVar(None,115200)
        Label(self,text="Baud Rate",justify=RIGHT).grid(row=1,column=0)
        Entry(self,textvariable=self.baud_rate,width=10,justify=RIGHT).grid(row=1,column=1,sticky=E+W)
        Radiobutton(self,variable=self.comm_var,value=1,text='Ethernet').grid(row=0,column=2)
        self.ipaddr_var = StringVar(None,default_ip)
        Label(self,text="IP Addr",justify=RIGHT).grid(row=0,column=3)
        Entry(self,textvariable=self.ipaddr_var,width=10,justify=RIGHT).grid(row=0,column=4)
        self.ipport_var = StringVar(None,str(default_port))
        Label(self,text="Port",justify=RIGHT).grid(row=0,column=5)
        Entry(self,textvariable=self.ipport_var,width=5,justify=RIGHT).grid(row=0,column=6)

    def getType(self):
        return self.comm_var.get()

    def getDevice(self):
        return self.usbdev_var.get()

    def getIPAddress(self):
        if self.ipport_var.get() == "":
            return [ self.ipaddr_var.get() ]
        return [self.ipaddr_var.get(),self.ipport_var.get()]

    def getTarget(self):
        which = self.comm_var.get()
        if which == 0:
            return self.getDevice()
        else:
            return ":".join(self.getIPAddress())

    def getBaudRate(self):
        return self.baud_rate.get()

def testprint(cpanel):
    whichcomm = cpanel.comm_var.get()
    usbdev_choice = cpanel.usbdev_var.get()
    print "Type is",cpanel.getType()
    print "Device",cpanel.getDevice()
    print "Target",cpanel.getTarget()
    return

def testsend(cpanel):
    whichcomm = cpanel.comm_var.get()
    if whichcomm == 0:
        pass
    else:
        (ip,port) = cpanel.getIPAddress()
        try:
            session = ftplib.FTP()
            session.connect(ip,int(port))
            session.login('anonymous')
            session.storbinary('STOR WriteFile.py',open('comm_panel.py','rb'))
            session.retrbinary('RETR WriteFile.py',open('ReadFile.py','wb').write)
            session.dir()
        except Exception,e:
            print "Failure opening or during FTP session: %s" % e

if __name__ == '__main__':

    root = Tk()
    f = Frame(root)
    f.grid(row=0,column=0)
    c = comm_panel(f,text='Test Communications Panel')
    c.grid(row=0,column=0)
    b = Button(f,text='Print',command=lambda x=c: testprint(x))
    b.grid(row=0,column=1)
    s = Button(f,text='Send',command=lambda x=c: testsend(x))
    s.grid(row=0,column=2)
    
    root.mainloop()
