import PyTango
from sardana.pool.controller import CounterTimerController
import time

from sardana import State, DataAccess
from sardana.pool.controller import MotorController
from sardana.pool.controller import Type, Access, Description, DefaultValue
from sardana.pool import PoolUtil

ReadOnly = DataAccess.ReadOnly
ReadWrite = DataAccess.ReadWrite

class MCAroisCtrl(CounterTimerController):
    "This class is the Tango Sardana CounterTimer controller for the MCA RoIs"
	

    axis_attributes = {'TangoDevice':{Type:str,Access:ReadOnly},
                       'TangoAttribute':{Type:str,Access:ReadWrite},
                       }
		     
    ctrl_properties = {'RootDeviceName':{Type:str,Description:'The root name of the MCArois Tango devices'},
                       'TangoHost':{Type:str,Description:'The tango host where searching the devices'}, 
                       }

    gender = "CounterTimer"
    model = "MCArois"
    organization = "DESY"
    state = ""
    status = ""
    
    def __init__(self,inst,props, *args, **kwargs):
        self.TangoHost = None
        CounterTimerController.__init__(self,inst,props, *args, **kwargs)
        if self.TangoHost != None:
            self.node = self.TangoHost
            self.port = 10000
            if self.TangoHost.find( ':'):
                lst = self.TangoHost.split(':')
                self.node = lst[0]
                self.port = int( lst[1])
        self.started = False
        self.dft_Offset = 0
        self.Offset = []
        self.AttributeNames = []
        proxy_name = self.RootDeviceName
        if self.TangoHost != None:
            proxy_name = str(self.node) + (":%s/" % self.port) + str(proxy_name)
        self.proxy = PyTango.DeviceProxy(proxy_name)

    def AddDevice(self,ind):
        CounterTimerController.AddDevice(self,ind)
        self.Offset.append(self.dft_Offset)
        self.AttributeNames.append("")
        if ind == 1:
            self.AttributeNames[ind -1] = "Master"
        
    def DeleteDevice(self,ind):
        CounterTimerController.DeleteDevice(self,ind)
        self.proxy =  None
        
		
    def StateOne(self,ind):
        sta = self.proxy.command_inout("State")
        if sta == PyTango.DevState.ON:
            status_string = "MCA is in ON state"
        elif sta == PyTango.DevState.MOVING:
            status_string = "MCA is busy"
        tup = (sta, status_string)
        return tup

    def PreReadAll(self):
        pass
        

    def PreReadOne(self,ind):
        if ind == 1:
            if self.proxy.state() != PyTango.DevState.ON:
                self.proxy.command_inout("Stop")
            self.proxy.command_inout("Read")

    def ReadAll(self):
        pass

    def PreStartOne(self,ind,pos):
        return True
        
    def StartOneCT(self,ind):
        if ind == 1:
        # the state may be ON but one bank can be active
            self.proxy.command_inout("Stop")
            #self.proxy.command_inout("Clear")
            self.proxy.command_inout("Start")
            
    def ReadOne(self,ind):
        if ind == 1:
            value = -1
        else:
            value = self.proxy.read_attribute(self.AttributeNames[ind-1]).value
        return  value
	
    def AbortOne(self,ind):
        pass
        
    def PreStartAllCT(self):
        self.wantedCT = []

    def PreStartOneCT(self,ind):
        pass
	
    def StartAllCT(self):
        pass
		     	
    def LoadOne(self,ind,value):
        self.exp_time = value
	
    def GetExtraAttributePar(self,ind,name):
        if name == "TangoDevice":
            tango_device = self.node + ":" + str(self.port) + "/" + self.proxy.name() 
            return tango_device
        if name == "TangoAttribute":
            return self.AttributeNames[ind-1]
        
            
    def SetExtraAttributePar(self,ind,name,value):
        if name == "TangoAttribute":
            if ind != 1:
                self.AttributeNames[ind-1] = value
			
    def SendToCtrl(self,in_data):
        return "Nothing sent"

    def __del__(self):
        print "PYTHON -> MCAroisCtrl/",self.inst_name,": dying"
