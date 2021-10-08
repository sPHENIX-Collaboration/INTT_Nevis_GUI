
from Tkinter import *
import tkSimpleDialog

class GetPasswd(tkSimpleDialog.Dialog):
    def __init__(self,parent=None,title=None):
        if not parent:
            import Tkinter
            parent = Tkinter._default_root
        tkSimpleDialog.Dialog.__init__(self,parent,title)

    def body(self,master):
        Label(master,text="Username:").grid(row=0,column=0)
        Label(master,text="Password:").grid(row=1,column=0)
        self.user_entry = Entry(master,name="usernameEntry")
        self.pass_entry = Entry(master,name="passwordEntry",show="*")
        self.user_entry.grid(row=0,column=1)
        self.pass_entry.grid(row=1,column=1)
        return self.user_entry
        #return None

    def apply(self):
        username = self.user_entry.get()
        password = self.pass_entry.get()
        self.result = username, password

#
# Main body of the script
#
if __name__ =='__main__':

    master = Tk()
    master.withdraw()

    d = GetPasswd(master,title='Login')
    print d.result

    #master.mainloop()
